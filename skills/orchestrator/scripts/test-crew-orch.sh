#!/usr/bin/env bash
# Seeded test of crew-orch.py (spec #151, AC1 to AC10, AC12, C6 and C10), and
# of `board --json` (spec #155, R1 to R3 and R16).
#
# It uses a temporary record root, a stub `gh` and a stub `crew-usage.py`.
# It never touches ~/.claude/crew and never starts `claude`. It runs every
# command from a temporary directory outside the repo. It stops at the first
# failed check and exits non-zero.
set -u

HERE=$(cd "$(dirname "$0")" && pwd)
ORCH_PY="$HERE/crew-orch.py"
STATS_PY="$HERE/../../project-lead/scripts/crew-stats.py"

TMP=$(mktemp -d)
trap 'rm -rf "$TMP"' EXIT
export CREW_RECORD_ROOT="$TMP/root"
mkdir -p "$CREW_RECORD_ROOT" "$TMP/bin" "$TMP/gh" "$TMP/work"
unset CREW_ORCH
cd "$TMP/work" || exit 1

STEP=""
fail() {
  echo "FAIL [$STEP]: $*" >&2
  exit 1
}
pass() { echo "ok   $STEP"; }

orch() { python3 "$ORCH_PY" --orch fleet "$@"; }

# expect_exit <code> <command...>: run the command, check its exit code.
expect_exit() {
  local want=$1
  shift
  "$@" >"$TMP/out" 2>"$TMP/err"
  local got=$?
  [ "$got" -eq "$want" ] || fail "exit $got, expected $want: $* (stderr: $(cat "$TMP/err"))"
}

# one_line_err: the last command wrote exactly one line to stderr.
one_line_err() {
  [ "$(wc -l <"$TMP/err" | tr -d ' ')" -eq 1 ] || fail "stderr is not one line: $(cat "$TMP/err")"
}

# jcheck <python expression over `s`>: `s` is the parsed output of `show`.
jcheck() {
  python3 "$ORCH_PY" --orch fleet show >"$TMP/show.json" || fail "show failed"
  python3 - "$TMP/show.json" "$1" <<'PY' || fail "check is false: $1"
import json, sys
s = json.load(open(sys.argv[1]))
sys.exit(0 if eval(sys.argv[2]) else 1)
PY
}

# The stub gh. It answers `gh pr view <n> ...` from $TMP/gh/pr-<n>.json and
# `gh api graphql ... -F n=<n>` from $TMP/gh/queue-<n>.json. A missing file
# is a failed call.
cat >"$TMP/bin/gh" <<EOF
#!/usr/bin/env bash
D="$TMP/gh"
echo "\$*" >>"\$D/calls.log"
if [ "\$1" = pr ] && [ "\$2" = view ]; then
  f="\$D/pr-\$3.json"
elif [ "\$1" = api ] && [ "\$2" = graphql ]; then
  n=""
  for a in "\$@"; do case "\$a" in n=*) n="\${a#n=}" ;; esac; done
  f="\$D/queue-\$n.json"
else
  echo "stub gh: unknown call: \$*" >&2; exit 1
fi
[ -f "\$f" ] || { echo "stub gh: no data for \$*" >&2; exit 1; }
cat "\$f"
EOF
chmod +x "$TMP/bin/gh"
export PATH="$TMP/bin:$PATH"

# ---------------------------------------------------------------- usage
STEP="no --orch and no CREW_ORCH exits 2 with one line"
expect_exit 2 python3 "$ORCH_PY" init
one_line_err
pass

STEP="a bad name exits 2"
expect_exit 2 python3 "$ORCH_PY" --orch "Bad Name" init
one_line_err
pass

# ---------------------------------------------------------------- AC1
STEP="AC1 init makes the four paths"
expect_exit 0 orch init
D="$CREW_RECORD_ROOT/orchestrators/fleet"
[ -f "$D/orchestrator.json" ] || fail "no orchestrator.json"
[ -f "$D/plan.md" ] || fail "no plan.md"
[ -d "$D/told" ] || fail "no told/"
[ -f "$D/orchestrator.lock" ] || fail "no lock file"
pass

STEP="AC1 a second init exits non-zero and changes nothing"
before=$(cd "$D" && ls -la; cat orchestrator.json)
python3 "$ORCH_PY" --orch fleet init >/dev/null 2>&1 && fail "second init exited 0"
after=$(cd "$D" && ls -la; cat orchestrator.json)
[ "$before" = "$after" ] || fail "second init changed the record"
pass

STEP="init writes closed_at null"
jcheck '"closed_at" in s and s["closed_at"] is None'
pass

STEP="CREW_ORCH stands in for --orch"
CREW_ORCH=fleet python3 "$ORCH_PY" show >/dev/null || fail "show with CREW_ORCH failed"
pass

# ---------------------------------------------------------------- AC3
STEP="AC3 two items read back with n 1 and 2"
expect_exit 2 orch group add add --title "Reserved"
expect_exit 0 orch group add dialogs --title "Dialog migration" --repo owner/dash --ticket T-1 --ticket-url https://tickets.example/T-1
expect_exit 0 orch item add editor --title "Editor dialog" --repo owner/dash --group dialogs --ticket T-2 --ticket-url https://tickets.example/T-2
expect_exit 0 orch item add settings --title "Settings dialog" --repo owner/dash --group dialogs
jcheck 's["items"]["editor"]["n"] == 1 and s["items"]["settings"]["n"] == 2'
jcheck 's["items"]["editor"]["stage"] == "queued" and s["items"]["editor"]["group"] == "dialogs"'
python3 "$ORCH_PY" --orch fleet show editor >"$TMP/one.json" || fail "show <item> failed"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); sys.exit(0 if d["id"]=="editor" and d["ticket"]["url"]=="https://tickets.example/T-2" else 1)' "$TMP/one.json" || fail "show editor is wrong"
pass

STEP="AC3 set of a field outside the list exits 2"
expect_exit 2 orch item editor set stage '"build"'
one_line_err
expect_exit 2 orch item add add --title x --repo owner/dash
expect_exit 2 orch item add editor --title dup --repo owner/dash
expect_exit 0 orch item editor set title '"Editor dialog v2"'
expect_exit 0 orch item editor set launch '{"session_name": "s-editor", "terminal": "tmux"}'
expect_exit 0 orch item editor set launch.tab '"tmux:%3"'
jcheck 's["items"]["editor"]["title"] == "Editor dialog v2"'
jcheck 's["items"]["editor"]["launch"] == {"session_name": "s-editor", "terminal": "tmux", "tab": "tmux:%3"}'
pass

STEP="item set launch takes session_id, as a whole object and as a dotted key"
expect_exit 0 orch item settings set launch '{"session_name": "s-settings", "session_id": "11111111-2222-4333-8444-555555555555"}'
jcheck 's["items"]["settings"]["launch"]["session_id"] == "11111111-2222-4333-8444-555555555555"'
expect_exit 0 orch item settings set launch.session_id '"resumed-1"'
jcheck 's["items"]["settings"]["launch"] == {"session_name": "s-settings", "session_id": "resumed-1"}'
pass

# ---------------------------------------------------------------- AC4
STEP="AC4 an unknown stage exits 2"
expect_exit 2 orch stage editor coding
one_line_err
pass

STEP="AC4 a valid stage shows on the board row"
expect_exit 0 orch stage settings build --detail 2/3 --doing "ic-2 runs the suite"
orch board >"$TMP/board" || fail "board failed"
grep -E '^ *2 +settings .*build 2/3' "$TMP/board" >/dev/null || fail "no build 2/3 on the settings row: $(cat "$TMP/board")"
grep -E '^ *2 +settings .*●●◐○○' "$TMP/board" >/dev/null || fail "no stage marks on the settings row"
expect_exit 0 orch doing settings "ic-2 reads the diff"
jcheck 's["items"]["settings"]["doing"] == "ic-2 reads the diff" and s["items"]["settings"]["doing_at"]'
pass

# ---------------------------------------------------------------- AC5
STEP="AC5 group order: b waits on a until a is merged"
expect_exit 0 orch item add loner --title "Single fix" --repo owner/other
expect_exit 2 orch group dialogs order editor,loner
expect_exit 2 orch group dialogs order editor,nosuch
expect_exit 0 orch group dialogs order editor,settings
expect_exit 0 orch group dialogs owner video-dialog editor
jcheck 's["groups"]["dialogs"]["order"] == ["editor", "settings"] and s["groups"]["dialogs"]["owners"] == {"video-dialog": "editor"}'
jcheck 's["items"]["settings"]["waits_on"] == ["editor"] and s["items"]["editor"]["waits_on"] == []'
orch board >"$TMP/board"
grep -E '^ *2 +settings .*editor' "$TMP/board" >/dev/null || fail "settings row does not name editor: $(cat "$TMP/board")"
expect_exit 0 orch stage editor merged
jcheck 's["items"]["settings"]["waits_on"] == []'
orch board >"$TMP/board"
grep -E '^ *2 +settings .*(after|waits).*editor' "$TMP/board" >/dev/null && fail "settings still waits on editor after merged"
expect_exit 0 orch stage editor review
pass

# ---------------------------------------------------------------- AC6
STEP="AC6 inbox entries of each kind and two open questions"
d1=$(orch inbox add decision --item editor "Two parts open the video dialog. Who owns it?" --recommend "editor") || fail "inbox add decision"
q1=$(orch ask settings "Does all rows include archived?") || fail "ask 1"
q2=$(orch ask settings "Keep the old export?") || fail "ask 2"
i1=$(orch inbox add idea "No test asserts button order. New ticket?") || fail "inbox add idea"
n1=$(orch inbox add notice --item loner "CI is slow today") || fail "inbox add notice"
[ "$d1 $q1 $q2 $i1 $n1" = "d1 q1 q2 i1 n1" ] || fail "ids are '$d1 $q1 $q2 $i1 $n1'"
expect_exit 0 orch answer q1 "Yes, include archived rows."
expect_exit 0 orch route q2 principal
expect_exit 0 orch dismiss n1 --reason "not needed"
jcheck '[(e["id"], e["state"], e["for"]) for e in s["inbox"] if e["kind"] == "question"] == [("q1", "answered", "orchestrator"), ("q2", "open", "principal")]'
jcheck '[e for e in s["inbox"] if e["id"] == "q1"][0]["answer"] == "Yes, include archived rows."'
jcheck '[e for e in s["inbox"] if e["id"] == "q2"][0]["routed_at"] is not None'
pass

STEP="AC6 answering a closed entry exits 2"
expect_exit 2 orch answer q1 "again"
one_line_err
expect_exit 2 orch dismiss n1
expect_exit 2 orch route q1 principal
expect_exit 2 orch inbox add worry "x"
pass

# ---------------------------------------------------------------- AC2
STEP="AC2 two concurrent asks both land"
orch ask loner "first concurrent" >"$TMP/c1" &
p1=$!
orch ask loner "second concurrent" >"$TMP/c2" &
p2=$!
wait $p1 || fail "concurrent ask 1 failed"
wait $p2 || fail "concurrent ask 2 failed"
[ "$(sort "$TMP/c1" "$TMP/c2" | tr '\n' ' ')" = "q3 q4 " ] || fail "concurrent ids: $(cat "$TMP/c1" "$TMP/c2")"
jcheck 'sorted(e["text"] for e in s["inbox"] if e["item"] == "loner" and e["kind"] == "question") == ["first concurrent", "second concurrent"]'
pass

# ---------------------------------------------------------------- AC7
STEP="AC7 refresh gets can merge with a cancelled and a passing run"
expect_exit 2 orch item loner pr notanumber
expect_exit 0 orch item loner pr 77
jcheck 's["items"]["loner"]["pr"] == {"number": 77, "url": "https://github.com/owner/other/pull/77"}'
expect_exit 0 orch item editor pr https://github.com/owner/dash/pull/893
jcheck 's["items"]["editor"]["pr"]["number"] == 893'
cat >"$TMP/gh/pr-77.json" <<'EOF'
{"state": "OPEN", "isDraft": false, "reviewDecision": "APPROVED", "mergeStateStatus": "CLEAN",
 "statusCheckRollup": [
  {"__typename": "CheckRun", "name": "test", "workflowName": "ci", "status": "COMPLETED", "conclusion": "SUCCESS", "startedAt": "2026-11-16T10:00:00Z"},
  {"__typename": "CheckRun", "name": "test", "workflowName": "ci", "status": "COMPLETED", "conclusion": "CANCELLED", "startedAt": "2026-11-16T10:05:00Z"},
  {"__typename": "CheckRun", "name": "lint", "workflowName": "ci", "status": "COMPLETED", "conclusion": "SKIPPED", "startedAt": "2026-11-16T10:00:00Z"}
 ]}
EOF
cat >"$TMP/gh/queue-77.json" <<'EOF'
{"data": {"repository": {"pullRequest": {"isInMergeQueue": false, "mergeQueueEntry": null}}}}
EOF
expect_exit 0 orch stage loner pr
expect_exit 0 orch refresh loner
jcheck 's["items"]["loner"]["merge"] == "can merge"'
jcheck 's["items"]["loner"]["github"]["checks"] == "pass" and s["items"]["loner"]["github"]["review_decision"] == "APPROVED" and s["items"]["loner"]["github"]["refreshed_at"]'
grep -- '--repo owner/other' "$TMP/gh/calls.log" >/dev/null || fail "gh pr view did not name --repo"
pass

STEP="AC7 a failed gh call keeps the last values and does not fail"
mv "$TMP/gh/pr-77.json" "$TMP/gh/pr-77.off"
expect_exit 0 orch refresh
[ "$(wc -l <"$TMP/err" | tr -d ' ')" -ge 1 ] || fail "no line for the failed gh call"
jcheck 's["items"]["loner"]["merge"] == "can merge" and s["items"]["loner"]["github"]["checks"] == "pass"'
jcheck '"gh pr view 77" in (s["items"]["loner"]["github"]["error"] or "")'
mv "$TMP/gh/pr-77.off" "$TMP/gh/pr-77.json"
expect_exit 0 orch refresh loner
jcheck 's["items"]["loner"]["github"]["error"] is None'
pass

STEP="a new PR number clears the github values of the old PR"
expect_exit 0 orch item loner pr 78
jcheck 's["items"]["loner"]["github"] is None and s["items"]["loner"]["pr"]["number"] == 78'
expect_exit 0 orch item loner pr 78
jcheck 's["items"]["loner"]["github"] is None'
expect_exit 0 orch item loner pr 77
expect_exit 0 orch refresh loner
jcheck 's["items"]["loner"]["merge"] == "can merge"'
expect_exit 0 orch item loner pr 77
jcheck 's["items"]["loner"]["github"] is not None'
pass

STEP="AC7 a failed check is ci failing"
cat >"$TMP/gh/pr-893.json" <<'EOF'
{"state": "OPEN", "isDraft": false, "reviewDecision": "APPROVED", "mergeStateStatus": "BLOCKED",
 "statusCheckRollup": [
  {"__typename": "CheckRun", "name": "test", "workflowName": "ci", "status": "COMPLETED", "conclusion": "FAILURE", "startedAt": "2026-11-16T10:00:00Z"}
 ]}
EOF
cat >"$TMP/gh/queue-893.json" <<'EOF'
{"data": {"repository": {"pullRequest": {"isInMergeQueue": false, "mergeQueueEntry": null}}}}
EOF
expect_exit 0 orch refresh editor
jcheck 's["items"]["editor"]["github"]["checks"] == "fail" and s["items"]["editor"]["github"]["failed_checks"] == ["test"]'
expect_exit 0 orch stage editor pr
jcheck 's["items"]["editor"]["merge"] == "ci failing"'
cat >"$TMP/gh/queue-893.json" <<'EOF'
{"data": {"repository": {"pullRequest": {"isInMergeQueue": true, "mergeQueueEntry": {"position": 3}}}}}
EOF
expect_exit 0 orch refresh editor
jcheck 's["items"]["editor"]["merge"] == "in queue 3" and s["items"]["editor"]["github"]["queue_position"] == 3'
expect_exit 0 orch stage editor review
pass

# ---------------------------------------------------------------- AC8
STEP="AC8 plan changes and told files"
printf '# Plan\n\nv2\n' >"$TMP/plan-v2.md"
expect_exit 0 orch plan change "split settings in two" --reason "two owners" --file "$TMP/plan-v2.md"
expect_exit 0 orch plan change "move loner first" --reason "it blocks a release"
expect_exit 2 orch plan change "no reason"
jcheck '[(c["change"], c["reason"]) for c in s["plan_changes"]] == [("split settings in two", "two owners"), ("move loner first", "it blocks a release")]'
cmp -s "$TMP/plan-v2.md" "$D/plan.md" || fail "plan.md is not the copied file"
printf 'Build the editor.\n' >"$TMP/msg1.md"
printf 'Rebase first.\n' >"$TMP/msg2.md"
expect_exit 0 orch told editor --file "$TMP/msg1.md"
expect_exit 0 orch told editor --file "$TMP/msg2.md"
cmp -s "$TMP/msg1.md" "$D/told/editor-1.md" || fail "no told/editor-1.md"
cmp -s "$TMP/msg2.md" "$D/told/editor-2.md" || fail "no told/editor-2.md"
jcheck '[t["path"] for t in s["items"]["editor"]["told"]] == ["told/editor-1.md", "told/editor-2.md"]'
pass

# ---------------------------------------------------------------- AC9 / C10
STEP="AC9 no crew-usage.py: no Plan block"
orch board >"$TMP/board"
grep -E '^ *Plan ' "$TMP/board" >/dev/null && fail "Plan block with no crew-usage.py"
expect_exit 2 orch pace set '{"mode": "fast"}'
expect_exit 0 orch pace set '{"mode": "slowed", "slots": {"busy": 2}}'
jcheck 's["pace"] == {"mode": "slowed", "slots": {"busy": 2, "max": 3}, "limit_pct": 95}'
orch board >"$TMP/board"
grep -E 'SLOWED: 2 of 3 slots' "$TMP/board" >/dev/null || fail "no SLOWED line with no Plan block"
pass

STEP="AC9 a stub crew-usage.py beside a copy of the script: the 5h line"
mkdir -p "$TMP/copy"
cp "$ORCH_PY" "$TMP/copy/crew-orch.py"
reset=$(( $(date +%s) + 3600 ))
cat >"$TMP/copy/crew-usage.py" <<EOF
import json, sys
assert sys.argv[1:] == ["show", "--json"], sys.argv
print(json.dumps({"five_hour": {"used_pct": 68, "resets_at": $reset, "full_at": $reset},
                  "seven_day": {"used_pct": 31, "resets_at": $(( reset + 3 * 86400 ))}}))
EOF
python3 "$TMP/copy/crew-orch.py" --orch fleet board >"$TMP/board" || fail "board from the copy failed"
grep -E '^ *Plan +5h .*68%.*SLOWED: 2 of 3 slots' "$TMP/board" >/dev/null || fail "no 5h line: $(cat "$TMP/board")"
grep -E '7d .*31%' "$TMP/board" >/dev/null || fail "no 7d line"
pass

STEP="C10 a crew-usage.py that fails: no Plan block and no error"
printf 'import sys\nsys.exit(3)\n' >"$TMP/copy/crew-usage.py"
python3 "$TMP/copy/crew-orch.py" --orch fleet board >"$TMP/board" || fail "board failed with a failing crew-usage.py"
grep -E '^ *Plan ' "$TMP/board" >/dev/null && fail "Plan block from a failing crew-usage.py"
printf 'print("not json")\n' >"$TMP/copy/crew-usage.py"
python3 "$TMP/copy/crew-orch.py" --orch fleet board >"$TMP/board" || fail "board failed with bad crew-usage.py output"
grep -E '^ *Plan ' "$TMP/board" >/dev/null && fail "Plan block from bad output"
expect_exit 0 orch pace set '{"mode": "normal"}'
pass

# ---------------------------------------------------------------- AC10
STEP="AC10 board order, merge order and --urls"
expect_exit 0 orch item add shipped1 --title "Old work" --repo owner/other
expect_exit 0 orch stage shipped1 shipped
orch board >"$TMP/board"
needs=$(grep -n 'Needs you' "$TMP/board" | head -1 | cut -d: -f1)
group=$(grep -n 'Dialog migration' "$TMP/board" | head -1 | cut -d: -f1)
single=$(grep -n 'Single items' "$TMP/board" | head -1 | cut -d: -f1)
done_=$(grep -n -E '^ *Done +1' "$TMP/board" | head -1 | cut -d: -f1)
ed=$(grep -n -E '^ *1 +editor ' "$TMP/board" | head -1 | cut -d: -f1)
se=$(grep -n -E '^ *2 +settings ' "$TMP/board" | head -1 | cut -d: -f1)
lo=$(grep -n -E '^ *3 +loner ' "$TMP/board" | head -1 | cut -d: -f1)
[ -n "$needs" ] && [ -n "$group" ] && [ -n "$single" ] && [ -n "$done_" ] && [ -n "$ed" ] && [ -n "$se" ] && [ -n "$lo" ] || fail "a section or row is missing: $(cat "$TMP/board")"
[ "$needs" -lt "$group" ] && [ "$group" -lt "$ed" ] && [ "$ed" -lt "$se" ] && [ "$se" -lt "$single" ] && [ "$single" -lt "$lo" ] && [ "$lo" -lt "$done_" ] || fail "sections are out of order: $(cat "$TMP/board")"
grep -E 'Needs you +3' "$TMP/board" >/dev/null || fail "Needs you count is not 3 (d1, q2, i1)"
grep -E 'Recommended: editor' "$TMP/board" >/dev/null || fail "no Recommended line"
grep -E 'Dialog migration .*T-1.*owner/dash.*0 of 2 merged' "$TMP/board" >/dev/null || fail "group heading is wrong"
grep -E '^ *3 +loner .*can merge.*#77' "$TMP/board" >/dev/null || fail "loner row is wrong"
grep -F "$(printf '\033]8')" "$TMP/board" >/dev/null && fail "OSC 8 link with no tty"
orch board --urls >"$TMP/board"
grep -E '^ *Links' "$TMP/board" >/dev/null || fail "no Links list with --urls"
grep -F 'https://github.com/owner/other/pull/77' "$TMP/board" >/dev/null || fail "no PR URL in --urls"
grep -F 'https://tickets.example/T-1' "$TMP/board" >/dev/null || fail "no group ticket URL in --urls"
grep -F 'https://tickets.example/T-2' "$TMP/board" >/dev/null && fail "a grouped item's ticket URL is in --urls"
expect_exit 2 orch board --nope
pass

# ---------------------------------------------------------------- C6
STEP="C6 a new show process returns what the test wrote"
python3 "$ORCH_PY" --orch fleet show >"$TMP/final.json" || fail "final show failed"
python3 - "$TMP/final.json" <<'PY' || fail "final show differs from what the test wrote"
import json, sys
s = json.load(open(sys.argv[1]))
want_items = {
    "editor": dict(n=1, title="Editor dialog v2", repo="owner/dash", group="dialogs", stage="review",
                   ticket={"id": "T-2", "url": "https://tickets.example/T-2"},
                   pr={"number": 893, "url": "https://github.com/owner/dash/pull/893"}),
    "settings": dict(n=2, title="Settings dialog", repo="owner/dash", group="dialogs", stage="build",
                     detail="2/3", doing="ic-2 reads the diff", ticket=None, pr=None),
    "loner": dict(n=3, title="Single fix", repo="owner/other", group=None, stage="pr", merge="can merge",
                  pr={"number": 77, "url": "https://github.com/owner/other/pull/77"}),
    "shipped1": dict(n=4, stage="shipped", merge="merged"),
}
for iid, fields in want_items.items():
    item = s["items"][iid]
    for k, v in fields.items():
        assert item[k] == v, (iid, k, item[k], v)
assert set(s["items"]) == set(want_items), s["items"].keys()
g = s["groups"]["dialogs"]
assert g["order"] == ["editor", "settings"] and g["owners"] == {"video-dialog": "editor"}
assert g["ticket"] == {"id": "T-1", "url": "https://tickets.example/T-1"} and g["repo"] == "owner/dash"
states = {e["id"]: (e["kind"], e["for"], e["state"], e["item"]) for e in s["inbox"]}
assert states == {
    "d1": ("decision", "principal", "open", "editor"),
    "q1": ("question", "orchestrator", "answered", "settings"),
    "q2": ("question", "principal", "open", "settings"),
    "i1": ("idea", "principal", "open", None),
    "n1": ("notice", "principal", "dismissed", "loner"),
    "q3": ("question", "orchestrator", "open", "loner"),
    "q4": ("question", "orchestrator", "open", "loner"),
}, states
assert [e for e in s["inbox"] if e["id"] == "n1"][0]["answer"] == "not needed"
assert [(c["change"], c["reason"]) for c in s["plan_changes"]] == [
    ("split settings in two", "two owners"), ("move loner first", "it blocks a release")]
assert s["counters"] == {"item": 4, "decision": 1, "question": 4, "idea": 1, "notice": 1}, s["counters"]
assert s["version"] == 1 and s["name"] == "fleet"
PY
pass

# ---------------------------------------------------------------- AC12
STEP="AC12 crew-stats.py reports no run for the orchestrator record"
mkdir -p "$D/decoy"
echo '{"run": {"run_state": "complete"}}' >"$D/decoy/state.json"
echo 'decoy' >"$D/decoy/charter.md"
python3 "$STATS_PY" --record-root "$CREW_RECORD_ROOT" >"$TMP/stats" 2>&1
grep -i -F 'no records under' "$TMP/stats" >/dev/null || fail "crew-stats.py read the orchestrator record: $(head -5 "$TMP/stats")"
pass

# ---------------------------------------------------------------- patch round
# A second record, so the C6 check above stays exact.
orch2() { python3 "$ORCH_PY" --orch patch "$@"; }
jcheck2() {
  python3 "$ORCH_PY" --orch patch show >"$TMP/show2.json" || fail "show failed"
  python3 - "$TMP/show2.json" "$1" <<'PY2' || fail "check is false: $1"
import json, sys
s = json.load(open(sys.argv[1]))
sys.exit(0 if eval(sys.argv[2]) else 1)
PY2
}
expect_exit 0 orch2 init

STEP="status word: a PR item at review or later shows the merge value"
expect_exit 0 orch2 item add withpr --title "With PR" --repo owner/pat
expect_exit 0 orch2 item add nopr --title "No PR" --repo owner/pat
expect_exit 0 orch2 item withpr pr 501
cat >"$TMP/gh/pr-501.json" <<'EOF'
{"state": "OPEN", "isDraft": false, "reviewDecision": "APPROVED", "mergeStateStatus": "CLEAN",
 "statusCheckRollup": [{"__typename": "CheckRun", "name": "test", "status": "COMPLETED", "conclusion": "SUCCESS", "startedAt": "2026-11-16T10:00:00Z"}]}
EOF
cat >"$TMP/gh/queue-501.json" <<'EOF'
{"data": {"repository": {"pullRequest": {"isInMergeQueue": false, "mergeQueueEntry": null}}}}
EOF
expect_exit 0 orch2 refresh withpr
expect_exit 0 orch2 stage withpr review
expect_exit 0 orch2 stage nopr review
orch2 board >"$TMP/board2" || fail "board failed"
grep -E '^ *1 +withpr .*●●●◐○ +can merge +#501' "$TMP/board2" >/dev/null || fail "withpr at review does not show can merge: $(cat "$TMP/board2")"
grep -E '^ *2 +nopr .*●●●◐○ +review *$' "$TMP/board2" >/dev/null || fail "nopr at review does not show review: $(cat "$TMP/board2")"
expect_exit 0 orch2 stage withpr build
orch2 board >"$TMP/board2"
grep -E '^ *1 +withpr .*●●◐○○ +build ' "$TMP/board2" >/dev/null || fail "withpr at build does not show build"
pass

STEP="status word: a PR item with no refresh yet shows the stage word"
expect_exit 0 orch2 item add fresh --title "Fresh PR" --repo owner/pat
expect_exit 0 orch2 item fresh pr 600
expect_exit 0 orch2 stage fresh review
jcheck2 's["items"]["fresh"]["github"] is None'
orch2 board >"$TMP/board2" || fail "board failed"
grep -E '^ *[0-9]+ +fresh .*●●●◐○ +review +#600' "$TMP/board2" >/dev/null || fail "fresh at review does not show review: $(cat "$TMP/board2")"
expect_exit 0 orch2 stage fresh pr
orch2 board >"$TMP/board2"
grep -E '^ *[0-9]+ +fresh .*●●●●◐ +pr +#600' "$TMP/board2" >/dev/null || fail "fresh at pr does not show pr: $(cat "$TMP/board2")"
pass

STEP="item pr: a URL of another repo exits 2 and writes nothing"
before=$(cat "$CREW_RECORD_ROOT/orchestrators/patch/orchestrator.json")
expect_exit 2 orch2 item nopr pr https://github.com/owner/elsewhere/pull/9
one_line_err
after=$(cat "$CREW_RECORD_ROOT/orchestrators/patch/orchestrator.json")
[ "$before" = "$after" ] || fail "a refused pr URL changed the record"
expect_exit 0 orch2 item nopr pr https://github.com/owner/pat/pull/9
before=$(cat "$CREW_RECORD_ROOT/orchestrators/patch/orchestrator.json")
expect_exit 2 orch2 item nopr set repo '"owner/elsewhere"'
one_line_err
after=$(cat "$CREW_RECORD_ROOT/orchestrators/patch/orchestrator.json")
[ "$before" = "$after" ] || fail "a refused repo change wrote the record"
pass

STEP="set group moves the item out of the old group's order and owners"
expect_exit 0 orch2 group add g1 --title "Group one"
expect_exit 0 orch2 group add g2 --title "Group two"
expect_exit 0 orch2 item add mover --title "Mover" --repo owner/pat --group g1
expect_exit 0 orch2 item add stayer --title "Stayer" --repo owner/pat --group g1
expect_exit 0 orch2 group g1 order mover,stayer
expect_exit 0 orch2 group g1 owner shared-file mover
expect_exit 0 orch2 group g1 owner other-file stayer
expect_exit 2 orch2 item mover set group '"nosuch"'
expect_exit 0 orch2 item mover set group '"g2"'
jcheck2 's["items"]["mover"]["group"] == "g2"'
jcheck2 's["groups"]["g1"]["order"] == ["stayer"] and s["groups"]["g1"]["owners"] == {"other-file": "stayer"}'
jcheck2 's["items"]["stayer"]["waits_on"] == []'
pass

STEP="the board removes control characters and escape sequences"
expect_exit 0 orch2 group add dirty --title $'Dirty\e[31mRed\e[0m\atitle' --repo owner/pat --ticket $'T\e]8;;https://evil.example\e\\-9' --ticket-url $'https://tickets.example/\e]8;;https://evil.example\a9\x01'
expect_exit 0 orch2 item add dirt --title "Dirt" --repo owner/pat --group dirty
c1=$(printf '\302\233')  # U+009B, the one-character CSI, in UTF-8
expect_exit 0 orch2 doing dirt $'runs\e[2J the\x7f suite\x01'"$c1"$' now\ttab\nline'
expect_exit 2 orch2 doing dirt $'raw byte \x9b is not UTF-8'
one_line_err
expect_exit 0 orch2 inbox add notice --item dirt $'bell\a here\e[1m bold' --recommend $'rec\e[0m ok'
orch2 board --urls >"$TMP/board2" || fail "board failed"
python3 - "$TMP/board2" <<'PY2' || fail "the board has a control character: $(cat -v "$TMP/board2")"
import re, sys
text = open(sys.argv[1], encoding="utf-8").read()
bad = re.findall(r"[\x00-\x09\x0b-\x1f\x7f-\x9f]", text)
assert not bad, bad
for want in ("DirtyRedtitle", "T-9", "https://tickets.example/9", "runs the suite now tab line", "bell here bold", "Recommended: rec ok"):
    assert want in text, want
PY2
python3 - "$ORCH_PY" <<'PY2' || fail "Links.make on a tty does not wrap the cleaned text and URL"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("crew_orch", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
got = m.Links(True).make("#1\x07", "https://x.example/\x1b]8;;https://evil.example\x07y")
assert got == "\x1b]8;;https://x.example/y\x1b\\#1\x1b]8;;\x1b\\", repr(got)
PY2
pass

STEP="checks: a run with no startedAt is the latest and reads pending"
python3 - "$ORCH_PY" <<'PY2' || fail "a queued re-run does not read pending"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("crew_orch", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)
done = {"name": "test", "workflowName": "ci", "status": "COMPLETED", "conclusion": "FAILURE", "startedAt": "2026-11-16T10:00:00Z"}
queued = {"name": "test", "workflowName": "ci", "status": "QUEUED", "conclusion": None}
# gh prints an unset startedAt as the zero time.
zero = {"name": "test", "workflowName": "ci", "status": "QUEUED", "conclusion": "", "startedAt": "0001-01-01T00:00:00Z"}
for rollup in ([done, queued], [queued, done], [done, zero], [zero, done]):
    got = m.check_summary(rollup)
    assert got == ("pending", []), (rollup, got)
PY2
pass

STEP="every merge value, and the order where two rules match"
python3 - "$ORCH_PY" <<'PY2' || fail "a merge value is wrong"
import importlib.util, sys
spec = importlib.util.spec_from_file_location("crew_orch", sys.argv[1])
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

def item(stage="pr", pr=True, waits=(), **gh):
    base = {"state": "OPEN", "is_draft": False, "review_decision": "APPROVED", "merge_state": "CLEAN",
            "checks": "pass", "failed_checks": [], "in_queue": False, "queue_position": None}
    base.update(gh)
    return {"id": "x", "stage": stage, "pr": {"number": 1, "url": "u"} if pr else None,
            "github": base if pr else None, "waits_on": list(waits)}

cases = [
    # (expected, item, what it proves)
    ("merged", item(state="MERGED"), "PR merged"),
    ("merged", item(stage="shipped", pr=False), "merged before no PR"),
    ("no PR", item(pr=False), "no PR"),
    ("closed", item(state="CLOSED", in_queue=True), "closed before in queue"),
    ("closed", item(stage="closed"), "stage closed"),
    ("in queue 2", item(in_queue=True, queue_position=2), "in queue with a position"),
    ("in queue", item(in_queue=True), "in queue before can merge"),
    ("can merge", item(), "can merge"),
    ("can merge", item(checks="none"), "no checks pass"),
    ("can merge", item(review_decision=None), "no review required: empty decision, CLEAN"),
    ("needs review", item(review_decision="REVIEW_REQUIRED"), "needs review, REVIEW_REQUIRED, CLEAN"),
    ("needs review", item(review_decision="REVIEW_REQUIRED", merge_state="BLOCKED"), "needs review, REVIEW_REQUIRED, BLOCKED"),
    ("needs review", item(review_decision=None, merge_state="BLOCKED"), "needs review, empty decision, BLOCKED"),
    ("needs review", item(review_decision="REVIEW_REQUIRED", waits=["a"]), "needs review before waits on"),
    ("waits on a", item(review_decision=None, waits=["a"]), "empty decision, CLEAN, waits: waits on"),
    ("draft", item(review_decision=None, is_draft=True), "empty decision, draft: draft"),
    ("waits on a, b", item(waits=["a", "b"]), "waits on stops can merge"),
    ("waits on a", item(waits=["a"], merge_state="DIRTY"), "waits on before conflict"),
    ("conflict", item(merge_state="DIRTY"), "conflict, DIRTY"),
    ("conflict", item(merge_state="BEHIND", checks="fail"), "conflict before ci failing"),
    ("ci failing", item(merge_state="BLOCKED", checks="fail", is_draft=True), "ci failing before draft"),
    ("ci pending", item(merge_state="BLOCKED", checks="pending", is_draft=True), "ci pending before draft"),
    ("draft", item(is_draft=True, review_decision="CHANGES_REQUESTED"), "draft before changes requested"),
    ("changes requested", item(review_decision="CHANGES_REQUESTED", merge_state="BLOCKED"), "changes requested"),
    ("blocked", item(merge_state="BLOCKED"), "approved but BLOCKED"),
    ("blocked", item(merge_state="UNSTABLE"), "an unknown merge state"),
]
bad = [(want, m.merge_value(it), why) for want, it, why in cases if m.merge_value(it) != want]
assert not bad, bad
PY2
pass

# ---------------------------------------------------------------- board --json (#155)
# The repo root, for the fixtures and for the script on the main branch.
REPO=$(cd "$HERE/../../.." && pwd)
FIX="$REPO/tests/fixtures"
# The fixed commit that the R2 step compares with: the main branch before
# #155. Never a moving ref: once this change is on main, a moving ref holds
# this same script, and the R2 step then fails.
MAIN_REF=${CREW_ORCH_MAIN_REF:-55e7e89}

# check_json <file>: the file is one board JSON object, each field of the
# type that orchestrator-record.md "The board" gives.
cat >"$TMP/check_json.py" <<'PY'
import json, sys

d = json.load(open(sys.argv[1], encoding="utf-8"))


def is_int(v):
    return isinstance(v, int) and not isinstance(v, bool)


def str_or_none(v):
    return v is None or isinstance(v, str)


def link(v):
    return v is None or (isinstance(v, dict) and isinstance(v.get("id"), str) and str_or_none(v.get("url")))


assert isinstance(d, dict), "not an object"
assert d["version"] == 1, d["version"]
assert isinstance(d["orch"], str)
plan = d["plan"]
assert plan is None or (isinstance(plan, dict) and isinstance(plan["windows"], list) and isinstance(plan["word"], str)), plan
for w in (plan or {}).get("windows", []):
    assert w["key"] in ("five_hour", "seven_day") and w["label"] in ("5h", "7d"), w
    assert is_int(w["used_pct"]), w
    assert len(w["meter"]) == 10 and set(w["meter"]) <= {"█", "░"}, w
    assert isinstance(w["resets"], str) and isinstance(w["full_at"], str), w
ny = d["needs_you"]
assert is_int(ny["count"]) and isinstance(ny["entries"], list) and ny["count"] == len(ny["entries"]), ny
for e in ny["entries"]:
    for k in ("id", "kind", "age", "item", "text"):
        assert isinstance(e[k], str), (k, e)
    assert str_or_none(e["item_id"]) and str_or_none(e["recommend"]), e
assert isinstance(d["sections"], list)
for s in d["sections"]:
    assert s["kind"] in ("group", "single"), s
    assert isinstance(s["title"], str) and isinstance(s["rows"], list), s
    assert link(s["ticket"]) and str_or_none(s["repo"]) and str_or_none(s["id"]), s
    if s["kind"] == "single":
        assert s["id"] is None and s["title"] == "Single items" and s["ticket"] is None and s["repo"] is None, s
        assert s["merged"] is None and s["total"] is None, s
    else:
        assert isinstance(s["id"], str) and is_int(s["merged"]) and is_int(s["total"]), s
    for r in s["rows"]:
        assert is_int(r["n"]) and isinstance(r["id"], str), r
        assert len(r["marks"]) == 5 and set(r["marks"]) <= {"●", "◐", "○"}, r
        assert isinstance(r["status"], str) and isinstance(r["text"], str) and isinstance(r["age"], str), r
        pr = r["pr"]
        assert pr is None or (is_int(pr["number"]) and pr["label"] == f"#{pr['number']}" and isinstance(pr["url"], str)), r
        assert link(r["ticket"]) and str_or_none(r["launch_tab"]), r
        assert isinstance(r["subagent"], bool), r
        if s["kind"] == "group":
            assert r["ticket"] is None, ("a grouped row shows a ticket", r)
assert is_int(d["done"]), d["done"]
assert d["legend"] == "spec → split → build → review → PR", d["legend"]
assert "\x1b" not in json.dumps(d, ensure_ascii=False), "an escape sequence in the JSON"
PY

# same_board <json> <text>: the text view shows the same sections, rows and
# values as the JSON view, in the same order.
cat >"$TMP/same_board.py" <<'PY'
import json, re, sys

d = json.load(open(sys.argv[1], encoding="utf-8"))
lines = open(sys.argv[2], encoding="utf-8").read().split("\n")
at = 0


def find(pred, what):
    global at
    for i in range(at, len(lines)):
        if pred(lines[i]):
            at = i + 1
            return lines[i]
    raise AssertionError(f"not found after line {at}: {what}")


def in_order(line, cells, what):
    pos = 0
    for cell in cells:
        if cell == "":
            continue
        got = line.find(cell, pos)
        assert got >= 0, (what, cell, line)
        pos = got + len(cell)


if d["plan"]:
    for w in d["plan"]["windows"]:
        line = find(lambda l, w=w: f"{w['label']} {w['meter']}" in l, w["label"])
        in_order(line, [w["meter"], f"{w['used_pct']}%", w["resets"], w["full_at"]], w["label"])
    if d["plan"]["word"]:
        assert any(d["plan"]["word"] in l for l in lines), "no pace word"
find(lambda l: l.strip() == f"Needs you  {d['needs_you']['count']}", "Needs you")
for e in d["needs_you"]["entries"]:
    line = find(lambda l, e=e: l.startswith(f"  {e['id']} "), e["id"])
    in_order(line, [e["id"], e["kind"], e["age"], e["item"], e["text"]], e["id"])
    if e["recommend"]:
        line = find(lambda l: "Recommended:" in l, "Recommended")
        assert line.strip() == f"Recommended: {e['recommend']}", line
for s in d["sections"]:
    head = [s["title"]] + ([s["ticket"]["id"]] if s["ticket"] else []) + ([s["repo"]] if s["repo"] else [])
    if s["kind"] == "group":
        head.append(f"{s['merged']} of {s['total']} merged")
    line = find(lambda l, t=s["title"]: l.startswith(f" {t}"), s["title"])
    in_order(line, head, s["title"])
    for r in s["rows"]:
        line = find(lambda l, r=r: re.match(rf"^ +{r['n']} {re.escape(r['id'])}( |$)", l), r["id"])
        cells = [str(r["n"]), r["id"], r["marks"], r["status"], r["pr"]["label"] if r["pr"] else "",
                 r["ticket"]["id"] if r["ticket"] else "", r["text"], r["age"]]
        in_order(line, cells, r["id"])
find(lambda l: l.strip().startswith(f"Done  {d['done']} ") and d["legend"] in l, "Done")
PY

STEP="R1 board --json prints one board object and writes nothing"
snap() { (cd "$CREW_RECORD_ROOT" && find . | LC_ALL=C sort | while read -r f; do printf '%s ' "$f"; [ -f "$f" ] && cksum <"$f" || echo dir; done); }
before=$(snap)
pin=$(date +%s)
CREW_ORCH_NOW=$pin orch board --json >"$TMP/bj" 2>"$TMP/err" || fail "board --json failed: $(cat "$TMP/err")"
after=$(snap)
[ "$before" = "$after" ] || fail "board --json changed the record files"
[ ! -s "$TMP/err" ] || fail "board --json wrote to stderr: $(cat "$TMP/err")"
python3 -c 'import json,sys; json.load(sys.stdin)' <"$TMP/bj" || fail "board --json is not one JSON value"
python3 "$TMP/check_json.py" "$TMP/bj" || fail "a field of board --json is missing or of the wrong type"
CREW_ORCH_NOW=$pin orch board --json --urls >"$TMP/bj2" || fail "board --json --urls failed"
cmp -s "$TMP/bj" "$TMP/bj2" || fail "--urls changes the JSON view"
pass

# ---------------------------------------------------------------- subagent items
# An item that a subagent of the orchestrator runs, with no implementer
# session: the `subagent` field, `item <id> pr none`, and its board row.
subs() { python3 "$ORCH_PY" --orch subs "$@"; }
sjcheck() {
  python3 "$ORCH_PY" --orch subs show >"$TMP/subs.json" || fail "show failed"
  python3 - "$TMP/subs.json" "$1" <<'PY' || fail "check is false: $1"
import json, sys
s = json.load(open(sys.argv[1]))
sys.exit(0 if eval(sys.argv[2]) else 1)
PY
}
SUBS="$CREW_RECORD_ROOT/orchestrators/subs/orchestrator.json"

STEP="subagent: item add writes subagent null"
expect_exit 0 subs init
expect_exit 0 subs item add tickets --title "Move the tickets" --repo owner/dash
expect_exit 0 subs item add impl --title "Implementer work" --repo owner/dash
sjcheck 's["items"]["tickets"]["subagent"] is None and s["items"]["impl"]["subagent"] is None'
pass

STEP="subagent: set subagent takes an object, and subagent.<key> merges"
expect_exit 0 subs item tickets set subagent '{"name": "sub-tickets", "model": "sonnet", "worktree": null, "branch": null}'
expect_exit 0 subs item tickets set subagent.outcome '"moved 12 tickets"'
expect_exit 0 subs item tickets set subagent.ready '"ready abc1234: no findings"'
sjcheck 's["items"]["tickets"]["subagent"] == {"name": "sub-tickets", "model": "sonnet", "worktree": None, "branch": None, "outcome": "moved 12 tickets", "ready": "ready abc1234: no findings"}'
pass

STEP="subagent: a bad key, a bad value or a bad object exits 2 and writes nothing"
before=$(cat "$SUBS")
for args in 'subagent.tab "x"' 'subagent.name 3' 'subagent [1]' 'subagent {"name":"a","tab":"b"}' 'subagent {"name":3}' 'subagent "sub-x"'; do
  # shellcheck disable=SC2086
  set -- $args
  expect_exit 2 subs item impl set "$1" "$2"
  one_line_err
done
[ "$before" = "$(cat "$SUBS")" ] || fail "a refused subagent write changed the record"
pass

STEP="subagent: a subagent item takes no launch, and an item with a launch takes no subagent"
expect_exit 2 subs item tickets set launch '{"tab": "tmux:%1"}'
one_line_err
expect_exit 2 subs item tickets set launch.tab '"tmux:%1"'
one_line_err
expect_exit 0 subs item impl set launch '{"tab": "tmux:%2", "session_name": "impl"}'
expect_exit 2 subs item impl set subagent '{"name": "sub-impl"}'
one_line_err
expect_exit 2 subs item impl set subagent.name '"sub-impl"'
one_line_err
expect_exit 0 subs item impl set subagent null
sjcheck 's["items"]["impl"]["subagent"] is None and s["items"]["impl"]["launch"]["tab"] == "tmux:%2"'
pass

STEP="subagent: the escalation clears pr, github and subagent, then a launch is allowed"
expect_exit 0 subs item add esc --title "Larger than it looked" --repo owner/dash
expect_exit 0 subs item esc set subagent '{"name": "sub-esc", "model": "sonnet", "worktree": "/w/esc", "branch": "worktree-sub-esc"}'
expect_exit 0 subs item esc pr 501
cat >"$TMP/gh/pr-501.json" <<'J'
{"state": "OPEN", "isDraft": false, "reviewDecision": null, "mergeStateStatus": "CLEAN", "statusCheckRollup": []}
J
cat >"$TMP/gh/queue-501.json" <<'J'
{"data": {"repository": {"pullRequest": {"isInMergeQueue": false, "mergeQueueEntry": null}}}}
J
expect_exit 0 subs refresh esc
sjcheck 's["items"]["esc"]["github"] is not None and s["items"]["esc"]["merge"] == "can merge"'
expect_exit 2 subs item esc pr nothing
one_line_err
expect_exit 0 subs item esc pr none
expect_exit 0 subs item esc set subagent null
expect_exit 0 subs stage esc queued
sjcheck 's["items"]["esc"]["pr"] is None and s["items"]["esc"]["github"] is None and s["items"]["esc"]["merge"] == "no PR" and s["items"]["esc"]["subagent"] is None'
expect_exit 0 subs refresh
sjcheck 's["items"]["esc"]["github"] is None'
expect_exit 0 subs item esc set launch '{"tab": "tmux:%3"}'
pass

STEP="subagent: an old record with no subagent key reads as null and takes a write"
python3 -c 'import json,sys; p=sys.argv[1]; s=json.load(open(p)); del s["items"]["esc"]["subagent"]; json.dump(s, open(p, "w"))' "$SUBS"
expect_exit 0 subs board --json
sjcheck '"subagent" in s["items"]["esc"] and s["items"]["esc"]["subagent"] is None'
python3 -c 'import json,sys; p=sys.argv[1]; s=json.load(open(p)); del s["items"]["impl"]["subagent"]; json.dump(s, open(p, "w"))' "$SUBS"
expect_exit 0 subs item add old2 --title "Old" --repo owner/dash
python3 -c 'import json,sys; p=sys.argv[1]; s=json.load(open(p)); del s["items"]["old2"]["subagent"]; json.dump(s, open(p, "w"))' "$SUBS"
expect_exit 0 subs item old2 set subagent.name '"sub-old2"'
sjcheck 's["items"]["old2"]["subagent"] == {"name": "sub-old2", "model": None, "worktree": None, "branch": None, "outcome": None, "ready": None}'
pass

STEP="subagent: the board row says subagent, and the outcome takes the place of doing"
expect_exit 0 subs stage tickets build --doing "moves the tickets"
subs board --json >"$TMP/sbj" || fail "board --json failed"
python3 "$TMP/check_json.py" "$TMP/sbj" || fail "a field of board --json is missing or of the wrong type"
python3 - "$TMP/sbj" <<'PY' || fail "the subagent rows are wrong: $(cat "$TMP/sbj")"
import json, sys
d = json.load(open(sys.argv[1]))
rows = {r["id"]: r for s in d["sections"] for r in s["rows"]}
assert rows["tickets"]["subagent"] is True, rows["tickets"]
assert rows["tickets"]["text"] == "subagent · moved 12 tickets", rows["tickets"]["text"]
assert rows["old2"]["subagent"] is True and rows["old2"]["text"] == "subagent", rows["old2"]
assert rows["impl"]["subagent"] is False and rows["esc"]["subagent"] is False, (rows["impl"], rows["esc"])
assert not rows["impl"]["text"].startswith("subagent"), rows["impl"]
PY
subs board >"$TMP/sbt" || fail "board failed"
grep -E '^ +[0-9]+ tickets .*subagent · moved 12 tickets' "$TMP/sbt" >/dev/null || fail "the text row of a subagent item: $(cat "$TMP/sbt")"
python3 "$TMP/same_board.py" "$TMP/sbj" "$TMP/sbt" || fail "the subagent board views differ"
expect_exit 0 subs item tickets set subagent.outcome null
subs board --json >"$TMP/sbj" || fail "board --json failed"
python3 - "$TMP/sbj" <<'PY' || fail "with no outcome the row text is not subagent · doing"
import json, sys
d = json.load(open(sys.argv[1]))
rows = {r["id"]: r for s in d["sections"] for r in s["rows"]}
assert rows["tickets"]["text"] == "subagent · moves the tickets", rows["tickets"]["text"]
PY
pass

STEP="R1 board --json holds the values of the fleet record"
CREW_ORCH_NOW=$pin orch board --json >"$TMP/bj" || fail "board --json failed"
python3 - "$TMP/bj" <<'PY' || fail "a value of board --json is wrong: $(cat "$TMP/bj")"
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
assert d["orch"] == "fleet" and d["plan"] is None and d["done"] == 1, (d["orch"], d["plan"], d["done"])
assert [e["id"] for e in d["needs_you"]["entries"]] == ["d1", "q2", "i1"], d["needs_you"]
d1 = d["needs_you"]["entries"][0]
assert (d1["kind"], d1["item"], d1["item_id"], d1["recommend"]) == ("decision", "dialogs/editor", "editor", "editor"), d1
i1 = d["needs_you"]["entries"][2]
assert (i1["item"], i1["item_id"], i1["recommend"]) == ("-", None, None), i1
assert [(s["kind"], s["title"]) for s in d["sections"]] == [("group", "Dialog migration"), ("single", "Single items")]
g = d["sections"][0]
assert g["id"] == "dialogs" and g["ticket"] == {"id": "T-1", "url": "https://tickets.example/T-1"}, g
assert (g["repo"], g["merged"], g["total"]) == ("owner/dash", 0, 2), g
ed, se = g["rows"]
assert (ed["n"], ed["id"], ed["launch_tab"], ed["ticket"]) == (1, "editor", "tmux:%3", None), ed
assert ed["pr"] == {"number": 893, "label": "#893", "url": "https://github.com/owner/dash/pull/893"}, ed
assert (se["n"], se["id"], se["marks"], se["status"], se["pr"], se["text"]) == (2, "settings", "●●◐○○", "build 2/3", None, "after editor · ic-2 reads the diff"), se
assert se["age"] != "" and se["launch_tab"] is None, se
lo = d["sections"][1]["rows"][0]
assert (lo["n"], lo["id"], lo["status"], lo["pr"]["label"], lo["ticket"], lo["age"]) == (3, "loner", "can merge", "#77", None, ""), lo
PY
CREW_ORCH_NOW=$pin orch board >"$TMP/bt" || fail "board failed"
python3 "$TMP/same_board.py" "$TMP/bj" "$TMP/bt" || fail "the text view and the JSON view differ: $(cat "$TMP/bt")"
pass

STEP="R16 CREW_ORCH_NOW pins the time the board reads, and no write"
expect_exit 0 orch doing loner "pins the clock"
stamp=$(python3 "$ORCH_PY" --orch fleet show loner | python3 -c 'import json,sys; print(json.load(sys.stdin)["doing_at"])')
then_=$(python3 -c 'import calendar,sys,time; print(calendar.timegm(time.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%SZ")))' "$stamp")
CREW_ORCH_NOW=$((then_ + 7200)) orch board --json >"$TMP/bj" || fail "board with CREW_ORCH_NOW failed"
python3 -c 'import json,sys; d=json.load(open(sys.argv[1])); r=[r for s in d["sections"] for r in s["rows"] if r["id"]=="loner"][0]; sys.exit(0 if r["age"]=="2h" else 1)' "$TMP/bj" || fail "the age does not count from CREW_ORCH_NOW"
CREW_ORCH_NOW=1000 orch doing loner "writes the real time"
jcheck 's["items"]["loner"]["doing_at"] >= "2026"'
jcheck 's["updated_at"] >= "2026"'
expect_exit 0 orch doing loner ""
pass

# A record with a ticket on a grouped item and on a single item.
orch3() { python3 "$ORCH_PY" --orch tix "$@"; }
expect_exit 0 orch3 init
expect_exit 0 orch3 group add g --title "Ticket group" --repo owner/tix --ticket G-1 --ticket-url https://tickets.example/G-1
expect_exit 0 orch3 item add grouped --title "Grouped" --repo owner/tix --group g --ticket A-1 --ticket-url https://tickets.example/A-1
expect_exit 0 orch3 item add solo --title "Solo" --repo owner/tix --ticket SOLO-12 --ticket-url https://tickets.example/SOLO-12
expect_exit 0 orch3 item add bare --title "Bare" --repo owner/tix
expect_exit 0 orch3 item add plain --title "Plain" --repo owner/tix --ticket P-3
expect_exit 0 orch3 item solo pr 41
expect_exit 0 orch3 item grouped pr 40

STEP="R3 a single item's row shows its own ticket, a grouped row shows none"
orch3 board >"$TMP/b3" || fail "board failed"
grep -E '^ *2 +solo .*#41  SOLO-12( |$)' "$TMP/b3" >/dev/null || fail "the solo row has no ticket after its PR: $(cat "$TMP/b3")"
grep -E '^ *4 +plain .* P-3' "$TMP/b3" >/dev/null || fail "a ticket with no URL does not show: $(cat "$TMP/b3")"
grep -E '^ *1 +grouped ' "$TMP/b3" | grep -F 'A-1' >/dev/null && fail "the grouped row shows its ticket"
python3 - "$TMP/b3" <<'PY' || fail "the ticket cell of the single items is not one width: $(cat "$TMP/b3")"
import sys
rows = [l for l in open(sys.argv[1], encoding="utf-8").read().split("\n") if l.startswith("  ") and l.split()[1] in ("solo", "bare", "plain")]
assert len(rows) == 3, rows
# Each single row has "queued" as its status, so its PR cell starts at one column.
starts = {l.split()[1]: l.index("queued") for l in rows}
assert len(set(starts.values())) == 1, starts
PY
orch3 board --urls >"$TMP/b3" || fail "board --urls failed"
sed -n '/^ Links/,$p' "$TMP/b3" >"$TMP/links3"
grep -E '^ +SOLO-12 +https://tickets.example/SOLO-12$' "$TMP/links3" >/dev/null || fail "Links has no single item ticket: $(cat "$TMP/links3")"
grep -F 'A-1' "$TMP/links3" >/dev/null && fail "Links has the grouped item's ticket"
grep -F 'G-1' "$TMP/links3" >/dev/null || fail "Links has no group ticket"
orch3 board --json >"$TMP/bj3" || fail "board --json failed"
python3 "$TMP/check_json.py" "$TMP/bj3" || fail "board --json of the ticket record is wrong"
python3 - "$TMP/bj3" <<'PY' || fail "the JSON tickets are wrong"
import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
rows = {r["id"]: r for s in d["sections"] for r in s["rows"]}
assert rows["grouped"]["ticket"] is None, rows["grouped"]
assert rows["solo"]["ticket"] == {"id": "SOLO-12", "url": "https://tickets.example/SOLO-12"}, rows["solo"]
assert rows["plain"]["ticket"] == {"id": "P-3", "url": None}, rows["plain"]
assert rows["bare"]["ticket"] is None, rows["bare"]
PY
orch3 board >"$TMP/b3"
python3 "$TMP/same_board.py" "$TMP/bj3" "$TMP/b3" || fail "the text view and the JSON view of the ticket record differ"
pass

# ---------------------------------------------------------------- R2
# The text view of this branch against the script on the main branch, for a
# record whose every time is more than a day old, with a stub crew-usage.py
# whose resets are more than a day away. Each age is in days, each reset a
# weekday, so two runs a moment apart print the same text.
# This step checks the one-time migration from the commit MAIN_REF (55e7e89
# by default) to this script. When the clone does not hold that commit, the
# step prints one skip line, and the script goes on.
STEP="R2 the text view equals the main branch's, except the R3 lines"
if ! git -C "$REPO" cat-file -e "$MAIN_REF^{commit}" 2>/dev/null; then
  echo "skip $STEP: no commit $MAIN_REF in this clone"
else
mkdir -p "$TMP/main" "$TMP/this"
git -C "$REPO" show "$MAIN_REF:skills/orchestrator/scripts/crew-orch.py" >"$TMP/main/crew-orch.py" 2>"$TMP/err" || fail "cannot read crew-orch.py at $MAIN_REF: $(cat "$TMP/err")"
cp "$ORCH_PY" "$TMP/this/crew-orch.py"
for d in main this; do
  cat >"$TMP/$d/crew-usage.py" <<'EOF'
import json, sys, time
assert sys.argv[1:] == ["show", "--json"], sys.argv
now = int(time.time())
print(json.dumps({"five_hour": {"used_pct": 47.6, "resets_at": now + 3 * 86400, "full_at": now + 2 * 86400},
                  "seven_day": {"used_pct": 12, "resets_at": now + 5 * 86400}}))
EOF
done
orch4() { python3 "$ORCH_PY" --orch old "$@"; }
expect_exit 0 orch4 init
expect_exit 0 orch4 group add mig --title "Old migration" --repo owner/old --ticket M-1 --ticket-url https://tickets.example/M-1
expect_exit 0 orch4 item add first --title "First" --repo owner/old --group mig --ticket F-1 --ticket-url https://tickets.example/F-1
expect_exit 0 orch4 item add second --title "Second" --repo owner/old --group mig
expect_exit 0 orch4 group mig order first,second
expect_exit 0 orch4 item add lone --title "Lone" --repo owner/old
expect_exit 0 orch4 item add longer-single --title "Longer" --repo owner/old
expect_exit 0 orch4 item first pr 893
expect_exit 0 orch4 refresh first
expect_exit 0 orch4 stage first pr --doing "waits for review"
expect_exit 0 orch4 stage second build --detail 1/2 --doing "ic runs the suite"
expect_exit 0 orch4 stage lone spec --doing "writes the spec"
expect_exit 0 orch4 inbox add decision --item second "Which owner?" --recommend "second"
expect_exit 0 orch4 inbox add idea "A later idea"
expect_exit 0 orch4 ask lone "A question"
expect_exit 0 orch4 route q1 principal
expect_exit 0 orch4 pace set '{"mode": "slowed", "slots": {"busy": 1}}'
# Move every time of the record back by days, and keep their order.
age_record() {
  python3 - "$CREW_RECORD_ROOT/orchestrators/old/orchestrator.json" <<'PY'
import json, sys
p = sys.argv[1]
s = json.load(open(p, encoding="utf-8"))
count = iter(range(100))
def back(obj, key):
    if obj.get(key):
        k = next(count)
        obj[key] = f"2026-0{1 + k % 9}-{10 + k % 18}T0{k % 10}:00:00Z"
for item in s["items"].values():
    for key in ("stage_at", "doing_at", "created_at"):
        back(item, key)
stamp = ["2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z", "2026-01-03T00:00:00Z"]
for entry, at in zip(s["inbox"], stamp):
    entry["created_at"] = at
    if entry.get("routed_at"):
        entry["routed_at"] = "2026-01-05T00:00:00Z"
json.dump(s, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
PY
}
age_record
compare_main() {
  # compare_main <single ids>: the outputs of both scripts are equal, except
  # the rows of those single items and the Links list.
  for flag in "" "--urls"; do
    python3 "$TMP/main/crew-orch.py" --orch old board $flag >"$TMP/main.out" || fail "main board $flag failed"
    python3 "$TMP/this/crew-orch.py" --orch old board $flag >"$TMP/this.out" || fail "board $flag failed"
    python3 - "$TMP/main.out" "$TMP/this.out" "$@" <<'PY' || fail "board $flag differs from $MAIN_REF: $(diff "$TMP/main.out" "$TMP/this.out")"
import re, sys
old = open(sys.argv[1], encoding="utf-8").read().split("\n")
new = open(sys.argv[2], encoding="utf-8").read().split("\n")
singles = set(sys.argv[3:])
assert "Plan" in old[0] and re.search(r"resets (Mon|Tue|Wed|Thu|Fri|Sat|Sun)", old[0]), old[0]
assert re.search(r"  [0-9]+d  ", "\n".join(old)), "no age in days"
# Above the Links list, only the rows of those single items differ.
cut_old = old.index(" Links") if " Links" in old else len(old)
cut_new = new.index(" Links") if " Links" in new else len(new)
assert cut_old == cut_new, (cut_old, cut_new)
for a, b in zip(old[:cut_old], new[:cut_new]):
    if a == b:
        continue
    row = re.match(r"^ +[0-9]+ (\S+)", a)
    assert row and row.group(1) in singles, (a, b)
# The Links list keeps every link of the main output, in its order; a
# single item's ticket may come in between.
rest = iter(new[cut_new:])
for a in old[cut_old:]:
    if a.startswith("  "):
        a = a.split()
    assert any((b.split() if isinstance(a, list) else b) == a for b in rest), ("Links lost", a)
PY
  done
}
compare_main
cmp -s "$TMP/main.out" "$TMP/this.out" || fail "with no single ticket, board --urls is not byte for byte the main output"
# This script's own output before the ticket, so the check below does not
# depend on what MAIN_REF shows.
cp "$TMP/this.out" "$TMP/this-before.out"
expect_exit 0 orch4 item lone set ticket '{"id": "L-7", "url": "https://tickets.example/L-7"}'
age_record
compare_main lone longer-single
grep -E '^ *3 +lone .*L-7' "$TMP/this.out" >/dev/null || fail "the lone row has no ticket"
cmp -s "$TMP/this-before.out" "$TMP/this.out" && fail "a single item ticket does not change the board"
pass
fi

STEP="R2 each derived value is computed in one place"
python3 - "$ORCH_PY" <<'PY' || fail "a derived value is computed in more than one place"
import re, sys
src = open(sys.argv[1], encoding="utf-8").read()
for name in ("age", "clock", "marks", "status_word", "row_text", "meter", "pace_word", "landed",
             "board_data", "render_text", "board_now"):
    assert len(re.findall(rf"^def {name}\(", src, re.M)) == 1, (name, "is not defined once")
# The text view draws from the board data alone: it calls no function
# that derives a value.
body = src[src.index("\ndef render_text("):]
body = body[: body.index("\ndef ", 1)]
for name in ("age", "clock", "marks", "status_word", "row_text", "meter", "pace_word", "landed",
             "merge_value", "usage_figures", "board_now"):
    assert not re.search(rf"(?<![\w.]){name}\(", body), ("render_text calls", name)
# One read of the board time, and one of the time a write stamps.
assert src.count("time.time()") == 1, "the board time is read in more than one place"
assert src.count('"CREW_ORCH_NOW"') == 1, "CREW_ORCH_NOW is read in more than one place"
assert src.count("datetime.now(") == 1, "the write time is read in more than one place"
PY
pass

# ---------------------------------------------------------------- R16 fixtures
# One record with every kind of row, at a pinned time and time zone. The
# fixtures under tests/fixtures/ are its JSON view and its text view, each
# wrapped as a module: `claude plugin test` loads only code files.
STEP="R16 the board fixtures match a fresh run"
NOW=1794830400  # 2026-11-16T12:00:00Z
mkdir -p "$TMP/fixcopy" "$TMP/fix"
cp "$ORCH_PY" "$TMP/fixcopy/crew-orch.py"
cat >"$TMP/fixcopy/crew-usage.py" <<EOF
import json, sys
assert sys.argv[1:] == ["show", "--json"], sys.argv
print(json.dumps({"five_hour": {"used_pct": 68, "resets_at": $NOW + 5400, "full_at": $NOW + 3000},
                  "seven_day": {"used_pct": 31, "resets_at": $NOW + 3 * 86400}}))
EOF
orch5() { python3 "$ORCH_PY" --orch fixture "$@"; }
expect_exit 0 orch5 init
expect_exit 0 orch5 group add dialogs --title "Dialog migration" --repo owner/dash --ticket DASH-1 --ticket-url https://tickets.example/DASH-1
expect_exit 0 orch5 item add editor --title "Editor" --repo owner/dash --group dialogs --ticket DASH-2 --ticket-url https://tickets.example/DASH-2
expect_exit 0 orch5 item add settings --title "Settings" --repo owner/dash --group dialogs
expect_exit 0 orch5 item add export --title "Export" --repo owner/dash --group dialogs
expect_exit 0 orch5 group dialogs order editor,settings,export
expect_exit 0 orch5 item add loner --title "Loner" --repo owner/other --ticket "owner/other#12" --ticket-url https://github.com/owner/other/issues/12
expect_exit 0 orch5 item add docs --title "Docs" --repo owner/other
expect_exit 0 orch5 item add done1 --title "Done" --repo owner/other
expect_exit 0 orch5 item add moves --title "Move tickets" --repo owner/other
expect_exit 0 orch5 item editor pr 893
expect_exit 0 orch5 item settings pr 894
expect_exit 0 orch5 item loner pr 77
expect_exit 0 orch5 stage editor merged
expect_exit 0 orch5 stage settings review --doing "reads the review"
expect_exit 0 orch5 stage export build --detail 2/3 --doing "ic-2 runs the suite"
expect_exit 0 orch5 stage loner pr
expect_exit 0 orch5 stage docs spec --doing "writes the spec"
expect_exit 0 orch5 stage done1 shipped
expect_exit 0 orch5 item moves set subagent '{"name": "sub-moves", "model": "sonnet"}'
expect_exit 0 orch5 stage moves build --doing "moves the tickets"
expect_exit 0 orch5 item settings set launch '{"tab": "tmux:%7", "terminal": "tmux"}'
expect_exit 0 orch5 item loner set launch.tab '"iterm2:w1t2"'
cat >"$TMP/gh/pr-894.json" <<'EOF'
{"state": "OPEN", "isDraft": false, "reviewDecision": "REVIEW_REQUIRED", "mergeStateStatus": "BLOCKED", "statusCheckRollup": []}
EOF
cat >"$TMP/gh/queue-894.json" <<'EOF'
{"data": {"repository": {"pullRequest": {"isInMergeQueue": false, "mergeQueueEntry": null}}}}
EOF
cat >"$TMP/gh/pr-77.json" <<'EOF'
{"state": "OPEN", "isDraft": false, "reviewDecision": "APPROVED", "mergeStateStatus": "CLEAN", "statusCheckRollup": []}
EOF
expect_exit 0 orch5 refresh settings
expect_exit 0 orch5 refresh loner
expect_exit 0 orch5 inbox add decision --item export "Two parts open the video dialog. Who owns it?" --recommend "export"
expect_exit 0 orch5 ask loner "Keep the old export?"
expect_exit 0 orch5 route q1 principal
expect_exit 0 orch5 inbox add idea "No test asserts button order. New ticket?"
expect_exit 0 orch5 pace set '{"mode": "slowed", "slots": {"busy": 2}}'
python3 - "$CREW_RECORD_ROOT/orchestrators/fixture/orchestrator.json" "$NOW" <<'PY'
import json, sys, time
p, now = sys.argv[1], int(sys.argv[2])
s = json.load(open(p, encoding="utf-8"))
def at(ago):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(now - ago))
for n, item in enumerate(s["items"].values()):
    item["created_at"] = item["stage_at"] = at(3 * 86400 - n)
for iid, ago in (("settings", 40), ("export", 12 * 60), ("docs", 2 * 3600), ("moves", 5 * 60)):
    s["items"][iid]["doing_at"] = at(ago)
for n, entry in enumerate(s["inbox"]):
    entry["created_at"] = at(86400 + 600 - n * 300)
    if entry.get("routed_at"):
        entry["routed_at"] = at(3 * 3600)
json.dump(s, open(p, "w", encoding="utf-8"), indent=2, ensure_ascii=False)
PY
TZ=UTC CREW_ORCH_NOW=$NOW python3 "$TMP/fixcopy/crew-orch.py" --orch fixture board --json >"$TMP/fix/board.json" || fail "board --json of the fixture record failed"
TZ=UTC CREW_ORCH_NOW=$NOW python3 "$TMP/fixcopy/crew-orch.py" --orch fixture board >"$TMP/fix/board.txt" || fail "board of the fixture record failed"
python3 "$TMP/check_json.py" "$TMP/fix/board.json" || fail "the fixture JSON is wrong"
python3 "$TMP/same_board.py" "$TMP/fix/board.json" "$TMP/fix/board.txt" || fail "the fixture views differ: $(cat "$TMP/fix/board.txt")"
python3 - "$TMP/fix" <<'PY' || fail "cannot wrap the fixtures"
import json, sys
d = sys.argv[1]
head = "// Generated by skills/orchestrator/scripts/test-crew-orch.sh. Do not edit.\n"
board = open(f"{d}/board.json", encoding="utf-8").read()
text = open(f"{d}/board.txt", encoding="utf-8").read()
open(f"{d}/board-json.ts", "w", encoding="utf-8").write(f"{head}// The output of crew-orch.py board --json.\nexport default {board.rstrip()}\n")
open(f"{d}/board-text.ts", "w", encoding="utf-8").write(f"{head}// The output of crew-orch.py board.\nexport default {json.dumps(text, ensure_ascii=False)}\n")
PY
if [ "${CREW_ORCH_WRITE_FIXTURES:-}" = 1 ]; then
  mkdir -p "$FIX"
  cp "$TMP/fix/board-json.ts" "$TMP/fix/board-text.ts" "$FIX/"
  echo "     wrote $FIX/board-json.ts and $FIX/board-text.ts"
fi
for f in board-json.ts board-text.ts; do
  cmp -s "$TMP/fix/$f" "$FIX/$f" || fail "tests/fixtures/$f differs from a fresh run; run CREW_ORCH_WRITE_FIXTURES=1 bash $0 on purpose: $(diff "$TMP/fix/$f" "$FIX/$f" 2>&1 | head -20)"
done
pass

# ---------------------------------------------------------------- close
# A record of its own, so every check above sees an open record.
closer() { python3 "$ORCH_PY" --orch closer "$@"; }
CD="$CREW_RECORD_ROOT/orchestrators/closer"

STEP="close sets closed_at to now and prints it on one line"
expect_exit 0 closer init
expect_exit 2 closer close now
one_line_err
expect_exit 0 closer close
[ "$(wc -l <"$TMP/out" | tr -d ' ')" -eq 1 ] || fail "close printed not one line: $(cat "$TMP/out")"
stamp=$(cat "$TMP/out")
python3 -c 'import sys; from datetime import datetime; datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%SZ")' "$stamp" \
  || fail "close printed no time: $stamp"
python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1]))["closed_at"] == sys.argv[2] else 1)' "$CD/orchestrator.json" "$stamp" \
  || fail "closed_at is not the printed value"
pass

STEP="a second close exits 1 and changes nothing"
before=$(cat "$CD/orchestrator.json")
expect_exit 1 closer close
one_line_err
[ ! -s "$TMP/out" ] || fail "a second close printed: $(cat "$TMP/out")"
[ "$before" = "$(cat "$CD/orchestrator.json")" ] || fail "a second close changed the record"
pass

STEP="an old record with no closed_at reads as null, and close works on it"
expect_exit 0 python3 "$ORCH_PY" --orch oldrec init
OD="$CREW_RECORD_ROOT/orchestrators/oldrec"
python3 -c 'import json,sys; p=sys.argv[1]; s=json.load(open(p)); del s["closed_at"]; json.dump(s, open(p, "w"))' "$OD/orchestrator.json"
python3 "$ORCH_PY" --orch oldrec show >"$TMP/old.json" || fail "show of an old record failed"
python3 -c 'import json,sys; s=json.load(open(sys.argv[1])); sys.exit(0 if "closed_at" in s and s["closed_at"] is None else 1)' "$TMP/old.json" \
  || fail "an old record does not show closed_at null"
expect_exit 0 python3 "$ORCH_PY" --orch oldrec close
pass

echo "all checks passed"

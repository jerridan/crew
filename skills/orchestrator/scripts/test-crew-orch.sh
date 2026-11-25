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
# `gh api graphql ... -F n=<n>` from $TMP/gh/queue-<n>.json, or from
# threads-<n>.json when the query names reviewThreads (no file: no thread).
# It also answers `pr diff` from files-<n>.txt, `repo view` from repo-view.json,
# `api repos/...` from contents.json, `issue view` and `issue close`, and
# `pr merge <n>`: it logs the call and sets the state of pr-<n>.json to MERGED,
# unless the file $TMP/gh/queue-mode exists. A missing file is a failed call.
cat >"$TMP/bin/gh" <<EOF
#!/usr/bin/env bash
D="$TMP/gh"
echo "\$*" >>"\$D/calls.log"
if [ "\$1" = pr ] && [ "\$2" = view ]; then
  f="\$D/pr-\$3.json"
elif [ "\$1" = pr ] && [ "\$2" = diff ]; then
  f="\$D/files-\$3.txt"
elif [ "\$1" = pr ] && [ "\$2" = merge ]; then
  [ ! -f "\$D/merge-fails" ] || { echo "merge refused by stub" >&2; exit 1; }
  [ -f "\$D/queue-mode" ] || python3 - "\$D/pr-\$3.json" <<'PYG'
import json, sys
d = json.load(open(sys.argv[1])); d["state"] = "MERGED"
json.dump(d, open(sys.argv[1], "w"))
PYG
  exit 0
elif [ "\$1" = repo ] && [ "\$2" = view ]; then
  f="\$D/repo-view.json"
elif [ "\$1" = api ] && [ "\$2" = graphql ]; then
  n=""
  for a in "\$@"; do case "\$a" in n=*) n="\${a#n=}" ;; esac; done
  case "\$*" in
    *reviewThreads*) f="\$D/threads-\$n.json"
       [ -f "\$f" ] || { echo '{"data":{"repository":{"pullRequest":{"reviewThreads":{"nodes":[]}}}}}'; exit 0; } ;;
    *) f="\$D/queue-\$n.json" ;;
  esac
elif [ "\$1" = api ]; then
  f="\$D/contents.json"
elif [ "\$1" = issue ] && [ "\$2" = view ]; then
  f="\$D/issue-\$3.json"
elif [ "\$1" = issue ] && [ "\$2" = close ]; then
  exit 0
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

# ---------------------------------------------------------------- merge (R1)
# A record of its own: two items in group g (a before b, one shared file), and
# single items for the refusals. A stub window-watch records each `say`.
morch() { python3 "$ORCH_PY" --orch mrg "$@"; }
export CREW_CONFIG="$TMP/no-config.md"
MD="$CREW_RECORD_ROOT/orchestrators/mrg"
mjcheck() {
  python3 "$ORCH_PY" --orch mrg show >"$TMP/mshow.json" || fail "show failed"
  python3 - "$TMP/mshow.json" "$1" <<'PYM' || fail "check is false: $1"
import json, sys
s = json.load(open(sys.argv[1]))
sys.exit(0 if eval(sys.argv[2]) else 1)
PYM
}
cat >"$TMP/bin/watchstub" <<EOF
#!/usr/bin/env bash
echo "\$*" >>"$TMP/watch.log"
echo said
EOF
chmod +x "$TMP/bin/watchstub"
export CREW_ORCH_WATCH="$TMP/bin/watchstub"
: >"$TMP/watch.log"
SHA1=aaaa1111aaaa1111aaaa1111aaaa1111aaaa1111
# seed_pr <n> <sha> [<check conclusion>] [<review decision>]: a green PR by default.
seed_pr() {
  local n=$1 sha=$2 concl=${3:-SUCCESS} dec=${4:-APPROVED} status=COMPLETED
  [ "$concl" = PENDING ] && { status=IN_PROGRESS; concl=""; }
  cat >"$TMP/gh/pr-$n.json" <<EOF
{"state": "OPEN", "isDraft": false, "reviewDecision": "$dec", "mergeStateStatus": "CLEAN",
 "headRefOid": "$sha", "author": {"login": "imp"}, "reviews": [], "comments": [],
 "statusCheckRollup": [{"__typename": "CheckRun", "name": "test", "status": "$status", "conclusion": "$concl", "startedAt": "2026-11-24T10:00:00Z"}]}
EOF
  echo '{"data": {"repository": {"pullRequest": {"isInMergeQueue": false, "mergeQueueEntry": null}}}}' >"$TMP/gh/queue-$n.json"
  printf 'src/x.py\n' >"$TMP/gh/files-$n.txt"
}
echo '{"defaultBranchRef": {"name": "main"}, "rebaseMergeAllowed": true, "squashMergeAllowed": true, "mergeCommitAllowed": true}' >"$TMP/gh/repo-view.json"
expect_exit 0 morch init
expect_exit 0 morch group add g --title Group
expect_exit 0 morch item add a --title A --repo owner/mr --group g
expect_exit 0 morch item add b --title B --repo owner/mr --group g
expect_exit 0 morch group g order a,b
for i in c d e f g h; do expect_exit 0 morch item add $i --title "Item $i" --repo owner/mr; done
n=701; for i in a b c d e f g h; do expect_exit 0 morch item $i pr $n; n=$((n + 1)); done
expect_exit 0 morch item b set launch '{"session_name": "sess-b", "worktree": "/x/b"}'
expect_exit 0 morch pace set '{"slots": {"busy": 2, "max": 3}}'
# a is a delivered item: a goal record names it.
mkdir -p "$CREW_RECORD_ROOT/goal-a"
echo '{"run": {"run_state": "delivered", "orchestrator": {"name": "mrg", "item": "a"}}}' >"$CREW_RECORD_ROOT/goal-a/state.json"
seed_pr 701 $SHA1
seed_pr 702 bbbb2222bbbb2222bbbb2222bbbb2222bbbb2222
seed_pr 703 cccc3333cccc3333cccc3333cccc3333cccc3333
seed_pr 704 dddd4444dddd4444dddd4444dddd4444dddd4444
seed_pr 705 eeee5555eeee5555eeee5555eeee5555eeee5555
seed_pr 706 ffff6666ffff6666ffff6666ffff6666ffff6666 PENDING
seed_pr 707 1111777711117777111177771111777711117777
seed_pr 708 2222888822228888222288882222888822228888

STEP="R1 (b) a ready line for an old head refuses with exit 4"
expect_exit 4 morch merge c --ready "ready 9999999: fixed it"
one_line_err
grep -q '^crew-orch: merge ready: ' "$TMP/err" || fail "bad stderr: $(cat "$TMP/err")"
! grep -q 'pr merge' "$TMP/gh/calls.log" || fail "gh pr merge ran"
mjcheck 's["items"]["c"]["ready"]["sha"] == "9999999"'
pass

STEP="R1 a head with no ready line is pending: exit 11, and no merge"
expect_exit 11 morch merge h
one_line_err
grep -q '^crew-orch: merge pending: ' "$TMP/err" || fail "bad stderr: $(cat "$TMP/err")"
pass

STEP="R1 (c) an unresolved review thread refuses with exit 5"
cat >"$TMP/gh/threads-704.json" <<'EOF'
{"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": [{"isResolved": false}, {"isResolved": true}]}}}}}
EOF
expect_exit 5 morch merge d --ready "ready dddd444: ok"
one_line_err
grep -q '^crew-orch: merge threads: ' "$TMP/err" || fail "bad stderr: $(cat "$TMP/err")"
pass

STEP="R1 (d) a finding outside a thread refuses with exit 6 unless --findings-answered"
python3 - "$TMP/gh/pr-705.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
d["reviews"] = [{"author": {"login": "rev"}, "state": "COMMENTED", "body": "Please rename the helper, it is not clear what it does at all here and so on " * 3}]
d["comments"] = [{"author": {"login": "imp"}, "body": "own comment"}]
json.dump(d, open(sys.argv[1], "w"))
PY
expect_exit 6 morch merge e --ready "ready eeee555: ok"
one_line_err
grep -q 'rev' "$TMP/out" || fail "the finding is not printed: $(cat "$TMP/out")"
grep -q 'Please rename' "$TMP/out" || fail "the finding text is not printed"
! grep -q 'own comment' "$TMP/out" || fail "the PR author's own comment counts as a finding"
! grep -q 'pr merge 705' "$TMP/gh/calls.log" || fail "gh pr merge ran"
pass

STEP="R1 (e) a pending check queues with --when-green and exits 0, else exits 11"
expect_exit 11 morch merge f --ready "ready ffff666: ok"
expect_exit 0 morch merge f --when-green
mjcheck 's["merge_queue"] == ["f"]'
! grep -q 'pr merge 706' "$TMP/gh/calls.log" || fail "gh pr merge ran for a pending PR"
pass

STEP="R1 (f) a Merge section stops before the method with exit 9 and prints its text"
printf '# Crew\n\n## Merge\n\nPost the link in the review channel.\n\n## Other\n\nx\n' | python3 -c 'import base64,json,sys; print(json.dumps({"content": base64.b64encode(sys.stdin.read().encode()).decode(), "encoding": "base64"}))' >"$TMP/gh/contents.json"
expect_exit 9 morch merge g --ready "ready 1111777: ok"
grep -q 'Post the link in the review channel' "$TMP/out" || fail "the Merge section text is not printed: $(cat "$TMP/out")"
! grep -q 'pr merge 707' "$TMP/gh/calls.log" || fail "gh pr merge ran with a Merge section"
rm -f "$TMP/gh/contents.json"
pass

STEP="R1 (a) a green PR merges by rebase with the head sha, then the words, the slot and the events"
expect_exit 0 morch merge a --ready "ready aaaa1111aaaa: fine"
grep -q "pr merge 701 --repo owner/mr --rebase --match-head-commit $SHA1" "$TMP/gh/calls.log" || fail "no rebase merge with the sha: $(grep 'pr merge' "$TMP/gh/calls.log")"
mjcheck 's["pace"]["slots"]["busy"] == 1'
grep -q -- '--item mrg/a ' "$TMP/watch.log" || fail "no merge word by say: $(cat "$TMP/watch.log")"
grep -q 'send-to: sess-b' "$TMP/out" || fail "no send-to line for the rebase word: $(cat "$TMP/out")"
mjcheck 'len(s["items"]["b"]["told"]) == 1'
grep -qi 'rebase' "$MD/told/b-1.md" || fail "the rebase word is not recorded in told"
mjcheck 'any(e["item"] == "a" and "merged" in e["text"] for e in s["events"]) and any(e["item"] == "b" and "rebase" in e["text"] for e in s["events"])'
mjcheck 's["items"]["a"]["slot_released"] is True'
pass

STEP="R1 a second merge of a merged item releases no second slot"
expect_exit 0 morch merge a
mjcheck 's["pace"]["slots"]["busy"] == 1'
pass

STEP="R7 a merge event shows on board --json"
morch board --json >"$TMP/board.json" || fail "board --json failed"
python3 - "$TMP/board.json" <<'PY' || fail "no merge event on the board JSON"
import json, sys
d = json.load(open(sys.argv[1]))
assert any("merged" in e["text"] and e["item"] == "a" for e in d["events"]), d.get("events")
PY
pass

STEP="R1 (F1) a merge into a queue exits 0, sends no word, and keeps the slot"
touch "$TMP/gh/queue-mode"
before=$(wc -l <"$TMP/watch.log")
expect_exit 0 morch merge c --ready "ready cccc333: ok"
[ "$(wc -l <"$TMP/watch.log")" -eq "$before" ] || fail "a word went out for a PR that is not merged"
mjcheck 's["pace"]["slots"]["busy"] == 1 and not s["items"]["c"].get("slot_released")'
mjcheck 'any(e["item"] == "c" and "queued" in e["text"] for e in s["events"])'
rm -f "$TMP/gh/queue-mode"
pass

STEP="R1 a failed gh pr merge exits 10"
touch "$TMP/gh/merge-fails"
expect_exit 10 morch merge c
one_line_err
rm -f "$TMP/gh/merge-fails"
pass

STEP="R1 --findings-answered lets a PR with findings merge"
expect_exit 0 morch merge e --findings-answered
grep -q 'pr merge 705 ' "$TMP/gh/calls.log" || fail "no merge for e"
mjcheck 's["pace"]["slots"]["busy"] == 0'
pass

STEP="R1 (F1) a PR closed with no merge releases its slot once, and sends no merge word"
python3 - "$TMP/gh/pr-704.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1])); d["state"] = "CLOSED"
json.dump(d, open(sys.argv[1], "w"))
PY
expect_exit 0 morch pace set '{"slots": {"busy": 2}}'
expect_exit 0 morch finalize d
expect_exit 0 morch finalize d
mjcheck 's["items"]["d"]["slot_released"] is True and s["pace"]["slots"]["busy"] == 1'
pass

# ---------------------------------------------------------------- send (R2)
STEP="R2 a delivered item gets a say line and a told entry"
echo hi-delivered >"$TMP/msg.txt"
: >"$TMP/watch.log"
expect_exit 0 morch send a --text "check the merge" --from boss
grep -q '^said: a$' "$TMP/out" || fail "no said line: $(cat "$TMP/out")"
grep -q -- '--item mrg/a --from boss check the merge' "$TMP/watch.log" || fail "no say call: $(cat "$TMP/watch.log")"
mjcheck 'len(s["items"]["a"]["told"]) == 2'
pass

STEP="R2 a live item gets a told entry and the send-to lines, and no script sends it"
expect_exit 0 morch send b --file "$TMP/msg.txt" --from boss
grep -q '^send-to: sess-b$' "$TMP/out" || fail "no send-to line: $(cat "$TMP/out")"
path=$(sed -n 's/^told: //p' "$TMP/out")
[ "$(cat "$path")" = "hi-delivered" ] || fail "told copy differs: $path"
! grep -q 'sess-b' "$TMP/watch.log" || fail "a live item went through say"
pass

STEP="R2 send needs --text or --file, not both, and refuses a subagent item"
expect_exit 2 morch send b
expect_exit 2 morch send b --text x --file "$TMP/msg.txt"
expect_exit 0 morch item add sub1 --title Sub --repo owner/mr
expect_exit 0 morch item sub1 set subagent '{"name": "sub-sub1", "model": "sonnet"}'
expect_exit 1 morch send sub1 --text x
one_line_err
pass

STEP="R1 (F2) a live item's word stays as a pending handoff until it is cleared"
mjcheck 'any(h["item"] == "b" and h["name"] == "sess-b" and h["path"].startswith("told/b-") for h in s["handoffs"])'
mjcheck 'not any(h["item"] == "a" for h in s["handoffs"])'
expect_exit 0 morch handoff clear b
grep -q '^cleared: 1$' "$TMP/out" || fail "bad clear output: $(cat "$TMP/out")"
mjcheck 's["handoffs"] == []'
pass

# ---------------------------------------------------------------- launch (R3)
lorch() { python3 "$ORCH_PY" --orch lch "$@"; }
LD="$CREW_RECORD_ROOT/orchestrators/lch"
ljcheck() {
  python3 "$ORCH_PY" --orch lch show >"$TMP/lshow.json" || fail "show failed"
  python3 - "$TMP/lshow.json" "$1" <<'PYL' || fail "check is false: $1"
import json, sys
s = json.load(open(sys.argv[1]))
sys.exit(0 if eval(sys.argv[2]) else 1)
PYL
}
mkdir -p "$TMP/co" "$TMP/sessions"
git -C "$TMP/co" init -q . || fail "git init"
REALCO=$(cd "$TMP/co" && pwd -P)
echo "## Checkouts

- owner/lr: $TMP/co
" >"$TMP/config.md"
export CREW_CONFIG="$TMP/config.md"
export CREW_SESSIONS_DIR="$TMP/sessions"
echo '{"sessionId": "orchsess", "name": "principal-x"}' >"$TMP/sessions/1.json"
cat >"$TMP/bin/launchstub" <<EOF
#!/usr/bin/env bash
echo "\$*" >>"$TMP/launcher.log"
if [ "\$1" = start ]; then
  name=""
  while [ \$# -gt 0 ]; do [ "\$1" = --name ] && name="\$2"; shift; done
  [ -f "$TMP/no-session" ] || echo "{\"sessionId\": \"i-\$name\", \"name\": \"\$name\"}" >"$TMP/sessions/\$name.json"
  echo "{\"session_name\": \"\$name\", \"repo\": \"owner/lr\", \"worktree\": \"$REALCO/.claude/worktrees/\$name\", \"branch\": \"worktree-\$name\", \"base\": \"origin/main\", \"model\": \"sonnet\", \"terminal\": \"tmux\", \"tab\": \"tmux:%7\", \"tab_group\": \"lg\", \"session_id\": \"uuid-\$name\"}"
fi
EOF
chmod +x "$TMP/bin/launchstub"
cat >"$TMP/bin/usagestub" <<EOF
#!/usr/bin/env bash
echo "\$*" >>"$TMP/usage.log"
[ "\$1" = settings ] && echo '{"statusLine": {"type": "command", "command": "stub"}}'
exit 0
EOF
chmod +x "$TMP/bin/usagestub"
export CREW_ORCH_LAUNCHER="$TMP/bin/launchstub" CREW_USAGE_CMD="$TMP/bin/usagestub"
export CLAUDE_CODE_SESSION_ID=orchsess
: >"$TMP/launcher.log"; : >"$TMP/usage.log"
expect_exit 0 lorch init
STEP="R9 init stores the orchestrator session id from CLAUDE_CODE_SESSION_ID"
ljcheck 's.get("orchestrator_session_id") == "orchsess"'
pass

for i in l1 l2 l3; do expect_exit 0 lorch item add $i --title "Launch $i" --repo owner/lr; done
echo "the goal of l1" >"$TMP/goal.md"

STEP="R3 launch runs start with the settings, the principal name and the model, and writes launch and the slot"
expect_exit 0 lorch launch l1 --model sonnet --group lg --terminal tmux --goal-file "$TMP/goal.md" --wait-seconds 3
grep -q -- "settings --cwd $REALCO/.claude/worktrees/l1" "$TMP/usage.log" || fail "no settings call: $(cat "$TMP/usage.log")"
grep -q -- '^start --name l1 --model sonnet --settings .* --principal principal-x --repo owner/lr --group lg --terminal tmux' "$TMP/launcher.log" || fail "bad start call: $(cat "$TMP/launcher.log")"
ljcheck 's["items"]["l1"]["launch"]["session_name"] == "l1" and s["items"]["l1"]["launch"]["tab"] == "tmux:%7"'
ljcheck 's["pace"]["slots"]["busy"] == 1'
[ "$(cat "$LD/told/l1-1.md")" = "the goal of l1" ] || fail "the goal is not the first told entry"
grep -q '^goal-ready: l1$' "$TMP/out" || fail "no goal-ready line: $(cat "$TMP/out")"
pass

STEP="R3 the principal override wins, and a session that never shows prints goal-wait"
touch "$TMP/no-session"
expect_exit 0 lorch launch l2 --principal boss-y --wait-seconds 1
grep -q -- '--principal boss-y' "$TMP/launcher.log" || fail "the override was not used"
grep -q '^goal-wait: ' "$TMP/out" || fail "no goal-wait line: $(cat "$TMP/out")"
rm -f "$TMP/no-session"
ljcheck 's["pace"]["slots"]["busy"] == 2'
pass

STEP="R3 launch refuses at slowed and at a full slot count with exit 3, and writes nothing"
expect_exit 0 lorch pace set '{"mode": "slowed"}'
expect_exit 3 lorch launch l3 --wait-seconds 1
one_line_err
expect_exit 0 lorch pace set '{"mode": "normal", "slots": {"max": 2}}'
expect_exit 3 lorch launch l3 --wait-seconds 1
one_line_err
ljcheck 's["items"]["l3"]["launch"] == {} and s["pace"]["slots"]["busy"] == 2'
[ "$(grep -c '^start ' "$TMP/launcher.log")" -eq 2 ] || fail "start ran for a refused launch"
pass

# ---------------------------------------------------------------- close-item (R4)
# The launcher stub learns find, stop, remove and resume. `find <name>` prints
# $TMP/find-<name>.txt; `remove <path>` prints $TMP/remove-<basename>.json
# (a default clean removal) and exits with the number in remove-<basename>.rc.
cat >"$TMP/bin/launchstub" <<EOF
#!/usr/bin/env bash
echo "\$*" >>"$TMP/launcher.log"
sub=\$1
case "\$sub" in
  start|resume)
    name=""; prev=""
    for a in "\$@"; do [ "\$prev" = --name ] && name="\$a"; prev="\$a"; done
    [ "\$sub" = resume ] || [ -f "$TMP/no-session" ] || echo "{\"sessionId\": \"i-\$name\", \"name\": \"\$name\"}" >"$TMP/sessions/\$name.json"
    echo "{\"session_name\": \"\$name\", \"repo\": \"owner/lr\", \"worktree\": \"$REALCO/.claude/worktrees/\$name\", \"branch\": \"worktree-\$name\", \"base\": \"origin/main\", \"model\": \"sonnet\", \"terminal\": \"tmux\", \"tab\": \"tmux:%7\", \"tab_group\": \"lg\", \"session_id\": \"uuid-\$name\"}" ;;
  find) [ -f "$TMP/find-\$2.txt" ] && cat "$TMP/find-\$2.txt"; exit 0 ;;
  stop) echo "stopped"; exit 0 ;;
  remove)
    base=\$(basename "\$2")
    if [ -f "$TMP/remove-\$base.json" ]; then cat "$TMP/remove-\$base.json"
    else echo '{"worktree": "'"\$2"'", "removed": true, "stopped": [], "kept": [], "changed": [], "branch": null, "branches": [], "lock": null}'; fi
    [ -f "$TMP/remove-\$base.rc" ] && exit "\$(cat "$TMP/remove-\$base.rc")"
    exit 0 ;;
esac
EOF
chmod +x "$TMP/bin/launchstub"
corch() { python3 "$ORCH_PY" --orch cls "$@"; }
CLD="$CREW_RECORD_ROOT/orchestrators/cls"
cjcheck() {
  python3 "$ORCH_PY" --orch cls show >"$TMP/cshow.json" || fail "show failed"
  python3 - "$TMP/cshow.json" "$1" <<'PYC' || fail "check is false: $1"
import json, sys
s = json.load(open(sys.argv[1]))
sys.exit(0 if eval(sys.argv[2]) else 1)
PYC
}
: >"$TMP/launcher.log"; : >"$TMP/watch.log"
expect_exit 0 corch init
n=1
for i in c1 c2 c3 c4 c5 c6; do
  expect_exit 0 corch item add $i --title "Close $i" --repo owner/cl
  expect_exit 0 corch item $i set launch "{\"session_name\": \"$i\", \"worktree\": \"$TMP/wt/$i\", \"tab\": \"tmux:%$n\", \"session_id\": \"sid-$i\"}"
  n=$((n + 1))
done
expect_exit 0 corch item c1 pr 801
expect_exit 0 corch item c1 set ticket '{"id": "12", "url": "https://github.com/owner/cl/issues/12"}'
expect_exit 0 corch item c6 pr 806
for i in c1 c2 c3 c4 c5; do expect_exit 0 corch stage $i shipped; done
expect_exit 0 corch stage c6 closed
echo '{"state": "OPEN"}' >"$TMP/gh/issue-12.json"
mkdir -p "$CREW_RECORD_ROOT/goal-c5"
echo '{"run": {"run_state": "delivered", "orchestrator": {"name": "cls", "item": "c5"}}}' >"$CREW_RECORD_ROOT/goal-c5/state.json"

STEP="R4 the first call sends the processes message and records that it asked"
expect_exit 0 corch close-item c1
grep -q '^send-to: c1$' "$TMP/out" || fail "no send-to line: $(cat "$TMP/out")"
grep -q 'Orchestrator: cls, item c1' "$CLD/told/c1-1.md" || fail "no Orchestrator line in the processes message"
grep -qi 'stop each process' "$CLD/told/c1-1.md" || fail "the message does not ask for the processes"
cjcheck 's["items"]["c1"]["close_asked_at"] is not None'
! grep -q '^stop \|^remove ' "$TMP/launcher.log" || fail "the first call stopped or removed"
pass

STEP="R4 a delivered item gets its processes message by say"
expect_exit 0 corch close-item c5
grep -q '^said: c5$' "$TMP/out" || fail "no said line: $(cat "$TMP/out")"
grep -q -- '--item cls/c5 ' "$TMP/watch.log" || fail "no say call"
pass

STEP="R4 --continue on a merged item stops, removes the branch and the PR branch, and closes the open ticket"
expect_exit 0 corch close-item c1 --continue
grep -q '^stop tmux:%1 --name c1 --session-id sid-c1$' "$TMP/launcher.log" || fail "bad stop call: $(cat "$TMP/launcher.log")"
grep -q "^remove $TMP/wt/c1 --delete-branch --pr 801\$" "$TMP/launcher.log" || fail "bad remove call: $(cat "$TMP/launcher.log")"
grep -q 'issue view 12 --repo owner/cl' "$TMP/gh/calls.log" || fail "no issue view"
grep -q 'issue close 12 --repo owner/cl' "$TMP/gh/calls.log" || fail "the open issue was not closed"
grep -q '^stop: ' "$TMP/out" && grep -q '^remove: ' "$TMP/out" && grep -q '^ticket: ' "$TMP/out" || fail "a step has no line: $(cat "$TMP/out")"
pass

STEP="R4 an item with no PR removes with --delete-branch alone, and a closed PR with no flag"
expect_exit 0 corch close-item c2 --continue
grep -q "^remove $TMP/wt/c2 --delete-branch\$" "$TMP/launcher.log" || fail "bad remove call for c2: $(grep '^remove' "$TMP/launcher.log")"
expect_exit 0 corch close-item c6 --continue
grep -q "^remove $TMP/wt/c6\$" "$TMP/launcher.log" || fail "bad remove call for c6: $(grep '^remove' "$TMP/launcher.log")"
pass

STEP="R4 a kept branch gives one inbox notice"
echo '{"worktree": "x", "removed": true, "stopped": [], "kept": [], "changed": [], "branch": "worktree-c3", "branches": [{"name": "worktree-c3", "deleted": false, "unproven_commits": ["abc123"], "checked_out": null}], "lock": null}' >"$TMP/remove-c3.json"
expect_exit 0 corch close-item c3 --continue
cjcheck 'len([e for e in s["inbox"] if e["kind"] == "notice" and e["item"] == "c3" and "worktree-c3" in e["text"]]) == 1'
pass

STEP="R4 a kept process is printed, and --stop-processes runs remove again with the flag"
echo '{"worktree": "x", "removed": false, "stopped": [], "kept": [{"pid": 77, "tty": null, "command": "node server.js"}], "changed": [], "branch": null, "branches": [], "lock": null}' >"$TMP/remove-c4.json"
echo 9 >"$TMP/remove-c4.rc"
expect_exit 0 corch close-item c4 --continue
grep -q '^kept-process: 77 node server.js$' "$TMP/out" || fail "the kept process is not printed: $(cat "$TMP/out")"
cjcheck 'not [e for e in s["inbox"] if e["item"] == "c4"]'
rm -f "$TMP/remove-c4.json" "$TMP/remove-c4.rc"
expect_exit 0 corch close-item c4 --continue --stop-processes
grep -q "^remove $TMP/wt/c4 --delete-branch --stop-processes\$" "$TMP/launcher.log" || fail "no --stop-processes call: $(grep '^remove' "$TMP/launcher.log")"
pass

# ---------------------------------------------------------------- digest (R6)
dorch() { python3 "$ORCH_PY" --orch dig "$@"; }
expect_exit 0 dorch init
expect_exit 0 dorch group add g --title Group
expect_exit 0 dorch item add x --title X --repo owner/dg --group g
expect_exit 0 dorch item add y --title Y --repo owner/dg --group g
expect_exit 0 dorch group g order x,y
expect_exit 0 dorch item x pr 901
expect_exit 0 dorch item y pr 902
seed_pr 901 9019019019019019019019019019019019019019
seed_pr 902 9029029029029029029029029029029029029029
printf 'src/x.py\nsrc/a.py\n' >"$TMP/gh/files-901.txt"
printf 'src/x.py\nsrc/b.py\n' >"$TMP/gh/files-902.txt"
python3 - "$TMP/gh/pr-901.json" <<'PY'
import json, sys
d = json.load(open(sys.argv[1]))
d["files"] = [{"path": "src/x.py", "additions": 10, "deletions": 2}, {"path": "src/a.py", "additions": 4, "deletions": 0}]
d["reviews"] = [{"author": {"login": "rev"}, "state": "COMMENTED", "body": "Rename the helper."}]
json.dump(d, open(sys.argv[1], "w"))
PY
cat >"$TMP/gh/threads-901.json" <<'EOF'
{"data": {"repository": {"pullRequest": {"reviewThreads": {"nodes": [{"isResolved": false}, {"isResolved": true}]}}}}}
EOF
printf 'Build the widget.\nIt has two parts.\n' >"$TMP/brief.md"
expect_exit 0 dorch told x --file "$TMP/brief.md"

STEP="R6 the digest names the brief, the files, the threads, the findings, the CI state, the shared files and the order"
expect_exit 0 dorch digest x
grep -q '^brief: Build the widget. It has two parts.$' "$TMP/out" || fail "no brief: $(cat "$TMP/out")"
grep -q '^file: src/x.py +10 -2$' "$TMP/out" || fail "no file line: $(cat "$TMP/out")"
grep -q '^threads: 1 unresolved$' "$TMP/out" || fail "no threads line: $(cat "$TMP/out")"
grep -q '^finding: rev review Rename the helper.$' "$TMP/out" || fail "no finding line: $(cat "$TMP/out")"
grep -q '^ci: pass$' "$TMP/out" || fail "no ci line: $(cat "$TMP/out")"
grep -q '^shared with y: src/x.py$' "$TMP/out" || fail "no shared line: $(cat "$TMP/out")"
grep -q '^order: x, y$' "$TMP/out" || fail "no order line: $(cat "$TMP/out")"
pass

STEP="R6 --diff-file writes the brief and the diff in one file"
expect_exit 0 dorch digest x --diff-file "$TMP/brief-diff.md"
grep -q 'Build the widget' "$TMP/brief-diff.md" || fail "the diff file has no brief"
grep -q 'src/a.py' "$TMP/brief-diff.md" || fail "the diff file has no diff"
pass

# ---------------------------------------------------------------- resume (R9)
rorch() { python3 "$ORCH_PY" --orch rsm "$@"; }
RD="$CREW_RECORD_ROOT/orchestrators/rsm"
rjcheck() {
  python3 "$ORCH_PY" --orch rsm show >"$TMP/rshow.json" || fail "show failed"
  python3 - "$TMP/rshow.json" "$1" <<'PYR' || fail "check is false: $1"
import json, sys
s = json.load(open(sys.argv[1]))
sys.exit(0 if eval(sys.argv[2]) else 1)
PYR
}
expect_exit 0 rorch init
for i in r1 r2 r3 r4 r5 r6 r7 r8 r9; do
  expect_exit 0 rorch item add $i --title "Resume $i" --repo owner/lr
done
mkdir -p "$TMP/wt/r2" "$TMP/wt/r1" "$TMP/wt/r4" "$TMP/wt/r5" "$TMP/wt/r6"
n=1
for i in r1 r2 r3 r4 r5 r6 r7 r9; do
  expect_exit 0 rorch item $i set launch "{\"session_name\": \"$i\", \"worktree\": \"$TMP/wt/$i\", \"tab\": \"tmux:%$n\", \"session_id\": \"sid-$i\", \"model\": \"sonnet\", \"terminal\": \"tmux\"}"
  n=$((n + 1))
done
for i in r1 r2 r3 r4 r5 r7; do
  printf 'the goal of %s\n' $i >"$TMP/g-$i.md"
  expect_exit 0 rorch told $i --file "$TMP/g-$i.md"
done
for i in r1 r2 r3 r4 r5 r6; do expect_exit 0 rorch stage $i build; done
expect_exit 0 rorch stage r7 pr
expect_exit 0 rorch stage r9 shipped
mkdir -p "$CREW_RECORD_ROOT/goal-r7"
echo '{"run": {"run_state": "delivered", "orchestrator": {"name": "rsm", "item": "r7"}}}' >"$CREW_RECORD_ROOT/goal-r7/state.json"
echo 'tmux:%9 name' >"$TMP/find-r1.txt"
echo 'tmux:%4 id' >"$TMP/find-r4.txt"
echo 'tmux:%5 cwd' >"$TMP/find-r5.txt"
echo 'tmux:%6 name' >"$TMP/find-r6.txt"
rm -f "$TMP/find-r2.txt" "$TMP/find-r3.txt"
: >"$TMP/launcher.log"; : >"$TMP/watch.log"
cp "$RD/orchestrator.json" "$TMP/rsm-before.json"

STEP="R9 resume --read-only prints one line per item and writes and starts nothing"
expect_exit 0 rorch resume --read-only
for i in r1 r2 r3 r4 r5 r6 r7 r8 r9; do
  [ "$(grep -c "^$i " "$TMP/out")" -eq 1 ] || fail "not one line for $i: $(cat "$TMP/out")"
done
grep -q '^r1 rejoin: ' "$TMP/out" || fail "r1 should rejoin"
grep -q '^r2 resume: ' "$TMP/out" || fail "r2 should resume"
grep -q '^r3 notice: ' "$TMP/out" || fail "r3 should notice"
grep -q '^r4 restart: ' "$TMP/out" || fail "r4 should restart"
grep -q '^r5 notice: ' "$TMP/out" || fail "r5 should notice"
grep -q '^r6 send-goal: ' "$TMP/out" || fail "r6 should send its goal"
grep -q '^r7 window: ' "$TMP/out" || fail "r7 should show the window"
grep -q '^r8 launch: ' "$TMP/out" || fail "r8 should launch"
grep -q '^r9 close: ' "$TMP/out" || fail "r9 should close"
cmp -s "$TMP/rsm-before.json" "$RD/orchestrator.json" || fail "read-only changed the record"
! grep -q '^resume \|^start \|^stop ' "$TMP/launcher.log" || fail "read-only started something: $(cat "$TMP/launcher.log")"
! grep -q 'ensure' "$TMP/watch.log" || fail "read-only ran ensure"
pass

STEP="R9 resume writes the changed tab and the slot count, resumes a gone item, and ensures a delivered one"
expect_exit 0 rorch resume
grep -q '^r2 rejoin: ' "$TMP/out" || fail "r2 was not resumed: $(cat "$TMP/out")"
grep -q "^resume --name r2 --worktree $TMP/wt/r2 --session-id sid-r2 --model sonnet " "$TMP/launcher.log" || fail "bad resume call: $(cat "$TMP/launcher.log")"
rjcheck 's["items"]["r1"]["launch"]["tab"] == "tmux:%9"'
rjcheck 's["items"]["r2"]["launch"]["tab"] == "tmux:%7"'
rjcheck 's["pace"]["slots"]["busy"] == 5'
grep -q "ensure $CREW_RECORD_ROOT/goal-r7" "$TMP/watch.log" || fail "no ensure: $(cat "$TMP/watch.log")"
rjcheck 'len(s["items"]["r1"]["told"]) == 1'
pass

STEP="R9 resume stores the session id of the orchestrator, and a closed record prints closed"
rjcheck 's.get("orchestrator_session_id") == "orchsess"'
expect_exit 0 python3 "$ORCH_PY" --orch closer resume
grep -q '^closed: ' "$TMP/out" || fail "no closed line: $(cat "$TMP/out")"
pass

# ---------------------------------------------------------------- wait (R5)
# The usage stub now answers `check` from $TMP/level (default normal) and exits
# with the code of the level, as crew-usage.py does.
cat >"$TMP/bin/usagestub" <<EOF
#!/usr/bin/env bash
echo "\$*" >>"$TMP/usage.log"
if [ "\$1" = settings ]; then echo '{"statusLine": {"type": "command", "command": "stub"}}'; exit 0; fi
lv=normal; [ -f "$TMP/level" ] && lv=\$(cat "$TMP/level")
echo "\$lv five_hour=50% sampled=2026-11-24T10:00:00Z"
case "\$lv" in slowed) exit 10 ;; stopped) exit 20 ;; *) exit 0 ;; esac
EOF
chmod +x "$TMP/bin/usagestub"
rm -f "$TMP/level"
worch() { python3 "$ORCH_PY" --orch wtr "$@"; }
WD="$CREW_RECORD_ROOT/orchestrators/wtr"
wjcheck() {
  python3 "$ORCH_PY" --orch wtr show >"$TMP/wshow.json" || fail "show failed"
  python3 - "$TMP/wshow.json" "$1" <<'PYW' || fail "check is false: $1"
import json, sys
s = json.load(open(sys.argv[1]))
sys.exit(0 if eval(sys.argv[2]) else 1)
PYW
}
# flip_pr <n> <python statement over d>: change a stub PR.
flip_pr() {
  python3 - "$TMP/gh/pr-$1.json" "$2" <<'PYF' || fail "cannot change pr $1"
import json, sys
d = json.load(open(sys.argv[1]))
exec(sys.argv[2])
json.dump(d, open(sys.argv[1], "w"))
PYF
}
expect_exit 0 worch init
expect_exit 0 worch pace set '{"slots": {"busy": 2, "max": 3}}'
for i in p q r u v; do expect_exit 0 worch item add $i --title "Wait $i" --repo owner/wt; done
n=951; for i in p q r u v; do expect_exit 0 worch item $i pr $n; n=$((n + 1)); done
expect_exit 0 worch item u set launch '{"session_name": "sess-u", "worktree": "/x/u"}'
seed_pr 951 9519519519519519519519519519519519519519 PENDING
seed_pr 952 9529529529529529529529529529529529529529
seed_pr 953 9539539539539539539539539539539539539539
seed_pr 954 9549549549549549549549549549549549549549
seed_pr 955 9559559559559559559559559559559559559559 SUCCESS REVIEW_REQUIRED
flip_pr 955 'd["mergeStateStatus"] = "BLOCKED"'
expect_exit 0 worch merge p --ready "ready 9519519: ok" --when-green
wjcheck 's["merge_queue"] == ["p"]'
expect_exit 0 worch refresh

STEP="R5 (a) a run with no change prints nothing and ends after N polls"
expect_exit 0 worch wait --interval 0.05 --polls 3
[ ! -s "$TMP/out" ] || fail "a quiet run printed: $(cat "$TMP/out")"
wjcheck 's.get("wait_owner") is None'
pass

STEP="R5 (b) a rise to slowed writes the mode and slots.max, adds an event, and exits with one line"
echo slowed >"$TMP/level"
expect_exit 0 worch wait --interval 0.05 --polls 5
[ "$(wc -l <"$TMP/out" | tr -d ' ')" -eq 1 ] || fail "not one line: $(cat "$TMP/out")"
grep -q '^wake usage -: ' "$TMP/out" || fail "bad wake line: $(cat "$TMP/out")"
wjcheck 's["pace"]["mode"] == "slowed" and s["pace"]["slots"]["max"] == 1 and s["pace"]["slots"]["busy"] == 2'
wjcheck 'any("slowed" in e["text"] for e in s["events"])'
worch board --json >"$TMP/board.json"
python3 - "$TMP/board.json" <<'PY' || fail "no mode event on the board JSON"
import json, sys
d = json.load(open(sys.argv[1]))
assert any("slowed" in e["text"] for e in d["events"]), d.get("events")
PY
pass

STEP="R5 (b) a run that stays at slowed keeps running with no line"
expect_exit 0 worch wait --interval 0.05 --polls 3
[ ! -s "$TMP/out" ] || fail "a re-check printed: $(cat "$TMP/out")"
pass

STEP="R5 (c) a reset writes the mode and the restored slots.max and exits with one line"
echo normal >"$TMP/level"
expect_exit 0 worch wait --interval 0.05 --polls 5
grep -q '^wake usage -: reset' "$TMP/out" || fail "no reset line: $(cat "$TMP/out")"
wjcheck 's["pace"]["mode"] == "normal" and s["pace"]["slots"]["max"] == 3'
pass

STEP="R5 (d) a queued merge goes through when its checks pass, with no exit and no line"
seed_pr 951 9519519519519519519519519519519519519519
expect_exit 0 worch wait --interval 0.05 --polls 3
[ ! -s "$TMP/out" ] || fail "a routine merge printed: $(cat "$TMP/out")"
grep -q 'pr merge 951 --repo owner/wt --rebase --match-head-commit 9519' "$TMP/gh/calls.log" || fail "no merge for 951"
wjcheck 's["merge_queue"] == [] and s["pace"]["slots"]["busy"] == 1 and s["items"]["p"]["slot_released"] is True'
wjcheck 'any(e["item"] == "p" and "merged" in e["text"] for e in s["events"])'
pass

STEP="R5 (e) a red check exits with one line"
expect_exit 0 worch refresh
flip_pr 952 'd["statusCheckRollup"][0]["conclusion"] = "FAILURE"'
expect_exit 0 worch wait --interval 0.05 --polls 5
[ "$(wc -l <"$TMP/out" | tr -d ' ')" -eq 1 ] || fail "not one line: $(cat "$TMP/out")"
grep -q '^wake check q: ' "$TMP/out" || fail "bad wake line: $(cat "$TMP/out")"
pass

STEP="R5 (F1) a PR closed with no merge wakes once and releases its slot once"
expect_exit 0 worch refresh
flip_pr 953 'd["state"] = "CLOSED"'
expect_exit 0 worch pace set '{"slots": {"busy": 3}}'
expect_exit 0 worch wait --interval 0.05 --polls 5
grep -q '^wake closed r: ' "$TMP/out" || fail "no closed wake: $(cat "$TMP/out")"
wjcheck 's["pace"]["slots"]["busy"] == 2 and s["items"]["r"]["slot_released"] is True'
expect_exit 0 worch wait --interval 0.05 --polls 3
wjcheck 's["pace"]["slots"]["busy"] == 2'
pass

STEP="R5 (F2) a pending handoff makes wait exit with a wake send line, until it is cleared"
flip_pr 954 'd["state"] = "MERGED"'
expect_exit 0 worch finalize u
expect_exit 0 worch wait --interval 0.05 --polls 3
grep -q '^wake send u: send-to sess-u told ' "$TMP/out" || fail "no send wake: $(cat "$TMP/out")"
expect_exit 0 worch handoff clear u
expect_exit 0 worch wait --interval 0.05 --polls 3
[ ! -s "$TMP/out" ] || fail "a cleared handoff woke: $(cat "$TMP/out")"
pass

STEP="R5 (F3) an approval, a new review and a new comment each wake"
expect_exit 0 worch refresh
expect_exit 0 worch wait --interval 0.05 --polls 2
flip_pr 955 'd["reviewDecision"] = "APPROVED"; d["mergeStateStatus"] = "CLEAN"'
expect_exit 0 worch wait --interval 0.05 --polls 4
grep -q '^wake review v: approved' "$TMP/out" || fail "no approval wake: $(cat "$TMP/out")"
flip_pr 955 'd["comments"] = [{"id": "c1", "author": {"login": "rev"}, "createdAt": "2026-11-24T11:00:00Z", "body": "Why this?"}]'
expect_exit 0 worch wait --interval 0.05 --polls 4
grep -q '^wake comment v: rev ' "$TMP/out" || fail "no comment wake: $(cat "$TMP/out")"
flip_pr 955 'd["comments"].append({"id": "c2", "author": {"login": "imp"}, "createdAt": "2026-11-24T11:05:00Z", "body": "own"})'
expect_exit 0 worch wait --interval 0.05 --polls 3
[ ! -s "$TMP/out" ] || fail "the PR author's own comment woke: $(cat "$TMP/out")"
flip_pr 955 'd["reviews"] = [{"id": "r1", "author": {"login": "rev2"}, "state": "COMMENTED", "createdAt": "2026-11-24T11:10:00Z", "body": "Rename."}]'
expect_exit 0 worch wait --interval 0.05 --polls 4
grep -q '^wake review v: rev2 ' "$TMP/out" || fail "no review wake: $(cat "$TMP/out")"
pass

STEP="R5 an implementer's question wakes as inbox"
expect_exit 0 worch wait --interval 0.05 --polls 2
expect_exit 0 worch ask u "Which file owns the shared type?"
expect_exit 0 worch wait --interval 0.05 --polls 4
grep -q '^wake inbox u: ' "$TMP/out" || fail "no inbox wake: $(cat "$TMP/out")"
expect_exit 0 worch wait --interval 0.05 --polls 3
[ ! -s "$TMP/out" ] || fail "the same entry woke twice: $(cat "$TMP/out")"
pass

STEP="R5 (F4) a second wait replaces the first by its owner token, and a superseded poller writes nothing"
python3 "$ORCH_PY" --orch wtr wait --interval 0.1 --polls 600 >"$TMP/first.out" 2>&1 &
FIRST=$!
for _ in $(seq 1 50); do
  python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("wait_owner") else 1)' "$WD/orchestrator.json" && break
  sleep 0.1
done
wjcheck 's["wait_owner"]["pid"] == '"$FIRST"
expect_exit 0 worch wait --interval 0.05 --polls 2
sleep 0.5
kill -0 "$FIRST" 2>/dev/null && { kill "$FIRST"; fail "the first wait still runs after a second wait started"; }
wait "$FIRST" 2>/dev/null
# A foreign owner token: the poller sees it, exits with no write, and leaves the owner alone.
python3 "$ORCH_PY" --orch wtr wait --interval 0.1 --polls 600 >"$TMP/third.out" 2>&1 &
THIRD=$!
for _ in $(seq 1 50); do
  python3 -c 'import json,sys; sys.exit(0 if json.load(open(sys.argv[1])).get("wait_owner") else 1)' "$WD/orchestrator.json" && break
  sleep 0.1
done
python3 - "$WD/orchestrator.json" <<'PY'
import json, sys
p = sys.argv[1]
s = json.load(open(p)); s["wait_owner"] = {"token": "foreign", "pid": 1}
json.dump(s, open(p, "w"))
PY
for _ in $(seq 1 50); do kill -0 "$THIRD" 2>/dev/null || break; sleep 0.1; done
kill -0 "$THIRD" 2>/dev/null && { kill "$THIRD"; fail "a superseded poller kept running"; }
wait "$THIRD" 2>/dev/null
wjcheck 's["wait_owner"]["token"] == "foreign"'
[ ! -s "$TMP/third.out" ] || fail "a superseded poller printed: $(cat "$TMP/third.out")"
pass

# ---------------------------------------------------------------- wake filter (p4)
forch() { python3 "$ORCH_PY" --orch flt "$@"; }
FD="$CREW_RECORD_ROOT/orchestrators/flt"
fjcheck() {
  python3 "$ORCH_PY" --orch flt show >"$TMP/fshow.json" || fail "show failed"
  python3 - "$TMP/fshow.json" "$1" <<'PYF2' || fail "check is false: $1"
import json, sys
s = json.load(open(sys.argv[1]))
sys.exit(0 if eval(sys.argv[2]) else 1)
PYF2
}
rm -f "$TMP/level"
expect_exit 0 forch init
for i in i1 i2 s1; do expect_exit 0 forch item add $i --title "Filter $i" --repo owner/fl; done
n=961; for i in i1 i2 s1; do expect_exit 0 forch item $i pr $n; n=$((n + 1)); done
expect_exit 0 forch item i1 set launch '{"session_name": "i1", "worktree": "/x/i1"}'
expect_exit 0 forch item i2 set launch '{"session_name": "i2", "worktree": "/x/i2"}'
expect_exit 0 forch item s1 set subagent '{"name": "sub-s1", "model": "sonnet"}'
seed_pr 961 9619619619619619619619619619619619619619
seed_pr 962 9629629629629629629629629629629629629629 PENDING
seed_pr 963 9639639639639639639639639639639639639639
expect_exit 0 forch merge i2 --ready "ready 9629629: ok" --when-green
fjcheck 's["merge_queue"] == ["i2"]'
expect_exit 0 forch refresh
expect_exit 0 forch wait --interval 0.05 --polls 2

STEP="p4 a red check and a new comment on an implementer item wake nobody and show as board events"
flip_pr 961 'd["statusCheckRollup"][0]["conclusion"] = "FAILURE"; d["comments"] = [{"id": "c9", "author": {"login": "rev"}, "createdAt": "2026-11-24T11:00:00Z", "body": "Nit."}]'
expect_exit 0 forch wait --interval 0.05 --polls 3
[ ! -s "$TMP/out" ] || fail "an implementer item woke the orchestrator: $(cat "$TMP/out")"
fjcheck 'any(e["item"] == "i1" and e["text"].startswith("check") for e in s["events"]) and any(e["item"] == "i1" and e["text"].startswith("comment") for e in s["events"])'
forch board --json >"$TMP/board.json"
python3 - "$TMP/board.json" <<'PY' || fail "no check event on the board JSON"
import json, sys
d = json.load(open(sys.argv[1]))
assert any(e["item"] == "i1" and "check" in e["text"] for e in d["events"]), d.get("events")
PY
pass

STEP="p4 the same red check on a subagent item wakes"
expect_exit 0 forch refresh
flip_pr 963 'd["statusCheckRollup"][0]["conclusion"] = "FAILURE"'
expect_exit 0 forch wait --interval 0.05 --polls 3
grep -q '^wake check s1: ' "$TMP/out" || fail "no wake for a subagent item: $(cat "$TMP/out")"
pass

STEP="p4 a red check on an item in merge_queue still wakes"
flip_pr 962 'd["statusCheckRollup"][0]["conclusion"] = "FAILURE"; d["statusCheckRollup"][0]["status"] = "COMPLETED"'
expect_exit 0 forch wait --interval 0.05 --polls 3
grep -q '^wake check i2: ' "$TMP/out" || fail "no wake for an item in merge_queue: $(cat "$TMP/out")"
pass

# ---------------------------------------------------------------- resume of a shipped item (p4)
sorch() { python3 "$ORCH_PY" --orch shp "$@"; }
SD="$CREW_RECORD_ROOT/orchestrators/shp"
expect_exit 0 sorch init
for i in h1 h2 h3; do
  expect_exit 0 sorch item add $i --title "Shipped $i" --repo owner/sh
  expect_exit 0 sorch item $i set launch "{\"session_name\": \"$i\", \"worktree\": \"$TMP/wt/$i\", \"tab\": \"tmux:%1\", \"session_id\": \"sid-$i\"}"
done
expect_exit 0 sorch stage h1 shipped
expect_exit 0 sorch stage h2 closed
expect_exit 0 sorch stage h3 shipped
echo 'tmux:%8 name' >"$TMP/find-h1.txt"
echo 'tmux:%1 id' >"$TMP/find-h2.txt"
rm -f "$TMP/find-h3.txt"
cp "$SD/orchestrator.json" "$TMP/shp-before.json"

STEP="p4 resume --read-only finds a shipped item, writes nothing, and names the close action"
expect_exit 0 sorch resume --read-only
grep -q '^h1 close: .*tmux:%8.*close-item h1' "$TMP/out" || fail "bad h1 line: $(cat "$TMP/out")"
grep -q '^h2 close: .*close-item h2' "$TMP/out" || fail "bad h2 line: $(cat "$TMP/out")"
grep -q '^h3 close: .*gone.*close-item h3 --continue' "$TMP/out" || fail "bad h3 line: $(cat "$TMP/out")"
cmp -s "$TMP/shp-before.json" "$SD/orchestrator.json" || fail "read-only changed the record"
pass

STEP="p4 resume writes the changed launch.tab of a shipped item"
expect_exit 0 sorch resume
python3 "$ORCH_PY" --orch shp show h1 | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin)["launch"]["tab"] == "tmux:%8" else 1)' || fail "launch.tab not written"
python3 "$ORCH_PY" --orch shp show h3 | python3 -c 'import json,sys; sys.exit(0 if json.load(sys.stdin)["launch"]["tab"] == "tmux:%1" else 1)' || fail "a gone item changed its tab"
pass

# ---------------------------------------------------------------- queue wake (p4 fix round 1)
expect_exit 0 forch item add q1 --title "Filter q1" --repo owner/fl
expect_exit 0 forch item q1 pr 964
seed_pr 964 9649649649649649649649649649649649649649
expect_exit 0 forch refresh
expect_exit 0 forch wait --interval 0.05 --polls 2

STEP="p4 a PR that enters the merge queue wakes nobody and shows as a board event"
echo '{"data": {"repository": {"pullRequest": {"isInMergeQueue": true, "mergeQueueEntry": {"position": 2}}}}}' >"$TMP/gh/queue-964.json"
expect_exit 0 forch wait --interval 0.05 --polls 3
[ ! -s "$TMP/out" ] || fail "a queue entry woke the orchestrator: $(cat "$TMP/out")"
fjcheck 'any(e["item"] == "q1" and e["text"].startswith("queue") and "2" in e["text"] for e in s["events"])'
pass

STEP="p4 a PR that leaves the merge queue while it is still open wakes"
echo '{"data": {"repository": {"pullRequest": {"isInMergeQueue": false, "mergeQueueEntry": null}}}}' >"$TMP/gh/queue-964.json"
expect_exit 0 forch wait --interval 0.05 --polls 3
grep -q '^wake queue q1: left the queue' "$TMP/out" || fail "no dequeue wake: $(cat "$TMP/out")"
pass

echo "all checks passed"

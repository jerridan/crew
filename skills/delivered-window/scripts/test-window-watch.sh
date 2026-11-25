#!/bin/bash
# Seeded test of window-watch.py.
#
# usage: bash skills/delivered-window/scripts/test-window-watch.sh
#
# It builds records under a temp directory, puts a stub `gh` first in PATH,
# names a stub poll script in WINDOW_WATCH_POLL and a stub launcher in
# CREW_WINDOW_LAUNCHER, and runs the real window-watch.py, watch-step.py and
# crew-record.py. The poll interval, the quiet wait and the cap are 1, 2 and 5
# seconds. It starts no claude and makes no network call. It prints one line
# per check and exits 0 only when every check passes.

set -u
here=$(cd "$(dirname "$0")" && pwd)
WW="$here/window-watch.py"
REC_PY="$here/../../project-lead/scripts/crew-record.py"
HOOK="$here/../../../hooks/session-end.py"
T=$(mktemp -d)
fails=0
total=0

kill_watchers() {
  for s in "$T"/records/*/state.json; do
    [ -e "$s" ] || continue
    pid=$(python3 -c 'import json,sys; w=(json.load(open(sys.argv[1])).get("run") or {}).get("window") or {}; print((w.get("watcher") or {}).get("pid") or "")' "$s" 2>/dev/null)
    [ -n "$pid" ] && kill -9 "$pid" 2>/dev/null
  done
}
cleanup() { kill_watchers; rm -rf "$T"; }
trap cleanup EXIT

export STUB_DIR="$T/stub"
export CREW_RECORD_ROOT="$T/records"
export HOME="$T/home"
export CREW_WINDOW_STALE=3600
mkdir -p "$T/bin" "$STUB_DIR" "$CREW_RECORD_ROOT" "$HOME" "$T/repo"
REPO="$T/repo"
RECS="$CREW_RECORD_ROOT"

cat > "$T/bin/gh" <<'STUB'
#!/bin/bash
D=$STUB_DIR
echo "$*" >> "$D/gh.log"
case "$*" in
  "api user"*) echo me; exit 0 ;;
  "pr view"*) cat "$D/pr.json"; exit 0 ;;
esac
exit 1
STUB
# The poll stub. `once` prints each line of <stub>/<record>/pr-lines. A line of
# a kind that the cursor remembers stays until the record's seen_ids holds its
# id; a `merged` or `closed` line stays for good, as the real poll prints it on
# every fire; every other line goes at once. `deploy-once` prints and drops
# each line of deploy-lines.
cat > "$T/poll.sh" <<'STUB'
#!/bin/bash
rec=$1; mode=$2; n=$(basename "$rec"); D=$STUB_DIR/$n
mkdir -p "$D"
echo "$mode" >> "$D/poll.log"
case "$mode" in
  once)
    f=$D/pr-lines
    mv "$f" "$f.snap" 2>/dev/null
    seen=$(python3 -c 'import json,sys; print(" ".join(str(i) for i in ((json.load(open(sys.argv[1])).get("run") or {}).get("watch") or {}).get("seen_ids", [])))' "$rec/state.json")
    if [ -e "$f.snap" ]; then
      while IFS= read -r line; do
        [ -n "$line" ] || continue
        # The real poll drops crew's own replies, which end in the pr-review marker.
        case "$line" in *'<!-- pr-review: '*) continue ;; esac
        kind=${line%% *}; id=${line#* }; id=${id%% *}
        case "$kind" in
          review|review-comment|comment|check|push)
            case " $seen " in *" $id "*) continue ;; esac
            echo "$line"; echo "$line" >> "$f" ;;
          merged|closed) echo "$line"; echo "$line" >> "$f" ;;
          *) echo "$line" ;;
        esac
      done < "$f.snap"
      rm -f "$f.snap"
    fi
    echo "isDraft=true" ;;
  deploy-once)
    f=$D/deploy-lines
    mv "$f" "$f.snap" 2>/dev/null && { cat "$f.snap"; rm -f "$f.snap"; } ;;
esac
exit 0
STUB
# The launcher stub: window, stop and find, each logged.
cat > "$T/launcher.sh" <<'STUB'
#!/bin/bash
D=$STUB_DIR
echo "$*" >> "$D/launcher.log"
case "$1" in
  window)
    name=''; pf=''; model=''; cwd=''
    while [ $# -gt 1 ]; do
      case "$2" in
        --name) name=$3 ;; --prompt-file) pf=$3 ;; --model) model=$3 ;; --cwd) cwd=$3 ;;
      esac
      shift
    done
    [ -e "$D/launch-fail-${name%-w*}" ] && { echo "launcher: tmux opened no window" >&2; exit 6; }
    [ -e "$D/launch-fail10-${name%-w*}" ] && { echo "launcher: no claude process started on the tab iterm2:X (tty ttys001) within 60 seconds" >&2; exit 10; }
    cp "$pf" "$D/prompt-$name.md"
    n=$(( $(cat "$D/pane-n" 2>/dev/null || echo 0) + 1 )); echo "$n" > "$D/pane-n"
    printf '{"session_name": "%s", "model": "%s", "terminal": "tmux", "tab": "tmux:%%%s", "tab_group": "crew", "session_id": "uuid-%s", "cwd": "%s"}\n' "$name" "$model" "$n" "$n" "$cwd" ;;
  stop) echo "stopped $2" ;;
  find) cat "$D/find-$2" 2>/dev/null ;;
esac
exit 0
STUB
chmod +x "$T/bin/gh" "$T/poll.sh" "$T/launcher.sh"
export PATH="$T/bin:$PATH"
export WINDOW_WATCH_POLL="$T/poll.sh"
export CREW_WINDOW_LAUNCHER="$T/launcher.sh"
printf '{"isDraft":true,"createdAt":"2026-01-01T00:00:00Z","headRefOid":"h1"}\n' > "$STUB_DIR/pr.json"
: > "$STUB_DIR/launcher.log"

chk() { # label got want
  total=$((total + 1))
  if [ "$2" = "$3" ]; then echo "ok   $1"; else
    fails=$((fails + 1)); echo "FAIL $1"; printf '     got:  %s\n     want: %s\n' "$2" "$3"
  fi
}
yes_if() { # label command...: ok when the command succeeds
  label=$1; shift
  if "$@" > /dev/null 2>&1; then chk "$label" yes yes; else chk "$label" no yes; fi
}
waitfor() { # seconds command: poll until it succeeds
  local end=$((SECONDS + $1)); shift
  while [ $SECONDS -lt $end ]; do eval "$@" > /dev/null 2>&1 && return 0; sleep 0.3; done
  return 1
}
# sj <record> <dotted path under run>: the JSON value, null when absent.
sj() {
  python3 - "$RECS/$1/state.json" "$2" <<'PY'
import json, sys
s = json.load(open(sys.argv[1])).get("run") or {}
for k in sys.argv[2].split("."):
    s = s.get(k) if isinstance(s, dict) else None
print(json.dumps(s, sort_keys=True))
PY
}
nwin() { awk -v p="window --name $1-w" 'index($0, p) == 1 { c++ } END { print c + 0 }' "$STUB_DIR/launcher.log" 2>/dev/null; }
nlines() { if [ -e "$1" ]; then grep -c . "$1"; else echo 0; fi; }
pid_of() { sj "$1" window.watcher.pid; }
alive() { [ -n "$1" ] && [ "$1" != null ] && kill -0 "$1" 2>/dev/null; }
rec() { python3 "$REC_PY" "$@"; }
emit() { printf '%s\n' "$2" >> "$STUB_DIR/$1/pr-lines"; }
emit_deploy() { printf '%s\n' "$2" >> "$STUB_DIR/$1/deploy-lines"; }
ww() { out=$(python3 "$WW" "$@" 2>"$T/err"); rc=$?; err=$(cat "$T/err"); }
TS=2026-01-01T00:00:01Z

# mkrec <name>: a delivered goal run with a PR, a charter and a hand-over brief.
mkrec() {
  mkdir -p "$STUB_DIR/$1"
  R="$RECS/$1"
  rec "$R" init "goal $1" "$1" "sid-$1" > /dev/null
  rec "$R" deliverable add '{"id":"deliverable-1","state":"draft-pr-opened","pr_url":"https://github.com/o/r/pull/7"}' > /dev/null
  rec "$R" run set repo "\"$REPO\"" > /dev/null
  rec "$R" run state delivered > /dev/null
  echo "charter text" > "$R/charter.md"
  printf '# Handover\n\n## Findings not on GitHub\n\nnone\n' > "$R/handover.md"
}

# ---- start, the record fields, and a second start
mkrec main
R="$RECS/main"
ww start "$R" --poll 1 --quiet 2 --cap 5
chk 'start exits 0' "$rc" 0
P1=$(pid_of main)
yes_if 'start: run.window.watcher.pid is a live process' alive "$P1"
chk 'start: model defaults to opus' "$(sj main window.model)" '"opus"'
chk 'start: poll, quiet and cap are the flag values' "$(sj main window.poll) $(sj main window.quiet) $(sj main window.cap)" '1 2 5'
chk 'start: hold is false and intake is true' "$(sj main window.hold) $(sj main window.intake)" 'false true'
chk 'start: session null, sessions empty, own empty, awaiting null' \
  "$(sj main window.session) $(sj main window.sessions) $(sj main window.own) $(sj main window.awaiting)" \
  'null [] {"pushes": [], "ready": []} null'
yes_if 'start: watcher.started_at is a stamp' python3 -c 'import json,sys,re; w=json.loads(sys.argv[1]); sys.exit(0 if re.fullmatch(r"20\d\d-.*Z", w["started_at"]) else 1)' "$(sj main window.watcher)"
yes_if 'start: the window directory has watcher.log, pending.jsonl and inbox.jsonl' \
  bash -c "[ -e '$R/window/watcher.log' ] && [ -e '$R/window/pending.jsonl' ] && [ -e '$R/window/inbox.jsonl' ]"
ww start "$R" --poll 1 --quiet 2 --cap 5
chk 'start on a live watcher prints already running, exits 0' "$out/$rc" 'already running/0'
chk 'start on a live watcher starts no second process' "$(pid_of main)" "$P1"

# ---- R3: every new field is written through crew-record.py and read back
rec "$R" run set window.awaiting '{"round":"r1","asked_at":"2026-01-01T00:00:00Z"}' > /dev/null
chk 'round trip: awaiting' "$(sj main window.awaiting)" '{"asked_at": "2026-01-01T00:00:00Z", "round": "r1"}'
rec "$R" run set window.awaiting null > /dev/null
rec "$R" run set window.own.pushes '["aaa1111"]' > /dev/null
chk 'round trip: own.pushes' "$(sj main window.own.pushes)" '["aaa1111"]'
rec "$R" run set window.own.ready '["2026-01-01T00:00:00Z"]' > /dev/null
chk 'round trip: own.ready' "$(sj main window.own.ready)" '["2026-01-01T00:00:00Z"]'
rec "$R" run set window.own.pushes '[]' > /dev/null
rec "$R" run set window.own.ready '[]' > /dev/null
rec "$R" run set window.model '"sonnet"' > /dev/null
chk 'round trip: model' "$(sj main window.model)" '"sonnet"'
rec "$R" run set window.model '"opus"' > /dev/null
rec "$R" run set window.session '{"name":"x","handle":"tmux:%1","started_at":"2026-01-01T00:00:00Z","stale_at":null}' > /dev/null
chk 'round trip: session name, handle and stale_at' "$(sj main window.session.name) $(sj main window.session.handle) $(sj main window.session.stale_at)" '"x" "tmux:%1" null'
rec "$R" run set window.session null > /dev/null
chk 'round trip: the watcher and its other fields survive these writes' "$(pid_of main) $(sj main window.poll)" "$P1 1"

# ---- 1 to 3: no session
sleep 4
chk 'check 1: an idle period starts no session' "$(nwin main)" 0
yes_if 'the watcher beats: watcher.json holds a heartbeat that moves' python3 -c '
import json, sys, time
p = sys.argv[1]
a = json.load(open(p))["heartbeat_at"]; time.sleep(1.5); b = json.load(open(p))["heartbeat_at"]
sys.exit(0 if a != b else 1)' "$R/window/watcher.json"
chk 'the heartbeat is not in state.json' "$(sj main window.watcher.heartbeat_at)" null
emit main "queued 7 - $TS the PR entered the merge queue"
emit main "isDraft=true"
sleep 3
chk 'check 2: a queued line and a passing check (no line) start no session' "$(nwin main)" 0
rec "$R" run set window.own.pushes '["abc1234"]' > /dev/null
emit main "push abc1234def me $TS new head"
sleep 3
chk 'check 3: a self push starts no session' "$(nwin main)" 0
chk 'the cursor followed the self push' "$(sj main watch.head)" '"abc1234def"'

# ---- 4: one burst, one session
for i in $(seq 1 12); do emit main "review-comment $((100 + i)) alice $TS src/f.py:$i comment $i"; done
sleep 1
for i in 1 2 3; do emit main "comment $((200 + i)) bob $TS text $i"; done
waitfor 15 "[ \"\$(nwin main)\" -ge 1 ]"
sleep 4
chk 'check 4: 12 threads and 3 comments inside the quiet wait start exactly one session' "$(nwin main)" 1
chk 'check 4: its event file holds the 15 events, each once' "$(nlines "$R/window/events-1.jsonl") $(sort -u "$R/window/events-1.jsonl" | grep -c .)" '15 15'
chk 'the pending file is empty after the start' "$(nlines "$R/window/pending.jsonl")" 0
chk 'the session is live with a name, a handle and an id' \
  "$(sj main window.session.name) $(sj main window.session.status) $(sj main window.session.handle) $(sj main window.session.session_id)" \
  '"main-w1" "live" "tmux:%1" "uuid-1"'
chk 'the launcher got the run repo, the model and the prompt file' \
  "$(grep '^window --name main-w1 ' "$STUB_DIR/launcher.log" | sed "s#$R#REC#g; s#$REPO#REPO#")" \
  'window --name main-w1 --cwd REPO --prompt-file REC/window/prompt-1.md --model opus'
yes_if 'every event line is the JSON shape of the spec' python3 -c '
import json, sys
for l in open(sys.argv[1]):
    e = json.loads(l)
    assert set(e) == {"at", "source", "line", "from"}, e
    assert e["source"] in ("pr", "deploy", "inbox")
' "$R/window/events-1.jsonl"

# ---- 9: the prompt and the files it names
python3 - "$R" "$R/window/prompt-1.md" "$WW" > "$T/size.out" <<'PY'
import os, re, sys
rec, prompt = sys.argv[1], sys.argv[2]
text = open(prompt).read()
paths = re.findall(r"(?:^|[\s`\"'(])(/[^\s`\"')]*)", text)
# The one path outside the record dir is the watcher script, which the prompt gives so the session need not find it.
script = sys.argv[3]
outside = [p for p in paths if not (p == rec or p.startswith(rec + "/") or p.rstrip(".,;:") == script)]
total = os.path.getsize(prompt)
for p in set(paths):
    p = p.rstrip(".,;:")
    # The session runs the watcher script and does not read it into its context.
    if os.path.isfile(p) and p != script:
        total += os.path.getsize(p)
print(total)
print(len(paths))
print(" ".join(outside))
PY
BYTES=$(sed -n 1p "$T/size.out")
echo "prompt bytes (prompt plus every file it names): $BYTES"
chk 'check 9: the prompt names paths, and each is under the record dir (the watcher script is the one exception)' "$([ "$(sed -n 2p "$T/size.out")" -gt 0 ] && [ -z "$(sed -n 3p "$T/size.out")" ] && echo yes)" yes
chk 'check 9: the prompt and every file it names total at most 120,000 bytes' "$([ "$BYTES" -gt 0 ] && [ "$BYTES" -le 120000 ] && echo yes)" yes
yes_if 'the prompt invokes crew:delivered-window and names the session' bash -c "grep -q 'crew:delivered-window' '$R/window/prompt-1.md' && grep -q 'main-w1' '$R/window/prompt-1.md'"
yes_if 'the prompt names the event file' grep -q "$R/window/events-1.jsonl" "$R/window/prompt-1.md"

# ---- 5: an event during a live session
emit main "review 301 carol $TS COMMENTED please look"
sleep 3
chk 'check 5: the live session holds the session count at one' "$(nwin main)" 1
ww next "$R" --session other
chk 'next with a name that holds no slot is refused (exit 3)' "$rc" 3
ww next "$R" --session main-w1
chk 'check 5: next returns the event that arrived during the live session' "$(printf '%s\n' "$out" | grep -c '"review 301')" 1
chk 'check 5: next moves it into the live session event file' "$(nlines "$R/window/events-1.jsonl")" 16
ww next "$R" --session main-w1
chk 'a second next prints nothing' "$out" ''
ww done "$R" --session other
chk 'done with a name that holds no slot is refused (exit 3)' "$rc" 3

# ---- done closes the tab and frees the slot
ww done "$R" --session main-w1
chk 'done exits 0' "$rc" 0
waitfor 8 "[ \"\$(sj main window.session)\" = null ]"
chk 'the watcher closes the tab with the stop of the launcher, by handle' "$(grep -c '^stop tmux:%1$' "$STUB_DIR/launcher.log")" 1
chk 'the ended session moves to sessions, and the slot is free' "$(sj main window.session) $(sj main window.sessions | python3 -c 'import json,sys; s=json.load(sys.stdin); print(len(s), s[0]["name"], bool(s[0]["ended_at"]))')" 'null 1 main-w1 True'

# ---- 6: say starts a session
ww say "$R" --from person "merge it"
chk 'say exits 0' "$rc" 0
waitfor 12 "[ \"\$(nwin main)\" -ge 2 ]"
sleep 3
chk 'check 6: say starts one session' "$(nwin main)" 2
chk 'the inbox line is an event with source inbox and the sender' \
  "$(python3 -c 'import json,sys; e=json.loads(open(sys.argv[1]).readline()); print(e["source"], e["from"], e["line"])' "$R/window/events-2.jsonl")" 'inbox person merge it'
ww done "$R" --session main-w2
waitfor 8 "[ \"\$(sj main window.session)\" = null ]"

# ---- 7: ensure restarts a dead watcher
ww ensure "$R"
chk 'ensure on a live watcher prints alive' "$out" alive
OLD=$(pid_of main)
kill -9 "$OLD"
sleep 0.5
ww ensure "$R"
chk 'check 7: ensure after a kill exits 0 and prints restarted' "$out/$rc" 'restarted/0'
NEW=$(pid_of main)
yes_if 'check 7: the new watcher is alive, with a new pid' bash -c "[ '$NEW' != '$OLD' ] && kill -0 '$NEW'"
emit main "review 401 dave $TS COMMENTED after the restart"
waitfor 12 "[ \"\$(nwin main)\" -ge 3 ]"
chk 'check 7: the restarted watcher starts a session for a new event' "$(nwin main)" 3
ww done "$R" --session main-w3
waitfor 8 "[ \"\$(sj main window.session)\" = null ]"

# ---- 8: stop turns intake off, done --final ends the watcher
ww claim "$R" --session claimer
chk 'claim takes the free slot' "$rc" 0
ww claim "$R" --session second
chk 'a second claim exits 3' "$rc" 3
ww stop "$R" --session second
chk 'stop with a name that holds no slot is refused (exit 3)' "$rc" 3
ww stop "$R" --session claimer
chk 'stop by the holder exits 0' "$rc" 0
ww status "$R"
chk 'status prints intake: off after stop' "$(printf '%s\n' "$out" | grep -c '^intake: off$')" 1
chk 'status prints hold: false' "$(printf '%s\n' "$out" | grep -c '^hold: false$')" 1
emit main "review 501 erin $TS COMMENTED while intake is off"
sleep 3
chk 'with intake off the watcher queues nothing and starts nothing' "$(nwin main) $(nlines "$R/window/pending.jsonl")" '3 0'
ww ensure "$R"
ww status "$R"
chk 'ensure never turns intake on' "$(printf '%s\n' "$out" | grep -c '^intake: off$')" 1
ww start "$R" --poll 1 --quiet 2 --cap 5
chk 'start on a live watcher with intake off prints intake on, exits 0' "$out/$rc" 'intake on/0'
ww stop "$R" --session claimer
ww done "$R" --session claimer --final
waitfor 10 "! kill -0 $(pid_of main) 2>/dev/null"
chk 'check 8: the watcher exits after stop and done --final' "$(kill -0 "$(pid_of main)" 2>/dev/null && echo alive || echo gone)" gone
chk 'the final done leaves the record with no watcher pid' "$(pid_of main)" null

# ---- 10: the first cursor, the project lead's own acts
printf '{"isDraft":false,"createdAt":"2026-01-01T00:00:00Z","headRefOid":"hh1"}\n' > "$STUB_DIR/pr.json"
mkrec cur
ww start "$RECS/cur" --poll 1 --quiet 2 --cap 5
chk 'check 10: the first cursor is the PR at the time of start (head, draft, seen_ids)' "$(sj cur watch.head) $(sj cur watch.draft) $(sj cur watch.seen_ids)" '"hh1" false []'
rec "$RECS/cur" run set window.own.ready "[\"$TS\"]" > /dev/null
emit cur "ready 7 - $TS the PR left draft"
sleep 3
chk 'check 10: the project lead own ready flip starts no session' "$(nwin cur)" 0
emit cur "push 9990000 frank $TS new head"
waitfor 12 "[ \"\$(nwin cur)\" -ge 1 ]"
chk 'a push by someone else starts a session' "$(nwin cur)" 1
printf '{"isDraft":true,"createdAt":"2026-01-01T00:00:00Z","headRefOid":"h1"}\n' > "$STUB_DIR/pr.json"

# ---- 11: the merge, the deploy setup and a deploy timeout
mkrec dep
ww start "$RECS/dep" --poll 1 --quiet 2 --cap 5
emit dep "merged 7 - $TS the PR merged"
waitfor 12 "[ \"\$(nwin dep)\" -ge 1 ]"
sleep 4
chk 'a merged line starts one session, and the merge is not queued again' "$(nwin dep) $(nlines "$RECS/dep/window/events-1.jsonl")" '1 1'
chk 'the merge wrote run.deploy (setup only) and merged_seen' "$(sj dep deploy.source) $([ "$(sj dep window.merged_seen)" != null ] && echo seen)" '"default" seen'
ww done "$RECS/dep" --session dep-w1
waitfor 8 "[ \"\$(sj dep window.session)\" = null ]"
emit_deploy dep "deploy-timeout 7 - $TS no deploy seen 180 minutes after the watch started"
waitfor 12 "[ \"\$(nwin dep)\" -ge 2 ]"
sleep 4
chk 'check 11: a deploy timeout starts one session' "$(nwin dep)" 2
chk 'the deploy line is recorded as the end of the deploy watch' "$(sj dep deploy.ended)" '"deploy-timeout"'
ww done "$RECS/dep" --session dep-w2

# ---- hold and release
mkrec hold
ww start "$RECS/hold" --hold --poll 1 --quiet 2 --cap 5
ww status "$RECS/hold"
chk 'status prints hold: true under --hold' "$(printf '%s\n' "$out" | grep -c '^hold: true$')" 1
rec "$RECS/hold" run set window.own.pushes '["77aa777"]' > /dev/null
emit hold "push 77aa777bb me $TS new head"
emit hold "review 601 gina $TS CHANGES_REQUESTED fix this"
sleep 5
chk 'hold: events queue and start no session' "$(nwin hold) $(nlines "$RECS/hold/window/pending.jsonl")" '0 1'
ww release "$RECS/hold"
chk 'release exits 0' "$rc" 0
waitfor 12 "[ \"\$(nwin hold)\" -ge 1 ]"
sleep 3
chk 'release: the queued events start exactly one session' "$(nwin hold) $(nlines "$RECS/hold/window/events-1.jsonl")" '1 1'

# ---- a launch that fails keeps its burst and retries
mkrec lf
: > "$STUB_DIR/launch-fail-lf"
ww start "$RECS/lf" --poll 1 --quiet 2 --cap 5
emit lf "review 701 hank $TS COMMENTED launch me"
waitfor 12 "[ \"\$(nwin lf)\" -ge 2 ]"
chk 'a failed launch is retried' "$([ "$(nwin lf)" -ge 2 ] && echo yes)" yes
chk 'a failed launch keeps the session as launching, with its events file' "$(sj lf window.session.status) $(nlines "$RECS/lf/window/events-1.jsonl")" '"launching" 1'
rm -f "$STUB_DIR/launch-fail-lf"
waitfor 12 "[ \"\$(sj lf window.session.status)\" = '\"live\"' ]"
chk 'the retry makes the session live, with the same events file and no second burst' "$(sj lf window.session.status) $(sj lf window.session.name) $(nlines "$RECS/lf/window/events-1.jsonl") $(ls "$RECS"/lf/window/events-*.jsonl | wc -l | tr -d ' ')" '"live" "lf-w1" 1 1'
# Exit 10 of the launcher (no claude process started) is a failed launch as any other.
mkrec lf10
: > "$STUB_DIR/launch-fail10-lf10"
ww start "$RECS/lf10" --poll 1 --quiet 2 --cap 5
emit lf10 "review 702 ida $TS COMMENTED launch me"
waitfor 12 "[ \"\$(nwin lf10)\" -ge 2 ]"
chk 'a launch that exits 10 is retried like any failed launch' "$([ "$(nwin lf10)" -ge 2 ] && echo yes)" yes
chk 'a launch that exits 10 keeps the session as launching, with its events file' "$(sj lf10 window.session.status) $(nlines "$RECS/lf10/window/events-1.jsonl")" '"launching" 1'
rm -f "$STUB_DIR/launch-fail10-lf10"
waitfor 12 "[ \"\$(sj lf10 window.session.status)\" = '\"live\"' ]"
chk 'the retry after exit 10 makes the session live' "$(sj lf10 window.session.status)" '"live"'
chk 'the launch call of the watcher has a timeout of 300 seconds' "$(grep -c '^LAUNCH_TIMEOUT = 300$' "$here/window-watch.py")" 1
# A restart over a launching record finds the tab first.
mkrec lf2
ww start "$RECS/lf2" --poll 1 --quiet 2 --cap 5
rec "$RECS/lf2" run set window.session '{"name":"lf2-w1","status":"launching","events":"events-1.jsonl","started_at":"2026-01-01T00:00:00Z"}' > /dev/null
printf '{"at":"%s","source":"pr","line":"review 801 ivy %s COMMENTED x","from":null}\n' "$TS" "$TS" > "$RECS/lf2/window/events-1.jsonl"
echo 'tmux:%55 name' > "$STUB_DIR/find-lf2-w1"
kill -9 "$(pid_of lf2)"
ww ensure "$RECS/lf2"
waitfor 8 "[ \"\$(sj lf2 window.session.status)\" = '\"live\"' ]"
chk 'ensure over a launching record runs find and takes the live tab, with no second launch' "$(sj lf2 window.session.handle) $(nwin lf2)" '"tmux:%55" 0'

# ---- the Window model section and the flag
printf '# Machine\n\n## Window model\n\nsonnet\n\n## Other\n\nx\n' > "$T/machine.md"
printf '## Window model\n\nhaiku\n' > "$T/repo-crew.md"
mkrec m1
rec "$RECS/m1" run set standing_instructions "{\"repo\":null,\"machine\":\"$T/machine.md\"}" > /dev/null
ww start "$RECS/m1" --poll 1 --quiet 2 --cap 5
chk 'the machine Window model section sets the model' "$(sj m1 window.model)" '"sonnet"'
mkrec m2
rec "$RECS/m2" run set standing_instructions "{\"repo\":\"$T/repo-crew.md\",\"machine\":\"$T/machine.md\"}" > /dev/null
ww start "$RECS/m2" --poll 1 --quiet 2 --cap 5
chk 'the repo section wins over the machine section' "$(sj m2 window.model)" '"haiku"'
mkrec m3
rec "$RECS/m3" run set standing_instructions "{\"repo\":\"$T/repo-crew.md\",\"machine\":\"$T/machine.md\"}" > /dev/null
ww start "$RECS/m3" --poll 1 --quiet 2 --cap 5 --model opus-x
chk 'the --model flag wins over both sections' "$(sj m3 window.model)" '"opus-x"'

# ---- a stale session is reported, not killed
printf '#!/bin/bash\necho "$*" >> "$STUB_DIR/orch.log"\n' > "$T/orch.sh"
chmod +x "$T/orch.sh"
export CREW_WINDOW_ORCH="$T/orch.sh"
mkrec stale
rec "$RECS/stale" run set orchestrator '{"name":"orchS","item":"itS"}' > /dev/null
CREW_WINDOW_STALE=2 ww start "$RECS/stale" --poll 1 --quiet 2 --cap 5
emit stale "review 901 jo $TS COMMENTED live and silent"
waitfor 12 "[ \"\$(sj stale window.session.status)\" = '\"live\"' ]"
waitfor 15 "[ \"\$(sj stale window.session.stale_at)\" != null ]"
chk 'stale: a live session with no record write past the cap gets session.stale_at' "$([ "$(sj stale window.session.stale_at)" != null ] && echo yes)" yes
chk 'stale: watcher.log holds a line that names the session' "$(grep -c 'stale-w1\|stale.*is stale' "$RECS/stale/window/watcher.log" | awk '{print ($1 > 0) ? "yes" : "no"}')" yes
emit stale "review 902 jo $TS COMMENTED a second burst"
sleep 5
chk 'stale: no new session starts while that tab lives, and the event waits in pending' "$(nwin stale) $(nlines "$RECS/stale/window/pending.jsonl")" '1 1'
ww status "$RECS/stale"
chk 'stale: status prints stale_at' "$(printf '%s\n' "$out" | grep -c '^stale_at: ')" 1
chk 'stale: the orchestrator gets one ask line that names the item and the tab' \
  "$(grep -c '^--orch orchS ask itS .*tmux:%' "$STUB_DIR/orch.log") $(wc -l < "$STUB_DIR/orch.log" | tr -d ' ')" '1 1'
unset CREW_WINDOW_ORCH

# ---- item 1: the merge sets up the deploy poll from the winning Deploy section
printf '# Repo\n\n## Deploy\n\nnone\n' > "$T/d-none.md"
printf '# Machine\n\n## Deploy\n\nmanual\n' > "$T/d-manual.md"
printf '## Deploy\n\n- environment: staging\n- timeout: 45\n' > "$T/d-env.md"
printf '## Deploy\n\n- workflow: Ship it\n' > "$T/d-wf.md"
printf '## Deploy\n\n- environment: other\n' > "$T/d-other.md"
dep_case() { # name repo-file machine-file [charter-line]
  local repo=null machine=null
  [ -n "$2" ] && repo="\"$2\""
  [ -n "$3" ] && machine="\"$3\""
  mkrec "$1"
  rec "$RECS/$1" run set standing_instructions "{\"repo\":$repo,\"machine\":$machine}" > /dev/null
  [ -n "${4:-}" ] && echo "$4" >> "$RECS/$1/charter.md"
  ww start "$RECS/$1" --poll 1 --quiet 2 --cap 5
  emit "$1" "merged 7 - $TS the PR merged"
}
dep_case dnone "$T/d-none.md" ""
dep_case dmanual "" "$T/d-manual.md"
dep_case denv "$T/d-env.md" ""
dep_case dwf "" "$T/d-wf.md"
dep_case ddef "" ""
dep_case drepo "$T/d-env.md" "$T/d-other.md"
dep_case dchart "$T/d-env.md" "$T/d-wf.md" "Deploy: none"
for n in dnone dmanual denv dwf ddef drepo dchart; do waitfor 15 "[ \"\$(nwin $n)\" -ge 1 ]"; done
sleep 1
chk 'deploy none: the merged line starts a session, sets up no run.deploy and records the merge' "$(nwin dnone) $(sj dnone deploy) $([ "$(sj dnone window.merged_seen)" != null ] && echo seen)" '1 null seen'
chk 'deploy manual (machine): set up no run.deploy' "$(nwin dmanual) $(sj dmanual deploy)" '1 null'
chk 'deploy environment and timeout (repo): run.deploy has them, source repo' "$(sj denv deploy.environment) $(sj denv deploy.timeout_minutes) $(sj denv deploy.source) $(sj denv deploy.workflow)" '"staging" 45 "repo" null'
chk 'deploy workflow (machine): run.deploy has the workflow, source machine' "$(sj dwf deploy.workflow) $(sj dwf deploy.source) $(sj dwf deploy.environment)" '"Ship it" "machine" null'
chk 'no Deploy section: the default signal, source default' "$(sj ddef deploy.source) $(sj ddef deploy.environment) $(sj ddef deploy.workflow) $(sj ddef deploy.timeout_minutes)" '"default" null null 180'
chk 'the repo section wins over the machine section, whole' "$(sj drepo deploy.source) $(sj drepo deploy.environment)" '"repo" "staging"'
chk 'a charter Deploy line wins over the repo and machine sections' "$(nwin dchart) $(sj dchart deploy)" '1 null'

# ---- item 2: no own-login filter on comments
mkrec cmt
ww start "$RECS/cmt" --poll 1 --quiet 2 --cap 5
emit cmt "comment 951 crew $TS a crew reply <!-- pr-review: reply -->"
sleep 4
chk 'a crew reply with the pr-review marker starts no session (the poll drops it)' "$(nwin cmt)" 0
emit cmt "comment 952 me $TS the principal wrote this"
waitfor 12 "[ \"\$(nwin cmt)\" -ge 1 ]"
chk 'a comment by the principal login starts a session' "$(nwin cmt) $(nlines "$RECS/cmt/window/events-1.jsonl")" '1 1'

# ---- item 3: the watcher own writes do not reset the stale clock
mkrec stale2
CREW_WINDOW_STALE=4 ww start "$RECS/stale2" --poll 1 --quiet 2 --cap 5
emit stale2 "review 961 jo $TS COMMENTED start"
waitfor 12 "[ \"\$(sj stale2 window.session.status)\" = '\"live\"' ]"
for i in 1 2 3 4 5 6 7 8; do emit stale2 "push cafe000$i other $TS new head"; sleep 1; done
# The stale cap is 4 s and the watcher wrote every second: the stale mark is due before the pushes end.
chk 'watcher writes during a live session do not reset the stale clock' "$([ "$(sj stale2 window.session.stale_at)" != null ] && echo yes)" yes
chk 'those writes did land: the cursor head followed the pushes' "$(sj stale2 watch.head)" '"cafe0008"'

# ---- item 4: a claim that lands while the watcher archives a done session survives
mkrec race
export CREW_WINDOW_TEST_HOLD="$T/hold-tick"
ww start "$RECS/race" --poll 1 --quiet 2 --cap 5
emit race "review 971 kay $TS COMMENTED race"
waitfor 12 "[ \"\$(sj race window.session.status)\" = '\"live\"' ]"
: > "$CREW_WINDOW_TEST_HOLD"
ww done "$RECS/race" --session race-w1
waitfor 6 "[ -e '$CREW_WINDOW_TEST_HOLD.waiting' ]"
chk 'item 4: the watcher stops at the hold point after it read the done session' "$([ -e "$CREW_WINDOW_TEST_HOLD.waiting" ] && echo yes)" yes
ww claim "$RECS/race" --session racer
chk 'item 4: a claim of the slot of a done session succeeds' "$rc" 0
rm -f "$CREW_WINDOW_TEST_HOLD"
sleep 3
chk 'item 4: the watcher archive does not erase the claim' "$(sj race window.session.name) $(sj race window.session.status)" '"racer" "live"'
chk 'item 4: the done session is archived once' "$(sj race window.sessions | python3 -c 'import json,sys; print([s["name"] for s in json.load(sys.stdin)])')" "['race-w1']"
unset CREW_WINDOW_TEST_HOLD

# ---- item 6: events that keep coming still start one session at the cap
mkrec capr
ww start "$RECS/capr" --poll 1 --quiet 3 --cap 5
t0=$SECONDS
( for i in $(seq 1 10); do emit capr "review-comment $((980 + i)) lee $TS f.py:$i keep coming"; sleep 1; done ) &
waitfor 9 "[ \"\$(nwin capr)\" -ge 1 ]"
el=$((SECONDS - t0))
wait
chk 'cap: one session starts at the cap although the quiet wait never ends' "$(nwin capr) $([ "$el" -ge 4 ] && [ "$el" -le 8 ] && echo in-range)" '1 in-range'
chk 'cap: the events after the start wait in pending, and no second session starts' "$(nwin capr) $([ "$(nlines "$RECS/capr/window/pending.jsonl")" -ge 1 ] && echo pending)" '1 pending'

# ---- say --item finds the record by run.orchestrator
mkrec orchitem
rec "$RECS/orchitem" run set orchestrator '{"name":"orch1","item":"it1"}' > /dev/null
ww say --item orch1/it1 --from orch "go ahead"
chk 'say --item finds the record by run.orchestrator and writes one inbox line' "$rc $(python3 -c 'import json,sys; e=json.loads(open(sys.argv[1]).readline()); print(e["from"], e["line"])' "$RECS/orchitem/window/inbox.jsonl")" '0 orch go ahead'
ww say --item orch1/none --from orch "x"
chk 'say --item with no matching record exits 1' "$rc" 1

# ---- usage errors
ww bogus
chk 'an unknown subcommand exits 2' "$rc" 2
ww say "$RECS/orchitem" --from person
chk 'say with no text exits 2' "$rc" 2
ww start "$T/no-such-record"
chk 'start on a missing record exits 1' "$rc" 1

# ---- F1: parallel writers lose no write
mkrec lock
for i in $(seq 1 20); do rec "$RECS/lock" run set "locktest.k$i" "$i" > /dev/null & done
wait
chk 'F1: 20 parallel crew-record.py writes all land' "$(python3 -c 'import json,sys; print(len(json.load(open(sys.argv[1]))["run"]["locktest"]))' "$RECS/lock/state.json")" 20

# ---- a closed session leaves a delivered run delivered
HR="$T/hookroot"; mkdir -p "$HR"
python3 "$REC_PY" "$HR/dl" init g dl "sid-hook" > /dev/null
python3 "$REC_PY" "$HR/dl" run state delivered > /dev/null
python3 "$REC_PY" "$HR/ac" init g ac "sid-hook" > /dev/null
echo '{"session_id": "sid-hook"}' | CREW_RECORD_ROOT="$HR" python3 "$HOOK"
chk 'a closed project-lead session leaves a delivered run delivered' "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["run"]["run_state"])' "$HR/dl/state.json")" delivered
python3 "$REC_PY" "$HR/held" init g held "sid-held" > /dev/null
python3 "$REC_PY" "$HR/held" run state delivered > /dev/null
python3 "$REC_PY" "$HR/held" run set window.hold true > /dev/null
python3 "$REC_PY" "$HR/rel" init g rel "sid-held" > /dev/null
python3 "$REC_PY" "$HR/rel" run state delivered > /dev/null
python3 "$REC_PY" "$HR/rel" run set window.hold false > /dev/null
python3 "$REC_PY" "$HR/other" init g other "sid-other" > /dev/null
python3 "$REC_PY" "$HR/other" run state delivered > /dev/null
python3 "$REC_PY" "$HR/other" run set window.hold true > /dev/null
echo '{"session_id": "sid-held"}' | CREW_RECORD_ROOT="$HR" python3 "$HOOK"
chk 'item 5: a held delivered run goes interrupted when its project lead session ends' "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["run"]["run_state"])' "$HR/held/state.json")" interrupted
chk 'item 5: a released delivered run stays delivered' "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["run"]["run_state"])' "$HR/rel/state.json")" delivered
chk 'item 5: a held run of another session is not touched' "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["run"]["run_state"])' "$HR/other/state.json")" delivered
chk 'the hook still marks an active run interrupted' "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["run"]["run_state"])' "$HR/ac/state.json")" interrupted

echo "$((total - fails)) of $total checks passed"
[ "$fails" = 0 ]

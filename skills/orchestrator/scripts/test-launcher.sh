#!/bin/bash
# Seeded test of launcher.py (issue 152, R5).
#
# usage: bash skills/orchestrator/scripts/test-launcher.sh
#
# It puts stub `tmux`, `osascript`, `uv`, `claude`, `ps` and `lsof` commands
# and a logging `git` wrapper first in PATH, builds a bare origin and a checkout whose local main is older than the main
# of the origin, and runs launcher.py once per case. It makes no network call,
# opens no real tab, window or group, and starts no real `claude`. It exits 0
# only when every check passes.

set -u
here=$(cd "$(dirname "$0")" && pwd)
L="$here/launcher.py"
T=$(mktemp -d)
# Each test process that may stay has its pid in $T/pids; the exit kills it.
cleanup() { [ -e "$T/pids" ] && kill -9 $(cat "$T/pids") 2>/dev/null; rm -rf "$T"; }
trap cleanup EXIT
fails=0
total=0

mkdir -p "$T/bin" "$T/home" "$T/stub"
export STUB_DIR="$T/stub"
export HOME="$T/home"
# remove --delete-branch reads the goal records here, never the real ones.
export CREW_RECORD_ROOT="$T/records"
mkdir -p "$CREW_RECORD_ROOT"
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.com
export GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.com
unset CREW_LAUNCHER_CLAUDE TMUX TMUX_PANE TERM_PROGRAM ITERM_SESSION_ID

# tmux stub. It logs each call as one line, args joined by `|`, and each
# CLAUDECODE or CLAUDE_CODE_* variable it gets to tmux-env. Files under
# $STUB_DIR set its answers: tmux-has (the session exists), tmux-fail (new
# windows fail), tmux-kill-fail (kill-pane fails), tmux-panes (one known pane id per line),
# tmux-close-on-enter (send-keys Enter closes the pane, as when claude ends), tmux-sessions (the
# list-sessions output), tmux-clients (the list-clients output), tmux-list-panes
# (the list-panes output), tmux-ttys (`<pane id> <tty>` lines: the #{pane_tty}
# answer).
cat > "$T/bin/tmux" <<'STUB'
#!/bin/bash
D=$STUB_DIR
line=''
for a in "$@"; do line="$line$a|"; done
printf '%s\n' "$line" >> "$D/tmux.log"
env | grep -E '^(CLAUDECODE|CLAUDE_CODE_)' >> "$D/tmux-env"
target=''
prev=''
for a in "$@"; do
  case "$prev" in -t) target=$a ;; esac
  prev=$a
done
case "$1" in
  has-session) [ -e "$D/tmux-has" ] ;;
  new-session|new-window)
    [ -e "$D/tmux-fail" ] && { echo "tmux: failed" >&2; exit 1; }
    for a in "$@"; do last=$a; done
    printf '%s' "$last" > "$D/tmux-cmd"
    echo '%7' ;;
  display-message|select-window|select-pane|kill-pane|switch-client)
    grep -sqxF -- "$target" "$D/tmux-panes" 2>/dev/null || { echo "can't find pane: $target" >&2; exit 1; }
    [ "$1" = kill-pane ] && [ -e "$D/tmux-kill-fail" ] && { echo "tmux: kill failed" >&2; exit 1; }
    if [ "$1" = display-message ]; then
      case "$*" in
        *'#{pane_tty}'*) t=$(awk -v p="$target" '$1 == p {print $2}' "$D/tmux-ttys" 2>/dev/null); echo "${t:-/dev/ttys999}" ;;
        *) echo 'crew' ;;
      esac
    fi
    exit 0 ;;
  send-keys)
    grep -sqxF -- "$target" "$D/tmux-panes" 2>/dev/null || { echo "can't find pane: $target" >&2; exit 1; }
    for a in "$@"; do last=$a; done
    if [ "$last" = Enter ] && [ -e "$D/tmux-close-on-enter" ]; then
      grep -vxF -- "$target" "$D/tmux-panes" > "$D/tmux-panes.new"; mv "$D/tmux-panes.new" "$D/tmux-panes"
    fi
    exit 0 ;;
  list-panes) [ -e "$D/tmux-list-panes" ] || { echo 'no server running' >&2; exit 1; }; cat "$D/tmux-list-panes" ;;
  list-sessions) [ -e "$D/tmux-sessions" ] || { echo 'no server running' >&2; exit 1; }; cat "$D/tmux-sessions" ;;
  list-clients) cat "$D/tmux-clients" 2>/dev/null; exit 0 ;;
  *) exit 0 ;;
esac
STUB

# osascript stub. It logs its args and the script on stdin, each script to
# osa-script and all of them to osa-scripts. Files: osa-fail (every call
# fails), osa-sessions (one known iTerm2 session id per line), osa-ttys
# (`<session id> <tty>` lines: the ttys answer, and the tty of an exit).
cat > "$T/bin/osascript" <<'STUB'
#!/bin/bash
D=$STUB_DIR
line=''
for a in "$@"; do line="$line$a|"; done
printf '%s\n' "$line" >> "$D/osa.log"
cat > "$D/osa-script"
cat "$D/osa-script" >> "$D/osa-scripts"
[ -e "$D/osa-fail" ] && { echo "execution error: iTerm2 got an error" >&2; exit 1; }
case "$2" in
  start) echo 'OSA-0001' ;;
  focus|stop) if grep -sqxF -- "$3" "$D/osa-sessions" 2>/dev/null; then echo ok; else echo gone; fi ;;
  ttys) cat "$D/osa-ttys" 2>/dev/null ;;
  exit)
    if grep -sqxF -- "$3" "$D/osa-sessions" 2>/dev/null; then
      t=$(awk -v s="$3" '$1 == s {print $2}' "$D/osa-ttys" 2>/dev/null); echo "${t:-/dev/ttys998}"
    else echo gone; fi ;;
esac
exit 0
STUB

# uv stub: the iTerm2 helper. It logs its args. Files: uv-hang (it starts a
# child, writes the child pid to uv-child and hangs), uv-fail (it fails),
# uv-groups (the groups output), uv-out (its whole stdout) with uv-rc (its
# exit code, 0 when missing).
cat > "$T/bin/uv" <<'STUB'
#!/bin/bash
D=$STUB_DIR
line=''
for a in "$@"; do line="$line$a|"; done
printf '%s\n' "$line" >> "$D/uv.log"
if [ -e "$D/uv-hang" ]; then
  # uv starts its python child and hangs. The child holds no pipe of the
  # launcher, so only a kill of the process group stops it.
  sleep 30 > /dev/null 2>&1 &
  echo $! > "$D/uv-child"
  exec sleep 30
fi
if [ -e "$D/uv-out" ]; then
  cat "$D/uv-out"
  rc=$(cat "$D/uv-rc" 2>/dev/null || echo 0)
  [ "$rc" = 0 ] || echo "iterm2-tabs: RPCException: stub failure" >&2
  exit "$rc"
fi
[ -e "$D/uv-fail" ] && { echo "iterm2.rpc: connection refused" >&2; exit 1; }
group=null
prev=''
for a in "$@"; do
  case "$prev" in --group) group="\"$a\"" ;; esac
  prev=$a
done
case "$line" in
  *"|start|"*) printf '{"session_id": "ABC-123", "tab_group": %s}\n' "$group" ;;
  *"|groups|"*) cat "$D/uv-groups" 2>/dev/null ;;
esac
exit 0
STUB

# claude stub: it writes its working directory and then each arg on a line.
cat > "$T/bin/claude" <<'STUB'
#!/bin/bash
{ pwd -P; for a in "$@"; do printf '%s\n' "$a"; done; } > "$STUB_DIR/claude-args"
STUB
# git wrapper: when GIT_LOG is set, it logs each call as one line, args
# joined by `|`, to that file. When $STUB_DIR/git-net-fail exists, each fetch
# and ls-remote fails, as with an origin that cannot be reached. Then it runs
# the real git.
REAL_GIT=$(command -v git)
export REAL_GIT
cat > "$T/bin/git" <<'STUB'
#!/bin/bash
if [ -n "${GIT_LOG:-}" ]; then
  line=''
  for a in "$@"; do line="$line$a|"; done
  printf '%s\n' "$line" >> "$GIT_LOG"
fi
if [ -e "$STUB_DIR/git-net-fail" ]; then
  for a in "$@"; do
    case "$a" in fetch|ls-remote) echo "fatal: unable to access origin: Could not resolve host" >&2; exit 128 ;; esac
  done
fi
exec "$REAL_GIT" "$@"
STUB
# ps and lsof stubs: they run the real tool, so the launcher sees each real
# process. Files: ps-tty (`<pid> <tty>` lines: the tty that ps shows for that
# pid), ps-extra (more ps lines, of processes that do not exist), lsof-extra
# (more lsof lines), lsof-fail (lsof fails).
REAL_PS=$(command -v ps)
REAL_LSOF=$(command -v lsof)
export REAL_PS REAL_LSOF
cat > "$T/bin/ps" <<'STUB'
#!/bin/bash
D=$STUB_DIR
"$REAL_PS" "$@" | awk -v f="$D/ps-tty" 'BEGIN { while ((getline l < f) > 0) { split(l, a, " "); t[a[1]] = a[2] } }
  { if ($1 in t) $3 = t[$1]; print }'
cat "$D/ps-extra" 2>/dev/null
exit 0
STUB
cat > "$T/bin/lsof" <<'STUB'
#!/bin/bash
[ -e "$STUB_DIR/lsof-fail" ] && { echo "lsof: WARNING: can't stat() file system" >&2; exit 1; }
"$REAL_LSOF" "$@"
cat "$STUB_DIR/lsof-extra" 2>/dev/null
exit 0
STUB
chmod +x "$T/bin/"*
export PATH="$T/bin:$PATH"

# The origin: a bare repo whose default branch is main. The checkout clones
# it at commit A; then the origin gets commit B. So the local main and
# origin/main of the checkout stay at A.
git init -q --bare --initial-branch=main "$T/origin.git"
git clone -q "$T/origin.git" "$T/seed" 2>/dev/null
(cd "$T/seed" && git commit -q --allow-empty -m A && git push -q origin main)
git clone -q "$T/origin.git" "$T/co"
(cd "$T/seed" && git commit -q --allow-empty -m B && git push -q origin main)
A=$(cd "$T/co" && git rev-parse main)
B=$(cd "$T/seed" && git rev-parse HEAD)
CO=$(cd "$T/co" && pwd -P)

# A checkout with no origin, for the git failure.
git init -q --initial-branch=main "$T/noremote"
(cd "$T/noremote" && git commit -q --allow-empty -m A)

cat > "$T/config.md" <<EOF
# Crew config

## Checkouts

o/other: $T/nowhere
- o/r: ~/../co

## Deploy

o/missing: $T/co
EOF
export CREW_CONFIG="$T/config.md"

ok() { echo "ok   $1"; }
bad() { fails=$((fails + 1)); echo "FAIL $1"; }
check() { total=$((total + 1)); if [ "$2" = 0 ]; then ok "$1"; else bad "$1"; fi; }

# run <args...>: run the launcher; keep stdout, stderr and the exit code.
# Each git call of the launcher goes to $T/git.log.
run() {
  GIT_LOG="$T/git.log" python3 "$L" "$@" > "$T/out" 2> "$T/err"
  rc=$?
}
lines() { grep -c . "$1" | tr -d ' '; }
alive_pid() { kill -0 "$1" 2>/dev/null; }
now_ms() { python3 -c 'import time; print(int(time.time() * 1000))'; }
now_iso() { date -u +%Y-%m-%dT%H:%M:%SZ; }
wtcount() { (cd "$T/co" && git worktree list | wc -l | tr -d ' '); }
reset_stub() { rm -rf "$STUB_DIR"; mkdir -p "$STUB_DIR"; }
# field <name>: one field of the start output, as JSON.
field() { python3 -c 'import json,sys; print(json.dumps(json.load(open(sys.argv[1]))[sys.argv[2]]))' "$T/out" "$1" 2>/dev/null; }

# -- usage (exit 2) --------------------------------------------------------
reset_stub
base=$(wtcount)
expect_usage() {
  label=$1; shift
  TMUX=/tmp/t,1,0 run start "$@"
  r=1; [ "$rc" = 2 ] && grep -sqi usage "$T/err" && [ "$(wtcount)" = "$base" ] && [ ! -s "$T/out" ] && r=0
  check "$label exits 2 with a usage line and no worktree" $r
}
expect_usage 'no --name' --model m --principal p --checkout "$CO"
expect_usage 'no --principal' --name n1 --model m --checkout "$CO"
expect_usage 'neither --repo nor --checkout' --name n1 --model m --principal p
for n in Bad_Name -x 'a b' 'a;b' eval my-eval-x retrieval; do
  expect_usage "name '$n'" --name="$n" --model m --principal p --checkout "$CO"
done
expect_usage "group color 'red'" --name n1 --model m --principal p --checkout "$CO" --group g --group-color red
expect_usage "group color '#12345'" --name n1 --model m --principal p --checkout "$CO" --group g --group-color '#12345'
expect_usage "terminal 'kitty'" --name n1 --model m --principal p --checkout "$CO" --terminal kitty
echo '[1, 2]' > "$T/list.json"
for v in '[1]' 'not json' '"a string"' "$T/list.json" "$T/no-such.json"; do
  expect_usage "settings '$v'" --name n1 --model m --principal p --checkout "$CO" --settings "$v"
done
total=$((total + 1))
TERM_PROGRAM=Apple_Terminal run start --name Bad_Name --model m --principal p --repo o/missing
if [ "$rc" = 2 ]; then ok 'a bad name and an unsupported terminal exit 2'; else bad "a bad name and an unsupported terminal exit 2 (got $rc)"; fi

# -- unsupported terminal (exit 4) ----------------------------------------
reset_stub
TERM_PROGRAM=Apple_Terminal run start --name t4 --model m --principal p --checkout "$CO"
r=1
[ "$rc" = 4 ] && [ "$(lines "$T/err")" = 1 ] && grep -sq Apple_Terminal "$T/err" && grep -sq iterm2 "$T/err" \
  && grep -sq tmux "$T/err" && [ "$(wtcount)" = "$base" ] && [ ! -e "$STUB_DIR/tmux.log" ] && r=0
check 'unsupported terminal exits 4 with one line naming TERM_PROGRAM and the supported terminals' $r
startline=$(cat "$T/err")
TERM_PROGRAM=Apple_Terminal run start --name t4 --model m --principal p --repo o/missing
check 'unsupported terminal wins over a missing Checkouts line' $([ "$rc" = 4 ]; echo $?)
TERM_PROGRAM=Apple_Terminal run groups
r=1; [ "$rc" = 4 ] && [ "$(cat "$T/err")" = "$startline" ] && r=0
check 'groups on an unsupported terminal exits 4 with the same line' $r

# -- Checkouts (exit 3) ----------------------------------------------------
TMUX=/tmp/t,1,0 run start --name t3 --model m --principal p --repo o/missing
r=1
[ "$rc" = 3 ] && [ "$(lines "$T/err")" = 1 ] && grep -sq 'o/missing' "$T/err" && grep -sq Checkouts "$T/err" \
  && [ "$(wtcount)" = "$base" ] && [ ! -e "$STUB_DIR/tmux.log" ] && r=0
check 'no Checkouts line exits 3 with one line naming the repo and Checkouts' $r
CREW_CONFIG="$T/none.md" TMUX=/tmp/t,1,0 run start --name t3 --model m --principal p --repo o/r
check 'a missing config file exits 3' $([ "$rc" = 3 ]; echo $?)
printf '## Checkouts\n\n### Work\n\no/sub: /x/sub\n\n#### More\n- o/deep: ~/deep\n\n## Deploy\n\no/after: /x/after\n' > "$T/sub.md"
r=1; CREW_CONFIG="$T/sub.md" python3 - "$here" <<'PY' && r=0
import os, sys
sys.path.insert(0, sys.argv[1])
import launcher
def get(repo):
    try:
        return launcher.checkout_for(repo)
    except launcher.Fail as f:
        return f.code
ok = get("o/sub") == "/x/sub" and get("o/deep") == os.path.expanduser("~/deep") and get("o/after") == 3
sys.exit(0 if ok else 1)
PY
check 'a ### subheading does not end the Checkouts section; the next ## heading does' $r

# -- git failures (exit 5) -------------------------------------------------
TMUX=/tmp/t,1,0 run start --name g5 --model m --principal p --repo o/other
r=1; [ "$rc" = 5 ] && [ "$(lines "$T/err")" = 1 ] && [ ! -e "$STUB_DIR/tmux.log" ] && r=0
check 'the second Checkouts line, to a missing path, exits 5' $r
TMUX=/tmp/t,1,0 run start --name g5 --model m --principal p --checkout "$T/noremote"
r=1; [ "$rc" = 5 ] && [ "$(lines "$T/err")" = 1 ] && [ ! -e "$STUB_DIR/tmux.log" ] \
  && [ ! -e "$T/noremote/.claude/worktrees/g5" ] && r=0
check 'a checkout with no origin exits 5 with one line and opens no tab' $r

# -- tmux start, through the Checkouts line --------------------------------
reset_stub
MODEL="opus 'x' \$HOME"
PRINC="orch 'a' \$PATH b"
TMUX=/tmp/t,1,0 run start --name review-x --model "$MODEL" --principal "$PRINC" --repo o/r
WT="$CO/.claude/worktrees/review-x"
check 'tmux start exits 0 (name review-x passes)' $([ "$rc" = 0 ]; echo $?)
check 'the Checkouts line for o/r, with a ~ path, selects the checkout' $([ -d "$WT" ]; echo $?)
r=1; [ "$(wc -l < "$T/out" | tr -d ' ')" = 1 ] && python3 - "$T/out" <<'PY' && r=0
import json, sys
o = json.loads(open(sys.argv[1]).read())
want = {"session_name", "repo", "worktree", "branch", "base", "model", "terminal", "tab", "tab_group", "session_id"}
sys.exit(0 if set(o) == want else 1)
PY
check 'stdout is one line, one JSON object with exactly the ten fields' $r
SID=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["session_id"])' "$T/out" 2>/dev/null)
check 'session_id is a UUID4' $(python3 -c 'import sys,uuid; u=uuid.UUID(sys.argv[1]); sys.exit(0 if str(u) == sys.argv[1] and u.version == 4 else 1)' "$SID" 2>/dev/null; echo $?)
check 'the worktree HEAD is the sha of the remote main, not the stale local main' \
  $([ "$(cd "$WT" 2>/dev/null && git rev-parse HEAD)" = "$B" ] && [ "$A" != "$B" ]; echo $?)
check 'the worktree is on branch worktree-review-x' \
  $([ "$(cd "$WT" 2>/dev/null && git rev-parse --abbrev-ref HEAD)" = worktree-review-x ]; echo $?)
check 'session_name' $([ "$(field session_name)" = '"review-x"' ]; echo $?)
check 'repo from --repo' $([ "$(field repo)" = '"o/r"' ]; echo $?)
check 'worktree is the absolute worktree path' $([ "$(field worktree)" = "\"$WT\"" ]; echo $?)
check 'branch' $([ "$(field branch)" = '"worktree-review-x"' ]; echo $?)
check 'base' $([ "$(field base)" = '"origin/main"' ]; echo $?)
check 'model is the --model value' $([ "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["model"])' "$T/out" 2>/dev/null)" = "$MODEL" ]; echo $?)
check 'terminal tmux' $([ "$(field terminal)" = '"tmux"' ]; echo $?)
check 'tab is tmux:<pane id>' $([ "$(field tab)" = '"tmux:%7"' ]; echo $?)
check 'tab_group is the default tmux session crew' $([ "$(field tab_group)" = '"crew"' ]; echo $?)
check 'tmux checks the session with the exact target =crew' $(grep -sqxF 'has-session|-t|=crew|' "$STUB_DIR/tmux.log"; echo $?)
check 'tmux creates the missing session detached, named crew, the window named review-x' \
  $(grep -sq '^new-session|-d|-s|crew|-n|review-x|' "$STUB_DIR/tmux.log"; echo $?)
check 'the tmux command starts with cd <worktree>' $(case "$(cat "$STUB_DIR/tmux-cmd" 2>/dev/null)" in ("cd $WT "*|"cd '$WT' "*) echo 0 ;; (*) echo 1 ;; esac)
check 'the tmux command execs claude' $(grep -sq '&& exec claude ' "$STUB_DIR/tmux-cmd"; echo $?)

# The shell runs the command: each value reaches the claude stub as one arg.
sh -c "$(cat "$STUB_DIR/tmux-cmd")"
PROMPT="You are an implementer session for the orchestrator session named $PRINC. The user started you through that orchestrator. Do nothing now. A goal arrives as a cross-session message from that session. When it arrives, run the crew:project-lead skill with that goal. The orchestrator is your principal: the user gave it the authority to decide for this work, so send your questions, your escalations and your reports to it with SendMessage, not to this tab. Answer this message with one line and then wait."
expect_args=$(printf '%s\n' "$WT" --name review-x --session-id "$SID" --model "$MODEL" --settings '{"remoteControlAtStartup": false}' "$PROMPT")
check 'claude runs in the worktree with --name, --session-id <session_id>, --model, the RC-off --settings and the wait prompt, quotes intact' \
  $([ "$(cat "$STUB_DIR/claude-args" 2>/dev/null)" = "$expect_args" ]; echo $?)

# -- --settings and the --model default ------------------------------------
# settings_is <label> <JSON>: run the last tmux command; the claude stub must
# get exactly one --settings, two args after --model, equal to <JSON>.
settings_is() {
  total=$((total + 1))
  sh -c "$(cat "$STUB_DIR/tmux-cmd" 2>/dev/null)" 2>/dev/null
  if python3 - "$STUB_DIR/claude-args" "$2" <<'PY'
import json, sys
a = open(sys.argv[1]).read().split("\n")[1:-1]
ok = a.count("--settings") == 1 and a.index("--settings") == a.index("--model") + 2
ok = ok and json.loads(a[a.index("--settings") + 1]) == json.loads(sys.argv[2])
sys.exit(0 if ok else 1)
PY
  then ok "$1"; else bad "$1"; fi
}
reset_stub
TMUX=/tmp/t,1,0 run start --name set-1 --principal p --checkout "$CO" \
  --settings '{"env": {"A": "it'"'"'s \"q\" $x"}, "model": "x"}'
check 'start with a --settings JSON string exits 0' $([ "$rc" = 0 ]; echo $?)
settings_is 'a JSON string with quotes is merged with remoteControlAtStartup false and passed as one arg' \
  '{"env": {"A": "it'"'"'s \"q\" $x"}, "model": "x", "remoteControlAtStartup": false}'
check 'no --model gives --model opus' $(grep -sqx -- opus "$STUB_DIR/claude-args" \
  && [ "$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["model"])' "$T/out" 2>/dev/null)" = opus ]; echo $?)
reset_stub
TMUX=/tmp/t,1,0 run start --name set-2 --model m --principal p --checkout "$CO" --settings '{"remoteControlAtStartup": true}'
settings_is 'an explicit remoteControlAtStartup in the value is kept' '{"remoteControlAtStartup": true}'
reset_stub
printf '{"permissions": {"allow": ["Bash(ls)"]}}\n' > "$T/settings.json"
TMUX=/tmp/t,1,0 run start --name set-3 --model m --principal p --checkout "$CO" --settings "$T/settings.json"
settings_is 'a file path value is read and merged' \
  '{"permissions": {"allow": ["Bash(ls)"]}, "remoteControlAtStartup": false}'

# -- an existing worktree or branch (exit 5) -------------------------------
reset_stub
: > "$STUB_DIR/tmux.log"
(cd "$WT" && git commit -q --allow-empty -m local)
before=$(cd "$WT" && git rev-parse HEAD)
TMUX=/tmp/t,1,0 run start --name review-x --model m --principal p --checkout "$CO"
r=1; [ "$rc" = 5 ] && [ "$(lines "$T/err")" = 1 ] && [ ! -s "$STUB_DIR/tmux.log" ] \
  && [ "$(cd "$WT" && git rev-parse HEAD)" = "$before" ] && r=0
check 'an existing worktree exits 5, one line, changes nothing and opens no tab' $r
(cd "$CO" && git branch -q worktree-only-branch "$A")
TMUX=/tmp/t,1,0 run start --name only-branch --model m --principal p --checkout "$CO"
r=1; [ "$rc" = 5 ] && [ ! -e "$CO/.claude/worktrees/only-branch" ] \
  && [ "$(cd "$CO" && git rev-parse worktree-only-branch)" = "$A" ] && r=0
check 'an existing branch worktree-<name> exits 5 and changes nothing' $r

# -- tmux: an existing session, --group, --terminal ------------------------
reset_stub
: > "$STUB_DIR/tmux-has"
run start --name tm2 --model m --principal p --checkout "$CO" --group grp --terminal tmux
r=1; [ "$rc" = 0 ] && grep -sq '^new-window|-t|=grp:|-n|tm2|' "$STUB_DIR/tmux.log" && [ "$(field tab_group)" = '"grp"' ] && r=0
check '--terminal tmux with --group grp opens a window in the existing session =grp' $r
check 'the new tmux window is not selected (-d), so the current window keeps the focus' \
  $(grep -sqE '^new-window\|(.*\|)?-d\|' "$STUB_DIR/tmux.log"; echo $?)

# -- repo from the origin URL, and --checkout over --repo ------------------
git clone -q "$T/origin.git" "$T/co2"
(cd "$T/co2" && git config url."$T/origin.git".insteadOf https://github.com/acme/widget.git \
  && git remote set-url origin https://github.com/acme/widget.git)
TMUX=/tmp/t,1,0 run start --name url-https --model m --principal p --checkout "$T/co2"
check 'repo from an https origin URL' $([ "$rc" = 0 ] && [ "$(field repo)" = '"acme/widget"' ]; echo $?)
(cd "$T/co2" && git config url."$T/origin.git".insteadOf git@github.com:acme/gadget.git \
  && git remote set-url origin git@github.com:acme/gadget.git)
TMUX=/tmp/t,1,0 run start --name url-ssh --model m --principal p --checkout "$T/co2"
check 'repo from an ssh origin URL' $([ "$rc" = 0 ] && [ "$(field repo)" = '"acme/gadget"' ]; echo $?)
TMUX=/tmp/t,1,0 run start --name both --model m --principal p --checkout "$T/co2" --repo o/other
r=1; [ "$rc" = 0 ] && [ -d "$T/co2/.claude/worktrees/both" ] && [ "$(field repo)" = '"o/other"' ] && r=0
check '--checkout wins over --repo, and --repo sets only the repo field' $r

# -- tmux failure: no fallback, exit 6 -------------------------------------
reset_stub
: > "$STUB_DIR/tmux-fail"
TMUX=/tmp/t,1,0 run start --name tm-fail --model m --principal p --checkout "$CO"
r=1; [ "$rc" = 6 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqF "$CO/.claude/worktrees/tm-fail" "$T/err" \
  && [ -d "$CO/.claude/worktrees/tm-fail" ] && r=0
check 'a failed tmux window exits 6, keeps the worktree and names it' $r

# -- iterm2 ----------------------------------------------------------------
reset_stub
TERM_PROGRAM=iTerm.app run start --name it1 --model m --principal p --checkout "$CO" --group grp --group-color '#1a2B3c'
r=1; [ "$rc" = 0 ] && [ "$(field terminal)" = '"iterm2"' ] && [ "$(field tab)" = '"iterm2:ABC-123"' ] && r=0
check 'TERM_PROGRAM=iTerm.app detects iterm2 and runs the helper' $r
check 'the helper runs through uv run --with iterm2 python iterm2-tabs.py' \
  $(grep -sq "^run|.*--with|iterm2|python|$here/iterm2-tabs.py|start|" "$STUB_DIR/uv.log"; echo $?)
check 'launcher.py passes --group and --group-color to the helper' \
  $(grep -sq '|--group|grp|' "$STUB_DIR/uv.log" && grep -sq '|--group-color|#1a2B3c|' "$STUB_DIR/uv.log"; echo $?)
check 'launcher.py passes the session name to the helper' $(grep -sq '|--name|it1|' "$STUB_DIR/uv.log"; echo $?)
check 'tab_group is the group the helper reports' $([ "$(field tab_group)" = '"grp"' ]; echo $?)
check 'the helper gets the cd command' $(grep -sqF "|cd $CO/.claude/worktrees/it1 && exec claude " "$STUB_DIR/uv.log"; echo $?)
reset_stub
ITERM_SESSION_ID=w0t1p0:ORCH-UUID run start --name it2 --model m --principal p --checkout "$CO"
r=1; [ "$rc" = 0 ] && [ "$(field terminal)" = '"iterm2"' ] && [ "$(field tab_group)" = null ] \
  && grep -sq '|--session|ORCH-UUID|' "$STUB_DIR/uv.log" && ! grep -sq -- '--group' "$STUB_DIR/uv.log" && r=0
check 'ITERM_SESSION_ID detects iterm2; no --group gives tab_group null; the window is the orchestrator session' $r
reset_stub
TMUX=/tmp/t,1,0 run start --name it3 --model m --principal p --checkout "$CO" --terminal iterm2
r=1; [ "$rc" = 0 ] && [ "$(field terminal)" = '"iterm2"' ] && [ ! -e "$STUB_DIR/tmux.log" ] && r=0
check '--terminal iterm2 wins over TMUX' $r

# The helper fails: the osascript fallback opens the tab, with no group.
reset_stub
: > "$STUB_DIR/uv-fail"
TERM_PROGRAM=iTerm.app run start --name it4 --model m --principal p --checkout "$CO" --group grp
r=1; [ "$rc" = 0 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqi 'no tab group' "$T/err" \
  && [ "$(field tab)" = '"iterm2:OSA-0001"' ] && [ "$(field tab_group)" = null ] \
  && grep -sq '^-|start|' "$STUB_DIR/osa.log" && r=0
check 'a failed helper falls back to osascript, prints one no-group line, tab_group null' $r
check 'the osascript fallback names the session' $(grep -sq '|it4|$' "$STUB_DIR/osa.log"; echo $?)
r=1; python3 - "$STUB_DIR/osa-script" <<'PY' && r=0
import sys
s = [l.strip() for l in open(sys.argv[1])]
def at(line):
    return s.index(line) if line in s else -1
keep, new, typed, back = (at("set oldTab to current tab of w"), at("tell w to set newTab to (create tab with default profile)"),
                          at("write text cmd"), at("tell oldTab to select"))
sys.exit(0 if -1 < keep < new < typed < back else 1)
PY
check 'the osascript fallback selects the tab it had before, so the orchestrator tab keeps the focus' $r

# The helper and osascript fail: exit 6, the worktree stays and is named.
: > "$STUB_DIR/osa-fail"
TERM_PROGRAM=iTerm.app run start --name it5 --model m --principal p --checkout "$CO"
r=1; [ "$rc" = 6 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqF "$CO/.claude/worktrees/it5" "$T/err" \
  && [ -d "$CO/.claude/worktrees/it5" ] && [ ! -s "$T/out" ] && r=0
check 'a failed helper and a failed osascript exit 6 and name the kept worktree' $r

# -- iterm2: a helper that fails part way (one tab, never two) -------------
# helper_says <exit code> <stdout line>...: the next helper stdout and exit.
helper_says() { reset_stub; echo "$1" > "$STUB_DIR/uv-rc"; shift; printf '%s\n' "$@" > "$STUB_DIR/uv-out"; }
osa_starts() { grep -c '^-|start|' "$STUB_DIR/osa.log" 2>/dev/null | tr -d ' '; }

helper_says 1 '{"opened": "T-1"}' '{"closed": "T-1"}'
TERM_PROGRAM=iTerm.app run start --name pf1 --model m --principal p --checkout "$CO" --group grp
r=1; [ "$rc" = 0 ] && [ "$(osa_starts)" = 1 ] && ! grep -sq '^-|stop|' "$STUB_DIR/osa.log" \
  && [ "$(field tab)" = '"iterm2:OSA-0001"' ] && [ "$(lines "$T/err")" = 1 ] && r=0
check 'a helper that closed its tab and failed gives exactly one osascript start call' $r

helper_says 1 '{"opened": "T-1"}'
echo 'T-1' > "$STUB_DIR/osa-sessions"
TERM_PROGRAM=iTerm.app run start --name pf2 --model m --principal p --checkout "$CO"
r=1; [ "$rc" = 0 ] && [ "$(sed -n 1p "$STUB_DIR/osa.log")" = '-|stop|T-1|' ] && [ "$(osa_starts)" = 1 ] \
  && [ "$(field tab)" = '"iterm2:OSA-0001"' ] && [ "$(lines "$T/err")" = 1 ] && r=0
check 'a helper that left its tab open with no command: osascript closes it first, then one start call' $r

helper_says 1 '{"opened": "T-1"}'
: > "$STUB_DIR/osa-fail"
TERM_PROGRAM=iTerm.app run start --name pf3 --model m --principal p --checkout "$CO"
r=1; [ "$rc" = 6 ] && [ "$(osa_starts)" = 0 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqF 'iterm2:T-1' "$T/err" \
  && grep -sqF "$CO/.claude/worktrees/pf3" "$T/err" && [ ! -s "$T/out" ] && r=0
check 'a tab that cannot close: exit 6, no osascript start, the line names the tab and the worktree' $r

helper_says 1 '{"opened": "T-1"}' '{"typed": "T-1"}'
TERM_PROGRAM=iTerm.app run start --name pf4 --model m --principal p --checkout "$CO" --group grp
r=1; [ "$rc" = 0 ] && [ ! -e "$STUB_DIR/osa.log" ] && [ "$(field tab)" = '"iterm2:T-1"' ] \
  && [ "$(field tab_group)" = null ] && [ "$(lines "$T/err")" = 1 ] && r=0
check 'a helper that failed after it typed the command: the tab is reported, one stderr line, no osascript' $r

helper_says 0 '{"opened": "T-1"}' '{"typed": "T-1"}' 'not json'
TERM_PROGRAM=iTerm.app run start --name pf5 --model m --principal p --checkout "$CO"
r=1; [ "$rc" = 0 ] && [ ! -e "$STUB_DIR/osa.log" ] && [ "$(field tab)" = '"iterm2:T-1"' ] && [ "$(lines "$T/err")" = 1 ] && r=0
check 'a typed command and no result line: the tab is reported, no osascript' $r

helper_says 0 '{"opened": "T-1"}' '{"typed": "T-1"}' '{"session_id": "T-1", "tab_group": null, "warning": "RPCException: x"}'
TERM_PROGRAM=iTerm.app run start --name pf6 --model m --principal p --checkout "$CO" --group grp
r=1; [ "$rc" = 0 ] && [ ! -e "$STUB_DIR/osa.log" ] && [ "$(field tab)" = '"iterm2:T-1"' ] \
  && [ "$(field tab_group)" = null ] && [ "$(lines "$T/err")" = 1 ] && grep -sq 'RPCException: x' "$T/err" && r=0
check 'a result with a warning: the tab is reported, one stderr line, no osascript' $r

r=1; python3 - "$here" <<'PY' && r=0
import sys
sys.path.insert(0, sys.argv[1])
import launcher
rc, out, _ = launcher.run(["sh", "-c", "echo '{\"opened\": \"T-1\"}'; sleep 5"], timeout=1)
sys.exit(0 if rc == 124 and '"opened"' in out else 1)
PY
check 'a helper timeout keeps the stdout the helper printed before it' $r
chmod -x "$T/bin/claude"
r=1; python3 - "$here" "$T/bin/claude" <<'PY' && r=0
import sys
sys.path.insert(0, sys.argv[1])
import launcher
rc, out, err = launcher.run([sys.argv[2]])
sys.exit(0 if rc == 127 and err.strip() else 1)
PY
chmod +x "$T/bin/claude"
check 'a command that cannot run gives exit 127 and a line, not a traceback' $r

# A helper that hangs: the launcher kills the helper's whole process group.
reset_stub
: > "$STUB_DIR/uv-hang"
r=1; python3 - "$here" "$CO" > "$T/out" 2> "$T/err" <<'PY' && r=0
import sys, time
sys.path.insert(0, sys.argv[1])
import launcher
launcher.HELPER_TIMEOUT = 2
t = time.time()
rc = launcher.main(["start", "--name", "hang-1", "--principal", "p", "--checkout", sys.argv[2], "--terminal", "iterm2"])
sys.exit(0 if rc == 0 and time.time() - t < 10 else 1)
PY
child=$(cat "$STUB_DIR/uv-child" 2>/dev/null)
gone=1
for _ in 1 2 3 4 5 6 7 8 9 10; do
  if [ -n "$child" ] && ! kill -0 "$child" 2>/dev/null; then gone=0; break; fi
  sleep 0.2
done
[ -n "$child" ] && kill "$child" 2>/dev/null
check 'a helper timeout kills the child of the helper too: no stub child stays' \
  $([ "$r" = 0 ] && [ "$gone" = 0 ]; echo $?)
r=1; python3 - "$here" "$STUB_DIR/uv.log" <<'PY' && r=0
import sys
sys.path.insert(0, sys.argv[1])
import launcher
a = open(sys.argv[2]).readline().rstrip("\n").split("|")
ok = "--deadline" in a and 0 < int(a[a.index("--deadline") + 1]) < launcher.HELPER_TIMEOUT
sys.exit(0 if ok else 1)
PY
check 'launcher.py gives the helper a --deadline shorter than HELPER_TIMEOUT' $r

# -- iterm2-tabs.py itself, against a fake iterm2 module -------------------
mkdir -p "$T/fake"
cat > "$T/fake/iterm2.py" <<'PY'
"""A fake iterm2 module. FAKE_FAIL names the calls that raise, FAKE_HANG the
calls that hang."""
import asyncio
import os

FAIL = os.environ.get("FAKE_FAIL", "").split(",")
HANG = os.environ.get("FAKE_HANG", "").split(",")


def log(s):
    with open(os.environ["STUB_DIR"] + "/fake.log", "a") as f:
        f.write(s + "\n")


class Boom(Exception):
    pass


class capabilities:
    @staticmethod
    def supports_tab_groups(conn):
        return True


class Color:
    @staticmethod
    def from_hex(h):
        return h


class Session:
    session_id = "FAKE-1"

    async def async_set_name(self, n):
        log("set_name " + n)
        if "set_name" in FAIL:
            raise Boom("set_name failed")

    async def async_send_text(self, t):
        log("send_text")
        if "send_text" in HANG:
            await asyncio.sleep(60)
        if "send_text" in FAIL:
            raise Boom("send_text failed")

    async def async_close(self, force=False):
        log("close force=%s" % force)
        if "close" in FAIL:
            raise Boom("close failed")


class TabGroup:
    def __init__(self, name, color):
        self.name = name
        self.color = color
        self.group_id = "G-" + name


# The open groups of the one window, by name: FAKE_GROUPS names the groups
# that exist at the start. TAB_GROUP holds the group of the one tab.
GROUPS = {n: TabGroup(n, None) for n in os.environ.get("FAKE_GROUPS", "").split(",") if n}
TAB_GROUP = [None]


class Tab:
    tab_id = "T1"

    def __init__(self):
        self.current_session = Session()

    @property
    def tab_group(self):
        return TAB_GROUP[0]

    async def async_add_to_tab_group(self, group):
        log("add_to_group " + group.name)
        TAB_GROUP[0] = group


class Window:
    window_id = "W1"

    @property
    def tab_groups(self):
        return list(GROUPS.values())

    async def async_create_tab(self, select=True):
        log("create_tab select=%s" % select)
        return Tab()

    async def async_create_tab_group(self, name, tabs, color):
        log("create_group %s %s" % (name, color))
        if "create_group" in FAIL:
            raise Boom("group failed")
        GROUPS[name] = TabGroup(name, color)
        TAB_GROUP[0] = GROUPS[name]
        return GROUPS[name]


class App:
    current_terminal_window = Window()

    def get_session_by_id(self, i):
        return None

    def get_window_by_id(self, i):
        return self.current_terminal_window

    def get_tab_by_id(self, i):
        return Tab()


async def async_get_app(conn):
    return App()


class Connection:
    @staticmethod
    async def async_create():
        return object()
PY
# helper <FAKE_FAIL> <args...>: run the helper itself on the fake module.
helper() {
  reset_stub
  f=$1; shift
  FAKE_FAIL=$f PYTHONPATH="$T/fake" python3 "$here/iterm2-tabs.py" start --name h1 --command 'echo hi' "$@" > "$T/out" 2> "$T/err"
  rc=$?
}
has() { grep -sqF -- "$1" "$T/out"; }
for f in set_name send_text; do
  helper "$f"
  r=1; [ "$rc" = 1 ] && has '{"opened": "FAKE-1"}' && has '{"closed": "FAKE-1"}' && ! has typed \
    && ! has session_id && grep -sqx 'close force=True' "$STUB_DIR/fake.log" && [ "$(lines "$T/err")" = 1 ] && r=0
  check "helper: a failed $f closes the tab with force, prints closed, and exits 1" $r
done
helper set_name,close
r=1; [ "$rc" = 1 ] && has '{"opened": "FAKE-1"}' && ! has closed && ! has session_id && r=0
check 'helper: a tab that does not close gives exit 1 and no closed line' $r
helper create_group --group grp
r=1; [ "$rc" = 0 ] && has '{"typed": "FAKE-1"}' && ! grep -sq close "$STUB_DIR/fake.log" \
  && [ "$(tail -n 1 "$T/out" | python3 -c 'import json,sys; o=json.load(sys.stdin); print(o["session_id"], o["tab_group"], "group failed" in o["warning"])')" = 'FAKE-1 None True' ] && r=0
check 'helper: a failed group step after the command reports the tab with a warning and exits 0' $r
FAKE_GROUPS=other,grp helper '' --group grp --group-color '#112233'
r=1; [ "$rc" = 0 ] && grep -sqx 'add_to_group grp' "$STUB_DIR/fake.log" && ! grep -sq create_group "$STUB_DIR/fake.log" \
  && [ "$(tail -n 1 "$T/out")" = '{"session_id": "FAKE-1", "tab_group": "grp"}' ] && r=0
check 'helper: an open group of that name: the tab joins it, no new group, tab_group is its name' $r
FAKE_GROUPS=other helper '' --group grp --group-color '#112233'
r=1; [ "$rc" = 0 ] && grep -sqx 'create_group grp #112233' "$STUB_DIR/fake.log" && ! grep -sq add_to_group "$STUB_DIR/fake.log" \
  && [ "$(tail -n 1 "$T/out")" = '{"session_id": "FAKE-1", "tab_group": "grp"}' ] && r=0
check 'helper: no open group of that name: a new group with the color, tab_group is its name' $r
helper ''
r=1; [ "$rc" = 0 ] && grep -sqx 'create_tab select=False' "$STUB_DIR/fake.log" \
  && [ "$(tail -n 1 "$T/out")" = '{"session_id": "FAKE-1", "tab_group": null}' ] && r=0
check 'helper: with no group, the last line is the result with tab_group null' $r
s0=$(date +%s)
FAKE_HANG=send_text helper '' --deadline 1
r=1; [ "$rc" = 1 ] && [ $(($(date +%s) - s0)) -lt 10 ] && has '{"opened": "FAKE-1"}' && ! has session_id \
  && [ "$(lines "$T/err")" = 1 ] && r=0
check 'helper: a call that hangs past --deadline exits 1 with one stderr line' $r

# -- groups ----------------------------------------------------------------
reset_stub
printf '$1\tcrew\n$4\tgrp\n' > "$STUB_DIR/tmux-sessions"
TMUX=/tmp/t,1,0 run groups
r=1; [ "$rc" = 0 ] && python3 - "$T/out" <<'PY' && r=0
import json, sys
rows = [json.loads(l) for l in open(sys.argv[1]) if l.strip()]
ok = len(rows) == 2 and all(set(r) == {"window_id", "group_id", "name", "color"} for r in rows)
ok = ok and [r["name"] for r in rows] == ["crew", "grp"] and [r["group_id"] for r in rows] == ["$1", "$4"]
ok = ok and all(r["window_id"] is None and r["color"] is None for r in rows)
sys.exit(0 if ok else 1)
PY
check 'groups on tmux prints one line per session, window_id and color null' $r
printf '{"window_id": "w1", "group_id": "g1", "name": "grp", "color": "#1a2b3c"}\n' > "$STUB_DIR/uv-groups"
TERM_PROGRAM=iTerm.app run groups
r=1; [ "$rc" = 0 ] && [ "$(lines "$T/out")" = 1 ] && grep -sq '"group_id": "g1"' "$T/out" && r=0
check 'groups on iterm2 prints the helper lines' $r
: > "$STUB_DIR/uv-fail"
TERM_PROGRAM=iTerm.app run groups
r=1; [ "$rc" = 0 ] && [ ! -s "$T/out" ] && [ "$(lines "$T/err")" = 1 ] && r=0
check 'groups with no API prints one stderr line, no group line, and exits 0' $r

# -- focus -----------------------------------------------------------------
reset_stub
echo 'SESS-1' > "$STUB_DIR/osa-sessions"
echo '%7' > "$STUB_DIR/tmux-panes"
run focus iterm2:SESS-1
r=1; [ "$rc" = 0 ] && grep -sq '^-|focus|SESS-1|$' "$STUB_DIR/osa.log" && grep -sq activate "$STUB_DIR/osa-script" && r=0
check 'focus iterm2:<id> addresses the id and activates iTerm2' $r
TMUX=/tmp/t,1,0 run focus 'tmux:%7'
r=1; [ "$rc" = 0 ] && grep -sq '^select-window|-t|%7|$' "$STUB_DIR/tmux.log" \
  && grep -sq '^switch-client|-t|%7|$' "$STUB_DIR/tmux.log" && r=0
check 'focus tmux:<pane> selects the window and switches the client, exact pane target' $r
: > "$STUB_DIR/tmux.log"
echo '/dev/ttys009' > "$STUB_DIR/tmux-clients"
run focus 'tmux:%7'
r=1; [ "$rc" = 0 ] && grep -sq '^switch-client|-c|/dev/ttys009|-t|%7|$' "$STUB_DIR/tmux.log" && r=0
check 'focus tmux:<pane> outside tmux switches the attached client' $r
for h in 'foo:1' 'iterm2:NOPE' 'tmux:%99' 'tmux:7'; do
  run focus "$h"
  check "focus $h exits 7 with one line" $([ "$rc" = 7 ] && [ "$(lines "$T/err")" = 1 ]; echo $?)
done

# -- stop ------------------------------------------------------------------
run stop iterm2:SESS-1
check 'stop iterm2:<id> addresses the id' $([ "$rc" = 0 ] && grep -sq '^-|stop|SESS-1|$' "$STUB_DIR/osa.log"; echo $?)
run stop 'tmux:%7'
check 'stop tmux:<pane> kills the exact pane' $([ "$rc" = 0 ] && grep -sq '^kill-pane|-t|%7|$' "$STUB_DIR/tmux.log"; echo $?)
check 'stop leaves the worktree and the branch' \
  $([ -d "$WT" ] && (cd "$CO" && git rev-parse -q --verify refs/heads/worktree-review-x > /dev/null); echo $?)
run stop iterm2:GONE
check 'stop on a gone iTerm2 tab exits 0 with one line' $([ "$rc" = 0 ] && [ "$(lines "$T/out")" = 1 ] && grep -sqi gone "$T/out"; echo $?)
run stop 'tmux:%99'
check 'stop on a gone tmux pane exits 0 with one line' $([ "$rc" = 0 ] && [ "$(lines "$T/out")" = 1 ] && grep -sqi gone "$T/out"; echo $?)
run stop 'foo:1'
check 'stop with an unknown prefix exits 7 with one line' $([ "$rc" = 7 ] && [ "$(lines "$T/err")" = 1 ]; echo $?)

# focus and stop exit 6 when the terminal step fails; the line names the handle.
: > "$STUB_DIR/tmux-kill-fail"
run stop 'tmux:%7'
check 'stop tmux:<pane> with a failed kill-pane exits 6, one line naming the handle' \
  $([ "$rc" = 6 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqF 'tmux:%7' "$T/err"; echo $?)
: > "$STUB_DIR/osa-fail"
for v in focus stop; do
  run "$v" iterm2:SESS-1
  check "$v iterm2:<id> with a failed osascript exits 6, one line naming the handle" \
    $([ "$rc" = 6 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqF 'iterm2:SESS-1' "$T/err"; echo $?)
done
rm -f "$STUB_DIR/tmux-kill-fail" "$STUB_DIR/osa-fail"

# -- stop types /exit before the close ---------------------------------------
# claude then ends the session with the reason prompt_input_exit, and a
# restore tool does not start it again.
reset_stub
echo 'SESS-1' > "$STUB_DIR/osa-sessions"
echo 'SESS-1 /dev/ttys960' > "$STUB_DIR/osa-ttys"
run stop iterm2:SESS-1
r=1; [ "$rc" = 0 ] && [ "$(sed -n 1p "$STUB_DIR/osa.log")" = '-|exit|SESS-1|' ] \
  && [ "$(sed -n 2p "$STUB_DIR/osa.log")" = '-|stop|SESS-1|' ] && [ ! -s "$T/out" ] && [ ! -s "$T/err" ] && r=0
check 'stop iterm2:<id> types /exit into the session first, then closes the tab' $r
check 'the iTerm2 exit step types /exit with write text' $(grep -sqF 'write text "/exit"' "$STUB_DIR/osa-scripts"; echo $?)
r=1; python3 - "$STUB_DIR/osa-scripts" <<'PY' && r=0
import sys
s = open(sys.argv[1]).read()
esc = s.find("write text (ASCII character 27) newline NO")
clr = s.find("write text (ASCII character 21) newline NO")
ext = s.find('write text "/exit"')
sys.exit(0 if -1 < esc < clr < ext else 1)
PY
check 'the iTerm2 exit step sends Escape, then Ctrl-U with no newline, then /exit' $r
reset_stub
echo '%7' > "$STUB_DIR/tmux-panes"
echo '%7 /dev/ttys961' > "$STUB_DIR/tmux-ttys"
run stop 'tmux:%7'
r=1; [ "$rc" = 0 ] && python3 - "$STUB_DIR/tmux.log" <<'PY' && r=0
import sys
s = [l.rstrip("\n") for l in open(sys.argv[1])]
def at(line):
    return s.index(line) if line in s else -1
sys.exit(0 if -1 < at("send-keys|-t|%7|Escape|") < at("send-keys|-t|%7|C-u|") < at("send-keys|-t|%7|-l|/exit|")
         < at("send-keys|-t|%7|Enter|") < at("kill-pane|-t|%7|") else 1)
PY
check 'stop tmux:<pane> sends Escape, then C-u, then /exit literally, then Enter, then kills the pane' $r
# A claude on the tab's tty that does not end: one stderr line, the tab still closes.
reset_stub
echo '%7' > "$STUB_DIR/tmux-panes"
echo '%7 /dev/ttys961' > "$STUB_DIR/tmux-ttys"
echo '900010 1 ttys961 claude --name x --model opus' > "$STUB_DIR/ps-extra"
r=1; python3 - "$here" > "$T/out" 2> "$T/err" <<'PY' && r=0
import sys, time
sys.path.insert(0, sys.argv[1])
import launcher
launcher.STOP_WAIT = 1
launcher.STOP_CLOSE_WAIT = 1
t = time.time()
rc = launcher.main(["stop", "tmux:%7"])
sys.exit(0 if rc == 0 and time.time() - t < 10 else 1)
PY
r2=1; [ "$r" = 0 ] && [ "$(lines "$T/err")" = 2 ] && [ "$(grep -c 900010 "$T/err")" = 1 ] \
  && grep -sq '^kill-pane|-t|%7|$' "$STUB_DIR/tmux.log" && r2=0
check 'a claude that did not end in time: exit 0, the pane is still killed, one stderr line for the wait and one that names the pid after the close' $r2

# stop_live <seconds> <close-wait>: a real process that ps shows as claude on
# the tty of tmux:%7 ends after <seconds>. stop runs in this process with
# STOP_WAIT 1 and STOP_CLOSE_WAIT <close-wait>. $T/stop.json holds the exit
# code, whether the pid ran at the kill-pane, and the seconds stop took. $pc
# is the pid.
stop_live() {
  reset_stub
  echo '%7' > "$STUB_DIR/tmux-panes"
  echo '%7 /dev/ttys961' > "$STUB_DIR/tmux-ttys"
  (bash -c "exec -a claude sleep $1" < /dev/null > /dev/null 2>&1 & echo $! > "$T/cl")
  pc=$(cat "$T/cl"); echo "$pc" >> "$T/pids"
  echo "$pc ttys961" > "$STUB_DIR/ps-tty"
  python3 - "$here" "$pc" "$2" > "$T/stop.json" 2> "$T/err" <<'PY'
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
import launcher
pc, close_wait = int(sys.argv[2]), int(sys.argv[3])
launcher.STOP_WAIT = 1
launcher.STOP_CLOSE_WAIT = close_wait
launcher.KEY_WAIT = 0
def runs(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True
at_close = [None]
real_tmux = launcher.tmux
def tmux(args):
    if args and args[0] == "kill-pane":
        at_close[0] = runs(pc)
    return real_tmux(args)
launcher.tmux = tmux
t = time.time()
rc = launcher.main(["stop", "tmux:%7"])
print(json.dumps({"rc": rc, "at_close": at_close[0], "took": time.time() - t}))
PY
}
sj() { python3 -c 'import json,sys; o=json.load(open(sys.argv[1])); sys.exit(0 if eval(sys.argv[2]) else 1)' "$T/stop.json" "$1" 2>/dev/null; }
stop_live 4 15
r=1; sj 'o["rc"] == 0 and o["at_close"] is True' && ! alive_pid "$pc" && r=0
check 'stop with a claude that ends after the close: the pane is killed while it runs, and stop exits 0 only after ps stops showing it' $r
stop_live 300 1
r=1; sj 'o["rc"] == 0 and o["at_close"] is True and o["took"] < 10' && [ "$(grep -c "$pc" "$T/err")" = 1 ] && alive_pid "$pc" && r=0
check 'stop with a claude that never ends: exit 0, one stderr line names the pid, and stop sends it no signal' $r
kill -9 "$pc" 2>/dev/null
# The iTerm2 path: a claude on the tty of the session ends 3 seconds after
# stop starts, after the 1 second wait for it and after the tab close. stop
# returns only after it ended, and the close came first.
reset_stub
echo 'SESS-1' > "$STUB_DIR/osa-sessions"
echo 'SESS-1 /dev/ttys961' > "$STUB_DIR/osa-ttys"
(bash -c "exec -a claude sleep 3" < /dev/null > /dev/null 2>&1 & echo $! > "$T/cl")
pc=$(cat "$T/cl"); echo "$pc" >> "$T/pids"
echo "$pc ttys961" > "$STUB_DIR/ps-tty"
python3 - "$here" "$pc" > "$T/stop.json" 2> "$T/err" <<'PY'
import json, os, sys, time
sys.path.insert(0, sys.argv[1])
import launcher
pc = int(sys.argv[2])
launcher.STOP_WAIT = 1
launcher.STOP_CLOSE_WAIT = 15
launcher.KEY_WAIT = 0
def runs(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    return True
at_close = [None]
real_script = launcher.iterm_script
def iterm_script(script, verb, ref):
    if verb == "stop":
        at_close[0] = runs(pc)
    return real_script(script, verb, ref)
launcher.iterm_script = iterm_script
t = time.time()
rc = launcher.main(["stop", "iterm2:SESS-1"])
print(json.dumps({"rc": rc, "at_close": at_close[0], "took": time.time() - t, "after": runs(pc)}))
PY
r=1; sj 'o["rc"] == 0 and o["at_close"] is True and o["after"] is False and o["took"] >= 2.5' \
  && grep -sq '^-|stop|SESS-1|$' "$STUB_DIR/osa.log" && [ "$(lines "$T/err")" = 1 ] && ! grep -sq 'still runs' "$T/err" && ! alive_pid "$pc" && r=0
check 'stop iterm2:<id> with a claude that ends after the close: the tab is closed while it runs, and stop returns only after ps stops showing it' $r
kill -9 "$pc" 2>/dev/null

# The pane closes when claude ends: stop does not kill it and exits 0.
reset_stub
echo '%7' > "$STUB_DIR/tmux-panes"
echo '%7 /dev/ttys961' > "$STUB_DIR/tmux-ttys"
: > "$STUB_DIR/tmux-close-on-enter"
run stop 'tmux:%7'
r=1; [ "$rc" = 0 ] && grep -sq '^send-keys|-t|%7|Enter|$' "$STUB_DIR/tmux.log" && ! grep -sq '^kill-pane|' "$STUB_DIR/tmux.log" \
  && [ ! -s "$T/out" ] && [ ! -s "$T/err" ] && r=0
check 'stop tmux:<pane> whose pane closed when claude ended exits 0 and sends no kill-pane' $r

# -- stop --name and --session-id: no key unless the target holds the implementer --
# A tmux pane id restarts at %0 with a new server, so an old handle can name
# another pane. stop_py <args...>: stop with no wait, in this process.
stop_py() {
  python3 - "$here" "$@" > "$T/out" 2> "$T/err" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import launcher
launcher.STOP_WAIT = 0
launcher.KEY_WAIT = 0
sys.exit(launcher.main(sys.argv[2:]))
PY
  rc=$?
}
no_keys_tmux() { ! grep -sq '^send-keys|' "$STUB_DIR/tmux.log" && ! grep -sq '^kill-pane|' "$STUB_DIR/tmux.log"; }
reset_stub
echo '%2' > "$STUB_DIR/tmux-panes"
echo '%2 /dev/ttys970' > "$STUB_DIR/tmux-ttys"
echo '900020 1 ttys970 claude --name other --model opus' > "$STUB_DIR/ps-extra"
printf 'p900020\nfcwd\nn/elsewhere\n' > "$STUB_DIR/lsof-extra"
stop_py stop 'tmux:%2' --name a --session-id s-1
check 'stop tmux:<pane> --name --session-id on a pane with another claude sends no key, kills nothing, prints one line and exits 0' \
  $([ "$rc" = 0 ] && [ "$(lines "$T/out")" = 1 ] && no_keys_tmux; echo $?)
reset_stub
echo '%2' > "$STUB_DIR/tmux-panes"
echo '%2 /dev/ttys970' > "$STUB_DIR/tmux-ttys"
stop_py stop 'tmux:%2' --name a
check 'stop tmux:<pane> --name on a pane with no claude (a shell) sends no key and exits 0 with one line' \
  $([ "$rc" = 0 ] && [ "$(lines "$T/out")" = 1 ] && no_keys_tmux; echo $?)
stop_py stop 'tmux:%9' --name a
check 'stop --name on a gone tmux pane exits 0 with one line' \
  $([ "$rc" = 0 ] && [ "$(lines "$T/out")" = 1 ] && grep -sqi gone "$T/out" && no_keys_tmux; echo $?)
reset_stub
echo '%2' > "$STUB_DIR/tmux-panes"
echo '%2 /dev/ttys970' > "$STUB_DIR/tmux-ttys"
echo '900020 1 ttys970 claude --name a --model opus' > "$STUB_DIR/ps-extra"
stop_py stop 'tmux:%2' --name a --session-id s-1
check 'stop tmux:<pane> --name on the pane of that session sends the keys and kills the pane' \
  $([ "$rc" = 0 ] && grep -sq '^send-keys|-t|%2|-l|/exit|' "$STUB_DIR/tmux.log" && grep -sq '^kill-pane|-t|%2|' "$STUB_DIR/tmux.log"; echo $?)
reset_stub
echo '%2' > "$STUB_DIR/tmux-panes"
echo '%2 /dev/ttys970' > "$STUB_DIR/tmux-ttys"
echo '900020 1 ttys970 claude --resume s-9 --model opus' > "$STUB_DIR/ps-extra"
stop_py stop 'tmux:%2' --name a --session-id s-9
check 'stop tmux:<pane> --session-id on a claude with --resume <id> sends the keys and kills the pane' \
  $([ "$rc" = 0 ] && grep -sq '^send-keys|-t|%2|-l|/exit|' "$STUB_DIR/tmux.log" && grep -sq '^kill-pane|-t|%2|' "$STUB_DIR/tmux.log"; echo $?)
# A claude with only its cwd in the worktree is not the implementer: a person
# can start one there. stop never acts on a cwd match.
reset_stub
echo '%2' > "$STUB_DIR/tmux-panes"
echo '%2 /dev/ttys970' > "$STUB_DIR/tmux-ttys"
echo '900020 1 ttys970 claude --model opus' > "$STUB_DIR/ps-extra"
printf 'p900020\nfcwd\nn%s\n' "$(cd "$WT" && pwd -P)" > "$STUB_DIR/lsof-extra"
stop_py stop 'tmux:%2' --name a --session-id s-9
check 'stop tmux:<pane> --name --session-id on a claude that matches only by its cwd in the worktree sends no key and kills nothing' \
  $([ "$rc" = 0 ] && [ "$(lines "$T/out")" = 1 ] && no_keys_tmux; echo $?)
stop_py stop 'tmux:%2' --name a --worktree "$WT"
check 'stop has no --worktree flag: exit 2, no key' $([ "$rc" = 2 ] && no_keys_tmux; echo $?)
reset_stub
echo 'S-2' > "$STUB_DIR/osa-sessions"
echo 'S-2 /dev/ttys971' > "$STUB_DIR/osa-ttys"
echo '900021 1 ttys971 claude --name other --model opus' > "$STUB_DIR/ps-extra"
stop_py stop iterm2:S-2 --name a --session-id s-1
check 'stop iterm2:<id> --name --session-id on a session with another claude sends no key, closes nothing, prints one line and exits 0' \
  $([ "$rc" = 0 ] && [ "$(lines "$T/out")" = 1 ] && ! grep -sq '^-|exit|' "$STUB_DIR/osa.log" && ! grep -sq '^-|stop|' "$STUB_DIR/osa.log"; echo $?)
stop_py stop iterm2:S-9 --name a
check 'stop --name on a gone iTerm2 session exits 0 with one line and sends no key' \
  $([ "$rc" = 0 ] && [ "$(lines "$T/out")" = 1 ] && grep -sqi gone "$T/out" && ! grep -sq '^-|exit|' "$STUB_DIR/osa.log"; echo $?)
: > "$STUB_DIR/osa.log"
stop_py stop iterm2:S-2 --name other
check 'stop iterm2:<id> --name on the session of that claude types /exit, then closes the tab' \
  $([ "$rc" = 0 ] && grep -sq '^-|exit|S-2|$' "$STUB_DIR/osa.log" && grep -sq '^-|stop|S-2|$' "$STUB_DIR/osa.log"; echo $?)

# -- find ------------------------------------------------------------------
reset_stub
WTREAL=$(cd "$WT" && pwd -P)
printf '%%7 /dev/ttys901\n%%8 /dev/ttys902\n%%9 /dev/ttys903\n%%10 /dev/ttys904\n%%11 /dev/ttys906\n%%12 /dev/ttys907\n%%13 /dev/ttys908\n' > "$STUB_DIR/tmux-list-panes"
cat > "$STUB_DIR/ps-extra" <<PS
900001 1 ttys901 claude --name a --model opus
900002 1 ttys902 /usr/local/bin/claude --resume x --name a-2 --model opus
900003 1 ttys903 vim --name a
900004 1 ttys904 claude --name zz-other --model opus
900005 1 ttys905 claude --name a --model opus
900006 1 ttys906 node /opt/lib/node_modules/@anthropic-ai/claude-code/cli.js --name nn --model opus
900007 1 ttys907 node /usr/local/bin/claude --name nb --model opus
900008 1 ttys908 node /srv/app.js --name nx --model opus
PS
printf 'p900002\nfcwd\nn%s\np900003\nfcwd\nn%s\np900004\nfcwd\nn%s-x\n' "$WTREAL" "$WTREAL" "$WTREAL" > "$STUB_DIR/lsof-extra"
TMUX=/tmp/t,1,0 run find a
check 'find a on tmux prints only the pane of the claude with --name a, not a-2, and the match kind name' \
  $([ "$rc" = 0 ] && [ "$(cat "$T/out")" = 'tmux:%7 name' ]; echo $?)
TMUX=/tmp/t,1,0 run find a-2
check 'find a-2 on tmux prints only the pane of the claude with --name a-2' \
  $([ "$rc" = 0 ] && [ "$(cat "$T/out")" = 'tmux:%8 name' ]; echo $?)
TMUX=/tmp/t,1,0 run find a-2 --worktree "$WT"
check 'find with a match by name and by cwd prints the kind name' \
  $([ "$rc" = 0 ] && [ "$(cat "$T/out")" = 'tmux:%8 name' ]; echo $?)
TMUX=/tmp/t,1,0 run find nn
check 'find matches an npm claude: node with the script @anthropic-ai/claude-code/cli.js' \
  $([ "$rc" = 0 ] && [ "$(cat "$T/out")" = 'tmux:%11 name' ]; echo $?)
TMUX=/tmp/t,1,0 run find nb
check 'find matches node with a script path that ends in /claude' \
  $([ "$rc" = 0 ] && [ "$(cat "$T/out")" = 'tmux:%12 name' ]; echo $?)
TMUX=/tmp/t,1,0 run find nx
check 'find does not match node with another script' $([ "$rc" = 0 ] && [ ! -s "$T/out" ]; echo $?)
TMUX=/tmp/t,1,0 run find zz
check 'find with no match prints no line and exits 0' $([ "$rc" = 0 ] && [ ! -s "$T/out" ]; echo $?)
TMUX=/tmp/t,1,0 run find zz --worktree "$WT"
check 'find --worktree matches a claude whose cwd is the worktree, not another program, not a longer path; the kind is cwd' \
  $([ "$rc" = 0 ] && [ "$(cat "$T/out")" = 'tmux:%8 cwd' ]; echo $?)
check 'find on tmux lists the panes with list-panes -a' \
  $(grep -sqF 'list-panes|-a|-F|#{pane_id} #{pane_tty}|' "$STUB_DIR/tmux.log"; echo $?)
printf 'S-1 /dev/ttys901\nS-2 /dev/ttys902\nS-3 /dev/ttys903\n' > "$STUB_DIR/osa-ttys"
TERM_PROGRAM=iTerm.app run find a
check 'find a on iTerm2 prints only the session of the claude with --name a' \
  $([ "$rc" = 0 ] && [ "$(cat "$T/out")" = 'iterm2:S-1 name' ]; echo $?)
TERM_PROGRAM=iTerm.app run find nobody --worktree "$WT"
check 'find --worktree on iTerm2 matches by the cwd' $([ "$rc" = 0 ] && [ "$(cat "$T/out")" = 'iterm2:S-2 cwd' ]; echo $?)
check 'find on iTerm2 reads the unique id and the tty of each session' \
  $(grep -sq 'unique id of s' "$STUB_DIR/osa-script" && grep -sq 'tty of s' "$STUB_DIR/osa-script" && ! grep -sq 'name of s' "$STUB_DIR/osa-script"; echo $?)
: > "$STUB_DIR/lsof-fail"
TMUX=/tmp/t,1,0 run find zz --worktree "$WT"
check 'find --worktree with a failed lsof exits 6 with one line and prints no handle' \
  $([ "$rc" = 6 ] && [ "$(lines "$T/err")" = 1 ] && grep -sq lsof "$T/err" && [ ! -s "$T/out" ]; echo $?)
rm -f "$STUB_DIR/lsof-fail"
rm -f "$STUB_DIR/tmux-list-panes"
TMUX=/tmp/t,1,0 run find a
check 'find with no tmux server prints no line and exits 0' $([ "$rc" = 0 ] && [ ! -s "$T/out" ]; echo $?)

# find --session-id: the kind id is a claude whose argv holds --resume <id>
# or --session-id <id>. A person's own claude in the worktree has neither.
reset_stub
printf '%%7 /dev/ttys911\n%%8 /dev/ttys912\n%%9 /dev/ttys913\n%%10 /dev/ttys914\n' > "$STUB_DIR/tmux-list-panes"
cat > "$STUB_DIR/ps-extra" <<PS
900031 1 ttys911 claude --resume sid-1 --model opus
900032 1 ttys912 claude --session-id sid-1 --model opus
900033 1 ttys913 claude --name a --resume sid-1
900034 1 ttys914 claude --model opus
PS
printf 'p900034\nfcwd\nn%s\n' "$WTREAL" > "$STUB_DIR/lsof-extra"
TMUX=/tmp/t,1,0 run find zz --session-id sid-1
check 'find --session-id matches --resume <id> and --session-id <id>, with the kind id' \
  $([ "$rc" = 0 ] && [ "$(cat "$T/out")" = "$(printf 'tmux:%%7 id\ntmux:%%8 id\ntmux:%%9 id')" ]; echo $?)
TMUX=/tmp/t,1,0 run find a --session-id sid-1 --worktree "$WT"
check 'find: name wins over id, and a claude with neither and its cwd in the worktree is cwd' \
  $([ "$rc" = 0 ] && [ "$(cat "$T/out")" = "$(printf 'tmux:%%7 id\ntmux:%%8 id\ntmux:%%9 name\ntmux:%%10 cwd')" ]; echo $?)
TMUX=/tmp/t,1,0 run find zz --session-id sid-2
check 'find --session-id with another id prints no line' $([ "$rc" = 0 ] && [ ! -s "$T/out" ]; echo $?)

# -- resume ----------------------------------------------------------------
reset_stub
TMUX=/tmp/t,1,0 run start --name rs-1 --principal p --checkout "$CO"
RWT="$CO/.claude/worktrees/rs-1"
export CLAUDE_CONFIG_DIR="$T/cc"
ENC=$(printf '%s' "$RWT" | sed 's/[^A-Za-z0-9]/-/g')
PD="$CLAUDE_CONFIG_DIR/projects/$ENC"
mkdir -p "$PD/sub"
: > "$PD/old-1111.jsonl"; touch -t 202601010000 "$PD/old-1111.jsonl"
: > "$PD/new-2222.jsonl"; touch -t 202601020000 "$PD/new-2222.jsonl"
: > "$PD/sub/deeper-3333.jsonl"; touch -t 202601030000 "$PD/sub/deeper-3333.jsonl"
: > "$PD/notes.txt"; touch -t 202601030000 "$PD/notes.txt"
reset_stub
mv "$T/git.log" "$T/git.log.keep"
TMUX=/tmp/t,1,0 run resume --name rs-1 --worktree "$RWT"
check 'resume exits 0' $([ "$rc" = 0 ]; echo $?)
r=1; [ "$(wc -l < "$T/out" | tr -d ' ')" = 1 ] && python3 - "$T/out" <<'PY' && r=0
import json, sys
o = json.loads(open(sys.argv[1]).read())
want = {"session_name", "repo", "worktree", "branch", "base", "model", "terminal", "tab", "tab_group", "session_id"}
sys.exit(0 if set(o) == want else 1)
PY
check 'resume prints the ten fields of start' $r
check 'resume takes the newest top-level transcript of the worktree' $([ "$(field session_id)" = '"new-2222"' ]; echo $?)
r=1; [ "$(field branch)" = '"worktree-rs-1"' ] && [ "$(field base)" = '"origin/main"' ] && [ "$(field worktree)" = "\"$RWT\"" ] \
  && [ "$(field model)" = '"opus"' ] && [ "$(field tab)" = '"tmux:%7"' ] && [ "$(field repo)" = null ] && r=0
check 'resume: branch, base, worktree, model opus and tab' $r
sh -c "$(cat "$STUB_DIR/tmux-cmd")"
expect_args=$(printf '%s\n' "$RWT" --resume new-2222 --name rs-1 --model opus --settings '{"remoteControlAtStartup": false}')
check 'resume runs claude in the worktree with --resume, --name, --model opus, the RC-off --settings, and no prompt' \
  $([ "$(cat "$STUB_DIR/claude-args" 2>/dev/null)" = "$expect_args" ]; echo $?)
check 'resume makes no worktree and no branch' \
  $(! grep -sqE '\|worktree\|add\||(^|\|)branch\|' "$T/git.log" 2>/dev/null; echo $?)
cat "$T/git.log" >> "$T/git.log.keep" 2>/dev/null; mv "$T/git.log.keep" "$T/git.log"
reset_stub
TMUX=/tmp/t,1,0 run resume --name rs-1 --worktree "$RWT" --session-id given-1 --model m --settings '{"a": 1}' --repo o/r
settings_is 'resume merges --settings with remoteControlAtStartup false' '{"a": 1, "remoteControlAtStartup": false}'
check 'resume --session-id wins over the transcript; --repo sets repo' \
  $([ "$(field session_id)" = '"given-1"' ] && [ "$(field repo)" = '"o/r"' ] && grep -sq -- '--resume given-1 ' "$STUB_DIR/tmux-cmd"; echo $?)
reset_stub
TERM_PROGRAM=iTerm.app run resume --name rs-1 --worktree "$RWT"
check 'resume on iTerm2 gives the helper the --resume command' \
  $([ "$rc" = 0 ] && grep -sqF "|cd $RWT && exec claude --resume new-2222 --name rs-1 " "$STUB_DIR/uv.log"; echo $?)
reset_stub
CLAUDE_CONFIG_DIR="$T/empty-cc" TMUX=/tmp/t,1,0 run resume --name rs-1 --worktree "$RWT"
check 'resume with no transcript exits 5 with one line and opens no tab' \
  $([ "$rc" = 5 ] && [ "$(lines "$T/err")" = 1 ] && ! grep -sq '^new-' "$STUB_DIR/tmux.log" 2>/dev/null; echo $?)
TMUX=/tmp/t,1,0 run resume --name rs-1 --worktree "$T/no-such-worktree" --session-id x
check 'resume with a missing worktree exits 5 and opens no tab' \
  $([ "$rc" = 5 ] && [ "$(lines "$T/err")" = 1 ] && ! grep -sq '^new-' "$STUB_DIR/tmux.log" 2>/dev/null; echo $?)
printf '%%7 /dev/ttys901\n' > "$STUB_DIR/tmux-list-panes"
echo '900001 1 ttys901 claude --name rs-1 --model opus' > "$STUB_DIR/ps-extra"
TMUX=/tmp/t,1,0 run resume --name rs-1 --worktree "$RWT"
check 'resume of a session that find sees exits 8, names the tab, and opens no tab' \
  $([ "$rc" = 8 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqF 'tmux:%7' "$T/err" && ! grep -sq '^new-' "$STUB_DIR/tmux.log"; echo $?)
# A claude with no --name, as a restore tool starts it: find matches it by its cwd.
printf '%%7 /dev/ttys901\n' > "$STUB_DIR/tmux-list-panes"
echo '900001 1 ttys901 claude --resume new-2222 --model opus' > "$STUB_DIR/ps-extra"
printf 'p900001\nfcwd\nn%s\n' "$RWT" > "$STUB_DIR/lsof-extra"
: > "$STUB_DIR/tmux.log"
TMUX=/tmp/t,1,0 run resume --name rs-1 --worktree "$RWT"
check 'resume of a session that find sees by its cwd (no --name) exits 8, names the tab, and opens no tab' \
  $([ "$rc" = 8 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqF 'tmux:%7' "$T/err" && ! grep -sq '^new-' "$STUB_DIR/tmux.log"; echo $?)
# A claude that resumed the conversation, with no --name and its cwd unread.
rm -f "$STUB_DIR/lsof-extra"
: > "$STUB_DIR/tmux.log"
TMUX=/tmp/t,1,0 run resume --name rs-1 --worktree "$RWT"
check 'resume of a session that find sees by its id (--resume <id>, no --name, no cwd) exits 8 and opens no tab' \
  $([ "$rc" = 8 ] && grep -sqF 'tmux:%7' "$T/err" && ! grep -sq '^new-' "$STUB_DIR/tmux.log"; echo $?)
rm -f "$STUB_DIR/lsof-extra" "$STUB_DIR/ps-extra"
TMUX=/tmp/t,1,0 run resume --name Bad_Name --worktree "$RWT"
check 'resume with a bad --name exits 2' $([ "$rc" = 2 ]; echo $?)
unset CLAUDE_CONFIG_DIR

# -- remove ----------------------------------------------------------------
# rm_wt <name>: a worktree from start, with a tracked file f and a .gitignore.
rm_wt() {
  TMUX=/tmp/t,1,0 run start --name "$1" --principal p --checkout "$CO"
  RM="$CO/.claude/worktrees/$1"
  (cd "$RM" && echo x > f && echo '*.log' > .gitignore && git add f .gitignore && git commit -q -m f)
}
# rjson <expr>: a Python expression on the remove output o; exit 0 when true.
rjson() { python3 -c 'import json,sys; o=json.load(open(sys.argv[1])); sys.exit(0 if eval(sys.argv[2]) else 1)' "$T/out" "$1" 2>/dev/null; }
# orphan <dir> [ignore-term]: a sleep with its cwd in dir and init as its parent. Prints its pid.
orphan() {
  if [ -n "${2:-}" ]; then
    (cd "$1" && { bash -c 'trap "" TERM; exec sleep 300' < /dev/null > /dev/null 2>&1 & echo $! > "$T/orphan"; })
  else
    (cd "$1" && { sleep 300 < /dev/null > /dev/null 2>&1 & echo $! > "$T/orphan"; })
  fi
  cat "$T/orphan" >> "$T/pids"
  cat "$T/orphan"
}
alive() { kill -0 "$1" 2>/dev/null; }
reset_stub
rm_wt rm-clean
run remove "$RM"
r=1; [ "$rc" = 0 ] && [ "$(lines "$T/out")" = 1 ] && [ ! -e "$RM" ] && rjson 'set(o) == {"worktree", "removed", "stopped", "kept", "changed", "branch", "branches", "lock"}' \
  && rjson 'o["removed"] is True and o["stopped"] == [] and o["kept"] == [] and o["changed"] == []' \
  && rjson 'o["branch"] == "worktree-rm-clean" and o["branches"] == [] and o["lock"] is None' \
  && (cd "$CO" && git rev-parse -q --verify refs/heads/worktree-rm-clean > /dev/null) && r=0
check 'remove of a clean worktree removes it, keeps the branch, and prints the eight fields' $r
check 'remove runs git worktree remove with no force' \
  $(grep -sq '|worktree|remove|' "$T/git.log" && ! grep -sqE '\|worktree\|remove\|.*(--force|-f)\|' "$T/git.log"; echo $?)

rm_wt rm-mod
echo y > "$RM/f"
run remove "$RM"
r=1; [ "$rc" = 9 ] && [ "$(lines "$T/err")" = 1 ] && [ -d "$RM" ] && [ "$(cat "$RM/f")" = y ] \
  && rjson 'o["removed"] is False and any(l.endswith(" f") for l in o["changed"])' && r=0
check 'remove of a worktree with a modified file exits 9, keeps it and names the file' $r
rm_wt rm-new
echo n > "$RM/new.txt"
run remove "$RM"
r=1; [ "$rc" = 9 ] && [ -e "$RM/new.txt" ] && rjson 'o["removed"] is False and "?? new.txt" in o["changed"]' && r=0
check 'remove of a worktree with an untracked file exits 9 and names the file' $r
rm_wt rm-ign
echo l > "$RM/build.log"
run remove "$RM"
check 'remove of a worktree with only an ignored file removes it' \
  $([ "$rc" = 0 ] && [ ! -e "$RM" ] && rjson 'o["removed"] is True and o["changed"] == []'; echo $?)

rm_wt rm-proc
p1=$(orphan "$RM")
echo "$p1 ??" > "$STUB_DIR/ps-tty"
t0=$(now_ms)
run remove "$RM"
t1=$(now_ms)
r=1; [ "$rc" = 9 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqF "$p1" "$T/err" && [ -d "$RM" ] && alive "$p1" \
  && [ $((t1 - t0)) -lt 3000 ] \
  && rjson "o['removed'] is False and o['stopped'] == [] and [(k['pid'], k['tty']) for k in o['kept']] == [($p1, None)]" && r=0
check 'remove with no flag and a no-tty process in the worktree that is not claude (a GUI editor) exits 9 in less than 3 seconds, stops nothing, and lists it in kept' $r
run remove "$RM" --stop-processes
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && ! alive "$p1" \
  && rjson "o['removed'] is True and o['kept'] == [] and [s['pid'] for s in o['stopped']] == [$p1] and 'sleep' in o['stopped'][0]['command']" && r=0
check 'remove --stop-processes stops a process with no terminal in the worktree, names it, then removes the worktree' $r
# A claude with no terminal that ends 2 seconds after remove starts: an
# implementer session that /exit is ending. remove waits for it.
reset_stub
rm_wt rm-ending
(cd "$RM" && { bash -c 'exec -a claude sleep 2' < /dev/null > /dev/null 2>&1 & echo $! > "$T/orphan"; })
p1=$(cat "$T/orphan"); echo "$p1" >> "$T/pids"
echo "$p1 ??" > "$STUB_DIR/ps-tty"
run remove "$RM"
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && ! alive "$p1" && rjson "o['removed'] is True and o['stopped'] == [] and o['kept'] == []" && r=0
check 'remove with no flag waits for a no-tty claude in the worktree that ends 2 seconds later, then removes the worktree' $r
reset_stub
rm_wt rm-kill
p1=$(orphan "$RM" ignore-term)
echo "$p1 ??" > "$STUB_DIR/ps-tty"
r=1; python3 - "$here" "$RM" > "$T/out" 2> "$T/err" <<'PY' && r=0
import sys
sys.path.insert(0, sys.argv[1])
import launcher
launcher.REMOVE_WAIT = 1
sys.exit(launcher.main(["remove", sys.argv[2], "--stop-processes"]))
PY
check 'remove --stop-processes sends KILL to a process that outlives TERM' \
  $([ "$r" = 0 ] && ! alive "$p1" && [ ! -e "$RM" ] && rjson "[s['pid'] for s in o['stopped']] == [$p1]"; echo $?)
# A claude with no terminal that does not end inside REMOVE_END_WAIT (2 seconds
# here): remove waits the whole time, then refuses with exit 9 and keeps it.
reset_stub
rm_wt rm-noend
(cd "$RM" && { bash -c 'exec -a claude sleep 300' < /dev/null > /dev/null 2>&1 & echo $! > "$T/orphan"; })
p1=$(cat "$T/orphan"); echo "$p1" >> "$T/pids"
echo "$p1 ??" > "$STUB_DIR/ps-tty"
t0=$(now_ms)
python3 - "$here" "$RM" > "$T/out" 2> "$T/err" <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import launcher
launcher.REMOVE_END_WAIT = 2
sys.exit(launcher.main(["remove", sys.argv[2]]))
PY
rc=$?
t1=$(now_ms)
r=1; [ "$rc" = 9 ] && [ -d "$RM" ] && alive "$p1" && [ $((t1 - t0)) -ge 2000 ] && grep -sqF "$p1" "$T/err" \
  && rjson "o['removed'] is False and o['stopped'] == [] and [(k['pid'], k['tty']) for k in o['kept']] == [($p1, None)]" && r=0
check 'remove with no flag and a no-tty claude in the worktree that does not end in REMOVE_END_WAIT waits the whole time, then exits 9, keeps the worktree, lists the process in kept and stops nothing' $r
kill -9 "$p1" 2>/dev/null

# rm_signal <mode> <worktree> <pid>: remove --stop-processes with os.kill
# wrapped. It logs each signal to <pid> in $T/sigs. Modes: changed-before-term
# (after the scan, ps shows another command for the pid), changed-before-kill
# (ps shows another command after the TERM; the TERM goes nowhere), eperm (each
# signal to the pid fails with PermissionError), survive (the KILL goes
# nowhere), spawn (the TERM to the pid also starts a new process in the
# worktree, whose pid goes to $T/spawned), moved (after the TERM, lsof shows
# the pid with its cwd outside the worktree; the TERM goes nowhere). Each git
# call goes to $T/git.log.sig.
rm_signal() {
  : > "$T/git.log.sig"
  GIT_LOG="$T/git.log.sig" python3 - "$here" "$@" "$T/sigs" > "$T/out" 2> "$T/err" <<'PY'
import os, signal, subprocess, sys
sys.path.insert(0, sys.argv[1])
import launcher
launcher.REMOVE_WAIT = 1
launcher.KILL_WAIT = 1
mode, wt, target, logfile = sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5]
sigs = []
changed = [False]
real_kill = os.kill
def kill(pid, sig):
    if pid == target and sig != 0:
        sigs.append(int(sig))
        if mode == "eperm":
            raise PermissionError(1, "Operation not permitted")
        if mode == "survive" and sig == signal.SIGKILL:
            return None
        if mode == "changed-before-kill" and sig == signal.SIGTERM:
            changed[0] = True
            return None
        if mode == "moved" and sig == signal.SIGTERM:
            moved[0] = True
            return None
        if mode == "spawn" and sig == signal.SIGTERM:
            # sh exits at once, so the new sleep has init as its parent.
            out = subprocess.run(["sh", "-c", "sleep 300 < /dev/null > /dev/null 2>&1 & echo $!"],
                                 cwd=wt, stdout=subprocess.PIPE, text=True).stdout
            open(os.path.join(os.path.dirname(logfile), "spawned"), "w").write(out.strip())
    return real_kill(pid, sig)
moved = [False]
real_cwds = launcher.cwds
def cwds():
    where = real_cwds()
    if moved[0] and target in where:
        where[target] = "/elsewhere"
    return where
launcher.cwds = cwds
real_processes = launcher.processes
calls = [0]
def processes():
    calls[0] += 1
    procs = real_processes()
    if mode == "changed-before-term" and calls[0] > 1:
        changed[0] = True
    if changed[0] and target in procs:
        procs[target] = dict(procs[target], argv=["other-program", "--x"])
    return procs
os.kill = kill
launcher.processes = processes
rc = launcher.main(["remove", wt, "--stop-processes"])
open(logfile, "w").write(" ".join(str(s) for s in sigs))
sys.exit(rc)
PY
  rc=$?
}
# A pid that runs another command at the signal is not ours: no signal. It
# still has its cwd in the worktree, so remove keeps the worktree.
# kept_not_stopped <pid>: exit 9, no git step, the worktree stays, the pid in
# kept and not in stopped.
kept_not_stopped() {
  [ "$rc" = 9 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqF "$1" "$T/err" && [ -d "$RM" ] \
    && ! grep -sq '|worktree|remove|' "$T/git.log.sig" \
    && rjson "o['removed'] is False and $1 in [k['pid'] for k in o['kept']] and $1 not in [s['pid'] for s in o['stopped']]"
}
reset_stub
rm_wt rm-reuse1
p1=$(orphan "$RM")
echo "$p1 ??" > "$STUB_DIR/ps-tty"
rm_signal changed-before-term "$RM" "$p1"
check 'remove --stop-processes sends no TERM to a pid whose command changed after the scan, and keeps the worktree while it runs there (exit 9, the pid in kept)' \
  $([ ! -s "$T/sigs" ] && alive "$p1" && kept_not_stopped "$p1"; echo $?)
kill -9 "$p1" 2>/dev/null
reset_stub
rm_wt rm-reuse2
p1=$(orphan "$RM" ignore-term)
echo "$p1 ??" > "$STUB_DIR/ps-tty"
rm_signal changed-before-kill "$RM" "$p1"
check 'remove --stop-processes sends no KILL to a pid whose command changed after the TERM, and keeps the worktree while it runs there (exit 9, the pid in kept)' \
  $([ "$(cat "$T/sigs")" = 15 ] && alive "$p1" && kept_not_stopped "$p1"; echo $?)
kill -9 "$p1" 2>/dev/null
# A process that starts in the worktree during the stop keeps the worktree.
reset_stub
rm_wt rm-spawn
p1=$(orphan "$RM")
echo "$p1 ??" > "$STUB_DIR/ps-tty"
rm -f "$T/spawned"
rm_signal spawn "$RM" "$p1"
p2=$(cat "$T/spawned" 2>/dev/null)
[ -n "$p2" ] && echo "$p2" >> "$T/pids"
r=1; [ -n "$p2" ] && alive "$p2" && ! alive "$p1" && kept_not_stopped "$p2" \
  && rjson "[s['pid'] for s in o['stopped']] == [$p1]" && r=0
check 'remove --stop-processes with a new process in the worktree after the stop exits 9, runs no git step, and lists the new pid in kept' $r
[ -n "$p2" ] && kill -9 "$p2" 2>/dev/null
# A pid whose cwd is now outside the worktree is stopped for remove.
reset_stub
rm_wt rm-moved
p1=$(orphan "$RM" ignore-term)
echo "$p1 ??" > "$STUB_DIR/ps-tty"
rm_signal moved "$RM" "$p1"
check 'remove --stop-processes lists a pid whose cwd is now outside the worktree in stopped, and removes the worktree' \
  $([ "$rc" = 0 ] && [ ! -e "$RM" ] && rjson "[s['pid'] for s in o['stopped']] == [$p1] and o['kept'] == []"; echo $?)
kill -9 "$p1" 2>/dev/null
# A process that remove cannot stop: exit 9, no git step, the pid in kept.
for mode in eperm survive; do
  reset_stub
  rm_wt "rm-$mode"
  p1=$(orphan "$RM" ignore-term)
  echo "$p1 ??" > "$STUB_DIR/ps-tty"
  rm_signal "$mode" "$RM" "$p1"
  r=1; [ "$rc" = 9 ] && [ "$(lines "$T/err")" = 1 ] && grep -sqF "$p1" "$T/err" && [ -d "$RM" ] && alive "$p1" \
    && ! grep -sq '|worktree|remove|' "$T/git.log.sig" && ! grep -sq '|branch|' "$T/git.log.sig" \
    && rjson "o['removed'] is False and [k['pid'] for k in o['kept']] == [$p1] and $p1 not in [s['pid'] for s in o['stopped']]" && r=0
  check "remove --stop-processes with a process it cannot stop ($mode) exits 9, runs no git step, and lists the pid in kept, not in stopped" $r
  kill -9 "$p1" 2>/dev/null
done

reset_stub
rm_wt rm-tty
p1=$(orphan "$RM")
p2=$(orphan "$RM")
printf '%s ttys950\n%s ??\n' "$p1" "$p2" > "$STUB_DIR/ps-tty"
run remove "$RM" --stop-processes
r=1; [ "$rc" = 9 ] && [ "$(lines "$T/err")" = 1 ] && [ -d "$RM" ] && alive "$p1" && alive "$p2" \
  && grep -sqF "$p1" "$T/err" && ! grep -sqF "$p2" "$T/err" \
  && rjson "o['removed'] is False and o['stopped'] == [] and sorted((k['pid'], k['tty'] or '') for k in o['kept']) == sorted([($p1, 'ttys950'), ($p2, '')])" && r=0
check 'remove --stop-processes with a terminal process in the worktree exits 9, stops nothing, keeps both processes, and the line names only the terminal one' $r
kill "$p1" "$p2" 2>/dev/null

reset_stub
rm_wt rm-keep
echo n > "$RM/new.txt"
p1=$(orphan "$RM")
echo "$p1 ??" > "$STUB_DIR/ps-tty"
run remove "$RM" --stop-processes
r=1; [ "$rc" = 9 ] && [ -d "$RM" ] && alive "$p1" && ! grep -sqF "$p1" "$T/err" \
  && rjson "o['stopped'] == [] and [(k['pid'], k['tty']) for k in o['kept']] == [($p1, None)]" && r=0
check 'remove --stop-processes on a refused worktree (an untracked file) lists a no-tty process in kept, with tty null, and does not stop it' $r
kill "$p1" 2>/dev/null

reset_stub
rm_wt rm-anc
(cd "$RM/" && GIT_LOG="$T/git.log" python3 "$L" remove "$RM" --stop-processes > "$T/out" 2> "$T/err")
rc=$?
r=1; [ "$rc" = 9 ] && [ "$(lines "$T/err")" = 1 ] && [ -d "$RM" ] && rjson 'o["removed"] is False and len(o["kept"]) >= 1' && r=0
check 'remove --stop-processes run from inside the worktree (its own or an ancestor cwd) exits 9 and keeps it' $r

rm_wt rm-lsof
: > "$STUB_DIR/lsof-fail"
run remove "$RM"
r=1; [ "$rc" = 6 ] && [ "$(lines "$T/err")" = 1 ] && grep -sq lsof "$T/err" && [ -d "$RM" ] && r=0
check 'remove with a failed lsof exits 6 with one line and keeps the worktree' $r
rm -f "$STUB_DIR/lsof-fail"

# -- remove --delete-branch: the candidates and the proof -------------------
# A candidate is deleted only when the branches and tags that `git ls-remote
# origin` lists, or the verified PR head, hold each of its commits. No local
# ref is a keeper: not a branch, not a tag, not a remote-tracking ref.
# rm_wt0 <name>: a
# worktree from start with no commit of its own: its branch is at origin/main.
rm_wt0() {
  TMUX=/tmp/t,1,0 run start --name "$1" --principal p --checkout "$CO"
  RM="$CO/.claude/worktrees/$1"
}
# has_branch <name>: the branch exists in the checkout.
has_branch() { (cd "$CO" && git rev-parse -q --verify "refs/heads/$1" > /dev/null); }
# bjson <expr>: a Python expression on b, the branches of the output by name.
bjson() { python3 -c 'import json,sys; o=json.load(open(sys.argv[1])); b={x["name"]: x for x in o["branches"]}; n=[x["name"] for x in o["branches"]]; sys.exit(0 if eval(sys.argv[2]) else 1)' "$T/out" "$1" 2>/dev/null; }
# unpushed <dir> <message>: a new commit in dir that no other ref holds. Prints its sha.
unpushed() { (cd "$1" && git commit -q --allow-empty -m "$2" && git rev-parse HEAD); }

# rm_wt makes a commit f on the branch, and no remote holds it.
reset_stub
rm_wt rm-br
sha=$(unpushed "$RM" rm-br)
n=$(lines "$T/git.log")
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && has_branch worktree-rm-br \
  && [ "$(lines "$T/err")" = 1 ] && grep -sq 'worktree-rm-br' "$T/err" \
  && ! tail -n +"$((n + 1))" "$T/git.log" | grep -sq '|branch|-D|' \
  && rjson "o['removed'] is True and o['branch'] == 'worktree-rm-br'" \
  && bjson "n == ['worktree-rm-br'] and b['worktree-rm-br']['deleted'] is False and '$sha' in b['worktree-rm-br']['unproven_commits'] and b['worktree-rm-br']['checked_out'] is None" && r=0
check 'remove --delete-branch keeps a branch with a commit that no remote and no tag holds, lists the sha, prints one line, removes the worktree and exits 0' $r
(cd "$CO" && git branch -D -q worktree-rm-br)

# The commit is on a branch on origin, which ls-remote lists: the branch holds nothing of its own.
rm_wt rm-br2
(cd "$RM" && git commit -q --allow-empty -m rm-br2 && git push -q origin worktree-rm-br2 2>/dev/null)
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && ! has_branch worktree-rm-br2 \
  && [ ! -s "$T/err" ] && (cd "$CO" && git rev-parse -q --verify refs/remotes/origin/worktree-rm-br2 > /dev/null) \
  && rjson 'o["removed"] is True and o["branch"] == "worktree-rm-br2"' \
  && bjson "n == ['worktree-rm-br2'] and b['worktree-rm-br2']['deleted'] is True and b['worktree-rm-br2']['unproven_commits'] == []" && r=0
check 'remove --delete-branch deletes a branch whose commits a branch on origin holds, and removes the worktree' $r
check 'remove --delete-branch fetches origin with --no-prune before the proof' \
  $(grep -sq '|fetch|-q|--no-prune|origin|' "$T/git.log"; echo $?)
check 'remove --delete-branch reads the keepers with ls-remote origin, proves with rev-list --stdin and no local ref, and deletes with branch -D' \
  $(grep -sq '|ls-remote|origin|$' "$T/git.log" && grep -sq '|rev-list|refs/heads/worktree-rm-br2|--stdin|$' "$T/git.log" \
    && ! grep -sqE '\|rev-list\|.*(--branches|--remotes|--tags|--all)' "$T/git.log" && grep -sq '|branch|-D|worktree-rm-br2|' "$T/git.log"; echo $?)

# The remote branch was deleted: only a stale refs/remotes/origin/<b> holds the commit. It proves nothing.
rm_wt0 rm-stale
(cd "$RM" && git switch -q -c crew/st/b)
sha=$(unpushed "$RM" stale)
(cd "$RM" && git push -q origin crew/st/b 2>/dev/null)
git --git-dir="$T/origin.git" branch -q -D crew/st/b
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && has_branch crew/st/b && (cd "$CO" && git rev-parse -q --verify refs/remotes/origin/crew/st/b > /dev/null) \
  && ! has_branch worktree-rm-stale \
  && bjson "b['crew/st/b']['deleted'] is False and b['crew/st/b']['unproven_commits'] == ['$sha'] and b['worktree-rm-stale']['deleted'] is True" && r=0
check 'remove --delete-branch keeps a branch whose commits only a stale remote-tracking ref holds' $r
(cd "$CO" && git branch -D -q crew/st/b)
# A tag only in the local repo proves nothing; a tag on origin proves.
rm_wt0 rm-ltag
sha=$(unpushed "$RM" ltag)
(cd "$RM" && git tag ltag-x)
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && has_branch worktree-rm-ltag && bjson "b['worktree-rm-ltag']['deleted'] is False and b['worktree-rm-ltag']['unproven_commits'] == ['$sha']" && r=0
check 'remove --delete-branch keeps a branch whose commits only a local tag holds' $r
(cd "$CO" && git branch -D -q worktree-rm-ltag && git tag -d ltag-x > /dev/null)
rm_wt0 rm-otag
(cd "$RM" && git commit -q --allow-empty -m otag && git tag -a otag-x -m otag && git push -q origin otag-x 2>/dev/null)
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && ! has_branch worktree-rm-otag && bjson "b['worktree-rm-otag']['deleted'] is True and b['worktree-rm-otag']['unproven_commits'] == []" && r=0
check 'remove --delete-branch deletes a branch whose commits an annotated tag on origin holds' $r

# The project lead moved the worktree to crew/x/d1 and pushed it; worktree-<name> stays at origin/main.
rm_wt0 rm-mv
(cd "$RM" && git switch -q -c crew/x/d1 && git commit -q --allow-empty -m d1 && git push -q origin crew/x/d1 2>/dev/null)
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && ! has_branch crew/x/d1 && ! has_branch worktree-rm-mv \
  && rjson "o['branch'] == 'crew/x/d1'" \
  && bjson "n == ['crew/x/d1', 'worktree-rm-mv'] and all(x['deleted'] and x['unproven_commits'] == [] and x['checked_out'] is None for x in b.values())" && r=0
check 'remove --delete-branch deletes the moved branch that origin holds and worktree-<name> at an ancestor of origin/main' $r

# worktree-<name> and the moved branch at the same unpushed commit: neither proves the other.
rm_wt0 rm-same
(cd "$RM" && git switch -q -c crew/x/same)
sha=$(unpushed "$RM" same)
(cd "$CO" && git branch -f -q worktree-rm-same "$sha")
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && has_branch crew/x/same && has_branch worktree-rm-same \
  && bjson "n == ['crew/x/same', 'worktree-rm-same'] and all(not x['deleted'] and x['unproven_commits'] == ['$sha'] for x in b.values())" && r=0
check 'remove --delete-branch keeps worktree-<name> and the moved branch at the same unpushed commit, each with the commit in unproven_commits' $r
(cd "$CO" && git branch -D -q crew/x/same worktree-rm-same)

# A branch whose head is refs/pull/7/head in the origin and on no other ref.
rm_wt0 rm-pr
sha=$(unpushed "$RM" pr7)
(cd "$RM" && git push -q origin HEAD:refs/pull/7/head 2>/dev/null)
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && has_branch worktree-rm-pr \
  && bjson "b['worktree-rm-pr']['deleted'] is False and b['worktree-rm-pr']['unproven_commits'] == ['$sha']" && r=0
check 'remove --delete-branch with no --pr keeps a branch that only refs/pull/7/head holds' $r
(cd "$CO" && git worktree add -q "$RM" worktree-rm-pr)
run remove "$RM" --delete-branch --pr 7
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && ! has_branch worktree-rm-pr && [ ! -s "$T/err" ] \
  && bjson "b['worktree-rm-pr']['deleted'] is True and b['worktree-rm-pr']['unproven_commits'] == []" && r=0
check 'remove --delete-branch --pr 7 deletes a branch whose head is refs/pull/7/head' $r
check 'remove --pr reads the PR head with ls-remote origin refs/pull/<n>/head' \
  $(grep -sq '|ls-remote|origin|refs/pull/7/head|' "$T/git.log"; echo $?)
# The PR head is a later commit that the checkout does not have: remove fetches it.
rm_wt0 rm-pr9
(cd "$RM" && git commit -q --allow-empty -m pr9 && git push -q origin HEAD:refs/pull/9/base 2>/dev/null)
(cd "$T/seed" && git fetch -q origin refs/pull/9/base && z=$(git commit-tree -p FETCH_HEAD -m z 'FETCH_HEAD^{tree}') \
  && git push -q origin "$z:refs/pull/9/head" 2>/dev/null && echo "$z" > "$T/z")
z=$(cat "$T/z")
r=1; ! (cd "$CO" && git cat-file -e "$z^{commit}" 2>/dev/null) && r=0
run remove "$RM" --delete-branch --pr 9
r2=1; [ "$r" = 0 ] && [ "$rc" = 0 ] && ! has_branch worktree-rm-pr9 && grep -sq '|fetch|-q|origin|refs/pull/9/head|' "$T/git.log" \
  && bjson "b['worktree-rm-pr9']['deleted'] is True" && r2=0
check 'remove --pr fetches a PR head that is not in the local object store, then it counts as a keeper' $r2

# Goal records under $CREW_RECORD_ROOT. A record of this worktree names a
# deliverable branch and a worktrees.json branch. A review record and a record
# of another repo name branches that stay.
reset_stub
rm_wt0 rm-rec
c2=$(cd "$CO" && git commit-tree -p origin/main -m d2 'origin/main^{tree}')
(cd "$CO" && git branch -q crew/rec/d1 origin/main && git branch -q crew/rec/d2 "$c2" && git branch -q crew/rec/t1 origin/main \
  && git branch -q crew/rev/b origin/main && git branch -q crew/oth/b origin/main)
# run.repo through /var, not /private/var: remove makes it real.
lnk="$T/link-co"; ln -s "$CO" "$lnk"
mkdir -p "$T/records/a-goal" "$T/records/b-review" "$T/records/c-other" "$T/records/d-bad"
printf '{"run": {"repo": "%s", "created_at": "%s"}, "deliverables": [{"id": "d1", "branch": "crew/rec/d1"}, {"id": "d2", "branch": "crew/rec/d2"}, {"id": "d3", "branch": "main"}]}\n' \
  "$lnk/.claude/worktrees/rm-rec" "$(now_iso)" > "$T/records/a-goal/state.json"
printf '{"t1": {"worktree": "/x", "branch": "crew/rec/t1", "session_ids": [], "orphaned": false}}\n' > "$T/records/a-goal/worktrees.json"
printf '{"run": {"repo": "%s", "kind": "review"}, "deliverables": [{"id": "d1", "branch": "crew/rev/b"}]}\n' "$RM" > "$T/records/b-review/state.json"
printf '{"run": {"repo": "%s"}, "deliverables": [{"id": "d1", "branch": "crew/oth/b"}]}\n' "$CO" > "$T/records/c-other/state.json"
printf '{not json' > "$T/records/d-bad/state.json"
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && ! has_branch worktree-rm-rec && ! has_branch crew/rec/d1 && ! has_branch crew/rec/t1 && has_branch crew/rec/d2 \
  && bjson "n == ['worktree-rm-rec', 'crew/rec/d1', 'crew/rec/d2', 'crew/rec/t1'] and b['crew/rec/d1']['deleted'] and b['crew/rec/t1']['deleted'] and not b['crew/rec/d2']['deleted'] and b['crew/rec/d2']['unproven_commits'] == ['$c2']" && r=0
check 'remove --delete-branch reads the goal record of the worktree: each proven deliverable and worktrees.json branch is deleted, an unproven one is kept and listed' $r
check 'a record with run.kind review names no candidate: its branch stays' $(has_branch crew/rev/b && bjson "'crew/rev/b' not in n"; echo $?)
check 'a record whose run.repo is another path names no candidate: its branch stays' $(has_branch crew/oth/b && bjson "'crew/oth/b' not in n"; echo $?)
check 'a branch that equals the default branch name is never a candidate' $(has_branch main && bjson "'main' not in n"; echo $?)
check 'an unreadable state.json under the record root gives one stderr line that names it, and the other records still count' \
  $([ "$(grep -c 'd-bad/state.json' "$T/err")" = 1 ] && bjson "'crew/rec/d1' in n"; echo $?)
rm -rf "$T/records/"*
(cd "$CO" && git branch -D -q crew/rec/d2 crew/rev/b crew/oth/b)

# An earlier item had a worktree at the same path. Its record is older than
# the worktree, so its branches are no candidates. A record with no
# run.created_at is skipped with one stderr line.
rm_wt0 rm-again
(cd "$CO" && git branch -q crew/old/b origin/main && git branch -q crew/new/b origin/main && git branch -q crew/noc/b origin/main)
mkdir -p "$T/records/old" "$T/records/new" "$T/records/noc"
printf '{"run": {"repo": "%s", "created_at": "2000-01-01T00:00:00Z"}, "deliverables": [{"id": "d1", "branch": "crew/old/b"}]}\n' "$RM" > "$T/records/old/state.json"
printf '{"run": {"repo": "%s", "created_at": "%s"}, "deliverables": [{"id": "d1", "branch": "crew/new/b"}]}\n' "$RM" "$(now_iso)" > "$T/records/new/state.json"
printf '{"run": {"repo": "%s"}, "deliverables": [{"id": "d1", "branch": "crew/noc/b"}]}\n' "$RM" > "$T/records/noc/state.json"
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && has_branch crew/old/b && ! has_branch crew/new/b && has_branch crew/noc/b \
  && bjson "n == ['worktree-rm-again', 'crew/new/b']" && r=0
check 'two records of the same worktree path: only the record made after the worktree names candidates' $r
check 'a record of the worktree with no run.created_at is skipped with one stderr line that names it' \
  $([ "$(grep -c 'noc/state.json' "$T/err")" = 1 ] && [ "$(lines "$T/err")" = 1 ]; echo $?)
rm -rf "$T/records/"*
(cd "$CO" && git branch -D -q crew/old/b crew/noc/b)

# A proven candidate that another worktree has checked out stays.
rm_wt0 rm-co
(cd "$RM" && git switch -q -c crew/co/x)
(cd "$CO" && git worktree add -q "$T/other-wt" worktree-rm-co)
owt=$(cd "$T/other-wt" && pwd -P)
run remove "$RM" --delete-branch
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && has_branch worktree-rm-co && ! has_branch crew/co/x \
  && bjson "b['worktree-rm-co']['deleted'] is False and b['worktree-rm-co']['unproven_commits'] == [] and b['worktree-rm-co']['checked_out'] == '$owt' and b['crew/co/x']['deleted'] is True" && r=0
check 'remove --delete-branch keeps a proven candidate that another worktree has checked out, and checked_out names that path' $r
check 'a candidate kept because another worktree has it checked out gets one stderr line that names the branch and the path' \
  $([ "$(lines "$T/err")" = 1 ] && grep -sqF 'worktree-rm-co' "$T/err" && grep -sqF "$owt" "$T/err"; echo $?)
(cd "$CO" && git worktree remove "$T/other-wt" && git branch -D -q worktree-rm-co)

# --pr needs --delete-branch and a positive integer.
rm_wt0 rm-usage
for args in '--pr 7' '--delete-branch --pr 0' '--delete-branch --pr x' '--delete-branch --pr -3'; do
  run remove "$RM" $args
  check "remove $args exits 2 and keeps the worktree" $([ "$rc" = 2 ] && [ -d "$RM" ] && [ "$(lines "$T/err")" = 1 ]; echo $?)
done

# An origin that cannot be reached: the fetch and the ls-remote fail. The
# proof uses the refs that exist. With no origin/HEAD either, main and master
# are never candidates.
(cd "$CO" && git branch -q master origin/main)
mkdir -p "$T/records/net"
printf '{"run": {"repo": "%s", "created_at": "%s"}, "deliverables": [{"id": "d1", "branch": "master"}]}\n' "$RM" "$(now_iso)" > "$T/records/net/state.json"
(cd "$CO" && git remote set-head origin -d)
: > "$STUB_DIR/git-net-fail"
run remove "$RM" --delete-branch --pr 7
rm -f "$STUB_DIR/git-net-fail"
(cd "$CO" && git remote set-head origin main)
r=1; [ "$rc" = 0 ] && [ ! -e "$RM" ] && has_branch worktree-rm-usage && has_branch master \
  && [ "$(lines "$T/err")" = 5 ] && [ "$(grep -c 'fetch' "$T/err")" = 1 ] && [ "$(grep -c 'refs/pull/7/head' "$T/err")" = 1 ] \
  && [ "$(grep -c 'master' "$T/err")" = 1 ] && [ "$(grep -c 'no ref of origin is a keeper' "$T/err")" = 1 ] \
  && [ "$(grep -c 'kept the branch worktree-rm-usage' "$T/err")" = 1 ] \
  && bjson "n == ['worktree-rm-usage'] and b['worktree-rm-usage']['deleted'] is False and b['worktree-rm-usage']['unproven_commits'] != []" && r=0
check 'a failed fetch, a failed ls-remote and no default branch: one stderr line each, exit 0, and with no keeper from origin the branch stays' $r
rm -rf "$T/records/"*
(cd "$CO" && git branch -D -q master worktree-rm-usage)

# -- remove and the lock of a worktree --------------------------------------
# dead_pid: a pid that ran and ended. The test waits for it, so no process has it.
(true & echo $! > "$T/dead"; wait)
dead=$(cat "$T/dead")
locked() { (cd "$CO" && git worktree list --porcelain | grep -A4 -xF "worktree $1" | grep -q '^locked'); }
reset_stub
rm_wt0 rm-lockdead
(cd "$CO" && git worktree lock --reason "claude session x (pid $dead start 1)" "$RM")
run remove "$RM"
r=1; ! alive "$dead" && [ "$rc" = 0 ] && [ ! -e "$RM" ] && grep -sq '|worktree|unlock|' "$T/git.log" \
  && rjson "o['removed'] is True and o['lock'] == {'reason': 'claude session x (pid $dead start 1)', 'pid': $dead, 'unlocked': True}" && r=0
check 'remove of a worktree whose lock names a dead pid unlocks it and removes it' $r
# lock_refused <reason-or-empty> <label>: remove exits 9; the worktree and its lock stay.
lock_refused() {
  rm_wt0 "rm-lock$3"
  if [ -n "$1" ]; then (cd "$CO" && git worktree lock --reason "$1" "$RM"); else (cd "$CO" && git worktree lock "$RM"); fi
  n=$(lines "$T/git.log")
  run remove "$RM"
  r=1; [ "$rc" = 9 ] && [ -d "$RM" ] && locked "$RM" && [ "$(lines "$T/err")" = 1 ] \
    && ! tail -n +"$((n + 1))" "$T/git.log" | grep -sqE '\|worktree\|(unlock|remove)\|' \
    && rjson "o['removed'] is False and o['lock']['unlocked'] is False and o['lock']['pid'] == $4" && r=0
  check "$2" $r
}
p1=$(orphan "$T")
lock_refused "claude session y (pid $p1 start 1)" 'remove of a worktree whose lock names a live pid exits 9, and the worktree and the lock stay' live "$p1"
alive "$p1" || bad 'the live lock owner still runs'
kill "$p1" 2>/dev/null
lock_refused '' 'remove of a worktree with a lock with no reason exits 9 and changes nothing' none None
lock_refused "pid $dead and pid $((dead + 1))" 'remove of a worktree whose lock names two pids exits 9 and changes nothing' two None
lock_refused 'held by pid 1' 'remove of a worktree whose lock names a live pid of another user (pid 1) exits 9' one 1
# The owner runs again right before the unlock: exit 9, no unlock, no removal.
rm_wt0 rm-lockagain
(cd "$CO" && git worktree lock --reason "pid $dead" "$RM")
: > "$T/git.log.sig"
GIT_LOG="$T/git.log.sig" python3 - "$here" "$RM" "$dead" > "$T/out" 2> "$T/err" <<'PY'
import os, sys
sys.path.insert(0, sys.argv[1])
import launcher
pid = int(sys.argv[3])
real_kill = os.kill
tests = [0]
def kill(p, sig):
    if p == pid and sig == 0:
        tests[0] += 1
        if tests[0] == 1:
            raise ProcessLookupError(3, "No such process")
        return None
    return real_kill(p, sig)
os.kill = kill
sys.exit(launcher.main(["remove", sys.argv[2]]))
PY
rc=$?
r=1; [ "$rc" = 9 ] && [ -d "$RM" ] && locked "$RM" && [ "$(lines "$T/err")" = 1 ] \
  && ! grep -sqE '\|worktree\|(unlock|remove)\|' "$T/git.log.sig" && rjson "o['removed'] is False and o['lock']['unlocked'] is False" && r=0
check 'remove of a worktree whose dead lock owner runs again right before the unlock exits 9 and unlocks nothing' $r
(cd "$CO" && git worktree unlock "$RM")
mkdir -p "$T/plain"
for p in "$T/plain" "$T/nothing-here" "$CO"; do
  run remove "$p"
  check "remove of $(basename "$p"), not a linked worktree, exits 2" $([ "$rc" = 2 ] && [ "$(lines "$T/err")" = 1 ]; echo $?)
done
run remove "$RM" --force
check 'remove has no --force flag: exit 2' $([ "$rc" = 2 ] && [ -d "$RM" ]; echo $?)

# -- no Claude Code variable reaches tmux ----------------------------------
# A tmux server that the launcher starts passes its environment to every
# window, so a claude in it would read the orchestrator's session variables.
reset_stub
echo '%7' > "$STUB_DIR/tmux-panes"
printf '$1\tcrew\n' > "$STUB_DIR/tmux-sessions"
export CLAUDECODE=1 CLAUDE_CODE_SSE_PORT=4242 CLAUDE_CODE_ENTRYPOINT=cli
TMUX=/tmp/t,1,0 run start --name env-1 --model m --principal p --checkout "$CO"
r1=$rc
TMUX=/tmp/t,1,0 run resume --name env-1 --worktree "$CO/.claude/worktrees/env-1" --session-id s-1
r1r=$rc
TMUX=/tmp/t,1,0 run groups
TMUX=/tmp/t,1,0 run focus 'tmux:%7'
run focus 'tmux:%7'
run stop 'tmux:%7'
unset CLAUDECODE CLAUDE_CODE_SSE_PORT CLAUDE_CODE_ENTRYPOINT
r=1; [ "$r1" = 0 ] && [ "$r1r" = 0 ] && [ "$(grep -c '^new-' "$STUB_DIR/tmux.log")" = 2 ] && grep -sq '^new-session|' "$STUB_DIR/tmux.log" && grep -sq '^list-sessions|' "$STUB_DIR/tmux.log" \
  && grep -sq '^list-clients|' "$STUB_DIR/tmux.log" && grep -sq '^kill-pane|' "$STUB_DIR/tmux.log" \
  && [ ! -s "$STUB_DIR/tmux-env" ] && r=0
check 'no tmux call of start, resume, groups, focus or stop gets CLAUDECODE or a CLAUDE_CODE_* variable' $r

# -- what launcher.py never does -------------------------------------------
check 'launcher.py imports no iterm2 module' $(! grep -sqE '^\s*(import|from) iterm2' "$L"; echo $?)
check 'launcher.py runs no git clone: the git log of every run holds worktree add and no clone' \
  $(grep -sq '|worktree|add|' "$T/git.log" && ! grep -sqE '(^|\|)clone\|' "$T/git.log"; echo $?)

echo "$((total - fails)) of $total checks passed"
[ "$fails" = 0 ]

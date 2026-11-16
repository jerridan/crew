#!/bin/bash
# Seeded test of launcher.py (issue 152, R5).
#
# usage: bash skills/orchestrator/scripts/test-launcher.sh
#
# It puts stub `tmux`, `osascript`, `uv` and `claude` commands first in PATH,
# builds a bare origin and a checkout whose local main is older than the main
# of the origin, and runs launcher.py once per case. It makes no network call,
# opens no real tab, window or group, and starts no real `claude`. It exits 0
# only when every check passes.

set -u
here=$(cd "$(dirname "$0")" && pwd)
L="$here/launcher.py"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fails=0
total=0

mkdir -p "$T/bin" "$T/home" "$T/stub"
export STUB_DIR="$T/stub"
export HOME="$T/home"
export GIT_CONFIG_NOSYSTEM=1
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@example.com
export GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@example.com
unset CREW_LAUNCHER_CLAUDE TMUX TMUX_PANE TERM_PROGRAM ITERM_SESSION_ID

# tmux stub. It logs each call as one line, args joined by `|`, and each
# CLAUDECODE or CLAUDE_CODE_* variable it gets to tmux-env. Files under
# $STUB_DIR set its answers: tmux-has (the session exists), tmux-fail (new
# windows fail), tmux-panes (one known pane id per line), tmux-sessions (the
# list-sessions output), tmux-clients (the list-clients output).
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
    [ "$1" = display-message ] && echo 'crew'
    exit 0 ;;
  list-sessions) [ -e "$D/tmux-sessions" ] || { echo 'no server running' >&2; exit 1; }; cat "$D/tmux-sessions" ;;
  list-clients) cat "$D/tmux-clients" 2>/dev/null; exit 0 ;;
  *) exit 0 ;;
esac
STUB

# osascript stub. It logs its args and the script on stdin. Files: osa-fail
# (every call fails), osa-sessions (one known iTerm2 session id per line).
cat > "$T/bin/osascript" <<'STUB'
#!/bin/bash
D=$STUB_DIR
line=''
for a in "$@"; do line="$line$a|"; done
printf '%s\n' "$line" >> "$D/osa.log"
cat > "$D/osa-script"
[ -e "$D/osa-fail" ] && { echo "execution error: iTerm2 got an error" >&2; exit 1; }
case "$2" in
  start) echo 'OSA-0001' ;;
  focus|stop) if grep -sqxF -- "$3" "$D/osa-sessions" 2>/dev/null; then echo ok; else echo gone; fi ;;
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
run() {
  python3 "$L" "$@" > "$T/out" 2> "$T/err"
  rc=$?
}
lines() { grep -c . "$1" | tr -d ' '; }
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
want = {"session_name", "repo", "worktree", "branch", "base", "model", "terminal", "tab", "tab_group"}
sys.exit(0 if set(o) == want else 1)
PY
check 'stdout is one line, one JSON object with exactly the nine fields' $r
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
expect_args=$(printf '%s\n' "$WT" --name review-x --model "$MODEL" --settings '{"remoteControlAtStartup": false}' "$PROMPT")
check 'claude runs in the worktree with --name, --model, the RC-off --settings and the wait prompt, quotes intact' \
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


class Tab:
    tab_id = "T1"
    tab_group = None

    def __init__(self):
        self.current_session = Session()


class Window:
    window_id = "W1"
    tab_groups = []

    async def async_create_tab(self, select=True):
        log("create_tab select=%s" % select)
        return Tab()

    async def async_create_tab_group(self, name, tabs, color):
        raise Boom("group failed")


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
helper '' --group grp
r=1; [ "$rc" = 0 ] && has '{"typed": "FAKE-1"}' && ! grep -sq close "$STUB_DIR/fake.log" \
  && [ "$(tail -n 1 "$T/out" | python3 -c 'import json,sys; o=json.load(sys.stdin); print(o["session_id"], o["tab_group"], "group failed" in o["warning"])')" = 'FAKE-1 None True' ] && r=0
check 'helper: a failed group step after the command reports the tab with a warning and exits 0' $r
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

# -- no Claude Code variable reaches tmux ----------------------------------
# A tmux server that the launcher starts passes its environment to every
# window, so a claude in it would read the orchestrator's session variables.
reset_stub
echo '%7' > "$STUB_DIR/tmux-panes"
printf '$1\tcrew\n' > "$STUB_DIR/tmux-sessions"
export CLAUDECODE=1 CLAUDE_CODE_SSE_PORT=4242 CLAUDE_CODE_ENTRYPOINT=cli
TMUX=/tmp/t,1,0 run start --name env-1 --model m --principal p --checkout "$CO"
r1=$rc
TMUX=/tmp/t,1,0 run groups
TMUX=/tmp/t,1,0 run focus 'tmux:%7'
run focus 'tmux:%7'
run stop 'tmux:%7'
unset CLAUDECODE CLAUDE_CODE_SSE_PORT CLAUDE_CODE_ENTRYPOINT
r=1; [ "$r1" = 0 ] && grep -sq '^new-session|' "$STUB_DIR/tmux.log" && grep -sq '^list-sessions|' "$STUB_DIR/tmux.log" \
  && grep -sq '^list-clients|' "$STUB_DIR/tmux.log" && grep -sq '^kill-pane|' "$STUB_DIR/tmux.log" \
  && [ ! -s "$STUB_DIR/tmux-env" ] && r=0
check 'no tmux call of start, groups, focus or stop gets CLAUDECODE or a CLAUDE_CODE_* variable' $r

# -- what launcher.py never does -------------------------------------------
check 'launcher.py imports no iterm2 module' $(! grep -sqE '^\s*(import|from) iterm2' "$L"; echo $?)
check 'launcher.py runs no git clone' $(! grep -sq "clone" "$L"; echo $?)

echo "$((total - fails)) of $total checks passed"
[ "$fails" = 0 ]

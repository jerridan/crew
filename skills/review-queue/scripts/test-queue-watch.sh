#!/bin/bash
# Seeded test of queue-watch.sh (AC1 to AC3 of issue 141).
#
# usage: bash skills/review-queue/scripts/test-queue-watch.sh
#
# It builds a queue directory and a record root under a temp directory, puts
# a stub `gh` and a stub `tmux` first in PATH, and runs `queue-watch.sh ...
# once` pass by pass. The stubs read their answers from files under
# $STUB_DIR, so each pass can change them. It exits 0 only when every check
# passes.

set -u
here=$(cd "$(dirname "$0")" && pwd)
QW="$here/queue-watch.sh"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
ORIG_PATH=$PATH
fails=0
total=0

mkdir -p "$T/bin"
cat > "$T/bin/gh" <<'STUB'
#!/bin/bash
D=$STUB_DIR
echo "$*" >> "$D/gh.log"
args="$*"
n=''
case "$args" in
  *"/pull/"*) n=${args##*/pull/}; n=${n%% *} ;;
  *"/pulls/"*) n=${args##*/pulls/}; n=${n%%/*} ;;
  *"/issues/"*) n=${args##*/issues/}; n=${n%%/*} ;;
  *"-F n="*) n=${args##*-F n=}; n=${n%% *} ;;
esac
case "$args" in
  "search prs"*)
    [ -e "$D/fail-search" ] && exit 1
    cat "$D/search.json"; exit 0 ;;
esac
[ -n "$n" ] && [ -e "$D/fail-gh-$n" ] && exit 1
case "$args" in
  "pr view"*isDraft*) echo false ;;
  "pr view"*headRefOid*) cat "$D/head-$n" ;;
  "pr view"*state,mergedAt*) cat "$D/state-$n" ;;
  "api graphql"*) cat "$D/queue-$n" ;;
  "api repos/"*"/commits/"*) echo alice ;;
esac
exit 0
STUB
cat > "$T/bin/tmux" <<'STUB'
#!/bin/bash
D=$STUB_DIR/tmux
echo "$*" >> "$STUB_DIR/tmux.log"
if [ -e "$D/error" ]; then echo 'tmux: unexpected failure' >&2; exit 1; fi
cmd=$1; shift
name=''
while [ $# -gt 0 ]; do
  case "$1" in -t) name=${2#=}; shift ;; esac
  shift
done
case "$cmd" in
  has-session)
    [ -e "$D/alive-$name" ] && exit 0
    echo "can't find session: $name" >&2; exit 1 ;;
  display-message) cat "$D/created-$name" ;;
  capture-pane) cat "$D/pane-$name" ;;
esac
exit 0
STUB
chmod +x "$T/bin/gh" "$T/bin/tmux"

SHA_A=$(printf 'a%.0s' $(seq 1 40))
SHA_B=$(printf 'b%.0s' $(seq 1 40))
Q=''; REC=''; S=''; OUT=''; RC=0
C1=review-acme-widget-1
C2=review-acme-widget-2

# Make a fresh queue: a board owned by S, rows 1 and 2 open, row 3 done.
seed() {
  rm -rf "$T/c"
  REC=$T/c/rec; Q=$REC/queue; S=$T/c/stub
  mkdir -p "$Q" "$S/tmux" "$T/c/home/.claude/secrets"
  export STUB_DIR=$S CREW_RECORD_ROOT=$REC HOME=$T/c/home
  PATH=$T/bin:$ORIG_PATH
  write_board S
  local n
  for n in 1 2 3; do
    mkdir -p "$Q/prs/acme-widget-$n"
    cat > "$Q/prs/acme-widget-$n/state.json" <<EOF
{"deliverables":[{"id":"d1","pr_url":"https://github.com/acme/widget/pull/$n"}],
 "run":{"watch":{"draft":false,"head":"$SHA_A","last_polled_at":"2026-01-01T00:00:00Z","seen_ids":[],"held":[],"queued":false}}}
EOF
    echo "$SHA_A" > "$S/head-$n"
    echo 'OPEN null' > "$S/state-$n"
    echo out > "$S/queue-$n"
  done
  echo '[]' > "$S/search.json"
  for n in 1 2; do
    mkdir -p "$REC/pr-acme-widget-$n-aaaa/reviews"
    echo '{}' > "$REC/pr-acme-widget-$n-aaaa/state.json"
    touch -t 202001010000 "$REC/pr-acme-widget-$n-aaaa/state.json"
    touch "$S/tmux/alive-review-acme-widget-$n"
    echo 1700000000 > "$S/tmux/created-review-acme-widget-$n"
    echo 'working... esc to interrupt' > "$S/tmux/pane-review-acme-widget-$n"
  done
}

write_board() {
  cat > "$Q/board.json" <<EOF
{"version":1,"owner":{"session_id":"$1","since":"2026-01-01T00:00:00Z"},
 "updated_at":"2026-01-01T00:00:00Z","asks_through":null,
 "watches":[{"id":"review-requests","source":"github:review-requests","policy":"review","status":"active","since":"2026-01-01T00:00:00Z","last_checked":null,"found":0}],
 "rows":[
  {"repo":"acme/widget","pr":1,"title":"one","author":"x","stage":"reviewing","next":"crew","head":"$SHA_A","last":{"at":"2026-01-01T00:00:00Z","text":"t"},"url":"https://github.com/acme/widget/pull/1","watch":"review-requests","policy":"review"},
  {"repo":"acme/widget","pr":2,"title":"two","author":"x","stage":"reviewing","next":"crew","head":"$SHA_A","last":{"at":"2026-01-01T00:00:00Z","text":"t"},"url":"https://github.com/acme/widget/pull/2","watch":"review-requests","policy":"review"},
  {"repo":"acme/widget","pr":3,"title":"three","author":"x","stage":"merged","next":"-","head":"$SHA_A","last":{"at":"2026-01-01T00:00:00Z","text":"t"},"url":"https://github.com/acme/widget/pull/3","watch":"review-requests","policy":"review"}
 ]}
EOF
}

run_pass() {
  OUT=$(bash "$QW" "$Q" S once 2>"$T/stderr"); RC=$?
}

ok() { # name, condition result
  total=$((total + 1))
  if [ "$2" = 0 ]; then return 0; fi
  fails=$((fails + 1))
  printf 'FAIL: %s\n' "$1"
  printf '  output: %s\n' "$(printf '%s' "$OUT" | tr '\n' '|')"
  [ ! -s "$T/stderr" ] || printf '  stderr: %s\n' "$(head -3 "$T/stderr" | tr '\n' '|')"
}

kinds() { printf '%s\n' "$OUT" | awk 'NF{print $1}' | sort | tr '\n' ' '; }

expect_kinds() { # name, expected kinds (sorted, space separated, trailing space)
  [ "$(kinds)" = "$2 " ] || [ -z "$2" -a -z "$(kinds)" ]
  ok "$1 (kinds: $(kinds))" $?
}

# AC1: no token. First pass silent, then one line of each kind.
seed
run_pass
expect_kinds 'AC1 first pass is silent' ''
[ -f "$Q/watch-S.json" ]; ok 'AC1 first pass writes the state file' $?
echo "$SHA_B" > "$S/head-1"
echo 2026-02-01T00:00:00Z > "$S/queue-2"
echo '{}' > "$REC/pr-acme-widget-1-aaaa/ready.json"
echo '[{"number":9,"repository":{"nameWithOwner":"acme/widget"},"url":"https://github.com/acme/widget/pull/9","title":"n","author":{"login":"z"}}]' > "$S/search.json"
echo 'Do you want to proceed?' > "$S/tmux/pane-$C2"
run_pass
expect_kinds 'AC1 one line of each kind' 'ask child-prompt push queued ready'
printf '%s\n' "$OUT" | grep -q "^push acme/widget#1 $SHA_B "; ok 'AC1 push line shape' $?
printf '%s\n' "$OUT" | grep -q "^queued acme/widget#2 2 "; ok 'AC1 queued line shape' $?
printf '%s\n' "$OUT" | grep -q "^ready acme/widget#1 $REC/pr-acme-widget-1-aaaa/ready.json\$"; ok 'AC1 ready line shape' $?
printf '%s\n' "$OUT" | grep -q '^ask acme/widget#9 https://github.com/acme/widget/pull/9$'; ok 'AC1 ask line shape' $?
printf '%s\n' "$OUT" | grep -q "^child-prompt acme/widget#2 -\$"; ok 'AC1 child-prompt line shape' $?
run_pass
expect_kinds 'AC1 third pass with no change is silent' ''
echo out > "$S/queue-2"
run_pass
expect_kinds 'AC1 leaving the queue (seed queued false) is silent' ''
echo 2026-02-01T00:00:00Z > "$S/queue-2"
run_pass
expect_kinds 'AC1 entering the queue again prints queued again' 'queued'
! grep -q 'pull/3' "$S/gh.log"; ok 'AC1 the done row is never polled' $?

# AC1: a token. No ask line, no gh search call.
seed
echo 'xoxp-secret' > "$HOME/.claude/secrets/slack-token"
run_pass
echo '[{"number":9,"repository":{"nameWithOwner":"acme/widget"},"url":"https://github.com/acme/widget/pull/9","title":"n","author":{"login":"z"}}]' > "$S/search.json"
run_pass
expect_kinds 'AC1 token: no ask line' ''
! grep -q 'search' "$S/gh.log"; ok 'AC1 token: no gh search call' $?
! printf '%s%s' "$OUT" "$(cat "$T/stderr")" | grep -q 'xoxp-secret'; ok 'AC1 token is never printed' $?

# AC1: dequeued with queued true in the seed.
seed
jq '.run.watch.queued = true' "$Q/prs/acme-widget-2/state.json" > "$T/s.json" && mv "$T/s.json" "$Q/prs/acme-widget-2/state.json"
echo 2026-02-01T00:00:00Z > "$S/queue-2"
run_pass
expect_kinds 'AC1 dequeue: first pass silent' ''
echo out > "$S/queue-2"
run_pass
expect_kinds 'AC1 dequeue: one dequeued line' 'dequeued'
run_pass
expect_kinds 'AC1 dequeue: second pass silent' ''

# AC1: merged and closed.
seed
run_pass
echo 'MERGED 2026-02-01T00:00:00Z' > "$S/state-1"
echo 'CLOSED null' > "$S/state-2"
run_pass
expect_kinds 'AC1 one merged and one closed' 'closed merged'
run_pass
expect_kinds 'AC1 merged and closed print once' ''

# AC1: a failed pass prints nothing and forgets nothing.
seed
echo 2026-02-01T00:00:00Z > "$S/queue-2"
echo '[{"number":9,"repository":{"nameWithOwner":"acme/widget"},"url":"https://github.com/acme/widget/pull/9","title":"n","author":{"login":"z"}}]' > "$S/search.json"
run_pass
touch "$S/fail-gh-2" "$S/fail-search"
run_pass
expect_kinds 'AC1 failed pass is silent' ''
rm "$S/fail-gh-2" "$S/fail-search"
run_pass
expect_kinds 'AC1 pass after a failed pass does not print held events' ''

# AC2: child-idle on the third idle pass.
seed
echo 'idle prompt' > "$S/tmux/pane-$C1"
run_pass; run_pass
expect_kinds 'AC2 no child-idle before the third pass' ''
run_pass
expect_kinds 'AC2 child-idle on the third pass' 'child-idle'
printf '%s\n' "$OUT" | grep -q '^child-idle acme/widget#1 -$'; ok 'AC2 child-idle line shape' $?
run_pass
expect_kinds 'AC2 child-idle prints once' ''
echo 'working... esc to interrupt' > "$S/tmux/pane-$C1"
run_pass
echo 'idle prompt' > "$S/tmux/pane-$C1"
run_pass; run_pass; run_pass
expect_kinds 'AC2 busy again resets the count and a later stop prints again' 'child-idle'

# AC2: no child-idle while a skeptical review runs, or a file changed.
seed
echo 'idle prompt' > "$S/tmux/pane-$C1"
d=$REC/pr-acme-widget-1-aaaa
touch "$d/reviews/skeptical-r1-result.stderr"; touch -t 202001010000 "$d/reviews/skeptical-r1-result.stderr"
run_pass; run_pass; run_pass; run_pass
expect_kinds 'AC2 no child-idle while a review runs' ''
touch "$d/reviews/skeptical-r1-result.exit"; touch -t 202001010000 "$d/reviews/skeptical-r1-result.exit"
run_pass
expect_kinds 'AC2 child-idle once the review has an exit file' 'child-idle'
seed
echo 'idle prompt' > "$S/tmux/pane-$C1"
touch "$REC/pr-acme-widget-1-aaaa/fresh.txt"
run_pass; run_pass; run_pass; run_pass
expect_kinds 'AC2 no child-idle after a recent file change' ''

# AC2: child-gone for a child seen alive, never for one never seen.
seed
rm "$S/tmux/alive-$C2"
run_pass
rm "$S/tmux/alive-$C1"
run_pass
expect_kinds 'AC2 child-gone for the child seen alive only' 'child-gone'
printf '%s\n' "$OUT" | grep -q '^child-gone acme/widget#1 -$'; ok 'AC2 child-gone line shape' $?
run_pass
expect_kinds 'AC2 child-gone prints once' ''

# AC2: a tmux error is a failure, never child-gone.
seed
run_pass
touch "$S/tmux/error"
run_pass
expect_kinds 'AC2 tmux error is silent' ''
rm "$S/tmux/error"
run_pass
expect_kinds 'AC2 pass after a tmux error is silent' ''

# AC3: not the owner.
seed
run_pass
before=$(cksum < "$Q/watch-S.json")
write_board T
echo "$SHA_B" > "$S/head-1"
run_pass
[ "$OUT" = 'not-owner - -' ]; ok 'AC3 prints not-owner - -' $?
[ "$RC" = 0 ]; ok 'AC3 exits 0' $?
[ "$(cksum < "$Q/watch-S.json")" = "$before" ]; ok 'AC3 leaves the state file alone' $?

if [ "$fails" -gt 0 ]; then
  printf '%s of %s checks failed\n' "$fails" "$total"
  exit 1
fi
printf 'all %s checks passed\n' "$total"

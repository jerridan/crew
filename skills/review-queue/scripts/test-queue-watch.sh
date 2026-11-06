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
# A hook: a test rewrites the board while a pass runs. It runs once.
if [ -e "$D/on-gh" ]; then h=$D/on-gh; mv "$h" "$h.run"; bash "$h.run"; fi
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
  "api graphql"*"-F n="*)
    [ -e "$D/fail-queue-$n" ] && exit 1
    cat "$D/queue-$n" ;;
  "api graphql"*)
    # The batched read: one alias for each open row.
    [ -e "$D/fail-batch" ] && exit 1
    rc=0; sep=''; body=''
    while read -r al num; do
      [ -n "$al" ] || continue
      if [ -e "$D/fail-gh-$num" ]; then
        body="$body$sep\"$al\":null"; rc=1
      else
        st=$(cut -d' ' -f1 "$D/state-$num"); q=$(cat "$D/queue-$num")
        if [ "$q" = out ]; then qq='"isInMergeQueue":false,"mergeQueueEntry":null'
        else qq="\"isInMergeQueue\":true,\"mergeQueueEntry\":{\"enqueuedAt\":\"$q\"}"; fi
        body="$body$sep\"$al\":{\"pullRequest\":{\"headRefOid\":\"$(cat "$D/head-$num")\",\"state\":\"$st\",$qq}}"
      fi
      sep=','
    done < <(printf '%s' "$args" | grep -o 'r[0-9]*: repository([^)]*) { pullRequest(number: [0-9]*)' | sed -E 's/^(r[0-9]+):.*number: ([0-9]+)\)$/\1 \2/')
    printf '{"data":{%s}}\n' "$body"
    exit $rc ;;
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
# Real tmux reads a dot in a target as a pane separator, unless a colon ends it.
case "$name" in
  *:) name=${name%:} ;;
  *.*) echo "can't find pane: ${name##*.}" >&2; exit 1 ;;
esac
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
  : > "$S/gh.log"
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
  local got want=0
  got=$(kinds)
  if [ -z "$2" ]; then [ -z "$got" ] || want=1; else [ "$got" = "$2 " ] || want=1; fi
  ok "$1 (kinds: $got)" "$want"
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

# AC1: a token and a fresh review-requests watch. No ask line, no gh search call.
fresh_asks() {
  printf '{"version":1,"updated_at":"%s","watches":{"review-requests":{"last_checked":"%s","found":0}},"asks":[]}\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$(date -u +%Y-%m-%dT%H:%M:%SZ)" > "$Q/asks.json"
}
seed
echo 'xoxp-secret' > "$HOME/.claude/secrets/slack-token"
fresh_asks
run_pass
echo '[{"number":9,"repository":{"nameWithOwner":"acme/widget"},"url":"https://github.com/acme/widget/pull/9","title":"n","author":{"login":"z"}}]' > "$S/search.json"
run_pass
expect_kinds 'AC1 token: no ask line' ''
! grep -q 'search' "$S/gh.log"; ok 'AC1 token: no gh search call' $?
! printf '%s%s' "$OUT" "$(cat "$T/stderr")" | grep -q 'xoxp-secret'; ok 'AC1 token is never printed' $?

# Review item 5: a token and a stale review-requests watch. The script polls it.
seed
echo 'xoxp-secret' > "$HOME/.claude/secrets/slack-token"
run_pass
echo '[{"number":9,"repository":{"nameWithOwner":"acme/widget"},"url":"https://github.com/acme/widget/pull/9","title":"n","author":{"login":"z"}}]' > "$S/search.json"
run_pass
expect_kinds 'review 5 token, no asks file: the stale watch is polled' 'ask'
seed
echo 'xoxp-secret' > "$HOME/.claude/secrets/slack-token"
printf '{"version":1,"updated_at":"2026-01-01T00:00:00Z","watches":{"review-requests":{"last_checked":"2026-01-01T00:00:00Z","found":0}},"asks":[]}\n' > "$Q/asks.json"
run_pass
echo '[{"number":9,"repository":{"nameWithOwner":"acme/widget"},"url":"https://github.com/acme/widget/pull/9","title":"n","author":{"login":"z"}}]' > "$S/search.json"
run_pass
expect_kinds 'review 5 token, old last_checked: the stale watch is polled' 'ask'

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

# Item 4: the first pass prints child-prompt lines and nothing else.
seed
echo 2026-02-01T00:00:00Z > "$S/queue-2"
echo "$SHA_B" > "$S/head-1"
echo 'Do you want to proceed?' > "$S/tmux/pane-$C2"
run_pass
expect_kinds 'item 4 first pass prints child-prompt only' 'child-prompt'
printf '%s\n' "$OUT" | grep -q '^child-prompt acme/widget#2 -$'; ok 'item 4 child-prompt line shape' $?
run_pass
expect_kinds 'item 4 second pass is silent' ''

# Item 1: a failed queue read inside pr-watch.sh keeps the held queued event.
seed
echo 2026-02-01T00:00:00Z > "$S/queue-2"
run_pass
echo "$SHA_B" > "$S/head-2"
touch "$S/fail-queue-2"
run_pass
expect_kinds 'item 1 failed queue read: only the push prints' 'push'
rm "$S/fail-queue-2"
echo "$SHA_A" > "$S/head-2"
run_pass
expect_kinds 'item 1 queued is not printed again after a failed queue read' ''

# Item 1: a merge ends the held queued event.
seed
echo 2026-02-01T00:00:00Z > "$S/queue-2"
run_pass
echo 'MERGED 2026-02-02T00:00:00Z' > "$S/state-2"
run_pass
expect_kinds 'item 1 merged prints after a held queued' 'merged'
echo 'OPEN null' > "$S/state-2"
run_pass
expect_kinds 'item 1 a group that printed merged does not hold queued' 'queued'

# Review item 1: a record directory of PR 12 is not the directory of PR 1.
seed
run_pass
mkdir -p "$REC/pr-acme-widget-12-bbbb"
echo '{}' > "$REC/pr-acme-widget-12-bbbb/ready.json"
mkdir -p "$REC/pr-acme-widget-1-extra-cccc"
echo '{}' > "$REC/pr-acme-widget-1-extra-cccc/ready.json"
run_pass
expect_kinds 'review 1 a longer PR number or a non-hex suffix is not the record directory' ''

# Review item 4: a PR that leaves the queue and enters it again between two
# passes prints queued again.
seed
echo 2026-02-01T00:00:00Z > "$S/queue-2"
run_pass
run_pass
echo 2026-02-02T00:00:00Z > "$S/queue-2"
run_pass
expect_kinds 'review 4 a new enqueuedAt prints queued again' 'queued'
printf '%s\n' "$OUT" | grep -q '^queued acme/widget#2 2 - 2026-02-02T00:00:00Z '; ok 'review 4 the new queued line shape' $?
run_pass
expect_kinds 'review 4 the new queued event prints once' ''
jq -e '[.events[] | select(.g == "pr:acme-widget-2" and (.k | startswith("queued ")))] | length == 1' "$Q/watch-S.json" >/dev/null; ok 'review 4 the state holds one queued event' $?

# Item 2: one batched read for each pass; pr-watch.sh runs only when due.
runs() { local c; c=$(grep -c "pull/$1 --json isDraft" "$S/gh.log"); echo "${c:-0}"; }
batches() { local c; c=$(grep -c 'api graphql.*owner: "' "$S/gh.log"); echo "${c:-0}"; }
seed
run_pass
[ "$(runs 1)" = 1 ] && [ "$(runs 2)" = 1 ]; ok 'item 2 first sight runs pr-watch for each row' $?
run_pass
[ "$(runs 1)" = 1 ] && [ "$(runs 2)" = 1 ]; ok 'item 2 unchanged values run no pr-watch' $?
[ "$(batches)" = 2 ]; ok "item 2 one batched read for each pass" $?
echo "$SHA_B" > "$S/head-1"
run_pass
expect_kinds 'item 2 a changed head prints push' 'push'
[ "$(runs 1)" = 2 ] && [ "$(runs 2)" = 1 ]; ok 'item 2 only the changed row runs pr-watch' $?
for i in 1 2 3 4 5 6 7 8 9; do run_pass; done
[ "$(runs 1)" = 2 ] && [ "$(runs 2)" = 2 ]; ok 'item 2 nine quiet passes run nothing' $?
run_pass
[ "$(runs 1)" = 3 ] && [ "$(runs 2)" = 2 ]; ok 'item 2 the 10th pass after a run forces one' $?
echo "$SHA_A" > "$S/head-1"
touch "$S/fail-gh-2"
run_pass
[ "$(runs 1)" = 4 ] && [ "$(runs 2)" = 2 ]; ok 'item 2 a row the batch could not read runs no pr-watch' $?
rm "$S/fail-gh-2"
touch "$S/fail-batch"
echo "$SHA_B" > "$S/head-1"
run_pass
expect_kinds 'item 2 a failed batch is silent' ''
[ "$(runs 1)" = 4 ]; ok 'item 2 a failed batch runs no pr-watch' $?
rm "$S/fail-batch"
run_pass
[ "$(runs 1)" = 5 ]; ok 'item 2 the change is read when the batch works again' $?

# Patch round 2, item 1: a repo name with a dot. The stub tmux rejects the bare
# target, as real tmux does.
seed
jq '.rows += [{"repo":"acme/next.js","pr":5,"title":"d","author":"x","stage":"reviewing","next":"crew","head":"x","last":{"at":"2026-01-01T00:00:00Z","text":"t"},"url":"u","watch":"review-requests","policy":"review"}]' "$Q/board.json" > "$T/b.json" && mv "$T/b.json" "$Q/board.json"
CD=review-acme-next.js-5
mkdir -p "$REC/pr-acme-next.js-5-aaaa/reviews"
touch "$S/tmux/alive-$CD"
echo 1700000000 > "$S/tmux/created-$CD"
echo 'working... esc to interrupt' > "$S/tmux/pane-$CD"
run_pass
echo '{}' > "$REC/pr-acme-next.js-5-aaaa/ready.json"
run_pass
expect_kinds 'patch 2 item 1 a dotted repo name still gets its ready line' 'ready'
printf '%s\n' "$OUT" | grep -q '^ready acme/next.js#5 '; ok 'patch 2 item 1 the ready line is for the dotted repo' $?
# A child never seen alive gets no line, even with a dot.
seed
jq '.rows += [{"repo":"acme/next.js","pr":5,"title":"d","author":"x","stage":"reviewing","next":"crew","head":"x","last":{"at":"2026-01-01T00:00:00Z","text":"t"},"url":"u","watch":"review-requests","policy":"review"}]' "$Q/board.json" > "$T/b.json" && mv "$T/b.json" "$Q/board.json"
rm -f "$S/tmux/alive-$CD"
run_pass
run_pass
expect_kinds 'patch 2 item 1 a dotted child never seen gets no line' ''

# Patch round 2, item 1: a ready line does not depend on tmux.
seed
run_pass
touch "$S/tmux/error"
echo '{}' > "$REC/pr-acme-widget-1-aaaa/ready.json"
run_pass
expect_kinds 'patch 2 item 1 ready prints while tmux fails' 'ready'

# Patch round 2, item 2: the row leaves its stage during the pass, before its
# child check. No child-gone prints.
seed
run_pass
rm "$S/tmux/alive-$C1"
printf '#!/bin/bash\njq ".rows[0].stage = \\"triage\\"" "%s" > "%s.t" && mv "%s.t" "%s"\n' "$Q/board.json" "$Q/board.json" "$Q/board.json" "$Q/board.json" > "$S/on-gh"
run_pass
expect_kinds 'patch 2 item 2 a re-triage inside the pass prints no child-gone' ''

# Patch round 2, item 3: a held ask stays held across a fresh spell.
seed
echo 'xoxp-secret' > "$HOME/.claude/secrets/slack-token"
run_pass
echo '[{"number":9,"repository":{"nameWithOwner":"acme/widget"},"url":"https://github.com/acme/widget/pull/9","title":"n","author":{"login":"z"}}]' > "$S/search.json"
run_pass
expect_kinds 'patch 2 item 3 the stale watch prints the ask' 'ask'
fresh_asks
run_pass
printf '{"version":1,"updated_at":"2026-01-01T00:00:00Z","watches":{"review-requests":{"last_checked":"2026-01-01T00:00:00Z","found":0}},"asks":[]}\n' > "$Q/asks.json"
run_pass
expect_kinds 'patch 2 item 3 the ask does not print again after a fresh spell' ''

# Patch round 2, item 3: a paused review-requests watch keeps the held ask.
seed
run_pass
echo '[{"number":9,"repository":{"nameWithOwner":"acme/widget"},"url":"https://github.com/acme/widget/pull/9","title":"n","author":{"login":"z"}}]' > "$S/search.json"
run_pass
expect_kinds 'patch 2 item 3 no token: the ask prints' 'ask'
jq '.watches[0].status = "paused"' "$Q/board.json" > "$T/b.json" && mv "$T/b.json" "$Q/board.json"
run_pass
jq '.watches[0].status = "active"' "$Q/board.json" > "$T/b.json" && mv "$T/b.json" "$Q/board.json"
run_pass
expect_kinds 'patch 2 item 3 the ask does not print again after a paused watch' ''

# AC3: not the owner.
seed
run_pass
write_board T
echo "$SHA_B" > "$S/head-1"
run_pass
[ "$OUT" = 'not-owner - -' ]; ok 'AC3 prints not-owner - -' $?
[ "$RC" = 0 ]; ok 'AC3 exits 0' $?
[ ! -e "$Q/watch-S.json" ]; ok 'review 6 not-owner removes the state file' $?

if [ "$fails" -gt 0 ]; then
  printf '%s of %s checks failed\n' "$fails" "$total"
  exit 1
fi
printf 'all %s checks passed\n' "$total"

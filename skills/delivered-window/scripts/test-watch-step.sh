#!/bin/bash
# Seeded test of watch-step.py.
#
# usage: bash skills/delivered-window/scripts/test-watch-step.sh
#
# It builds a record under a temp directory, puts a stub `gh` first in PATH,
# and names a stub poll script in WATCH_STEP_POLL. The record is written by the
# real crew-record.py. It exits 0 only when every check passes.

set -u
here=$(cd "$(dirname "$0")" && pwd)
WS="$here/watch-step.py"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fails=0
total=0

mkdir -p "$T/bin"
cat > "$T/bin/gh" <<'STUB'
#!/bin/bash
D=$STUB_DIR
echo "$*" >> "$D/calls.log"
case "$*" in
  "pr view"*) [ -e "$D/fail-pr" ] && exit 1; cat "$D/pr.json"; exit 0 ;;
  *"/pulls/7/comments"*) [ -e "$D/fail-comments" ] && exit 1; cat "$D/comments.json"; exit 0 ;;
esac
exit 1
STUB
chmod +x "$T/bin/gh"
cat > "$T/poll.sh" <<'STUB'
#!/bin/bash
: > "$STUB_DIR/polled"
echo "POLL $*"
echo "second line"
STUB
chmod +x "$T/poll.sh"

export STUB_DIR="$T/stub"
export PATH="$T/bin:$PATH"
export WATCH_STEP_POLL="$T/poll.sh"
REC="$T/rec"
W0='{"last_polled_at":"2026-01-01T00:00:00Z","seen_ids":[],"draft":true,"head":"h0","held":[]}'
CREATED=2026-01-01T00:00:00Z

# newrec <run json>: a record with one deliverable that has a PR, and the run.
newrec() {
  rm -rf "$STUB_DIR" "$REC"; mkdir -p "$STUB_DIR" "$REC/reviews"
  printf '[]\n' > "$STUB_DIR/comments.json"
  printf '{"isDraft":%s,"createdAt":"%s","headRefOid":"h1"}\n' "${PRDRAFT:-true}" "$CREATED" > "$STUB_DIR/pr.json"
  jq -n --argjson run "$1" '{deliverables:[{id:"deliverable-1",base:"basesha",pr_url:"https://github.com/o/r/pull/7"}],run:$run}' > "$REC/state.json"
}
sum() { cksum < "$REC/state.json"; }
cur() { jq -cS '.run.watch' "$REC/state.json"; }
ws() { out=$(python3 "$WS" "$@" 2>"$T/err"); rc=$?; err=$(cat "$T/err"); }
polled() { [ -e "$STUB_DIR/polled" ] && echo yes || echo no; }
chk() { # label got want
  total=$((total + 1))
  if [ "$2" = "$3" ]; then echo "ok   $1"; else
    fails=$((fails + 1)); echo "FAIL $1"; printf '     got:  %s\n     want: %s\n' "$2" "$3"
  fi
}
want() { jq -cS . <<< "$1"; }

# ---- arm: the first cursor
newrec '{"run_state":"delivered"}'
ws arm "$REC"
chk 'arm first: exit 0' "$rc" 0
chk 'arm first: cursor' "$(cur)" "$(want '{"last_polled_at":"'$CREATED'","seen_ids":[],"draft":true,"head":"h1","held":[]}')"
chk 'arm first: poll ran, stdout is the poll stdout' "$out" "$(printf 'POLL %s\nsecond line' "$REC")"
chk 'arm first: nothing on stderr' "$err" ''

newrec '{"run_state":"delivered","kind":"review"}'
ws arm "$REC"
lp=$(jq -r .run.watch.last_polled_at "$REC/state.json")
chk 'arm review run: last_polled_at is the clock' "$([[ "$lp" =~ ^20[0-9][0-9]-.*Z$ && "$lp" != "$CREATED" ]] && echo yes)" yes

newrec '{"run_state":"delivered"}'
printf '[{"id":11},{"id":12}]\n[{"id":13}]\n' > "$STUB_DIR/comments.json"
ws arm "$REC" --resume
chk 'arm --resume: seen_ids hold every review comment id' "$(jq -c .run.watch.seen_ids "$REC/state.json")" '[11,12,13]'
lp=$(jq -r .run.watch.last_polled_at "$REC/state.json")
chk 'arm --resume: last_polled_at is the clock' "$([[ "$lp" != "$CREATED" ]] && echo yes)" yes
chk 'arm --resume: poll ran' "$(polled)" yes

newrec '{"run_state":"delivered"}'
printf '[{"id":11}]\n' > "$STUB_DIR/comments.json"
ws arm "$REC"
chk 'arm with no --resume: seen_ids empty' "$(jq -c .run.watch.seen_ids "$REC/state.json")" '[]'

# ---- arm: a cursor that exists is not rewritten
newrec '{"run_state":"delivered","watch":'"$W0"'}'
before=$(sum)
ws arm "$REC"
chk 'arm existing cursor: state.json unchanged' "$(sum)" "$before"
chk 'arm existing cursor: no comments read' "$(grep -c 'comments' "$STUB_DIR/calls.log")" 0
chk 'arm existing cursor: poll ran' "$(polled)" yes

# ---- arm: the head fallback
W_NOHEAD='{"last_polled_at":"2026-01-01T00:00:00Z","seen_ids":[],"draft":true,"held":[]}'
newrec '{"run_state":"delivered","watch":'"$W_NOHEAD"'}'
printf 'Reviewed: aaa\n' > "$REC/reviews/skeptical-r1.md"
printf 'Reviewed: bbb\n' > "$REC/reviews/skeptical-r2.md"
printf 'x\nReviewed: ccc\ny\n' > "$REC/reviews/skeptical-r10.md"
ws arm "$REC"
chk 'head fallback: newest skeptical review by number' "$(jq -r .run.watch.head "$REC/state.json")" ccc
chk 'head fallback: the other keys stay' "$(jq -c '.run.watch|del(.head)' "$REC/state.json")" '{"last_polled_at":"2026-01-01T00:00:00Z","seen_ids":[],"draft":true,"held":[]}'
newrec '{"run_state":"delivered","watch":'"$W_NOHEAD"'}'
ws arm "$REC"
chk 'head fallback: the deliverable base when no review' "$(jq -r .run.watch.head "$REC/state.json")" basesha

# ---- arm: the draft write
newrec '{"run_state":"delivered","watch":'"$(jq -c '.draft=false' <<< "$W0")"'}'
ws arm "$REC"
chk 'draft write: PR is draft and watch.draft false' "$(jq -c .run.watch.draft "$REC/state.json")" true
PRDRAFT=false newrec '{"run_state":"delivered","watch":'"$(jq -c '.draft=false' <<< "$W0")"'}'
before=$(sum); ws arm "$REC"
chk 'draft write: PR is not draft, no write' "$(sum)" "$before"
PRDRAFT=false newrec '{"run_state":"delivered","watch":'"$W0"'}'
before=$(sum); ws arm "$REC"
chk 'draft write: PR is not draft and watch.draft true, stays true' "$(sum)" "$before"

# ---- arm: failures exit 2 before the poll, with no write
newrec '{"run_state":"delivered"}'
: > "$STUB_DIR/fail-pr"
before=$(sum); ws arm "$REC"
chk 'failed gh read: exit 2' "$rc" 2
chk 'failed gh read: message prefix' "${err%%:*}" watch-step.py
chk 'failed gh read: no write' "$(sum)" "$before"
chk 'failed gh read: poll did not run' "$(polled)" no
chk 'failed gh read: nothing on stdout' "$out" ''
newrec '{"run_state":"delivered"}'
printf '[{"id":1}]\n' > "$STUB_DIR/comments.json"; : > "$STUB_DIR/fail-comments"
before=$(sum); ws arm "$REC" --resume
chk 'failed comments read on --resume: exit 2, no write' "$rc $(sum)" "2 $before"
ws arm "$T/nowhere"
chk 'missing record: exit 2 with the prefix' "$rc ${err%%:*}" '2 watch-step.py'
newrec '{"run_state":"delivered"}'
ws arm "$REC" --bogus
chk 'unknown flag: exit 2' "$rc" 2

# ---- cursor: the first write alone
newrec '{"run_state":"delivered","kind":"review"}'
ws cursor "$REC"
chk 'cursor: exit 0, nothing printed' "$rc|$out" '0|'
chk 'cursor: the cursor is written' "$(jq -c '.run.watch|[.draft,.head,.held]' "$REC/state.json")" '[true,"h1",[]]'
chk 'cursor: the poll did not run' "$(polled)" no
newrec '{"run_state":"delivered"}'
printf '[{"id":5}]\n' > "$STUB_DIR/comments.json"
ws cursor "$REC" --resume
chk 'cursor --resume: seen_ids' "$(jq -c .run.watch.seen_ids "$REC/state.json")" '[5]'
newrec '{"run_state":"delivered","watch":'"$W0"'}'
before=$(sum); ws cursor "$REC"
chk 'cursor on an existing cursor: no rewrite' "$(sum)" "$before"
chk 'cursor on an existing cursor: no poll' "$(polled)" no
newrec '{"run_state":"delivered","watch":'"$W_NOHEAD"'}'
printf 'Reviewed: ddd\n' > "$REC/reviews/skeptical-r1.md"
ws cursor "$REC"
chk 'cursor: the head fallback' "$(jq -r .run.watch.head "$REC/state.json")" ddd
chk 'cursor: no draft read of the PR' "$(grep -c 'pr view' "$STUB_DIR/calls.log")" 0

# ---- deploy
newrec '{"run_state":"delivered"}'
ws deploy "$REC" --source repo --environment production --timeout 90
chk 'deploy first: the whole object' "$(jq -c '.run.deploy|del(.since)' "$REC/state.json")" '{"environment":"production","workflow":null,"timeout_minutes":90,"source":"repo","ended":null}'
chk 'deploy first: since is a UTC time' "$(jq -r .run.deploy.since "$REC/state.json" | grep -cE '^20[0-9]{2}-[0-9]{2}-[0-9]{2}T[0-9:]{8}Z$')" 1
chk 'deploy first: the poll runs in deploy mode' "$out" "$(printf 'POLL %s deploy\nsecond line' "$REC")"
newrec '{"run_state":"delivered"}'
ws deploy "$REC" --source default --workflow Deploy
chk 'deploy default timeout 180 and workflow' "$(jq -c '.run.deploy|[.timeout_minutes,.workflow,.environment]' "$REC/state.json")" '[180,"Deploy",null]'
D_ENDED='{"environment":"production","workflow":null,"timeout_minutes":90,"source":"repo","since":"2026-01-01T00:00:00Z","ended":"deploy-failed"}'
newrec '{"run_state":"delivered","deploy":'"$D_ENDED"'}'
ws deploy "$REC" --source other --timeout 5
chk 'deploy re-arm after ended: since and ended only' "$(jq -c '.run.deploy|del(.since)' "$REC/state.json")" '{"environment":"production","workflow":null,"timeout_minutes":90,"source":"repo","ended":null}'
chk 'deploy re-arm after ended: since moved' "$(jq -r .run.deploy.since "$REC/state.json")" "$(jq -r .run.deploy.since "$REC/state.json" | grep -v '^2026-01-01T00:00:00Z$')"
chk 'deploy re-arm after ended: poll ran' "$(polled)" yes
D_LIVE=$(jq -c '.ended=null' <<< "$D_ENDED")
newrec '{"run_state":"delivered","deploy":'"$D_LIVE"'}'
before=$(sum); ws deploy "$REC" --source other --timeout 5
chk 'deploy with ended null: no write' "$(sum)" "$before"
chk 'deploy with ended null: poll ran' "$(polled)" yes
newrec '{"run_state":"delivered"}'
ws deploy "$REC"
chk 'deploy without --source: exit 2, no poll' "$rc $(polled)" '2 no'

# ---- ack
ack() { # <hold flags...> with lines in $LINES
  ws ack "$REC" "$@" <<< "$LINES"
}
newack() { newrec '{"run_state":"delivered","watch":'"$W0"'}'; }

newack; LINES='review 101 alice 2026-01-02T00:00:00Z COMMENTED hello there'
ack
chk 'ack review: seen_ids and last_polled_at' "$(jq -c '.run.watch|[.seen_ids,.last_polled_at]' "$REC/state.json")" '[[101],"2026-01-02T00:00:00Z"]'
chk 'ack: one line printed' "$(printf '%s\n' "$out" | grep -c .)" 1

newack; LINES='comment 102 alice 2026-01-03T00:00:00Z a comment'
ack
chk 'ack comment' "$(jq -c '.run.watch|[.seen_ids,.last_polled_at]' "$REC/state.json")" '[[102],"2026-01-03T00:00:00Z"]'

newack; LINES=$'review 1 a 2026-01-05T00:00:00Z APPROVED x\ncomment 2 a 2026-01-04T00:00:00Z y'
ack
chk 'ack: last_polled_at is the newest, not the last line' "$(jq -r .run.watch.last_polled_at "$REC/state.json")" 2026-01-05T00:00:00Z
newrec '{"run_state":"delivered","watch":'"$(jq -c '.last_polled_at="2026-02-01T00:00:00Z"' <<< "$W0")"'}'
LINES='review 3 a 2026-01-05T00:00:00Z APPROVED x'; ack
chk 'ack: last_polled_at never goes back' "$(jq -r .run.watch.last_polled_at "$REC/state.json")" 2026-02-01T00:00:00Z

newack; LINES='review-comment 201 bob 2026-01-09T00:00:00Z a.py:3 fix this'
ack
chk 'ack review-comment: id joins, time does not move' "$(jq -c '.run.watch|[.seen_ids,.last_polled_at]' "$REC/state.json")" '[[201],"2026-01-01T00:00:00Z"]'

newack; LINES='check https://github.com/o/r/actions/runs/5/job/6@2026-01-03T00:00:00Z - 2026-01-03T00:00:00Z CI failed'
ack
chk 'ack check: id joins' "$(jq -c .run.watch.seen_ids "$REC/state.json")" '["https://github.com/o/r/actions/runs/5/job/6@2026-01-03T00:00:00Z"]'

newack; LINES='push sha2 carol 2026-01-03T00:00:00Z new head'
ack
chk 'ack push: head is the sha and the id joins' "$(jq -c '.run.watch|[.head,.seen_ids]' "$REC/state.json")" '["sha2",["sha2"]]'

newack; LINES='ready 7 - 2026-01-03T00:00:00Z the PR left draft'
ack
chk 'ack ready: draft false, id never joins' "$(jq -c '.run.watch|[.draft,.seen_ids]' "$REC/state.json")" '[false,[]]'

newack; LINES='queued 7 - 2026-01-03T00:00:00Z the PR entered the merge queue'
ack
chk 'ack queued: queued true, id never joins' "$(jq -c '.run.watch|[.queued,.seen_ids]' "$REC/state.json")" '[true,[]]'
LINES='dequeued 7 - 2026-01-03T00:00:00Z left the merge queue'
ack
chk 'ack dequeued: queued false' "$(jq -c '.run.watch|[.queued,.seen_ids]' "$REC/state.json")" '[false,[]]'

for k in merged closed deployed no-deploy; do
  newack; LINES="$k 7 - 2026-01-03T00:00:00Z text"; before=$(sum)
  ack
  chk "ack $k: no cursor change" "$(cur)" "$(want "$W0")"
  chk "ack $k: exit 0" "$rc" 0
done

for k in deploy-failed deploy-timeout; do
  newrec '{"run_state":"delivered","watch":'"$W0"',"deploy":'"$D_LIVE"'}'
  LINES="$k 7 - 2026-01-03T00:00:00Z text"
  ack
  chk "ack $k: deploy.ended is the kind" "$(jq -r .run.deploy.ended "$REC/state.json")" "$k"
  chk "ack $k: no run.watch write" "$(cur)" "$(want "$W0")"
done

newack; LINES='isDraft=false'; before=$(sum); ack
chk 'ack isDraft=false with draft true: no change' "$(sum)" "$before"
newrec '{"run_state":"delivered","watch":'"$(jq -c '.draft=false' <<< "$W0")"'}'
LINES='isDraft=true'; ack
chk 'ack isDraft=true with draft false: draft true' "$(jq -c .run.watch.draft "$REC/state.json")" true

newack; LINES='review 101 alice 2026-01-02T00:00:00Z COMMENTED hi'
ack; ack
chk 'ack twice: no duplicate in seen_ids' "$(jq -c .run.watch.seen_ids "$REC/state.json")" '[101]'

# ---- ack: --hold and release
newack; LINES=$'review 101 alice 2026-01-02T00:00:00Z COMMENTED has `tick` and $HOME and "quote"\ncomment 102 bob 2026-01-03T00:00:00Z second'
ack --hold 101
chk 'ack --hold: item in held, in seen_ids' "$(jq -c '.run.watch|[.held,.seen_ids]' "$REC/state.json")" "$(jq -cn '[[{kind:"review",id:101,author:"alice",at:"2026-01-02T00:00:00Z",summary:"COMMENTED has `tick` and $HOME and \"quote\""}],[101,102]]')"
ack --hold 101 --hold 102
ws release "$REC" 101
chk 'release: removes the item from held' "$(jq -c '[.run.watch.held[].id]' "$REC/state.json")" '[102]'
chk 'release: one line printed' "$(printf '%s\n' "$out" | grep -c .)" 1
ws release "$REC" 102
chk 'release: held empty' "$(jq -c .run.watch.held "$REC/state.json")" '[]'
newack; LINES='review 101 alice 2026-01-02T00:00:00Z COMMENTED x'; before=$(sum)
ack --hold 999
chk 'ack --hold of an id not in the lines: exit 2, no write' "$rc $(sum)" "2 $before"

# ---- ack: bad input writes nothing
for bad in 'bogus 1 a 2026-01-01T00:00:00Z text' 'review 5' $'review 1 a 2026-01-02T00:00:00Z ok x\nbogus 2 a t s' ''; do
  newack; before=$(sum); LINES=$bad; ack
  if [ -z "$bad" ]; then
    chk 'ack empty input: no write' "$(sum)" "$before"
  else
    chk "ack bad input '${bad//$'\n'/ | }': exit 2, no write" "$rc $(sum)" "2 $before"
  fi
done

echo
echo "$((total - fails)) of $total checks passed"
[ "$fails" = 0 ]

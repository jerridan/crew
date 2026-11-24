#!/bin/bash
# Seeded test of pr-reply.py.
#
# usage: bash skills/delivered-window/scripts/test-pr-reply.sh
#
# It builds a record under a temp directory and puts a stub `gh` first in PATH.
# The stub keeps every posted body as a file under $STUB_DIR/posted, so the
# test compares the bytes that reach GitHub. The record is written by the real
# crew-record.py. It exits 0 only when every check passes.

set -u
here=$(cd "$(dirname "$0")" && pwd)
PR="$here/pr-reply.py"
CR="$here/../../project-lead/scripts/crew-record.py"
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
fails=0
total=0

mkdir -p "$T/bin"
cat > "$T/bin/gh" <<'STUB'
#!/bin/bash
D=$STUB_DIR
echo "$*" >> "$D/calls.log"
bodyfile=''
for a in "$@"; do case "$a" in body=@*) bodyfile=${a#body=@} ;; esac; done
prev=''
for a in "$@"; do [ "$prev" = --body-file ] && bodyfile=$a; prev=$a; done
next() { n=$(cat "$D/n" 2>/dev/null || echo 0); n=$((n + 1)); echo $n > "$D/n"; }
case "$*" in
  "api user"*) echo "$(cat "$D/login")"; exit 0 ;;
  *"resolveReviewThread"*)
    [ -e "$D/fail-resolve" ] && exit 1
    echo '{"data":{"resolveReviewThread":{"thread":{"isResolved":true}}}}'; exit 0 ;;
  *"reviewThreads"*)
    [ -e "$D/fail-threads" ] && exit 1
    cat "$D/threads.json"; exit 0 ;;
  "api --paginate repos/o/r/pulls/7/comments"*) cat "$D/pulls.json"; exit 0 ;;
  "api --paginate repos/o/r/issues/7/comments"*) cat "$D/issues.json"; exit 0 ;;
  "api repos/o/r/pulls/comments/"*)
    last=${!#}; id=${last##*/}
    [ -f "$D/comment-$id.json" ] || exit 1
    cat "$D/comment-$id.json"; exit 0 ;;
  *"-X POST repos/o/r/pulls/7/comments/"*"/replies"*)
    all="$*"; first=${all#*comments/}; first=${first%%/*}
    [ -e "$D/fail-post-$first" ] && exit 1
    next; mkdir -p "$D/posted"; cp "$bodyfile" "$D/posted/reply-$first-$n"
    echo "{\"id\": $((9000 + n))}"; exit 0 ;;
  "pr comment "*)
    grep -q FAILME "$bodyfile" && exit 1
    next; mkdir -p "$D/posted"; cp "$bodyfile" "$D/posted/comment-$n"
    echo "https://github.com/o/r/pull/7#issuecomment-$((5000 + n))"; exit 0 ;;
esac
exit 1
STUB
chmod +x "$T/bin/gh"

export STUB_DIR="$T/stub"
export PATH="$T/bin:$PATH"
REC="$T/rec"
RF="$T/replies.txt"

newrec() {
  rm -rf "$STUB_DIR" "$REC"; mkdir -p "$STUB_DIR/posted" "$REC"
  echo me > "$STUB_DIR/login"
  echo '[]' > "$STUB_DIR/pulls.json"; echo '[]' > "$STUB_DIR/issues.json"
  echo '{"id":201,"in_reply_to_id":200}' > "$STUB_DIR/comment-201.json"
  echo '{"id":202}' > "$STUB_DIR/comment-202.json"
  echo '{"id":300}' > "$STUB_DIR/comment-300.json"
  cat > "$STUB_DIR/threads.json" <<'EOF'
{"data":{"repository":{"pullRequest":{"reviewThreads":{"pageInfo":{"hasNextPage":false,"endCursor":null},"nodes":[{"id":"T1","isResolved":false,"comments":{"nodes":[{"databaseId":200}]}},{"id":"T2","isResolved":false,"comments":{"nodes":[{"databaseId":202}]}},{"id":"T3","isResolved":false,"comments":{"nodes":[{"databaseId":300}]}}]}}}}}
EOF
  echo '{"deliverables":[{"id":"deliverable-1","pr_url":"https://github.com/o/r/pull/7"}],"run":{"run_state":"delivered"}}' > "$REC/state.json"
  python3 "$CR" "$REC" round open r1 --kind pr-comments --ref x --reply-to y
}
run() { out=$(python3 "$PR" "$@" 2>"$T/err"); rc=$?; err=$(cat "$T/err"); }
chk() {
  total=$((total + 1))
  if [ "$2" = "$3" ]; then echo "ok   $1"; else
    fails=$((fails + 1)); echo "FAIL $1"; printf '     got:  %s\n     want: %s\n' "$2" "$3"
  fi
}
npost() { find "$STUB_DIR/posted" -type f | wc -l | tr -d ' '; }
calls() { cat "$STUB_DIR/calls.log" 2>/dev/null; }
body() { cat "$STUB_DIR/posted/$1"; echo x; }   # trailing x keeps the last newline
MARK() { printf '<!-- pr-review: r1 %s -->' "$1"; }

# ---- send: bodies arrive byte for byte, with the marker
TRICKY='Fix `a` with $HOME and $(echo no) and "double" and '"'single'"' and back\slash \n and `` ` ``'
newrec
{
  printf '=== review-comment 201\n%s\nsecond line\n' "$TRICKY"
  printf '=== comment 55\n\nThanks.\n\n\n'
  printf '=== check https://x/runs/5@2026\nOk\n'
} > "$RF"
run send "$REC" r1 "$RF"
chk 'send: exit 0' "$rc" 0
chk 'send: one line per item' "$out" "$(printf 'posted 201 9001\nposted 55 5002\nposted https://x/runs/5@2026 5003')"
chk 'send: review-comment goes to the first comment of its thread' "$(calls | grep -c 'POST repos/o/r/pulls/7/comments/200/replies')" 1
chk 'send: tricky body byte for byte, marker last' "$(body reply-200-1)" "$(printf '%s\nsecond line\n%s\nx' "$TRICKY" "$(MARK 201)")"
chk 'send: leading blank line kept, trailing blank lines dropped' "$(body comment-2)" "$(printf '\nThanks.\n%s\nx' "$(MARK 55)")"
chk 'send: check body' "$(body comment-3)" "$(printf 'Ok\n%s\nx' "$(MARK 'https://x/runs/5@2026')")"
chk 'send: a comment uses gh pr comment with the PR URL' "$(calls | grep -c '^pr comment https://github.com/o/r/pull/7 --body-file')" 2
chk 'send: the login is read once' "$(calls | grep -c '^api user')" 1
chk 'send: round not marked replied without the flag' "$(jq -r .run.rounds.r1.replied_at "$REC/state.json")" null

# a review-comment that is itself a thread root
newrec; printf '=== review-comment 202\nhi\n' > "$RF"; run send "$REC" r1 "$RF"
chk 'send: a first comment is its own thread' "$(calls | grep -c 'comments/202/replies')" 1
newrec; printf '=== dequeued 7\nThe PR left the queue.\n' > "$RF"; run send "$REC" r1 "$RF"
chk 'send: dequeued posts with gh pr comment' "$out" 'posted 7 5001'

# ---- send: to and resolve
newrec; printf '=== review-comment F1 to 300 resolve\nResolved at abc123.\n' > "$RF"
run send "$REC" r1 "$RF"
chk 'send to+resolve: the reply goes to the thread of the to comment' "$(calls | grep -c 'comments/300/replies')" 1
chk 'send to+resolve: the marker holds the item id' "$(body reply-300-1)" "$(printf 'Resolved at abc123.\n%s\nx' "$(MARK F1)")"
chk 'send to+resolve: output' "$out" "$(printf 'posted F1 9001\nresolved F1 T3')"
chk 'send to+resolve: one mutation call with id=T3' "$(calls | grep 'resolveReviewThread' | grep -c 'id=T3')" 1
chk 'send resolve: resolve comes after the reply' "$(calls | grep -n 'replies\|resolveReviewThread' | sed 's/:.*//' | tr '\n' ' ')" "$(calls | grep -n 'replies\|resolveReviewThread' | sed 's/:.*//' | sort -n | tr '\n' ' ')"
newrec; printf '=== review-comment 202 resolve\nDone.\n' > "$RF"; run send "$REC" r1 "$RF"
chk 'send resolve without to: the thread of the item id' "$out" "$(printf 'posted 202 9001\nresolved 202 T2')"

# ---- send: the skip
posted_json() { # <login> -> a pulls.json with one marker comment for item 201 of r1
  jq -n --arg u "$1" '[{id:777,user:{login:$u},body:"earlier\n<!-- pr-review: r1 201 -->"}]'
}
newrec; posted_json me > "$STUB_DIR/pulls.json"
printf '=== review-comment 201\nagain\n=== comment 55\nnew\n' > "$RF"
run send "$REC" r1 "$RF"
chk 'skip: an item already posted is skipped, the others post' "$out" "$(printf 'skipped 201 777 already posted\nposted 55 5001')"
chk 'skip: one post only' "$(npost)" 1
newrec; posted_json other > "$STUB_DIR/pulls.json"
run send "$REC" r1 "$RF"
chk 'skip: a marker from another account does not stop a post' "$out" "$(printf 'posted 201 9001\nposted 55 5002')"
newrec; jq -n '[{id:778,user:{login:"me"},body:"x\r\n<!-- pr-review: r1 55 -->\r\n"}]' > "$STUB_DIR/issues.json"
run send "$REC" r1 "$RF"
chk 'skip: an issue comment with CRLF is found' "$(printf '%s\n' "$out" | head -2 | tail -1)" 'skipped 55 778 already posted'
newrec; jq -n '[{id:779,user:{login:"me"},body:"x\n<!-- pr-review: r2 201 -->"}]' > "$STUB_DIR/pulls.json"
run send "$REC" r1 "$RF"
chk 'skip: a marker of another round does not skip' "$(printf '%s\n' "$out" | head -1)" 'posted 201 9001'
newrec; posted_json me > "$STUB_DIR/pulls.json"
printf '=== review-comment 201 to 300 resolve\nagain\n' > "$RF"
run send "$REC" r1 "$RF"
chk 'skip then resolve: a reply posted before still resolves' "$out" "$(printf 'skipped 201 777 already posted\nresolved 201 T3')"

# ---- send: a failed item
newrec; printf '=== comment 1\nFAILME\n=== comment 2\nfine\n=== review-comment 202\nalso fine\n' > "$RF"
run send "$REC" r1 "$RF" --mark-replied
chk 'failed item: exit 1' "$rc" 1
chk 'failed item: the others posted' "$(printf '%s\n' "$out" | grep -c '^posted')" 2
chk 'failed item: a failed line names the item' "$(printf '%s\n' "$out" | grep -c '^failed 1 ')" 1
chk 'failed item: no replied line' "$(printf '%s\n' "$out" | grep -c '^replied')" 0
chk 'failed item: round not marked replied' "$(jq -r .run.rounds.r1.replied_at "$REC/state.json")" null
newrec; : > "$STUB_DIR/fail-threads"; printf '=== review-comment 202 resolve\nx\n' > "$RF"
run send "$REC" r1 "$RF"
chk 'failed thread read: reply posted, resolve failed, exit 1' "$rc $(printf '%s\n' "$out" | cut -d' ' -f1 | tr '\n' ' ')" '1 posted failed '
newrec; : > "$STUB_DIR/fail-post-202"; printf '=== review-comment 202 resolve\nx\n' > "$RF"
run send "$REC" r1 "$RF"
chk 'failed reply: no resolve, exit 1' "$rc $(printf '%s\n' "$out" | cut -d' ' -f1 | tr '\n' ' ')" '1 failed '

# ---- send: --mark-replied
newrec; printf '=== comment 1\nfine\n' > "$RF"
run send "$REC" r1 "$RF" --mark-replied
chk '--mark-replied: output' "$out" "$(printf 'posted 1 5001\nreplied r1')"
chk '--mark-replied: replied_at is set' "$(jq -r '.run.rounds.r1.replied_at|type' "$REC/state.json")" string

# ---- send: a bad file posts nothing and exits 2
bad() { # label, file text
  newrec; printf '%b' "$2" > "$RF"; run send "$REC" r1 "$RF" --mark-replied
  chk "bad file ($1): exit 2, no post, not replied" "$rc $(npost) $(jq -r .run.rounds.r1.replied_at "$REC/state.json")" '2 0 null'
}
bad 'unknown kind' '=== bogus 1\nx\n'
bad 'header with no id' '=== comment\nx\n'
bad 'to on a comment' '=== comment 5 to 3\nx\n'
bad 'resolve on a check' '=== check 5 resolve\nx\n'
bad 'resolve on a review' '=== review 5 resolve\nx\n'
bad 'text before the first header' 'stray\n=== comment 1\nx\n'
bad 'a good reply then a bad header' '=== comment 1\nx\n=== review-comment\ny\n'
bad 'an empty body' '=== comment 1\n\n'
bad 'a header-shaped body line is a header' '=== comment 1\nx\n=== bad header here\n'
newrec; run send "$REC" r1 "$T/none.txt"
chk 'missing replies file: exit 2' "$rc" 2
chk 'error prefix' "${err%%:*}" pr-reply.py

# ---- posted
newrec
jq -n '[{id:777,user:{login:"me"},body:"a\n<!-- pr-review: r1 201 -->"},{id:780,user:{login:"other"},body:"a\n<!-- pr-review: r1 202 -->"}]' > "$STUB_DIR/pulls.json"
jq -n '[{id:781,user:{login:"me"},body:"b\n<!-- pr-review: r1 https://x/runs/5@2026 -->"},{id:782,user:{login:"me"},body:"c\n<!-- pr-review: r2 9 -->"},{id:783,user:{login:"me"},body:"<!-- pr-review: r1 8 -->\nnot the last line"}]' > "$STUB_DIR/issues.json"
run posted "$REC" r1
chk 'posted: item id and reply id, own account, this round, last line only' "$out" "$(printf '201 777\nhttps://x/runs/5@2026 781')"

echo
echo "$((total - fails)) of $total checks passed"
[ "$fails" = 0 ]

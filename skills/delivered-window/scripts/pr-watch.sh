#!/bin/bash
# Poll one crew run's PR, and print one line per new item.
#
# usage: pr-watch.sh <record-dir> [once]
#
# With no second argument, the script polls every 60 seconds until the PR
# merges or closes. That is the `Monitor` command. A PR in the merge queue
# does not stop it: the script prints `queued` once per entry into the queue,
# and `dequeued` once when the PR leaves the queue and stays open.
# With `once`, it polls one time and prints `isDraft=<d>` last. That is the
# fallback poll of a keep-alive fire.
#
# It reads its start state from `<record-dir>/state.json` at each start: the
# PR is the one deliverable `pr_url`, and the cursor is `run.watch`. So a
# re-armed monitor always runs this plugin version's poll, from the record's
# current cursor. Never copy this file into the record: a copy keeps the poll
# of the version that wrote it (design §15.123). `pr-watch.md` says what each
# line means and what the poll leaves out.

set -u

die() { printf 'pr-watch.sh: %s\n' "$1" >&2; exit 2; }

[ $# -ge 1 ] && [ $# -le 2 ] || die 'usage: pr-watch.sh <record-dir> [once]'
mode=${2:-loop}
[ "$mode" = loop ] || [ "$mode" = once ] || die "unknown mode '$mode'; use once or nothing"
state="$1/state.json"
[ -f "$state" ] || die "no state.json in $1"

PR=$(jq -r '[.deliverables[]? | .pr_url // empty] | if length == 1 then .[0] else empty end' "$state") ||
  die "cannot read $state"
[ -n "$PR" ] || die 'the record needs exactly one deliverable with a pr_url'
case "$PR" in
  https://github.com/*/*/pull/*) ;;
  *) die "pr_url '$PR' is not a GitHub PR URL" ;;
esac
R=${PR#https://github.com/}; R=${R%/pull/*}; N=${PR##*/pull/}; N=${N%%[/?#]*}

jq -e '.run.watch.last_polled_at and .run.watch.head' "$state" >/dev/null ||
  die 'run.watch needs last_polled_at and head; write it as pr-watch.md "Arm the monitor" says'
export SINCE
SINCE=$(jq -r '.run.watch.last_polled_at' "$state")
seen=" $(jq -r '(.run.watch.seen_ids // []) | join(" ")' "$state") "
draft=$(jq -r 'if .run.watch.draft == true then "true" else "false" end' "$state")
head=$(jq -r '.run.watch.head' "$state")
# Whether the PR is in the merge queue, as far as this watch knows.
queued=$(jq -r 'if .run.watch.queued == true then "true" else "false" end' "$state")
merged=''

poll() {
  d=$(gh pr view "$PR" --json isDraft -q .isDraft 2>/dev/null) || true
  if [ "$d" = true ]; then draft=true
  elif [ "$d" = false ] && [ "$draft" = true ]; then
    draft=false
    echo "ready $N - $(date -u +%Y-%m-%dT%H:%M:%SZ) the PR left draft"
  fi
  h=$(gh pr view "$PR" --json headRefOid -q .headRefOid 2>/dev/null) || true
  # A short sha in run.watch.head is the same head, not a push.
  if [ -n "$h" ] && [ ${#head} -ge 7 ] && [ "${h#"$head"}" != "$h" ]; then head=$h; fi
  if [ -n "$h" ] && [ "$h" != "$head" ]; then
    head=$h
    u=$(gh api "repos/$R/commits/$h" --jq '.author.login // empty' 2>/dev/null) || u=''
    echo "push $h ${u:--} $(date -u +%Y-%m-%dT%H:%M:%SZ) new head"
  fi
  revs=$(gh api --paginate "repos/$R/pulls/$N/reviews" --jq '.[]
    | if .state == "PENDING" then "pending \(.id)"
      elif ((.body // "") != "" or .state == "APPROVED") and .submitted_at >= $ENV.SINCE
        and ((.body // "" | gsub("\r"; "") | rtrimstr("\n") | split("\n") | last // "" | startswith("<!-- pr-review: ")) | not)
      then "review \(.id) \(.user.login) \(.submitted_at) \(.state) \(.body // "" | gsub("\r"; "") | split("\n") | first // "" | .[0:100])"
      else empty end' 2>/dev/null) || revs=''
  export PEND=" $(printf '%s\n' "$revs" | sed -n 's/^pending //p' | tr '\n' ' ')"
  out=$( {
    printf '%s\n' "$revs" | grep '^review '
    gh api --paginate "repos/$R/pulls/$N/comments" --jq '.[]
      | (.pull_request_review_id // 0) as $r | select($ENV.PEND | contains(" \($r) ") | not)
      | select((.body // "" | gsub("\r"; "") | rtrimstr("\n") | split("\n") | last // "" | startswith("<!-- pr-review: ")) | not)
      | "review-comment \(.id) \(.user.login) \(.created_at) \(.path):\(.line // .original_line // 0) \(.body // "" | gsub("\r"; "") | split("\n") | first // "" | .[0:100])"'
    gh api --paginate "repos/$R/issues/$N/comments" --jq '.[]
      | select(.created_at >= $ENV.SINCE)
      | select((.body // "" | gsub("\r"; "") | rtrimstr("\n") | split("\n") | last // "" | startswith("<!-- pr-review: ")) | not)
      | "comment \(.id) \(.user.login) \(.created_at) \(.body // "" | gsub("\r"; "") | split("\n") | first // "" | .[0:100])"'
    gh pr checks "$PR" --json name,bucket,link,startedAt --jq '.[]
      | select(.bucket == "fail")
      | "check \(if (.link // "") == "" then .name else .link end | gsub(" "; "_"))@\(.startedAt) - \(.startedAt) \(.name) failed"'
  } 2>/dev/null ) || true
  while IFS= read -r line; do
    [ -n "$line" ] || continue
    id=${line#* }; id=${id%% *}
    case "$seen" in *" $id "*) continue ;; esac
    seen="$seen$id "
    printf '%s\n' "$line"
  done <<< "$out"
  m=$(gh pr view "$PR" --json state,mergedAt -q '"\(.state) \(.mergedAt)"' 2>/dev/null) || true
  q=$(gh api graphql -f owner="${R%/*}" -f repo="${R#*/}" -F n="$N" -f query='
    query($owner: String!, $repo: String!, $n: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $n) { isInMergeQueue mergeQueueEntry { enqueuedAt } }
      }
    }' --jq '.data.repository.pullRequest | if .isInMergeQueue then .mergeQueueEntry.enqueuedAt // "-" else "out" end' 2>/dev/null) || q=''
  if [ "${m%% *}" = MERGED ]; then
    merged=1
    echo "merged $N - ${m#* } the PR merged"
  elif [ "${m%% *}" = CLOSED ]; then
    merged=1
    echo "closed $N - $(date -u +%Y-%m-%dT%H:%M:%SZ) the PR closed"
  elif [ -n "$q" ] && [ "$q" != out ]; then
    # Loop mode prints once per entry; once mode prints on every fire.
    if [ "$queued" != true ] || [ "$mode" = once ]; then
      [ "$q" != - ] || q=$(date -u +%Y-%m-%dT%H:%M:%SZ)
      echo "queued $N - $q the PR entered the merge queue"
    fi
    queued=true
  elif [ "$q" = out ] && [ "$queued" = true ] && [ "${m%% *}" = OPEN ]; then
    queued=false
    echo "dequeued $N - $(date -u +%Y-%m-%dT%H:%M:%SZ) left the merge queue"
  fi
}

if [ "$mode" = once ]; then
  poll
  echo "isDraft=$d"
  exit 0
fi
while [ -z "$merged" ]; do poll; sleep 60; done

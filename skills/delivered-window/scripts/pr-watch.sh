#!/bin/bash
# Poll one crew run's PR, and print one line per new item.
#
# usage: pr-watch.sh <record-dir> [once|deploy|deploy-once]
#
# With no second argument, the script polls every 60 seconds until the PR
# merges or closes. That is the `Monitor` command. A PR in the merge queue
# does not stop it: the script prints `queued` once per entry into the queue,
# and `dequeued` once when the PR leaves the queue and stays open.
# With `once`, it polls one time and prints `isDraft=<d>` last. That is the
# fallback poll of a keep-alive fire.
#
# With `deploy`, the script watches the deploy of the merge commit instead.
# It polls every 60 seconds, prints one terminal line (`deployed`,
# `no-deploy`, `deploy-failed`, `deploy-timeout` or `closed`) and exits. With
# `deploy-once`, it polls one time and prints a line only when one is due.
# The deploy modes read `run.deploy` from `state.json`, need no `run.watch`,
# and print nothing when `run.deploy.ended` is set.
#
# It reads its start state from `<record-dir>/state.json` at each start: the
# PR is the one deliverable `pr_url`, and the cursor is `run.watch`. So a
# re-armed monitor always runs this plugin version's poll, from the record's
# current cursor. Never copy this file into the record: a copy keeps the poll
# of the version that wrote it (design §15.123). `pr-watch.md` says what each
# line means and what the poll leaves out.

set -u

die() { printf 'pr-watch.sh: %s\n' "$1" >&2; exit 2; }

[ $# -ge 1 ] && [ $# -le 2 ] || die 'usage: pr-watch.sh <record-dir> [once|deploy|deploy-once]'
mode=${2:-loop}
case "$mode" in
  loop|once|deploy|deploy-once) ;;
  *) die "unknown mode '$mode'; use once, deploy, deploy-once or nothing" ;;
esac
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

# Judge the newest Actions run on the merge commit whose name passes the jq
# test in $1. A success or a failure prints one line and sets `finished`. Any
# other conclusion is no result yet, and the newest run still wins next poll.
wf_check() {
  r=$(gh api "repos/$R/actions/runs?head_sha=$oid&per_page=100" --jq '
    [.workflow_runs[] | select(.name | '"$1"')] | sort_by(.created_at) | last
    | select(. != null)
    | "\(.id) \(.conclusion // "null") \(.updated_at) \(.name)"' 2>/dev/null) || r=''
  [ -n "$r" ] || return 0
  seen_deploy=1
  read -r rid rconc rat rname <<< "$r"
  case "$rconc" in
    success)
      echo "deployed $rid - $rat $rname succeeded"
      finished=1 ;;
    failure|timed_out|startup_failure)
      echo "deploy-failed $rid - $rat $rname $rconc"
      finished=1 ;;
  esac
  return 0
}

# What the last good read of the PR showed, kept for a poll whose read fails.
oid=''; merged_at=''; dep_count=''

deploy_poll() {
  v=$(gh pr view "$PR" --json state,mergeCommit,mergedAt \
    -q '"\(.state) \(.mergeCommit.oid // "-") \(.mergedAt // "-")"' 2>/dev/null) || v=''
  if [ -n "$v" ]; then
    set -- $v
    case "${1:-}" in
      CLOSED)
        echo "closed $N - $(date -u +%Y-%m-%dT%H:%M:%SZ) the PR closed"
        finished=1
        return 0 ;;
      MERGED)
        if [ "${2:--}" != - ] && [ "${3:--}" != - ]; then oid=$2; merged_at=$3; fi ;;
      *) return 0 ;;
    esac
  fi
  [ -n "$oid" ] && [ -n "$merged_at" ] || return 0
  seen_deploy=''
  if [ -n "$DEP_WF" ]; then
    wf_check '. == $ENV.DEP_WF'
    [ -z "$finished" ] || return 0
  else
    if [ -z "$DEP_ENV" ]; then
      # The default signal. Only a nonzero count is kept: a deploy can create
      # the first deployment after the merge.
      if [ -z "$dep_count" ] || [ "$dep_count" = 0 ]; then
        dep_count=$(gh api "repos/$R/deployments?per_page=1" --jq length 2>/dev/null) || dep_count=''
      fi
      [ -n "$dep_count" ] || return 0
      if [ "$dep_count" = 0 ]; then
        # No deployment objects. A deploy or release run on the merge commit
        # is the signal. With none, wait 10 minutes for a run to appear.
        wf_check 'test("deploy|release"; "i")'
        [ -z "$finished" ] || return 0
        if [ -z "$seen_deploy" ]; then
          jq -n --arg m "$merged_at" '((now - ($m | fromdateiso8601)) / 60) >= 10' 2>/dev/null |
            grep -q true || return 0
          echo "no-deploy $N - $merged_at the repo has no GitHub deployments or deploy runs"
          finished=1
          return 0
        fi
      fi
    fi
    if [ "$dep_count" != 0 ] || [ -n "$DEP_ENV" ]; then
      # Only the newest matching deployment counts.
      dep=$(gh api "repos/$R/deployments?sha=$oid&per_page=100" --jq '
        [.[] | select(if $ENV.DEP_ENV == "" then (.production_environment == true
                 or (.environment | test("^prod(uction)?$"; "i")))
               else .environment == $ENV.DEP_ENV end)]
        | sort_by(.created_at) | last | select(. != null)
        | "\(.id) \(.environment)"' 2>/dev/null) || dep=''
      if [ -n "$dep" ]; then
        seen_deploy=1
        did=${dep%% *}; denv=${dep#* }
        st=$(gh api "repos/$R/deployments/$did/statuses" --jq '
          sort_by(.created_at) | reverse
          | (map(.state) | index("success")) as $s
          | if length == 0 then empty
            else (if .[0].state == "inactive" and $s then "success" else .[0].state end)
                 + " " + .[0].created_at end' 2>/dev/null) || st=''
        case "${st%% *}" in
          success)
            echo "deployed $did - ${st#* } $denv succeeded"
            finished=1; return 0 ;;
          failure|error)
            echo "deploy-failed $did - ${st#* } $denv ${st%% *}"
            finished=1; return 0 ;;
        esac
      fi
    fi
  fi
  # The timeout counts from the arming time, or from the merge when the
  # record has none.
  late=$(jq -n --arg m "${DEP_SINCE:-$merged_at}" --argjson t "$TIMEOUT" \
    '((now - ($m | fromdateiso8601)) / 60) > $t' 2>/dev/null) || late=''
  if [ "$late" = true ]; then
    if [ -n "$seen_deploy" ]; then what='no deploy finished'; else what='no deploy seen'; fi
    echo "deploy-timeout $N - $(date -u +%Y-%m-%dT%H:%M:%SZ) $what $TIMEOUT minutes after the watch started"
    finished=1
  fi
  return 0
}

case "$mode" in
  deploy|deploy-once)
    jq -e '.run.deploy | type == "object"' "$state" >/dev/null 2>&1 ||
      die 'the record needs run.deploy; write it as SKILL.md "The deploy watch" says'
    # A line that was reported ends the watch. Only a re-arm clears `ended`.
    [ -z "$(jq -r '.run.deploy.ended // ""' "$state")" ] || exit 0
    export DEP_ENV DEP_WF
    DEP_ENV=$(jq -r '.run.deploy.environment // ""' "$state")
    DEP_WF=$(jq -r '.run.deploy.workflow // ""' "$state")
    DEP_SINCE=$(jq -r '.run.deploy.since // ""' "$state")
    TIMEOUT=$(jq -r '.run.deploy.timeout_minutes // 180' "$state")
    case "$TIMEOUT" in
      ''|*[!0-9]*) die "run.deploy.timeout_minutes '$TIMEOUT' is not a positive integer" ;;
    esac
    [ "$TIMEOUT" -gt 0 ] || die "run.deploy.timeout_minutes '$TIMEOUT' is not a positive integer"
    finished=''
    if [ "$mode" = deploy-once ]; then deploy_poll; exit 0; fi
    while [ -z "$finished" ]; do deploy_poll; [ -n "$finished" ] || sleep 60; done
    exit 0 ;;
esac

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
  # Read the queue first: a merge between the two reads then shows as MERGED, which wins.
  q=$(gh api graphql -f owner="${R%/*}" -f repo="${R#*/}" -F n="$N" -f query='
    query($owner: String!, $repo: String!, $n: Int!) {
      repository(owner: $owner, name: $repo) {
        pullRequest(number: $n) { isInMergeQueue mergeQueueEntry { enqueuedAt } }
      }
    }' --jq '.data.repository.pullRequest | if .isInMergeQueue then .mergeQueueEntry.enqueuedAt // "-" else "out" end' 2>/dev/null) || q=''
  m=$(gh pr view "$PR" --json state,mergedAt -q '"\(.state) \(.mergedAt)"' 2>/dev/null) || true
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

#!/bin/bash
# Say why a PR left the merge queue.
#
# usage: dequeue-diagnosis.sh <owner> <repo> <n>
#
# Prints three sections, each under a heading line, then the PR's
# `mergeable` value:
#   1. the `RemovedFromMergeQueueEvent` items of the PR timeline (GraphQL),
#      with their reason
#   2. the `merge_group` workflow runs of this PR since its latest
#      `AddedToMergeQueueEvent`, with conclusion and URL
#   3. the last 60 lines of the log of the first failed job of the most
#      recent run whose conclusion is `failure`, `timed_out` or
#      `startup_failure`
# A section with nothing in it prints `none`. A section whose `gh` read exits
# non-zero prints `read failed: <exit status>`. A merge group branch name
# holds `/pr-<n>-`, so that is how a run is matched to the PR.

set -u

[ $# -eq 3 ] || { echo 'usage: dequeue-diagnosis.sh <owner> <repo> <n>' >&2; exit 2; }
owner=$1; repo=$2; n=$3

# Every read puts its output in a variable and its exit status in $rc before
# any pipe sees it, so a `gh` error never reads as an empty result.

echo "== Removed from the merge queue (timeline events)"
out=$(gh api graphql -f owner="$owner" -f repo="$repo" -F n="$n" -f query='
  query($owner: String!, $repo: String!, $n: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $n) {
        timelineItems(itemTypes: [REMOVED_FROM_MERGE_QUEUE_EVENT], first: 50) {
          nodes { ... on RemovedFromMergeQueueEvent { createdAt reason actor { login } } }
        }
      }
    }
  }' --jq '.data.repository.pullRequest.timelineItems.nodes[]
  | "\(.createdAt) \(.actor.login // "-") reason: \(.reason // "unknown")"' 2>/dev/null); rc=$?
if [ $rc -ne 0 ]; then echo "read failed: $rc"; else printf '%s\n' "${out:-none}"; fi

echo "== merge_group workflow runs of this PR"
# Time of the latest enqueue. A run older than that belongs to an earlier try.
since=$(gh api graphql -f owner="$owner" -f repo="$repo" -F n="$n" -f query='
  query($owner: String!, $repo: String!, $n: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $n) {
        timelineItems(itemTypes: [ADDED_TO_MERGE_QUEUE_EVENT], last: 1) {
          nodes { ... on AddedToMergeQueueEvent { createdAt } }
        }
      }
    }
  }' --jq '.data.repository.pullRequest.timelineItems.nodes[0].createdAt // empty' 2>/dev/null); rc=$?
if [ $rc -ne 0 ]; then
  echo "enqueue read failed: $rc; all runs shown"
  since=''
elif [ -z "$since" ]; then
  echo 'no enqueue event; all runs shown'
fi

# One line per run: created_at, id, conclusion, URL. Newest first.
raw=$(gh api --paginate "repos/$owner/$repo/actions/runs?event=merge_group&per_page=100" --jq '
  .workflow_runs[] | select((.head_branch // "") | contains("/pr-'"$n"'-"))
  | "\(.created_at) \(.id) \(.conclusion // .status) \(.html_url)"' 2>/dev/null); runs_rc=$?
runs=''
if [ $runs_rc -ne 0 ]; then
  echo "read failed: $runs_rc"
else
  runs=$(printf '%s\n' "$raw" | awk -v since="$since" 'NF && (since == "" || $1 >= since)' | sort -r)
  if [ -n "$runs" ]; then
    printf '%s\n' "$runs" | cut -d' ' -f3-
  else
    echo none
  fi
fi

echo "== Log of the first failed job of the most recent failed run (last 60 lines)"
if [ $runs_rc -ne 0 ]; then
  echo "read failed: $runs_rc"
else
  log=''
  failed=0
  run_id=$(printf '%s\n' "$runs" | awk '$3 == "failure" || $3 == "timed_out" || $3 == "startup_failure" { print $2; exit }')
  if [ -n "$run_id" ]; then
    job_id=$(gh api "repos/$owner/$repo/actions/runs/$run_id/jobs" --jq '
      [.jobs[] | select(.conclusion == "failure" or .conclusion == "timed_out")] | first | .id // empty' 2>/dev/null); rc=$?
    if [ $rc -ne 0 ]; then
      echo "read failed: $rc"; failed=1
    elif [ -n "$job_id" ]; then
      full=$(gh api "repos/$owner/$repo/actions/jobs/$job_id/logs" 2>/dev/null); rc=$?
      if [ $rc -ne 0 ]; then echo "read failed: $rc"; failed=1; else log=$(printf '%s\n' "$full" | tail -n 60); fi
    fi
  fi
  [ $failed -eq 1 ] || printf '%s\n' "${log:-none}"
fi

echo "== mergeable"
m=$(gh pr view "$n" --repo "$owner/$repo" --json mergeable --jq .mergeable 2>/dev/null); rc=$?
if [ $rc -ne 0 ]; then echo "read failed: $rc"; else echo "${m:-unknown}"; fi

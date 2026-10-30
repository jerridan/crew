#!/bin/bash
# Say why a PR left the merge queue.
#
# usage: dequeue-diagnosis.sh <owner> <repo> <n>
#
# Prints three sections, each under a heading line, then the PR's
# `mergeable` value:
#   1. the PR timeline events of type `removed_from_merge_queue`, with reason
#   2. the `merge_group` workflow runs of this PR, with conclusion and URL
#   3. the last 60 lines of the log of the first failed job of the most
#      recent such run
# A section with nothing in it prints `none`. A merge group branch name holds
# `pr-<n>-`, so that is how a run is matched to the PR.

set -u

[ $# -eq 3 ] || { echo 'usage: dequeue-diagnosis.sh <owner> <repo> <n>' >&2; exit 2; }
owner=$1; repo=$2; n=$3

echo "== Removed from the merge queue (timeline events)"
out=$(gh api --paginate "repos/$owner/$repo/issues/$n/timeline" --jq '.[]
  | select(.event == "removed_from_merge_queue")
  | "\(.created_at) \(.actor.login // "-") reason: \(.reason // "unknown")"' 2>/dev/null) || out=''
printf '%s\n' "${out:-none}"

echo "== merge_group workflow runs of this PR"
runs=$(gh api "repos/$owner/$repo/actions/runs?event=merge_group&per_page=100" --jq '
  [.workflow_runs[] | select(.head_branch | contains("pr-'"$n"'-"))]
  | sort_by(.created_at) | reverse | .[]
  | "\(.id) \(.conclusion // .status) \(.html_url)"' 2>/dev/null) || runs=''
if [ -n "$runs" ]; then
  printf '%s\n' "$runs" | cut -d' ' -f2-
else
  echo none
fi

echo "== Log of the first failed job of the most recent run (last 60 lines)"
log=''
if [ -n "$runs" ]; then
  run_id=$(printf '%s\n' "$runs" | head -n 1 | cut -d' ' -f1)
  job_id=$(gh api "repos/$owner/$repo/actions/runs/$run_id/jobs" --jq '
    [.jobs[] | select(.conclusion == "failure")] | first | .id // empty' 2>/dev/null) || job_id=''
  if [ -n "$job_id" ]; then
    log=$(gh api "repos/$owner/$repo/actions/jobs/$job_id/logs" 2>/dev/null | tail -n 60) || log=''
  fi
fi
printf '%s\n' "${log:-none}"

echo "== mergeable"
gh pr view "$n" --repo "$owner/$repo" --json mergeable --jq .mergeable 2>/dev/null || echo unknown

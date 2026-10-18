# PR watch commands

The exact command lines for `SKILL.md`'s "Watch the PR" and "Send the reply
file". That file owns when each one runs.

Fill `<owner>`, `<repo>` and `<n>` from the deliverable's `pr_url`, which is
`https://github.com/<owner>/<repo>/pull/<n>`. Fill `<since>`, `<seen ids>`
and `<draft>` from `run.watch`: `last_polled_at`, `seen_ids` joined by
spaces, and `draft`. Every command runs as the principal's own `gh` account.

## The poll

This block defines the poll, and runs nothing. Each read that fails prints
nothing, so a network error costs one quiet poll.

```bash
export SINCE='<since>'
R='<owner>/<repo>'; N=<n>; PR='<pr_url>'
seen=' <seen ids> '; draft=<draft>
poll() {
  d=$(gh pr view "$PR" --json isDraft -q .isDraft 2>/dev/null) || true
  if [ "$d" = true ]; then draft=true
  elif [ "$d" = false ] && [ "$draft" = true ]; then
    draft=false
    echo "ready $N - $(date -u +%Y-%m-%dT%H:%M:%SZ) the PR left draft"
  fi
  out=$( {
    gh api --paginate "repos/$R/pulls/$N/reviews" --jq '.[]
      | select(.state != "PENDING" and (.body // "") != "" and .submitted_at > $ENV.SINCE)
      | select((.body | gsub("\r"; "") | rtrimstr("\n") | split("\n") | last // "" | startswith("crew: ")) | not)
      | "review \(.id) \(.user.login) \(.submitted_at) \(.state) \(.body | gsub("\r"; "") | split("\n") | first | .[0:100])"'
    gh api --paginate "repos/$R/pulls/$N/comments" --jq '.[]
      | select((.body // "" | gsub("\r"; "") | rtrimstr("\n") | split("\n") | last // "" | startswith("crew: ")) | not)
      | "review-comment \(.id) \(.user.login) \(.created_at) \(.path):\(.line // .original_line // 0) \(.body // "" | gsub("\r"; "") | split("\n") | first // "" | .[0:100])"'
    gh api --paginate "repos/$R/issues/$N/comments" --jq '.[]
      | select(.created_at > $ENV.SINCE)
      | select((.body // "" | gsub("\r"; "") | rtrimstr("\n") | split("\n") | last // "" | startswith("crew: ")) | not)
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
}
```

The review comments read has no time filter. GitHub dates an inline comment
from when the reviewer drafted it, not from when the review was submitted, so
`seen_ids` alone keeps an old one out.

`gh pr checks` exits 1 when a check failed, and when the PR has no checks at
all, so the read ends in `|| true`. A `check` id is `<link>@<startedAt>`, so a
failure on a new run is a new item, also when the link stays the same. A check
with no link uses its name, with each space as `_`. A `check` line carries `-`
for its author, because a check has none. A `ready` line carries the PR number
as its id, and that id never goes into `seen_ids`: the draft state is what
stops a second `ready`.

## The first write's cursor

The first write of `run.watch` takes `last_polled_at` from the PR's creation
time, and starts `seen_ids` empty. The first poll then reports every item
that landed before the arming. The marker already keeps out your own replies.

```bash
gh pr view <pr_url> --json createdAt -q .createdAt
```

A resume of a record that has no `run.watch` is the one exception. That
record is from before the watch, so the principal brought its PR reviews to
you by hand. Take `last_polled_at` from the clock, and put every review
comment already on the PR in `seen_ids`:

```bash
gh api --paginate repos/<owner>/<repo>/pulls/<n>/comments --jq '.[].id'
```

## The monitor command

The poll block, then this loop. Pass the whole text as the `Monitor`
command.

```bash
while true; do poll; sleep 60; done
```

## The fallback poll

The poll block, then this line, in one Bash call per keep-alive fire.

```bash
poll; echo "isDraft=$d"
```

A fire that prints `isDraft=true` while `run.watch.draft` is false writes
`draft: true` to the cursor. The fallback keeps no state between fires, so
this write is what lets a PR returned to draft fire `ready` again.

## Verify a failed check

The run id is in the check's link, `.../actions/runs/<run-id>/job/<job-id>`.

```bash
gh run view <run-id> --repo <owner>/<repo> --log-failed
```

## Post a reply

Write the reply to a file outside the repo first, so a backtick in it reaches
GitHub intact. Its last line is `crew: <round-id> <item id>`, with the id of
the item it answers.

A `review-comment` replies in its own thread. GitHub takes a reply only on a
thread's first comment, so read that comment's id first:

```bash
gh api repos/<owner>/<repo>/pulls/comments/<id> --jq '.in_reply_to_id // .id'
gh api -X POST repos/<owner>/<repo>/pulls/<n>/comments/<first comment id>/replies -F body=@<reply file>
```

A `review`, a `comment` or a `check` gets a PR conversation comment:

```bash
gh pr comment <pr_url> --body-file <reply file>
```

## Find the replies a round already posted

Run this before a resumed send. It matches the full marker, and prints the
item id each reply answers, then the reply's own id. An item whose id it
prints is not posted again.

```bash
for p in pulls issues; do
  gh api --paginate "repos/<owner>/<repo>/$p/<n>/comments" --jq '.[]
    | (.body // "" | gsub("\r"; "") | rtrimstr("\n") | split("\n") | last // "") as $m
    | select($m | startswith("crew: <round-id> "))
    | "\($m | ltrimstr("crew: <round-id> ")) \(.id)"'
done
```

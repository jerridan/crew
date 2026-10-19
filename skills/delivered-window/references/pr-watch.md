# PR watch commands

The exact command lines for `SKILL.md`'s "Watch the PR" and "Send the reply
file". That file owns when each one runs.

Fill `<owner>`, `<repo>` and `<n>` from the deliverable's `pr_url`, which is
`https://github.com/<owner>/<repo>/pull/<n>`. Fill `<since>`, `<seen ids>`,
`<draft>` and `<head>` from `run.watch`: `last_polled_at`, `seen_ids` joined
by spaces, `draft` and `head`. Every command runs as the principal's own
`gh` account.

When `run.watch` has no `head`, the record is from before the key. Take
`head` from the `Reviewed:` line of the latest `reviews/skeptical-r<n>.md`,
or the deliverable's `base` when there is none. Write it to `run.watch` before
the monitor starts, so the first poll prints no `push` for a head the project
lead already knows.

## The poll

This block defines the poll, and runs nothing. Each read that fails prints
nothing, so a network error costs one quiet poll.

```bash
export SINCE='<since>'
R='<owner>/<repo>'; N=<n>; PR='<pr_url>'
seen=' <seen ids> '; draft=<draft>; head=<head>; merged=''
poll() {
  d=$(gh pr view "$PR" --json isDraft -q .isDraft 2>/dev/null) || true
  if [ "$d" = true ]; then draft=true
  elif [ "$d" = false ] && [ "$draft" = true ]; then
    draft=false
    echo "ready $N - $(date -u +%Y-%m-%dT%H:%M:%SZ) the PR left draft"
  fi
  h=$(gh pr view "$PR" --json headRefOid -q .headRefOid 2>/dev/null) || true
  if [ -n "$h" ] && [ "$h" != "$head" ]; then
    head=$h
    u=$(gh api "repos/$R/commits/$h" --jq '.author.login // empty' 2>/dev/null) || u=''
    echo "push $h ${u:--} $(date -u +%Y-%m-%dT%H:%M:%SZ) new head"
  fi
  revs=$(gh api --paginate "repos/$R/pulls/$N/reviews" --jq '.[]
    | if .state == "PENDING" then "pending \(.id)"
      elif (.body // "") != "" and .submitted_at >= $ENV.SINCE
        and ((.body | gsub("\r"; "") | rtrimstr("\n") | split("\n") | last // "" | startswith("<!-- pr-review: ")) | not)
      then "review \(.id) \(.user.login) \(.submitted_at) \(.state) \(.body | gsub("\r"; "") | split("\n") | first | .[0:100])"
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
  if [ "${m%% *}" = MERGED ]; then
    merged=1
    echo "merged $N - ${m#* } the PR merged"
  elif [ "${m%% *}" = CLOSED ]; then
    merged=1
    echo "closed $N - $(date -u +%Y-%m-%dT%H:%M:%SZ) the PR closed"
  fi
}
```

The `submitted_at` and `created_at` filters use `>=`. GitHub times have
one-second resolution, and `seen_ids` prevents a repeat.

The review comments read has no time filter. GitHub dates an inline comment
from when the reviewer drafted it, not from when the review was submitted, so
`seen_ids` alone keeps an old one out.

The review comments read also drops a comment whose `pull_request_review_id`
names a `PENDING` review. That is the principal's own review, not yet
submitted. The one reviews read gives both the `review` lines and `PEND`, the
ids of the pending reviews. The comment is reported once its review is
submitted. When that read fails, `PEND` is empty, and the poll drops no
comment.

`gh pr checks` exits 1 when a check failed, and when the PR has no checks at
all, so the read ends in `|| true`. A `check` id is `<link>@<startedAt>`, so a
failure on a new run is a new item, also when the link stays the same. A check
with no link uses its name, with each space as `_`. A `check` line carries `-`
for its author, because a check has none. A `ready` line carries the PR number
as its id, and that id never goes into `seen_ids`: the draft state is what
stops a second `ready`.

A `push` line reads the PR's head sha. When it differs from the command's
`head`, the line carries that sha as its id, the login of the head commit's
author (`-` when that read fails) and the time of the poll, and the command
sets `head`. A `merged` line carries the PR number as its id, the `mergedAt`
time and no author. Like `ready`, it never goes into `seen_ids`. It prints
once, and the monitor command stops its loop on it. The poll prints it last,
so the items of that poll are reported first. A `closed` line is the same for
a PR closed without a merge: the PR number as its id, the time of the poll, no
author, and the loop stops on it.

## What the poll leaves out

- A pending review and its inline comments. They are not yet submitted.
- A review whose body is empty.
- A review or conversation comment older than `run.watch.last_polled_at`.
- An item whose last line starts `<!-- pr-review: `. That marker is your
  own reply.
- An item whose id is in `run.watch.seen_ids`.
- A passing or pending check. A `check` is a `fail`-bucket entry of
  `gh pr checks`. Its id holds its start time, so a re-run is new.

## The first write's cursor

Write `run.watch` first at the first arming, before the monitor starts, with
`crew-record.py <record-dir> run set watch '<json>'`. It takes `draft` from
the PR's `isDraft`, `head` from its `headRefOid` and `last_polled_at` from
the PR's creation time, and starts `seen_ids` and `held` empty. The first
poll then reports every item that landed before the arming. The marker
already keeps out your own replies.

On a `run.kind: review` run, `last_polled_at` is the arming time instead, not
the PR's creation time. Every earlier item is left to the people already in
that conversation.

```bash
gh pr view <pr_url> --json isDraft,createdAt,headRefOid -q '"\(.isDraft) \(.createdAt) \(.headRefOid)"'
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
while [ -z "$merged" ]; do poll; sleep 60; done
```

## The fallback poll

The poll block, then this line, in one Bash call per keep-alive fire.

```bash
poll; echo "isDraft=$d"
```

A fire that prints `isDraft=true` while `run.watch.draft` is false runs
`crew-record.py <record-dir> run set watch.draft true`. The fallback keeps no
state between fires, so this write is what lets a PR returned to draft fire
`ready` again. A fire after the merge prints the `merged` line again, and a
fire after a close prints the `closed` line again, so sort each as a notice
already reported.

## Verify a failed check

The run id is in the check's link, `.../actions/runs/<run-id>/job/<job-id>`.

```bash
gh run view <run-id> --repo <owner>/<repo> --log-failed
```

## Post a reply

Write the reply to a file outside the repo first, so a backtick in it reaches
GitHub intact. Its last line is `<!-- pr-review: <round-id> <item id> -->`,
with the id of the item it answers.

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
    | select($m | startswith("<!-- pr-review: <round-id> "))
    | "\($m | ltrimstr("<!-- pr-review: <round-id> ") | rtrimstr(" -->")) \(.id)"'
done
```

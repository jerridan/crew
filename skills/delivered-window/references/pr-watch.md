# PR watch commands

The exact command lines and arming steps for `SKILL.md`'s "Watch the PR" and
"Send the reply file". That file owns when each one runs.

Fill `<owner>`, `<repo>` and `<n>` from the deliverable's `pr_url`, which is
`https://github.com/<owner>/<repo>/pull/<n>`. Every command runs as the
principal's own `gh` account.

When `run.watch` has no `head`, the record is from before the key. Take
`head` from the `Reviewed:` line of the latest `reviews/skeptical-r<n>.md`,
or the deliverable's `base` when there is none. Write it to `run.watch` before
the monitor starts, so the first poll prints no `push` for a head the project
lead already knows.

## The poll

The poll is the script `scripts/pr-watch.sh` in this skill's directory.
`<watch-script>` below is its absolute path. Make the path from the base
directory of the last `crew:delivered-window` invocation that you read.

**Run the script from the plugin every time. Never copy it, and never write
the poll into the record or a scratch file.** A copy keeps the poll of the
plugin version that wrote it, and a later fix never reaches it (design
§15.123).

The script reads its start state from `<record-dir>/state.json` at each start.
The PR is the one deliverable with a `pr_url`. The cursor is `run.watch`:
`last_polled_at`, `seen_ids`, `draft`, `head` and `queued`. An absent `queued`
reads as `false`. A `head` of 7 characters or more that starts the PR's head
sha is the same head. The script exits 2 with a message on stderr when the
record has no `state.json`, has no single `pr_url`, or has no
`run.watch.last_polled_at` and `head`. Each `gh` read that fails prints
nothing, so a network error costs one quiet poll.

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

A `queued` line is for a PR that entered the merge queue: the PR number as
its id, the `enqueuedAt` time and no author. The loop does not stop on it. It
prints once per entry into the queue. The script starts from
`run.watch.queued`, and remembers the queued state from poll to poll. So a PR
already queued at the start prints no second `queued` line.
`gh pr view --json` has no merge-queue field, so the poll reads
`isInMergeQueue` through `gh api graphql`. A `merged` or `closed` state wins
over the queue.

A `dequeued` line is for a PR that left the merge queue and is still open. It
prints once, when the start state or an earlier poll of this loop was
queued, and the PR now reads `isInMergeQueue` false and state `OPEN`. A merge
or a close is not a dequeue. The line has this form, with the poll's time and
`-` for the author:

```
dequeued <pr-number> - <poll time> left the merge queue
```

Like `ready`, a `queued` or `dequeued` id never goes into `seen_ids`: the
queued state is what stops a repeat.

## What the poll leaves out

- A pending review and its inline comments. They are not yet submitted.
- A review whose body is empty, unless it is an approval. A comment-only
  review with an empty body holds only inline comments, and the review
  comments read reports those.
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

## Arm the monitor

1. Stop the monitor you armed before, with `TaskStop` and the task id its
   `Monitor` call returned. **One monitor at a time**: a second one doubles
   the wakes. A resumed process holds no monitor from the old one.
2. When `run.watch` is absent, write it first, as "The first write's cursor"
   says.
3. Read `gh pr view <pr_url> --json isDraft -q .isDraft`. When it reads true
   and `run.watch.draft` is false, run `crew-record.py <record-dir> run set
   watch.draft true`.
4. Call `Monitor` with "The monitor command" below and `timeout_ms:
   1800000`, so one cache read lands inside the one-hour cache. Pass
   `persistent: false` when the tool offers that key.
5. When the monitor ends at once with a `pr-watch.sh:` message, the record
   is not ready. Do what the message says, then arm it again.

## The monitor command

The script with no mode polls every 60 seconds. It stops after a `merged` or
`closed` line, and on no other.

```bash
bash <watch-script> <record-dir>
```

## Arm the keep-alive job

1. Call `CronList`. It lists the jobs this process holds, and a job ends
   with the process that made it. Delete each job whose prompt starts
   "Crew keep-alive" with `CronDelete`.
2. Call `CronCreate` with `recurring: true`, the cron `13,43 * * * *`, and
   one of these prompts. With a `pr_url`:

   ```
   Crew keep-alive with a PR watch. Run the fallback poll in pr-watch.md, in one Bash call, and sort what it prints.
   ```

   With no `pr_url`:

   ```
   Crew keep-alive. Reply with the single word ok. Run no tool.
   ```

The job has no end date. It fires until the run ships, until the principal
stops it, or until Claude Code expires it 7 days after you armed it. The
re-arm on a new date restarts those 7 days. **One job at a time** is what
step 1 is for: a second job would double the reads.

## The fallback poll

The script with the mode `once`, in one Bash call per keep-alive fire. It
polls one time and prints `isDraft=<true|false>` last.

```bash
bash <watch-script> <record-dir> once
```

A fire that prints `isDraft=true` while `run.watch.draft` is false runs
`crew-record.py <record-dir> run set watch.draft true`. The fallback keeps no
state between fires, so this write is what lets a PR returned to draft fire
`ready` again. A fire after the merge prints the `merged` line again, a fire
after a close prints the `closed` line again, and a fire while the PR is in
the merge queue prints the `queued` line again. Sort each as a notice already
reported. A fire reads `run.watch.queued` at its start, so it prints
`dequeued` when that reads `true` and the PR has left the queue.

## Verify a failed check

The run id is in the check's link, `.../actions/runs/<run-id>/job/<job-id>`.

```bash
gh run view <run-id> --repo <owner>/<repo> --log-failed
```

## Diagnose a dequeue

Run this on every `dequeued` line. `<dequeue-script>` is
`scripts/dequeue-diagnosis.sh` beside `<watch-script>`, by its absolute path:

```bash
bash <dequeue-script> <owner> <repo> <n>
```

It prints three sections, each `none` when it is empty:

1. The PR's `RemovedFromMergeQueueEvent` timeline items, read through
   GraphQL, each with its time, its actor and its reason.
2. The `merge_group` workflow runs whose `head_branch` holds `/pr-<n>-`,
   newest first, with each run's conclusion and URL.
3. The last 60 lines of the log of the first failed job of the most recent
   of those runs whose conclusion is `failure`.

Then `== mergeable` and the PR's `mergeable` value. A missing argument exits
2. `SKILL.md`'s "Watch the PR" says how the output sorts the item.

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

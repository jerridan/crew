# PR watch commands

What the watcher runs, and the command lines a window session uses.
`SKILL.md`'s "What the watcher sends you" owns which events reach a session.
Three scripts in this skill's `scripts/` directory do the mechanical steps:
`window-watch.py` starts and ends the watcher, the sessions and the inbox,
`watch-step.py` writes the cursor and the deploy setup, and `pr-reply.py`
posts a round's replies. `<window-watch>`, `<watch-step>` and `<reply-script>`
below are their absolute paths, made like `<watch-script>` ("The poll"). The
watcher runs the poll and the cursor write. A window session runs neither.

Fill `<owner>`, `<repo>` and `<n>` from the deliverable's `pr_url`, which is
`https://github.com/<owner>/<repo>/pull/<n>`. Every command runs as the
principal's own `gh` account.

When `run.watch` has no `head`, the record is from before the key. The head
is the `Reviewed:` line of the latest `reviews/skeptical-r<n>.md`, or the
deliverable's `base` when there is none. `window-watch.py start` writes it to
`run.watch`, so the first poll prints no `push` for a head the project lead
already knows.

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

On a review run (`run.kind` is `review`), the poll makes no `gh pr checks`
read and prints no `check` line. `SKILL.md`'s "Sort what reaches you" owns
that rule.

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
once, and the watcher stops this poll on it. The poll prints it last,
so the items of that poll are reported first. A `closed` line is the same for
a PR closed without a merge: the PR number as its id, the time of the poll, no
author, and the watcher stops this poll on it.

A `queued` line is for a PR that entered the merge queue: the PR number as
its id, the `enqueuedAt` time and no author. The watcher does not stop on it. It
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

## The first cursor

`window-watch.py start` writes `run.watch` first, from the PR at the time of
`start`. It takes `draft` from the PR's `isDraft`, `head` from its
`headRefOid` and `last_polled_at` from the PR's creation time, and starts
`seen_ids` empty. So the project lead's own last push and ready flip start no
session. The marker already keeps out your own replies.

On a `run.kind: review` run, `last_polled_at` is the time of `start`
instead, not the PR's creation time. Every earlier item is left to the people
already in that conversation.

A resume of a record that has no `run.watch` is the one exception. That
record is from before the watch, so the principal brought its PR reviews to
you by hand. `last_polled_at` is the clock, and `seen_ids` holds every review
comment already on the PR. `watch-step.py cursor <record-dir> --resume`
writes it. A record with a cursor is not written again.

## The cursor write

The watcher writes the cursor itself with `watch-step.py ack`, after it
writes a batch of lines to `window/pending.jsonl` and flushes the file. It
passes every line of the batch, also a `queued` line and a draft change. A
window session never runs it. The reported ids join `seen_ids`.
`last_polled_at` moves to the newest time among the reported `review` and
`comment` items. `draft` goes to `false` after a `ready` line, and `head`
moves on a `push` line. The call also writes `run.deploy.ended` for a
`deploy-failed` or `deploy-timeout` line.

## The deploy poll

`SKILL.md`'s "The deploy watch" says when this runs. The watcher runs these
steps on a `merged` line:

1. It resolves the winning `Deploy`. The order is a `Deploy:` line of
   `charter.md`, then the `Deploy` section of the repo file, then the one of
   the machine file, at the paths in `run.standing_instructions`
   (`<project-lead-dir>/SKILL.md`, "Standing instructions", owns the section's
   lines). Under `none` or `manual` it sets up no poll and writes no
   `run.deploy`. This is the one place that owns this order.
2. Otherwise it runs `python3 <watch-step> deploy <record-dir> --setup-only
   --source <name> [--environment <e>] [--workflow <w>] [--timeout
   <minutes>]`. The call writes `run.deploy` and returns with exit 0. It runs
   no poll. `--source` is the winning source's name, or `default`.
   `--environment` and `--workflow` are the winning section's values, and
   neither is set with no `Deploy` section. `--timeout` is the section's
   `timeout`. `since` is the time now, and `ended` is `null`. When `ended` is
   set, the call writes `since` and `ended` only. When `ended` is `null`, it
   writes nothing.
3. It writes `run.window.merged_seen` with the `at` time of the `merged` line,
   so the next poll does not queue the line again. It writes it under `none`
   and `manual` too.
4. It runs `pr-watch.sh <record-dir> deploy` itself, every 60 seconds. That
   script reads `run.deploy` from `state.json`. It needs no `run.watch`. It
   exits 2 with a message on stderr when `run.deploy` is absent, or when its
   `timeout_minutes` is not a positive integer. It exits 0 and prints nothing
   when `run.deploy.ended` is set.

The deploy poll reads the PR state, the merge commit and the merge time with
one `gh pr view`. A poll whose read fails uses the last good values. A PR
that is not merged prints nothing. After the merge it reads the deploy signal
that `run.deploy` names:

- `environment` set: the newest GitHub deployment of the merge commit to that
  environment, with its newest status.
- `workflow` set: the newest GitHub Actions run of that workflow, by name,
  with `head_sha` equal to the merge commit. Only `success` and the
  conclusions `failure`, `timed_out` and `startup_failure` are results. Any
  other run state is no result, and a newer run replaces it.
- both `null`: the repo's GitHub deployments are read. With some, the script
  reads the newest deployment of the merge commit whose
  `production_environment` is true or whose environment is named `production`
  or `prod`, in any case. Name the environment in a `Deploy` section for a
  repo whose production environment has another name. With none, the script
  reads the newest Actions run on the merge commit whose name holds `deploy`
  or `release`, in any case, like a named workflow. When there is no such run,
  the script reads the repo's workflows with `gh api --paginate
  repos/<owner>/<repo>/actions/workflows`. A workflow counts when its state is
  `active` and its name or path holds `deploy` or `release`, in any case. With
  no such workflow, the script reads the files the merged PR added or renamed
  with `gh api --paginate repos/<owner>/<repo>/pulls/<n>/files --jq '.[] |
  select(.status == "added" or .status == "renamed") | .filename'`. When none
  is under `.github/workflows/`, it prints `no-deploy` once 2 minutes have
  passed since the merge, and prints nothing before, so a deploy run or a
  deployment that shows in those 2 minutes wins. An edit of an existing
  workflow file does not count. When the PR added or renamed one, because it
  can add the first deploy workflow, the script keeps the wait that follows.
  With a counting workflow, it waits until 10 minutes after the merge,
  because the run may not exist yet, and then prints `no-deploy`. A failed
  workflows read or a failed files read keeps that wait for that poll, and is
  read again on the next poll.

The script prints one line and exits. The kinds are:

| Line | Meaning |
|---|---|
| `deployed <id> - <time> <environment or workflow> succeeded` | the newest deployment status or the newest run conclusion is `success` |
| `no-deploy <n> - <mergedAt> <text>` | only with both `null`: the repo has no deployment, no deploy run, no active deploy workflow and no workflow file that the merged PR added or renamed, and 2 minutes have passed since the merge (the text says so), or it has a deploy workflow, or such a file, and no deploy run 10 minutes after the merge. The repo has no deploy, and the line is the ship word. A failed read prints nothing |
| `deploy-failed <id> - <time> <environment or workflow> <state>` | the newest deployment state is `failure` or `error`, or the newest run conclusion is `failure`, `timed_out` or `startup_failure`. A deployment that still runs holds this line back |
| `deploy-timeout <n> - <time> no deploy seen <timeout> minutes after the watch started` | no result by `timeout_minutes` after `run.deploy.since`, or after `mergedAt` when the record has no `since`. When a deploy was seen but is still pending, the text says `no deploy finished` |
| `closed <n> - <time> the PR closed` | the PR closed with no merge |

`<n>` is the PR number, and `<id>` is the deployment or the run. A deployment
that a newer deploy made `inactive` counts as `success` when an earlier status
was `success`. An empty deploy read costs one quiet poll.

## Verify a failed check

The run id is in the check's link, `.../actions/runs/<run-id>/job/<job-id>`.

```bash
gh run view <run-id> --repo <owner>/<repo> --log-failed
```

## Diagnose a dequeue

A window session runs this on every `dequeued` line, except on a review run (`run.kind` is
`review`). `<dequeue-script>` is `scripts/dequeue-diagnosis.sh` beside
`<watch-script>`, by its absolute path:

```bash
bash <dequeue-script> <owner> <repo> <n>
```

It prints three sections, each under a `==` heading line:

1. The PR's `RemovedFromMergeQueueEvent` timeline items, read through
   GraphQL, each with its time, its actor and its reason.
2. The `merge_group` workflow runs whose `head_branch` holds `/pr-<n>-`,
   newest first, with each run's conclusion and URL. The section lists only
   the runs created at or after the PR's latest `AddedToMergeQueueEvent`. A
   run older than that belongs to an earlier try. When the script cannot
   read that event, it prints `no enqueue event; all runs shown` or
   `enqueue read failed: <status>; all runs shown`, then every run.
3. The last 60 lines of the log of the first failed job of the most recent
   run in section 2 whose conclusion is `failure`, `timed_out` or
   `startup_failure`.

Then `== mergeable` and the PR's `mergeable` value. A section with nothing
in it prints `none`. A section whose `gh` read exits non-zero prints
`read failed: <status>`, with the exit status. A missing argument exits with
status 2. `SKILL.md`'s "What the watcher sends you" says how the output sorts the line.

## Post a reply

`pr-reply.py send` posts every reply of a round in one call. Write the
replies file outside the repo first, so a backtick in a body reaches GitHub
intact. A line that starts `=== ` opens a reply. Every line below it, up to
the next such line, is its body:

```
=== <kind> <item-id> [to <comment-id>] [resolve]
<body>
```

`<kind>` is `review-comment`, `review`, `comment`, `check` or `dequeued`.
`<item-id>` is the id of the item the reply answers. The script drops the
blank lines at the end of each body, then adds the marker
`<!-- pr-review: <round-id> <item-id> -->` as its last line. Write no marker.
A header it cannot read, a `to` or a `resolve` on a kind other than
`review-comment`, an empty body and text before the first header end the call
with exit 2 before any post.

A `review-comment` replies in its own thread, on the thread's first comment,
which the script reads. `to <comment-id>` names a comment of another thread
than the item's own: the finding comment of an earlier round, when the item id
is that finding's id. `resolve` resolves the thread after the reply, also when
an earlier call posted the reply. Every other kind posts a PR conversation
comment with `gh pr comment`.

```bash
python3 <reply-script> send <record-dir> <round-id> <replies-file> [--mark-replied]
```

It prints one line per item: `posted <item-id> <reply-id>`, `skipped <item-id>
<reply-id> already posted`, `resolved <item-id> <thread-id>` or `failed
<item-id> <step>: <message>`. A failed item does not stop the others, and the
exit status is then 1. With `--mark-replied` and no failure, it runs `round
replied <round-id>` and prints `replied <round-id>`.

## Find the replies a round already posted

`send` runs this search itself, once, and skips an item that it finds. Only a
marker from the login of the principal's own `gh` account counts. To read the
result, for a resumed send or for a round's earlier finding ids, run:

```bash
python3 <reply-script> posted <record-dir> <round-id>
```

It prints the item id each reply answers, then the reply's own id, one reply
per line.
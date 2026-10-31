# The ready file

A `crew:review` run in child mode writes the ready file. The queue session
reads it, and posts from it with no second read of the PR. This file owns
the ready file's path, the time it is written and every field.
`/crew:review`'s "Child mode" owns what else changes in child mode.

## The path

`<record-dir>/ready.json`, where `<record-dir>` is the child's own review
record directory, `<record-root>/pr-<owner>-<repo>-<n>-<hex>/`.

## When the child writes it

Once, at the first point where a run outside child mode would run
`/crew:review`'s "Post the review". Write it in place of the post:

- on the review path, after "Report and wait at the gate" of round 1;
- on the assist path, at step 2 or step 6 of "The assist path", or at the
  `Rounds:` cap.

Write the draft file `reviews/github-r<n>.md` first, as "Report and wait at
the gate" says. Write the file whole, with one write, so the queue session
never reads half of it.

## The fields

One JSON object:

```
{ "repo": "<owner>/<name>", "pr": <integer>, "head": "<sha the child reviewed>",
  "verdict": "accepted" | "changes-needed", "event": "APPROVE" | "REQUEST_CHANGES" | "COMMENT",
  "blocking": <integer>, "fix_rounds": <integer>, "pushed": <boolean>,
  "draft_path": "<absolute path of the review draft>", "ledger": "<absolute path of the finding ledger>",
  "session_id": "<the child's session id>", "written_at": "<ISO-8601 UTC>" }
```

| Field | Value |
|---|---|
| `repo` | the PR's repository, `<owner>/<name>` |
| `pr` | the PR number |
| `head` | `run.review_pending.head` of the last round: the head the draft reviews |
| `verdict` | `accepted` when `blocking` is 0, and `changes-needed` otherwise |
| `event` | the event `github-review.md`'s "The event rule" gives for the draft |
| `blocking` | the count of `blocking` findings that the draft posts |
| `fix_rounds` | the count of fix rounds the assist path ran; 0 without `Assist: on` |
| `pushed` | `true` when the child pushed a commit to the PR branch |
| `draft_path` | the absolute path of `reviews/github-r<n>.md` of the last round |
| `ledger` | the absolute path of `reviews/skeptical-r<n>-reply.md` of the last round |
| `session_id` | `$CLAUDE_CODE_SESSION_ID` |
| `written_at` | the time of the write, in ISO-8601 UTC |

## Tell the queue session

After the write, send one cross-session message with `SendMessage`, to the
session the charter's `Queue:` line names. Its first line is `ready:
<absolute path of ready.json>`. Send nothing else to that session.

A failed send is retried once. A second failure is an escalation, as
`autonomy-contract.md`'s "How to escalate" says.

## A resume

A resume of a child-mode run reads `Queue:` in the charter. When
`ready.json` exists, send the message again, and stop. When it does not
exist, resume the open round, and child mode holds at every step.

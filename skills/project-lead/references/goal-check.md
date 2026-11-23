# Goal check

This file owns the **goal check**: the review of the finished diff on a goal
run, which is any run whose `run.kind` is not `review`. It runs once, at the
hand-over, on every path that hands over a branch. `simple-path.md`'s "The
goal check" is where a run enters the step, and `full-path.md` points there.

Two files own the rest. `skeptical-review.md` owns the round machinery that
the goal check shares with a review run: when a round is armed,
`review_pending`, the launch order, the resume list and the ledger.
`review-runner.md` owns the mechanics: the worktree, the command, the
instructions file, the checks and the session id.

A review run (`run.kind: review`) keeps the skeptical review on every head.
This file does not apply to it.

## The question

The goal check asks one question: **does the finished change do what the
charter asked, with every constraint that the principal stated?**

- **Read the diff against the goal and the repo, never against the spec.**
  The goal is what the principal wrote in `charter.md`, constraints and all.
  `spec.md` and the package briefs are your own writing, and a miss they
  share with the code is the miss this step exists to find.
- **Look for the three shapes of a goal miss.** A deliverable that the goal
  asked for is added and never run, such as a measurement script with no
  measurement. Code that the goal needs is reached by no caller. A stated
  exclusion is still broken, such as a module the goal kept out that a
  bundle still holds.
- **It is not a bug hunt.** The repo's own review owns code defects: CI, a
  bot or a person. A code defect that the check sees in passing is a
  `suggestion` at most, never `blocking`.
- **Only a goal miss can be `blocking`.** A goal miss is a change that does
  not do what the charter asked, or that breaks a constraint the principal
  stated.
- **It runs no suite and no gate.** Each package was verified against its
  criterion, you ran the suite on the branch head at "Integrate", and CI runs
  on the PR. What this gives up is a second suite run at the final head, by a
  reader other than you.
- **Say what was checked and found nothing.** Each part of the goal and each
  constraint that the check read and found met goes in the report.

`review-runner.md`'s goal-check block carries these rules to the reviewer.

**The report carries `Check: goal`.** The line comes after the `Reviewed:`
line, and after a `Source:` line when one exists. An older report has none.
`crew-stats.py` counts goal checks by this line. When a report on disk lacks
it, write it yourself before you adjudicate.

## One round

**The goal check runs once, on the head handed over.** `crew-record.py
deliver --review-head` arms round 1 at the hand-over, as
`skeptical-review.md`'s "When the review runs" says.

**No later round runs, on any head move.** That holds after a goal-miss
patch, a push for a PR comment, a CI finding, a change request and a rebase.
A follow-up package still integrates with `crew-record.py integrate
<package-id> --review-head <sha>`. Once `run.review_rounds` is 1 or more, that
write arms nothing. It leaves `review_pending` `null` and appends `{head,
reason: "goal-check-done", at}` to `run.unreviewed_heads`. A head moved by
a push that the PR watch sorts takes `arm-review --head <sha>`, with the same
result. No message to the principal names such a head.

**A failed round is retried, and the retry is the same round.**
`review-runner.md`'s failure path owns the retry.

**One more goal check is a command.** When the principal asks for one in
words, run `crew-record.py <record-dir> arm-review --head <branch head>
--past-cap`. It arms the head at the next round, and it writes no
`unreviewed_heads` entry. Log a `preference` decision whose `Citation:`
quotes the principal's words. That check launches fresh, as round 1 does,
with the goal-check block and the whole diff from the deliverable's `base`.
Never hand-edit `review_pending`.

## Labels and the verdict

**Label each finding** as `SKILL.md`'s "Every review in this run is
adjudicated the same way" says, with one limit: only a goal miss can be
`blocking`. Label a code defect that the goal check reports `suggestion` at
most. The repo's own review owns it.

**Your two verdict strings are `accepted` and `patch round needed`.** The
verdict is `accepted` exactly when the report holds no `blocking` finding,
and `patch round needed` exactly when it holds one or more.
`review-runner.md`'s goal-check block tells the reviewer both, and that rule.
`review-output.md` owns the shape of the three closing lines.

**Your labels decide the verdict.** When the reviewer wrote `accepted` and
you label a finding `blocking`, the verdict is `patch round needed`. When the
reviewer wrote `patch round needed` and no finding is `blocking` after your
labels, the verdict is `accepted`. Log each change in `decisions.md`. Then
write the verdict that results as the last line of the reply file:
`Verdict after labels: accepted` or `Verdict after labels: patch round
needed`. That line, not the report, is the verdict of the check. A session
that resumes reads it there. An `unsure` finding does not count as
`blocking` when you write the line. When the principal answers that it is
`blocking`, rewrite the line to `patch round needed` before the package for
that finding integrates. A check with no reply file holds no finding, and its
verdict is `accepted`.

## What follows the check

The reply file is `skeptical-review.md`'s ledger, and
`crew:delivered-window`'s "Findings from a review" owns the round it opens.

- **Put every accepted finding in one patch package**: each `blocking` goal
  miss, and each `suggestion` you take. Decline the rest, with the reason.
- **No second goal check follows that package.** Its integration arms
  nothing, as "One round" says.
- **`patch round needed` opens a round of the delivered window**, never a
  fix round on a package: the packages are integrated and the work is handed
  over.
- **Name each goal miss to the principal**, with the package that answers it,
  in your next message.

## Mark the PR ready

The PR opens as a draft at the hand-over (`simple-path.md`'s "End the run").
It leaves draft when the goal check is done and its patch, if any, is pushed.
The repo's own automated reviewers then start on a diff that crew has
finished with. This section is the only place that decides when. It does not
apply to a `run.kind: review` run, because the PR and its draft state are the
author's.

Mark the PR ready when all of these hold:

- The deliverable has a `pr_url`.
- `charter.md` has no `PR: draft` line. With that line, the PR stays a
  draft, and the principal marks it ready.
- `review_pending` is `null`: the goal check is adjudicated.
- No package is `pending` or `in-flight`: a goal-miss patch has integrated.
- Every `run.rounds` entry has a `replied_at`: its reply went out after the
  push.

A goal check that fails twice leaves `review_pending` set, so the PR stays a
draft. Say so in that escalation.

Run the check after every adjudication and after every reply you send. On a
resume, `skeptical-review.md`'s resume entry 9 runs it. Read the PR's state
from GitHub:

```
gh pr view <pr_url> --json isDraft -q .isDraft
```

`true` means write `crew-record.py run set watch.draft false`, then run `gh pr
ready <pr_url>`, and tell the principal in your next message that the PR is
ready for review. The write tells the PR watch that this flip is yours. Stop
the monitor before the write. Arm it again after `gh pr ready`, as
`crew:delivered-window`'s "Watch the PR" says, so the new command starts from
`false` and reports no `ready`. `false` means do nothing. The check reads
GitHub, not the record, so a session killed between the commands can run it
again safely.

When `run.orchestrator` is set, write the stage `pr` when this check passes,
as `orchestrator-report.md` says. With `PR: draft`, write it when every other
condition holds.

**Mark the PR ready once.** A later change request or patch round pushes to a
PR that is already ready. Never turn it back into a draft.

# Resume

This file owns what a project lead does when its argument is `--resume
<goal-slug>`: which record it reopens, which work it re-enters, and which path
it takes again. `SKILL.md`'s "Take the goal" sends you here.

A resume reopens the existing record, never a new directory. A `--resume`
argument carries no `Orchestrator:` line, so when `run.orchestrator` is set,
read `orchestrator-report.md` before you re-enter. Append this session's id to
`run.session_ids`, reconcile, re-enter at the first unfinished work, and
re-run nothing already finished. With `worktrees.json`, `full-path.md`'s
"Resume after a kill" owns the reconciliation; without it, `git log` on the
deliverable branch is the whole job. A resumed run writes no charter, no spec
and no new branch, and creates no record directory.

**A record whose `run_state` is already `complete` is closed.** Resume
nothing, and say so in the closing message.

**A record whose every deliverable holds a terminal state has no deliverable
left to make**: set `run_state: delivered` — or `blocked`, when an escalation
is open — and invoke the skill `crew:delivered-window` again. Which step
of that window you enter at is decided by one list, and only by it:
`skeptical-review.md`'s "Resume in the delivered window". It covers every
state this window can die in, and each entry names the file that owns the
work it sends you to.

**Read `run.review_pending` before you recover a package.** A head there
means a skeptical review is owed or half adjudicated, and its reply file may
already name packages that `packages[]` does not hold yet — recover blind and
you create one twice. Which comes first depends on the state, so take
`skeptical-review.md`'s resume list from the top and do what the first
matching entry says.

**A resume re-dispatches no spec critic that left a report.** A record whose
`reviews/` holds a spec critic report holds its one round. When `decisions.md`
holds no adjudication of that report, adjudicate it, then go on. A record
whose `reviews/` holds a spec critic reservation file and no report for it
holds no report: dispatch the critic again at the next reserved number.
`SKILL.md`'s "Have the spec reviewed" owns both rules.

**A resume picks the path too.** Read the reopened `charter.md` by the path
test in `SKILL.md`'s "Take the goal". A record holding `diagnosis.md` took the
investigation path and got as far as the artifact, so re-enter by that file's
`## Outcome`. A record with none re-enters at `investigation-path.md`'s first
unfinished phase.

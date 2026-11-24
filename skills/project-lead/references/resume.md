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

**A record whose `run.plan_review` exists with `status` `planning` or
`reviewing` died in the planning step.** `plan-review.md`'s "Resume in the
planning step" decides what you re-enter, before you recover any package. A
record with no `run.plan_review` takes the rules below.

**A record whose every deliverable holds a terminal state has no deliverable
left to make**: set `run_state: delivered` — or `blocked`, when an escalation
is open — and run `window-watch.py ensure <record-dir>`, which restarts a
dead watcher. A machine restart kills it, and so does a crash. Then take the
one session slot with `window-watch.py claim <record-dir> --session <name>`,
with a name of your own. Exit 3 means a window session holds the slot: that
session does the owed work, so say so and end. With the slot, invoke the skill
`crew:delivered-window` and work as a window session. Which step you enter at
is decided by one list, and only by it: `skeptical-review.md`'s "Resume in the
delivered window". It covers every state this window can die in, and each
entry names the file that owns the work it sends you to. Handle each
obligation that `record-format.md`'s "What a delivered-window round still
owes" lists, then run `window-watch.py done <record-dir> --session <name>` and
end. No resumed session stays up for PR events. `window-watch.py status
<record-dir>` prints `hold: true|false` and `intake: on|off`. `hold: true`
means the project lead died before its last call: finish the goal check, then
`goal-check.md`'s "The last call".

**Read `run.review_pending` before you recover a package.** A head there
means a review round is owed or half adjudicated, the goal check on a goal
run, and its reply file may
already name packages that `packages[]` does not hold yet — recover blind and
you create one twice. Which comes first depends on the state, so take
`skeptical-review.md`'s resume list from the top and do what the first
matching entry says.

**A resume before the sweep re-enters the spec review by `SKILL.md`'s "Have
the spec reviewed".** That section owns which spec critic report counts, and
when the critic is dispatched again.

**A resume picks the path too.** Read the reopened `charter.md` by the path
test in `SKILL.md`'s "Take the goal". A record holding `diagnosis.md` took the
investigation path and got as far as the artifact, so re-enter by that file's
`## Outcome`. A record with none re-enters at `investigation-path.md`'s first
unfinished phase.

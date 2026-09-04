# Simple path

This file owns the loop for one deliverable with one package (design §9.1).
`SKILL.md` runs steps 1 to 5 first, then sends you here.

The full path is `full-path.md`. Nothing here applies to it, except the three
steps it borrows: steps 7, 12 and 14 below, which it cites from its own steps
3, 9, 11 and 12.

One unnamed subagent does the work, in this checkout, on one branch. No split
critic runs, no worktree is created and nothing merges.

**A bounded edit runs a subset of these steps.** `SKILL.md`'s shape table
sends it here for steps 6 and 7, then 12 to 14. You make the edit yourself,
so steps 8 to 11 have no IC to dispatch and no package review to run. Every
other step holds as written, with the three exceptions steps 6, 7 and 13 name.

## 6. Write the split

Write `split.md` in `record-format.md`'s format, one deliverable and one
package, banded by `band-rubric.md`, mirrored into `state.json`'s
`packages[]`. No split critic runs — one package has no sibling to overlap.
`crew:deliverable-reviewer` reads it at step 13.

A bounded edit writes the same file and the same entry, so that steps 12 and
13 have a package to mark and a split to read. It consumes and produces
nothing, and its acceptance criterion is the charter's. Its file set is the
files the edit touches, less any shared file: `record-format.md` keeps those
out of every file set, and step 12 is where you edit them.

## 7. Create the branch

Read the checkout's branch: `git -C <repo> branch --show-current`. Then `git -C
<repo> switch -c crew/<goal-slug>/<deliverable-id>`; never work on the main
branch. Write the `deliverables[]` entry now — `id`, branch, the head sha as
`base`, `state: pending`, `pr_url: null`, and that branch as `checkout_branch`.

**A bounded edit makes its change here**, on the branch this step just
created. Copy this entry's `base` to the package's `base`, and set the package
and the deliverable `in-flight`, before you touch the file. Commit the change
when the edit is done.

## 8. Dispatch the IC

Dispatch one **unnamed** subagent at the package's band model: `crew:ic` for
code, `crew:ic-instructions` for an instruction file. It inherits no history,
so the spawn prompt carries all of: `ic-contract.md`'s full text, the brief,
the file set, this checkout's path, the interface contract, the acceptance
criterion, the global constraints section, the record root, the package id,
and **that it is a subagent** — `ic-contract.md`'s plan gate branches on it.

**The plan gate is two dispatches here.** The first ends at `plans/<id>.md` —
a subagent has no channel to wait on. Read it, approve it or send it back, set
`plan_approved_at`, then dispatch again to implement, naming the plan's path.

**Expect the contents instead of the file.** A dispatch shape that denies
the IC every record write (§15.26b, §15.31b) puts the plan or report in its
final message. Transcribe it, and say that you did.

Set the package and its deliverable `in-flight` at the first dispatch, and write
the package's `base`: the deliverable's `base`, since there is one package.

## 9. Verify before you believe

The IC's report is a claim; `git -C <repo> log` and `diff` are the evidence.
Check the diff's file list against the declared file set, and run the acceptance
criterion yourself. `band-rubric.md` says what a `BLOCKED` cause earns.

**Run the criterion at the red commit too**, when the package adds the test
its criterion names (design §7). `ic-contract.md`'s "Write the failing test
first" owns this check: it gives the procedure, the clean-tree precondition,
and what a criterion that passes there costs. Run it here, in this checkout,
against the sha the IC's report gives. Switch the branch back before anything
else — this is the principal's own checkout, and step 14's
`checkout_restored` records what it was left on.

## 10. Review the package

Write the diff to `diffs/<id>-r<n>.patch` so it never enters your context:
`git -C <repo> diff <base>..HEAD > <path>`, `base` being the deliverable's.
An instruction package gets its checklist file instead.

`crew:package-reviewer` requires five inputs. Send all five: the package's
record entry (`file_set`, `interface_contract`, `acceptance_criterion`), the
checkout path, the IC's report, the diff or checklist path, and the brief.
Inject `review-output.md` too, at its absolute path:
`<record-root>/reviews/<id>-package-review-r<n>.md`, `<n>` being `fix_rounds_used`.

## 11. Fix rounds

Run a round only on `Verdict: fix round needed`. Each round is a fresh
subagent, so its prompt describes what is already committed — `git log
--oneline` plus `git diff --stat` — and which findings to fix. Rounds 4 and 5
promote a band; `band-rubric.md` says what a `deep` package does instead.

**Every round goes back through steps 9 and 10** — a fix nobody re-reviewed
is a claim. Leave only on `Verdict: accepted`. Increment `fix_rounds_used`
**before** the round runs — steps 10 and 11 name their files from it, so a
late increment overwrites the previous round's files. Five is the cap: at
it, fix the package yourself or park it as `abandoned` with your reasoning
recorded. At the top band, escalate instead.

## 12. Integrate

Nothing merges — the work is already on the deliverable branch. Run the suite
on the branch head and read the output. Then read the target repo's own
instructions for which shared files must change together, edit them, and keep
the values they require equal. Commit them, and mark the package `integrated`.

**Sweep for stale status claims.** You own this check alone. Run the block in
`writing-standard.md`'s "Keep the status true" over the deliverable branch.

**Write the diff again now**, to `diffs/<deliverable-id>-final.patch`. Step
10's diff predates the fix rounds and the shared-file edits you just made,
which the next reviewer's shared-file check exists to read.

## 13. Review the deliverable

Dispatch `crew:deliverable-reviewer`, unnamed, with `spec.md`, `split.md`,
the checkout path and base ref, the fresh diff path, the accepted package
review, `review-output.md` whole, and its absolute path:
`<record-root>/reviews/<deliverable-id>-deliverable-review.md`. Four of its
seven checks need the record. Adjudicate as in `SKILL.md` step 4; clear every
`[Critical]` first.

A bounded edit has no package review, because no package reviewer ran. Send
the other inputs, and say in the dispatch that you made the edit yourself.

## 14. End the run

Push the branch. Fill the repo's pull request template if it has one, and put
`spec.md` and `decisions.md` in the body, one long line per paragraph and list
item. Never hard wrap what you send to GitHub (`writing-standard.md`).

`gh pr create --draft`. Record `pr_url`, set the deliverable
`draft-pr-opened` and `run_state: complete`. A human merges it. Then run
`scripts/spend.py --write` (`autonomy-contract.md`), and stop every process
the run left listening — `lsof -iTCP -sTCP:LISTEN` names them (§15.50).

When the push or `gh pr create` cannot run, check `escalations` first for the
entry with trigger text `launch check 3 (trigger 7): no remote` — the
preference sweep writes it only when `full-path.md` step 0's check 3 failed,
before the split (`autonomy-contract.md`). Found: act on the answer, and do
not ask again. "Keep the work local" means skip straight to `work-complete`
below. "Add a remote" means one should already exist — push. If it still
fails, the promised remote never arrived: that is new information, so
escalate it now, plainly, the same way as below.

No such entry means check 3 passed at the sweep — this checkout had a remote
then. A push or `gh pr create` failure here is a different problem: expired
auth, a rejected push, a repo setting. Ask the principal, plainly, and
**wait for the answer**: `blocked` until it lands, then `active`. One who
already refused the PR has answered; do not ask twice. Then record
`work-complete`, `pr_url: null` and `run_state: complete` in one write, and
hand over the branch.

**Restore the checkout at every end.** With a clean tree and a
`checkout_branch`, `git -C <repo> switch <checkout_branch>`; otherwise record
why not in `checkout_restored`. Name both branches in your last message.

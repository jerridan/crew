---
name: project-lead
description: Take one goal to a reviewable draft PR without stopping for approval. Use when handing off a whole goal rather than a single task. Triggers on "run this as a project", "hand this to crew", "take this to a draft PR".
---

# Project lead

You take one goal to a reviewable draft PR. You answer your own questions, and
you stop for the **principal** only when you cannot proceed correctly.

## The references

The **simple path** is steps 6-14 below; the **full path** is
`references/full-path.md`, and step 5 routes between them.

- `references/autonomy-contract.md` owns routing, councils, escalation, spend,
  and who the principal is. Read it before your first question, not at one.
- `references/record-format.md` owns the record: every file, field and
  state transition. Read it before you create the record.
- `references/band-rubric.md` owns the band.
- `references/ic-contract.md` is the IC's rules. You do not follow it.
- `references/writing-standard.md` governs any instruction file you draft.
- `references/review-output.md` is the shape every review agent reports in.
  Inject it whole into every review dispatch. You do not follow it.

`record-format.md` says how to write `state.json`, with `scripts/crew-record.py`
beside this file. Every path you hand an agent is absolute: its cwd is not yours.

## 1. Take the goal

**Plan mode stops every dispatch.** If it is on, say so and stop — planning
the goal yourself is not the job (design §15.32).

The argument is `--resume <goal-slug>`, a goal string, or a charter path. A
path that exists on disk becomes `charter.md` unchanged. Any other string you
expand into `charter.md`: the goal, and one falsifiable acceptance criterion.

**`--resume` skips the rest of this step.** It reopens the existing record —
never a new directory — appends this session's id to `run.session_ids`, and
reconciles. With `worktrees.json`, `full-path.md` step 13 owns the
reconciliation; without it, `git log` on the deliverable branch is the whole
job. Re-enter at the first unfinished step and re-run no finished one. A
resumed run writes no charter, no spec and no new branch.

On a new goal: write no falsifiable criterion, do no work — escalate and stop.
Otherwise create `<record-root>/<slug>-<4 hex chars>/`, generating the suffix
once; `record-format.md` says where the root is. Write `charter.md`, then
`crew-record.py init` with `$CLAUDE_CODE_SESSION_ID` — read it, never invent
it — and `run set spend.budget` when the charter carries a `Budget:` line.

## 2. Scout

Keep the reading out of your own context: dispatch `Explore` subagents and read
their answers. Settle four questions. Does an analogous implementation exist?
Do tests cover this surface? What runs the suite? Which instruction files apply?

## 3. Write the spec

Write `spec.md`: the requirements, an acceptance criterion per requirement
that a command or a checklist can fail, the global constraints in full
(version floors, dependency limits, naming rules, platform requirements), and
the non-goals. State requirements, never implementations. A constraint
points at a file; it never enumerates the file's contents, because a closed
list is one missed item from a critic round (design §15.50).

Outline the spec yourself, have an unnamed `general-purpose` subagent at
`sonnet` write the prose, and revise what it returns. The spec is yours.

## 4. Have the spec reviewed

Dispatch `crew:spec-critic`, unnamed, with `spec.md`, `charter.md`, the repo
path, `review-output.md` whole, and the absolute path it writes its findings
to: `reviews/spec-critic-r<n>.md`, `<n>` being one more than the highest on
disk. Every review dispatch names its path this way and returns three lines;
open the file only when the count says there is something to adjudicate.

On `Verdict: re-spec needed`, adjudicate, revise `spec.md`, and dispatch
again. Three re-specs is the cap; escalate at it.

Adjudicate every review the same way: restate each finding in your own words,
verify it against the repo, and push back in writing where it is wrong here.

## 4a. Sweep for preference questions

Escalate every question in `charter.md` and `spec.md` that the repo cannot
answer, as one batch, before you split. `autonomy-contract.md` owns the rule.

## 5. Choose the shape

| The work is | You |
|---|---|
| A bounded edit: 1-2 tool calls, no file reading | Do it yourself, on a branch. Run step 7, then steps 12-14. |
| One package, short enough to run unattended | Run steps 6-14 |
| More than one package, or work long enough to need steering | Read `references/full-path.md` and run it in place of steps 6-14 |

## 6. Write the split

Write `split.md` in `record-format.md`'s format, one deliverable and one
package, banded by `band-rubric.md`, mirrored into `state.json`'s
`packages[]`. No split critic runs — one package has no sibling to overlap.
`crew:deliverable-reviewer` reads it at step 13. `full-path.md` step 1's
verification-tool rule holds here too.

## 7. Create the branch

Read the checkout's branch: `git -C <repo> branch --show-current`. Then `git -C
<repo> switch -c crew/<goal-slug>/<deliverable-id>`; never work on the main
branch. Write the `deliverables[]` entry now — `id`, branch, the head sha as
`base`, `state: pending`, `pr_url: null`, and that branch as `checkout_branch`.

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
seven checks need the record. Adjudicate as in step 4; clear every
`[Critical]` first.

## 14. End the run

Push the branch. Fill the repo's pull request template if it has one, and put
`spec.md` and `decisions.md` in the body, one long line per paragraph and list
item. Never hard wrap what you send to GitHub (`writing-standard.md`).

`gh pr create --draft`. Record `pr_url`, set the deliverable
`draft-pr-opened` and `run_state: complete`. A human merges it. Then run
`scripts/spend.py --write` (`autonomy-contract.md`), and stop every process
the run left listening — `lsof -iTCP -sTCP:LISTEN` names them (§15.50).

When the push or `gh pr create` cannot run, ask the principal and **wait for
the answer** — `blocked` until it lands, then `active`. One who already refused
the PR has answered; do not ask twice. Then record `work-complete`,
`pr_url: null` and `run_state: complete` in one write, and hand over the branch.

**Restore the checkout at every end.** With a clean tree and a
`checkout_branch`, `git -C <repo> switch <checkout_branch>`; otherwise record
why not in `checkout_restored`. Name both branches in your last message.

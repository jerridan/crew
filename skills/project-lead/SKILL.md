---
name: project-lead
description: Take one goal to a reviewable draft PR without stopping for approval. Use when handing off a whole goal rather than a single task. Triggers on "run this as a project", "hand this to crew", "take this to a draft PR".
---

# Project lead

You take one goal to a reviewable draft PR. You answer your own questions,
and you stop for the **principal** — whoever handed you this goal, the human
in this session today and a lead session later — only when you cannot
proceed correctly.

## What is built

Both paths run. The **simple path** — steps 6 to 14 below — is one package on
the deliverable branch here, worked by one unnamed subagent. The **full path**
is several packages in worktrees, worked by named IC teammates, and
`references/full-path.md` owns it. Councils are not built; that row in
`references/autonomy-contract.md` says what to do instead.

## The references

- `references/autonomy-contract.md` owns routing, escalation and spend.
  Read it before your first question, not when you hit one.
- `references/record-format.md` owns the record: every file, field and
  state transition. Read it before you create the record.
- `references/full-path.md` owns the loop for more than one package. Read it
  at step 5, only if that is the shape.
- `references/band-rubric.md` owns the band. Read it at step 6.
- `references/ic-contract.md` is the IC's rules. Inject it whole into the
  spawn prompt. You do not follow it.
- `references/writing-standard.md` governs any instruction file you draft.
- `references/review-output.md` is the shape every review agent reports in.
  Inject it whole into every review dispatch. You do not follow it.

Write `state.json` after **every** transition, never batched.

## 1. Take the goal

**Plan mode stops every dispatch.** If it is on, say so and stop — planning
the goal yourself is not the job (design §15.32).

The argument is `--resume <goal-slug>`, a goal string, or a path to a
charter file. A path that exists on disk becomes `charter.md` unchanged. Any
other string you expand into `charter.md` yourself: the goal, and one
falsifiable acceptance criterion.

**`--resume` skips the rest of this step.** It reopens
`~/.claude/crew/<goal-slug>/` — never a new directory — appends this session's
id to `run.session_ids`, and reconciles. `worktrees.json` says which path you
are resuming, because the simple path never writes it: with it, `full-path.md`
step 13 owns the reconciliation; without it, `git log` on the deliverable
branch is the whole job. Re-enter at the first unfinished step and re-run no
finished one. A resumed run writes no charter, no spec and no new branch.

On a new goal: write no falsifiable criterion, do no work — escalate and stop.
Otherwise create `~/.claude/crew/<slug>-<4 hex chars>/`, generating the suffix
once. Write `charter.md`, then `state.json` with `run_state: active` and a
spend ceiling of 2,000,000 tokens unless the principal names one.

## 2. Scout

Keep the reading out of your own context: dispatch `Explore` subagents and
read their answers. Settle four questions. Does an analogous implementation
exist? Do tests cover this surface? What runs the suite? Which instruction
files apply — `CLAUDE.md`, `.claude/rules/`, a nested one?

## 3. Write the spec

Write `spec.md`: the requirements, an acceptance criterion per requirement
that a command or a checklist can fail, the global constraints in full
(version floors, dependency limits, naming rules, platform requirements), and
the non-goals. State requirements, never implementations.

## 4. Have the spec reviewed

Dispatch `crew:spec-critic`, unnamed, with `spec.md`, `charter.md`, the repo
path, and `review-output.md` whole. Write its findings to
`reviews/spec-critic-r<n>.md`, `<n>` being one more than the highest on disk.

On `Verdict: re-spec needed`, adjudicate, revise `spec.md`, and dispatch
again. Three re-specs is the cap; escalate at it.

Adjudicate every review the same way: read the whole set, restate each finding
in your own words, verify it against the repo, and push back in writing where
it is wrong here. A finding is a claim, not a verdict.

## 5. Choose the shape

| The work is | You |
|---|---|
| A bounded edit: 1-2 tool calls, no file reading | Do it yourself, on a branch. Run step 7, then steps 12-14. |
| One package, short enough to run unattended | Run steps 6-14 |
| More than one package, or work long enough to need steering | Read `references/full-path.md` and run it in place of steps 6-14 |

Your own context is the most expensive place to work.

## 6. Write the split

Write `split.md` in `record-format.md`'s format, one deliverable and one
package. Assign the band from `band-rubric.md`, and mirror every field into
`state.json`'s `packages[]`. No split critic runs — one package has no sibling
to overlap. Write it anyway; `crew:deliverable-reviewer` reads it at step 13.

## 7. Create the branch

Branch from the current head:
`git -C <repo> switch -c crew/<goal-slug>/<deliverable-id>`.
Never work on the main branch. Write the `deliverables[]` entry now — `id`,
branch, the head sha as `base`, `state: pending`, `pr_url: null`.

## 8. Dispatch the IC

Dispatch one **unnamed** subagent at the package's band model: `crew:ic` for
code, `crew:ic-instructions` for a `CLAUDE.md`, a `.claude/rules/` file, a
`SKILL.md` or an agent definition.

It inherits no history, so the spawn prompt carries all of:
`ic-contract.md`'s full text, the brief, the file set, this checkout's path,
the interface contract, the acceptance criterion, the global constraints
section, the record root, the package id, and **that it is a subagent** —
`ic-contract.md`'s plan gate branches on it.

**The plan gate is two dispatches here.** The first ends at `plans/<id>.md` —
a subagent has no channel to wait on. Read it, approve it or send it back, set
`plan_approved_at`, then dispatch again to implement, naming the plan's path.

**Expect the contents instead of the file.** Some dispatch shapes deny an IC
every write to the record root (§15.26b, §15.31b); its final message then
carries the plan or the report. Transcribe it, and say that you did.

Set the package and its deliverable `in-flight` at the first dispatch, and
write the package's `base`: the deliverable's `base`, since there is one
package.

## 9. Verify before you believe

The IC's report is a claim. `git -C <repo> log` and `git -C <repo> diff` are
the evidence. Check the diff's file list against the declared file set, and run
the acceptance criterion yourself. A `BLOCKED` report names its cause;
`band-rubric.md` says what each earns.

## 10. Review the package

Write the diff to `diffs/<id>-r<n>.patch` so it never enters your context:
`git -C <repo> diff <base>..HEAD > <path>` — one package means its `base` is
the deliverable's. An instruction package gets its checklist file instead.

`crew:package-reviewer` requires five inputs and says so. Send all five: the
package's record entry (`file_set`, `interface_contract`,
`acceptance_criterion`), the checkout path, the IC's report, the diff or
checklist path, and the brief. Inject `review-output.md` too.

Write its findings to `reviews/<id>-package-review-r<n>.md`, `<n>` being
`fix_rounds_used`.

## 11. Fix rounds

Run a round only on `Verdict: fix round needed`. Each round is a fresh
subagent, so its prompt describes what is already committed — `git log
--oneline` plus `git diff --stat` — and which findings to fix. Rounds 4 and 5
run one band up, unless the package is `deep`: then escalate.

**Every round goes back through steps 9 and 10** — a fix nobody re-reviewed
is a claim. Leave this step only on `Verdict: accepted`.

Increment `fix_rounds_used` and write `state.json` **before** the round runs —
steps 10 and 11 name their files from that counter, so a late increment
overwrites the previous round's diff and review. Five is the cap: at it, fix
the package yourself or park it as `abandoned` with your reasoning recorded.
At the top band, escalate instead.

## 12. Integrate

Nothing merges — the work is already on the deliverable branch. Run the
suite on the branch head and read the output yourself. Then edit the shared
files: read the target repo's own instructions for which must change
together, and keep the values they require equal. Commit them, and mark the
package `integrated`.

**Write the diff again now**, to `diffs/<deliverable-id>-final.patch`. Step
10's diff predates the fix rounds and
every shared-file edit you just made — the edits the next reviewer's
shared-file check exists to read.

## 13. Review the deliverable

Dispatch `crew:deliverable-reviewer`, unnamed, with `spec.md`, `split.md`,
the checkout path and base ref, the fresh diff path, the accepted package
review, and `review-output.md` whole. It cannot run four of its seven checks
from a diff alone.

Write its findings to `reviews/<deliverable-id>-deliverable-review.md`.
Adjudicate as in step 4. Clear every `[Critical]` before the PR opens.

## 14. Open the draft PR

Push the branch. Fill the repo's pull request template if it has one, and put
`spec.md` and `decisions.md` in the body. Write each paragraph and list item
on one long line — GitHub renders a single newline as a line break.

`gh pr create --draft`. Record `pr_url`, set the deliverable
`draft-pr-opened` and `run_state: complete`. A human merges it.

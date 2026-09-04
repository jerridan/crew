---
name: project-lead
description: Take one goal to a reviewable draft PR without stopping for approval. Use when handing off a whole goal rather than a single task. Triggers on "run this as a project", "hand this to crew", "take this to a draft PR".
---

# Project lead

You take one goal to a reviewable draft PR. You answer your own questions, and
you stop for the **principal** only when you cannot proceed correctly.

## The references

This file owns steps 1 to 5. Step 5 then sends you to one path file, which
owns steps 6 to 14: `references/simple-path.md` for one package,
`references/full-path.md` for more than one.

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

**Your output is the run's most expensive.** So outline the spec yourself,
have an unnamed `general-purpose` subagent at `sonnet` write the prose, and
revise what it returns. The spec is yours.

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
**A finding is a claim, not a verdict.**

## 4a. Sweep for preference questions

Escalate every question in `charter.md` and `spec.md` that the repo cannot
answer, as one batch, before you split. `autonomy-contract.md` owns the rule.

## 5. Choose the shape

| The work is | You |
|---|---|
| A bounded edit: 1-2 tool calls, no file reading | Do it yourself, on a branch. Read `references/simple-path.md`, run its step 7, then its steps 12-14. |
| One package, short enough to run unattended | Read `references/simple-path.md` and run its steps 6-14 |
| More than one package, or work long enough to need steering | Read `references/full-path.md` and run its steps 0-13 |

**Your own context is the most expensive place to work.** Dispatch the
reading, the drafting and the diffs; keep the decisions.

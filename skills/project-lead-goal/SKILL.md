---
name: project-lead-goal
description: Take one goal to a reviewable draft PR without stopping for approval, stated as a goal and its constraints instead of a numbered loop. Use only when the launch names this form — `project-lead` is the default. Triggers on "run this as a project, goal form", "hand this to crew, goal form".
---

# Project lead

Take one goal to a reviewable draft PR that a human can merge. Answer your
own questions. Stop for the **principal** only when you cannot proceed
correctly.

The judgment is your job: the spec, the split, the order of the work, and
every adjudication. Dispatch the reading, the drafting and the diffs — your
own context is the most expensive place to work.

## Where the rules live

One reference sits beside this file: `references/simple-path.md`. Every other
reference and every script lives in the sibling skill directory
`../project-lead/`. Resolve that to an absolute path once, and use absolute
paths from then on. Every path you hand an agent is absolute: its cwd is not
yours.

| File | What it owns | When you read it |
|---|---|---|
| `autonomy-contract.md` | routing, councils, escalation, spend, and who the principal is | before your first question, not at one |
| `record-format.md` | the record: every file, field and state transition, and how `scripts/crew-record.py` writes `state.json` | before you create the record |
| `band-rubric.md` | the band | at the split |
| `review-output.md` | the shape every review agent reports in | inject it whole into every review dispatch; you do not follow it |
| `writing-standard.md` | any instruction file you draft | before you draft one |
| `ic-contract.md` | the IC's rules | you do not follow it |
| `references/simple-path.md`, beside this file | the whole run for one package | when the shape is one package |
| `../project-lead/references/full-path.md` | the whole run for more than one package | when the shape is more than one |

Other files cite this file by step number. Two rules carry those citations:

| Cited as | The rule here |
|---|---|
| `SKILL.md` step 4 | **How you adjudicate a review** |
| `SKILL.md`'s shape table | **The shape** |

## Before anything

**Plan mode stops every dispatch.** If it is on, say so and stop — planning
the goal yourself is not the job (design §15.32).

## The charter and the record

Your argument is one of three: `--resume <goal-slug>`, a goal string, or a
path to a charter.

**`--resume <goal-slug>`** reopens the existing record, never a new
directory. Append this session's id to `run.session_ids`, reconcile, re-enter
at the first unfinished work, and re-run nothing already finished. With
`worktrees.json`, `full-path.md`'s reconciliation owns the reconciliation;
without it, `git log` on the deliverable branch is the whole job. A resumed
run writes no charter, no spec and no new branch, and nothing else in this
section applies to it.

**A path that exists on disk** becomes `charter.md` unchanged. **Any other
string** you expand into `charter.md`: the goal, and one falsifiable
acceptance criterion. A goal you cannot give a falsifiable criterion is not a
run — escalate and stop, before you do any work.

Then the record: `<record-root>/<slug>-<4 hex chars>/`, the suffix generated
once; `record-format.md` says where the root is. Write `charter.md`, then
`crew-record.py init` with `$CLAUDE_CODE_SESSION_ID` — read it, never invent
it — and `run set spend.budget` when the charter carries a `Budget:` line.

## What you must know before you write a spec

Four questions, answered from this repo. Does an analogous implementation
exist? Do tests cover this surface? What runs the suite? Which instruction
files apply?

Dispatch `Explore` subagents and read their answers. The reading stays out of
your own context.

## The spec

`spec.md` is done when it carries the requirements, an acceptance criterion
per requirement that a command or a checklist can fail, the global
constraints in full (version floors, dependency limits, naming rules,
platform requirements), and the non-goals.

State requirements, never implementations. A constraint points at a file; it
never enumerates the file's contents, because a closed list is one missed
item from a critic round (design §15.50).

**Your output is the run's most expensive.** So outline the spec yourself,
have an unnamed `general-purpose` subagent at `sonnet` write the prose, and
revise what it returns. The spec is yours.

## The spec review

Dispatch `crew:spec-critic`, unnamed, with `spec.md`, `charter.md`, the repo
path, `review-output.md` whole, and the absolute path it writes its findings
to: `reviews/spec-critic-r<n>.md`, `<n>` being one more than the highest on
disk. Every review dispatch in this run names its path this way and returns
the short result `review-output.md` defines; open the file only when the
count says there is something to adjudicate.

`Verdict: re-spec needed` means adjudicate, revise `spec.md`, and dispatch
again. Three re-specs is the cap; escalate at it.

### How you adjudicate a review

Every review in this run, at every stage, the same way: restate each finding
in your own words, verify it against the repo, and push back in writing where
it is wrong here. **A finding is a claim, not a verdict.**

## The preference sweep

Every question in `charter.md` and `spec.md` that the repo cannot answer is
escalated, as one batch, before you split. `autonomy-contract.md` owns the
rule.

## The shape

| The work is | You |
|---|---|
| A bounded edit: 1-2 tool calls, no file reading | Do it yourself, on a branch. Read `references/simple-path.md`; it names the subset a bounded edit runs. |
| One package, short enough to run unattended | Read `references/simple-path.md`, beside this file. It owns the rest of the run. |
| More than one package, or work long enough to need steering | Read `../project-lead/references/full-path.md`. It owns the rest of the run. |

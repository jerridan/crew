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

You run the **simple path**: one deliverable, one package, one unnamed
subagent, on the deliverable branch in this checkout. No worktree, no
teammate, no split critic, no merge.

Two things are not built, and you improvise neither. **The full path** —
several packages in worktrees: when scouting shows the goal needs more than
one package, stop at step 5 and say so. **Councils**: answer a
council-route question inline with a citation, or escalate it.

## The references

- `references/autonomy-contract.md` owns routing, escalation and spend.
  Read it before your first question, not when you hit one.
- `references/record-format.md` owns the record: every file, field and
  state transition. Read it before you create the record.
- `references/band-rubric.md` owns the band. Read it at step 6.
- `references/ic-contract.md` is the IC's rules. Inject it whole into the
  spawn prompt. You do not follow it.
- `references/writing-standard.md` governs any instruction file you draft.

Write `state.json` after **every** transition, never batched.

## 1. Take the goal

The argument is a goal string or a path to a charter file. A path that
exists on disk becomes `charter.md` unchanged. Anything else you expand into
`charter.md` yourself: the goal, and one falsifiable acceptance criterion.

Write no falsifiable criterion, do no work: escalate and stop.

Create `~/.claude/crew/<slug>-<4 hex chars>/`, generating the suffix once.
Write `charter.md`, then `state.json` with `run_state: active` and a spend
ceiling of 2,000,000 tokens unless the principal names one.

## 2. Scout

Keep the reading out of your own context: dispatch `Explore` subagents and
read their answers. Settle four questions first. Does an analogous
implementation already exist? Do tests cover this surface? What command runs
the suite? Which instruction files apply — `CLAUDE.md`, then
`.claude/rules/`, then a nested `CLAUDE.md`?

## 3. Write the spec

Write `spec.md`: the requirements, an acceptance criterion per requirement
that a command or a checklist can fail, the global constraints written out
(version floors, dependency limits, naming rules, platform requirements),
and the non-goals. State requirements, never implementations.

## 4. Have the spec reviewed

Dispatch `crew:spec-critic`, unnamed, with `spec.md`, `charter.md` and the
repo path. Write its findings to `reviews/spec-critic-r<n>.md`, `<n>` being
one more than the highest already on disk.

On `Verdict: re-spec needed`, adjudicate, revise `spec.md`, and dispatch
again. Three re-specs is the cap; escalate at it.

Adjudicate every review the same way: read the whole set, restate each
finding in your own words, verify it against the repo, and push back in
writing where it is wrong here. A reviewer's finding is a claim, not a
verdict.

## 5. Choose the shape

| The work is | You |
|---|---|
| A bounded edit: 1-2 tool calls, no file reading | Do it yourself, on a branch. Run step 7, then steps 12-14. |
| One package | Run steps 6-14 |
| More than one package | Stop. Say the full path is not built. |

Your own context is the most expensive place to work.

## 6. Write the split

Write `split.md` in `record-format.md`'s format, one deliverable and one
package. Assign the band from `band-rubric.md`, and mirror every field into
`state.json`'s `packages[]`.

Shared files are yours, not the package's: version manifests, lockfiles,
barrel and `index` files, and shared config never enter a file set.

No split critic runs — one package has no sibling to overlap. Write
`split.md` anyway: `crew:deliverable-reviewer` reads it at step 13.

## 7. Create the branch

Branch from the current head: `git -C <repo> switch -c crew/<deliverable-id>`.
Never work on the main branch. Write the `deliverables[]` entry now — `id`,
branch, the head sha as `base`, `state: pending`, `pr_url: null`. It has no
`pending` to `draft-pr-opened` edge, so it passes through `in-flight` at
step 8.

## 8. Dispatch the IC

Dispatch one **unnamed** subagent at the package's band model: `crew:ic` for
code, `crew:ic-instructions` for a `CLAUDE.md`, a `.claude/rules/` file, a
`SKILL.md` or an agent definition.

It inherits no history, so the spawn prompt carries all of:
`ic-contract.md`'s full text, the brief, the file set, this checkout's path,
the interface contract, the acceptance criterion, the global constraints
section, the record root, and the package id.

**The plan gate is two dispatches here.** The first ends at
`plans/<id>.md` — a subagent has no message channel to wait on. Read that
plan, approve it or send it back, set `plan_approved_at`, then dispatch
again to implement and name the plan's path in that prompt.

**Expect the contents instead of the file.** A sandbox can deny every write
to the record root, and today one usually does (design §15.26b).
`ic-contract.md` then makes the IC's final message its plan or its report.
Transcribe it into `plans/<id>.md` or `reports/<id>.md` unchanged, and say
in the file that you transcribed it.

Set the package and its deliverable `in-flight` at the first dispatch.

## 9. Verify before you believe

The IC's report is a claim. `git -C <repo> log` and `git -C <repo> diff` are
the evidence. Check the diff's file list against the declared file set, and
run the acceptance criterion yourself.

A `BLOCKED` report names its cause. Only a `capability` cause promotes a
band; for an `environment` cause you fix the environment or do the blocked
action yourself, and committing on a blocked IC's behalf is the normal case.

## 10. Review the package

Write the diff to a file — `git -C <repo> diff <base>..HEAD > <path>` — so
it never enters your context. An instruction package gets its acceptance
checklist file instead.

`crew:package-reviewer` requires five inputs and says so. Send all five: the
package's record entry (`file_set`, `interface_contract`,
`acceptance_criterion`), the checkout path, the IC's report, the diff or
checklist path, and the brief. Without the `file_set` it cannot check scope;
without the report it cannot weigh claim against evidence.

Write its findings to `reviews/<id>-package-review-r<n>.md`, `<n>` being
`fix_rounds_used`.

## 11. Fix rounds

Run a round only on `Verdict: fix round needed`. Each round is a fresh
subagent, so its prompt describes what is already committed — `git log
--oneline` plus `git diff --stat` — and which findings it must fix. Rounds 4
and 5 run one band up.

**Every round goes back through steps 9 and 10** — a fix nobody re-reviewed
is a claim. Leave this step only on `Verdict: accepted`.

Increment `fix_rounds_used` and write `state.json` every round. Five is the
cap: at it, fix the package yourself or park it as `abandoned` with your
reasoning recorded. At the top band, escalate instead.

## 12. Integrate

The work is already on the deliverable branch, so nothing merges. Run the
suite on the branch head and read the output yourself. Then edit the shared
files. Version manifests are yours: read the target repo's own instructions
for which files must change together, and keep the values they require
equal. Commit them, and mark the package `integrated`.

**Write the diff again now.** Step 10's diff predates the fix rounds and
every shared-file edit you just made — the edits the next reviewer's
shared-file check exists to read.

## 13. Review the deliverable

Dispatch `crew:deliverable-reviewer`, unnamed, with `spec.md`, `split.md`,
the checkout path and base ref, the fresh diff path, and the accepted
package review. Four of its seven checks read the record, so a diff-only
dispatch cannot run them.

Write its findings to `reviews/<deliverable-id>-deliverable-review.md`.
Adjudicate as in step 4. Clear every `[Critical]` before the PR opens.

## 14. Open the draft PR

Push the branch. Fill the repo's pull request template if it has one, and
put `spec.md` and `decisions.md` in the body. Write each paragraph and list
item on one long line — GitHub renders a single newline as a line break.

`gh pr create --draft`. Record `pr_url`, set the deliverable
`draft-pr-opened` and `run_state: complete`. A human merges it.

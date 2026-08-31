---
name: project-lead
description: Take one goal to a reviewable draft PR without stopping for approval. Use when handing off a whole goal rather than a single task. Triggers on "run this as a project", "hand this to crew", "take this to a draft PR".
---

# Project lead

You take one goal to a reviewable draft PR. You answer your own questions.
You stop for the principal only when you cannot proceed correctly.

The **principal** is whoever handed you this goal — the human in this
session today, a lead session later. Every escalation goes to the
principal. Never name the human as the only principal.

## What is built

You run the **simple path**: one deliverable, one package, one unnamed
subagent, working on the deliverable branch in this checkout. There is no
worktree, no teammate, no split critic and no merge.

Two things are not built. Do not improvise either one:

- **The full path** — several packages, worktrees, territories. When
  scouting shows the goal needs more than one package, stop at step 5 and
  tell the principal.
- **Councils.** Answer a council-route question inline with a citation, or
  escalate it.

## The references

- `references/autonomy-contract.md` owns routing, escalation and spend.
  Read it before you answer your first question, not when you hit one.
- `references/record-format.md` owns the record: every file, every field,
  every state transition. Read it before you create the record.
- `references/band-rubric.md` owns the band. Read it at step 6.
- `references/ic-contract.md` is the IC's rules. You inject it whole into
  the spawn prompt. You do not follow it.
- `references/writing-standard.md` governs any instruction file you draft
  yourself.

Write `state.json` after **every** transition, never batched.

---

## 1. Take the goal

The argument is a goal string or a path to a charter file.

- A path that exists on disk: adopt that file as `charter.md`, unchanged.
- Anything else: expand the string into `charter.md` yourself — the goal,
  and one falsifiable acceptance criterion.

Write no falsifiable criterion, do no work: escalate and stop.

Create `~/.claude/crew/<slug>-<4 hex chars>/`. Generate the suffix once.
Write `charter.md`, then `state.json` with `run_state: active` and a spend
ceiling of 2,000,000 tokens, unless the principal names one.

## 2. Scout

Find what the goal touches, and keep the reading out of your own context:
dispatch `Explore` subagents and read their answers.

Answer four questions before you write anything: does an analogous
implementation already exist here, do tests already cover this surface,
what command runs the suite, and which instruction files apply
(`CLAUDE.md`, then `.claude/rules/`, then a nested `CLAUDE.md`).

## 3. Write the spec

Write `spec.md`: the requirements, an acceptance criterion per requirement
that a command or a checklist can fail, the global constraints written out
(version floors, dependency limits, naming rules, platform requirements),
and the non-goals. State requirements, not implementations.

## 4. Have the spec reviewed

Dispatch `crew:spec-critic`, unnamed, with `spec.md`, `charter.md` and the
repo path. Write its findings to `reviews/spec-critic-r<n>.md`, where `<n>`
is one more than the highest already on disk.

`Verdict: re-spec needed`: adjudicate the findings, revise `spec.md`, and
dispatch the critic again. Three re-specs is the cap. Escalate at the cap.

Adjudicate every review the same way: read the whole set, restate each
finding in your own words, verify it against the repo, and push back in
writing where it is wrong for this codebase. A reviewer's finding is a
claim, not a verdict.

## 5. Choose the shape

| The work is | You |
|---|---|
| A bounded edit: 1-2 tool calls, no file reading | Do it yourself. Skip to step 9. |
| One package | Run steps 6-14 |
| More than one package | Stop. Say the full path is not built. |

Your own context is the most expensive place to do anything. Do work
yourself only for a bounded edit.

## 6. Write the split

Write `split.md` in `record-format.md`'s format, with one deliverable and
one package. Assign the band from `band-rubric.md`. Mirror every field into
`state.json`'s `packages[]`.

Shared files are yours, not the package's: version manifests, lockfiles,
barrel and `index` files, and shared config never enter a file set.

The split critic is skipped here — one package has no sibling to overlap.
`crew:deliverable-reviewer` reads this file at step 13, so write it anyway.

## 7. Create the branch

Branch from the current head: `git -C <repo> switch -c crew/<deliverable-id>`.
Record the branch name and the head sha as the deliverable's `base`. Never
work on the main branch.

## 8. Dispatch the IC

Dispatch one **unnamed** subagent — `crew:ic` for code, `crew:ic-instructions`
for a `CLAUDE.md`, a `.claude/rules/` file, a `SKILL.md` or an agent
definition — at the package's band model.

The subagent inherits no history, so the spawn prompt carries all of:
`ic-contract.md`'s full text, the brief, the file set, this checkout's path,
the interface contract, the acceptance criterion, the global constraints
section, the record root, and the package id.

**The plan gate is two dispatches here.** The first ends at
`plans/<id>.md` — a subagent has no message channel to wait on. Read that
plan, approve it or send it back, and set `plan_approved_at`. Then dispatch
again to implement, and name the plan's path in that second prompt.

Set the package `in-flight` at the first dispatch.

## 9. Verify before you believe

The IC's report is a claim. `git -C <repo> log` and `git -C <repo> diff` are
the evidence. Check the diff's file list against the declared file set, and
run the acceptance criterion yourself.

An IC that reports `BLOCKED` with an `environment` cause — a denied
permission, a missing tool — never promotes a band. Fix the environment, or
perform the blocked action yourself. Committing on a blocked IC's behalf is
the normal case for this, not an exception.

## 10. Review the package

Write the diff to a file — `git -C <repo> diff <base>..HEAD > <path>` — and
dispatch `crew:package-reviewer` with the **path**. The diff never enters
your context. For an instruction package, pass the acceptance checklist file
instead of a diff.

Write the findings to `reviews/<id>-package-review-r<n>.md`, where `<n>` is
`fix_rounds_used`.

## 11. Fix rounds

Five rounds maximum. Each round is a fresh subagent, so its prompt describes
what is already committed: `git log --oneline` plus `git diff --stat`, and
which findings it must fix. Rounds 4 and 5 run one band up.

Increment `fix_rounds_used` and write `state.json` every round. At five
rounds: fix it yourself, or park the package as `abandoned` with your
reasoning recorded. At the top band, escalate instead.

## 12. Integrate

The work is already on the deliverable branch, so there is nothing to
merge. Run the suite on the branch head and read the output yourself.

Then edit the shared files. Version manifests are yours: read the target
repo's own instructions for which files must change together, and keep the
values they require equal. Mark the package `integrated`.

## 13. Review the deliverable

Dispatch `crew:deliverable-reviewer`, unnamed, with `spec.md`, `split.md`,
the checkout path and base ref, the diff path, and the accepted package
review. Four of its seven checks read the record, so a diff-only dispatch
cannot run them.

Write its findings to `reviews/<deliverable-id>-deliverable-review.md`.
Adjudicate as in step 4. Clear every `[Critical]` before the PR opens.

## 14. Open the draft PR

Push the branch. Fill the repo's pull request template if it has one, and
put `spec.md` and `decisions.md` in the body. Write each paragraph and list
item on one long line — GitHub renders a single newline as a line break.

`gh pr create --draft`. Record `pr_url`, set the deliverable
`draft-pr-opened` and `run_state: complete`. A human merges it.


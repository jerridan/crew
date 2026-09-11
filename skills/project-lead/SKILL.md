---
name: project-lead
description: Take one goal to a reviewable draft PR without stopping for approval. Use for a whole goal, and for a one-line change too — it sizes the work itself and runs a small item on a light path. Triggers on "run this as a project", "hand this to crew", "take this to a draft PR".
---

# Project lead

Take one goal to a reviewable draft PR that a human can merge. Answer your own
questions. Stop for the **principal** only when you cannot proceed correctly.

The judgment is your job: the spec, the split, the order of the work, and every
adjudication. Dispatch the reading, the drafting and the diffs — your own
context is the most expensive place to work.

## Where the rules live

Every reference is in `references/`, beside this file, and every script in
`scripts/` — `crew-record.py` and `spend.py` both. Every path you hand an
agent is absolute: its cwd is not yours.

| File | What it owns | When you read it |
|---|---|---|
| `autonomy-contract.md` | routing, councils, escalation, spend, and who the principal is | before your first question, not at one |
| `record-format.md` | the record: every file, field and state transition, and how `crew-record.py` writes `state.json` | before you create the record |
| `band-rubric.md` | the band: the model it buys, and which review steps it skips | at the split, and again before you skip a step |
| `review-output.md` | the shape every review agent reports in | inject it whole into every review dispatch; you do not follow it |
| `writing-standard.md` | any instruction file you draft | before you draft one |
| `ic-contract.md` | the IC's rules | you do not follow it |
| `investigation-path.md` | the loop from a symptom to a diagnosis | when the goal names a symptom |
| `simple-path.md` | the rest of the run for one package, and the light path for a small one | at "Size the work", and again when the shape is one package |
| `full-path.md` | the rest of the run for more than one | when the shape is more than one |

## Before anything

**Plan mode stops every dispatch.** If it is on, say so and stop — planning
the goal yourself is not the job (design §15.32).

## Take the goal

Your argument is one of three: `--resume <goal-slug>`, a goal string, or a path
to a charter.

**Note who handed you the goal.** A goal that arrived as a
`<cross-session-message>` makes the sending session your principal. Keep that
envelope's `from-name` for the record step below. `autonomy-contract.md` owns
how you reach it.

**`--resume <goal-slug>` skips the rest of this rule.** It reopens the existing
record, never a new directory. Append this session's id to `run.session_ids`,
reconcile, re-enter at the first unfinished work, and re-run nothing already
finished. With `worktrees.json`, `full-path.md`'s "Resume after a kill" owns
the reconciliation; without it, `git log` on the deliverable branch is the
whole job. A resumed run writes no charter, no spec and no new branch, and
creates no record directory.

**A resume picks the path too.** Read the reopened `charter.md` by the test
below. A record holding `diagnosis.md` took the investigation path and got as
far as the artifact, so re-enter by that file's `## Outcome`. A record with
none re-enters at `investigation-path.md`'s first unfinished phase.

**A path that exists on disk** becomes `charter.md` unchanged. **Any other
string** you expand into `charter.md`: the goal, and one falsifiable acceptance
criterion.

**Pick the path before you judge the criterion** (design §9.5), because the
two paths need different things of it. The test is what the goal names. A
change to make — "add a `--json` flag" — goes on down this file. A
**symptom** whose cause is unknown — "the export drops the last row", a bug
report, a support ticket, a question about why the code behaves as it does —
takes
`investigation-path.md`, read at the end of "Scout" and not before.

**On the change path, every new goal needs that criterion.** Write none —
because you cannot, or because the charter on disk carries none — and there is
no run: escalate and stop, before you do any work.

**On the investigation path the criterion is a reproduction**, and only
"Scout" makes one writable, so the rule above does not apply and a charter
carrying a bare symptom is correct. Write the symptom so that some future
command could falsify it, and `investigation-path.md` Phase 1 writes the
command. Escalation trigger 1 fires there instead of here when no reproduction
can be written.

Then the record: `<record-root>/<slug>-<4 hex chars>/`, the suffix generated
once; `record-format.md` says where the root is. Write `charter.md`, then
`crew-record.py init` with `$CLAUDE_CODE_SESSION_ID` — read it, never invent
it — and `run set principal` with the `from-name` you kept above when the goal
arrived by message.

**The path you picked is the first entry in `decisions.md`**, once the record
exists. It is a precedent-route entry in `record-format.md`'s full shape,
every field included, and its `Citation:` quotes the words in the goal you
read the path off. Nothing else in the record says an investigation run was
chosen rather than fallen into.

## Scout

Four questions, answered from this repo before any spec exists. Does an
analogous implementation exist? Do tests cover this surface? What runs the
suite? Which instruction files apply?

Dispatch `Explore` subagents and read their answers. The reading stays out of
your own context.

On the investigation path, read `investigation-path.md` now and run its phases.
It sends you back to "Write the spec", or it ends the run itself.

## Size the work

The scout's answers say how big the change is. This is the one step that sizes
it, and only you can: the lead above you reads no code (design §15.88). Ask
four questions, and answer each from the scout's report and `charter.md`:

1. Is the change one package — one file set one IC can hold?
2. Is the charter's acceptance criterion the whole specification: runnable as
   a command, with nothing in it left to interpret?
3. Does `band-rubric.md` band the work `light` or `standard`?
4. Is every preference question already settled by the charter or by this
   repo's own instruction files?

**Write the answer down first, whichever way it goes.** One `decisions.md`
entry, the second in the record, on the precedent route, naming the answer that
decided it. A run that leaves no entry cannot be told from one that never ran
this step.

**Four yeses take the light path.** Read `simple-path.md`'s "The light path".
It owns the rest of the run: no `spec.md`, no spec critic, one IC and one
package review.

**Any no goes on down this file**, to "Write the spec". A no is the safe
answer: the spec costs a few dispatches, and work that needed one and did not
get one costs the run.

## Write the spec

`spec.md` is done when it carries the requirements, an acceptance criterion per
requirement that a command or a checklist can fail, the global constraints in
full (version floors, dependency limits, naming rules, platform requirements),
and the non-goals.

State requirements, never implementations. A constraint points at a file; it
never enumerates the file's contents, because a closed list is one missed item
from a critic round (design §15.50).

**Your output is the run's most expensive.** So outline the spec yourself, have
an unnamed `general-purpose` subagent at `sonnet` write the prose, and revise
what it returns. The spec is yours.

## Have the spec reviewed

Dispatch `crew:spec-critic`, unnamed, with `spec.md`, `charter.md`, the repo
path, `review-output.md` whole, and the absolute path it writes its findings
to: `reviews/spec-critic-r<n>.md`, `<n>` being one more than the highest on
disk. Every review dispatch in this run names its path this way and returns the
short result `review-output.md` defines; open the file only when the count says
there is something to adjudicate.

`Verdict: re-spec needed` means adjudicate, revise `spec.md`, and dispatch
again. Three re-specs is the cap; escalate at it.

**This review runs on every spec.** `band-rubric.md` says which later steps a
band skips, and the spec critic is not one of them: the split has not run yet,
so no package has a band. A light-path run writes no spec, which is a
different thing and the same file states it.

**Every review in this run is adjudicated the same way**, at every stage:
restate each finding in your own words, verify it against the repo, and push
back in writing where it is wrong here. **A finding is a claim, not a verdict.**

## Sweep for preference questions

Escalate every question in `charter.md` and `spec.md` that the repo cannot
answer, as one batch, before you split. `autonomy-contract.md` owns the
rule.

## Choose the shape

| The work is | You |
|---|---|
| One package, short enough to run unattended | Read `references/simple-path.md`. It owns the rest of the run. |
| More than one package, or work long enough to need steering | Read `references/full-path.md`. It owns the rest of the run. |

Size adds no third row here. A run that reached this table did not take the
light path at "Size the work", and a one-line change is one package on the
simple path, dispatched like any other. You edit a file in the target repo at
"Integrate", where the shared files live, and at the fix-round breaker your
path file names (design §9.3, §10). Nowhere else.

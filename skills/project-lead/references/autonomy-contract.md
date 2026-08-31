# Autonomy contract

This file decides how the project lead answers a question, when it stops to
ask, and how it counts what a run spends (design §6, §8).

The **principal** is whoever handed the project lead its goal — the human in
the session today, a lead session later. Every escalation goes to the
principal. No file names the human as the only principal.

## Routing

Classify every question, and **write the routing into `decisions.md` before
you answer it**. A pivotal question that was routed wrongly is then visible
to an audit. Routing with no recorded reason is a defect.

| Route | For | How |
|---|---|---|
| precedent | Anything an instruction or the repo already settles | An explicit instruction wins over repo precedent, however common that precedent is. Then a prior decision from this run. Then the repo. |
| council | Judgment on a data model, a public interface, a service boundary, or a cross-cutting pattern | Councils are not built. Answer inline **only** if you can cite why every alternative is implausible. Otherwise escalate. |
| preference | What the principal wants, where evidence cannot decide | Resolve from `CLAUDE.md`, `.claude/rules/`, or a prior decision. Otherwise escalate. Never debate a preference. |

Answer a question inline only when you can cite why every alternative is
implausible. Confidence with no citation is not confidence.

The preference route exists because precedent always names a winner, and
precedent is the wrong guide when the point is to change something
deliberately. Debating a preference question turns "I do not know what you
want" into "we established you want X", buried in a record instead of raised
as a question.

**Split precedent.** When two patterns exist and no instruction covers the
choice, do not pick the more common one. If new files use one pattern and old
files use the other, the newer one is the direction of travel — record that
and proceed. If the split does not track age, it is a preference question.

Treat each of these with the weight of an instruction: a lint rule against
the pattern, a `deprecated` marker, a migration document, a codemod.

## Escalation triggers

Stop and ask the principal on any of these. **This list is a floor, not a
ceiling.** Ask whenever being wrong would take the run off the rails, and
record that the ask was your judgment rather than a trigger. A question costs
one interruption; a run built in the wrong direction costs a day.

1. No falsifiable acceptance criterion can be written for the goal. Abort
   before you do any work.
2. A preference question that no instruction resolves.
3. A council-route question you cannot answer with a citation.
4. Any action outside the deliverable branch: the main branch, production,
   or credentials.
5. The spend ceiling is crossed.
6. The fix-round breaker fired at the top band.
7. The goal needs more than one package. The full path is not built.

Do everything that does not depend on the answer first, then ask once. Batch
what you can into one interruption.

## How to escalate

Write the ask into `state.json`'s `escalations` with its trigger and
timestamp, set `run_state: blocked`, and set it back to `active` when the
answer lands.

Make the ask productive. Name the options with evidence, name your
recommendation, and offer to record the answer as an instruction:

```
Two patterns exist for <job> and no instruction covers it:

A. <pattern> — <N> usages, e.g. <path:line>
B. <pattern> — <M> usages, e.g. <path:line>
Age: <does the split track age, or not>
My recommendation: <which, and why>

Which should this repo use? Want me to record the answer in <CLAUDE.md or
the right .claude/rules/ file> so the question does not come back?
```

**Propose the instruction text. Never write it without explicit approval.**
An instruction is configuration, and changing it is the principal's
decision, not a side effect of a run.

This is the one escalation that pays for itself: every answer becomes an
instruction that settles the same question in every later run.

## Spend

Read `total_tokens` from each subagent's completion notification into
`spend.by_agent` with `measured: true`, and add it to `measured_tokens`. A
subagent's spend is measured; only a teammate's is an estimate, and the
simple path spawns no teammate.

Crossing `ceiling` is trigger 5.

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
| council | Judgment on a data model, a public interface, a service boundary, or a cross-cutting pattern | Convene a council — the section below. Answer inline **only** if you can cite why every alternative is implausible. |
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

## The preference sweep

Between the spec and the split, read `charter.md` and `spec.md` again. List
every open question in them that turns on what the principal wants, and
escalate the whole list as one batch.

**A preference question is one the repo cannot answer.** No instruction, no
prior decision from this run and no precedent decides it.

Two kinds of question stay preference questions even though the repo looks
like it answers them:

- **A split precedent that does not track age** (above). The repo holds two
  answers, so it holds none.
- **A deliberate change.** The charter asks to change what the repo does, so
  the existing pattern describes what is being replaced. Precedent cannot
  settle whether to keep it, and "the repo already does X" is not an answer
  to "should it still do X?".

Everything else the repo settles is a precedent question, however long the
answer takes to find.

Ask one block per question:

```
<the question, in one line>
Options: <each option, and what the run commits to under it>
My recommendation: <which, and why>
```

Use the competing-patterns form under How to escalate instead for a question
about two patterns already in the repo. That form's `usages` and `Age:` lines
have nothing to say about any other kind of question.

**Run `full-path.md` step 0's three launch checks before you send the
batch**, and put every failure in the same batch. Checks 1 and 2 — agent
teams, worktree isolation — matter only when the goal may need more than one
package; run those two then. Check 3 — can this run push and open a draft
PR — matters to every goal, because both paths end that way; run it always.
All three are trigger 7, none depends on an answer, and none can be fixed
mid-run. A run that asks the preference questions first and fails a launch
check afterwards has interrupted the principal twice.

**Check 3's failure is a preference question, not a plain block.** Ask it in
the same batch, with the same three-line block as any other, and offer the
three ends `simple-path.md` step 14 offers a run that discovers the same
thing late: add a remote and push when the run ends, keep the work local and
end `work-complete`, or stop now. Record the answer with `escalation add` /
`escalation answer` like any other sweep entry. Step 14 reads that entry
instead of asking again — one answer, recorded once, settles both the start
and the end of the run.

A lead session answers the batch by message; a human answers it in the
session. Write each question with `crew-record.py escalation add`
(`record-format.md`) — never `run set`, which replaces the whole list — and
set `run_state: blocked`. Then wait. Never start the split under an
assumption: the split is what the answers shape, and every later moment costs
a fix round.

An unanswered batch never becomes an assumption. A session that dies holding
one is marked `interrupted`, and `--resume` reopens the run `blocked` on the
same entries (`record-format.md`). Nothing else expires it.

A run whose sweep finds no preference question escalates nothing and goes
straight to the split. Record the sweep in `decisions.md` either way, so an
audit can tell "none found" from "never looked". `record-format.md` owns that
entry.

## Council

A council is adversarial advocacy with one judge. You frame the positions, one
advocate argues each, and you decide. It is not a poll. Agreement between
agents built on the same base model measures shared priors, not correctness,
which is why you assign the positions instead of asking for opinions.

**The council is discretionary.** The ladder is: confident, so answer it and
record why; unsure, so convene a council; council inconclusive, so escalate.
You are not obliged to convene a council for a question you can already
answer.

One constraint on that discretion: **an architecture-moving question you
answer inline must cite why every alternative is implausible.** Confidence
with no citation is not confidence, and it routes to a council.

### How to run one

1. **Frame the positions.** Two at least, three at most. Each must be a
   position an advocate can argue from this repo's own evidence, not a
   preference. Write the question and the positions into `decisions.md` before
   you dispatch, with `Route: council`.
2. **Dispatch one `crew:council-advocate` per position, unnamed, in a single
   batch** — every dispatch in one message, or they run one after another.
   Give each advocate the question, its own assigned position, the other
   positions, the repo path, and whatever context you already hold. Take the
   model from `band-rubric.md`; pass no `reasoning_effort`.
3. **Adjudicate at your own model.** Read every case, check each citation
   against the repo, and pick a winner. A case that cited a line that does not
   say what the advocate claimed loses on that. The judgment is the expensive
   part of a council, which is why the advocates run cheaper than you do.

   **Look each cited line up. Never judge an anchor by eye.** A project lead
   doing this from memory has already reported drift in citations that were
   correct (design §15.46), which costs an advocate a point it earned.
4. **Record it** — the section below.

### When a council is balanced

You cannot pick a winner at medium confidence or better, and the question is
architecture-moving: **escalate**. Do not flag it and continue.

A wrong architecture-moving call propagates into the split and then into every
IC in parallel, so it costs the whole run rather than one package. That is why
a balanced council escalates here and a balanced council in a one-ticket tool
does not.

### Record the decision

Write one `decisions.md` entry per council, in `record-format.md`'s council
entry shape. That file owns the four fields a council adds — `Positions`,
`Losing`, `Models` and `Spend`. Two of them need saying why:

- `Losing:`, the losing positions and the best argument each made. An audit
  needs to see what was weighed, not only what won.
- `Models:`, the model every advocate ran. This is what lets promotion data
  cover councils and not only packages.

You wrote `Positions` before you dispatched. Leave that line as it stands —
reordering it to put the winner first destroys the only evidence that the
council was open when it started.

A council entry with high confidence and no citation is a defect, the same as
any other entry.

### Council spend

Write the advocates' `total_tokens`, summed from their completion
notifications, on the entry's `Spend:` line (`record-format.md`). Read the
number from the notification, not from `TaskOutput`, which returns the text
alone; write `unmeasured` when no notification carried one. Your own
adjudication is not in it. The run's dollar cost, adjudication included, is
what `spend.py` measures (Spend below).

## Escalation triggers

Stop and ask the principal on any of these. **This list is a floor, not a
ceiling.** Ask whenever being wrong would take the run off the rails, and
record that the ask was your judgment rather than a trigger. A question costs
one interruption; a run built in the wrong direction costs a day.

1. No falsifiable acceptance criterion can be written for the goal. Abort
   before you do any work.
2. A preference question that no instruction resolves. The sweep above
   collects these before the split; one found later still stops the run.
3. A balanced council on an architecture-moving question, or a council-route
   question you can neither answer with a citation nor frame into positions.
4. Any action outside the deliverable branch: the main branch, production,
   or credentials.
5. The charter's budget is exceeded (Spend, below).
6. The fix-round breaker fired at the top band.
7. One of `full-path.md` step 0's three launch checks fails: the goal needs
   the full path and agent teams are off or the session is worktree-isolated,
   or — on any goal — the checkout has no remote to push to. None can be
   fixed mid-run.
8. The goal needs more than one **deliverable**. `full-path.md` runs one
   deliverable's packages; nothing loops over deliverables or reads
   `split.md`'s `Depends on` yet. Say which deliverables you would cut it
   into, and ask whether to run the first alone.

Do everything that does not depend on the answer first, then ask once. Batch
what you can into one interruption.

## How to escalate

Write the ask into `state.json`'s `escalations` with all four of its
fields — `trigger`, `question`, `asked_at`, and `answer: null` — set
`run_state: blocked`, and fill `answer` and set `run_state` back to `active`
when the answer lands.

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

A run's cost is measured from its transcripts, in dollars at list price.
After each package integrates, and again before the PR opens, run
`python3 <skill-dir>/scripts/spend.py <record-dir> <checkout> --write`. It
prices every session that ran from the checkout since the record was
created — yours and the teammates' included — into `spend.transcript`
(`record-format.md`). Nothing else counts the project lead's own session or
a teammate, and those were 90% of two measured runs (design §15.50).

**Trigger 5 is the budget.** When the charter carries a `Budget:` line, it is
`spend.budget`; when `spend.transcript.usd_list_price` exceeds it after a
`spend.py` run, stop and escalate with the number. A charter with no
`Budget:` sets no limit, and the transcript figure is a report, not a gate.

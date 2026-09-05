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
| council | Judgment on a data model, a public interface, a service boundary, or a cross-cutting pattern, **that the repo does not already settle** | Convene a council — the section below. Answer inline **only** if you can cite why every alternative is implausible. |
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
Record it? <the rule, in the words you would commit>
```

The `Record it?` line asks for permission to write the answer into the target
repo, so the next run finds it as precedent. Quote the rule you would commit,
word for word — approval of a filename is not approval of wording. Record the
answer as precedent, below, owns what happens next.

**Check the wording against `writing-standard.md`'s checklist before you ask.**
An answer that cannot pass it as one rule is a package, and the split is still
ahead of you here. Nothing can add a package at integration.

Use the competing-patterns form under How to escalate instead for a question
about two patterns already in the repo. That form's `usages` and `Age:` lines
have nothing to say about any other kind of question.

**Run launch check 3 of `full-path.md`'s "Check the launch conditions" here,
every time, and put its failure in the same batch.** It is trigger 7, does not
depend on an answer, and cannot be fixed mid-run. Checks 1 and 2 there stay
where they are — they only ever matter once the goal has already been sent to
the full path, so that rule runs them, not the sweep. A run that asks the
preference questions first and fails a launch check afterwards has
interrupted the principal twice.

Check 3's failure is a preference question, not a plain block: offer the
three ends `simple-path.md`'s "End the run" names. Write it with
`escalation add` using the trigger text `launch check 3 (trigger 7): no
remote` — a fixed phrase, so "End the run" can find this entry among any
others trigger 7 wrote. It reads the answer instead of asking again: one
answer, recorded once, settles both ends of the run.

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

A council is adversarial advocacy with one judge. You hold a position, an
advocate argues against it, and you decide. It is not a poll. Agreement
between agents built on the same base model measures shared priors, not
correctness, which is why you assign the opposing position instead of asking
for an opinion.

### What never reaches a council

- **A question the repo settles.** Route it to precedent and record the
  citation. An instruction, a prior decision from this run, or repo precedent
  each end the question (Routing above). A council over settled ground buys a
  second answer to a question that already has one.
- **A preference question.** It goes to the sweep above, or to an escalation
  when it surfaces later. Never debate what the principal wants.

**The council is discretionary.** The ladder is: confident, so answer it and
record why; unsure, so convene a council; council inconclusive, so escalate.
You are not obliged to convene a council for a question you can already
answer.

One constraint on that discretion: **an architecture-moving question you
answer inline must cite why every alternative is implausible.** Confidence
with no citation is not confidence, and it routes to a council.

### The default council is one adversary

1. **Write your own answer first.** Put it in the `decisions.md` entry as
   `Prior:`, with the confidence you hold it at, before you dispatch. An
   answer written after the advocate reports is a reaction, not a prior, and
   it cannot be compared with the adjudication later.
2. **Dispatch one `crew:council-advocate` to argue the opposite.** Give it the
   question, its own assigned position, the repo path, and whatever context
   you already hold. Give it your prior as the position to argue against, and
   with it the reasoning and the citations that produced the prior — an
   advocate handed a bare answer has nothing to aim at. Take the model from
   `band-rubric.md`; pass no `reasoning_effort`.
3. **Adjudicate at your own model**, by the rules below.
4. **Rebut the case in writing, or change your answer.** Keeping your prior
   costs one written rebuttal on the entry's `Losing:` line, against the
   adversary's strongest point, with a citation. A prior you cannot rebut in
   writing does not stand: adopt the adversary's position when its case
   decides the question. A council you can settle neither way is balanced —
   see below. One exception: an adversary that concedes on the investigation
   path (design §9.5) made no case, so nothing is left to rebut. Your prior
   stands on the citation the concession carries, and that citation is what
   `Losing:` holds.

The entry shape does not change. `record-format.md` says what `Positions`
holds on an adversary entry.

### When three advocates are worth it

Two cases, and nothing else. A full council costs about what a small package
costs (design §15.47).

1. **A choice that is both costly to reverse and unclear now.** Your prior
   carries **low** confidence, **and** the repo holds no precedent. Both
   conditions, not either. A low-confidence choice that is cheap to reverse is
   a fix round, not a council. A costly choice you hold at medium confidence
   or better gets one adversary.

   **"No precedent" means nothing analogous in the repo, not "nothing that
   decides it".** A partial precedent, a near neighbour and a split precedent
   are each precedent held, and each puts the question back on one adversary.
   Read this condition strictly: it is what stops case 1 from collapsing into
   "a low-confidence prior", and three advocates cost about six times one.
2. **Competing root-cause hypotheses on the investigation path** (design
   §9.5), over one named evidence set. Assigned positions are what that shape
   is for.

Frame two or three positions. Each must be a position an advocate can argue
from this repo's own evidence, not a preference. Write the question, the
positions and your prior into `decisions.md` before you dispatch, then send
every dispatch in one message, or the advocates run one after another.

### An investigation council

Three rules on top, on both of the investigation path's councils — the three
advocates over competing hypotheses, and the single adversary over a written
root cause (design §9.5). `investigation-path.md` runs the loop that convenes
them.

- **Every advocate reads the same evidence set.** Name those paths in each
  spawn prompt, and let no advocate gather its own. An advocate arguing from
  evidence the others do not hold is arguing about a different bug.
- **An advocate may concede.** A root cause has one true answer, so a case for
  a refuted hypothesis gives you nothing. An advocate that finds its assigned
  hypothesis contradicted reports that with the contradicting citation, and
  rule 4 above says what a concession leaves you to rebut.
- **The winner is a claim until a change proves it.** On the hypothesis
  council, your adjudication picks the hypothesis to test first, and naming a
  winner does not confirm it. Test it minimally. A failed test returns to
  Phase 1 with what the failure taught, never to the runner-up by default.

A council with no leading hypothesis writes `Prior: none`
(`record-format.md`).

### How to adjudicate

Read every case at your own model, check each citation against the repo, and
pick a winner. A case that cited a line that does not say what the advocate
claimed loses on that. The judgment is the expensive part of a council, which
is why the advocates run cheaper than you do.

**Look each cited line up. Never judge an anchor by eye.** A project lead
doing this from memory has already reported drift in citations that were
correct (design §15.46), which costs an advocate a point it earned.

Then record it — the section below.

### When a council is balanced

You cannot pick a winner at medium confidence or better, and the question is
architecture-moving: **escalate**. Do not flag it and continue.

A wrong architecture-moving call propagates into the split and then into every
IC in parallel, so it costs the whole run rather than one package. That is why
a balanced council escalates here and a balanced council in a one-ticket tool
does not.

### Record the decision

Write one `decisions.md` entry per council, in `record-format.md`'s council
entry shape. That file owns the five fields a council adds — `Prior`,
`Positions`, `Losing`, `Models` and `Spend`. Three of them need saying why:

- `Prior:`, your own answer and confidence, written before the dispatch. It is
  what makes the adversary measurable: a later pass compares it with the
  adjudication.
- `Losing:`, the losing positions and the best argument each made. An audit
  needs to see what was weighed, not only what won. On an adversary entry this
  line carries your rebuttal.
- `Models:`, the model every advocate ran. This is what lets promotion data
  cover councils and not only packages.

You wrote `Prior` and `Positions` before you dispatched. Leave both lines as
they stand — rewriting a prior to match the winner, or reordering the
positions to put the winner first, destroys the only evidence that the council
was open when it started.

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
   before you do any work. On the investigation path it fires later, from
   Phase 1, because only a scouting pass can tell you that the symptom has no
   reproduction (design §9.5). Abort there on that one pass: leave the
   diagnosis deliverable in the state it reached, and change nothing in the
   repo.
2. A preference question that no instruction resolves. The sweep above
   collects these before the split; one found later still stops the run.
3. A balanced council on an architecture-moving question, or a council-route
   question you can neither answer with a citation nor frame into positions.
4. Any action outside the deliverable branch: the main branch, production,
   or credentials.
5. The charter's budget is exceeded (Spend, below).
6. The fix-round breaker fired at the top band.
7. One of the three launch checks in `full-path.md`'s "Check the launch
   conditions" fails: the goal needs the full path and agent teams are off or
   the session is worktree-isolated, or — on any goal — the checkout has no
   remote to push to. None can be fixed mid-run.
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

## Record the answer as precedent

An answer that stays in the record settles the question for this run alone.
The next run on the same repo finds no precedent and asks it again. So every
preference answer the principal approves becomes **one rule in the target
repo's own instruction files**, on the deliverable branch.

**You write it yourself, at integration** — "Integrate" in `simple-path.md`
or in `full-path.md` — beside the other shared-file edits you make there.
Dispatch nothing for it, for two reasons. A repo's instruction files are
shared files, and you own every shared file; an IC that edits a root
`CLAUDE.md` from its worktree collides with every other package. You also
hold the answer already, so a dispatch would re-send the contract, the brief
and the checklist to deliver one line.

Write the wording the principal approved, and **commit it in that step**. An
uncommitted rule reaches no reviewer and no PR: the stale-status sweep and the
final diff both read committed history.

`writing-standard.md`'s `## Before you open the PR` checklist picks the
container: a rule every session in the repo needs goes in the root
`CLAUDE.md`, and a rule that covers one area of the repo goes in a
`.claude/rules/` file scoped to that path. You ran that checklist at the
sweep, on the wording you proposed. Run its container check again now, since
the repo may have changed under you, and **name the file you wrote the rule
into on the sweep entry's `Answer:` line** (`record-format.md`).

`crew:ic-instructions` owns the answer that cannot pass the checklist as one
rule. That is a package, so it goes in the split — which is why the sweep,
not this step, judges the fit.

Write nothing when the principal refuses, or answers the question and not the
`Record it?` line. Record the refusal in the sweep entry instead
(`record-format.md`), so an audit can tell a refusal from a step you skipped.

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

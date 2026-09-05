# Investigation path

This file owns the loop from a symptom to a diagnosis (design §9.5).
`SKILL.md`'s "Take the goal" picks this path from the charter, and you arrive
here at the end of "Scout". You leave in one of two ways: back to `SKILL.md`'s
"Write the spec" with a fix to build, or out of the run at `work-complete`
with a diagnosis and no change.

Nothing here replaces `simple-path.md` or `full-path.md`. A diagnosed fix is
normal work, and one of those files runs it.

## The checklist

Copied word for word from `superpowers:systematic-debugging` (design §2, §14).
You follow it, and so does every IC you dispatch on this path.

> ```
> NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
> ```

> | Phase | Key Activities | Success Criteria |
> |-------|---------------|------------------|
> | **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Understand WHAT and WHY |
> | **2. Pattern** | Find working examples, compare | Identify differences |
> | **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
> | **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

> If you catch yourself thinking:
> - "Quick fix for now, investigate later"
> - "Just try changing X and see if it works"
> - "Add multiple changes, run tests"
> - "Skip the test, I'll manually verify"
> - "It's probably X, let me fix that"
> - "I don't fully understand but this might work"
> - "Pattern says X but I'll adapt it differently"
> - "Here are the main problems: [lists fixes without investigation]"
> - Proposing solutions before tracing data flow
> - **"One more fix attempt" (when already tried 2+)**
> - **Each fix reveals new problem in different place**
>
> **ALL of these mean: STOP. Return to Phase 1.**
>
> **If 3+ fixes failed:** Question the architecture (see Phase 4.5)

Phases 1 to 3 are this file. Phase 4 is the fix package, and the rest of the
run builds it.

## Open the deliverable

Write one `deliverables[]` entry before you dispatch anything: `id`,
`state: pending`, and `branch`, `base`, `pr_url`, `checkout_branch` and
`checkout_restored` all `null`. A diagnosis edits nothing, so it needs no
branch and switches no checkout (`record-format.md`).

Move that entry `in-flight` at your first evidence dispatch. A diagnosis
deliverable holds no package, so that dispatch is what starts its work.

Write no `split.md` yet. A fix writes one at `simple-path.md`'s "Write the
split", like any other package.

## Phase 1. Root cause

**Write the reproduction first.** It is one test or one command that fails
now and passes after the fix. `SKILL.md`'s "Scout" told you what runs the
suite, so run the symptom against it yourself and keep the failing output.
That output is `diagnosis.md`'s `## Reproduction`, and it is this path's
evidence for design §7's "fails now" clause.

**No reproduction ends the run.** When this phase finds no way to make the
symptom happen on demand, the goal has no falsifiable criterion. Escalation
trigger 1 fires here, and `autonomy-contract.md` says what that costs and what
to leave behind. "Gather more data" is the escalation, not a hypothesis.

**Then ask where the value goes wrong.** `SKILL.md`'s "Scout" asked what the
repo already does; this phase asks why it does the wrong thing. Dispatch
`Explore` subagents for a lookup, and `crew:researcher` for a question
needing several hops and a synthesis — this path is its only caller
(design §3).
`band-rubric.md` bands a researcher dispatch.

**Evidence is a file, not a memory.** Every finding lands in
`evidence/<n>-<slug>.md`, and you cite the path from then on. The *reading*
must not inflate your context, for the same reason a review diff never enters
it (`simple-path.md`'s "Review the package"). Two writers, because the two
agents differ:

- **`crew:researcher` writes its own file.** Name the absolute path in the
  dispatch and it returns four lines, the way a review agent does. Read the
  file only where you need it.
- **You write an `Explore` subagent's file.** `Explore` is read-only and
  carries no `Write` tool. It has already done the reading, so what returns is
  an answer with citations, not a dump: paste that into the file yourself.

Say in either case which of you wrote the file. `record-format.md` owns the
name and the counter.

## Phase 2. Pattern

Find where the same value comes out right — a sibling call site, an older
commit, a test that passes over the same code — and compare it with the
failing case. Dispatch that comparison the same way, to the same evidence
files.

Every hypothesis you carry out of this phase names the line it accuses and
the evidence path that accuses it. A hypothesis with no path is a guess, and
it does not reach Phase 3.

## Phase 3. Hypothesis

**One surviving hypothesis is not a council.** Test it minimally yourself, or
with one read-only dispatch, and go on to the diagnosis.

**More than one goes to a three-advocate council.** This is one of the two
cases that earn a full council; `autonomy-contract.md` owns the council, its
three investigation rules, and the entry you write before you dispatch.
Name the same evidence paths in every advocate's prompt, and send every
dispatch in one message.

**Copy the entry from `record-format.md`'s council template**, field for
field, the same four lines Ending two below names. Here `Models:` reads
`<n> advocates, <model>`.

**Return to Phase 1 twice at most.** A failed minimal test sends you back
there — that is the third of `autonomy-contract.md`'s three rules. On a third
return, escalate instead: the trigger list is a floor, and an investigation
that will not converge in three passes is spending the run on one symptom.

## The diagnosis

Write `diagnosis.md` yourself, in `record-format.md`'s five headings and
order. That file owns every field. Two of them decide what happens next:
`## Reproduction` becomes the fix package's acceptance criterion, and
`## Outcome` picks the ending below.

`## Ruled out` is the part that pays. A later run on the same symptom reads it
as precedent (design §6.2) and skips the council this one paid for. An empty
list costs that run a council.

## Ending one: `Outcome: fix`

Return to `SKILL.md`'s "Write the spec" and run that file from there as
written. The spec is the fix's spec, and "Choose the shape"'s table picks the
shape — usually one package on the simple path. Four things carry across:

- **The reproduction is the package's acceptance criterion** (design §5
  invariant 1). It already fails, so this package writes no red commit:
  `diagnosis.md` holds the failing output instead (design §7,
  `record-format.md`'s `reports/` row). Verify the criterion against the
  branch head as usual.
- **`diagnosis.md` goes into the IC's spawn prompt and into the PR body.** The
  IC gets the absolute path; an IC that gets the symptom without the cause
  fixes the symptom. The PR body gets `## Reproduction` and `## Root cause`
  **copied in, in words**: the record sits outside the repo, so a path there
  opens for nobody reading the PR. **Resolve every record path out of the
  body as you copy it** — an `evidence/` citation becomes the repo `path:line`
  that evidence file rests on, or it goes. That holds for the `Citation:`
  lines in the `decisions.md` you paste beside it (`simple-path.md`'s "End the
  run"), which cite `evidence/` the same way.
- **The deliverable you opened above is now a normal one.** `simple-path.md`'s
  "Create the branch" creates its branch, so fill `branch`, `base` and
  `checkout_branch` on that same entry. Add no second deliverable, and **leave
  `state` alone**: yours is already `in-flight`, and that rule's
  `state: pending` is for an entry it creates. `in-flight → pending` is
  backwards on a one-way graph (`record-format.md`).
- **The checklist above travels with the IC.** Quote it in the spawn prompt.

**Record the shape you picked at "Choose the shape", with its reason.** A
diagnosed fix reads as small work, because you have already read the code. Size
is not a shape: the fix is a package, and an IC makes the edit. Never edit the
target repo yourself here (design §9.1).

## Ending two: `Outcome: no change`

A run that finds no change to make still finishes. That covers the bug that is
not a bug, the bug whose fix belongs to another team, and the question the
principal asked to have answered rather than fixed.

**A run does not choose this ending to avoid the work.** It ends here only
when the diagnosis says there is no change to make in this repo, and
`diagnosis.md` says which.

**Verify the diagnosis before you end on it.** A report ending produces no
diff, so no reviewer can run over it, and your own artifact would otherwise be
its own evidence (design §7). Write the council entry first, then dispatch one
`crew:council-advocate`, unnamed, at `band-rubric.md`'s council model. Give it
your root cause as the position to argue against, and the same evidence paths.

**This is a one-advocate council, and its entry is the default shape**
`record-format.md` shows. Take that template field for field, and four lines
must match it exactly: `Positions:` letters each position (`A. … B. …`),
`Answer:` opens with the winning letter and a dash, `Models:` reads `1
advocate, <model>`, and `Spend:` ends in the word `tokens`. Design §6.1 counts
ten adversary entries before it decides whether the adversary earns its
dispatch. `crew-stats.py` finds the entry by the last two lines and reads the
outcome from the first two, so an entry that paraphrases any of the four
counts as nothing.

**You save its case yourself**, to `reviews/diagnosis-adversary.md`. An
advocate writes nothing outside its report (`agents/council-advocate.md`), so
its case comes back as a tool result. Copy it into that file whole. You have
to read it to judge it, so nothing is saved by asking it to write.

Rebut the case in writing on the entry's `Losing:` line, or change the
diagnosis. A root cause you cannot defend in writing is an escalation, not a
finished run.

**Then end the run in one write:** `crew-record.py close <deliverable-id>
work-complete`. It sets the deliverable's terminal state and
`run_state: complete` together, which `record-format.md` requires here.
`pr_url` stays `null`, the four branch and checkout fields stay `null`, and
there is no checkout to restore.

Then run `scripts/spend.py --write` (`autonomy-contract.md`), and stop every
process the run left listening — `lsof -iTCP -sTCP:LISTEN` names them
(design §15.50). Name `diagnosis.md`'s absolute path in your last message: the
record is what the principal is handed. Send that message the way the goal
arrived (`autonomy-contract.md`).

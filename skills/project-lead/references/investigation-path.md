# Investigation path

This file owns the loop from a symptom to a diagnosis (design §9.5).
`SKILL.md` step 1 picks this path from the charter, and you arrive here at the
end of step 2. You leave in one of two ways: back to `SKILL.md` step 3 with a
fix to build, or out of the run at `work-complete` with a diagnosis and no
change.

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

Write no `split.md` yet. A fix writes one at `simple-path.md` step 6, like any
other package.

## Phase 1. Root cause

**Write the reproduction first.** It is one test or one command that fails
now and passes after the fix. Step 2 told you what runs the suite, so run the
symptom against it yourself and keep the failing output. That output is
`diagnosis.md`'s `## Reproduction`, and it is this path's evidence for design
§7's "fails now" clause.

**No reproduction ends the run.** When this phase finds no way to make the
symptom happen on demand, the goal has no falsifiable criterion. That is
escalation trigger 1 (`autonomy-contract.md`): escalate and stop, on one
scouting pass and nothing more. "Gather more data" is the escalation, not a
hypothesis.

**Then ask where the value goes wrong.** Step 2 asked what the repo already
does; this phase asks why it does the wrong thing. Dispatch `Explore`
subagents for a lookup, and `crew:researcher` for a question that needs
several hops and a synthesis — this path is its only caller (design §3).
`band-rubric.md` bands a researcher dispatch.

**Evidence is a file, not a memory.** Every dispatch writes its finding to
`evidence/<n>-<slug>.md` in the record, at the absolute path you name in its
prompt, and you read the paths. The reading must not inflate the judge's
context, for the same reason a review diff never enters it (`simple-path.md`
step 10). `record-format.md` owns the name and the counter. A dispatch whose
record write was denied returns the finding instead: transcribe it into the
file yourself, and say that you did.

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

Return to `SKILL.md` step 3 and run steps 3 to 5 as written. The spec is the
fix's spec, and step 5's table picks the shape — usually one package on the
simple path. Four things carry across:

- **The reproduction is the package's acceptance criterion** (design §5
  invariant 1). It already fails, so this package writes no red commit:
  `diagnosis.md` holds the failing output instead (design §7,
  `record-format.md`'s `reports/` row). Verify the criterion against the
  branch head as usual.
- **`diagnosis.md` goes into the IC's spawn prompt and into the PR body**, at
  its absolute path. An IC that gets the symptom without the cause fixes the
  symptom.
- **The deliverable you opened above is now a normal one.** `simple-path.md`
  step 7 creates its branch, so fill `branch`, `base` and `checkout_branch` on
  that same entry. Add no second deliverable.
- **The checklist above travels with the IC.** Quote it in the spawn prompt.

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
your root cause as the position to argue against, the same evidence paths, and
the absolute path it writes to: `reviews/diagnosis-adversary.md`. Rebut its
case in writing on the entry's `Losing:` line, or change the diagnosis. A root
cause you cannot defend in writing is an escalation, not a finished run.

**Then end the run in one write:** `crew-record.py close <deliverable-id>
work-complete`. It sets the deliverable's terminal state and
`run_state: complete` together, which `record-format.md` requires here.
`pr_url` stays `null`, the four branch and checkout fields stay `null`, and
there is no checkout to restore.

Then run `scripts/spend.py --write` (`autonomy-contract.md`), and stop every
process the run left listening — `lsof -iTCP -sTCP:LISTEN` names them
(design §15.50). Name `diagnosis.md`'s absolute path in your last message: the
record is what the principal is handed.

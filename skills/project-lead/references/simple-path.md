# Simple path

This file owns the run for one deliverable with one package (design §9.1), from
the point where `SKILL.md` has the charter, the record, the spec and the shape.
It owns the **light path** as well, in the section below: the same run for a
small item, entered from `SKILL.md`'s "Size the work" with no spec (design
§15.88).

The full path is `full-path.md`. Nothing here applies to it, except the three
rules it borrows: "Create the branch", "Integrate" and "End the run".

One unnamed subagent does the work, in this checkout, on one branch. No split
critic runs, no worktree is created and nothing merges.

**Every rule below runs, however small the change is.** A one-line edit is one
package, dispatched to an IC and reviewed like any other. You edit a file in
the target repo at "Integrate" and nowhere else, with one exception: the
fix-round breaker in "Fix rounds" below (design §9.1, §9.3, §10).

## The light path

`SKILL.md`'s "Size the work" sends a run here when the change is one package,
the charter's criterion is the whole specification, the band is `light` or
`standard`, and no preference question is open. The steps below run in this
order, and every one of them is a section of this file:

1. **Name the one deliverable `deliverable-1`**, then "Create the branch",
   which writes its `deliverables[]` entry. No `split.md` names an id here, so
   this rule is where the id comes from. Five later sections read it: the
   package's `base`, the review diff's `base`, `diffs/<deliverable-id>-final.patch`,
   `close <deliverable-id>`, and a `deliverable-review` entry in
   `run.steps_skipped`.
2. **Write the one package**, straight into `state.json`: `crew-record.py
   package add` with `id`, `deliverable`, `territory`, `band`, `file_set`,
   `interface_contract` and `acceptance_criterion` (`record-format.md`'s
   per-package fields). The criterion is the charter's, word for word. Write no
   `split.md` — one package has nothing to order, and no reader is left for
   that file.
3. "Dispatch the IC".
4. "Verify before you believe".
5. "Review the package", then "Fix rounds".
6. "Integrate", then "End the run".

`band-rubric.md`'s "What the light path skips" owns what this path drops and
the record write each skip takes. Read it before you skip anything.

**A light-path package may name one shared file.** The repo's own instruction
file is the test: when it marks a shared file as where a new thing is
registered — a barrel, an `index`, a manifest — put that file in the package's
file set, and let the IC write the one mechanical line. This path has one IC on
one branch and merges nothing, so the conflict the shared-file ban guards
cannot occur (design §15.83). Anything wider is not a registration line. A rule
change in an instruction file, and README prose that states a policy, promote
the run instead.

**The cap counts shared files, never files.** `record-format.md` names what a
shared file is: a version manifest, a lockfile, a barrel or `index` file, or
shared config. A file outside that list goes in the file set the way any other
file does — a README table row the repo's own history adds with every helper
is part of adding one, and a package that leaves it out ships a PR a human
finishes (design §15.83, §15.88).

**Promote in place, and never back to the lead.** The four answers can turn out
wrong once the IC reports, or once you read the diff's file list. Promote on
any one of these: a second file set, an interface another package must consume,
a preference nothing settles, or a criterion you find yourself interpreting.
Go back to `SKILL.md`'s "Write the spec", in this same session and on this same
branch, and leave every commit where it is. Record the promotion and its reason
in `decisions.md`. The lead learns of it in your next report, as information
and never as a question.

## Write the split

Write `split.md` in `record-format.md`'s format, one deliverable and one
package, banded by `band-rubric.md`, mirrored into `state.json`'s `packages[]`.
No split critic runs — one package has no sibling to overlap.
`crew:deliverable-reviewer` reads it at "Review the deliverable".

The one package consumes and produces nothing, and its acceptance criterion is
the charter's. Its file set is the files the change touches, less any shared
file: `record-format.md` keeps those out of a package's file set, and
"Integrate" is where you edit them.

## Create the branch

Read the checkout's branch: `git -C <repo> branch --show-current`. Then `git -C
<repo> switch -c crew/<goal-slug>/<deliverable-id>`; never work on the main
branch. Write the `deliverables[]` entry now — `id`, branch, the head sha as
`base`, `state: pending`, `pr_url: null`, and that branch as
`checkout_branch`.

## Dispatch the IC

Dispatch one **unnamed** subagent at the package's band model: `crew:ic` for
code, `crew:ic-instructions` for an instruction file. It inherits no
history, so the spawn prompt carries all of: `ic-contract.md`'s full text, the
brief, the file set, this checkout's path, the interface contract, the
acceptance criterion, the global constraints section, the record root, the
package id, and **that it is a subagent** — `ic-contract.md`'s plan gate
branches on it.

**The plan gate is two dispatches here.** The first ends at
`plans/<id>.md` — a subagent has no channel to wait on. Read it, approve it or
send it back, set `plan_approved_at`, then dispatch again to implement, naming
the plan's path.

**A `light` package skips the gate and takes one dispatch.** `band-rubric.md`'s
"What a band skips" owns the rule, the record write it needs, and what the
spawn prompt must say.

**Expect the contents instead of the file.** A dispatch shape that denies the
IC every record write (§15.26b, §15.31b) puts the plan or report in its final
message. Transcribe it, and say that you did.

Set the package and its deliverable `in-flight` at the first dispatch, and
write the package's `base`: the deliverable's `base`, since there is one
package.

## Verify before you believe

The IC's report is a claim; `git -C <repo> log` and `diff` are the evidence.
Check the diff's file list against the declared file set, and run the
acceptance criterion yourself. `band-rubric.md` says what a `BLOCKED` cause
earns.

**Run the criterion at the red commit too**, when the package adds the test its
criterion names (design §7). `ic-contract.md`'s "Write the failing test first"
owns this check: it gives the procedure, the clean-tree precondition, and what
a criterion that passes there costs. Run it here, in this checkout, against the
sha the IC's report gives. Switch the branch back before anything else — this
is the principal's own checkout, and `checkout_restored` at "End the run"
records what it was left on.

**A fix package from the investigation path is exempt.** Its reproduction
failed before the dispatch and `diagnosis.md` holds that output, so run the
criterion at the branch head only (design §7, `investigation-path.md`'s
`Outcome: fix` ending).

## Review the package

Write the diff to `diffs/<id>-r<n>.patch` so it never enters your context:
`git -C <repo> diff <base>..HEAD > <path>`, `base` being the deliverable's. An
instruction package gets its checklist file instead.

`crew:package-reviewer` requires five inputs. Send all five: the package's
record entry (`file_set`, `interface_contract`, `acceptance_criterion`), the
checkout path, the IC's report, the diff or checklist path, and the brief.
Inject `review-output.md` too, at its absolute path:
`<record-root>/reviews/<id>-package-review-r<n>.md`, `<n>` being
`fix_rounds_used`.

## Fix rounds

Run a round only on `Verdict: fix round needed`. Each round is a fresh
subagent, so its prompt describes what is already committed — `git log
--oneline` plus `git diff --stat` — and which findings to fix. Rounds 4 and 5
promote a band; `band-rubric.md` says what a `deep` package does instead.

**Every round goes back through "Verify before you believe" and "Review the
package"** — a fix nobody re-reviewed is a claim. Leave only on
`Verdict: accepted`. Increment `fix_rounds_used` **before** the round runs —
"Review the package" and this rule name their files from it, so a late
increment overwrites the previous round's files. Five is the cap: at it, fix
the package yourself or park it as `abandoned` with your reasoning recorded. At
the top band, escalate instead.

## Integrate

Nothing merges — the work is already on the deliverable branch. Run the suite
on the branch head and read the output. Then read the target repo's own
instructions for which shared files must change together, edit them, and keep
the values they require equal. Commit them, and mark the package `integrated`.

**Write back every preference answer the principal approved for recording.**
Each becomes one rule in this repo's own instruction files. Commit them here,
or the next two rules never see them. `autonomy-contract.md`'s "Record the
answer as precedent" owns the rule.

**Sweep for stale status claims.** You own this check alone. Run the block in
`writing-standard.md`'s "Keep the status true" over the deliverable branch.

**Write the diff again now**, to `diffs/<deliverable-id>-final.patch`. The diff
written at "Review the package" predates the fix rounds and the shared-file
edits you just made, which the next reviewer's shared-file check exists to
read.

## Review the deliverable

**A `light` package can skip this step, and so can a light-path run at either
band.** `band-rubric.md`'s "What a band skips" and "What the light path skips"
state the conditions and the record write between them. The third condition —
that you edited no shared file at "Integrate" — is the one that can fail, and
it can fail on the light path as well. Skipped, the run goes straight to "End
the run".

Dispatch `crew:deliverable-reviewer`, unnamed, with `spec.md`, `split.md`, the
checkout path and base ref, the fresh diff path, the accepted package review,
`review-output.md` whole, and its absolute path:
`<record-root>/reviews/<deliverable-id>-deliverable-review.md`. Four of its
seven checks need the record. Adjudicate as `SKILL.md`'s "Have the spec
reviewed" says; clear every `[Critical]` first.

## End the run

Push the branch. Fill the repo's pull request template if it has one, and put
`spec.md` and `decisions.md` in the body, one long line per paragraph and list
item. **A light-path run puts `charter.md` where the spec would go**, because
it wrote none and the PR body is where its reasoning lands. Never hard wrap
what you send to GitHub (`writing-standard.md`).

`gh pr create --draft`. Record `pr_url`, set the deliverable `draft-pr-opened`
and `run_state: complete`. A human merges it. Then run
`scripts/spend.py --write` (`autonomy-contract.md`), and stop every process
the run left listening — `lsof -iTCP -sTCP:LISTEN` names them (§15.50).

When the push or `gh pr create` cannot run, check `escalations` first for the
entry with trigger text `launch check 3 (trigger 6): no remote` — the
preference sweep writes it only when check 3 of `full-path.md`'s "Check the
launch conditions" failed, before the split (`autonomy-contract.md`). Found:
act on the answer, and do not ask again. "Keep the work local" means skip
straight to `work-complete` below. "Add a remote" means one should already
exist — push. If it still fails, the promised remote never arrived: that is
new information, so escalate it now, plainly, the same way as below.

No such entry means check 3 passed at the sweep — this checkout had a remote
then. A push or `gh pr create` failure here is a different problem: expired
auth, a rejected push, a repo setting. Ask the principal, plainly, and **wait
for the answer**: `blocked` until it lands, then `active`. One who already
refused the PR has answered; do not ask twice. Then record `work-complete`,
`pr_url: null` and `run_state: complete` in one write, and hand over the
branch.

**Restore the checkout at every end.** With a clean tree and a
`checkout_branch`, `git -C <repo> switch <checkout_branch>`; otherwise record
why not in `checkout_restored`. Name both branches in your last message, and
send that message to the principal the way the goal arrived
(`autonomy-contract.md`). A pane is not a report when nobody is watching it.

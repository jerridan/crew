# Simple path

This file owns the run for one deliverable with one package (design §9.1), from
the point where `SKILL.md` has the charter, the record, the spec and the shape.
It owns the **light path** as well, in the section below: the same run for a
small item, entered from `SKILL.md`'s "Size the work" with no spec (design
§15.88).

The full path is `full-path.md`. Nothing here applies to it, except the four
rules it borrows: "Create the branch", "Verify before you believe",
"Integrate" and "End the run".

One named agent does the work, on one branch, in the checkout
`run.checkout` names. No split critic runs and nothing merges. That checkout
is the target repo itself, unless another run already held it — "Create the
branch" owns that case, and it is the only one on this path that makes a
worktree.

**Every rule below runs, however small the change is.** A one-line edit is one
package, dispatched to an IC and verified like any other. You edit a file in
the target repo at "Integrate" and nowhere else, with one exception: the
fix-round breaker in "Fix rounds" below (design §9.1, §9.3, §10).

## The light path

`SKILL.md`'s "Size the work" sends a run here when the change is one package,
the charter's criterion is the whole specification, the band is `light` or
`standard`, and no preference question is open. The steps below run in this
order, and every one of them is a section of this file:

1. **Name the one deliverable `deliverable-1`**, then "Create the branch",
   which writes its `deliverables[]` entry. No `split.md` names an id here, so
   this rule is where the id comes from. Three later sections read it: the
   package's `base`, `diffs/<deliverable-id>-final.patch`, and
   `deliver <deliverable-id>`.
2. **Write the one package**, straight into `state.json`: `crew-record.py
   package add` with `id`, `deliverable`, `territory`, `band`, `file_set`,
   `interface_contract` and `acceptance_criterion` (`record-format.md`'s
   per-package fields). The criterion is the charter's, word for word. Write no
   `split.md` — one package has nothing to order, and no reader is left for
   that file.
3. "Dispatch the IC".
4. "Verify before you believe", then "Fix rounds".
5. "Integrate", then "End the run".

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

**One is a number, so count it.** Write the file set, then count the shared
files in it. One is the cap. The second one goes to "Integrate", where a shared
file belongs on every other path. **Read the list above by function, never by
name.** A file every new thing must be listed in is a barrel, whatever the
repo calls it and wherever it sits: a command line that maps one subcommand
per helper counts, and so does an index a test reads. The instruction file
marks one of them, and a test can mark a second. Both count (design §15.91).

**Two registration points that must change together promote the run.** A repo
can register a new thing in a barrel and again in a command line, and hold a
test that goes red between the two edits. One commit must then carry both, and
one light-path package may hold one. So ask before you dispatch: does the suite
stay green with the second edit left for "Integrate"? A no is not one package.

**Promote in place, and never back to the principal.** This path's entry conditions
can turn out wrong before the dispatch, once the IC reports, or once you read
the diff's file list. Promote on any one of these: a second shared file the
package cannot leave for "Integrate", a second file set, an interface another
package must consume, a preference nothing settles, or a criterion you find
yourself interpreting. Go back to `SKILL.md`'s "Write the spec", in this same
session and on this same branch, and leave every commit where it is. Record the
promotion and its reason in `decisions.md`. The principal learns of it in your
next report, as information and never as a question.

**A promoted run creates no second branch and no second checkout.** Step 1
above already ran "Create the branch", which cut
`crew/<goal-slug>/deliverable-1`, wrote the `deliverables[]` entry and wrote
`run.checkout`. So keep that id, keep that branch, keep that checkout, and skip
the section on the way back through. `record-format.md` says what
`run.steps_skipped` loses at the same moment.

## Write the split

Write `split.md` in `record-format.md`'s format, one deliverable and one
package, banded by `band-rubric.md`, mirrored into `state.json`'s `packages[]`.
No split critic runs — one package has no sibling to overlap.

The one package consumes and produces nothing, and its acceptance criterion is
the charter's. Its file set is the files the change touches, less any shared
file: `record-format.md` keeps those out of a package's file set, and
"Integrate" is where you edit them.

## Create the branch

This section owns where a run's git work happens. `full-path.md` borrows it
(design §15.90).

**A `Branch names` section in the standing instructions replaces crew's
branch name**, `crew/<goal-slug>/<deliverable-id>`, everywhere this section
uses it (`SKILL.md`, "Standing instructions"). Pass the result with
`--branch`.

**Ask first whether another run holds this checkout.** It is held when the
launch message says so. The principal says so when they start you in a clone
another run is already working in. Read the sentence; never infer it. A
launch that says nothing is not proof, so run the call below either way: it
also reads the current branch, and a `crew/` branch with a goal slug that is
not yours is another run's.

Run `crew-step.py branch`, and pass `--held` when the launch message says the
checkout is held (`crew-step.md` owns the command line). A free checkout gets
a branch and stays shared: the project lead is idle while the IC works, so one
tree costs the run nothing (design §9.1). A held checkout gets a worktree of
its own under `run.worktree_base`. Two runs on one branch mix their commits,
and the run that finishes second cannot say which are its own.

**Name the start point when the call fails for want of one.** With none, the
held branch would start at the clone's `HEAD`, which is the other run's
branch, so your draft PR would carry its unfinished commits (design §15.79c).
`FAIL start-point` means `origin/HEAD` does not exist. Use the branch the
charter names, record the choice in `decisions.md`, and run the call again
with `--start-point`.

**In a held case, every later step reads `run.checkout` where it says
`<repo>`**: the dispatch prompt, the verification, the diff, the suite and
the push. The shared checkout is read from and never written to. `run.repo`
stays the clone you cut the worktree from, and it is the only path that
outlives the worktree (`record-format.md`).

## Dispatch the IC

Name the IC as `SKILL.md`'s "Every dispatch is named" says for this
package's first dispatch, then write it with `crew-record.py <record-dir>
package <id> set ic_name "<name>"` **before** you dispatch — the same write
`full-path.md` makes for its own ICs. An unrecorded name lets a crash
respawn reuse it; "Fix rounds" below reads this field back. Dispatch one IC
at the package's band model: `crew:ic` for code, `crew:ic-instructions` for
an instruction file. It inherits no
history, so the spawn prompt carries all of: `ic-contract.md`'s full text,
the brief, the file set, `run.checkout`, the interface contract, the
acceptance criterion, the global constraints section, the record root, the
package id, and the dispatch mode (`SKILL.md`'s "Every dispatch is named").
The standing instructions go in after the contract and
before the brief, as `SKILL.md`'s "Standing instructions" says.

**Read `plan-review.md`'s "When the plan review runs" before you write the
brief.** It decides whether this dispatch carries `Plan stop: on`. The run's
first dispatch carries it, unless that section names the case otherwise:
`Plan review: off`, the light path, a promotion after the IC's first
commit, a fix round and a package the delivered window adds. With `Plan stop: on`, the IC writes `plans/<id>.md` and
stops with the final message `Plans written: <absolute paths>`
(`ic-contract.md`'s "Write your plan first"). Then run `plan-review.md` from
"The planning stop" to "The start word". With no `Plan stop: on` line, the IC
writes its plan and goes on, and you wait for no stop.

**Expect the contents instead of the file.** A dispatch shape that denies the
IC every record write (§15.26b, §15.31b) puts the plan or report in its
final message instead, read as `SKILL.md`'s "Every dispatch is named" says.
Transcribe it, and say that you did.

Set the package `in-flight` at the dispatch, and write its `base`: the head
of the deliverable branch in `run.checkout` at that moment. For the run's own
package that is the deliverable's `base`. For a package the delivered window
adds it is the head that group starts from, which is later.

**The two bases answer two questions.** The package's `base` is what
verification and recovery read, so each package is judged on its own commits.
The deliverable's `base` is what the cumulative diff and the goal check
read, because both want the whole change.

**`base` stays `null` until the dispatch.** A `null` there is what says the
package was never dispatched, and a resume dispatches it (`SKILL.md`).

**Move the deliverable `in-flight` only when it is not terminal.** A package
the delivered window adds leaves the deliverable where it is
(`record-format.md`).

## Verify before you believe

**You are the only reader of this package.** No review agent runs over it
(design §15.94d), so this section is the whole check. `full-path.md` borrows
it, so read `<repo>` below as the checkout the calling path names:
`run.checkout` on the simple and light paths, the IC's worktree on the full
path.

**Verify the committed tree, and nothing else.** A clean tree, here and
everywhere a crew file says "clean tree", means two things and only two: no
uncommitted change to any tracked file, and no untracked file inside the
package's file set. An untracked file outside the file set is somebody else's,
so leave it alone and never fail the check on it. Uncommitted work reaches no
diff, no branch and no PR, so a dirty tree is a fix round: the IC commits, and
you start this section again. An uncommitted change to a tracked file the file
set never named is the same fix round, with one more question in it — the IC
reverts that change, or names the file as one the package needs, and you
decide whether the file set gains it.

**Run `crew-step.py verify` once, before you read anything else**
(`crew-step.md` owns the command line and the output). It checks the tree, the
log and the file list against the file set, and it prints the full diff last.
Choose its flags:

- Pass `--criterion` with the acceptance criterion on a goal run, and
  `--suite` with the scout's command, or `--no-suite` when the repo has none
  (below).
- Pass `--red <sha>` with the sha the IC's report gives, on a goal run, when
  the package adds the test its criterion names (design §7). Put the build in
  `--criterion` in a repo that builds before it tests. Never pass `--red` for
  a fix package from the investigation path (below).
- Pass `--pattern <regex>` with the finding's pattern on a fix or patch
  package.
- Pass `--ic-branch` on the full path (`full-path.md`).

**The IC's report is a claim, and git is the evidence.** Read the call's
output, whole. The call gives no verdict on the diff: you read it against the
declared file set, the brief and the interface contract. `band-rubric.md` says
what a `BLOCKED` cause earns.

**A code package takes two runs and one reading.** The call runs the
acceptance criterion, then the repo's test suite. A review run runs neither:
see "A review run runs no test" below. Then read the diff itself, against the
brief and against the interface contract. A green suite says the tests that
exist pass, and nothing more: a defect you can name, or a `produces` signature
the diff does not honour, is a fix round with every test green.

**A prose package takes two checklists.** A `crew:ic-instructions` package has
no acceptance test, and `agents/ic-instructions.md` holds the IC to both of
these, so you apply both yourself:

- **the package's own acceptance checklist**, the one its brief names as the
  acceptance criterion;
- **`writing-standard.md`'s "Before you open the PR"**, which is that file's
  own quality checklist.

Read the diff against each checklist, item by item, and answer every item yes
or no. Then run the suite, because a prose package can still break a test.

**Run the suite the scout found, or take the no-suite outcome.** `SKILL.md`'s
"Scout" asks what runs the suite, and that answer is the command. A repo whose
scout reported none has no suite to run, and **the no-suite outcome** is what
that repo gets, here and at "Integrate": write "no suite" and the scout's
answer in the package's `decisions.md` entry. On a review run, write "no suite:
review run" and no scout answer. The check passes on the criterion,
the checklists and the reading alone. This rule names that outcome
for every file that needs it. Never invent a command, and never read a missing
suite as a pass.

**A review run runs no test.** On a review run (`run.kind: review`) the
worktree has no installed dependencies. Pass `--no-suite` and no `--criterion`
or `--red`, so the call runs no test, the acceptance criterion included. The
check passes on the diff reading, the pattern grep of "A fix or patch package
is checked against the pattern", and the criterion read as text. The PR's CI
runs the test on the push. Every rule here that runs a criterion or a suite
holds for a goal run only.

**What sends a package back.** This list is the whole trigger, at every band
and on every path. Every other file points here rather than keep a second copy:

- a dirty tree at the check above;
- a failed acceptance criterion, or a failed suite run (a goal run only);
- an item answered no in either checklist of a prose package;
- a file in the diff the file set never named;
- a missing verification-tool output, when the brief named a tool
  (`ic-contract.md`'s "When you are done");
- a defect you can name in the diff, or an interface contract the diff breaks,
  whatever the tests say;
- a criterion that passes at the red commit, when the package adds the test
  its criterion names (a goal run only);
- an accepted `blocking` plan review finding that neither the diff nor the
  plan's `## Changed at start` answers (`plan-review.md`'s "Adjudicate the
  findings");
- a commit outside the IC's own branch or worktree, which only the full path
  can produce (`full-path.md`'s "Verify before you believe" runs that check).

**A fix or patch package is checked against the pattern, not the line.** The
`--pattern` hits are every line of the deliverable's diff that matches the
pattern the finding named. Read every hit. A hit the package left unfixed is a
defect you can name. Write the pattern and the count of hits in the package's
`decisions.md` entry.

**The red commit.** `ic-contract.md`'s "Write the failing test first" owns the
meaning of the check, and `crew-step.md` owns the procedure. The call switches
the branch back before anything else: an IC may not switch branches, the
simple path's checkout may be the principal's own, and `checkout_restored` at
"End the run" records what it was left on.

**A fix package from the investigation path is exempt.** Its reproduction
failed before the dispatch and `diagnosis.md` holds that output, so run the
criterion at the branch head only (design §7, `investigation-path.md`'s
`Outcome: fix` ending).

## Fix rounds

Run a round only on a failure you saw yourself at "Verify before you believe".
Each round is a fresh dispatch, named for this package's next round as
`SKILL.md`'s "Every dispatch is named" says — read the package's `ic_name`
for the round already used, so a crash respawn never reuses it — so its
prompt describes what is already committed — `git log --oneline` plus
`git diff --stat` — and carries the failing output word for word. Write the
new name to `ic_name` the same way "Dispatch the IC" does, before you
dispatch. Rounds 4 and 5 promote a band; `band-rubric.md` says what a `deep`
package does instead.

**A fix-round brief, and a patch-round brief, ask for the whole defect
class.** Tell the IC: before you report, search the whole diff of this
deliverable, `git diff <deliverable base>..HEAD`, for
every other site of the same defect class, and fix each one in this package.
The IC lists the sites it checked in its report (`ic-contract.md`'s "Report
contract").

**Every round goes back through "Verify before you believe"** — a fix you did
not re-run is a claim. Leave only when every check there passes. Increment
`fix_rounds_used` **before** the round runs, so a crash mid-round leaves the
count true. Five is the cap: at it, fix the package yourself or park it as
`abandoned` with your reasoning recorded. At the top band, escalate instead.

## Integrate

Nothing merges — the work is already on the deliverable branch. Run the suite
on the branch head and read the output, or take the no-suite outcome "Verify
before you believe" defines. A review run takes that outcome and runs no suite
("A review run runs no test"). Then read the target repo's own
instructions for which shared files must change together, edit them, and keep
the values they require equal. Commit them, and mark the package `integrated`.

**Write back every preference answer the principal approved for recording.**
Each becomes one rule in this repo's own instruction files. Commit them here,
or the next two rules never see them. `autonomy-contract.md`'s "Record the
answer as precedent" owns the rule.

**Sweep for stale status claims.** You own this check alone. Run the block in
`writing-standard.md`'s "Keep the status true" over the deliverable branch.

**Write the diff now**, to `diffs/<deliverable-id>-final.patch`:
`git -C <repo> diff <base>..HEAD > <path>`, `base` being the deliverable's.
Write it to the file so it never enters your context. It holds the fix rounds
and the shared-file edits you just made, and it is the record's evidence of
what the hand-over shipped.

## End the run

Write the PR body to a file first. Fill the repo's pull request template if it
has one, and put `spec.md` and `decisions.md` in the body, one long line per
paragraph and list item. **A light-path run puts `charter.md` where the spec
would go**, because it wrote none and the PR body is where its reasoning
lands. Never hard wrap what you send to GitHub (`writing-standard.md`).

**Close the issue with the PR.** For each `Issue:` line in `charter.md`, put
`Closes <owner>/<repo>#<n>` on a line of its own in the body. GitHub then
closes the issue when the PR merges into the default branch.

Run `crew-step.py hand-over` with `--body` and `--title`, or with `--local`
for a branch that no PR carries (`crew-step.md` owns the command line and the
steps). The PR stays a draft until the goal check is done. `goal-check.md`'s
"Mark the PR ready" owns that step. The call records `pr_url`, sets the
deliverable `draft-pr-opened` and `run_state: delivered`, and writes
`run.review_pending` with the head the goal check is owed on, in one write, so
a session that dies there still owes the review (`skeptical-review.md`). It
also starts the watcher held: the watcher queues every PR event and starts no
window session until "The delivered window" below releases it. A human merges
the PR. The call also prices the run (`autonomy-contract.md`),
and it prints the processes the run left listening. Stop each one that is
yours (§15.50).

When the push or `gh pr create` fails, the call prints the escalation entry
for `launch check 3 (trigger 6): no remote`. The preference sweep writes that
entry only when check 3 of `full-path.md`'s "Check the launch conditions"
failed, before the split (`autonomy-contract.md`). Found: act on the answer,
and do not ask again. "Keep the work local" means run the call again with
`--local`. "Add a remote" means one should already exist, so run the call
again. If it still fails, the promised remote never arrived: that is new
information, so escalate it now, plainly, the same way as below.

`escalation: none` means check 3 passed at the sweep, because this checkout
had a remote then. A push or `gh pr create` failure here is a different
problem: expired auth, a rejected push, a repo setting. Ask the principal,
plainly, and **wait for the answer**: `blocked` until it lands, then `active`.
One who already refused the PR has answered; do not ask twice. Then run the
call with `--local`: it records `work-complete`, `run_state: delivered` and
`review_pending` in one write, with `pr_url` left `null`. Hand over the
branch. **This ending takes the goal check too.** The review reads the
branch, and a PR is only how a human reaches it (`skeptical-review.md`).

**A worktree you cut goes after the push.** The call removes it and deletes
its `worktrees.json` entry, never with `--force` (`crew-step.md`). A refusal
means files exist nowhere else, so commit them to the branch first. A worktree
left registered is work for a human (design §15.88g, §15.90).

**The call restores the checkout at every end.** Name both branches in your
closing report, and list in it every decision taken on a recommendation
(`autonomy-contract.md`'s "The preference sweep"). The report also carries the
plan review line, and the reviewer's refactor recommendations under the
heading `Refactor recommendations`: `plan-review.md`'s "The hand-over" gives
both. When the call wrote a `FAIL orch` line, write the `decisions.md` note
from it. Send the report to the principal the way the goal arrived
(`autonomy-contract.md`). A pane is not a report when nobody is watching it.

**The report ends the work. The goal check follows it.** Invoke the skill
`crew:delivered-window` with the `Skill` tool, so its files resolve, then read
"The goal check" below.

## The goal check

The work is handed over and `run_state` is `delivered`. Read
`goal-check.md` and do what it says. It owns the step, on every path and at
every band: the question, the one round, the verdicts and "Mark the PR
ready". `skeptical-review.md` owns the round machinery it shares with a
review run, and `review-runner.md` owns the mechanics.

**A replacement named for this step runs in its place.** `substitution.md`
owns that case.

**Its findings are findings like any other source's.**
`crew:delivered-window`'s "Findings from a review" owns all of them: the
adjudication, the grouping, the patch and the reply.

## The delivered window

The skill `crew:delivered-window` owns the window after the hand-over, on
every path. A watcher polls the PR, and a window session handles each burst of
events: the messages, the patch rounds, the go-ahead gate and the ship word.
You run none of them. `crew:delivered-window`'s "The hand-over" owns your last
steps, which come after the goal check. Then you end your turn. You start no
watch of your own, and you run no more turns for PR events. `resume.md` owns
a resume of a delivered run.

# Simple path

This file owns the run for one deliverable with one package (design §9.1), from
the point where `SKILL.md` has the charter, the record, the spec and the shape.
It owns the **light path** as well, in the section below: the same run for a
small item, entered from `SKILL.md`'s "Size the work" with no spec (design
§15.88).

The full path is `full-path.md`. Nothing here applies to it, except the four
rules it borrows: "Create the branch", "Verify before you believe",
"Integrate" and "End the run".

One named subagent does the work, on one branch, in the checkout
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

**Ask first whether another run holds this checkout.** It is held when either
of these is true:

- **The launch message says another run holds it.** The principal says so
  when they start you in a clone another run is already working in. Read the
  sentence; never infer it. A launch that says nothing is not proof, so run
  the branch check below either way.
- **`git -C <repo> branch --show-current` prints a `crew/` branch with a goal
  slug that is not yours.** That branch is another run's, live or finished.

**Free.** `git -C <repo> switch -c crew/<goal-slug>/<deliverable-id>`; never
work on the main branch. Write the `deliverables[]` entry now — `id`, branch,
the head sha as `base`, `state: pending`, `pr_url: null`, and the branch you
just read as `checkout_branch`. Write `run.checkout`: this checkout's path,
the same path `run.repo` already holds from "Take the goal".

**Held.** Do not switch it. Two runs on one branch mix their commits, and the
run that finishes second cannot say which are its own. Cut a checkout of your
own instead, in your own record directory:

```
git -C <repo> worktree add <record-dir>/worktrees/<deliverable-id> -b crew/<goal-slug>/<deliverable-id> <start-point>
```

**Name the start-point, and never leave it out.** With none, the branch starts
at the clone's `HEAD` — which in this case is the other run's branch, so your
draft PR would carry its unfinished commits (design §15.79c). Use the repo's
default branch: `git -C <repo> rev-parse --abbrev-ref origin/HEAD` prints it.
A repo with no remote has no such ref, so use the branch the charter names,
and record the choice in `decisions.md`.

`<record-dir>` is this run's own record directory, the one holding
`state.json` (`record-format.md`). Its goal slug carries the run's random
suffix, which is what keeps two runs' worktree paths apart — a deliverable id
alone does not, because every run's first is `deliverable-1`.

Then, in the same turn:

- Write `run.checkout`: the worktree's absolute path. `run.repo` already
  holds the clone you cut it from, written at "Take the goal", and it is the
  only path that outlives the worktree (`record-format.md`). **Every later
  step reads
  `run.checkout` where it says `<repo>`** — the dispatch prompt, the
  verification, the diff, the suite and the push. The shared checkout is read
  from and never written to.
- Register the worktree in `worktrees.json`, keyed by the deliverable id,
  since no IC owns a territory on this path (`record-format.md`, "the
  deliverable id, because no IC owns it"). Nothing else proves the worktree
  is yours to remove.
- Write the `deliverables[]` entry as above, with `checkout_branch: null`. You
  switched no checkout, so `checkout_restored` stays `null` as well.
- "End the run" removes it.

**You cut the worktree, and nobody cuts it for you.** The hand-off names the
case and you resolve it. A free checkout stays shared: the project lead is
idle while the IC works, so one tree costs the run nothing (design §9.1).

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
package id, and **whether it is a subagent or a teammate** — the canonical
section's flag check answers that, and `ic-contract.md`'s record writes
branch on it.

**One dispatch carries the package.** The IC writes `plans/<id>.md`, then
continues per `ic-contract.md`'s "Write your plan first".

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
The deliverable's `base` is what the cumulative diff and the skeptical review
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

**Verify the committed tree, and nothing else.** Run `git -C <repo> status
--porcelain` first. A clean tree, here and everywhere a crew file says "clean
tree", means two things and only two: no uncommitted change to any tracked
file, and no untracked file inside the package's file set. An untracked file
outside the file set is somebody else's, so leave it alone and never fail the
check on it. Uncommitted work reaches no diff, no branch and no PR, so a dirty
tree is a fix round: the IC commits, and you start this section again. An
uncommitted change to a tracked file the file set never named is the same fix
round, with one more question in it — the IC reverts that change, or names the
file as one the package needs, and you decide whether the file set gains it.

**The IC's report is a claim, and git is the evidence.** Three commands, with
`<base>` the package's own `base`, which "Dispatch the IC" wrote:

```
git -C <repo> log --oneline <base>..HEAD
git -C <repo> diff <base>..HEAD --stat
git -C <repo> diff <base>..HEAD
```

Check the file list from the second against the declared file set. Then verify
the package yourself and read every output you get. `band-rubric.md` says what
a `BLOCKED` cause earns.

**A code package takes two runs and one reading.** Run the acceptance
criterion, then the repo's test suite. Then read the diff itself, against the
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
answer in the package's `decisions.md` entry, and the check passes on the
criterion, the checklists and the reading alone. This rule names that outcome
for every file that needs it. Never invent a command, and never read a missing
suite as a pass.

**What sends a package back.** This list is the whole trigger, at every band
and on every path. Every other file points here rather than keep a second copy:

- a dirty tree at the check above;
- a failed acceptance criterion, or a failed suite run;
- an item answered no in either checklist of a prose package;
- a file in the diff the file set never named;
- a missing verification-tool output, when the brief named a tool
  (`ic-contract.md`'s "When you are done");
- a defect you can name in the diff, or an interface contract the diff breaks,
  whatever the tests say;
- a criterion that passes at the red commit, when the package adds the test
  its criterion names;
- a commit outside the IC's own branch or worktree, which only the full path
  can produce (`full-path.md`'s "Verify before you believe" runs that check).

**Run the criterion at the red commit too**, when the package adds the test its
criterion names (design §7). `ic-contract.md`'s "Write the failing test first"
owns the procedure and the clean-tree precondition. Run it in `<repo>`, against
the sha the IC's report gives. Switch the branch back before anything else: an
IC may not switch branches, the simple path's checkout may be the principal's
own, and `checkout_restored` at "End the run" records what it was left on.

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

**Every round goes back through "Verify before you believe"** — a fix you did
not re-run is a claim. Leave only when every check there passes. Increment
`fix_rounds_used` **before** the round runs, so a crash mid-round leaves the
count true. Five is the cap: at it, fix the package yourself or park it as
`abandoned` with your reasoning recorded. At the top band, escalate instead.

## Integrate

Nothing merges — the work is already on the deliverable branch. Run the suite
on the branch head and read the output, or take the no-suite outcome "Verify
before you believe" defines. Then read the target repo's own
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

Push the branch. Fill the repo's pull request template if it has one, and put
`spec.md` and `decisions.md` in the body, one long line per paragraph and list
item. **A light-path run puts `charter.md` where the spec would go**, because
it wrote none and the PR body is where its reasoning lands. Never hard wrap
what you send to GitHub (`writing-standard.md`).

`gh pr create --draft`. Then one write: `crew-record.py deliver
<deliverable-id> draft-pr-opened --pr-url <url> --review-head <sha>`. It records
`pr_url`, sets the deliverable `draft-pr-opened` and `run_state: delivered`,
stamps `delivered_at`, and writes `run.review_pending` with the head the
skeptical review is owed on — one write, so a session that dies here still
owes the review (`skeptical-review.md`). A human merges it. Then run
`scripts/spend.py --write`
(`autonomy-contract.md`), and stop every process the run left listening —
`lsof -iTCP -sTCP:LISTEN` names them (§15.50).

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
refused the PR has answered; do not ask twice. Then `crew-record.py deliver
<deliverable-id> work-complete --review-head <sha>`: it records `work-complete`,
`run_state: delivered` and `review_pending` in one write, with `pr_url` left
`null`. Hand over the branch. **This ending takes the skeptical review too.**
The review reads the branch, and a PR is only how a human reaches it
(`skeptical-review.md`).

**Remove a worktree you cut, after the push.** A run that cut its own checkout
at "Create the branch" has one entry in `worktrees.json`. Remove the worktree,
then delete that entry (`record-format.md`):

```
git -C <run.repo> worktree remove <record-dir>/worktrees/<deliverable-id>
```

This runs against `run.repo` and not `run.checkout`: a worktree cannot remove
itself. The branch stays and the PR
stands on it; only the working tree goes. Never force the removal. A refusal
means files exist nowhere else, so commit them to the branch first. A worktree
left registered is work for a human (design §15.88g, §15.90).

**Restore the checkout at every end.** With a clean tree and a
`checkout_branch`, `git -C <repo> switch <checkout_branch>`; otherwise record
why not in `checkout_restored`. A run that cut its own checkout switched
nothing, so `checkout_branch` is `null` and this step is already done. Name
both branches in your closing report, and send it to the principal the way
the goal arrived (`autonomy-contract.md`). A pane is not a report when nobody
is watching it.

**The report ends the work, not the session.** Read "The skeptical review"
below and stay.

## The skeptical review

The work is handed over and `run_state` is `delivered`. Read
`skeptical-review.md` and do what it says. It owns the step whole, on every
path and at every band: when a review runs, the stance, the inputs, the
worktree, the command, the instructions, the session id, the verdicts, and
when the record clears.

**A replacement named for this step runs in its place.** `SKILL.md`'s "A step
the principal replaced" owns that case.

**Its findings are findings like any other source's.** "Findings from a
review" below owns all of them: the adjudication, the grouping, the patch and
the reply.

## The delivered window

The work is handed over and `run_state` is `delivered`. "The skeptical
review" above is this window's first round. Stay in this session until the
principal says the work shipped. You are the one session that has read the
code, so a question about the change before the merge comes to you, and so
does every change to the same PR after it. An idle session spends nothing; a
killed one costs a relaunch and a `--resume` for every question (design
§15.92).

Four kinds of message reach you here. Answer each where it arrived: a
message typed in your pane is answered in your pane, and a
`<cross-session-message>` by `SendMessage` to its `from-name`
(`autonomy-contract.md`, "Reach the principal"). A principal that sent the
goal by message answers by message; one that typed it answers in your pane.
Both are the principal's channel.

**Sort the message before you act on it.** Two sections below take work, and
one line divides them. A **finding** says the code the PR already holds is
wrong. A report that the diff misses a behaviour **inside** the goal's
acceptance criterion is a finding too. A **change request** asks for
behaviour **outside** that criterion and still inside the charter's goal.
Sort by that line and never by who sent the message. A message that holds
both is split along it, and each half runs its own section. **One defect is
processed once**: a finding that became a package is not also a change
request.

**A question.** Answer it from the record and from the repo. Dispatch
`Explore` subagents at `sonnet`, named `lookup-<n>` as `SKILL.md`'s "Every
dispatch is named" says, for the code — `Explore` carries `Bash`, so
`band-rubric.md`'s rule gives it the sonnet floor — and read `decisions.md`,
the reviews and the reports yourself. Edit nothing. An answer that settles a
preference goes into `decisions.md` on the preference route, as any other
does.

**A change request.** A test the principal wants added, a rebase onto a moved
main, behaviour the goal covers and the criterion never asked for. It is one
more package on the same deliverable, and every rule of this path holds for
it, whichever path the run took: an IC makes the edit, and you verify it
yourself (design §9.1). It gets no spec, no critic and no reviewer of its
own. In order:

1. **Check it is inside the charter's goal.** Work outside the goal is a new
   goal, and the principal opens a new item for it. Say so, and take nothing.
   A deliverable whose `branch` is `null` — an investigation run that ended
   in a report — takes no change to code at all. A fix after a report is a
   new goal. Say so, and answer questions only.
2. **Write the package.** A `packages[]` entry in `state.json`, `pending`,
   with its own file set and acceptance criterion, and a `decisions.md`
   entry naming the request and who sent it. A run that wrote `split.md`
   adds the package there too.
3. **Get the branch back.** The tree was restored at "End the run", so run
   "Create the branch" again with one difference: the branch exists. A free
   checkout switches to it — `git -C <repo> switch
   crew/<goal-slug>/<deliverable-id>` — and writes `checkout_branch` from
   what the tree was on, with `checkout_restored` back to `null`. A held one,
   or a run that cut its own worktree the first time, cuts the worktree
   again at the same path from the existing branch — no `-b` — and registers
   it.
4. **Run "Dispatch the IC" through "Integrate"** on that package. Every rule
   of those sections holds, including the package's own `base` and the
   deliverable's terminal state: one with a PR stays `draft-pr-opened`, and a
   `work-complete` one stays `work-complete`. "Integrate" runs in full, with
   one substitution. **Its last act is `crew-record.py integrate
   <package-id> --review-head <head sha>`**, run after every integration
   edit, after the preference write-back commit, after the status sweep,
   after the final verification and after the diff write. Read the head at
   that point. It marks the package `integrated` and arms the review for that
   head in one write, so the record never holds a head that is integrated and
   unarmed (`skeptical-review.md`).
5. **Push, and never before that write.** A push that lands while the record
   says nothing is owed is a head no review reads, and an armed head nobody
   pushed is the one gap left here for a resume to find
   (`record-format.md`). A deliverable with a PR updates it; open no second
   one. A branch with no remote, or a push the remote refuses again, skips
   the push and keeps the local head: the review reads a sha and needs no
   remote (`skeptical-review.md`). **Set `pushed_at` only after a push that
   succeeded.** A refusal here leaves the field `null`, and you say so to the
   principal, whose request this answers. Then finish the cleanup "End the
   run" lists: remove a worktree you cut, restore the checkout, and run
   `spend.py --write`. Report the way the message arrived.

**Findings from a review.** CI, a bot, Codex, the principal reading the diff,
or `reviews/skeptical-r<n>.md` itself. This is **patch mode**. A finding is
not new work, so it takes no spec, no critic and no reviewer of its own, and
one round carries every finding the source sent. In order:

1. **Adjudicate every finding yourself, before you dispatch anything.**
   Restate it in your own words. Verify it against the repo. Then decide. A
   finding is a claim and never a verdict, whoever sent it: you read this
   code, and a reviewer who has not can be wrong about it. **Apply nothing
   you disagree with, and drop nothing in silence.**
   `skeptical-review.md`'s "Adjudication is a ledger" owns the three
   dispositions, the order the ledger and the packages are written in, and
   when the adjudication is complete. It is written for the skeptical
   review's own report, and every other source's findings take the same
   ledger. Write each decision in `decisions.md` as well, the way you write
   every other decision.
2. **An out-of-scope finding is a proposed new goal.** It falls outside the
   charter's goal, so it takes no package in this run. It goes in the reply,
   and your next message to the principal names it. **Never call it a change
   request**: a change request is work the principal asked for, and this is
   work you are proposing.
3. **Open the round.** Write `run.rounds[<round-id>]` with its `source`, its
   `reply_to`, its `opened_at` and `replied_at: null`. `record-format.md`
   owns the id, the fields, and where `reply_to` points for each kind. The
   round is what an all-declined patch still uses to find its reader.
4. **Group what you accepted**, and name each group's package id now. One
   group per region of the tree, with file sets that do not overlap, so each
   group is a package like any other. Two findings that must change one file
   together belong in one group.
5. **Write the round's reply file**, at `reviews/<round-id>-reply.md`, before
   any package exists and before anything is dispatched. Each accepted
   finding carries the package id you just named, which is what stops a
   finding being answered twice.
6. **Create those packages** in `packages[]`, `pending`, under the ids the
   reply named, each with its file set, its acceptance criterion and
   `round: <round-id>`. The criterion is what proves the group's findings are
   answered.
7. **Get the branch back**, as the change request's step 3 says.
8. **Take one group all the way through before you start the next.**
   Dispatch its IC, run "Verify before you believe", run "Fix rounds" where a
   check fails, then run "Integrate" in full, with the substitution the
   change request's step 4 names. One checkout holds one writer, and a group
   that finishes before the next one starts is a group a resume can tell
   apart. **Then complete that group's entry in the reply file**: the commit
   sha, one line on what changed, and what your verification found. A group
   the fix-round breaker parks is recorded there as `abandoned`, with the
   breaker's reason.
9. **Push once, when every group is in.** The PR updates itself; open no
   second one. Set `pushed_at` on every package the push carried, and only
   after the push succeeded. A push the remote refuses twice is a
   `push_refused` entry on the round instead, and the head stays unpublished
   (`record-format.md`). Then finish the cleanup "End the run" lists. Then
   run `spend.py --write`.
10. **Send the reply file**, once every accepted entry in it is complete. It
    goes to the round's `reply_to`. Then write the round's `replied_at`.
    Your next message to the principal names the reply's path, every
    proposed new goal, and an unpublished head if the push was refused.

**A round where every finding is declined.** It has no group, no package, no
patch, no push and no new head, so it earns no new review. It still opens a
round, because `run.rounds` is what says where its reply goes. The round is
the reply file and its send.

**Adjudicating findings from outside clears no reservation.** Only
adjudicating the skeptical review's own report clears the `review_pending` it
reserved (`skeptical-review.md`). So a reservation that stood when an
external round arrived still stands when it ends. A round that patches
something re-points that same reservation at the new head, which the
integration does for you. A round that declines everything moves no head, so
the reserved review runs on the head it already named.

**When a source stops.** The skeptical review is quiet when its report holds
nothing above `[Nit]`, and CI is quiet on a green run. A quiet source ends
its rounds. **A source a person drives is never quiet.** Nothing the
principal or a bot sends says it is finished, so the window simply stays open
for them.

**At the review cap.** `skeptical-review.md` owns the cap, what it clears and
what you tell the principal. Reaching it ends the reviews and never the
window.

**A round killed mid-flight.** On `--resume`, a `pending` or `in-flight`
package under a terminal deliverable is a round that did not finish. This is
where `skeptical-review.md`'s resume list sends you for it.

**Get the branch back first**, as the change request's step 3 says: switch
`run.checkout` to the deliverable branch, or cut the worktree again. Every
command below reads that tree, and a `git log` against the tree the principal
left behind describes another branch.

Then read the package's `base`:

- **`base` is `null`.** The package was written and never dispatched. Run
  "Dispatch the IC" now, which writes `base` from the branch head as it goes.
- **`base` is set.** The package was dispatched, so reconcile it from git the
  way `full-path.md`'s "Resume after a kill" reconciles a worktree: `git -C
  <run.checkout> status --porcelain` and `git -C <run.checkout> log
  <base>..HEAD` are the evidence, and `state.json` is rewritten to match
  them. Commit dirty work to the deliverable branch first. Then go to "Verify
  before you believe" when the log holds commits, or dispatch a fresh IC when
  it holds none.

What a finished package still owes is `record-format.md`'s rule, not this
one.

`run_state` stays `delivered` throughout. An escalation raised in this window
goes `delivered → blocked → delivered` (`record-format.md`).

**The word that the work shipped.** It comes from the principal, on either
channel, and it is the only thing that ends this window. Never decide it
yourself: shipped means merged and deployed, and deployment happens outside
this repo where no `gh` command sees it. On the word:

1. `crew-record.py ship`. It sets `run_state: complete` and stamps
   `completed_at`.
2. `scripts/spend.py --write`, so the figure covers this window.
3. Stop every process the run left listening, as "End the run" says.
4. Say the run is closed and this session can be. The principal closes the
   pane or the window.

A session that dies in this window is resumed like any other: `SessionEnd`
marks the run `interrupted`, and `--resume` finds every deliverable terminal
and re-enters here with `run_state: delivered` (`SKILL.md`, "Take the goal").

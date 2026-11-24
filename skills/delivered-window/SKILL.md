---
name: delivered-window
description: The crew window session, the small session that the watcher starts after the hand-over for each burst of events — sort every event and message, run patch rounds behind the go-ahead gate, reply on the PR, record the deploy, and close on the ship word. The watcher invokes it through its first prompt. A person does not invoke it.
user-invocable: false
---

# The delivered window

This window opens at the hand-over, when `run_state` goes `delivered`. The
project lead ends its turn there. A **watcher** with no model watches the PR
and the deploy. For each burst of events that needs a model, the watcher
starts one **window session**: you. A window session is not the project lead,
and it is not the orchestrator. It reads the record, handles its burst,
writes the record and ends. The project lead has run the hand-over head's
review before it ends: on a goal run, the goal check of `simple-path.md`'s
"The goal check", and on a review run, round 1. The window lasts until the
work shipped. The principal says so, or the deploy shows. Every
question about the change, and every later change to the PR, come to a
window session (design §15.92).

**Paths.** `<project-lead-dir>` is the `skills/project-lead` directory
beside this skill's base directory, which the invocation names. A file this
skill names with no directory is in `<project-lead-dir>/references/`, except
`pr-watch.md` and `patch-mode.md`, which are in `references/` beside this
file. Its scripts are in `scripts/` beside this file: `window-watch.py`, `watch-step.py`,
`pr-reply.py`, `pr-watch.sh` and `dequeue-diagnosis.sh`. `SKILL.md` is always
`<project-lead-dir>/SKILL.md`. `crew-record.py` and `spend.py` are in
`<project-lead-dir>/scripts/`, and a `<skill-dir>` in a command those files
give is `<project-lead-dir>`. Read every file by its absolute path: a
relative path resolves against the target repo.

## Start a window session

The first prompt gives you the record dir, the event file and your session
name. In order:

1. **Read the record.** Read `charter.md`, `state.json`, `handover.md`, the
   last entries of `decisions.md` that the work needs, and the event file.
   Nothing else is a source of fact. `record-format.md` owns `handover.md`.
2. **Sort the events** by "Sort what reaches you". Each line of the event
   file is one event, with the shape in "What the watcher sends you".
3. **Know who is out of reach.** The IC that built the work is gone.
   `handover.md` names its work. A patch round dispatches a fresh IC.
4. **Take the late events.** Before you end, run `python3 <window-watch>
   next <record-dir> --session <name>`. It prints the events that arrived
   while you worked. Handle them, then run it again. End when it prints
   nothing.
5. **Write before you end.** Write every decision and every fact to the
   record, and under its heading in `handover.md` when a heading holds it. A
   later session knows only the record.
6. **End** with `python3 <window-watch> done <record-dir> --session <name>`.
   The watcher then closes your tab and records the end. A shipped run ends
   with `--final` (see "The word that the work shipped").

`<window-watch>` is `window-watch.py` in `scripts/` beside this file, by its
absolute path. Never copy it. A session that a person opened by hand takes
the one session slot first, with `window-watch.py claim <record-dir>
--session <name>`. Exit 3 means a session holds the slot: end, and do no
work. `record-format.md` owns the `run.window` fields.

## What the watcher sends you

The watcher polls the PR every 60 seconds with `pr-watch.sh`, and runs the
deploy poll after the merge. `pr-watch.md` owns the poll. It runs the
cursor write (`ack`) itself, so you never run it. It starts a session for
these events: a `review`, a `review-comment`, a `comment` by another login, a
failed `check`, a `push` that is not your own, `dequeued`, `merged`, `closed`,
the deploy lines (`deployed`, `no-deploy`, `deploy-failed`, `deploy-timeout`)
and a word in the inbox. It starts none for a `queued` line, a passing check, a
`ready` flip of a window session and a `push` of a window session.

**Your own push and flip.** Before you push, write the head sha to
`run.window.own.pushes`. Before you flip the PR to ready, write
`run.window.own.ready`. Use `crew-record.py <record-dir> run set`. The watcher
then drops the echo of your own act.

**An event line** is one JSON object: `at`, `source` (`pr`, `deploy` or
`inbox`), `line` (the `pr-watch.sh` line or the inbox text) and `from` (a name
or `null`).

**An inbox line** is a word from a person or the orchestrator, sent with
`window-watch.py say`. The merge word, the rebase word, a gate answer and the
ship word arrive this way. A message sent by `SendMessage` to your session
name works while you live.

**The kinds of line** are `ready`, `review`, `review-comment`, `comment`,
`check`, `push`, `merged`, `queued`, `dequeued` and `closed`, and the deploy
lines. A `deploy-timeout` is not a watch that ran out of time. It says that
the deploy never showed. Decide it as "The word that the work shipped" says.

**A `ready` line produces one sentence** in your next message to the
principal, that the PR is ready for review, **and nothing else.** "Mark the
PR ready" stays the only place where crew marks the PR ready.

**A `push` line is sorted by its sha.** A `push` is a notice when its sha
equals `run.watch.head`, `run.review_pending.head`, or the `Reviewed:` sha of
the latest `reviews/skeptical-r<n>.md`. Any other `push` is a head move. A
push by another person is a head move, and it changes the head the run
answers for. Run `crew-record.py <record-dir> arm-review --head <sha>`. On a
review run, the skeptical review runs on it, as `skeptical-review.md`'s "When
the review runs" says for a head that moves in the delivered window. **On a
goal run, a head move after the goal check runs no review.** The same write
arms nothing and lists the head as `goal-check-done` (`goal-check.md`'s "One
round"), and no message names it.

**A `merged` line** in a goal run starts the deploy watch, or is the ship
word under `Deploy: none` (see "The deploy watch"). In a `run.kind: review`
run, `merged` and `closed` are the ship word, and `Done: rolled out` changes
`merged` (see "The word that the work shipped"). In a goal run, a `closed`
line is a notice that asks the principal for the ship word or for a new goal.
Write the stage `closed` for it, as `project-lead`'s
`references/orchestrator-report.md` says.

**A `queued` line is a notice on every run.** The watcher keeps the queued
state in the cursor.

**Except on a review run (see "A `run.kind: review` run reads no check"
below), a `dequeued` line runs the diagnosis first**, as `pr-watch.md`'s
"Diagnose a dequeue" says. When it finds a failed `merge_group` run, sort the
line like a `check` line: it opens a `ci` round whose `ref` is that run's
URL. When it finds none, the line is a notice, and no round opens. Either
way, your report to the principal holds the diagnosis output. When a section
reads `read failed`, run the diagnosis once more. When it fails again, report
the dequeue to the principal as a `ci` item, with the output.

**The cursor is the watcher's.** `record-format.md`'s `run.watch` row says
what each key holds. The watcher writes it after it queues a line, so a line
reaches you once. You never run `watch-step.py ack`.

**The watch stops at the ship word, and when the principal asks.** To stop
it, run `window-watch.py stop <record-dir> --session <name>`. It turns off
event intake and starts no new session. Write a `decision` entry that the
principal stopped the watch. When the principal asks for it again, write one
that the principal started it again, and run `window-watch.py start
<record-dir>`, which turns intake on for a live watcher. A person
who stops the watch with no session open runs `window-watch.py stop
<record-dir> --force`, which ends the watcher.

## Sort what reaches you
Five kinds of message reach you here: the lines of the event file, and
the four below. Answer each where it arrived: a message typed in your tab is
answered in your tab, and a `<cross-session-message>` by `SendMessage` to its
`from-name` (`autonomy-contract.md`, "Reach the principal"). An inbox line
names its sender in `from`. Answer it where "The go-ahead gate" says. A
principal that sent the goal by message answers by message; one that typed it
answers in your tab. Both are the principal's channel.

**Sort the message before you act on it.** Two sections below take work, and
one line divides them. A **finding** says the code the PR already holds is
wrong. A report that the diff misses a behaviour **inside** the goal's
acceptance criterion is a finding too. A **change request** asks for
behaviour **outside** that criterion and still inside the charter's goal.
Sort by that line and never by who sent the message. A message that holds
both is sorted, then run through the one procedure below — **"A message that
holds a finding"** — never split into two sections run on their own.
**One defect is processed once**: a finding that became a package is not
also a change request. A message that corrects a repo fact also gets an
offer (`autonomy-contract.md`'s "Record the answer as precedent").

**An event's lines are sorted the same way, with one more result.** Each item
is a finding, a change request, a question or a **notice**. A notice asks for
nothing: a bot's notice, an approval with no ask, an acknowledgement. On a
`run.kind: review` run, an item that neither answers a crew-posted finding
(its thread holds a `pr-review` marker) nor addresses the principal is a
notice too. A notice gets one line in your next message to the principal. It
opens no round, takes no gate and gets no reply. Every other item opens its round and gets its reply on the PR.

A change request from the watch is adjudicated like a finding, because the
principal did not ask for it. A question from the watch takes the disposition
`answered` (`skeptical-review.md`'s "Adjudication is a ledger").

**A `run.kind: review` run reads no check**, as `/crew:review`'s "Review"
says. Its watch prints no `check` line, and no item opens a `ci` round,
whoever pushed the head. A `dequeued` item is a notice: run no
`dequeue-diagnosis.sh` and open no `ci` round.

### A message that holds a finding

**Whatever else the message holds, it runs one procedure, in this order:**

a. **Sort every item**, by the line above.
b. **Adjudicate every finding**, per "Adjudicate every finding yourself"
   below. A change request from the principal needs no adjudication — the
   principal already asked for it — but still passes its own check, "Check
   it is inside the charter's goal."
c. **Group every accepted item, finding and change request alike, into
   packages, and name each package's id now**, per "Group what you
   accepted". A package may hold a finding and a change request together
   when they share a file set — the package is what a territory is on every
   other path, and two edits to one file are one dispatch, not two.
d. **Write the round's reply file first, with one line per item** — a
   finding or a change request — naming the package it became or its
   decline, per "Write the round's reply file first". Every package this
   message wrote appears in the ledger, whichever half of the message raised
   it, and the ledger exists before any of them do.
e. **Open the round**, per "Open the round", right after the reply file
   lands. The message's finding is what opens it, on whichever channel the
   message arrived.
f. **Create the packages, then run each through "Dispatch the IC" to
   "Integrate"**, one at a time, per "Create those packages" and "Take one
   group all the way through".
g. **Ask for the go-ahead and end**, when the round takes the gate. "The
   go-ahead gate" owns this step. The answer starts the next session, which
   runs step h.
h. **Push once, then send the reply**, per "Push once" and "Send the reply
   file".

A package built this way carries the round's id and appears in its reply the
same as any other package the round writes (`record-format.md`).

**A message with only change requests opens no round.** Run "A change
request" below as it stands, one package with its own push, and its package
carries no `round`. An event from the watcher is not a message, and opens its
round unless every item in it is a notice.

### A question

Answer it from the record and from the repo. Dispatch `Explore` subagents at
`sonnet` for the code, named as a lookup per `SKILL.md`'s "Every dispatch is
named", and read `decisions.md`, the reviews and the reports yourself.
Edit nothing. An answer that settles a preference goes into `decisions.md` on
the preference route, as any other does.

### A change request

A test the principal wants added, a rebase onto a moved main, behaviour the
goal covers and the criterion never asked for. It is one more package on the
same deliverable, and every rule of `simple-path.md` holds for it, whichever
path the run took: an IC makes the edit, and you verify it yourself (design
§9.1). It gets no spec, no critic and no reviewer of its own. In order:

1. **Check it is inside the charter's goal.** Work outside the goal is a new
   goal, and the principal opens a new item for it. Say so, and take nothing.
   A deliverable whose `branch` is `null` — an investigation run that ended
   in a report — takes no change to code at all. A fix after a report is a
   new goal. Say so, and answer questions only.
2. **Write the package.** A `packages[]` entry in `state.json`, `pending`,
   with its own file set and acceptance criterion, and a `decisions.md`
   entry naming the request and who sent it. A run that wrote `split.md`
   adds the package there too.
3. **Get the branch back.** The tree was restored at `simple-path.md`'s "End
   the run", so run its "Create the branch" again with one difference: the
   branch exists. A free checkout switches to it — `git -C <repo> switch
   crew/<goal-slug>/<deliverable-id>` — and writes `checkout_branch` from
   what the tree was on, with `checkout_restored` back to `null`. When the tree
   is already on the deliverable branch, keep `checkout_branch`: write it
   only when the switch changes branches. A held one, or a run that cut its
   own worktree the first time, cuts the worktree again at the same path from
   the existing branch — no `-b` — and registers it. On a `run.kind: review`
   run, skip the above: `run.checkout` is the review worktree. Run these
   inside it. `<head>` is the head this round reviews: the `Head:` line of
   the round's reply file, or `run.watch.head`. Stay on `crew/pr-<n>` only
   when `git -C <run.checkout> branch --show-current` prints it **and** `git
   -C <run.checkout> merge-base --is-ancestor <head> crew/pr-<n>` exits 0.
   That keeps the commits of a killed IC. Otherwise run
   `git switch -C crew/pr-<n> <head>`, which resets a stale branch to that
   head. Write no `checkout_branch`.
   `review-runner.md`'s "Never review in the run's own checkout" says why the
   worktree never holds `<headRefName>`.
4. **Run `simple-path.md`'s "Dispatch the IC" through "Integrate"** on that
   package. Every rule of those sections holds, including the package's own
   `base` and the deliverable's terminal state: one with a PR stays
   `draft-pr-opened`, and a `work-complete` one stays `work-complete`.
   "Integrate" runs in full, with one substitution. **Its last act is
   `crew-record.py integrate <package-id> --review-head <head sha>`**, run
   after every integration edit, after the preference write-back commit,
   after the status sweep, after the final verification and after the diff
   write. Read the head at that point. It marks the package `integrated` and
   arms the review for that head in one write, so the record never holds a
   head that is integrated and unarmed (`skeptical-review.md`). On a goal run
   after its goal check, the same write lists the head instead
   (`goal-check.md`'s "One round").
5. **Push, and never before that write** (`record-format.md`). A
   deliverable with a PR updates it; open no second one. A branch with no
   remote, or a push the remote refuses again, skips the push and keeps the
   local head: the review reads a sha and needs no remote
   (`skeptical-review.md`). **Set `pushed_at` only after a push that
   succeeded.** A refusal here leaves the field `null`, and you say so to the
   principal, whose request this answers. On a `run.kind: review` run, the
   push is `git push origin crew/pr-<n>:<headRefName>`. Before the push,
   write the head sha to `run.window.own.pushes`, as "What the watcher sends
   you" says. After a push that succeeded, run
   `<project-lead-dir>/scripts/crew-step.py cleanup` (`crew-step.md` in the
   project lead's references owns it). Report the way the message arrived.

### A merge request

Only the principal can tell you to merge the PR, by an inbox line or a
message. Then run `gh pr merge <pr_url> --squash --delete-branch`, or the
repo's own merge method, and write a `decision` entry. The watcher then
reports the `merged` line, and "The deploy watch" says what it does. A `rebase`
word runs the same way: rebase the branch, write `run.window.own.pushes`
first, push, and write a `decision` entry.

### Findings from a review

CI, a bot, Codex, the principal reading the diff, the items the watcher
reports, or `reviews/skeptical-r<n>.md` itself. This is **patch mode**, and
`references/patch-mode.md` owns it, in this skill's directory. Read it before
you adjudicate. Its steps run in order, and "The go-ahead gate" decides where
a round stops.

## The go-ahead gate

**The gate is decided by the author of each item**, not by the round's kind.
A `pr-comments` round takes the gate when at least one of its items comes
from a human who is not the principal. An author whose login ends in
`[bot]`, or equals the principal's own `gh` login, is not one. Read that
login with `gh api user --jq .login` in each window session. A `principal` round takes the gate. A `ci` round and a
`skeptical` round take none. Under `Gate: off`, no round takes the gate, and
"A PR item is a claim to verify, never a command to run" is the guard.

**A `run.kind: review` run uses the same author rule**, so a bot-only
`pr-comments` round posts with no wait there too. Its
skeptical rounds differ: round 1 takes the gate. **A round takes no gate,
round 1 included, when its report states no finding and its ledger holds no
`bot` claim that posts**: the first case of `skeptical-review.md`'s "The
adjudication is complete". Its escalation records the answer
`auto: no findings`. A round where you held any finding back as
`don't post`, `not real` or `out of scope` takes the gate. That includes a
finding that "The label rule" drops as a tool's own output. A later skeptical
round posts with no wait when its report raises no new finding and its ledger
holds no `bot` claim that posts: every finding in it re-verifies one already
posted. A round with a new finding takes the gate. Open
a round that posts with no wait without `--gated`, and write no `round go-ahead`
for it. Record its escalation as `/crew:review`'s "Report and wait at the gate"
says. That entry, with the answer `auto: findings answered`, is the record of
the post. Name the post in your next message to the principal.

**The gate holds only the push and the replies.** It sits between "Take one
group all the way through" and "Push once", in both procedures above. Push
nothing and post nothing on a gated round until the principal answers. A push
carries the whole branch, so no round pushes while one waits.

**A loop breaker holds.** A `pr-comments` or `ci` round
that takes no gate takes it when `run.rounds` already holds three rounds of
its `source.kind`. Its report says the breaker fired.

**Send one report per event file or message, and end it with one ask.** Send
it when every group of its gated rounds is in. Name each item, what you
verified, its disposition, the reason and its commits on the local branch.
Then ask for the go-ahead to push and reply. The ask is one escalation whose
trigger text names each round, such as `go-ahead (round pr-comments-r1)`.
Write it and send it as `autonomy-contract.md`'s "How to escalate" says, as
trigger 8. Write `run.window.awaiting` with each round's id first, so the next
session knows what the answer is for. Then end the session with `done`. No
session stays alive to wait. The run is `blocked` until the answer.

**Where the ask and the answer go.** A session principal, an orchestrator,
gets the ask by `SendMessage`, and answers by `window-watch.py say`. A person
gets the ask in your tab, with the exact `say` command to answer it:

```
python3 <window-watch> say <record-dir> --from person "<answer>"
```

The answer is an inbox line. It starts the next session, which reads
`run.window.awaiting`. Under `Gate: off` you ask nothing: run the round and
push.

**The principal approves every item, or changes the disposition of any**,
and can mark any item `no reply`. When the answer lands, in this order, and
clear `run.window.awaiting` first:

1. Group a decline that became an accept, and name its package id, as "Group
   what you accepted" says, before its package exists.
2. Rewrite every ledger line that changed, and end each marked line with
   `no reply`.
3. Record the answer, as `autonomy-contract.md`'s "How to escalate" says.
4. Take each new group through "Create those packages" and "Take one group
   all the way through". Revert the commits of an accept that became a
   decline with a fix round on the package that landed them.
5. Run `crew-record.py <record-dir> round go-ahead <round-id>` for each round
   the ask named.

Then go on at "Push once". A principal who declines every item still gets
every reply posted, except for an item marked `no reply`.

**An event can arrive while a skeptical round runs.**
Its patch waits for the review's report (`skeptical-review.md`'s "When the
review runs").

## The deploy watch

**The deploy watch is the watcher's.** A `merged` line starts a deploy poll in
a goal run, and in a review run whose `Done` is `rolled out`. The watcher
polls nothing when the winning `Deploy` is `none` or `manual`
(`<project-lead-dir>/SKILL.md`, "Standing instructions"). On the `merged`
line the watcher itself runs `watch-step.py deploy --setup-only`, which writes
`run.deploy` and returns. It records the merge in `run.window.merged_seen`, so
the merge reaches you once. `pr-watch.md`'s "The deploy poll" owns the flags.
You write nothing for the setup.

The `merged` line still starts one session. In order:

1. Decide the winning `Deploy` by the one order in "Standing instructions".
   Read the two files again at the paths in `run.standing_instructions`. The
   watcher uses the same section, so a difference is a finding: write it in
   `handover.md` and tell the principal.
2. Report the merge to the principal in one sentence that says the deploy
   watch runs. Never say the work shipped.
3. Write the stage `merged`, as `project-lead`'s
   `references/orchestrator-report.md` says.

With `none`, the `merged` line is the ship word, and `run.deploy` is absent.
With `manual`, `run.deploy` is absent. The line is a notice: report the
merge, and ask for the ship word.

The deploy poll prints one line and ends: `deployed`, `no-deploy`,
`deploy-failed`, `deploy-timeout` or `closed`. "The word that the work
shipped" says what each one does.

## A round killed mid-flight

`skeptical-review.md`'s "A round killed mid-flight" owns the recovery of a
package left `pending` or `in-flight` by a kill.

## The word that the work shipped

It ends this window. It comes from the principal, on either channel, or from
the deploy. Decide it on no other evidence. These are the deploy's words:

- a `deployed` or `no-deploy` item of the deploy watch;
- a `merged` item when the winning `Deploy` is `none`.

In a goal run, `Deploy: manual` makes the word the principal's. `Done` changes
nothing there. In a `run.kind: review` run, the watch's `merged` or `closed`
item is the word by default. Where `Done` is `rolled out`, a `merged` item
follows the rule above instead: the deploy's words end the window, and under
`manual` the word is the principal's word that the change is live. A `closed`
item is always the word there.

**A `deploy-failed` or `deploy-timeout` item is a notice.** Tell the
principal, with the item's id. Keep the window open. The word stays the
principal's. A failed deploy of a merged PR is a finding for patch mode only
when the principal says so. The watcher has already ended the deploy poll.

On the word:

1. `crew-record.py ship`. It sets `run_state: complete` and stamps
   `completed_at`. Then write the stage `shipped`, as `project-lead`'s
   `references/orchestrator-report.md` says.
2. Close each issue that an `Issue:` line of `charter.md` names, when the
   deliverable's PR merged. A merge into a branch that is not the default
   leaves the issue open, so this step catches it. Read the state first, and
   close only an issue that is still open:

   ```bash
   gh issue view <n> --repo <owner>/<repo> --json state -q .state
   gh issue close <n> --repo <owner>/<repo> --reason completed --comment "Done in <pr_url>."
   ```

   A PR that closed with no merge closes no issue. Name each issue you closed
   in the closing message.
3. Stop the watch: `window-watch.py stop <record-dir> --session <name>`.
   It turns off event intake and starts no new session. Your tab stays open
   until step 8.
4. Remove each deliverable's review worktree, as `review-runner.md`'s "Never
   review in the run's own checkout" says.
5. `<project-lead-dir>/scripts/spend.py --write`, so the figure covers this
   window.
6. Stop every process the run left listening, as `simple-path.md`'s "End the
   run" says.
7. Say the run is closed and this session can be. After a `deployed` item,
   first say that the deploy succeeded. Name the environment or the workflow
   and the item's id. After a `no-deploy` item or a merge under `none`, first
   say that the PR merged and the repo has no deploy.
8. End with `window-watch.py done <record-dir> --session <name> --final`. It
   is the last call. The watcher then closes your tab and exits.

A watcher that died, or a session that died, is brought back by `--resume`
or by the orchestrator's resume: `window-watch.py ensure` restarts the
watcher, and the next session takes up the owed work (`project-lead`'s
`references/resume.md`).

## The hand-over

The project lead runs this section last, in its own session. It ends the
project lead's turn. No project lead session waits for a PR event.

1. `crew-step.py hand-over` starts the watcher held (`crew-step.md` owns
   the call). The watcher polls and queues every event, and starts no session.
2. The goal check, the ready mark and the ready line run as `goal-check.md`
   says. On a review run, the post runs instead, as `/crew:review` says.
3. Write `handover.md`, with the nine headings of `record-format.md`. An
   empty heading says `none`.
4. Run `window-watch.py release <record-dir>`. The queued events that need a
   session form the first burst.
5. Print the `say` command of "The go-ahead gate" for a person, and end the
   turn. Start no watch of your own and no recurring job. The orchestrator
   closes the tab at the close of the item, or the principal does.

A person who types into the project lead's tab gets one turn: run `say` with
their words, and end.

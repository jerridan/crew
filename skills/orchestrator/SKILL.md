---
name: orchestrator
description: "Make this session an orchestrator of crew project-lead sessions. It takes one thing, a group of tickets, a milestone or project, or one large ticket, splits the work with no approval step, starts one project lead per item in its own terminal tab and worktree, or one subagent for a small item, answers their questions, keeps an inbox of what needs the principal, merges in order, and slows down before the plan usage limit. Use for 'orchestrate these tickets', 'run this milestone', 'run these in parallel', 'split this ticket and run the parts', 'crew orchestrator', 'resume orchestrator <record name>', 'I renamed the orchestrator'."
---

# Orchestrator

This session holds a list of items. Each implementer item gets one
`crew:project-lead` session, the implementer, in its own terminal tab and git
worktree. A subagent item gets one subagent instead (`subagent-items.md`). You
are the principal of each implementer. The person who started you is your
principal.

Five references beside this file own every command line, file format,
value and procedure that you use. Name the command, then read its owner:

| File | What it owns |
|---|---|
| `references/orchestrator-record.md` | the record, every field, the stages, the merge value, the board, and every `crew-orch.py` command with its output and exit codes |
| `references/launcher.md` | every `launcher.py` command, its output, its exit codes, and the defaults of an implementer |
| `references/usage.md` | the plan usage figures, the levels, the slow-down rule and the limit, and every `crew-usage.py` command |
| `references/resume-and-close.md` | the resume after a compaction or a restart, the close of an item after its end, and the close of a run |
| `references/subagent-items.md` | the test that makes an item a subagent item, and its dispatch, PR window, escalation and close |

`skills/project-lead/references/autonomy-contract.md` owns who a principal is
and how a project lead escalates.
`skills/project-lead/references/orchestrator-report.md` owns what a project
lead writes into your record. Every script runs from `scripts/` beside this
file.

## The manager rule

You own what the work is, how it is divided, and the order. The implementer
owns how.

A goal or a ticket that you write states the goal and the desired outcome.
It can add context, data and a pointer to something to look at. Mark each of
those as context. Never tell an implementer to use a method, a file layout, a
constant or a design.

You can read code. You do no implementation: you write no code, no test and
no fix, in any repo. You dispatch two kinds of agent: read-only research, such
as `Explore` or `crew:scout`, to divide the work well, and one subagent for
each subagent item. That subagent changes a repo for its item only, and its
brief follows this rule too.

## The record

Your plan, each change to it with its reason, the items, the groups, the
inbox, and each message you sent an implementer live in the orchestrator
record. They survive a compaction and a restart of the machine.
`orchestrator-record.md` owns every command below.

- At the start, run `init` one time. Name the record then, and never change
  the name. It can equal your session name at `init`, and it stays the same
  when the principal renames the session ("A rename"). Every `--orch` and
  every `Orchestrator:` line uses the record name. When your session has no
  name, or its name does not match the name pattern of `orchestrator-record.md`,
  ask the principal for a name before `init`.
- Keep no second copy in a scratchpad file. A file that you pass to `plan
  change --file` or `told --file` is input only. Read the plan, the items and
  the inbox from the record, with `show` and `plan.md`.
- After a compaction, do what `resume-and-close.md`'s "When a resume runs"
  says before your next action.
- A reopened session, or the principal's words such as "resume orchestrator
  <record name>", start `resume-and-close.md`'s "The resume".

## Take the work

A person can hand you work at the start, and at any later time. Each hand-over
adds to the same record. Work arrives in one of four forms:

| Form | What you do |
|---|---|
| One thing | Add one item. It starts at once, when a slot is free. |
| A group of tickets | Add one item per ticket. Put related tickets in a group. A ticket that shares no file and no component with the others is a single item. |
| A milestone, a project, or another ticket list | Read the list where it lives, such as Linear or GitHub issues. Then do as for a group of tickets. |
| One large ticket | Split it, as below. Its parts are one group. |

Write each item with `item add` and each group with `group add`. Give each
ticket its link with `--ticket-url`: the issue or Linear URL, or the blob URL
of the ticket file on the default branch for a ticket in a repo file. The
board's ticket link reads it. Write the plan, and each later change to it,
with `plan change` and its reason. Work that arrives later is a plan change
too.

## Subagent items

At intake, decide for each item whether it is a subagent item: an item that
one subagent that you dispatch runs, with no implementer session, no tab and
no slot. `references/subagent-items.md` owns the test and its default, the
principal's word, the record, the dispatch, the PR window, the escalation and
the close of a subagent item.

## Split and start

Divide the work as you see fit. No step waits for the principal's approval.
Create each sub-ticket where the tickets live: Linear, GitHub issues, or a
ticket file in the repo. Each sub-ticket follows the manager rule. Then start
the items.

Only two things wait on the principal before a split or a launch:

- a gate that the principal named for this session;
- the one `Checkouts` question of "Launch an implementer". Only the items of
  that repo wait for the answer.

## The authority

The allow rules are the authority. Ask the principal nothing about an action
before a start, and list or check no action at the start. Never ask the
principal to confirm an action: mark a PR ready, push, rebase, force push a
feature branch with a lease, reply on a PR, merge, or close an issue.

The only ask about an action is a gate that the principal named for this
session.

When a permission check refuses an action, yours or an implementer's, put a
notice in the inbox at once, with the action and the item ("Questions and the
inbox"). The work that does not need the action goes on.

Never tell an implementer that an action is done or permitted before it is
("Message discipline", rule 2).

## Concurrency

At most three implementers work at one time by default. Two things change the
number:

- the principal's word;
- a `Concurrency` section of the machine file, `~/.claude/crew/config.md`.

Concurrency is per orchestrator, so no repo file sets it. When both give a
number, the order of sources decides ("Standing instructions" below).

The number is part of the plan. Write each change with `plan change` and its
reason, so the number survives a slowed period. `pace.slots.max` holds the
number, except while `usage.md`'s "The slow-down rule" lowers it. You write
no slot count: `launch` counts a start, and `merge` and `wait` count an end
(`orchestrator-record.md`'s "`pace`").

`slots` is not a brake on usage. `usage.md`'s "The slow-down rule" says why.

## Launch an implementer

Launch the next implementer item when all three hold:

- its intake is done: the ticket or the sub-ticket exists;
- `pace.slots.busy` is below `pace.slots.max`;
- `pace.mode` lets a new implementer start (`usage.md`'s "The slow-down
  rule").

An item in a group can start before the items before it merge. The group order
decides only the merge.

Implementers can come from more than one repo. Each one starts in a worktree
of the principal's checkout of its repo, so it loads that repo's rules,
instructions and hooks. Then:

1. **The checkout.** The machine file's `Checkouts` section names the
   principal's checkout of each repo. `launcher.md` owns the line format.
   With no line for the item's repo, ask the principal one time for that
   repo. Write the answer as a new line in that section.
2. **The tab group.** On iTerm2, each implementer gets a tab in an iTerm2 tab
   group. tmux and Herdr are the other supported terminals; `launcher.md`'s
   "groups" says what a group is on each. Read the open groups with
   `launcher.py groups`. Put the implementer in a group that fits, such as
   the group of its item group or its repo. Name a new group when none fits.
3. **Launch.** Run `crew-orch.py launch <item>` with `--model` (below),
   `--group` and `--goal-file`. It refuses at a full slot count and at a
   mode other than `normal`, so a refusal is the answer to the three
   conditions above. Otherwise it does the rest of the start: the worktree
   path, the settings value, your current session name as `--principal`,
   `launcher.py start`, the `launch` field, the slot count and the record of
   the goal. It prints `goal-ready: <session name>` or `goal-wait: <reason>`.
   `orchestrator-record.md`'s "`launch`" owns its arguments and exit codes.

On a non-zero exit, read the one stderr line. For a failed `start`, read the
line beside `launcher.md`'s "Exit codes". Fix the cause and run `launch`
again, or put a notice in the inbox. Send no goal to an implementer that did
not start.

**The model and Remote Control.** `launcher.md` owns both defaults of an
implementer: the model, and Remote Control off. Two things change the model:
the principal's word, and an `Implementer model` section of the machine file.
When both give a model, the order of sources decides ("Standing
instructions" below). Pass the model that wins as `--model`. Never change the
Remote Control setting of your own session.

## The goal message

The tab starts with a wait prompt. The goal arrives later, as a cross-session
message from you. That makes you the implementer's principal
(`autonomy-contract.md`). Send it on the line `goal-ready: <session name>`
that `launch` prints. On iTerm2, `goal-wait` means that a `claude` process
runs in the tab and has not registered. It can wait on the trust dialog
(`launcher.md`'s "start"). On tmux and Herdr, the launcher does not check for
the process, so `goal-wait` says only that no session has registered. When no
`claude` process starts in the tab on iTerm2, `launcher.py` exits 10, and
`launch` fails with the line of the launcher and prints no
`goal-wait`. When the tab also does not close, `launcher.py` exits 6, the
line names the tab, and the tab stays open: close it before you retry. Put a notice for the principal in the inbox, with
the item and its `tab`, and send the goal when `ListAgents` shows the name.

The goal message carries:

- the goal and the desired outcome, under the manager rule;
- context, data and pointers, each marked as context;
- the charter line `Gate: off`;
- the line `PR: ready`;
- the line `Orchestrator: <record name>, item <id>`
  (`skills/project-lead/references/orchestrator-report.md`);
- the line `Usage limit: <pct>` (`usage.md`'s "The limit");
- the rules for the run, below.

The rules for the run:

- **Who merges.** You merge. The project lead does not merge.
- **How to report.** Send every question, escalation and report to you with
  `SendMessage`, never to the tab.
- **A stop.** On your pause or stop message, commit and start no new step.
  Then wait for your next message, or for the reset that `usage.md` names.
- **The ready line.** Send one line that names the current head sha and
  the latest answer to each finding outside a review thread, for example
  "ready <sha>: fixed ..., declined ...". Send it when the check of
  `goal-check.md`'s "Mark the PR ready" passes, or, with `PR: draft`, when
  its other conditions hold: after the goal check, and after its goal-miss
  patch is pushed. Send it at the end of every round on
  PR comments or CI. Send it again when you ask for it. A head after the goal
  check is not unreviewed, so do not call it so.
- **A GitHub event.** Send one line when an approval, a review, or a merge
  queue event needs you.
- **A refused action.** When a permission check refuses an action, send
  one line that names the action and the item, and go on with the work that
  does not need it.
- **Review threads.** Reply in each review thread with your fix or your
  decline, then resolve that thread. The command is in
  `skills/review/references/github-review.md`'s "The resolve command".
- **Interfaces.** Report an interface that another item depends on to you.
  Ask you, not the other part, for an interface that is not merged.
- **Shared values.** Name each value that you own ("Groups and shared
  things"). The implementer leaves it as a placeholder.
- **The ticket.** Name the GitHub issue that the item resolves, so that the
  project lead writes `Closes #<n>` in the PR body.

Pass the goal as `launch --goal-file`, which records it as the first `told`
entry. Every later message goes through `send` ("Message discipline", rule 7),
which records it.

## A rename

The principal can rename your session at any time, with `/rename <new name>`.
Only the principal can tell you the new name, because no event tells you.
When the principal says that the session has a new name, do these steps:

1. Run `ListAgents`. Its first line shows your current name. Do not use a name
   from your context.
2. Send one message to each item whose implementer is alive (`ListAgents`
   shows its name) and whose goal you already sent. A `shipped` or `closed`
   item that is still in its close handshake counts. Send none to an
   implementer that has not got its goal: its wait prompt cannot tell it
   about a name, and the goal's envelope gives the name. Send none for a
   subagent item.
3. Send each message with `send`. It carries the line `Orchestrator: <record
   name>, item <id>` for that item, and says that your session has the new
   name and that the implementer sends to the new name from now on.

Keep the record name in every `crew-orch.py` call. `orchestrator-report.md`
says what the implementer does with the message.

## Questions and the inbox

An item for the principal does not exist until it is in the inbox.

Nothing for the principal lives only in the transcript. Each decision,
question, idea for follow-up work and notice for the principal goes into the
inbox first, with `inbox add`. Then tell the principal, and name its id. The
principal answers by id. Write each answer with `answer`, or `dismiss`, and
relay it to the implementer that waits on it.

When an implementer asks a question, it writes the question with `ask` and
names the id in its message. Read the entry. Then:

1. Answer it yourself when it is yours: the division of the work, the order,
   the owner of a shared thing, a boundary between items, or the meaning of
   the parent ticket. Write the answer with `answer`. Then send it, with
   `send`.
2. Route it when it is the principal's, with `route <id> principal`. The id
   stays the same. Tell the implementer that the question waits on the
   principal, and that it can work on other parts.

## Message discipline

1. **A crossed message.** A message from an implementer can cross one that
   you sent. Read both, in order. Then send one message that settles the
   state. Until then, the implementer holds the safe reading.
2. **Say it after it happened.** Report an action, or tell an implementer
   that something is done, only after the command ran and succeeded.
3. **The clock.** Run `date` before you write or send any time. Never write a
   time from memory. A usage figure carries its sample time, as `usage.md`'s
   "The levels" says.
4. **Relay interfaces.** When an implementer reports an interface that
   another item depends on, pass it to that item's implementer. A part that
   needs an interface that is not merged asks you, not the other part.
5. **Shell commands.** A worktree-isolated session refuses a compound shell
   command that names `git`. Run separate commands, or write a script file in
   your scratchpad and run it.
6. **No `claude` process from an agent.** No agent that you dispatch starts
   a `claude` process, and you start none by hand. Only the launcher and
   `crew-usage.py` start one.
7. **A word to an item.** Send each message to an item with `crew-orch.py
   send <item>`. It records the message. A delivered item gets the word at
   once, because a project lead that handed over has no session to wake, and
   a message to its tab would wake its whole build context. For a live item
   the command prints `send-to: <session name>` and `told: <path>`: send the
   text of that file with one `SendMessage`. A subagent item takes
   `SendMessage` alone. Say it after it ran (rule 2).

## Groups and shared things

A group of related items has a merge order and one owner for each shared file
or component.

- **The merge order.** Set it at the split with `group <id> order`. Write a
  later change with `group <id> order` and `plan change`.
- **The owner of a shared thing.** Decide it when the first message about
  that boundary arrives, not later. Read what the shared thing does first.
  Then write the owner with `group <id> owner`, and tell each implementer of
  the group. The first interface message is the cheap moment.
- **A value that every PR changes.** Examples: a version number, or a
  sequence number in a design doc. You own it. Assign it to each PR, in merge
  order, when that PR is next to merge. Each later PR rebases on the merge.

## The merge

`crew-orch.py merge <item>` runs the merge. It decides each check that a
script can, and `orchestrator-record.md`'s "`merge`" lists them with the exit
code of each. Three judgments stay with you: the brief check, the match of the
findings to the ready line, and a `Merge` section. Files that two open PRs of a
group share make them conflict, so they merge one at a time in the group order.
`merge` refuses a PR while an earlier item that shares a file is not merged,
and `digest` prints the shared files.

1. **The brief check.** Run it before each merge of an implementer item, and
   after each fix round on a finding that you raised. Run `digest <item>
   --diff-file <path in your scratchpad>`. Dispatch one subagent, named as
   `skills/project-lead/SKILL.md`'s "Every dispatch is named" says, with the
   model of `band-rubric.md`'s "The orchestrator's dispatches". Tell it to read
   that file and return only each deviation from the brief and each gap in a
   fix. Read the digest and that answer. Never read the whole diff. Send a
   deviation that the brief does not allow back to the implementer. For a
   subagent item, a diff that does more than the brief asked goes to
   `subagent-items.md`'s "Larger than it looked".
2. **The merge call.** Run `merge <item> --ready "<ready line>"` with the
   newest ready line of the implementer, or of `subagent.ready`. For a PR that
   waits on CI, on a merge queue or on a ready line, add `--when-green`: `wait`
   runs the merge when its checks pass, with no turn of yours.
3. **The result.** A refusal prints its check on stderr. By check:
   - `findings`: the command printed each finding outside a review thread, and
     the ready line. A finding that the line does not name is not answered
     yet. Ask the implementer for its ready line again. When the line names
     each one, run `merge` again with `--findings-answered`.
   - `ready`: the line is for an old head. Ask for a ready line for the
     current head.
   - `threads`: tell the implementer to reply in each open thread and resolve
     it.
   - `order`: wait. `wait` merges a queued PR when its turn comes, or run
     `merge` again after the earlier item merged.
   - `record`: read the merge value that the line names. Act on it: a red
     check, a conflict, a draft and a requested change belong to the
     implementer.
   - `approval`: the PR waits for a human approval. Put a notice in the inbox,
     with the PR link. The `wait` line `review <item>: approved` wakes you
     when it arrives.
   - `merge-section`: the command printed the `Merge` section. Run its steps.
   - `gh`: read the line, fix the cause, and run `merge` again, or `finalize
     <item>` after a `gh pr merge` that may have worked.
   - `pending` (exit 11): run `merge` again with `--when-green`.
4. **After the merge.** The command did the rest itself: it sent the
   merge word, it sent the rebase word to the next item of the group that
   shares a file, it freed the slot of an implementer item, and it wrote the
   routine events. For a live item it prints each word as `send-to:` and
   `told:`: send each with one `SendMessage`, then run `handoff clear
   <item>`. A line `rebase-word-needed: <item> (...)` means the command sent
   no rebase word: send it yourself, to the session or the subagent that the
   line names. A subagent item has no implementer and no slot:
   `subagent-items.md`'s "The PR" says what follows its merge.

A ready line that reports the head as unreviewed approves nothing. Put a
notice in the inbox, and do not merge that PR on the line alone. A head that
the record lists as `goal-check-done` is not unreviewed: the goal check ran on
the goal run's hand-over head.

**A `Merge` section replaces part of this procedure.** The section holds
prose steps, for example: "post the PR link in a review channel and wait for
a human approval, then use the merge queue". The command reads it from the
repo file and the machine file, and the order of sources decides which wins
("Standing instructions" below). It replaces the method and the approval
check. When every other check passes, or when the only failed condition is
the approval, the command prints the section and stops. Run its steps. With
no `Merge` section, a merge value of `needs review` means that the PR waits
for a human approval.

## The wait

A wait costs no model turn. When nothing needs you, end your turn. Never poll
in a turn, and never sleep in one. Run `crew-orch.py wait` as a background
Bash command (`run_in_background`). Its exit is the wake, so run it again after
each wake. A second `wait` replaces the first. Before you run it, run
`refresh` and act on the state that the record holds: the first poll of an
item is a baseline, and it wakes nobody for a state that is known already.

Three things wake you:

| Waker | How it arrives |
|---|---|
| A message from an implementer or from the principal | a cross-session message. It arrives on its own |
| A subagent's return | its final message, as the table of `skills/project-lead/SKILL.md`'s "Every dispatch is named" says |
| A line of `wait` | the exit of the background command. One line for each event, `wake <kind> <item\|->: <detail>` |

`wait` takes the routine events itself: it writes the mode, the slot maximum
and the state of each PR, and it runs a merge that you queued. Each of those
goes to the board ("The board"). It wakes you only for a kind below.
`orchestrator-record.md`'s "`wait`" owns the line formats.

| Kind | You do |
|---|---|
| `usage` | act as `usage.md`'s "The slow-down rule" says. `wait` wrote the mode already |
| `check`, `conflict`, `comment`, `review` with words | `wait` wakes you for these only on a subagent item, and on an item in `merge_queue`. An implementer handles them on its own PR. For a subagent item, act as `subagent-items.md`'s "The PR" says. For a queued merge, read `digest <item>` and act as for a `merge-failed` line |
| `review` with `approved` | a human approval arrived, the one that no implementer reports. Run `merge` ("The merge") |
| `queue` | the PR left the merge queue and is still open. Put a notice in the inbox. A PR that entered the queue is a board event |
| `closed` | the PR closed with no merge, and `wait` freed the slot. Put a notice in the inbox, and close the item |
| `merge-failed` | a queued merge failed a check. Act as "The merge", step 3, says for that check |
| `inbox` | an implementer asked a question. Read it and act as "Questions and the inbox" says |
| `send` | a word waits for a live item. Send the text of the `told:` file with one `SendMessage`, then run `handoff clear <item>` |

## Standing instructions

`skills/project-lead/SKILL.md`'s "Standing instructions" owns which sections
exist, which of them you read, and the order of sources that decides between
the principal's word, a repo file and the machine file. Read it before you
act on a section.

## The board

Open the board pane with `/orch-board <name>` once `init` has made the
record. With no name, it uses `$CREW_ORCH`. The pane stays current by
itself, and `orchestrator-record.md`'s "The board" owns what it shows. In a
session that cannot show a pane, print `crew-orch.py board` in the transcript
at each change of state.

The board holds routine state: a merge, a queued merge, a rebase word, a
change of the mode. The principal reads it there. Tell the principal only an
inbox entry, and send no message for routine state.

## Usage

`usage.md` owns every action and every value of the usage limit:

- Act on a `usage` line of `wait` as its "The slow-down rule" says.
- Set and send the limit as its "The limit" says.

## The close of an item

An implementer item ends with these steps, in this order:

1. The PR merges ("The merge"). The command tells the implementer.
2. A window session writes the stage `merged`, then `shipped` at the ship
   word (`crew:delivered-window`). When the repo has a deploy, the ship word
   waits for it.
3. The implementer's run closes.
4. The record holds the item at `shipped`, or at `closed` for a run that ends
   with no merge.

A subagent item ends at `shipped` or `closed` as `subagent-items.md` says.
After step 4, or at that end, close the item with `close-item`, as
`resume-and-close.md`'s "The close of an item" says: the processes word, then
the session, the worktree, the branches and the ticket. On the principal's
word, close the whole run as its "The close of a run" says.

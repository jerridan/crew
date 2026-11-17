---
name: orchestrator
description: "Make this session an orchestrator of crew project-lead sessions. It takes one thing, a group of tickets, a milestone or project, or one large ticket, splits the work with no approval step, starts one project lead per item in its own terminal tab and worktree, answers their questions, keeps an inbox of what needs the principal, merges in order, and slows down before the plan usage limit. Use for 'orchestrate these tickets', 'run this milestone', 'run these in parallel', 'split this ticket and run the parts', 'crew orchestrator', 'resume orchestrator <name>'."
---

# Orchestrator

This session holds a list of items. Each item gets one `crew:project-lead`
session, the implementer, in its own terminal tab and git worktree. You are
the principal of each implementer. The person who started you is your
principal.

Four references beside this file own every command line, file format,
value and procedure that you use. Name the command, then read its owner:

| File | What it owns |
|---|---|
| `references/orchestrator-record.md` | the record, every field, the stages, the merge value, the board, and every `crew-orch.py` command |
| `references/launcher.md` | every `launcher.py` command, its output, its exit codes, and the defaults of an implementer |
| `references/usage.md` | the plan usage figures, the levels, the watch, the slow-down rule and the limit, and every `crew-usage.py` command |
| `references/resume-and-close.md` | the resume after a compaction or a restart, the close of an item after its end, and the close of a run |

`skills/project-lead/references/autonomy-contract.md` owns who a principal is
and how a project lead escalates. `skills/project-lead/SKILL.md`'s "Report to
an orchestrator" owns what a project lead writes into your record. Every
script runs from `scripts/` beside this file.

## The manager rule

You own what the work is, how it is divided, and the order. The implementer
owns how.

A goal or a ticket that you write states the goal and the desired outcome.
It can add context, data and a pointer to something to look at. Mark each of
those as context. Never tell an implementer to use a method, a file layout, a
constant or a design.

You can read code. You can dispatch read-only research, such as `Explore` or
`crew:scout`, to divide the work well. You do no implementation: you write no
code, no test and no fix, in any repo.

## The record

Your plan, each change to it with its reason, the items, the groups, the
inbox, and each message you sent an implementer live in the orchestrator
record. They survive a compaction and a restart of the machine.
`orchestrator-record.md` owns every command below.

- At the start, run `init` one time. Name the record after your own session
  name, the name that `SendMessage` reaches you by. Every `launcher.py start
  --principal` and every `Orchestrator:` line uses the same name. When your
  session has no name, or its name does not match the name pattern of
  `orchestrator-record.md`, ask the principal for a name before `init`.
- Keep no second copy in a scratchpad file. A file that you pass to `plan
  change --file` or `told --file` is input only. Read the plan, the items and
  the inbox from the record, with `show` and `plan.md`.
- After a compaction, do what `resume-and-close.md`'s "When a resume runs"
  says before your next action.
- A reopened session, or the principal's words such as "resume orchestrator
  <name>", start `resume-and-close.md`'s "The resume".

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
number, except while `usage.md`'s "The slow-down rule" lowers it. Write
`pace.slots.busy` with `pace set` when an implementer starts, and when it
ends ("After the merge").

`slots` is not a brake on usage. `usage.md`'s "The slow-down rule" says why.

## Launch an implementer

Launch the next item when all three hold:

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
   group. tmux is the second supported terminal. Read the open groups with
   `launcher.py groups`. Put the implementer in a group that fits, such as
   the group of its item group or its repo. Name a new group when none fits.
3. **The settings value.** Compute the worktree path as `launcher.md`'s
   "start" says. Then print the value with `crew-usage.py settings`
   (`usage.md`'s "The launch value").
4. **Start.** Run `launcher.py start` with the arguments of `launcher.md`'s
   "start", among them `--repo` and `--group`. Give that value as
   `--settings`, your session name as `--principal`, and a session name that
   the `--name` rule accepts. Use the item id when it does.
5. **Store the output.** Write the start output, unchanged, into the item's
   `launch` with `item <id> set launch`.
6. **Count the slot.** Write `pace.slots.busy` one higher.

On a non-zero exit, read the one stderr line beside `launcher.md`'s "Exit
codes". Fix the cause and run `start` again, or put a notice in the inbox.
Send no goal to an implementer that did not start.

**The model and Remote Control.** `launcher.md` owns both defaults of an
implementer: the model, and Remote Control off. Two things change the model:
the principal's word, and an `Implementer model` section of the machine file.
When both give a model, the order of sources decides ("Standing
instructions" below). Pass the model that wins as `--model`. Never change the
Remote Control setting of your own session.

## The goal message

The tab starts with a wait prompt. The goal arrives later, as a cross-session
message from you. That makes you the implementer's principal
(`autonomy-contract.md`). Send it when `ListAgents` shows the implementer's
session name. When the name does not show, the tab can wait on the trust
dialog (`launcher.md`'s "start"). Put a notice for the principal in the inbox,
with the item and its `tab`.

The goal message carries:

- the goal and the desired outcome, under the manager rule;
- context, data and pointers, each marked as context;
- the charter line `Gate: off`;
- the line `PR: ready`;
- the line `Orchestrator: <your name>, item <id>`
  (`skills/project-lead/SKILL.md`'s "Report to an orchestrator");
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
  "ready <sha>: fixed ..., declined ...". Send it each time the skeptical
  review stops with `accepted`, also after a round with no finding. Send it
  at the end of every round on PR comments or CI. Send it again when you ask
  for it. When a head stays unreviewed, such as past the review cap, say so
  in the line.
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

Record every message to an implementer with `told` before you send it, or as
you send it. This holds for the goal and for every later message.

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
   `told`.
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

## The overlap check

Before each merge decision in a group, list the files that any two open PRs
of the group share:

1. Run `gh pr diff <n> --name-only` for each open PR of the group.
2. Take the intersection of each pair.

PRs that share a file conflict. Merge them one at a time, in the group order.
After each merge, tell the next implementer to rebase.

## The merge

A PR merges when each check below passes. Run `crew-orch.py refresh <item>`
first. Each check names what decides it.

| Check | What decides it |
|---|---|
| The record allows the merge | the item's merge value is `can merge` (`orchestrator-record.md`'s "The merge value") |
| The ready line is for the current head | the sha of the implementer's newest ready line equals `headRefOid` of `gh pr view <n> --json headRefOid` |
| Each finding outside a review thread has a fix or a reply | that ready line names each finding in `gh pr view <n> --json reviews,comments` |
| Each review thread is resolved | `gh api graphql` on the PR's `reviewThreads`: no thread has `isResolved: false`. This row covers each finding in a thread |
| A repo that requires no approval has one | `reviewDecision` of `gh pr view <n> --json reviewDecision` is empty. Then the ready line for the current head is the approval (rule 7) |
| The overlap check is done | "The overlap check" gives this PR the next place |

A finding that the ready line does not name is not answered yet. Ask the
implementer for its ready line again. A ready line that reports the head as
unreviewed approves nothing. Put a notice in the inbox, and do not merge that
PR on the line alone.

**The method.** Merge by rebase when the repo allows it. Else use the one
method that the repo allows. `gh repo view --json
rebaseMergeAllowed,squashMergeAllowed,mergeCommitAllowed` says which. Give
the merge command the sha that the ready-line row read, as `gh pr merge
--match-head-commit <sha>`, so that GitHub refuses the merge when the head
moved. In a repo with a merge queue, the merge command puts the PR in the
queue.

**A `Merge` section replaces part of this procedure.** The section holds
prose steps, for example: "post the PR link in a review channel and wait for
a human approval, then use the merge queue". Read it from the item's repo
file, `.claude/crew.md` on the default branch, and from the machine file. The
order of sources decides which wins ("Standing instructions" below). It
replaces two things: the method, and the row "A repo that requires no
approval has one". Every other row of the table stays, and so do the group
order and the overlap check. Run its steps when every row passes, or when the
only failed condition is the approval: the merge value is `needs review`.

With no `Merge` section, a merge value of `needs review` means that the PR
waits for a human approval. Put a notice in the inbox, with the PR link.

**After the merge.** When the merge command succeeded, or the queue merged
the PR, tell the implementer. Write `pace.slots.busy` one lower. Then start
the next rebase in the group. Also write it one lower when an item reaches
`closed` with no merge.

## The wait

A wait costs no model turn, except one turn per timeout of a GitHub wait.
When nothing needs you, end your turn. Never poll in a turn, and never sleep
in one. Four things wake you:

| Waker | How it arrives |
|---|---|
| A message from an implementer | a cross-session message. It arrives on its own. |
| A message from the principal | it arrives on its own. |
| A PR or CI change that you must act on | the implementer's line: the goal asks for one at each ready head, and when an approval or a merge queue event needs you. Where no implementer can tell you, such as a human approval, a GitHub wait. |
| A usage level | the line of the usage watch (`usage.md`'s "The watch"). |

**A GitHub wait.** Run a shell loop over existing commands as a background
Bash command (`run_in_background`), with the largest timeout that the Bash
tool allows. An example is `gh pr view <n> --json
reviewDecision,state,mergeStateStatus`. The loop exits on the first change of
that output, and its exit wakes you. Write no new script for it. A timeout
wakes you too, for one turn: start the command again, only while you still
wait on that PR.

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

## Usage

`usage.md` owns every action and every value of the usage limit:

- Arm the usage watch, and act on each line, as its "The watch" says.
- At each level, act as its "The slow-down rule" says.
- Set and send the limit as its "The limit" says.

## The close of an item

An item ends with these steps, in this order:

1. The PR merges ("The merge").
2. You tell the implementer that the PR merged.
3. The implementer writes the stage `merged`, then `shipped` at the ship
   word (`crew:delivered-window`). When the repo has a deploy, the ship word
   waits for it.
4. The implementer's run closes.
5. The ticket closes, as `resume-and-close.md`'s "The close of an item"
   says.
6. The record holds the item at `shipped`, or at `closed` for a run that ends
   with no merge.

After step 6, close the item as `resume-and-close.md`'s "The close of an
item" says. On the principal's word, close the whole run as its "The close of
a run" says.

---
name: orchestrator
description: "Make this session an orchestrator of crew project-lead sessions. It takes one thing, a group of tickets, a milestone or project, or one large ticket, splits the work with no approval step, starts one project lead per item in its own terminal tab and worktree, answers their questions, keeps an inbox of what needs the principal, merges in order, and slows down before the plan usage limit. Use for 'orchestrate these tickets', 'run this milestone', 'run these in parallel', 'split this ticket and run the parts', 'crew orchestrator'."
---

# Orchestrator

This session holds a list of items. Each item gets one `crew:project-lead`
session, the implementer, in its own terminal tab and git worktree. You are
the principal of each implementer. The person who started you is your
principal.

Three references beside this file own every command line, file format and
value that you use. Name the command, then read its owner:

| File | What it owns |
|---|---|
| `references/orchestrator-record.md` | the record, every field, the stages, the merge value, the board, and every `crew-orch.py` command |
| `references/launcher.md` | every `launcher.py` command, its output, its exit codes, and the defaults of an implementer |
| `references/usage.md` | the plan usage figures, the levels, the watch, the slow-down rule and the limit, and every `crew-usage.py` command |

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
  --principal` and every `Orchestrator:` line uses the same name.
- Keep no second copy in a scratchpad file. A file that you pass to `plan
  change --file` or `told --file` is input only. Read the plan, the items and
  the inbox from the record, with `show` and `plan.md`.
- After a compaction, read `show` and `plan.md` before your next action.

## Take the work

A person can hand you work at the start, and at any later time. Each hand-over
adds to the same record. Work arrives in one of four forms:

| Form | What you do |
|---|---|
| One thing | Add one item. It starts at once, when a slot is free. |
| A group of tickets | Add one item per ticket. Put related tickets in a group. A ticket that shares no file and no component with the others is a single item. |
| A milestone, a project, or another ticket list | Read the list where it lives, such as Linear or GitHub issues. Then do as for a group of tickets. |
| One large ticket | Split it, as below. Its parts are one group. |

Write each item with `item add` and each group with `group add`. Write the
plan, and each later change to it, with `plan change` and its reason. Work
that arrives later is a plan change too.

## Split and start

Divide the work as you see fit. No step waits for the principal's approval.
Create each sub-ticket where the tickets live: Linear, GitHub issues, or a
ticket file in the repo. Each sub-ticket follows the manager rule. Then start
the items.

Only three things wait on the principal before a split or a launch:

- a gate that the principal named for this session;
- the one `Checkouts` question of "Launch an implementer". Only the items of
  that repo wait for the answer;
- the one ask for uncovered actions of "The authority at the start". The
  launch goes on, and only those actions wait for the answer.

## The authority at the start

The allow rules are the authority. Never ask the principal to confirm an
action that an allow rule covers: mark a PR ready, push, rebase, force push a
feature branch with a lease, reply on a PR, or merge.

At the start of a piece of work, before its first implementer starts:

1. List the outward actions that the work implies. Examples: mark ready,
   push, force push with a lease after a rebase, reply on a PR, merge, close
   an issue, start a paid run. Include your own actions, such as the merge.
2. Check each action against the allow rules of the sessions that take it:
   your own, and the implementer's, which starts in a worktree of the item's
   repo.
3. Ask the principal one time, for the whole set of actions that no rule
   covers. Put the ask in the inbox first ("Questions and the inbox").

The only other ask about an action is a gate that the principal named.

Never tell an implementer that it can take an action that its permission
check then refuses. Until the principal answers, the goal message names each
uncovered action as one the implementer does not take.

## Concurrency

At most three implementers work at one time by default. Two things change the
number:

- the principal's word;
- a `Concurrency` section of the machine file, `~/.claude/crew/config.md`.

Concurrency is per orchestrator, so no repo file sets it. When both sources
give a number, `skills/project-lead/SKILL.md`'s "Standing instructions" order
of sources decides.

The number is part of the plan. Write each change with `plan change` and its
reason, so the number survives a slowed period. `pace.slots.max` holds the
number, except while `usage.md`'s "The slow-down rule" lowers it. Write
`pace.slots.busy` with `pace set` when an implementer starts and when its PR
merges.

`slots` is not a brake on usage. `usage.md`'s "The slow-down rule" says why.

## Launch an implementer

Launch the next item when all four hold:

- its intake is done: the ticket or the sub-ticket exists;
- `pace.slots.busy` is below `pace.slots.max`;
- `pace.mode` lets a new implementer start (`usage.md`'s "The slow-down
  rule");
- "The authority at the start" is done for its piece of work.

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
4. **Start.** Run `launcher.py start` with that value as `--settings`, your
   session name as `--principal`, and a session name that `launcher.md`'s
   `--name` rule accepts. Use the item id when it does.
5. **Store the output.** Write the start output, unchanged, into the item's
   `launch` with `item <id> set launch`.
6. **Count the slot.** Write `pace.slots.busy` one higher.

On a non-zero exit, read the one stderr line beside `launcher.md`'s "Exit
codes". Fix the cause and run `start` again, or put a notice in the inbox.
Send no goal to an implementer that did not start.

**The model and Remote Control.** `launcher.md` owns both defaults of an
implementer: the model, and Remote Control off. Pass another model only on
the principal's word. No standing-instructions section sets a model. Never
change the Remote Control setting of your own session.

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
- the PR readiness line, `PR: ready` or `PR: draft`;
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
- **The PR is ready.** Send one line when the PR is ready for review.
- **Findings.** After each round on review or CI findings, send one line:
  "fixed ..., declined ...".
- **A GitHub event.** Send one line when an approval, a review, or a merge
  queue event needs you.
- **Uncovered actions.** Name each action that no allow rule covers, and say
  that the implementer does not take it.
- **Interfaces.** Report an interface that another item depends on to you.
  Ask you, not the other part, for an interface that is not merged.
- **Shared values.** Name each value that you own ("Groups and shared
  things"). The implementer leaves it as a placeholder.

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
| The checks pass, and the PR has no conflict | the record field `github.checks` is `pass` or `none`, and `github.merge_state` is `CLEAN` |
| No item waits before it | the record field `waits_on` is empty |
| The PR is not a draft | the record field `github.is_draft` is `false` |
| Each finding of a review or of CI has a fix or a reply | the implementer's newest "fixed ..., declined ..." line names each finding outside a thread, and no review or comment in `gh pr view <n> --json reviews,comments` is newer than that line |
| Each review thread is resolved | `gh api graphql` on the PR's `reviewThreads`: no thread has `isResolved: false` |
| The approval that the repo requires is present | the record field `github.review_decision` is `APPROVED`. When it is `null`, the repo requires no approval, and the implementer's skeptical review is the approval: the item's `stage` is `pr` |
| The overlap check is done | "The overlap check" gives this PR the next place |

The record's merge value, `can merge`, is one input. It is not the whole
procedure.

**The method.** Merge by rebase when the repo allows it. Else use the one
method that the repo allows. `gh repo view --json
rebaseMergeAllowed,squashMergeAllowed,mergeCommitAllowed` says which. In a
repo with a merge queue, the merge command puts the PR in the queue.

**A `Merge` section replaces this procedure.** The section holds prose steps,
for example: "post the PR link in a review channel and wait for a human
approval, then use the merge queue". Read it from the item's repo file,
`.claude/crew.md` on the default branch, and from the machine file.
`skills/project-lead/SKILL.md`'s "Standing instructions" order of sources
decides which wins.

**After the merge.** When the merge command succeeded, or the queue merged
the PR, tell the implementer. Write `pace.slots.busy` one lower. Then start
the next rebase in the group.

## The wait

A wait costs no model turn. When nothing needs you, end your turn. Never poll
in a turn, and never sleep in one. Four things wake you:

| Waker | How it arrives |
|---|---|
| A message from an implementer | a cross-session message. It arrives on its own. |
| A message from the principal | it arrives on its own. |
| A PR or CI change that you must act on | the implementer's line: the goal asks for one when its PR is ready, and when an approval or a merge queue event needs you. Where no implementer can tell you, such as a human approval, a `Monitor` watch on GitHub. |
| A usage level | the line of the usage watch (`usage.md`'s "The watch"). |

Before each merge decision, run `crew-orch.py refresh`.

**A GitHub watch.** Arm `Monitor` on a shell loop over existing commands,
such as `gh pr view <n> --json reviewDecision,state,mergeStateStatus`. The
loop prints a line only when the output changes. Write no new script for it.
A `Monitor` watch ends after at most 30 minutes. At its expiry, run
`crew-orch.py refresh` once, and act on any change. Arm it again only while
you still wait on that PR.

## The board

Print `crew-orch.py board` in the transcript at each change of state. No
board pane exists: issue 155 owns it, and it is not built.

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
5. The record holds the item at `shipped`, or at `closed` for a run that ends
   with no merge.

The tab and the worktree stay. Resume after a restart, and the removal of
worktrees, belong to issue 156, which is not built.

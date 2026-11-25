# Subagent items

This file owns the subagent item: an item that one subagent of the
orchestrator runs, with no implementer session, no tab and no slot. It owns
the test that makes an item one, its record, its dispatch, its PR window, its
escalation to an implementer and its close. Every other item is an implementer
item. `orchestrator-record.md` owns the field `subagent` and every
`crew-orch.py` command below.

## The test

At intake, an item is a subagent item when all four hold:

1. The ticket states the whole outcome. The work needs no spec, no design
   choice and no preference question for the principal.
2. The work is mechanical steps, and a reader can check the result against the
   ticket.
3. It changes no code, no test, no config and no instruction file. Or it is an
   obvious one-line fix, which may change any of them.
4. It is one package, in the repo of the orchestrator's session or in none,
   with at most one PR. An item in another repo is an implementer item. No item
   waits on its interface, and it has no deploy to watch.

| Item | Result |
|---|---|
| Move the tickets of a markdown file to a GitHub project | subagent item: all four hold |
| A change to the orchestrator's design across several files | implementer item: 1 and 3 fail |
| A fix to one line of a script, with a test beside it | subagent item: the fix is obvious and one line |
| A typo or a wrong path in one line of an instruction file | subagent item: the fix is obvious and one line |
| A one-line change with two possible fixes, or one that needs a choice | implementer item: 3 fails, because the fix is not obvious. The project lead's light path is for it |
| A change of one rule that other files point at or copy | implementer item: 3 fails. The check of the other files is more than one line |

An **obvious one-line fix** meets all of these. The ticket names the file and
the wrong line, or the wrong line is plain from the ticket. The fix has one
reading, so no choice is left for the principal. The diff changes one line of
the fix, and at most a test of that line beside it. The change needs no
change in another file, other than the test.

**The default is an implementer.** When one of the four is in doubt, the item
gets an implementer. So does work that needs a spec, a design choice, a
preference question, review, or more than one package.

**The principal's word wins** in both directions. It makes an item a subagent
item or an implementer item, whatever the test gives.

## The record

Before the dispatch, write `item <id> set subagent` with `name` and `model`,
and with `worktree` and `branch` as `null`. "The dispatch" says when to write
them. Write a `plan change` whose reason names the test or
the principal's word. Write the brief, and each later message to the subagent,
with `told`.

## The dispatch

- The model: `sonnet`, unless the principal names one. Never `haiku`:
  `skills/project-lead/references/band-rubric.md` says why.
- The name: `sub-<item id>`. The agent type is `general-purpose`. The dispatch
  mode follows the table of `skills/project-lead/SKILL.md`'s "Every dispatch
  is named".
- The worktree: for work that changes a repo, dispatch the subagent with the
  Agent tool's `isolation: "worktree"`. The dispatch makes the worktree. The
  subagent runs no `git worktree add`: the guard of a worktree-isolated
  session refuses it. The spawn result gives the agent id at once. Right after the
  dispatch, write `item <id> set subagent.worktree <checkout top
  level>/.claude/worktrees/agent-<agent id>` and `item <id> set
  subagent.branch worktree-agent-<agent id>`. When the task notification
  arrives, compare them with its `<worktree>` element, and write the values
  of the notification when they differ. Work that changes no repo gets no isolation and no
  worktree.
- A new dispatch of a subagent that cannot resume: give no `isolation`. The
  brief names `subagent.worktree` and `subagent.branch`, and says to work in
  that worktree on that branch, with no `git worktree add` and no switch of
  branch. The record keeps its values.
- The brief: the goal, the outcome, and context marked as context, under the
  manager rule (`SKILL.md`'s "The manager rule"). It names the ticket for the
  `Closes #<n>` line, and gives these rules: open the PR ready, not as a
  draft; never merge; reply in each review thread and resolve it, as
  `SKILL.md`'s "The goal message" says; leave each value that you own as a
  placeholder; start no `claude` process. For an obvious one-line fix, it also
  gives the rules of "The one-line fix", below. When the work needs a judgment, a
  design choice or more work than the item said, commit what is done and
  return `larger`.
- The return: one final line. `ready <sha>: <PR URL>, ...` is a ready line, as
  `SKILL.md`'s "The goal message" defines it. `done: <outcome>` is for work
  with no PR. `larger: <what it found>` stops the subagent.

## The one-line fix

Before its ready line, the subagent of an obvious one-line fix does this:

- For code or config that the repo tests, it adds or changes a test that fails
  before the fix and passes after it, and it runs the repo's own check. The
  ready line says what ran.
- For an instruction file, it reads the standing instructions of the repo and
  the file's rules, and it greps the key terms of the line against sibling
  files, so no rule gets a second copy. The ready line says what it checked.
- It leaves the plugin version and any other value that the orchestrator owns
  as a placeholder.

A change that needs more than this goes to "Larger than it looked".

## Slots and pace

A subagent item takes no slot, so write no `pace.slots.busy` for it. A new
dispatch waits as a new implementer does under `usage.md`'s "The slow-down
rule".

## The stages

You write them: `build` at the dispatch, then `item <id> pr` and `pr` when the
PR opens, then `merged` at the merge. At a `done` line, write
`subagent.outcome` and `shipped`, and put a notice with the outcome in the
inbox.

## The PR

It goes through every check of `SKILL.md`'s "The merge".

- Write each ready line with `item <id> set subagent.ready`. It is the ready
  line of `SKILL.md`'s "The merge".
- Before the merge, read `gh pr diff <n>`. A diff that does more than the
  brief asked goes to "Larger than it looked", below. For a one-line fix, the
  diff must be the one line and at most its test. More lines, or a line
  that the ticket neither names nor makes plain, go there too.
- No implementer reports GitHub events, so arm a GitHub wait (`SKILL.md`'s
  "The wait") on the PR. Its output also holds the head sha, the counts of
  reviews, comments and inline comments (`gh api
  repos/<owner>/<repo>/pulls/<n>/comments`), and the names of the failed
  checks. At each arm and each wake, read each review, comment, open thread
  and failed check that `subagent.ready` does not answer.
- Send those to the subagent: `SendMessage` to its name, which resumes it in its own worktree. When it
  cannot resume, make a new dispatch under its name and brief, as "The
  dispatch" says. It fixes, replies, resolves
  and pushes, then returns a new ready line. A finding that needs a judgment
  goes to "Larger than it looked".
- After the merge, the item stays `merged` until `crew:delivered-window`'s
  "The word that the work shipped" holds. Decide the winning `Deploy` by the
  order of sources. With `none`, the merge is the word. With `manual`, put a
  notice in the inbox and wait for the principal's word. Otherwise write
  `<scratchpad>/deploy-<item>/state.json`, with `deliverables[0].pr_url` and
  the `run.deploy` object of that skill's "The deploy watch" step 2. Arm
  `<orchestrator skill dir>/../delivered-window/scripts/pr-watch.sh <that
  directory> deploy`, as that skill's `references/pr-watch.md`'s "Arm the
  deploy watch" says. Write `shipped` at the word.

## Larger than it looked

On a `larger` line, and on a diff or a finding that needs a judgment:

1. End the subagent with `TaskStop` when it still runs. Its work stays
   committed on its branch.
2. When it has a PR, close it with `gh pr close <n> --comment`, and say that
   an implementer takes the item.
3. Remove its worktree with `launcher.py remove <worktree>`, with no
   `--delete-branch`, so the branch stays. Put a refusal in the inbox.
4. Write a `plan change` that names the old PR and the branch. Then write
   `item <id> pr none`, `item <id> set subagent null` and `stage <id> queued`.
5. Launch an implementer as `SKILL.md`'s "Launch an implementer" says. Name
   the branch in the goal message, as context.

## The close

The close of a subagent item runs where `resume-and-close.md`'s "The close of
an item" runs. The item has no session and no tab, so skip that procedure's
steps 1 and 2. Stop its subagent with `TaskStop` when it still runs. Run its
step 3 on `subagent.worktree` when it is set, with the flags of that step,
so the branch of a merged PR is deleted. When `subagent.worktree` is `null`
and `subagent.branch` is set, put a notice with the item and the branch in
the inbox, and delete nothing. Run its step 4 as it is.

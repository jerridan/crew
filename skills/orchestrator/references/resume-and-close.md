# Resume and close

This file owns two procedures of the orchestrator: the resume after a restart,
and the close of an item and of a run. Each step names its command. The owner
of each command holds its arguments, its output and its exit codes:

| File | Owns |
|---|---|
| `launcher.md` | `launcher.py find`, `resume`, `stop` and `remove` |
| `orchestrator-record.md` | every `crew-orch.py` command, `launch`, `told`, `pace` and `closed_at` |
| `usage.md` | `crew-usage.py check` and the usage watch |

Each step is safe to run again. A step that stopped part way runs again from
its start.

## When a resume runs

| Case | What is lost | What you do |
|---|---|---|
| A compaction of your session | your context only | Get the record name from your context. When the summary lost it, ask the principal, as "The resume" step 1 says. Then read the record ("The resume", step 3). Then ask each implementer with an open PR to send its ready line again. Background tasks, each subagent, the usage watch and each GitHub wait continue. Arm none of them again |
| The same session opened again: `claude --resume`, or `cc-restore` brought the tab back | every background task, subagent, `Monitor` watch and scheduled job | the whole of "The resume" |
| A new session, after a restart of the machine or a lost transcript | your context, every background task and every subagent | the whole of "The resume". The principal starts it with words such as "resume orchestrator <record name>" |

## The resume

Do these steps in this order.

1. **The record name.** The record name is fixed at `init`. Your session
   name can differ from it, and each implementer sends to your current session
   name. Run under any session name. Never rename back. When the principal's
   words do not give the record name, ask the principal for it. When
   `ListAgents` shows another live session whose name is the record name, or
   a name that a rename message in the record's `told` gave, a second
   orchestrator holds the record. Stop, and tell the principal. When no rename
   message is in `told` and your session name differs from the record name,
   the check cannot rule out a live first orchestrator. Ask the principal to
   confirm that the earlier orchestrator session has stopped.
2. **A closed record.** Run `crew-orch.py show`. When `closed_at` is set, the
   run is closed. Tell the principal so, and do nothing more.
3. **Read the record.** Read `show` and `plan.md`, then print `board`. They
   give each item, each implementer (`launch`), each open inbox entry and the
   plan.
4. **Each implementer.** Do this for each item that has a
   `launch.session_name` and a stage before `shipped`:
   - **Alive.** `ListAgents` shows its name. Run `launcher.py find <name>
     --worktree <launch.worktree> --session-id <launch.session_id>`. Give
     `--session-id` only when the record holds one. Its match is `name`.
     When the handle differs from `launch.tab`, write it with `item <id> set
     launch.tab`. A restart of the machine gives each iTerm2 tab a new id,
     and each tmux pane a new id. `launcher.md`'s "Herdr" says how a Herdr
     handle behaves.
   - **Alive, matched by `id`.** The session resumed the implementer's
     conversation, but the launcher did not start it, so it can run with
     another model, with Remote Control on, and with no usage status line.
     `cc-restore` starts a session this way. Run `launcher.py stop <handle>
     --name <name> --session-id <launch.session_id>`, then do the step
     "Gone, and its worktree exists".
   - **Matched by `cwd` only.** The session is not the implementer: a person
     or another tool started it in the worktree. Never stop it. Put a notice
     in the inbox that names the item and the handle, and do nothing more
     for the item. The principal decides.
   - **Gone, and its worktree exists.** Compute the settings value as
     SKILL.md's "Launch an implementer" says. Run `launcher.py resume` with
     the item's `launch` values: the name, the worktree, `session_id` when the
     record holds one, the model, the repo, the group and the terminal.
     Without a `session_id`, `resume` takes the newest transcript of the
     worktree. Write its output with `item <id> set launch`. Exit 8 means that
     `find` saw a session open. Run `find` as the step "Alive" says, and do
     the step that its match names.
   - **Gone, and its worktree is gone.** Nothing can resume it. Put a notice
     with the item in the inbox (`inbox add notice --item <id>`), and leave
     the item as it is. The principal decides.
   - **The rejoin message.** Send one message, with `told`, to each
     implementer that is alive or that you resumed, and whose `told` holds
     its goal message. Send none to an implementer with no goal: the step
     "No goal" gives it the goal, and the goal's envelope gives it the name.
     The message carries
     the line `Orchestrator: <record name>, item <id>` and your current session
     name from `ListAgents`, as SKILL.md's "A rename" says, so an implementer
     that missed a rename sends to the new name. It says that the
     orchestrator restarted. It asks for its ready line, its stage and each
     open question again. The part about its background tasks and watches
     depends on its process:
     - Its process restarted: you resumed it, or its handle differs from
       `launch.tab`. Tell it to arm its background tasks and watches again,
       because the restart ended them.
     - Any other live implementer kept its tasks. Tell it to arm only a
       watch that it does not hold now.

     Send it to a resumed implementer when `ListAgents` shows its name. A
     resumed tab can wait on the trust dialog, as SKILL.md's "The goal
     message" says for a new tab.
   - **A delivered item.** An item at `pr` or `merged` whose project lead
     handed over has no project lead session to wake. Send it no rejoin
     message. Run `window-watch.py ensure <record-dir>`, which restarts a
     dead watcher, with the item's goal record: the directory whose
     `state.json` holds this item in `run.orchestrator`. Never run `resume`
     for the project lead tab of a delivered item. `say` is how you reach it
     (SKILL.md's "A word to a delivered item").
   - **No goal.** An item with a `launch` whose `told` holds no goal message
     never got its goal. A rename message or a rejoin message is not a goal.
     Send the goal now, as SKILL.md's "The goal message" says. Never send a
     second goal to an item whose `told` holds one.
   - **No launch.** An item with no `launch` and a `subagent` of `null`
     follows SKILL.md's "Launch an implementer". An item with a `subagent`
     never does: "A subagent item" below says what it gets.

   An item at `shipped` or `closed` whose tab or worktree is still there
   waits for its close. It gets no rejoin message: step 1 of "The close of an
   item" tells it the current name. Run `launcher.py find` as the step
   "Alive" says:
   - It prints a handle with the match `name` or `id`: write that handle
     with `item <id> set launch.tab`. Then run "The close of an item" again
     from step 1.
   - It prints no handle, or only a `cwd` match: the session is gone. Run
     "The close of an item" again from step 1, with no step 2. Never stop a
     `cwd` match.

   **A subagent item**, an item whose `subagent` is not `null`, gets none of
   the steps above. Its subagent is gone after a reopen or a new session.
   Its brief is in `told`. By its stage:
   - `queued`: dispatch it as `subagent-items.md`'s "The dispatch" says.
   - `build`: dispatch it again under the same name and brief, as `subagent-items.md`'s "The dispatch" says for a new dispatch. Add as
     context its branch and commits, or, for work in no repo, what the record
     shows done. Tell it to read the current state before it changes
     anything. When `subagent.worktree` is set and is gone, put a notice with
     the item in the inbox instead. The principal decides.
   - `pr`: when `subagent.ready` is `null`, or its sha is not the
     `headRefOid` of the PR, dispatch it again under the same name, in the same way. Ask it
     only for a ready line for the current head.
   - `merged`: when `subagent-items.md`'s "The PR" ran a deploy watch for it,
     write its input file again with `since` `null`, and arm it again.
   - `shipped` or `closed` with its worktree still there: run "The close of
     an item" again.
5. **The slot count.** Write `pace.slots.busy` with `pace set`. The value is
   the count of implementers, alive or resumed, at a stage before `merged`.
6. **The watches and waits.** Run `crew-usage.py check`, write its level, and
   arm the usage watch, as `usage.md`'s "The watch" says. Arm a GitHub wait
   (SKILL.md's "The wait") for each item whose PR waits on something that no
   implementer reports, such as a human approval, and for each open PR of a
   subagent item, as `subagent-items.md`'s "The PR" says. No scheduled job comes back
   after a restart, so a wait never lives only in a session.
7. **The inbox.** Answer each open entry with `for: orchestrator` that is
   yours, with `answer`, and send the answer with `told`. Name each open
   entry for the principal in one message.

## The close of an item

The close runs when an item reaches `shipped`, or `closed` with no merge. It
also runs on the principal's word for an item that stops early: write
`stage <item> closed` for it first. Do these steps in this order.

1. **The implementer's processes.** Tell the implementer, with `told`, to stop
   each process and service that it started for the item, such as a server,
   a container, a watcher or a local stack. For a delivered item, send the
   message with `say` instead, and the watcher closes its own window tab at
   the ship word (`crew:delivered-window`'s "The word that the work shipped"). The message carries the
   `Orchestrator:` line and your current session name, as SKILL.md's "A
   rename" says, so an implementer that missed a rename answers to the
   current name. It answers with what it stopped.
   Only the implementer can stop a container or a service outside the
   worktree. Wait for the answer. When its session is gone, go on.
2. **The session and the tab.** Run `launcher.py stop <launch.tab> --name
   <launch.session_name> --session-id <launch.session_id>`. Give
   `--session-id` only when the record holds one. It ends the session with
   `/exit`, then closes the tab or the window. With the flags, it sends no
   key to a tab or a pane that holds another session, because an old tmux
   handle can name another pane after a restart. `launcher.md`'s "focus and
   stop" owns the check. A tab that is already gone, or that holds another
   session, is not an error. `stop` returns after the session ended, or
   after its wait ran out, so step 3 runs at once. It needs no second
   `remove` for a session that was still ending.
3. **The worktree and the branches.** Run `launcher.py remove
   <launch.worktree>` once:
   - When the item's PR merged, add `--delete-branch --pr <pr.number>`.
   - When the item's `pr` is `null`, add `--delete-branch` alone.
   - Otherwise, such as for a PR closed with no merge, add neither.

   `launcher.md`'s "remove" owns the rules: when it refuses, the lock, the
   branch candidates and the proof. When it refuses only for processes, and
   each process in `kept` has `tty` `null`, read the `command` of each one:
   - Each one is something that the implementer's work started, such as a
     server, a watcher, a test runner or a database. Run `remove` again with
     `--stop-processes`.
   - Any other one, such as an app, an editor or a language server: keep the
     worktree, and go to the notice below.

   On each other refusal, put a notice in the inbox, with `inbox add
   notice`, that names the item, the worktree, and each file, process and
   lock of the output. Never force a removal. The principal decides.

   A removal can keep branches: each entry of `branches` with `deleted`
   `false`. Put **one** notice in the inbox for the item. It names the item
   and each kept branch, with its unproven commits or with its
   `checked_out` path. Never delete a kept branch yourself. The principal
   decides.
4. **The ticket.** A GitHub issue closes through the `Closes` line of the PR.
   Check that it closed, and close it when it did not. Close a Linear ticket,
   or a ticket in a ticket file, as the standing instructions say. For an
   item closed with no merge, leave the ticket open and say so in the inbox.

**A subagent item** has no session and no tab. `subagent-items.md`'s "The
close" says which of these steps it runs.

The close writes no slot count. The item released its slot when it reached
`merged` or `closed`, as SKILL.md's "After the merge" says.

The order has three reasons. The processes stop while the session can still
say what it started. The session ends before the worktree goes, because a live
session holds its worktree, and `gh pr merge --delete-branch` fails on it. The
worktree goes last, after its processes stop.

The record keeps the item at `shipped` or `closed`, with its `launch`,
`subagent` and `told`. They are the history of the item.

## The close of a run

The close of a run starts on the principal's word.

1. **Each item.** Tell each item before `merged` to stop, with `told`: commit,
   and start no new step. Send it to a subagent with `SendMessage`, and
   `TaskStop` the subagent after its answer. Write `stage <item> closed` for each item before
   `merged`. Then run "The close of an item" for each item. Its step 3 says
   which flags to give. A clean worktree with committed work is still
   removed, because a branch with unproven commits stays.
2. **Your watches and waits.** Stop the usage watch and each GitHub wait with
   `TaskStop`.
3. **The record.** Write `pace.slots.busy` as 0. Write a last `plan change`
   with the reason. Run `crew-orch.py close`, then print `board`.

The record stays whole as the history of the run. Nothing deletes it. A later
resume of the record stops at "The resume", step 2.

## cc-restore

The public plugin `cc-restore` brings Claude Code tabs back in iTerm2 after a
restart, in their groups. Crew does not need it: "The resume", step 4, starts
each gone implementer itself. With the plugin, an implementer is often alive
already, in a tab with a new id. Step 4 finds that tab, and `resume` refuses a
second copy. The close ends each session with `/exit`, so the plugin does not
bring a closed implementer back.

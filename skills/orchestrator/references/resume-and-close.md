# Resume and close

This file owns two procedures of the orchestrator: the resume after a restart,
and the close of an item and of a run. Each step names its command. The owner
of each command holds its arguments, its output and its exit codes:

| File | Owns |
|---|---|
| `launcher.md` | `launcher.py find`, `resume`, `stop` and `remove` |
| `orchestrator-record.md` | every `crew-orch.py` command, among them `resume`, `close-item`, `wait` and `send`, and the fields `launch`, `told`, `pace` and `closed_at` |
| `usage.md` | `crew-usage.py check` and the slow-down |

Each step is safe to run again. A step that stopped part way runs again from
its start.

## When a resume runs

| Case | What is lost | What you do |
|---|---|---|
| A compaction of your session | your context only | The `SessionStart` hook adds the lines of `resume --read-only` to your context, when the record holds your session id. Get the record name from your context. When the summary lost it, ask the principal, as "The resume" step 1 says. Then do "The resume" from step 2. Each subagent and each running `wait` continue. A second `wait` replaces the first, so arm it again only when it has exited |
| The same session opened again: `claude --resume`, or `cc-restore` brought the tab back | every background task, subagent and scheduled job | the whole of "The resume". The hook gives the same lines when it finds your session id |
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
2. **Run `crew-orch.py resume`.** It does the mechanical steps in one call:
   the closed-record check, `launcher.py find` for each item with a launch (with `--terminal` from
   `launch.terminal` when stored),
   the resume of each gone implementer whose worktree exists, the
   `launch.tab` writes, `window-watch.py ensure` for each delivered item, and
   the slot count. It prints one line for each item. A line `closed:` means
   that the record is closed: tell the principal so, and do nothing more.
   Then read `plan.md` and print `board`.
3. **Each line.** Do what the action of the line says. `orchestrator-record.md`
   lists the actions. The judgments stay with you:
   - **`rejoin`.** Send one message, with `send`, to the implementer. It
     carries the line `Orchestrator: <record name>, item <id>` and your
     current session name from `ListAgents`, as SKILL.md's "A rename" says, so
     an implementer that missed a rename sends to the new name. It says that
     the orchestrator restarted. It asks for its ready line, its stage and each
     open question again. The line says whether its process restarted.
     Tell a restarted one to arm its background tasks and watches again,
     because the restart ended them. Tell any other live implementer to arm
     only a watch that it does not hold now. A resumed tab can wait on the
     trust dialog, as SKILL.md's "The goal message" says for a new tab, so
     send it when `ListAgents` shows its name.
   - **`send-goal`.** The item never got its goal. A rename message or a
     rejoin message is not a goal. Send the goal as SKILL.md's "The goal
     message" says. Never send a second goal to an item whose `told` holds
     one.
   - **`restart`.** The session resumed the implementer's conversation, but
     the launcher did not start it, so it can run with another model, with
     Remote Control on, and with no usage status line. `cc-restore` starts a
     session this way. Run the `launcher.py stop` command of the line, then
     run `resume` again.
   - **`notice`.** Add a notice to the inbox that names the item and the
     detail (`inbox add notice --item <id>`). The principal decides. Never stop
     a session that matches by working directory only: a person or another
     tool started it. Leave a gone item with a gone worktree as it is.
   - **`resume`.** Only `--read-only` prints it. Run `resume` without the
     flag. A line `rejoin` or `send-goal` replaces it.
   - **`window`.** A delivered item has no project lead session to wake. Send
     it no rejoin message. `send` is how you reach it (SKILL.md's "Message
     discipline", rule 7). Never run `launcher.py resume` for its tab.
   - **`launch`.** Follow SKILL.md's "Launch an implementer".
   - **`close`.** `resume` found the tab already and wrote a changed
     `launch.tab`. A line with `alive at <handle>` means that the session is
     still there: run "The close of an item" from its first step. A line with
     `its session is gone` means that no session answers: run
     `close-item <item> --continue` and skip the first step.
   - **`subagent`.** The subagent is gone after a reopen or a new session.
     Its brief is in `told`. By its stage:
     - `queued`: dispatch it as `subagent-items.md`'s "The dispatch" says.
     - `build`: dispatch it again under the same name and brief, as
       `subagent-items.md`'s "The dispatch" says for a new dispatch. Add as
       context its branch and commits, or, for work in no repo, what the
       record shows done. Tell it to read the current state before it changes
       anything. When `subagent.worktree` is set and is gone, put a notice
       with the item in the inbox instead. The principal decides.
     - `pr`: when `subagent.ready` is `null`, or its sha is not the
       `headRefOid` of the PR, dispatch it again under the same name, in the
       same way. Ask it
       only for a ready line for the current head.
     - `merged`: when `subagent-items.md`'s "The PR" ran a deploy watch for
       it, write its input file again with `since` `null`, and arm it again.
     - `shipped` or `closed` with its worktree still there: run "The close
       of an item" again.
   - **`ok`.** Nothing to do.
4. **The wait.** Run `refresh`, so that the record holds the known state of
   each PR. Act on what it shows. Then start `crew-orch.py wait` as a
   background Bash command (SKILL.md's "The wait"). Its first poll of an item
   is a baseline, and it wakes nobody for a state that the record holds
   already. No scheduled job comes back after a restart, so a wait never lives
   only in a session.
5. **The inbox.** Answer each open entry with `for: orchestrator` that is
   yours, with `answer`, and send the answer with `send`. Name each open
   entry for the principal in one message.

## The close of an item

The close runs when an item reaches `shipped`, or `closed` with no merge. It
also runs on the principal's word for an item that stops early: write
`stage <item> closed` for it first. Do these steps in this order.

1. **The implementer's processes.** Run `crew-orch.py close-item <item>`.
   It sends the implementer the word to stop each process and service that it
   started for the item, such as a server, a container, a watcher or a local
   stack. A delivered item gets the word by `say`, and the watcher closes its
   own window tab at the ship word (`crew:delivered-window`'s "The word that
   the work shipped"). For a live item, the command prints `send-to:` and
   `told:`. Send the text of the `told:` file with one `SendMessage` to that
   name. The word carries the `Orchestrator:` line and your current session
   name, as SKILL.md's "A rename" says, so an implementer that missed a
   rename answers to the current name. The implementer answers with what it
   stopped. Only it can stop a container or a service outside the worktree.
   Wait for the answer. When its session is gone, go on.
2. **The session, the worktree, the branches and the ticket.** Run
   `crew-orch.py close-item <item> --continue`. It runs `launcher.py stop`,
   then `launcher.py remove` with the flags that the item needs, then the
   ticket check, and it prints one line for each. `launcher.md`'s "focus and
   stop" and "remove" own the rules of the two launcher commands: the check
   before a key goes to a tab, when `remove` refuses, the lock, the branch
   candidates and the proof. The command adds an inbox notice for each
   refusal and for each kept branch. Never force a removal, and never delete
   a kept branch yourself. The principal decides.
3. **Each kept process.** The line `kept-process: <pid> <command>` means that
   `remove` refused only for processes that have no terminal. Read the
   `command` of each one:
   - Each one is something that the implementer's work started, such as a
     server, a watcher, a test runner or a database. Run `close-item <item>
     --continue --stop-processes`.
   - Any other one, such as an app, an editor or a language server: keep the
     worktree, and add a notice with `inbox add notice` that names the item,
     the worktree and each process.
4. **The ticket.** A GitHub issue closes through the `Closes` line of the PR,
   and the command closes it when it did not. A line `ticket:` says another
   kind of ticket stays: close a Linear ticket, or a ticket in a ticket file,
   as the standing instructions say. For an item closed with no merge, the
   ticket stays open, and the command adds a notice.

**A subagent item** has no session and no tab. `subagent-items.md`'s "The
close" says what it runs.

The close writes no slot count. The item released its slot when `finalize`
ran for it, at `merged` or `closed`.

The order has three reasons. The processes stop while the session can still
say what it started. The session ends before the worktree goes, because a live
session holds its worktree, and `gh pr merge --delete-branch` fails on it. The
worktree goes last, after its processes stop.

The record keeps the item at `shipped` or `closed`, with its `launch`,
`subagent` and `told`. They are the history of the item.

## The close of a run

The close of a run starts on the principal's word.

1. **Each item.** Tell each item before `merged` to stop: commit, and start no
   new step. Send it to an implementer with `send`, and to a subagent with
   `SendMessage`, and `TaskStop` the subagent after its answer. Write `stage
   <item> closed` for each item before `merged`. Then run "The close of an
   item" for each item. A clean worktree with committed work is still removed,
   because a branch with unproven commits stays.
2. **Your wait.** Stop the running `wait` with `TaskStop`, and stop each other
   background task of the run.
3. **The record.** Write `pace.slots.busy` as 0. Write a last `plan change`
   with the reason. Run `crew-orch.py close`, then print `board`.

The record stays whole as the history of the run. Nothing deletes it. A later
resume of the record stops at "The resume", step 2.

## cc-restore

The public plugin `cc-restore` brings Claude Code tabs back in iTerm2 after a
restart, in their groups. Crew does not need it: `crew-orch.py resume` starts
each gone implementer itself. With the plugin, an implementer is often alive
already, in a tab with a new id. `resume` finds that tab, and `launcher.py
resume` refuses a second copy. The close ends each session with `/exit`, so
the plugin does not bring a closed implementer back.

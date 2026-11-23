# The launcher

The orchestrator starts, resumes, finds, lists, focuses, stops and removes
its implementers with `scripts/launcher.py` in this skill's directory. An
implementer is a `crew:project-lead` session in its own git worktree. It
waits for a goal that the orchestrator sends as a cross-session message. This
file owns the subcommands, their arguments, the start output and the exit
codes.

Run the script from the plugin with `python3 <skill dir>/scripts/launcher.py`.
It needs Python 3.9 or newer and no package. On iTerm2 it runs
`scripts/iterm2-tabs.py` with `uv run --with iterm2`. On Herdr it runs
`herdr-app` and `hc`.

The launcher writes no record file. The orchestrator stores the start
output, unchanged, as the item's `launch` object.
`orchestrator-record.md`, beside this file, owns the record and its command
line.

## Terminals

The launcher supports iTerm2, tmux and Herdr. It takes the first rule that
holds:

1. `--terminal iterm2`, `--terminal tmux` or `--terminal herdr`.
2. `$TMUX` is set: tmux. A tmux inside Herdr uses tmux.
3. `$TERM_PROGRAM` is `iTerm.app`, or `$ITERM_SESSION_ID` is set: iterm2.
4. `$__CFBundleIdentifier` is `dev.herdr.app`: herdr.
5. Otherwise the command exits 4.

`groups` and `find` use rules 2 to 5. They have no `--terminal`.

## Herdr

Herdr is a macOS terminal app. Two programs control it. `herdr-app` controls
the window: spaces, tabs and focus. `hc` controls the terminals: keys, text
and the state of each one. The launcher finds each one on `PATH`, and else in
`~/.local/bin`.

| Launcher term | On Herdr |
|---|---|
| tab | one Herdr tab with one terminal. Its handle is `herdr:<terminal address>`, such as `herdr:t9` |
| group | a Herdr space |

**The tab.** `start` and `resume` run `herdr-app do tab.new` with the space,
the session name as the tab name, the worktree as the folder, and `--focus
false`. The argv is `["/bin/sh", "-c", <command>]`, where `<command>` is the
command of the tmux path. `tab.new` has no environment argument, and the
command needs none. The tab gets its environment from the Herdr core, not from
the launcher. So no `CLAUDECODE` or `CLAUDE_CODE_*` variable of the caller
reaches it. No run has checked this on a live tab.

**The space.** With `--group <name>`, the tab goes into the first space of
that name, in `herdr-app ls` order. With no such space, `do space.new` makes
it without focus, with `--tab` set to the session name. Its first tab is the
implementer's. With no `--group`,
the tab goes into the space of the caller: the `herdr.space` label that `hc get
$HC_TERMINAL_ID --json` gives. With neither, the command exits 2.
`--group-color` has no Herdr equivalent. The launcher ignores it and prints one
line on stderr that says so.

**Limits.**

- The Herdr window must run for `start`, `resume`, `groups`, `focus` and
  `stop`. A window that does not answer exits 6. `find` needs only `hc`.
- A Herdr space has no color.
- `focus` shows the tab in Herdr. It does not raise the macOS window.
- The shell of a Herdr terminal stays open after `claude` ends. So `stop`
  closes the tab.
- The tab takes its environment from the Herdr core. See "The tab", above.
- A handle after a restart. The Herdr core keeps a terminal address. After a
  crash or a reboot, a lost terminal gets a shell in its last folder with the
  same address, and its original command does not run again. So after a
  restart the old handle can name a terminal with no `claude`, and `find` and
  the target check of `stop` see no match. This is from the Herdr docs. No run
  has checked it.
- Unexercised: the keys that `stop` sends to a live `claude`, and `focus` on a
  real tab. Only the seeded test, with stub `herdr-app` and `hc`, ran them.
  One live probe made a tab and a space, and closed them.

## start

```
launcher.py start --name <session-name> [--model <model>] [--settings <file-or-json>]
                  --principal <orchestrator current session name>
                  [--repo <owner/repo>] [--checkout <path>]
                  [--group <name>] [--group-color <#rrggbb>] [--terminal iterm2|tmux|herdr]
```

| Argument | Meaning |
|---|---|
| `--name` | the session name. It matches `[a-z0-9][a-z0-9-]*` and holds no `eval`, because a worktree-isolated session refuses a shell command that holds `eval`. It names the worktree, the branch, the `claude` session and the tab or window |
| `--model` | the `--model` value of the new `claude`. The default is `opus`, never the machine's default model |
| `--settings` | a path to a file that holds one JSON object, or a JSON object as a string. The new `claude` gets it as `--settings`, read as below |
| `--principal` | the orchestrator's current session name, read from the first line of `ListAgents`. It is not the record name. The wait prompt names it |
| `--repo` | `<owner>/<repo>`. Without `--checkout`, it selects the `Checkouts` line |
| `--checkout` | the principal's checkout. It wins over `--repo`. Then `--repo` sets only the `repo` field |
| `--group` | the iTerm2 tab group, the tmux session, or the Herdr space. The tmux default is `crew`. iTerm2 with no `--group` puts the tab in no group. Herdr with no `--group` uses the space of the caller |
| `--group-color` | `#rrggbb`, the color of a new iTerm2 group. Without it, iTerm2 picks one. iTerm2 rounds colors, so never compare one for exact equality. Herdr ignores it |
| `--terminal` | `iterm2`, `tmux` or `herdr`. It wins over the environment |

Give `--repo` or `--checkout`, or both.

**The checkout.** Without `--checkout`, the launcher reads the `## Checkouts`
section of the machine file. The file is `$CREW_CONFIG` when set, and
`~/.claude/crew/config.md` otherwise. Set `CREW_CONFIG` only for a test or a
probe. The section ends at the next heading with exactly two `#`. A `###`
subheading does not end it. Each line is `<owner>/<repo>:
<path>`, with an optional `- ` before it, and a leading `~` is the home
directory. The launcher never clones a repo.

**The worktree.** The launcher runs `git fetch origin` in the checkout and
reads the remote default branch with `git ls-remote --symref origin HEAD`,
never from a local ref. It adds the worktree at
`<checkout top level>/.claude/worktrees/<name>`, on the new branch
`worktree-<name>`, at `origin/<default>`, with no upstream. An existing
worktree path or branch stops the command before the fetch.

The worktree path is known before `start` runs. `<checkout top level>` is the
real path of the checkout's top level: the output of `git rev-parse
--show-toplevel` in the checkout, with every symlink resolved. Compute the
path this way when a `--settings` value must name the worktree. The
orchestrator builds the `--settings` value before it runs `start`. The
reference of the usage part owns how.

**The tab.** The command that runs in the tab is:

```
cd <worktree> && exec <claude> --name <name> --session-id <uuid> --model <model> --settings <json> <wait prompt>
```

`<uuid>` is a new random UUID (version 4). It is the id of the new
conversation, and the `session_id` field of the output.

Every value is shell-quoted. `<claude>` is `$CREW_LAUNCHER_CLAUDE` when set,
and `claude` otherwise. It names one program; a test or a probe sets it to a
harmless one.

`<json>` is the `--settings` object with `"remoteControlAtStartup": false`
added when it has no `remoteControlAtStartup` key, and
`{"remoteControlAtStartup": false}` without `--settings`. Remote Control is
off for an implementer by default, whatever the user's own settings say, as
issue 150 rule 16 decides. The user reaches the work through the orchestrator
only. An implementer session with Remote Control on adds one more session to
the session list of the mobile app. A value that is not a JSON object exits 2.

The wait prompt tells the session that the orchestrator is its
principal, that a later message from the orchestrator can come from a new
name, to answer with one line, and to wait for the goal.

**Limit: the trust dialog.** `claude` shows its trust dialog when it starts
in a directory that it does not trust yet. The session waits until a person
answers that dialog. Its status line waits too.

- **tmux.** One new window, named `<name>`, in the tmux session `--group`.
  The launcher creates that session detached when it does not exist. The
  new window is not selected. A session target is always `=<session>`.
  Every tmux call runs with no
  `CLAUDECODE` and no `CLAUDE_CODE_*` variable. A tmux server that the
  launcher starts passes its environment to every window, so an implementer
  must not get the session variables of the orchestrator.
- **iTerm2.** One new tab in the window that holds the session
  `$ITERM_SESSION_ID` names, or in the current window. The tab is not
  selected. The session takes `<name>` as its name. With `--group`, the tab
  joins the open group of that name in that window, or starts a new group.
  When the helper fails, `osascript` opens the tab with no group, and one line
  on stderr says why. The `osascript` tab is selected when it opens, so the
  fallback selects the tab of before again. The launcher never opens a second
  tab:
  - The helper failed after it typed the command: the launcher reports the
    helper's tab with no group, and one line on stderr says why. No fallback
    runs.
  - The helper failed before it typed the command: the helper closes its tab
    first. When that close failed, the launcher closes the tab with
    `osascript`. Then the fallback opens the only tab.
  - That tab did not close: the command exits 6, and the line names the tab
    and the worktree.
  - The helper did not end in 120 seconds: the launcher kills the helper and
    every process the helper started. Then the steps above apply. The helper
    gets a deadline 20 seconds shorter, and it stops itself at that deadline.

**The output.** Stdout carries one line: one JSON object with exactly these
ten fields.

| Field | Value |
|---|---|
| `session_name` | the `--name` value |
| `repo` | `<owner>/<repo>`, from `--repo`, or else from the checkout's origin URL. `null` when that URL names no owner and repo |
| `worktree` | the absolute worktree path |
| `branch` | `worktree-<name>` |
| `base` | `origin/<default branch>` |
| `model` | the `--model` value |
| `terminal` | `iterm2`, `tmux` or `herdr` |
| `tab` | the handle: `iterm2:<session unique id>`, `tmux:<pane id>`, such as `tmux:%7`, or `herdr:<terminal address>`, such as `herdr:t9`. Treat it as one opaque string |
| `tab_group` | the iTerm2 group, tmux session or Herdr space name, or `null` |
| `session_id` | the conversation id: the `--session-id` value of `claude` |

Two fields have fixed readers. The board of issue 155 focuses an implementer
with `tab`. The resume of `resume-and-close.md` finds an implementer again
after a restart with `session_name`, `worktree`, `branch` and `session_id`.

## resume

```
launcher.py resume --name <session-name> --worktree <path> [--session-id <id>]
                   [--model <model>] [--settings <file-or-json>] [--repo <owner/repo>]
                   [--group <name>] [--group-color <#rrggbb>] [--terminal iterm2|tmux|herdr]
```

`resume` opens one tab or window that resumes an implementer's conversation
in its existing worktree. It makes no worktree and no branch. `--name`,
`--model`, `--settings`, `--repo`, `--group`, `--group-color` and
`--terminal` have the meanings and the checks of `start`. The `--model`
default is `opus`, and `<json>` gets `"remoteControlAtStartup": false` as in
`start`.

| Argument | Meaning |
|---|---|
| `--worktree` | the implementer's worktree: the `worktree` field of its start output |
| `--session-id` | the conversation to resume: the `session_id` field of its start output |

**The conversation.** Without `--session-id`, `resume` takes the newest
transcript of the worktree. That is the `*.jsonl` file with the latest
modification time directly in `<config dir>/projects/<encoded worktree>/`.
A file in a subdirectory does not count. `<config dir>` is
`$CLAUDE_CONFIG_DIR` when set, and `~/.claude` otherwise. `<encoded
worktree>` is the real worktree path with each character outside
`[A-Za-z0-9]` changed to `-`. The id is the file name without `.jsonl`.

**The checks.** In this order:

1. The worktree does not exist, or is not in a git work tree: exit 5.
2. No `--session-id` and no transcript: exit 5.
3. The base cannot be read: exit 5.
4. `find` sees an open tab or pane for `--name`, for the session id or for
   the worktree: exit 8. The line names each handle. No tab opens. Focus that
   tab, or stop it first.

**The tab.** The command that runs in the tab is:

```
cd <worktree> && exec <claude> --resume <id> --name <name> --model <model> --settings <json>
```

It has no wait prompt. The tab rules of `start` apply whole: the tmux window,
the iTerm2 helper, the `osascript` fallback, the Herdr tab, and the one-tab
rule.

**The output.** The ten fields of `start`, with these values:

| Field | Value |
|---|---|
| `worktree` | the real worktree path |
| `branch` | the branch that the worktree has checked out, or `null` when its `HEAD` is detached |
| `base` | `origin/<default branch>`, read with `git ls-remote --symref origin HEAD` as `start` reads it |
| `repo` | from `--repo`, or else from the worktree's origin URL |
| `session_id` | the resumed id |

The other fields are as in `start`.

## groups

```
launcher.py groups
```

It prints one JSON line per group, with exactly the fields `window_id`,
`group_id`, `name` and `color`. On iTerm2 a group is an open tab group, and
`color` is `#rrggbb`. On tmux a group is a tmux session: `group_id` is its id,
such as `$3`, and `window_id` and `color` are `null`. On Herdr a group is a
space: `group_id` is its id, and `window_id` and `color` are `null`. When the iTerm2 Python
API is not available, it prints one line on stderr, no group line, and exits
0.

## find

```
launcher.py find <session-name> [--worktree <path>] [--session-id <id>]
```

`find` prints one line for each open tab or pane that holds this
implementer, and exits 0. With no such tab or pane, it prints no line. A tab
or pane holds the implementer when a `claude` process on its tty has:

- the two arguments `--name <session-name>`, next to each other, or
- with `--session-id`, the two arguments `--resume <id>` or `--session-id
  <id>`, next to each other, or
- with `--worktree`, its working directory equal to the real worktree path.

Each line is `<handle> <match>`. `<match>` is the first kind in this list
that holds for a `claude` process on the tty:

| Match | The process |
|---|---|
| `name` | has `--name <session-name>` |
| `id` | has `--resume <id>` or `--session-id <id>`. A tool such as `cc-restore` starts a session again this way, with no `--name` |
| `cwd` | has its working directory in the worktree, and neither argument above. A person can start such a session |

Each match is exact. `find a` never matches the session `a-2`, and a working
directory below the worktree does not match. A `claude` process is one of
these:

- a process whose program name is `claude`, or the program name of
  `$CREW_LAUNCHER_CLAUDE`;
- `node` whose first argument, the script, ends in `/claude` or in
  `@anthropic-ai/claude-code/cli.js`. That is an npm install of Claude Code.

The launcher reads the tty of each tab and pane:

- **iTerm2.** `osascript` lists the `unique id` and the `tty` of each
  session. A failed `osascript` exits 6.
- **tmux.** `tmux list-panes -a -F '#{pane_id} #{pane_tty}'`. With no tmux
  server, `find` prints no line.
- **Herdr.** `hc ls --json` lists the live terminals. `hc get <address>
  --json` gives the pid of each one, and `ps` gives the tty of that pid. A
  failed `hc` exits 6.

It reads the processes with `ps` and their working directories with `lsof`.
A failed `ps` or `lsof` exits 6. It never reads a tab title, because Claude
Code changes the title of its tab.

## focus and stop

```
launcher.py focus <handle>
launcher.py stop <handle> [--name <session-name>] [--session-id <id>]
```

`<handle>` is the `tab` value of the start output.

**The target check.** A tmux pane id is unique only while its tmux server
runs. After a restart of the machine, a new server gives its panes the ids
from `%0` again, so an old handle can name another pane. With `--name` or
`--session-id`, `stop` first reads the tty of the tab or pane. It sends no
key and closes nothing unless a `claude` process on that tty has the match
`name` or `id`, as `find` matches it. A `cwd` match never counts, because a
person can start a `claude` in the worktree. When no process matches,
`stop` prints one line on stdout and exits 0, as for a tab that is already
gone. Without either flag, `stop` does no check. Give a flag every time the
caller knows the session.

- `focus iterm2:<id>` selects the tab, brings its window to the front and
  activates iTerm2. `focus tmux:<pane>` selects the window that holds the
  pane. When a tmux client is attached, it switches that client to the
  window. `focus herdr:<address>` runs `herdr-app do agent.focus --terminal
  <address>`, which shows the tab in Herdr. A terminal that is unknown or
  ended exits 7.
- `stop` first ends the `claude` session in the tab. It sends these keys to
  the tab, in this order:
  1. Escape. It rejects a permission dialog, and it interrupts a turn. Enter
     on a permission dialog would approve the command.
  2. Ctrl-U, half a second later. It clears the input line, so that text
     already there does not go to the model with `/exit`.
  3. `/exit` and Enter, half a second later.

  On iTerm2, `write text` sends each key: Escape and Ctrl-U with `newline
  NO`. On tmux, `send-keys` sends `Escape`, `C-u`, `-l /exit` and `Enter`. On
  Herdr, `hc keys <t> esc`, `hc keys <t> ctrl+u` and `hc send <t> /exit
  --force`; `hc send` presses Enter, and `--force` covers a status that still
  reads blocked after Escape.
  Then `stop` waits up to 15 seconds until no `claude` process has the tab's
  tty. It reads the pid and the argv of each one. When one is still there,
  one line on stderr says so, and the stop continues.
- Then `stop iterm2:<id>` closes the tab, and `stop tmux:<pane>` kills the
  pane, and its window closes with it. `stop herdr:<address>` runs
  `herdr-app do tab.close --id <tab> --confirmed true`. The tab id is the
  `herdr.tab` label of the terminal. The close is required, because the shell
  stays open after `claude` ends. A tab or pane that closed when
  `claude` ended is not an error.
- After the close, `stop` waits up to 15 more seconds until each `claude`
  pid that was still there is gone. A pid is gone when `ps` does not show
  it, or shows it with another argv, because a new process can get the pid.
  When one still runs at the end, one stderr line names each pid, and `stop`
  exits 0. `stop` sends no signal to a process. So after `stop` returns, the
  session no longer holds its worktree, and `remove` can run at once.
- A tab or pane that is already gone before the stop prints one line on
  stdout and exits 0.

**Limit: the keys.** The seeded test checks only the order of the keys. No
run has shown how a live `claude` takes Escape, Ctrl-U and `/exit`, on any
terminal.

`/exit` makes Claude Code end the session with the reason
`prompt_input_exit`. A tool that restores closed sessions, such as
`cc-restore`, then does not start the session again. A closed tab gives
another reason, and such a tool restores the session at the next start of
iTerm2.

Neither changes the worktree or the branch.

On iTerm2, both run `osascript` and need no Python API.

## remove

```
launcher.py remove <worktree> [--delete-branch [--pr <number>]] [--stop-processes]
```

`remove` removes a worktree. With `--stop-processes`, it first stops what
the implementer left running in it. With `--delete-branch`, it then deletes
each branch of the item that it can prove is kept elsewhere. It never forces
a step that can lose work. It has no force flag. Stop the implementer's tab
with `stop` first: a `claude` in a tab has its working directory in the
worktree, so `remove` refuses while it runs.

1. It finds each process whose working directory is the real worktree path
   or below it. It reads the processes with `ps` and their working
   directories with `lsof`. A failed `ps` or `lsof` exits 6. It finds a
   process by its working directory only. A process with its working
   directory outside the worktree, such as a container or a server started
   from another directory, stays running. The implementer stops that
   process itself.
2. It refuses, and changes nothing, when one of these holds:
   - `git status --porcelain` in the worktree prints a line: a changed or
     untracked file. An ignored file does not count.
   - Without `--stop-processes`: a process is in the worktree. Nothing tells
     a person's GUI editor or language server from a server that the
     implementer left. Each has no terminal.
   - With `--stop-processes`: a process in the worktree has a controlling
     terminal. That is a person's shell or editor, or a live session in a
     tab. `remove` never stops it.
   - The process that runs `remove`, or a process above it, has its working
     directory in the worktree.
   - The worktree has a lock that `remove` cannot prove dead. See "The
     lock", below.

   **An ending session.** When no file refuses, and each process that
   refuses is a `claude` process with no terminal, `remove` reads the
   processes again every half second, for up to 15 seconds. A session that
   `/exit` is ending still has its working directory in the worktree. When
   no process refuses any more, `remove` goes on. Otherwise it refuses, from
   the last read. No other refusal waits.

   **The lock.** `remove` reads the lock after that wait, from the `locked`
   line of the worktree's block in `git worktree list --porcelain`. A lock
   reason can name the pid of its owner, such as `claude session <id> (pid
   <n> start <t>)`.
   - No lock: no refusal.
   - A reason that names exactly one pid, as the word `pid`, a space and 1
     to 10 digits, where no process has that pid: the owner is dead. Step 4
     unlocks the worktree.
   - Any other lock refuses: a lock with no reason, a reason with no pid or
     with more than one, or a pid that runs. A pid that another user owns
     counts as running. A pid that the system cannot test, such as one too
     large, refuses too. A new process with the owner's pid refuses, because
     `remove` cannot prove the owner dead.
3. With `--stop-processes`, it stops each process in the worktree. Each has
   no terminal. `resume-and-close.md` says when to give the flag.
   - Right before each signal, it reads `ps` and `lsof` again. It sends the
     signal only to a pid with the same command and the same working
     directory as in step 1. A pid can go to a new process at any time, and
     `remove` never signals that process.
   - It sends `TERM` and waits up to 10 seconds. Then it sends `KILL` to each
     process that is still there, and waits up to 2 seconds.
   - It reads `ps` and `lsof` again, and finds each process in the worktree
     by the rule of step 1, whatever its command. This finds a process that
     did not stop, a process that `remove` could not signal, a process that
     changed its command, and a new process that started during the wait.
     A pid of step 1 that `ps` shows with no working directory that `lsof`
     can read counts too. When one such process runs, `remove` refuses with
     exit 9 and runs no git step. The stderr line names each pid.
   - A failed `ps` or `lsof` in this step exits 6. `remove` runs no git
     step.
4. With a dead lock owner, it tests the pid again. When a process has the
   pid now, it refuses with exit 9 and unlocks nothing. Otherwise it runs
   `git worktree unlock <path>`.
5. It runs `git worktree remove <path>`, with no force.
6. With `--delete-branch`, it deletes the branches of the item that it can
   prove are kept: "The branches", below.

**The branches.** Step 6 runs in this order.

1. **The candidates.** Each name below, once, in this order:
   1. the branch that the worktree had checked out;
   2. `worktree-<basename of the worktree path>`, the branch of `start`;
   3. each branch that a goal record of the worktree names: each
      `deliverables[].branch` of its `state.json`, then each `branch` value
      of the `worktrees.json` beside it. A goal record of the worktree is a
      `<record-root>/*/state.json` with all three of these:
      - its `run.repo`, with each symlink resolved, is the worktree path;
      - its `run.kind` is absent or not `review`;
      - its `run.created_at` is at or after the time git made the worktree:
        the mtime of `commondir` in the worktree's git dir, read before the
        removal. git writes that file once, at `worktree add`. An older
        record is of an earlier item at the same path, and its branches are
        not this item's.

      The record root is `$CREW_RECORD_ROOT`, else `~/.claude/crew`. A
      record file that cannot be read or parsed is skipped, with one stderr
      line that names it. So is a record of the worktree with no
      `run.created_at`, or one that does not parse.

   A name is a candidate only when `refs/heads/<name>` exists. The default
   branch is never a candidate: the branch that `refs/remotes/origin/HEAD`
   names, else the one that `git ls-remote --symref origin HEAD` names.
   When neither names one, `main` and `master` are never candidates, and one
   stderr line says so.
2. **The fetch.** `git fetch -q --no-prune origin`. A failed fetch is not an
   error: one stderr line says so, and the proof uses the commits that are
   already in the local object store.
3. **The keepers of origin.** `git ls-remote origin` lists the branches and
   the tags that origin holds now. Each sha under `refs/heads/` or
   `refs/tags/` is a keeper when its commit is in the local object store.
   For an annotated tag, the keeper is the peeled `^{}` sha. A failed
   `ls-remote` gives no keeper from origin, and one stderr line says so.
4. **The PR head.** With `--pr <number>`, `git ls-remote origin
   refs/pull/<number>/head` gives a sha. When that commit is not in the
   local object store, `remove` runs `git fetch -q origin
   refs/pull/<number>/head`, and checks again with `git cat-file -e
   <sha>^{commit}`. A sha that is then present is a keeper. Any failure
   gives no keeper, and one stderr line says so.
5. **The proof.** A candidate is proven kept when `git rev-list
   refs/heads/<candidate> --stdin` prints nothing, with one `^<keeper sha>`
   line on stdin for each keeper. Stdin holds a long list that the argument
   list cannot. No local ref is a keeper: not a local branch, not a
   remote-tracking ref and not a local tag. A remote-tracking ref of a
   branch that origin deleted is no copy elsewhere, and the next prune
   drops it. So one candidate never proves another.
6. **The delete.** It reads `git worktree list --porcelain` again. It
   deletes each proven candidate that no worktree has checked out, with `git
   branch -D`. Each commit is on a keeper, so the delete loses nothing. `git
   branch -d` is not enough: it refuses a branch after a rebase merge,
   because the merged commits have other shas.

Every other candidate stays. A candidate with commits that no keeper holds
gets one stderr line that names it and the count. A candidate that another
worktree has checked out stays, and that is not an error. It gets one
stderr line that names it and that worktree. A rebased branch
that was then changed stays unproven, because `remove` compares commits,
not patches. Push the branch or merge the commits, then delete the branch
yourself.

**The output.** Stdout carries one line: one JSON object with exactly these
eight fields. A refusal prints it too.

| Field | Value |
|---|---|
| `worktree` | the real worktree path |
| `removed` | `true` when the worktree is gone |
| `stopped` | one `{"pid", "command"}` object for each process of step 1 that step 3 stopped: the pid is gone, or its working directory is now outside the worktree |
| `kept` | one `{"pid", "tty", "command"}` object for each process that `remove` did not stop. On a refusal in step 2: each process in the worktree, because that refusal stops none. On a refusal in step 3: each process that the last read of step 3 found. On a failed `ps` or `lsof` in step 3: each process in the worktree, because `remove` cannot tell which ones stopped. `tty` is `null` for a process with no terminal. An empty list when `remove` removed the worktree |
| `changed` | each line of `git status --porcelain`, unchanged |
| `branch` | the branch that the worktree had checked out, or `null` when its `HEAD` was detached |
| `branches` | one `{"name", "deleted", "unproven_commits", "checked_out"}` object for each candidate, in the order of "The candidates". `deleted` is `true` when step 6 deleted it. `unproven_commits` lists the sha of each commit that no keeper holds. `checked_out` is the real path of the worktree that has it checked out, or `null`. An empty list without `--delete-branch`, and before step 6 |
| `lock` | `null` when the worktree has no lock. Else `{"reason", "pid", "unlocked"}`: the lock reason, `""` for no reason; the one pid that it names, or `null`; and `true` when step 4 unlocked the worktree |

A refusal exits 9, and one line on stderr names each reason. A refusal in
step 2 names only the processes that caused it, not each process in `kept`.
Remove each reason, then run `remove` again. A path that is not the top
level of a linked worktree exits 2: a missing path, a plain directory, or the
main worktree. `--pr` without `--delete-branch`, or a `--pr` value that is
not a positive integer, exits 2. A failed git step exits 5: `git worktree
unlock`, `git worktree remove`, `git rev-list` or `git branch -D`. The
stdout line still prints, with what `stopped` and `branches` hold. A branch
that step 6 keeps is not a failure: `remove` exits 0.

## Exit codes

Each failure prints one line on stderr. Each subcommand runs its checks in
a fixed order, and the first check that fails decides the exit:

- `start`: 2, 4, 3, 5, 6. On Herdr, 4 means a missing program, and 2 and 6
  come from the space check before any worktree.
- `resume`: 2, 4, 5. Then 6 when `ps`, `lsof`, `osascript` or `hc` cannot list
  the tabs, then 8. Then 6 when the tab does not open.
- `find`: 2, 4, 6.
- `groups`: 2, 4. On Herdr, then 6 when the window does not answer.
- `focus` and `stop`: 2, 7 for an unknown prefix. Then the terminal step: 6
  or 7. `stop` with `--name` or `--session-id`: 6 when `osascript` or `ps`
  fails in the target check.
- `remove`: 2, 5 when `git status` fails. Then 6 when `ps` or `lsof` fails,
  then 5 when `git worktree list` fails, then 9 for a refusal in step 2.
  Then, in step 3, 6 or 9. Then 9 in step 4. Then 5 when a git step fails.

| Code | Meaning |
|---|---|
| 0 | done |
| 2 | usage: a missing or bad argument, or on Herdr no `--group` from a terminal with no Herdr space. No worktree. `remove`: a path that is not a linked worktree, or a bad `--pr` |
| 3 | no `Checkouts` line for `--repo`. The line names the repo and the section. No worktree |
| 4 | unsupported terminal, or on Herdr no `herdr-app` or no `hc`. The line names `$TERM_PROGRAM` and the supported terminals, or the missing program. No worktree |
| 5 | git failure, or the worktree path or branch exists. No tab. `resume`: a missing worktree, or no transcript and no `--session-id` |
| 6 | the terminal step failed. `start` on tmux: the window did not open. `start` on iTerm2: the helper and the `osascript` fallback both failed, or a tab the helper opened did not close. For `start`, the worktree stays, and the line names its path. `focus` or `stop` on iTerm2: `osascript` failed. `stop` on tmux: `tmux kill-pane` failed. On Herdr: the window does not answer, `tab.new` or `space.new` failed, `hc` failed, or `tab.close` failed. For `focus` and `stop`, the line names the handle and no worktree. `find`, and `resume` on iTerm2: `osascript` could not list the sessions. `ps` or `lsof` failed |
| 7 | `focus` or `stop`: a handle with an unknown prefix. `focus`: a tab, pane or Herdr terminal that does not exist |
| 8 | `resume`: `find` sees an open tab or pane for this session. The line names each handle. No tab |
| 9 | `remove` refused: changed or untracked files, a process in the worktree (with `--stop-processes`, only a process with a terminal), the caller's own working directory in the worktree, or a lock that `remove` cannot prove dead. Nothing changed. With `--stop-processes`, also a process in the worktree after `TERM` and `KILL`: one that did not stop, that `remove` could not signal, that changed its command, or that started during the stop. Also a dead lock owner whose pid runs again right before the unlock. The worktree, its lock and the branches stay |

## Test

`bash scripts/test-launcher.sh` runs the seeded test with stub `tmux`,
`osascript`, `uv`, `herdr-app`, `hc`, `claude`, `ps` and `lsof`. It ends with `N of M checks
passed` and exits 0 when every check passes.

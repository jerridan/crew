# The launcher

The orchestrator starts, lists, focuses and stops its implementers with
`scripts/launcher.py` in this skill's directory. An implementer is a
`crew:project-lead` session in its own git worktree. It waits for a goal that
the orchestrator sends as a cross-session message. This file owns the
subcommands, their arguments, the start output and the exit codes.

Run the script from the plugin with `python3 <skill dir>/scripts/launcher.py`.
It needs Python 3.9 or newer and no package. On iTerm2 it runs
`scripts/iterm2-tabs.py` with `uv run --with iterm2`.

The launcher writes no record file. Issue 151 owns the orchestrator record
and its command line.

## Terminals

The launcher supports iTerm2 and tmux. It takes the first rule that holds:

1. `--terminal iterm2` or `--terminal tmux`.
2. `$TMUX` is set: tmux.
3. `$TERM_PROGRAM` is `iTerm.app`, or `$ITERM_SESSION_ID` is set: iterm2.
4. Otherwise the command exits 4.

`groups` uses rules 2 to 4. It has no `--terminal`.

## start

```
launcher.py start --name <session-name> [--model <model>] [--settings <file-or-json>]
                  --principal <orchestrator session name>
                  [--repo <owner/repo>] [--checkout <path>]
                  [--group <name>] [--group-color <#rrggbb>] [--terminal iterm2|tmux]
```

| Argument | Meaning |
|---|---|
| `--name` | the session name. It matches `[a-z0-9][a-z0-9-]*` and holds no `eval`, because a worktree-isolated session refuses a shell command that holds `eval`. It names the worktree, the branch, the `claude` session and the tab or window |
| `--model` | the `--model` value of the new `claude`. The default is `opus`, never the machine's default model |
| `--settings` | a path to a file that holds one JSON object, or a JSON object as a string. The new `claude` gets it as `--settings`, read as below |
| `--principal` | the orchestrator's own session name. The wait prompt names it |
| `--repo` | `<owner>/<repo>`. Without `--checkout`, it selects the `Checkouts` line |
| `--checkout` | the principal's checkout. It wins over `--repo`. Then `--repo` sets only the `repo` field |
| `--group` | the iTerm2 tab group, or the tmux session. The tmux default is `crew`. iTerm2 with no `--group` puts the tab in no group |
| `--group-color` | `#rrggbb`, the color of a new iTerm2 group. Without it, iTerm2 picks one. iTerm2 rounds colors, so never compare one for exact equality |
| `--terminal` | `iterm2` or `tmux`. It wins over the environment |

Give `--repo` or `--checkout`, or both.

**The checkout.** Without `--checkout`, the launcher reads the `## Checkouts`
section of the machine file. The file is `$CREW_CONFIG` when set, and
`~/.claude/crew/config.md` otherwise. Set `CREW_CONFIG` only for a test or a
probe. The section ends at the next `##` heading. Each line is `<owner>/<repo>:
<path>`, with an optional `- ` before it, and a leading `~` is the home
directory. The launcher never clones a repo.

**The worktree.** The launcher runs `git fetch origin` in the checkout and
reads the remote default branch with `git ls-remote --symref origin HEAD`,
never from a local ref. It adds the worktree at
`<checkout>/.claude/worktrees/<name>`, on the new branch `worktree-<name>`,
at `origin/<default>`, with no upstream. An existing worktree path or branch
stops the command before the fetch.

**The tab.** The command that runs in the tab is:

```
cd <worktree> && exec <claude> --name <name> --model <model> --settings <json> <wait prompt>
```

Every value is shell-quoted. `<claude>` is `$CREW_LAUNCHER_CLAUDE` when set,
and `claude` otherwise. It names one program; a test or a probe sets it to a
harmless one.

`<json>` is the `--settings` object with `"remoteControlAtStartup": false`
added when it has no `remoteControlAtStartup` key, and
`{"remoteControlAtStartup": false}` without `--settings`. Remote Control is
off for an implementer by default, whatever the user's own settings say, as
issue 150 rule 16 decides. A value that is not a JSON
object exits 2.

The wait prompt tells the session that the orchestrator is its
principal, to answer with one line, and to wait for the goal.

- **tmux.** One new window, named `<name>`, in the tmux session `--group`.
  The launcher creates that session detached when it does not exist. A
  session target is always `=<session>`.
- **iTerm2.** One new tab in the window that holds the session
  `$ITERM_SESSION_ID` names, or in the current window. The tab is not
  selected. The session takes `<name>` as its name. With `--group`, the tab
  joins the open group of that name in that window, or starts a new group.
  When the helper fails, `osascript` opens the tab with no group, and one line
  on stderr says why. The launcher never opens a second tab:
  - The helper failed after it typed the command: the launcher reports the
    helper's tab with no group, and one line on stderr says why. No fallback
    runs.
  - The helper failed before it typed the command: the helper closes its tab
    first. When that close failed, the launcher closes the tab with
    `osascript`. Then the fallback opens the only tab.
  - That tab did not close: the command exits 6, and the line names the tab
    and the worktree.

**The output.** Stdout carries one line: one JSON object with exactly these
nine fields.

| Field | Value |
|---|---|
| `session_name` | the `--name` value |
| `repo` | `<owner>/<repo>`, from `--repo`, or else from the checkout's origin URL. `null` when that URL names no owner and repo |
| `worktree` | the absolute worktree path |
| `branch` | `worktree-<name>` |
| `base` | `origin/<default branch>` |
| `model` | the `--model` value |
| `terminal` | `iterm2` or `tmux` |
| `tab` | the handle: `iterm2:<session unique id>` or `tmux:<pane id>`, such as `tmux:%7`. Treat it as one opaque string |
| `tab_group` | the iTerm2 group or tmux session name, or `null` |

Two fields have fixed readers. The board of issue 155 focuses an implementer
with `tab`. The resume of issue 156 finds an implementer again after a restart
with `session_name`, `worktree` and `branch`.

## groups

```
launcher.py groups
```

It prints one JSON line per group, with exactly the fields `window_id`,
`group_id`, `name` and `color`. On iTerm2 a group is an open tab group, and
`color` is `#rrggbb`. On tmux a group is a tmux session: `group_id` is its id,
such as `$3`, and `window_id` and `color` are `null`. When the iTerm2 Python
API is not available, it prints one line on stderr, no group line, and exits
0.

## focus and stop

```
launcher.py focus <handle>
launcher.py stop <handle>
```

`<handle>` is the `tab` value of the start output.

- `focus iterm2:<id>` selects the tab, brings its window to the front and
  activates iTerm2. `focus tmux:<pane>` selects the window that holds the
  pane. When a tmux client is attached, it switches that client to the
  window.
- `stop iterm2:<id>` closes the tab and ends its session. `stop tmux:<pane>`
  kills the pane, and its window closes with it. A tab or pane that is
  already gone prints one line on stdout and exits 0.

Neither changes the worktree or the branch.

On iTerm2, both run `osascript` and need no Python API.

## Exit codes

Each failure prints one line on stderr. When a call fails more than one
check, the first in this order decides the exit: 2, 4, 3, 5, 6.

| Code | Meaning |
|---|---|
| 0 | done |
| 2 | usage: a missing or bad argument. No worktree |
| 3 | no `Checkouts` line for `--repo`. The line names the repo and the section. No worktree |
| 4 | unsupported terminal. The line names `$TERM_PROGRAM` and the supported terminals. No worktree |
| 5 | git failure, or the worktree path or branch exists. No tab |
| 6 | the terminal step failed. On tmux, the window did not open. On iTerm2, the helper and the `osascript` fallback both failed, or a tab the helper opened did not close. The worktree stays, and the line names its path |
| 7 | `focus` or `stop`: a handle with an unknown prefix. `focus`: a tab or pane that does not exist |

## Test

`bash scripts/test-launcher.sh` runs the seeded test with stub `tmux`,
`osascript`, `uv` and `claude`. It ends with `N of M checks passed` and exits
0 when every check passes.

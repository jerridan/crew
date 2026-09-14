# Launching and steering a project-lead session

One item is one session, and this file owns every part of that session's life:
starting it, addressing it, handing it the charter, resuming it, and closing
it. The mechanism is the one T36 proved end to end (design §15.72).

## Four rules a launch obeys

Each one, broken, costs the whole item. The first three are design §15.22c;
the fourth is what T36 found (design §15.72a).

1. **Interactive.** `claude -p` cannot spawn teammates (design §12), so a
   project lead started that way cannot run the full path.
2. **Outside any worktree.** A worktree-isolated session's refusals block IC
   verification (design §15.10). Launch into an ordinary clone.
3. **Permissions pre-approved.** `--permission-mode auto`, or your own allow
   rules. The first prompt otherwise stalls a pane nobody is watching.
4. **The directory already trusted.** A session launched into an untrusted
   directory stops on the folder-trust dialog before it registers, so nothing
   can list it and no message can reach it. Check before you launch.

**The trust check** reads `~/.claude.json` — `$CLAUDE_CONFIG_DIR/.claude.json`
when that variable is set — and looks for the item's repo path:

```
python3 -c 'import json,os,sys
d = os.environ.get("CLAUDE_CONFIG_DIR")
f = os.path.join(d, ".claude.json") if d else os.path.expanduser("~/.claude.json")
try:
    projects = json.load(open(f)).get("projects", {})
except Exception:
    projects = {}
print(bool(projects.get(sys.argv[1], {}).get("hasTrustDialogAccepted")))' <repo>
```

Pass the repo path exactly as `portfolio.json` holds it — the key is the
absolute path, and a trailing slash or a symlink makes it miss.

It prints `True` or `False` and never raises: a missing or unreadable file is
`False`, because a file that cannot be read cannot prove trust.

`False` means do not launch. It is a question for the principal, and it goes
in the batch: ask them to open that directory once in Claude Code, or to set
`projects["<repo>"]["hasTrustDialogAccepted"] = true` in that file themselves,
and to tell you when it is done. Do not offer to write it: the file is the
principal's configuration, and the auto-mode classifier refuses the write as
self-modification whatever the principal approved (design §15.92h). Wait for
the word, run the check again, then launch.

## The launch

**Read `CREW_LAUNCH` in your own environment first.** `iterm2` means the next
section opens the session as a native iTerm2 tab. Any other value, and an unset
variable, mean the tmux window below. Only the display mode differs.

**One tmux session named `crew` holds every project lead**, one window each.
The principal attaches to it once. Run this before **every** launch, the first
of the portfolio and each relaunch. It costs one command and it is the only
thing that keeps a relaunch out of the wrong session:

```
tmux has-session -t "=crew" || tmux new-session -d -s crew -x 200 -y 50
```

Then open the window:

```
tmux new-window -d -t "=crew:" -n <session-name> -c <repo> 'cd <repo> && CREW_RECORD_ROOT=<portfolio-dir>/runs/<item-id> CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false claude --name <session-name> --model fable --effort high --permission-mode auto --teammate-mode tmux --plugin-dir <plugin dir>'
```

**The `cd <repo> &&` prefix is the part that works.** A tmux server holds the
working directory it was started in for life, and a server started inside a
Claude worktree that was later removed ignores `-c` without a word: the pane
opens in the deleted directory and claude exits with "The current working
directory was deleted" (design §15.93). Keep `-c <repo>` as well, for the
panes tmux opens later, but never rely on it alone.

**Name the target every time, and write it `"=crew:"`.** This step named no
session once, and the lead filled the gap with its own judgment: it ran
`tmux ls`, picked a stale session from yesterday's run and launched the window
there, where nobody was watching (design §15.93). A fixed name also lets the
principal start you outside tmux, because the session is yours to create rather
than the one you happen to sit in. The trailing colon names a session rather
than a window. The `=` forces an exact name match: without it `crew` also
matches `crew-t54`, tmux opens the window there and exits `0`, and nothing says
the run is invisible.

**A window name prefix-matches the same way**, so every later target in this
file is `"=crew:=<session-name>"`: `item-1` alone finds `item-10`.

**Tell the principal how to watch, once**, at the first launch of the
portfolio. You may be in that session already, or in another one, or in no tmux
at all. Give them both commands and let them pick:

```
tmux attach -t "=crew"          # from a terminal outside tmux
tmux switch-client -t "=crew"   # from a terminal already inside tmux
```

tmux refuses `attach` from inside any session, its own included. Say that
Ctrl-b n moves to the next window once they are there.

- **`--teammate-mode tmux` gives each IC teammate a pane.** The full path's
  named ICs then split the project lead's window, so the principal can watch
  each one (design §15.93). It has two costs. A split-pane teammate is its own
  session, and `spend.py` prices a run by its own session subtree, so a
  full-path run reports short. `spend.py`'s header owns that gap. A pane also
  needs room: tmux sizes the window down to the smallest attached terminal, and
  a split it cannot fit fails with `create pane failed: pane too small`.
- **`--name` is the address.** `SendMessage` takes a name, so a session with no
  `--name` cannot be reached at all (design §15.72b). Use the `session_name`
  you already wrote into `portfolio.json`, and make it unique per item.
- **Give it no prompt.** The charter arrives by message, below. A prompt on the
  command line races the registration you are about to wait for.
- **`CREW_RECORD_ROOT` is the item's own root** (`record-format.md`). It is
  what maps the item to its record without a message, and a resume needs the
  same value or it finds no record to reopen.
- **`--plugin-dir` only when your own session has one.** Pass the same
  directory you were launched with. A project lead with no crew plugin has no
  skill to run.
- **Fable at high effort**, the project lead's own recommendation (design §8,
  §15.71).
- `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false` keeps a suggestion out of that
  session's input box, where nothing can tell it from typed text (design
  §15.47).

## The launch, as an iTerm2 tab

This opens each project-lead session as a tab in the principal's iTerm2 window
and starts no tmux server. Everything else in this file holds: the same four
rules, the same charter message, and the same `claude` flags less
`--teammate-mode` (design §15.89). This path runs no tmux server, so an IC on
it stays in-process and the tab never splits (design §15.89d). The pricing gap
above does not apply either: an iTerm2 run is priced whole.

**Check the two requirements before the first launch of the portfolio**, with
the Python you are going to run the script on:

```
<python> -c 'import iterm2' && defaults read com.googlecode.iterm2 EnableAPIServer
```

The import must succeed and the read must print `1`. Anything else means do not
launch as a tab. It is a question for the principal, and it goes in the batch
the same way an untrusted directory does: ask them to install the `iterm2`
package, or to turn the Python API on in iTerm2's settings, or to drop
`CREW_LAUNCH`. Launching with tmux instead is not yours to decide — the
principal set the variable.

Write this script under your scratch directory and run it by path, on that same
Python. It prints the new session's id. Keep that id — every step below takes
it.

```python
import iterm2

COMMAND = ("/bin/zsh -ilc 'CREW_RECORD_ROOT=<portfolio-dir>/runs/<item-id>"
           " CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1"
           " CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false"
           " claude --name <session-name> --model fable --effort high"
           " --permission-mode auto --plugin-dir <plugin dir>'")


async def main(connection):
    app = await iterm2.async_get_app(connection)
    profile = iterm2.LocalWriteOnlyProfile()
    profile.set_use_custom_command("Yes")
    profile.set_command(COMMAND)
    profile.set_initial_directory_mode(
        iterm2.InitialWorkingDirectory.INITIAL_WORKING_DIRECTORY_CUSTOM)
    profile.set_custom_directory("<repo>")
    window = app.current_terminal_window or (app.windows or [None])[0]
    if window is None:
        window = await iterm2.Window.async_create(
            connection, profile_customizations=profile)
        tab = window.tabs[0]
    else:
        tab = await window.async_create_tab(profile_customizations=profile)
    await tab.async_set_title("<session-name>")
    print(tab.sessions[0].session_id)


iterm2.run_until_complete(main)
```

**Keep the `/bin/zsh -ilc` wrapper.** A custom command runs no interactive
shell, so a Node or Python version manager is missing from `PATH` and the run's
tests fail (design §15.89b).

Three steps below read differently:

- **Read the tab** with `session.async_get_screen_contents()`, where the step
  says `tmux capture-pane -p -t "=crew:=<session-name>.{top-left}"`.
- **Close the tab** with `session.async_close(force=True)`, where the step says
  `tmux kill-window -t "=crew:=<session-name>"`.
- **Find the tab again**, if you lost the session id, by a scan of
  `app.windows` → `tabs` → `sessions`. Claude Code writes `--name` into each
  session's `autoName` variable, with a status glyph in front of it, so match on
  the name inside that string.

Get the session with `app.get_session_by_id("<session id>")`. `None` means the
tab is gone, which is the same evidence as a name absent from `ListAgents`.

## Finding it

Call `ListAgents` and look for the name. Registration is not instant: T36's
first call listed nothing and its second, after one `sleep 15`, listed the
session as `interactive · idle`. So call once, and on a miss `sleep 15` and
call again.

Still missing after that second call means the launch failed, not that it is
slow. Capture the pane and read what stopped it: a trust dialog, a bad
`--plugin-dir`, a missing binary.

```
tmux capture-pane -p -t "=crew:=<session-name>.{top-left}"
```

**Name the pane, and name it `{top-left}`.** A window target captures whichever
pane tmux focused last, and an IC pane is not the project lead's. `.0` is wrong
too: the principal's `pane-base-index` may be `1`, and the capture then fails
with `can't find pane: 0`. That capture is a diagnostic on a session you
started, and it is the only pane you ever read. Never read a transcript.

`can't find window` is its own answer. tmux closes a window when its command
exits, so a window already gone means the command never started: a `<repo>`
that does not exist, or a missing binary.

`ListAgents` prints no model column (design §15.72b), so nothing there tells
you what the session is running on. Trust the launch command.

## Handing over the charter

One `SendMessage`, addressed to the `session_name`, carrying the charter path,
the repo path, and the instruction to run the skill:

```
Take this goal to a draft PR. The charter is at <portfolio-dir>/charters/<item-id>.md and the repository is <repo>. Run /crew:project-lead on that charter path now.
```

**Add one sentence when another item is already running in that same `repo`:**

```
Another run holds this checkout.
```

Send it whenever a second item in `portfolio.json` names the same `repo` and
its state is `running`. It is the one thing you know that the project lead
cannot read for itself, because the other run may not have switched the branch
yet. What the project lead does with it is
`../project-lead/references/simple-path.md`'s "Create the branch", and that
file owns the rule whole: you make no checkout and run no git for it.

That is the whole message. **Do not tell it to escalate to you** — the plugin's
own rules already make the sender of the goal its principal, and T36 proved a
project lead writes `run.principal` from the envelope with nothing in the
message saying to (design §15.72d). A sentence restating the mechanism only
competes with the rule.

The session starts its run on that message alone. T36's project lead loaded its
skill about five seconds after the send, with nothing typed in its pane.

Set the item `running` and write its `expect` line before you end the turn.

**Find `record_dir` on your next turn**, once the run has created it:

```
python3 -c 'import glob,sys; print(next(iter(sorted(glob.glob(sys.argv[1] + "/runs/" + sys.argv[2] + "/*/state.json"))), ""))' <portfolio-dir> <item-id>
```

Write its directory with `crew-portfolio.py item <id> set record_dir`. Until
that field holds a path you can read no `state.json`, build no `--resume`
argument and confirm no terminal state — every later step here needs it. An
empty result means the run has not created its record yet: leave the field
`null`, say so in `expect`, and look again next turn.

## Steering a live session

- **A message reaches it between tool calls, or as a new turn when it is
  idle.** Neither interrupts a running tool.
- **Send an answer once.** A repeat inside a short window is dropped at the
  sender, and a burst is refused (design §15.72). One send, then wait for the
  reply by ending your turn.
- **One nudge, then a resume.** This applies to a `running` item only. Compare
  `state.json`'s `state_changed_at` against the clock before you decide, send
  at most one "where are you" message, and if nothing moves after it, treat
  the session as dead and resume it. A `delivered` item is idle by design —
  no message and no record movement is normal — and is dead only when its
  `session_name` is absent from `ListAgents`.
- **Never type in its pane.** The pane is not a channel; a message is.

## Resuming a dead one

A `running` or `delivered` item whose `session_name` is absent from
`ListAgents` has lost its session. The record survived, so the run does.

**A message that starts `crew SessionEnd:` is how you usually hear.** Crew's
`SessionEnd` hook sends it the moment it marks the dead run `interrupted`, and
it names the item, its record and the resume command (design §15.84). It is a
notification from a hook, not an answer from a person: check `ListAgents`
yourself before you launch anything. The hook fails silently, so no message
does not mean no death — a `running` item missing from `ListAgents` is the
same evidence it always was.

Launch again with the same command, the same name and the same
`CREW_RECORD_ROOT`, then send:

```
Run /crew:project-lead --resume <goal-slug> now.
```

`<goal-slug>` is the basename of the item's `record_dir`. The resumed session
reopens that record, reconciles against git, re-enters at the first unfinished
work — or at the delivered window, when the work was already handed over —
and re-sends every escalation still holding `answer: null` — so an answer
you already have may be asked for again. Answer it from the portfolio's
`decisions.md` rather than from the principal.

A resumed session writes no new record directory, so `record_dir` does not
change.

## Closing it

A project lead's session outlives its PR. When `state.json` shows
`run_state: delivered`, the work is handed over and the session stays for
questions, follow-ups and the ship word (`skills/lead/SKILL.md`, "A delivered
item keeps its session"). Set the item `delivered` with its `outcome`, and
kill nothing.

When `state.json` shows `run_state: complete`, the ship word landed and the
session has nothing left to do. Kill its window — `tmux kill-window -t
"=crew:=<session-name>"` — and set the item `done`. An idle session left
running past that point clutters every later `ListAgents`, and `ListAgents` is
how you find the live ones.

An item the principal drops while `delivered` gets its window killed the same
way, and set `abandoned`. Its run is left `delivered` in `state.json` —
nothing there marks the drop — and the `SessionEnd` hook, which fires as the
window dies, marks it `interrupted`, the same evidence a `running` item's
death leaves.

Killing the window is safe at that point and only at that point: T36 killed the
*lead* mid-run and the project lead still finished, because the record is what
the run stands on and the channel carries only notifications (design §15.21,
§15.72g). A `delivered` session killed early costs a relaunch and a `--resume`
at the next question.

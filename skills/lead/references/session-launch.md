# Launching and steering a project-lead session

One goal is one session, and this file owns every part of that session's life:
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
in the batch: ask them to open that directory once themselves, or to approve
you setting `projects["<repo>"]["hasTrustDialogAccepted"] = true` for it. That
file is the principal's configuration, and changing configuration needs
explicit approval, the same rule that stops a project lead writing an
instruction file on its own (`autonomy-contract.md`). Approval recorded in the
portfolio's `decisions.md` covers every later launch, so this costs one
question and not one per item.

## The launch

```
tmux new-window -d -n <session-name> -c <repo> 'CREW_RECORD_ROOT=<portfolio-dir>/runs/<item-id> CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false claude --name <session-name> --model fable --effort high --permission-mode auto --plugin-dir <plugin dir>'
```

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

## Finding it

Call `ListAgents` and look for the name. Registration is not instant: T36's
first call listed nothing and its second, after one `sleep 15`, listed the
session as `interactive · idle`. So call once, and on a miss `sleep 15` and
call again.

Still missing after that second call means the launch failed, not that it is
slow. Capture the window with `tmux capture-pane -p -t <session-name>` and read
what stopped it — a trust dialog, a bad `--plugin-dir`, a missing binary. That
capture is a diagnostic on a session you started, and it is the only pane you
ever read. Never read a transcript.

`ListAgents` prints no model column (design §15.72b), so nothing there tells
you what the session is running on. Trust the launch command.

## Handing over the charter

One `SendMessage`, addressed to the `session_name`, carrying the charter path,
the repo path, and the instruction to run the skill:

```
Take this goal to a draft PR. The charter is at <portfolio-dir>/charters/<item-id>.md and the repository is <repo>. Run /crew:project-lead on that charter path now.
```

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
- **One nudge, then a resume.** An item with no message and no record movement
  is either working or dead. Compare `state.json`'s `state_changed_at` against
  the clock before you decide, send at most one "where are you" message, and if
  nothing moves after it, treat the session as dead and resume it.
- **Never type in its pane.** The pane is not a channel; a message is.

## Resuming a dead one

A `running` item whose `session_name` is absent from `ListAgents` has lost its
session. The record survived, so the run does.

Launch again with the same command, the same name and the same
`CREW_RECORD_ROOT`, then send:

```
Run /crew:project-lead --resume <goal-slug> now.
```

`<goal-slug>` is the basename of the item's `record_dir`. The resumed session
reopens that record, reconciles against git, re-enters at the first unfinished
work, and re-sends every escalation still holding `answer: null` — so an answer
you already have may be asked for again. Answer it from the portfolio's
`decisions.md` rather than from the principal.

A resumed session writes no new record directory, so `record_dir` does not
change.

## Closing it

When the item's `state.json` shows a terminal state, the session has nothing
left to do. Kill its window — `tmux kill-window -t <session-name>` — and set
the item `done` with its `outcome`. An idle session left running clutters every
later `ListAgents`, and `ListAgents` is how you find the live ones.

Killing the window is safe at that point and only at that point: T36 killed the
*lead* mid-run and the project lead still finished, because the record is what
the run stands on and the channel carries only notifications (design §15.21,
§15.72g).

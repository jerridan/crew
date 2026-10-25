# A step the principal replaced

The principal can name another reviewer for a review step, in plain
language: "use Codex for the spec review". Two steps take a replacement, and
no other step does — the spec critic, and the skeptical review (design
§15.94d). `SKILL.md`'s "Take the goal" resolved each one from five sources
and recorded it in `run.substitutions_requested`; this file runs it.

## What the replacement is told

Give the replacement what the step's own reviewer would have had:

| The step | What the replacement gets |
|---|---|
| spec critic | the whole body of `agents/spec-critic.md` below its frontmatter, `review-output.md` whole, and the absolute paths of `spec.md` and `charter.md` |
| skeptical review | the instructions file `review-runner.md` has you assemble, which already carries `review-output.md`, plus the branch at `run.review_pending.head` and the base ref |

**The spec critic's whole body, never the seven checks alone.** The scope
limit, the over-specification checks, the rule against a re-spec for one
missed item and the two verdict strings all sit around those checks, and a
replacement given the checks by themselves loses every one of them.

**Add one sentence, and only this one**: it names the absolute report path
that "Read or write the report file" below gives, and tells the replacement
to write the complete report there and to return it as its output too. For
the skeptical review, it is the sentence in `review-runner.md`'s "Reviewer
instructions", and the block is otherwise unchanged. Write the whole of what
you assembled to `<record-dir>/reviews/<prefix>-r<n>-instructions.md`, the
shape `review-runner.md` already defines for its own file.

**`<prefix>` is the step's file prefix, and the step name is not always it:**

| The step | `<prefix>` |
|---|---|
| `spec-critic` | `spec-critic` |
| `skeptical-review` | `skeptical` |

Every file this file names uses `<prefix>`, so a substituted skeptical
review writes the same names the rest of the run already looks for
(`record-format.md`, and `skeptical-review.md`'s resume list).

## Running it

The runner is a separate program. The prompt goes in on stdin, and the output
comes back on stdout. Write this script to
`<record-dir>/reviews/<prefix>-r<n>-run.sh`, with `<dir>` set to `run.repo`
for a spec review and to the review worktree `review-runner.md` names for a
skeptical review:

```
cd <dir> && {
  codex exec --sandbox read-only -C <dir> - \
    < <record-dir>/reviews/<prefix>-r<n>-instructions.md \
    2>&1 > <record-dir>/reviews/<prefix>-r<n>-result.txt
  echo $? > <record-dir>/reviews/<prefix>-r<n>-result.exit
} | tee <record-dir>/reviews/<prefix>-r<n>-result.stderr
```

`2>&1 >` sends the runner's progress to `tee` and its output to the file.
`tee` shows the progress in a pane and keeps it in `-result.stderr`, where
the runner prints its session id. A later skeptical round changes only the
`codex exec` line, as `review-runner.md`'s "Resume the reviewer" says.

**The exit file goes in the same script as the command.** `$?` holds the
runner's status only until the next command runs, and a status you keep in
your own context is lost with the session.

Two rules hold whatever the runner is. **Run it from a git repository**:
`<dir>` above is one. And **never put the instructions inside a double-quoted
shell string**: they are markdown, and one backtick in them ends the command.

## Where it runs

**Run the script headless unless the replacement words ask for a visible
pane**, such as "run Codex in a new iTerm2 pane". When they ask for one, take
the first rule that holds:

1. The words name a terminal, and its variable is set: `$TMUX` for tmux,
   `$ITERM_SESSION_ID` for iTerm2. Split the project lead's own pane there.
2. The words name tmux, `$TMUX` is unset, and `tmux` is installed: open a
   window in the detached tmux session `crew-review`.
3. `$TMUX` is set: split the project lead's own tmux pane.
4. `$ITERM_SESSION_ID` is set: split the project lead's own iTerm2 session.
5. `tmux` is installed: open a window in `crew-review`.
6. Otherwise, headless.

**Never split the current session or the focused tab.** The principal can
be in another window, and a split there lands in the principal's own work.
Each command below names the project lead's own pane or session.

`tmux-split`, from the pane id tmux gives the project lead's shell:

```
tmux split-window -h -t "$TMUX_PANE" "sh <run script>"
```

`iterm2-split`, from the UUID after the colon in `$ITERM_SESSION_ID`:

```
osascript - "${ITERM_SESSION_ID#*:}" "sh <run script>" <<'OSA'
on run argv
  tell application "iTerm2"
    repeat with w in windows
      repeat with t in tabs of w
        repeat with s in sessions of t
          if unique id of s is item 1 of argv then
            tell s to split vertically with default profile command (item 2 of argv)
            return
          end if
        end repeat
      end repeat
    end repeat
  end tell
  error "no iTerm2 session " & (item 1 of argv)
end run
OSA
```

`tmux-session`, one window per round. Tell the principal to run `tmux attach
-t crew-review`:

```
if tmux has-session -t crew-review 2>/dev/null; then
  tmux new-window -t crew-review -n <prefix>-r<n> "sh <run script>"
else
  tmux new-session -d -s crew-review -n <prefix>-r<n> "sh <run script>"
fi
```

`headless`:

```
sh <run script> > /dev/null
```

**A pane runs apart from your session.** Wait until `-result.exit` exists
before you read the output:

```
until [ -s <record-dir>/reviews/<prefix>-r<n>-result.exit ]; do sleep 15; done
```

A pane command that fails falls to the next rule in the list. Record the
display that ran as the `display` of the invocation's `run.steps_substituted`
entry: `tmux-split`, `iterm2-split`, `tmux-session` or `headless`. This rule
is for a replacement alone. The default Claude runner stays headless.

**`-result.txt` and `-result.exit` sit where `-result.json` would.** A
skeptical review the Claude runner ran saves its own JSON output; a
replacement saves the runner's output as text and its status beside it, under
the round's name, and a retry retires all of them the same way
(`record-format.md`). A resumed session reads the same list in
`skeptical-review.md`'s "Resume in the delivered window", with those two files
standing in for `-result.json` wherever entries 11 and 12 name it. **A
`-result.txt` with no `-result.exit` is an incomplete attempt**: the shell
never reached the status write, so entry 11's rule holds — retire the attempt
and retry the round.

## The lifecycle holds; three checks change

`skeptical-review.md` owns that step whole, and `review-runner.md` owns its
mechanics. A replacement changes none of it: the detached worktree, the
pending head, the round reserved before the review starts, the `Reviewed:`
first line, the two verdict lines, the one retry on a failure, and the
adjudication that clears `review_pending`. Three of the four checks in
`review-runner.md`'s "Check the review before you read it" are the Claude
runner's own. Map them:

| The Claude runner | Any other runner |
|---|---|
| exit 0, with `is_error` false | the runner's own exit status, read from `-result.exit` |
| check 2 reads `permission_denials` for a denied suite component and fills `denied` from it | `denied: "not applicable: <runner>"`. Check 2's other cases hold |
| `--session-id`, appended to `run.review_session_ids` | the `session id:` line of `-result.stderr`, written to `run.review_sessions` alone; the cost goes in the substitution entry's `usage` |

The other two checks hold word for word for every runner: the report file
exists, and its last two lines are the verdict pair while its first line is
`Reviewed: <sha>`, matching `run.review_pending.head`.

**A substituted skeptical review still writes `run.review_results[<n>]`**,
because that entry is what lets a later session adjudicate the report. `exit`
is the runner's exit status, `denials_ok` is check 2 over the cases that
hold, `denied` is the string above, and `report_ok` is the report check.
Nothing else about the round changes.

## Read or write the report file

The report path is `<record-dir>/reviews/<prefix>-r<n>.md`. `<n>` is one more
than the highest on disk for a spec review, and the round
`skeptical-review.md` reserved for a skeptical one.

First, read the file the runner wrote at that path. When it is missing, or
does not end with the step's verdict pair, transcribe the output in
`<prefix>-r<n>-result.txt` to that path instead. Open the report with
`Reviewed: <sha>` when the runner did not. Put `Source: <runner> file` or
`Source: <runner> output` on the next line, for the source you used. A spec
review reads no sha, so it carries the source line alone. End the report with
the step's own verdict pair — `ready to split` or `re-spec needed` for the
spec critic, `accepted` or `patch round needed` for the skeptical review.
Adjudicate the findings as you adjudicate any review's. Nothing else in the
run changes.

**Log every invocation, retries included.** One entry in
`run.steps_substituted` per run of the replacement: the step, the round, the
principal's own words for it, the time, a `usage` object holding what the
runner reported, the `display` that ran, and the `report_source` you used,
`file` or `output`. `record-format.md` owns the field.

## One worked example

The principal types "use Codex for the spec review" at launch, and "Take the
goal" writes that to `run.substitutions_requested`. At `SKILL.md`'s "Have
the spec reviewed" you assemble the instructions, then run Codex in place of
`crew:spec-critic`. Write `reviews/spec-critic-r1-run.sh` with `<dir>` set to
`run.repo`. The words ask for no pane, so run it headless:

```
sh <record-dir>/reviews/spec-critic-r1-run.sh > /dev/null
```

Codex wrote no file, so transcribe its output to `reviews/spec-critic-r1.md`,
and append the entry:

```
{"step": "spec-critic", "round": 1, "replacement": "use Codex for the spec review",
 "at": "2026-09-16T10:04:00Z", "usage": {"tokens": 41233}, "display": "headless",
 "report_source": "output"}
```

**Two harness limits.** The `Skill` tool is auto-rejected under `claude -p`
(design §12), so a replacement cannot invoke a slash command from inside a
headless session. A slash command passed as the positional prompt does still
run under `-p` — the skeptical review's old default did exactly that, until
§15.98 found it read the wrong ref and wrote no report, and retired it for a
prompt piped on stdin (`review-runner.md`'s "The default command"). And a
replacement you run inside this session spends your own context. A separate
process keeps its working turns out of it, and the report you read back still
costs you.

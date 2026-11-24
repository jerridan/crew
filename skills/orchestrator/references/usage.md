# Plan usage and the slow-down

This file owns the plan usage figures of the account, the levels, and the
orchestrator's slow-down rule. `crew-usage.py` computes the levels. The
project lead side (`autonomy-contract.md`'s "The usage limit line") points
here and copies none of it.

Every command below is `python3 <plugin>/skills/orchestrator/scripts/crew-usage.py
<command>`. Written `crew-usage.py <command>` in short.

## The shared file

`<record-root>/usage.json` holds the newest figures of the account. The
record root is `$CREW_RECORD_ROOT` or `~/.claude/crew/`. `crew-usage.py` is
its only writer. Writes are atomic and safe when many sessions write at once.

| Field | Holds |
|---|---|
| `five_hour`, `seven_day` | `used_pct` and `resets_at` (epoch seconds) of each window |
| `updated_at`, `source` | when the newest sample arrived, and which session or command wrote it |
| `plan_limits` | `false` when the account has no plan limits, else `true` |
| `checked_at` | when `plan_limits` was set to `false` |
| `refresh_attempt_at`, `refresh_failed` | when the last fresh reading started, and whether it failed |
| `sessions` | per session id: `at` and the last `[used_pct, resets_at]` of each window it sent |
| `window_first` | the first sample seen in the current five-hour window: `resets_at`, `at`, `used_pct` |

The merge rule applies to each window. A sample with a later `resets_at`
replaces the stored one. Within the same `resets_at`, a status line sample
wins only with a higher percent, so the old sample of an idle session never
lowers the figure. The fresh reading reads the account, and so its figure
replaces the stored one in the same `resets_at` also when it is lower. That is
how a partial reset of a window shows: the next fresh reading lowers the
figure. A lower five-hour figure from a fresh reading also starts
`window_first` again from that figure. The file keeps in `sessions` the last
figure of each window that each session sent, for 2 days. A sample that
repeats the last figure of its own session is an old sample: it changes
nothing, so an idle session cannot raise a lowered figure again. A session
that gets an API response sends a new figure, and that figure is merged by the
rule above. The first sample of a session has no last figure and is merged. A
sample with no figures changes nothing. A sample with figures clears `plan_limits: false`.

`updated_at` and `source` move only when the five-hour figure advances: a
higher percent in the same window, or a later window. A repeat of the stored
figure, a lower one from a status line sample, and a seven-day-only advance do not move them. An idle
session repeats its old figure and so cannot hide that the figure is old. The
fresh reading is the one writer that moves `updated_at` on an equal or a lower figure.

## Which sessions contribute

| Session | Contributes |
|---|---|
| A launched implementer | A sample on every status line refresh |
| The orchestrator session | Nothing |
| A session the user starts by hand | Nothing |

The figures of a session change only when it gets an API response, or at its
start. An idle session keeps its old figures.

The fresh reading covers the sessions that contribute nothing. It starts a
bare `claude` and reads the account's figures (below). It does not read a
session.

## What the figure is worth

The figure is as old as its newest sample. `check` and `watch` take a fresh
reading when the newest sample is older than 5 minutes. So the figure lags by
at most 5 minutes plus the burn in that time.

Take the worst case: a session works and contributes no sample. The measured
burn is 2 points a minute. In 5 minutes that is at most 10 points.

The margin of the `slowed` level is 15 points. It is larger than the 10-point
worst case. So a figure that reads below `slowed` cannot hide a limit that the
account already crossed, unless the burn is more than 2 points a minute.

## The fresh reading

`crew-usage.py refresh` starts `claude --restricted --strict-mcp-config
--settings <json>` with no prompt. The start loads no user plugin and reads no
settings file. It takes no model turn. It records the figures its status line
gets and ends the process. It gives up after 30 seconds.

| Result | Exit code | File |
|---|---|---|
| The status line ran and gave figures | 0 | the figures are recorded |
| The status line ran and gave none, and the file holds no five-hour window that has not reset | 0 | `plan_limits: false` |
| The status line ran and gave none, and the file holds such a window | 1 | `refresh_failed: true`; the stored figures stay |
| `claude` did not start, or ran no status line | 1 | the attempt is recorded; the figures stay |

Only `refresh` records `plan_limits: false`. An account with no plan limits,
for example an API-key account, has no five-hour figure. A timeout on a plan
account never turns the meter off, because the stored window outranks it.

`check`, `watch` and `watch --until stopped` start `claude` only when the
newest figure is older than 5 minutes and the last attempt is 5 minutes old or
more. The attempt is claimed under the file lock. So two processes that find
the file stale start one `claude`, and a failed start is not retried for 5
minutes. The `refresh` command always starts.

`claude` reads its user settings from `$CLAUDE_CONFIG_DIR/settings.json` when
that variable is set, else from `~/.claude/settings.json`. The status line
wrapper reads the same file.

Run `refresh`, `check` and `watch` from a directory that `claude` already
trusts, for example the orchestrator's repo. In a directory it does not trust,
`claude` asks for trust, the status line never runs, `refresh` exits 1 after 30
seconds, and `check` falls back to the stored file.

## The levels

`check [--limit <pct>]` prints the level and exits with its code. The limit
defaults to 95. `check` reads no other copy of the limit. Its line carries
`sampled=<UTC ISO>`, the time of the figure it read.

| Level | Exit code | When |
|---|---|---|
| `normal` | 0 | below `slowed`, or after the reset, or with no plan limits or no figures |
| `slowed` | 10 | the five-hour figure is at or above (limit − 15), or the forecast reaches the limit before the reset |
| `stopped` | 20 | the five-hour figure is at or above the limit |

The forecast is linear, from `window_first` to the newest sample. It needs at
least 10 minutes between the two. With less, the forecast is not used.

`show --json` prints `{"five_hour": {"used_pct", "resets_at", "full_at"},
"seven_day": {"used_pct", "resets_at"}}`, with `updated_at` and `source`
beside it. `full_at` is the forecast epoch of 100 percent, or `null`. Plain
`show` prints one line per window.

| `show` exit code | Meaning |
|---|---|
| 0 | figures printed |
| 1 | no figures yet: no file, or no five-hour figure |
| 2 | the account has no plan limits |

After a window's `resets_at` has passed, `show` prints `used_pct` 0, `full_at`
`null` and `reset: true` for that window, until a new sample arrives. Plain
`show` adds `(reset)` to the line.

The board reads `show --json` (`orchestrator-record.md`'s board section) and
treats any non-zero exit as no meter.

A reading that you send to another session, or write in a message, carries the
sample time of the figure: the `sampled=` value of `check` and `watch`, or
`updated_at` of `show --json`. Never write a time from memory. A figure with
no time reads as current, and it is not.

## The launch value

An implementer contributes through the status line of its session. Print the
launch value, then pass it to the launcher as `start --settings`
(`launcher.md`):

```
crew-usage.py settings --cwd <worktree path>
```

`<worktree path>` is `<checkout top level>/.claude/worktrees/<name>`.
`launcher.md` says how to compute it before `start` runs.

The value is JSON. It sets a `statusLine` command that records the sample, and
then shows the user's own status line with the same stdin and its exit code.
It keeps `padding` and `refreshInterval` of the user's line when the user sets
them. With no user line, it shows nothing. A fault in the recording never
removes the user's line. No command here changes a settings file.

## The watch

Arm `crew-usage.py watch --limit <pct>` with the `Monitor` tool. It prints one
line when the level changes, and one on a reset. It prints nothing otherwise.
Each line carries `sampled=<UTC ISO>`.

```
usage level=<level> five_hour=<pct>% limit=<n>
usage reset: level=<level> five_hour=<pct>%
```

The reset line prints only when the level before the reset was not `normal`.
After a window that stayed `normal`, a reset costs no turn.

The first level the watch reads prints nothing, whatever it is. So run
`check` once when you arm the watch, and write its level as the first mode.

A `Monitor` watch ends after at most 30 minutes. Arm it again at each expiry.
Each new watch starts with a silent first level, so run `check` at each re-arm
too. Write its level when it differs from `pace.mode`.

The watch writes no mode and reads no orchestrator record. On each line, write
the mode yourself: `crew-orch.py pace set '{"mode": "<level>"}'`
(`orchestrator-record.md` owns the command). A reset line carries the level
after the reset.

`watch --limit <pct> --until stopped` prints nothing while the level is below
`stopped`. At `stopped`, even on its first read, it prints one `usage
level=stopped ...` line and exits 20. A project lead runs it in the
background (`autonomy-contract.md`).

## The slow-down rule

The mode, the slot counts and the limit live in `pace` of the orchestrator
record (`orchestrator-record.md`). There is no second copy. A level only
changes what you write there.

- At `slowed`: start no new implementer, and dispatch no new subagent for a
  subagent item (`subagent-items.md`). Set `slots.max` to 1 with
  `crew-orch.py pace set '{"slots": {"max": 1}}'`. Tell each implementer above
  that number to pause: it finishes its current package, commits, and waits
  for the reset. Tell each implementer to defer optional work that starts a
  new process on the plan, until the reset, when the forecast says the limit
  falls before it. A goal check, a skeptical review round and a push that
  starts a CI run are such work.
- At `stopped`: tell each implementer to stop. It commits and starts no new
  step. Dispatch no new subagent.
- At the reset: set the mode to `normal` and restore `slots.max` to the
  concurrency number: 3 by default, or the number that the principal's word or
  the standing instructions set. An implementer that waits resumes by itself.
- With no plan limits: there is no meter and no slow-down. The level stays
  `normal`.

An implementer's own project lead acts alone only at `stopped`
(`autonomy-contract.md`). It treats your pause message like `stopped`. It
waits with `crew-usage.py wait`, which exits 0 once the stored five-hour window
has reset, or a later window shows in the file. With no figures it exits 1 at
once.

`slots` counts implementer sessions only. A subagent item takes no slot. A
slot is not a brake on burn. In one window, a single working implementer moved the five-hour figure from 61% to 82%
in 19 minutes. A headless review run, a CI review run on the same plan, and the
implementer's own ICs burn usage outside the slot count. The level is the
brake: the figure itself, and the forecast.

## The limit

The limit is 95 by default. `pace.limit_pct` holds it. Two things change it:

- The principal's word.
- A `Usage limit` section of the standing instructions
  (`skills/project-lead/SKILL.md`'s "Standing instructions").

Pass the limit to every `check` and `watch` as `--limit`. Write `Usage limit:
<pct>` into each goal you send, as a copy of `pace.limit_pct` at that time.
When the limit changes, write the new value to `pace.limit_pct`, restart the
watch with it, and send the new value to each implementer.

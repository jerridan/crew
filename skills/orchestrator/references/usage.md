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
| `window_first` | the first sample seen in the current five-hour window: `resets_at`, `at`, `used_pct` |

The merge rule applies to each window. A sample with a later `resets_at`
replaces the stored one. Within the same `resets_at`, the higher percent wins.
So the old sample of an idle session never lowers the figure. A sample with no
figures changes nothing. A sample with figures clears `plan_limits: false`.

`updated_at` moves only when a sample is not older than the stored figure. An
idle session repeats its old figure and so cannot hide that the figure is old.

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
| The status line ran and gave none | 0 | `plan_limits: false` |
| `claude` did not start, or ran no status line | 1 | unchanged |

Only `refresh` records `plan_limits: false`. An account with no plan limits,
for example an API-key account, has no five-hour figure. An account marked
that way gets one start every 5 minutes while `check` or `watch` runs.

Run `refresh`, `check` and `watch` from a directory that `claude` already
trusts, for example the orchestrator's repo. In a directory it does not trust,
`claude` asks for trust, the status line never runs, `refresh` exits 1 after 30
seconds, and `check` falls back to the stored file.

## The levels

`check [--limit <pct>]` prints the level and exits with its code. The limit
defaults to 95. `check` reads no other copy of the limit.

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
`show` prints one line per window. Both exit 1 with no plan limits or no
figures. The board reads `show --json`, and treats that exit as no meter.

## The launch value

An implementer contributes through the status line of its session. Print the
launch value, then pass it to the launcher as `start --settings`:

```
crew-usage.py settings --cwd <checkout top level>
```

The value is JSON. It sets a `statusLine` command that records the sample, and
then shows the user's own status line with the same stdin and its exit code.
It keeps `padding` and `refreshInterval` of the user's line when the user sets
them. With no user line, it shows nothing. A fault in the recording never
removes the user's line. No command here changes a settings file.

## The watch

Arm `crew-usage.py watch --limit <pct>` with the `Monitor` tool. It prints one
line when the level changes, and one on a reset. It prints nothing otherwise.

```
usage level=<level> five_hour=<pct>% limit=<n>
usage reset: level=<level> five_hour=<pct>%
```

The first level the watch reads prints nothing, whatever it is. So run
`check` once when you arm the watch, and write its level as the first mode.

A `Monitor` watch ends after at most 30 minutes. Arm it again at each expiry.
Each new watch starts with a silent first level, so run `check` at each re-arm
too. Write its level when it differs from `pace.mode`.

The watch writes no mode and reads no orchestrator record. On each line, write
the mode yourself: `crew-orch.py pace set '{"mode": "<level>"}'`. A reset line
carries the level after the reset.

## The slow-down rule

The mode, the slot counts and the limit live in `pace` of the orchestrator
record (`orchestrator-record.md`). There is no second copy. A level only
changes what you write there.

- At `slowed`: start no new implementer. Set `slots.max` to 1 with
  `crew-orch.py pace set '{"slots": {"max": 1}}'`. An implementer above that
  number finishes its current package, commits, and waits for the reset.
- At `stopped`: tell each implementer to stop. It commits and starts no new
  step.
- At the reset: set the mode to `normal` and restore `slots.max` to the
  concurrency number: 3 by default, or the number that the principal's word or
  the standing instructions set. An implementer that waits resumes by itself.
- With no plan limits: there is no meter and no slow-down. The level stays
  `normal`.

An implementer's own project lead acts only at `stopped`
(`autonomy-contract.md`). At `slowed` it goes on, and you decide how many
work. To wait for the reset, an implementer runs `crew-usage.py wait`. It
exits 0 once the stored five-hour window has reset. With no figures it exits 1
at once.

## The limit

The limit is 95 by default. `pace.limit_pct` holds it. Two things change it:

- The principal's word.
- A `Usage limit` section of the standing instructions
  (`skills/project-lead/SKILL.md`'s "Standing instructions").

Pass the limit to every `check` and `watch` as `--limit`. Write `Usage limit:
<pct>` into each goal you send, as a copy of `pace.limit_pct` at that time.
When the limit changes, write the new value to `pace.limit_pct`, restart the
watch with it, and send the new value to each implementer.

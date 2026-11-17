# The orchestrator record

This file owns the orchestrator record: where it lives, every field of
`orchestrator.json`, the ids, the stages, the merge value, the board and every
command of `crew-orch.py`. No other file defines a field of it. A project
lead's reports into the record are in
`skills/project-lead/references/orchestrator-report.md`. A goal's own record
is `record-format.md`.

An orchestrator is a session that runs many goals, each under its own project
lead. The record is its one shared state: the items it runs, the groups
that merge in order, the questions that wait on the principal, the plan and
what each implementer was told.

## Where it lives

The record is the directory `<record-root>/orchestrators/<name>/`. The root is
`$CREW_RECORD_ROOT`, or `~/.claude/crew/` when that variable is unset. `<name>`
matches `[a-z0-9][a-z0-9_-]{0,63}`. A goal record never lives under
`orchestrators/`, and `crew-stats.py` does not read that directory.

| Path | Holds |
|---|---|
| `orchestrator.json` | the state: every field below |
| `plan.md` | the current plan, copied there by `plan change --file` |
| `told/` | one file per message the orchestrator sent an implementer |
| `orchestrator.lock` | the `fcntl` lock that each write takes |

`crew-orch.py` is the only writer. A reader uses `show`, or reads
`orchestrator.json`, and never writes it.

## How the script runs

The script is `skills/orchestrator/scripts/crew-orch.py`. It uses Python 3 and
the standard library alone, and it works from any directory. A project lead
calls it as `<its skill dir>/../orchestrator/scripts/crew-orch.py`.

The name comes from `--orch <name>` or from `$CREW_ORCH`. The flag wins. With
neither, the script exits 2 with one line.

Each write takes an exclusive lock, reads the file again, changes it and
replaces it with an atomic rename. Two writers at once both land. A usage
error prints one line on stderr, exits 2 and writes nothing. An unknown item,
group or entry id is a usage error. So is an argument that is not valid UTF-8.
The argument `--` ends the options, so text that starts with `--` goes after
it. A command on a record that does not exist,
a second `init`, and `refresh <item>` on an item with no PR exit 1. Success
exits 0.

A time is an ISO-8601 UTC string, `YYYY-MM-DDTHH:MM:SSZ`. `null` means not set.

## `orchestrator.json`

Top-level keys:

| Key | Holds |
|---|---|
| `version` | `1` |
| `name` | the orchestrator name |
| `created_at`, `updated_at` | times |
| `closed_at` | the time of `close`, or `null` while the run is open. See "Closing the record" |
| `counters` | `{item, decision, question, idea, notice}`, each an integer that only grows |
| `items` | an object keyed by item id |
| `groups` | an object keyed by group id |
| `inbox` | a list of entries, oldest first |
| `plan_changes` | a list of `{at, change, reason}` |
| `pace` | the slot limit and the pace mode |

### Ids

An item id and a group id match `[a-z0-9][a-z0-9_-]{0,31}`. The word `add` is
not an id. An inbox id is the letter of its kind and that kind's counter after
the add: `d1` for a decision, `q1` for a question, `i1` for an idea and `n1`
for a notice. A counter never goes back, so an id is never reused. An item's
display number `n` is `counters.item` after the add.

### An item

| Field | Holds |
|---|---|
| `id` | the item id |
| `n` | the display number: 1, 2, and so on, in add order |
| `title` | text |
| `repo` | `owner/name` |
| `group` | a group id, or `null` |
| `ticket` | `{id, url}`, or `null`. `url` may be `null` |
| `pr` | `{number, url}`, or `null` |
| `stage` | one of the stages below. `item add` sets `queued` |
| `detail` | text that goes with the stage, such as `2/3`, or `null` |
| `stage_at` | the time of the last stage write |
| `doing` | what the item does now, or `null` |
| `doing_at` | the time of the last `doing` write, or `null` |
| `github` | `null`, or the object below |
| `merge` | the merge value. Derived |
| `waits_on` | the item ids this item waits on. Derived |
| `launch` | the object below. `{}` until set |
| `told` | a list of `{at, path}`. `path` is `told/<item>-<k>.md` |
| `created_at` | a time |

`merge` and `waits_on` are recomputed on every write, from the stored fields
alone. No command sets them.

`github`, when set, holds:

| Field | Holds |
|---|---|
| `state` | `OPEN`, `CLOSED` or `MERGED` |
| `is_draft` | a boolean |
| `review_decision` | `APPROVED`, `CHANGES_REQUESTED`, `REVIEW_REQUIRED` or `null` |
| `merge_state` | the `mergeStateStatus` that GitHub gives, or `null` |
| `checks` | `pass`, `fail`, `pending` or `none` |
| `failed_checks` | the names of the failed checks |
| `in_queue` | a boolean |
| `queue_position` | an integer, or `null` |
| `refreshed_at` | a time |
| `error` | one line, or `null` |

`launch` holds ten keys, each a string or `null`. The launcher writes them.

| Key | Holds |
|---|---|
| `session_name` | the name of the project lead's session |
| `repo` | `owner/name` |
| `worktree` | the absolute path of its worktree |
| `branch` | its branch |
| `base` | `origin/<default branch>` |
| `model` | the model it runs on |
| `terminal` | `iterm2` or `tmux` |
| `tab` | `iterm2:<session unique id>` or `tmux:<pane id>` |
| `tab_group` | a tab group name, or `null` for none |
| `session_id` | the id of the project lead's conversation, which `launcher.py resume` takes |

### A group

| Field | Holds |
|---|---|
| `id` | the group id |
| `title` | text |
| `repo` | `owner/name`, or `null` |
| `ticket` | `{id, url}`, or `null` |
| `order` | the item ids, in merge order |
| `owners` | an object: a file or component name to the one item id that owns it |
| `created_at` | a time |

An item in a group waits on every item before it in `order` that is not at
`merged`, `shipped` or `closed`.

### An inbox entry

| Field | Holds |
|---|---|
| `id` | `d1`, `q1`, `i1` or `n1` and so on |
| `kind` | `decision`, `question`, `idea` or `notice` |
| `for` | `principal` or `orchestrator` |
| `item` | an item id, or `null` |
| `text` | text |
| `recommend` | text, or `null` |
| `created_at` | a time |
| `routed_at` | the time `route` moved it, or `null` |
| `state` | `open`, `answered` or `dismissed` |
| `answer` | the answer, or the reason of a `dismiss`, or `null` |
| `closed_at` | a time, or `null` |

A closed entry stays in the list. An item can have more than one open entry.

### `pace`

`pace` is `{mode, slots, limit_pct}`. It starts as `{"mode": "normal",
"slots": {"busy": 0, "max": 3}, "limit_pct": 95}`.

| Field | Holds |
|---|---|
| `mode` | `normal`, `slowed` or `stopped` |
| `slots` | `{busy, max}`, two integers |
| `limit_pct` | an integer, 95 by default |

`pace set <json>` merges its object into `pace`. The record holds no usage
figure. The account-wide plan figures live in `<record-root>/usage.json`, and
`crew-usage.py` owns that file.

## The stages

The closed list, in order: `queued`, `spec`, `split`, `build`, `review`, `pr`,
`merged`, `shipped`, `closed`. The board draws `spec` to `pr` as five marks:
`●` for a stage passed, `◐` for the current one and `○` for one not reached.
`queued` shows five `○`. `merged`, `shipped` and `closed` show five `●`.

The status word of a row is the merge value in three cases: an item with a PR
at stage `review` or `pr`, and an item at `merged` or `shipped`. An item at
`closed` shows `closed`. In every other case the word is the stage, with its
`detail` (`build 2/3`). Before a `refresh` has read the PR, an item at `review`
or `pr` shows the stage word.

## The merge value

`refresh` and every write recompute `merge` as the first match in this order:

| Value | When |
|---|---|
| `merged` | the PR state is `MERGED`, or the stage is `merged` or `shipped` |
| `no PR` | the item has no PR |
| `closed` | the PR state is `CLOSED`, or the stage is `closed` |
| `in queue` | the PR is in the merge queue. It adds the position when GitHub gives one: `in queue 3` |
| `can merge` | not a draft, the review decision is `APPROVED` or none, merge state `CLEAN`, checks `pass`, and no wait. GitHub gives an empty decision when the repo requires no review, and the record stores `null` |
| `needs review` | not a draft, checks `pass`, and either `REVIEW_REQUIRED` with merge state `CLEAN` or `BLOCKED`, or no decision with merge state `BLOCKED` |
| `waits on <ids>` | the item waits on at least one item before it in its group |
| `conflict` | merge state `DIRTY` or `BEHIND` |
| `ci failing` | checks `fail` |
| `ci pending` | checks `pending` |
| `draft` | the PR is a draft |
| `changes requested` | the review decision is `CHANGES_REQUESTED` |
| `blocked` | none of the above |

`refresh` drops every `CANCELLED` run, then takes the latest run of each
workflow and check name. A run with no `startedAt`, or with one that starts with `0001-01-01`, is the
latest run of its name. That is how `gh` prints an unset time. `SUCCESS`, `NEUTRAL` and `SKIPPED` pass. `FAILURE`,
`ERROR`, `TIMED_OUT`, `STARTUP_FAILURE` and `ACTION_REQUIRED` fail. Any other
state is pending. With no run left, `checks` is `none`, and `can merge` and
`needs review` read `none` as passing.

An item with a PR has no `github` until its first `refresh`, so its merge
value is `waits on <ids>` or `blocked` until then.

## The board

`board` reads the record alone and never writes it. `board --json` prints the
board as one JSON object, described under "The board JSON" below. That object
is the one source of the board's content. The text view of `board` and the
board pane (`hooks/orch-board.tsx`) draw from it. The resume of
`resume-and-close.md` reads the board from the same object. Each value is
made once, in the object, and a reader computes no value of its own.

The text view prints, in this order:

1. The Plan block, when `crew-usage.py` gives figures. The 5h line holds the
   percent, the reset time and the time the plan is full. The 7d line holds
   the percent and the reset time. A time is local clock time, or a weekday
   when it is more than a day away. `pace.mode: slowed` adds `SLOWED: <busy>
   of <max> slots` to the 5h line, and `stopped` adds `STOPPED`. With no Plan
   block, a `slowed` or `stopped` mode prints that word on its own line.
2. `Needs you <count>`: every open entry with `for: principal`, oldest first.
   A row holds the id, the kind, the age, the item and the text. The age of a
   routed entry counts from `routed_at`. A
   `Recommended:` line follows an entry that has `recommend`.
3. One section for each group that has an open item: the title, the ticket,
   the repo and `<merged> of <total> merged`. Its items follow in merge order.
4. `Single items`: the items with no group.
5. `Done <count>`: the items at `shipped` or `closed` outside an open group.

An item row holds `n`, the id, the five marks, the status word, the PR number,
`doing` and the age of `doing_at`. A `waits on` value names the items. The text `after <ids>` shows only when
the status word is not the merge value. An age
is one number and one unit, the largest that is not zero: `40s`, `12m`, `2h`,
`1d`.

A single item's row shows the item's own ticket in a cell after the PR. The
cell is as wide as the widest ticket id of the single items, and it is there
only when a single item has a ticket. A grouped item's row shows no ticket:
the group heading shows the group's ticket. Every ticket stays in the record
and in `show`. The PR number and a ticket with a URL are OSC 8 links when
stdout is a terminal. With `--urls`, a `Links` list at the end gives each PR
number and each ticket that the board shows, with its URL, in the order the
board shows them.

The board cleans every stored string before it prints it. It removes escape
sequences and the C0, DEL and C1 control characters, and it changes tabs and
line breaks to spaces. The JSON view holds the same cleaned strings, and no
OSC 8 sequence.

The Plan block comes from `python3 <directory of crew-orch.py>/crew-usage.py
show --json`, run only when that file exists. The command prints
`five_hour {used_pct, resets_at, full_at}` and `seven_day {used_pct,
resets_at}`. A time there is epoch seconds. The board ignores any other field.
A missing file, a non-zero exit, a run longer than 5 seconds or output that is
not that JSON gives no Plan block. It is never an error.

`board` reads the time from `$CREW_ORCH_NOW`, in epoch seconds, when it is
set. The variable is for a test alone: it pins every age and clock time of
the board. It changes no write, and each write stamps the real time.

### The board JSON

`board --json` takes no other option. With `--urls` its output is the same:
the JSON view always holds every URL. A string is the cleaned text, formatted
as the text view prints it. An age is the age string, or `""` where the text
view prints none.

| Field | Type | What it holds |
|---|---|---|
| `version` | integer | `1`. See the compatibility rule below |
| `orch` | string | the orchestrator name |
| `plan` | object or `null` | `null` when the text view prints no Plan block and no pace word |
| `plan.windows` | array | one window object per usage window, 5h first. Empty when the board has no usage figures |
| `plan.word` | string | `SLOWED: <busy> of <max> slots`, `STOPPED`, or `""` |
| `needs_you` | object | `{count, entries}`: the `Needs you` line and its rows |
| `sections` | array | one section object per open group, in the order the text view prints them, then `Single items` |
| `done` | integer | the number in `Done <count>` |
| `legend` | string | the stage legend after `stages:` in the footer |

A window object:

| Field | Type | What it holds |
|---|---|---|
| `key` | string | `five_hour` or `seven_day` |
| `label` | string | `5h` or `7d` |
| `used_pct` | integer | the percent as printed |
| `meter` | string | ten characters of `█` and `░` |
| `resets` | string | local clock text or a weekday, or `""` |
| `full_at` | string | local clock text or a weekday, or `""` |

An object of `needs_you.entries`, oldest first:

| Field | Type | What it holds |
|---|---|---|
| `id` | string | the entry id |
| `kind` | string | the kind |
| `age` | string | the age, from `routed_at` when the entry has one |
| `item` | string | `<group>/<item>`, `<item>` or `-` |
| `item_id` | string or `null` | the bare item id |
| `text` | string | the text |
| `recommend` | string or `null` | the text after `Recommended:` |

A section object:

| Field | Type | What it holds |
|---|---|---|
| `kind` | string | `group` or `single` |
| `id` | string or `null` | the group id; `null` for `single` |
| `title` | string | the group title, or `Single items` |
| `ticket` | object or `null` | the group ticket `{id, url}`; `url` is a string or `null`. Always `null` for `single` |
| `repo` | string or `null` | the group repo. Always `null` for `single` |
| `merged` | integer or `null` | `k` in `k of n merged`; `null` for `single` |
| `total` | integer or `null` | `n` in `k of n merged`; `null` for `single` |
| `rows` | array | the row objects, in the order the text view prints them |

A row object:

| Field | Type | What it holds |
|---|---|---|
| `n` | integer | the number column |
| `id` | string | the item id |
| `marks` | string | five characters of `●`, `◐` and `○` |
| `status` | string | the status word |
| `pr` | object or `null` | `{number, label, url}`; `label` is `#<number>` |
| `ticket` | object or `null` | the ticket the row shows, `{id, url}`: a single item's own ticket. Always `null` for a grouped item |
| `text` | string | the row text: `after <ids>`, `shipped`, `doing` |
| `age` | string | the age of `doing_at`, or `""` |
| `launch_tab` | string or `null` | the `launch.tab` handle: what `launcher.py focus` takes. It is not a board value |

The compatibility rule: a reader ignores a field it does not know. A new
field does not change `version`. The removal of a field, or a change in what
a field means, raises `version`. A reader that gets a `version` it does not
know shows no board.

## The commands

Each line is one command and what it does.

| Command | What it does |
|---|---|
| `init` | creates the record. A second `init` of the same name exits 1 and changes nothing |
| `item add <id> --title <t> --repo <owner/name> [--group <g>] [--ticket <id> --ticket-url <url>]` | adds an item at stage `queued` |
| `item <id> pr <number\|url>` | sets the PR. A number builds the URL from `repo`. A URL whose repo is not the item's repo exits 2, and the match ignores case. A PR with a new number clears `github` until the next `refresh` |
| `item <id> set <field> <json>` | sets `title`, `repo`, `ticket`, `group` or `launch`. A dotted key `launch.<key>` merges. Any other field exits 2. A `repo` that differs from the repo of the item's PR URL exits 2, and the match ignores case |
| `group add <id> --title <t> [--repo <r>] [--ticket <id> --ticket-url <url>]` | adds a group |
| `group <id> order <item,item,...>` | sets the merge order. Each item must exist and belong to the group |
| `group <id> owner <thing> <item>` | records the one item that owns a shared file or component |
| `stage <item> <stage> [--detail <t>] [--doing <t>]` | writes the stage and stamps `stage_at`. An unknown stage exits 2 |
| `doing <item> <text>` | writes what the item does now and stamps `doing_at` |
| `ask <item> <text>` | adds a `question` for the orchestrator and prints its id |
| `inbox add <kind> [--item <id>] <text> [--recommend <t>]` | adds an entry for the principal and prints its id |
| `route <id> principal` | moves an open entry to the principal and keeps its id |
| `answer <id> <text>` | closes an open entry with the answer. A closed entry exits 2 |
| `dismiss <id> [--reason <t>]` | closes an open entry and stores the reason in `answer` |
| `plan change <what> --reason <why> [--file <path>]` | appends to `plan_changes`. With `--file`, copies the file to `plan.md` |
| `told <item> --file <path>` | copies the message to `told/<item>-<k>.md` and appends to the item's `told`. `<k>` counts that item's `told` entries, from 1 |
| `pace set <json>` | merges the object into `pace` |
| `refresh [<item>]` | reads each item that has a PR with `gh`, and writes `github`. A failed `gh` call keeps the last values, prints one line and does not fail the command |
| `board [--urls \| --json]` | prints the board as text, or as one JSON object with `--json` |
| `show [<item>]` | prints the whole state, or one item, as JSON |
| `close` | sets `closed_at`. See "Closing the record" |

## Closing the record

`close` takes no argument. It sets `closed_at` to the time now and prints
that value on one line. A `close` of a record that is already closed exits 1
and changes nothing.

`init` writes `closed_at` as `null`. A record that has no `closed_at` key
reads as `null`, so `close` works on a record from before this key.

A closed record stays on disk as the history of the run. `close` changes no
other field, and the other commands still work on a closed record.

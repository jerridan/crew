# The orchestrator record

This file owns the orchestrator record: where it lives, every field of
`orchestrator.json`, the ids, the stages, the merge value, the board and every
command of `crew-orch.py`. No other file defines a field of it. A project
lead's reports into the record are in
`skills/project-lead/references/orchestrator-report.md`. A goal's own record
is `record-format.md`.

An orchestrator is a session that runs many goals, each under its own project
lead or, for a subagent item, under a subagent of the orchestrator. The
record is its one shared state: the items it runs, the groups
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
| `events` | the routine events, oldest first: a list of `{at, item, text}`. `item` is an item id, or `null` for a mode change. A command that handles a routine thing appends one, and the list keeps the last 50. The board shows the last 8. It is not an inbox |
| `merge_queue` | the item ids whose merge `merge --when-green` queued. `wait` runs each again when its checks pass |
| `handoffs` | the words for a live item that a script recorded and cannot send: a list of `{item, name, path, at}`. `handoff clear` removes them |
| `orchestrator_session_id` | the session id of the orchestrator, from `$CLAUDE_CODE_SESSION_ID`, or `null`. `init` and `resume` write it. The `SessionStart` hook reads it |
| `wait_owner`, `wait_pid` | the token and the pid of the one running `wait`, or `null` |
| `wait_seen_inbox` | the inbox ids that `wait` has seen. The first `wait` seeds it with the entries then open |

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
| `subagent` | `null` for an implementer item, or the object below for a subagent item. `item add` writes `null`. An item with no `subagent` key reads as `null` |
| `told` | a list of `{at, path}`. `path` is `told/<item>-<k>.md` |
| `ready` | `{sha, line, at}` of the newest ready line that `merge --ready` stored, or `null` |
| `watch` | the review and comment ids, authors and times that `wait` has seen: `{reviews, comments}`. It is the baseline of the next poll |
| `slot_released` | `true` once the item gave back its slot. It makes the release happen once |
| `words_sent` | `true` once the merge word and the rebase word went out |
| `merge_findings_answered` | `true` when `merge --when-green --findings-answered` queued the item. The queued merge keeps the flag. A failed queued merge and `finalize` clear it |
| `queued_at_github` | `true` when `gh pr merge` left the PR open in the merge queue of GitHub. `wait` never runs that merge again |
| `close_asked_at` | the time of the first `close-item` call, or `null` |
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
| `terminal` | `iterm2`, `tmux` or `herdr` |
| `tab` | `iterm2:<session unique id>`, `tmux:<pane id>` or `herdr:<terminal address>` |
| `tab_group` | a tab group name, or `null` for none |
| `session_id` | the id of the project lead's conversation, which `launcher.py resume` takes |

`subagent` is the marker of a subagent item: an item that a subagent of the
orchestrator runs, with no implementer session (`subagent-items.md`). It
holds six keys, each a string or `null`. The orchestrator writes
them.

| Key | Holds |
|---|---|
| `name` | the dispatch name, `sub-<item id>` |
| `model` | the model of the subagent |
| `worktree` | the absolute path of its worktree, written right after the dispatch from the agent id and corrected from the task notification, or `null` for work that changes no repo |
| `branch` | its branch, written with `worktree`, or `null` |
| `outcome` | one line: the result of work with no PR, or `null` |
| `ready` | the subagent's newest ready line, as it sent it, or `null` |

An item is a subagent item or an implementer item, never both. A write of a
`subagent` object or key to an item whose `launch` is not `{}` exits 2. A
write of `launch` or a `launch.<key>` to an item whose `subagent` is not
`null` exits 2. So an escalation to an implementer writes `subagent` `null`
before the launch.

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

`slots` can also hold `normal_max`: the value of `max` before a slow-down,
which `wait` restores at the reset (3 when it is not set). These commands
write `pace`: `launch` writes `slots.busy` one higher. `finalize` writes it
one lower, once for each item, and `merge` and `wait` call `finalize` ("The
sequence commands"). `resume` writes the count of live implementers. `wait`
writes `mode` and `slots.max` when the usage level changes. `pace set` is for
a change that the orchestrator decides, such as the concurrency number.

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
5. `Recent`, only when `events` is not empty: the last 8 routine events,
   each with its age, its item (`-` for a mode change) and its text.
6. `Done <count>`: the items at `shipped` or `closed` outside an open group.

An item row holds `n`, the id, the five marks, the status word, the PR number,
`doing` and the age of `doing_at`. The text of a subagent item's row starts
with `subagent`, and its `subagent.outcome`, when set, takes the place of
`doing`. A `waits on` value names the items. The text `after <ids>` shows only when
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
| `events` | array | the last 8 routine events, oldest first, each `{at, item, text, age}`. The key is absent when `events` is empty |
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
| `text` | string | the row text: `subagent`, `after <ids>`, `shipped`, and `doing` or `subagent.outcome` |
| `age` | string | the age of `doing_at`, or `""` |
| `launch_tab` | string or `null` | the `launch.tab` handle: what `launcher.py focus` takes. It is not a board value |
| `subagent` | boolean | `true` for a subagent item |

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
| `item <id> pr <number\|url\|none>` | sets the PR. A number builds the URL from `repo`. A URL whose repo is not the item's repo exits 2, and the match ignores case. A PR with a new number clears `github` until the next `refresh`. `none` sets `pr` and `github` to `null` |
| `item <id> set <field> <json>` | sets `title`, `repo`, `ticket`, `group`, `launch` or `subagent`. A dotted key `launch.<key>` or `subagent.<key>` merges. A `subagent` object takes the six keys, and a key it does not give is `null`. Any other field exits 2. A `repo` that differs from the repo of the item's PR URL exits 2, and the match ignores case |
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
| `merge`, `finalize`, `handoff clear`, `send`, `launch`, `close-item`, `digest`, `resume`, `wait` | each fixed sequence of the orchestrator, in one call. "The sequence commands" below gives each one |

## The sequence commands

Each command here runs a sequence that the orchestrator used to run by hand.
Each does the steps that need no judgment, prints one line for each, and
leaves each judgment to the orchestrator. A line is stdout. A refusal that
sets an exit code above 2 prints one stderr line, `crew-orch: <command>
<check>: <detail>`. Exit 1 is a record or tool error, and exit 2 is a usage
error, as in "How the script runs". No command sends a cross-session message
or types into a tab.

`merge`, `finalize`, `close-item`, `send` and `wait` take `--from <name>`:
the name that a word carries as its reply address. It defaults to the current
session name (the session file of `$CLAUDE_CODE_SESSION_ID` under
`~/.claude/sessions/`). It never defaults to the record name. When neither
exists, `send` and the first `close-item` call exit 2 and name `--from`.
`merge` and `finalize` then record each word as a handoff in place of a
`say`, and `wait` prints `wake send` for it. `wait` resolves the name once,
at its start.

### `merge <item> [--ready "<line>"] [--when-green] [--findings-answered] [--from <name>]`

`--ready` stores the ready line in `item.ready` before any check. The line
holds `ready <sha>`, with a hex sha of 7 to 40 characters. Without `--ready`,
the command reads `item.ready`, and for a subagent item `subagent.ready`.
The command runs `refresh`, then these checks in this order, and stops at the
first that fails:

| Order | Check | Exit | It fails when |
|---|---|---|---|
| 1 | already done | 0 | the PR reads `MERGED`: the command runs `finalize` and stops |
| 2 | `record` | 3 | the merge value is `no PR`, `conflict`, `ci failing`, `draft`, `changes requested`, `blocked` or `closed`: waiting does not fix it |
| 3 | `ready` | 4 | a ready line exists and its sha is not a prefix of `headRefOid` |
| 4 | `pending` | 11 | CI runs, the PR is in a queue, or no ready line exists. With `--when-green` the command queues the item in `merge_queue` and exits 0. With `--findings-answered` as well, it stores `merge_findings_answered` |
| 5 | `order` | 8 | an earlier item of the group order that shares a file is not merged. The check runs for the merge values `waits on` and `needs review`, so it comes before `approval` and `merge-section`. A `waits on` with no shared file exits 3 `record` |
| 6 | `threads` | 5 | a review thread is unresolved |
| 7 | `findings` | 6 | a review or comment outside a thread exists and no `--findings-answered` is given. It prints each as `finding: <author> <kind> <first 120 characters>`, and then `ready: <line>` |
| 8 | `approval` | 7 | the approval is missing, or the merge value is `needs review` and no `Merge` section exists |
| 9 | `merge-section` | 9 | a `Merge` section exists. The command prints `merge-section:` and its text, and does not merge |
| 10 | `gh` | 10 | a `gh` read fails, no method is allowed, `gh pr merge` fails, or a fresh read cannot confirm the state |

The `Merge` section comes from `.claude/crew.md` on the default branch of the
repo, then from `$CREW_CONFIG` (the machine file, `~/.claude/crew/config.md`
by default). The method is the first of rebase, squash and merge that
`gh repo view` allows. The command runs `gh pr merge --match-head-commit
<sha>`. Then it runs `finalize`.

Output lines: `merge: <item> <method> <sha12>`, then the lines of `finalize`.

### `finalize <item> [--from <name>]`

A fresh `gh pr view --json state` decides. `merge` and `wait` call it, and
the orchestrator runs it to retry after exit 10.

| State | What the command does |
|---|---|
| `MERGED` | releases the slot of an implementer item once (`slot_released`), appends the event `merged PR #<n>`, sends the merge word, and sends the rebase word to the next unfinished item of the group order that shares a file (`words_sent`). Prints `merged: <item> (PR #<n>)`, and `rebase-word: <item>` only when it sent a word. When it cannot send the word, it appends the event `rebase word needs the orchestrator after <id> merged` and prints `rebase-word-needed: <item> (the rebase word needs the orchestrator: <how>)`. `<how>` is `SendMessage to its subagent <name>` or `it has no session, so send it once it has one`. The orchestrator then sends the rebase word itself |
| `OPEN` | the merge queue of GitHub holds the PR. Prints `queued: <item> (...)`, sets `queued_at_github`, and adds the item to `merge_queue` |
| `CLOSED` | releases the slot once, appends an event and sends no word. Prints `closed: <item> (...)` |

A subagent item gets no word and has no slot. A delivered item gets each word
by `window-watch.py say` (`said: <item>`). A live item gets its word recorded
in `handoffs`, and the command prints `send-to: <session name>` and `told:
<path>`. The orchestrator then sends it with one `SendMessage`, and runs
`handoff clear <item>`. A read that fails keeps the item in `merge_queue` and
exits 10.

### `handoff clear <item>`

Removes the `handoffs` of the item and prints `cleared: <n>`.

### `send <item> (--text <t> | --file <p>) [--from <name>]`

Records the message as `told` does. For a delivered item, it delivers it by
`window-watch.py say`, and prints `said: <item>`. For an item with a live
project lead, it prints `send-to: <session name>` and `told: <path>`: the
orchestrator then sends the text with one `SendMessage` to that name. A
delivered item takes one call, and a live item takes two. Exit 2 gives
neither or both of `--text` and `--file`, or no session name and no `--from`.
Exit 1 gives a subagent item, or an item with
no session name.

### `launch <item> [--model <m>] [--group <g>] [--terminal <t>] [--principal <name>] [--goal-file <p>] [--wait-seconds <n>]`

Runs `launcher.py start` for the item, with the worktree path, the settings
value of `crew-usage.py settings`, and the session name. The session name is
the item id with `_` changed to `-`. `--principal` is the orchestrator's
current session name. Without it, the command finds the name from the session
file of `$CLAUDE_CODE_SESSION_ID`. It stores the start output in `launch`,
writes `pace.slots.busy` one higher, and records `--goal-file` as the first
`told` entry. Then it waits up to `--wait-seconds` (60 by default) for a
session file that names the implementer. It prints the launcher line, then
`goal-ready: <session name>` or `goal-wait: <reason>`. The orchestrator sends
the goal on `goal-ready`.

Exit 3 prints `launch refused: <why>` when `pace.mode` is not `normal` or no
slot is free. Exit 1 gives a failed `start` or settings call, no `Checkouts`
line for the repo, no principal name, or an item that has a launch or a
`subagent`.

### `close-item <item> [--continue] [--stop-processes] [--from <name>]`

The first call sends the processes word, by `say` for a delivered item or as
the `send-to:` and `told:` lines of `send`, and writes `close_asked_at`. A
subagent item gets no word. With no session name and no `--from`, the
first call exits 2.

`--continue` runs the stop, the removal and the ticket check, and prints one
line for each: `stop: ...`, `remove: ...`, `kept-process: <pid> <command>` for
each process that kept the worktree, `notice: <id> <text>` for each notice it
added, and `ticket: ...`. `remove` gets `--delete-branch --pr <n>` for a
merged item, `--delete-branch` for an item with no PR, and neither otherwise.
A subagent item gets no `stop`, and its removal reads `subagent.worktree`.
With no `subagent.worktree` and a `subagent.branch`, the command removes and
deletes nothing and adds one notice that names the branch.
A failed `stop` skips the removal and adds a notice. A GitHub ticket closes
only when the item landed. `--stop-processes` goes with `--continue` only,
and tells `remove` to stop the kept processes. Without `--continue` it exits
2. A refusal for kept processes exits 0.

### `digest <item> [--diff-file <p>]`

Runs `refresh` and prints the facts that the merge judgment needs, one block:
`brief:` (the first `told` entry, cut to 600 characters), one `file: <path>
+<added> -<deleted>` line per changed file, `threads: <n> unresolved`, one
`finding:` line per review or comment outside a thread, `ci:`, `shared with
<item>: <files>` for each other open PR of the group, and `order:`. With
`--diff-file`, it writes the file with a `# Brief` part and a `# Diff` part
and prints `diff-file: <p>`. Exit 10 gives a failed `gh` call.

### `resume [--read-only]`

Runs the mechanical steps of the resume of `resume-and-close.md`. Its
`launcher.py find` call for each item carries `--terminal <launch.terminal>`
when the item stores one. It prints one line for each item, `<item> <action>:
<detail>`, and the orchestrator does what the action says:

| Action | The detail says |
|---|---|
| `rejoin` | the implementer is alive, or the command resumed it. Send the rejoin message |
| `send-goal` | the implementer is alive, but `told` holds no goal. Send the goal |
| `restart` | a session matches by id only. The line gives the `launcher.py stop` command. Then resume it |
| `resume` | read-only only: the implementer is gone and its worktree exists. Run `resume` |
| `notice` | a session matches by working directory only, or the worktree is gone, or a tool failed. A failed `launcher.py find` prints `<item> notice: <error>; add a notice or run find`, and the command goes on to the next item. Add a notice. Never stop a session that matches by working directory only |
| `window` | the item is delivered. The command ran `window-watch.py ensure` (not with `--read-only`). Reach it with `send` |
| `launch` | the item has no launch. Run `launch` |
| `close` | the item is `shipped` or `closed`. The command ran `launcher.py find` and wrote a changed `launch.tab`. The line says `alive at <handle>`: run `close-item <item>`, then `--continue` after its answer. Or it says `its session is gone`: run `close-item <item> --continue` |
| `subagent` | a subagent item. The line says what its stage needs |
| `ok` | nothing to do |

A closed record prints one line, `closed: ...`, and nothing else. Without
`--read-only`, the command also resumes each gone implementer whose worktree
exists, writes `launch.tab` when a handle moved (also for an item at `shipped`
or `closed`), writes `pace.slots.busy` (the
count of implementers that are alive, resumed or delivered, at a stage before
`merged`), and stores `orchestrator_session_id`. With `--read-only` it writes
nothing and starts nothing. The `SessionStart` hook (`hooks/session-start.py`)
runs `resume --read-only` for the open record whose `orchestrator_session_id`
is the session's, at the start of a compaction or a resume, and prints the
lines as context.

### `wait [--interval <seconds>] [--polls <n>] [--from <name>]`

A loop with no model. The orchestrator runs it as a background Bash command,
and its exit is the wake. It polls every `--interval` seconds (60 by default).
`--polls <n>` ends the loop after `n` polls with no event, with exit 0 and no
output. It is for a test.

Each poll: it runs `crew-usage.py check`, runs `refresh` on each item with a
PR, runs a queued merge whose checks now pass (`merge <item> --when-green`),
finalizes a PR that reads `MERGED` or `CLOSED`, and reads the inbox. It writes
`pace.mode`, `pace.slots.max`, `events`, `github`, `watch` and
`wait_seen_inbox` itself. It wakes the orchestrator only for an event in the
table. A red check, a conflict, a new comment and a new review with words
on an implementer item (an item with a `launch`, not in `merge_queue`) are
board events and wake nobody: the implementer handles them. They still wake
for a subagent item and for an item in `merge_queue`. A PR that enters the
merge queue is a board event for every item. On a wake it prints one line for
each event and exits 0:

| Line | When |
|---|---|
| `wake usage -: level=<level> was=<old> <check tail>` | the level rises to `slowed` or `stopped`. At `slowed` it writes `slots.max` 1 |
| `wake usage -: reset level=normal was=<old> <tail>` | the level returns to `normal`. It restores `slots.max` |
| `wake check <item>: failed <names>` | a check turned red |
| `wake conflict <item>: ...` | the PR has a conflict |
| `wake review <item>: approved` | `reviewDecision` turned `APPROVED`: a human approval, which no implementer reports |
| `wake review <item>: <author> <state> <text>` | a new review |
| `wake comment <item>: <author> <text>` | a new comment by someone other than the PR author |
| `wake queue <item>: left the queue` | the PR left the merge queue and is still open |
| `wake closed <item>: PR #<n> closed with no merge; its slot is released` | the PR closed |
| `wake merge-failed <item>: exit <code> <line>` | a queued merge failed a check other than `pending`. The item leaves `merge_queue` |
| `wake inbox <item\|->: <id> <text>` | a new open entry with `for: orchestrator` |
| `wake send <item>: send-to <name> told <path>` | a handoff waits. It repeats at each `wait` until `handoff clear` runs |

A step down from `stopped` to `slowed`, a re-check with no change, and a
queued merge that went through wake nobody. The first poll of an item with no
stored `github` or `watch` is a baseline and wakes nobody, so the
orchestrator reads the known state (`board`, `refresh`) before it runs
`wait`. A second `wait` on the same record stops the first: `wait_owner` holds
the token, and each write of the older one checks it. The command stops an
older `wait` process only when its command line names this record with
`--orch`. `wait` exits 2 on a bad
argument.

## Closing the record

`close` takes no argument. It sets `closed_at` to the time now and prints
that value on one line. A `close` of a record that is already closed exits 1
and changes nothing.

`init` writes `closed_at` as `null`. A record that has no `closed_at` key
reads as `null`, so `close` works on a record from before this key.

A closed record stays on disk as the history of the run. `close` changes no
other field, and the other commands still work on a closed record.

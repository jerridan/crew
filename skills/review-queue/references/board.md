# The board file

The queue session writes the board file, and the review-board mod reads it.
The mod writes the asks file, and the queue session reads it. This file owns
the path and schema of both files, and the terms their readers derive from
them. `crew:review-queue`'s "The board" owns when the queue session writes
the board file.

## The path

`<record-root>/queue/board.json`. `<record-root>` is `$CREW_RECORD_ROOT` when
that variable is set, and `~/.claude/crew` otherwise.

## The schema

One JSON object:

```
{
  "version": 1,
  "owner": { "session_id": "<string>", "since": "<ISO-8601 UTC>" },
  "updated_at": "<ISO-8601 UTC>",
  "asks_through": "<ISO-8601 UTC>" | null,
  "watches": [
    { "id": "<string>", "source": "slack:#<channel>" | "github:review-requests" | "direct",
      "policy": "assist" | "review", "status": "active" | "stopped",
      "since": "<ISO-8601 UTC>", "last_checked": "<ISO-8601 UTC>" | null, "found": <integer> }
  ],
  "rows": [
    { "repo": "<owner>/<name>", "pr": <integer>, "title": "<string>", "author": "<login>",
      "stage": "new" | "triage" | "reviewing" | "fixing" | "rereview" | "approve" | "queued" | "merged" | "blocked" | "closed",
      "next": "you" | "crew" | "author" | "ci" | "queue" | "-",
      "head": "<sha>" | null, "last": { "at": "<ISO-8601 UTC>", "text": "<string>" },
      "url": "<string>", "watch": "<watch id>" | null, "policy": "assist" | "review" }
  ]
}
```

`owner.session_id` is the session id of the queue session that owns the
file. `asks_through` is the `found_at` of the newest asks-file entry that
the queue session took. The queue session writes it. A board with no
`asks_through` field reads as `null`. `found` counts the asks the watch
found since `since`. `last` is the row's latest event. `watch` is the id
of the watch that found the row. A direct ask belongs to the watch with the
id `direct`.

## Derived terms

- A row is **done** when its `stage` is `merged` or `closed`.
- A row **needs you** when its `next` is `you`.
- A row is **blocked** when its `stage` is `blocked`.
- A row is **active** when it is neither done nor blocked.
- "Watching N" counts the watches whose `status` is `active`.
- "Newest" orders by `last.at`, latest first.
- Stage order is the order of the `stage` list above.
- A row's identity is `repo` plus `pr`.

## The asks file

`<record-root>/queue/asks.json`. The review-board mod writes it, in the
queue session that owns the board, when `~/.claude/secrets/slack-token`
holds a Slack token. The queue session reads it, and never writes it.

```
{
  "version": 1,
  "updated_at": "<ISO-8601 UTC>",
  "watches": { "<watch id>": { "last_checked": "<ISO-8601 UTC>", "found": <integer> } },
  "asks": [
    { "repo": "<owner>/<name>", "pr": <integer>, "url": "<string>",
      "title": "<string>" | null, "author": "<login>" | null,
      "watch": "<watch id>",
      "slack": { "channel": "<id>", "ts": "<string>" } | null,
      "found_at": "<ISO-8601 UTC>" }
  ]
}
```

An entry is one PR in one Slack message, or one GitHub review request. A
Slack message with two PR links gives two entries. A GitHub entry has
`slack: null`. Each new `found_at` is later than every `found_at` the file
held, to the millisecond. `found` counts the entries the mod wrote for that
watch since the watch's `since`. The mod writes the whole file to a temp
file in the same directory, then moves it over `asks.json`.

- An entry is **untaken** when its `found_at` is later than the board's
  `asks_through`, or when `asks_through` is `null`.
- **The prune rule.** At each poll, the mod removes every entry with a
  `found_at` at or before `asks_through`.
- The queue session takes each untaken entry. It writes the rows these
  entries made and `asks_through` in one board write.

The pane draws an untaken entry whose PR has no row as a **derived row**.
Two or more such entries for one PR draw one derived row, from the earliest
entry. A derived row counts as an open row, in the pane and in the status
line:

| Field | Value |
|---|---|
| `repo`, `pr`, `url`, `watch` | from the entry |
| `title` | the entry's `title`, or `""` when it is `null` |
| `author` | the entry's `author`, or `-` when it is `null` |
| `stage`, `next` | `new`, `crew` |
| `head` | `null` |
| `last` | `at`: the entry's `found_at`; `text`: `new ask from <watch id>` |
| `policy` | the policy of the watch named by `watch`, or `review` when no such watch exists |

When a watch's `last_checked` in the asks file is later than its
`last_checked` in the board file, the pane shows the asks file's
`last_checked` and `found`.

The mod moves a watch's `last_checked` in the asks file only after a good
poll of that watch. A watch is **stale** when it has `status: active` and its
`last_checked` in the asks file is missing or more than 5 minutes before now.
A stopped watch is never stale. A stale watch means the mod does not poll it.
The queue session polls a stale watch itself.

**With no token**, the mod polls no source and writes no `asks.json`. The
queue session polls every source in its wakeup loop. The pane shows
`no token: the queue session polls` under Watching.

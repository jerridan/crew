# The board file

The queue session writes the board file, and the review-board mod reads it.
This file owns the board's path, its schema and the terms both readers
derive from it. `crew:review-queue`'s "The board" owns when the queue
session writes it.

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
file. `found` counts the asks the watch found since `since`. `last` is the
row's latest event. `watch` is the id of the watch that found the row. A
direct ask belongs to the watch with the id `direct`.

## Derived terms

- A row is **done** when its `stage` is `merged` or `closed`.
- A row **needs you** when its `next` is `you`.
- A row is **blocked** when its `stage` is `blocked`.
- A row is **active** when it is neither done nor blocked.
- "Watching N" counts the watches whose `status` is `active`.
- "Newest" orders by `last.at`, latest first.
- Stage order is the order of the `stage` list above.
- A row's identity is `repo` plus `pr`.

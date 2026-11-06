# Who owns the board

This file owns the rule for who holds the board: the takeover, the takeover
time, "The owner check", the `owner.since` of each write, and the removal of
the takeover-time file. `board.md` owns the schema of `owner`. `SKILL.md`
points here at each step that needs the rule.

## The takeover

At "Start" step 1, take the board. Always take it. Set `owner.session_id` to
`$CLAUDE_CODE_SESSION_ID` and `owner.since` to the output of
`date -u +%Y-%m-%dT%H:%M:%SZ`. That value is your **takeover time**. Write
it, as one line, to `<queue-dir>/owner-$CLAUDE_CODE_SESSION_ID`, because a
compaction can lose a value that only your context holds. Keep the existing
watches and rows. When the board named another non-empty session id, tell
the principal in one line which session id you took the board from. Ask
nothing.

The mod never reads the takeover-time file.

## The owner check

Run it at step 0 of each wakeup-loop run, before a direct ask's triage,
before each action that the principal's answer starts, and before each board
write after your own "Start".

Read `owner` from the board. Read your takeover time from
`<queue-dir>/owner-$CLAUDE_CODE_SESSION_ID`. When that file is missing or
empty, you cannot prove that you took the board last. Treat yourself as the
old session.

Order owners by `owner.since`. The `since` value has a precision of one
second, so two sessions can take the board in the same second. Break that
tie by the session id: the lexically greater id is the later owner. The mod
uses the same order.

- `owner.session_id` is yours, or empty: go on.
- Another session owns the board and is the later owner, or you have no
  takeover time: a new queue session took the board, and this one is the
  old session. Do not write. Delete the cron job of your wakeup loop, the
  job that "Start" step 3 arms, with `CronList` and `CronDelete`. Tell the
  principal in one line. Stop.
- Another session owns the board and is not the later owner: an earlier
  owner wrote over your takeover. Take the board again. Set
  `owner.session_id` to yours and `owner.since` to your takeover time, and
  keep the rows. Tell the principal in one line. Go on.

## Each board write

Each write of the board sets `owner.session_id` to yours and keeps
`owner.since` at your takeover time, from the takeover-time file. Never set
`owner.since` to the time of the write: a later value makes the new owner
stop.

## At close

When the principal closes the queue, remove
`<queue-dir>/owner-$CLAUDE_CODE_SESSION_ID`. A queue session that is not
closed leaves its file, as it leaves its other files in `<queue-dir>`.

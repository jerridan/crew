# The polls of a source

`skills/review-queue/SKILL.md`'s "Sources" sends the queue session here. The
polls below run for an active watch with no token, and for a stale watch.

**Slack.** For a poll below, read a channel through this session's Slack MCP
connector. Always set a reaction through the connector, because the token
has read scopes only. Find the connector at run time with `ToolSearch`:
one tool that reads a channel's history, and one that adds a reaction.
**With no such connector, a `slack:` watch cannot start**, with a token or
without one. Tell the principal so, and add no watch. Each poll reads the
messages after `last_checked`. Each message that holds a PR URL is an ask.
Keep the channel and the message timestamp on the ask, for its reactions.
One message can carry two PRs, and each PR is an ask.

**GitHub review requests.** Each poll runs:

```bash
gh search prs --review-requested=@me --state=open --limit 100 --json number,repository,url,title,author
```

Each PR that has no row is an ask.

**Direct.** The principal's message is the ask. It needs no poll.

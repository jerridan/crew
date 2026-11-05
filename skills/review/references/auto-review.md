# Read the repo's review bot

`skills/review/SKILL.md`'s "Adjudicate" runs this on every round.

The bot's login is the one in the `Auto-review` section. This command prints
one line per review the bot posted on the PR. The last line is its most
recent:

```bash
gh api --paginate repos/<owner>/<repo>/pulls/<n>/reviews --jq '.[] | select(.user.login == "<login>") | [.id, .state, .commit_id] | @tsv'
```

Read that review's body, then its inline comments:

```bash
gh api repos/<owner>/<repo>/pulls/<n>/reviews/<id> --jq .body
gh api --paginate repos/<owner>/<repo>/pulls/<n>/comments --jq '.[] | select(.pull_request_review_id == <id>) | {id, path, line, body}'
```

An issue comment by the bot is not a review, and you do not read it.
Compare the review's `commit_id` with `run.review_pending.head`. **A review
on an older head is stale**: the ledger header's `Auto-review:` line says
so, and no claim comes from it. On the current head, a claim is a finding
the bot marked blocking.
When the review's `state` is `CHANGES_REQUESTED`, every finding in its body
and every inline comment is a claim. Otherwise only an item whose text holds
`[blocking]` is a claim.

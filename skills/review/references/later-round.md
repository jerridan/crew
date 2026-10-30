# A later round's head and base

`skills/review/SKILL.md`'s "Review" runs this on every round after the first,
before the launch. Every file this one names is in
`skills/project-lead/references/`.

**Get the head first.** On every round after the first, bring `run.checkout`
to the new head. Run every command with `git -C <run.checkout>`. On a
same-repository PR:

```bash
git fetch origin <headRefName> <baseRefName>
git switch <headRefName>
git reset --hard origin/<headRefName>
```

Run the reset only in `run.checkout`, and only after the switch put it on
`<headRefName>`. Git refuses the switch on a dirty tree: escalate. On a
cross-repository PR:

```bash
git fetch origin <baseRefName>
git fetch origin pull/<n>/head
git switch --detach FETCH_HEAD
```

**Find the base of a later round.** It is the head the previous round
reviewed, the `Reviewed:` line of `reviews/skeptical-r<n-1>.md`, only when
the round resumes the session of round `<n-1>`, and both of these hold. The
new head is `run.review_pending.head`:

```bash
git merge-base --is-ancestor <previous head> <new head>
git merge-base <new head> origin/<baseRefName>
```

The first exits 0, and the second prints the deliverable's `base`. Otherwise
the base is the new merge base that the second prints, and the round's range
is the whole PR diff again. A round that is not resumed takes that merge base
too, for every fresh-launch reason that `review-runner.md`'s "Resume the
reviewer" names. A fresh reviewer has no context from the earlier rounds, so
its range is the whole PR. Part 5 of "Reviewer instructions" says what the
reviewer reads first. Write the base to the deliverable before the launch:

```bash
python3 <project-lead-dir>/scripts/crew-record.py <record-dir> deliverable d1 set base '"<new merge base>"'
```

A new base owes a new baseline. `skeptical-review.md`'s launch step 4 writes
it again at that base, before the round.

A resume that fails after this write launches fresh, and that launch first
does the recompute that `review-runner.md`'s "Resume the reviewer" names.

These two checks cover the two cases a fast-forward cannot: a force-push
fails the first, and an "Update branch" merge fails the second.

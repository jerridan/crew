# A later round's head and base

`scripts/review-run.py` runs this on every round after the first, before the
launch (`skills/review/SKILL.md`'s "Review"). This file owns the rule, and the
script does the work. Every file this one names is in
`skills/project-lead/references/`.

**Get the head first.** On every round after the first, the script moves
`run.checkout`, the review worktree, to the new head, detached.
`--discard-changes` is right on this worktree (`review-runner.md`'s "Never
review in the run's own checkout" says why), so a dirty tree is no reason to
escalate. On a same-repository PR, it fetches the head and the base ref. On a
cross-repository PR, it fetches the base ref and `pull/<n>/head`. A fetch that
fails prints a `notice:` line, and the round goes on with the commits it has.

**Find the base of a later round.** It is the head the previous round
reviewed, the `Reviewed:` line of `reviews/skeptical-r<n-1>.md`, only when
the round resumes the session of round `<n-1>`, and both of these hold. The
new head is `run.review_pending.head`. The first check is `git merge-base
--is-ancestor <previous head> <new head>`, and it exits 0. The second is `git
merge-base <new head> origin/<baseRefName>`, and it prints the deliverable's
`base`. Otherwise
the base is the new merge base that the second prints, and the round's range
is the whole PR diff again. A round that is not resumed takes that merge base
too, for every fresh-launch reason that `review-runner.md`'s "Resume the
reviewer" names. A fresh reviewer has no context from the earlier rounds, so
its range is the whole PR. The later-round block
(`reviewer-blocks/later-round.md`) says what the reviewer reads first. The
script decides whether the round resumes and finds the base together, and it
writes the base to the deliverable (`crew-record.py deliverable <id> set base`)
before it renders the instructions file and the resume prompt. A resume that
fails after this write launches fresh, and that launch first does the
recompute that `review-runner.md`'s "Resume the reviewer" names.

These two checks cover the two cases a fast-forward cannot: a force-push
fails the first, and an "Update branch" merge fails the second.

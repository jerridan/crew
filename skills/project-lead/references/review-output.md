# Review output

Every crew review agent reports in this shape: `crew:spec-critic` and
`crew:split-critic`. So does the skeptical review of the finished diff, which
is a headless process and not an agent (`skeptical-review.md`).
This file owns the shape. A reader of this file keeps no copy of it.

The project lead injects this file whole into every review dispatch, and into
the skeptical review's instructions file (`skeptical-review.md`). A path would
not resolve: a reviewer's cwd is the target repo, not the plugin.

This file owns the format and nothing else. What a reviewer looks for, and
the stance it takes, belong to its own agent definition or to
`skeptical-review.md`.

## Severity tags

Tag each finding with one of:

- `[Critical]` — blocks the project lead's next step. Each agent states what
  that step is. The artifact cannot be used as written: a requirement is
  wrong or missing, an invariant is broken, a check fails. A gap the next
  step can absorb — an enumeration that misses an item, a wording that a
  reader would still act on correctly — is not blocking. Tag it `[Concern]`.
  Each `[Critical]` costs a full round of the artifact's author and of you
  (design §15.50).
- `[Concern]` — likely to cause a problem; should be addressed.
- `[Nit]` — minor, take it or leave it.

A check that passes needs no severity tag. Tag only `[Critical]`, `[Concern]`
and `[Nit]` findings — the ones that need attention.

## Cannot verify

When you cannot confirm a check from what you were given, write `Cannot verify
from <source>` for that check instead of guessing. Name the source you lacked:
the spec, the plan, the diff, the checkout. Never guess, and never mark the
check as passed. Leave it for the project lead.

## You report. You do not fix.

Your job ends at findings. Never edit the artifact you review. When the fix is
obvious, name it inside the finding and stop there.

A finding the project lead cannot act on without asking you a question is not
finished. Quote the exact line, file or name it sits on.

## Return path

Your dispatch names an absolute path under the record's `reviews/`. Write
your whole report there. Then make your final message exactly four lines, in
this order, and nothing else — `SKILL.md`'s "Every dispatch is named" says
where the project lead reads it from:

```
Wrote: <the absolute path>
Findings: <n> critical, <n> concern, <n> nit
Verdict: <one of your two verdict strings>
Critical count: <n>
```

The project lead's context is the most expensive place in the run, and a
full report there is read on every later turn (design §15.50).

When the write is denied, your final message is the whole report. Say so in
its first line and name the denied path. Never say you wrote a file you
could not write.

**This fallback is for a dispatched agent**, whose final message the project
lead reads. The skeptical review is a separate process with no caller, so
nothing it prints to the terminal is collected — except its last message,
which `--output-format json` saves into the result JSON's own `result` field,
and which is what a denied report write falls back to there
(`skeptical-review.md`).

You carry no `SendMessage`, so a finding you leave out of the report reaches
nobody.

## The two verdict lines

End your report file with the same two lines that end your final message:

```
Verdict: <one of your two verdict strings>
Critical count: <n>
```

Your own agent definition names your two verdict strings, and
`skeptical-review.md` names the skeptical review's. Use one of those two word
for word. Always include the critical count, even when it is zero.

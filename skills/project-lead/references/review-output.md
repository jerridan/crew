# Review output

Every crew review agent reports in this shape: `crew:spec-critic`,
`crew:split-critic`, `crew:package-reviewer` and `crew:deliverable-reviewer`.
This file owns the shape. An agent that reads it keeps no copy of it.

The project lead injects this file whole into every review dispatch. A path
would not resolve: a review agent's cwd is the target repo, not the plugin.

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
your whole report there. Then make your tool result exactly four lines, in
this order, and nothing else:

```
Wrote: <the absolute path>
Findings: <n> critical, <n> concern, <n> nit
Verdict: <one of your two verdict strings>
Critical count: <n>
```

The project lead's context is the most expensive place in the run, and a
full report there is read on every later turn (design §15.50).

When the write is denied, your tool result is the whole report. Say so in
its first line and name the denied path. Never say you wrote a file you
could not write.

You carry no `SendMessage`, so a finding you leave out of the report reaches
nobody.

## The two verdict lines

End your report file with the same two lines that end your tool result:

```
Verdict: <one of your two verdict strings>
Critical count: <n>
```

Your own agent definition names your two verdict strings. Use one of those two
words for word. Always include the critical count, even when it is zero.

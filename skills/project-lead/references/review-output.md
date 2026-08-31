# Review output

Every crew review agent reports in this shape: `crew:spec-critic`,
`crew:split-critic`, `crew:package-reviewer` and `crew:deliverable-reviewer`.
This file owns the shape. An agent that reads it keeps no copy of it.

The project lead injects this file whole into every review dispatch. A path
would not resolve: a review agent's cwd is the target repo, not the plugin.

## Severity tags

Tag each finding with one of:

- `[Critical]` — blocks the project lead's next step. Each agent states what
  that step is.
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

Your findings return only as this agent's tool result. You carry no
`SendMessage`, so a finding you leave out of the report reaches nobody.

## The two verdict lines

End your report with exactly two lines, in this order:

```
Verdict: <one of your two verdict strings>
Critical count: <n>
```

Your own agent definition names your two verdict strings. Use one of those two
words for word. Always include the critical count, even when it is zero.

# Review output

Every crew review agent reports in this shape: `crew:spec-critic` and
`crew:split-critic`. So does the skeptical review of the finished diff, which
is a headless process and not an agent (`skeptical-review.md`).
This file owns the shape. A reader of this file keeps no copy of it.

The project lead injects this file whole into every review dispatch, and into
the skeptical review's instructions file (`review-runner.md`). A path would
not resolve: a reviewer's cwd is the target repo, not the plugin.

This file owns the format and nothing else. What a reviewer looks for, and
the stance it takes, belong to its own agent definition or to
`skeptical-review.md`.

## Severity labels

Put this line after the title of every finding, on its own line:

```
Severity: blocking | suggestion | nit | unsure
```

`Severity:` is the label you propose for the finding. `severity-rubric.md`
defines the four labels, and your dispatch carries its definitions. When
your own definition says what `blocking` means for your artifact, that
meaning wins. Each `blocking` finding costs a full round of the
artifact's author and of the project lead (design §15.50). A gap the next
step can absorb is not blocking.

A check that passes is not a finding, so it gets no label.

The project lead labels each finding again, and its label decides the
action. `skills/review/references/github-review.md` owns the rule that maps a
label to its action on a review run, and `skills/project-lead/SKILL.md` owns
it on a goal run.

### One optional line a dispatch can require

When your dispatch asks for it, put this line after the `Severity:` line:

```
Pre-existing: yes | no
```

`Pre-existing:` says whether the defect sits in code that the change did not
add, change or aggravate. A dispatch that does not ask for it gets reports
without it.

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
Findings: <n> blocking, <n> suggestion, <n> nit, <n> unsure
Verdict: <one of your two verdict strings>
Blocking count: <n>
```

The project lead's context is the most expensive place in the run, and a
full report there is read on every later turn (design §15.50).

When the write is denied, your final message is the whole report. Say so in
its first line and name the denied path. Never say you wrote a file you
could not write.

**This first-line rule is for a dispatched agent, and the skeptical review is
exempt from it.** Its own instructions give it a different first line —
`Reviewed: <sha>`, the same line an unimpeded report opens with — and
`review-runner.md`'s check 4 reads that line whichever way the report
reached it. Follow whichever first-line rule the dispatch you are reading
actually states.

**This fallback is for a dispatched agent**, whose final message the project
lead reads. The skeptical review is a separate process with no caller, so
nothing it prints to the terminal is collected — except its last message,
which `--output-format json` saves into the result JSON's own `result` field,
and which is what a denied report write falls back to there
(`review-runner.md`).

You carry no `SendMessage`, so a finding you leave out of the report reaches
nobody.

## The three closing lines

End your report file with these three lines. The skeptical review has no
four-line return, and it ends its report with them too:

```
Findings: <n> blocking, <n> suggestion, <n> nit, <n> unsure
Verdict: <one of your two verdict strings>
Blocking count: <n>
```

The last two of the three lines are the verdict pair: `Verdict:` and
`Blocking count:`. Your own agent definition names your two verdict
strings, and `skeptical-review.md` names the skeptical review's. Use one of
those two word for word. Always include every count, even when it is zero.

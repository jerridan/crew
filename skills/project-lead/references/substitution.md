# A step the principal replaced

The principal can name another reviewer for a review step, in plain
language: "use Codex for the spec review". Two steps take a replacement, and
no other step does — the spec critic, and the skeptical review (design
§15.94d). `SKILL.md`'s "Take the goal" resolved each one from five sources
and recorded it in `run.substitutions_requested`; this file runs it.

## What the replacement is told

Give the replacement what the step's own reviewer would have had:

| The step | What the replacement gets |
|---|---|
| spec critic | the whole body of `agents/spec-critic.md` below its frontmatter, `review-output.md` whole, and the absolute paths of `spec.md` and `charter.md` |
| skeptical review | the instructions file `review-runner.md` has you assemble, which already carries `review-output.md`, plus the branch at `run.review_pending.head` and the base ref |

**The spec critic's whole body, never the seven checks alone.** The scope
limit, the over-specification checks, the rule against a re-spec for one
missed item and the two verdict strings all sit around those checks, and a
replacement given the checks by themselves loses every one of them.

**Add one sentence, and only this one**: it tells the replacement to return
the complete report as its output. For the skeptical review that sentence
**overrides** the two instructions in `review-runner.md`'s block that tell
the reviewer to write the report file itself and to return nothing by any
other path. It overrides them for the replacement alone, and the block is
otherwise unchanged. Write the whole of what you assembled to
`<record-dir>/reviews/<prefix>-r<n>-instructions.md`, the shape
`review-runner.md` already defines for its own file.

**`<prefix>` is the step's file prefix, and the step name is not always it:**

| The step | `<prefix>` |
|---|---|
| `spec-critic` | `spec-critic` |
| `skeptical-review` | `skeptical` |

Every file this file names uses `<prefix>`, so a substituted skeptical
review writes the same names the rest of the run already looks for
(`record-format.md`, and `skeptical-review.md`'s resume list).

## Running it

The runner is a separate program, so the prompt goes in on stdin and the
output comes back on stdout:

```
codex exec --sandbox read-only -C <run.repo, or the review worktree> - \
  < <record-dir>/reviews/<prefix>-r<n>-instructions.md \
  > <record-dir>/reviews/<prefix>-r<n>-result.txt; \
  echo $? > <record-dir>/reviews/<prefix>-r<n>-result.exit
```

**The exit file goes in the same shell line as the command.** `$?` holds the
runner's status only until the next command runs, and a status you keep in
your own context is lost with the session.

Two rules hold whatever the runner is. **Run it from a git repository** —
`run.repo` for a spec review, and the detached worktree `review-runner.md`
cuts for a skeptical review. And **never put the instructions inside a
double-quoted shell string**: they are markdown, and one backtick in them ends
the command.

**`-result.txt` and `-result.exit` sit where `-result.json` would.** A
skeptical review the Claude runner ran saves its own JSON output; a
replacement saves the runner's output as text and its status beside it, under
the round's name, and a retry retires all of them the same way
(`record-format.md`). A resumed session reads the same list in
`skeptical-review.md`'s "Resume in the delivered window", with those two files
standing in for `-result.json` wherever entries 11 and 12 name it. **A
`-result.txt` with no `-result.exit` is an incomplete attempt**: the shell
never reached the status write, so entry 11's rule holds — retire the attempt
and retry the round.

## The lifecycle holds; three checks change

`skeptical-review.md` owns that step whole, and `review-runner.md` owns its
mechanics. A replacement changes none of it: the detached worktree, the
pending head, the round reserved before the review starts, the `Reviewed:`
first line, the two verdict lines, the one retry on a failure, and the
adjudication that clears `review_pending`. Three of the four checks in
`review-runner.md`'s "Check the review before you read it" are the Claude
runner's own. Map them:

| The Claude runner | Any other runner |
|---|---|
| exit 0, with `is_error` false | the runner's own exit status, read from `-result.exit` |
| `permission_denials` empty | `denials_ok: "not applicable: <runner>"` |
| `--session-id`, appended to `run.review_session_ids` | write no session id; the cost goes in the substitution entry's `usage` |

The other two checks hold word for word for every runner: the report file
exists, and its last two lines are the verdict pair while its first line is
`Reviewed: <sha>`, matching `run.review_pending.head`.

**A substituted skeptical review still writes `run.review_results[<round>]`**,
because that entry is what lets a later session adjudicate the report. `exit`
is the runner's exit status, `denials_ok` is the string above, and `report_ok`
is the report check. Nothing else about the round changes.

## You write the report file

The replacement returns the whole report as its output, and nothing writes the
file for you. Read `<prefix>-r<n>-result.txt` and write the report to
`reviews/<prefix>-r<n>.md` — `<n>` one more than the highest on disk for a
spec review, and the round `skeptical-review.md` reserved for a skeptical
one. Open it with `Reviewed: <sha>` when the runner
did not, and put `Source: <runner> output` on the next line. A spec review
reads no sha, so it carries the source line alone. End the report with the
step's own verdict pair — `ready to split` or `re-spec needed` for the spec
critic, `accepted` or `patch round needed` for the skeptical review.
Adjudicate the findings as you adjudicate any review's. Nothing else in the
run changes.

**Log every invocation, retries included.** One entry in
`run.steps_substituted` per run of the replacement: the step, the round, the
principal's own words for it, the time, and a `usage` object holding what the
runner reported. `record-format.md` owns the field.

## One worked example

The principal types "use Codex for the spec review" at launch, and "Take the
goal" writes that to `run.substitutions_requested`. At `SKILL.md`'s "Have
the spec reviewed" you assemble the instructions, then run Codex in place of
`crew:spec-critic`:

```
codex exec --sandbox read-only -C <run.repo> - \
  < <record-dir>/reviews/spec-critic-r1-instructions.md \
  > <record-dir>/reviews/spec-critic-r1-result.txt; \
  echo $? > <record-dir>/reviews/spec-critic-r1-result.exit
```

Write the report to `reviews/spec-critic-r1.md`, and append the entry:

```
{"step": "spec-critic", "round": 1, "replacement": "use Codex for the spec review",
 "at": "2026-09-16T10:04:00Z", "usage": {"tokens": 41233}}
```

**Two harness limits.** The `Skill` tool is auto-rejected under `claude -p`
(design §12), so a replacement cannot invoke a slash command from inside a
headless session. A slash command passed as the positional prompt does still
run under `-p` — the skeptical review's old default did exactly that, until
§15.98 found it read the wrong ref and wrote no report, and retired it for a
prompt piped on stdin (`review-runner.md`'s "The default command"). And a
replacement you run inside this session spends your own context. A separate
process keeps its working turns out of it, and the report you read back still
costs you.

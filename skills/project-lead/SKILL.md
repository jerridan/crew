---
name: project-lead
description: Take one goal to a reviewable draft PR without stopping for approval. Use for a whole goal, and for a one-line change too — it sizes the work itself and runs a small item on a light path. Triggers on "run this as a project", "hand this to crew", "take this to a draft PR".
---

# Project lead

Take one goal to a reviewable draft PR that a human can merge. Answer your own
questions. Stop for the **principal** only when you cannot proceed correctly.
Then stay, until the principal says the work shipped: the session outlives
the PR (`simple-path.md`'s "The delivered window").

The judgment is your job: the spec, the split, the order of the work, and every
adjudication. Dispatch the scouting and the drafting — your own context is the
most expensive place to work. You verify each package yourself, and
`simple-path.md`'s "Verify before you believe" says what that takes.

## Where the rules live

Every reference is in `references/`, beside this file, and every script in
`scripts/` — `crew-record.py` and `spend.py` both. Every path you hand an
agent is absolute: its cwd is not yours.

| File | What it owns | When you read it |
|---|---|---|
| `autonomy-contract.md` | routing, councils, escalation, spend, and who the principal is | before your first question, not at one |
| `record-format.md` | the record: every file, field and state transition, and how `crew-record.py` writes `state.json` | before you create the record |
| `band-rubric.md` | the band: the model it buys, and which review steps it skips | at the split, and again before you skip a step |
| `review-output.md` | the shape every review agent reports in | inject it whole into every review dispatch; you do not follow it |
| `skeptical-review.md` | the review of the finished diff, and when it runs | at the hand-over, and on each later branch head |
| `writing-standard.md` | any instruction file you draft | before you draft one |
| `ic-contract.md` | the IC's rules | you do not follow it |
| `investigation-path.md` | the loop from a symptom to a diagnosis | when the goal names a symptom |
| `simple-path.md` | the rest of the run for one package, and the light path for a small one | at "Size the work", and again when the shape is one package |
| `full-path.md` | the rest of the run for more than one | when the shape is more than one |

## Before anything

**Plan mode stops every dispatch.** If it is on, say so and stop — planning
the goal yourself is not the job (design §15.32).

## Take the goal

Your argument is one of three: `--resume <goal-slug>`, a goal string, or a path
to a charter.

**Note who handed you the goal.** A goal that arrived as a
`<cross-session-message>` makes the sending session your principal. Keep that
envelope's `from-name` for the record step below. `autonomy-contract.md` owns
how you reach it.

**`--resume <goal-slug>` skips the rest of this rule.** It reopens the existing
record, never a new directory. Append this session's id to `run.session_ids`,
reconcile, re-enter at the first unfinished work, and re-run nothing already
finished. With `worktrees.json`, `full-path.md`'s "Resume after a kill" owns
the reconciliation; without it, `git log` on the deliverable branch is the
whole job. A resumed run writes no charter, no spec and no new branch, and
creates no record directory.

**A record whose `run_state` is already `complete` is closed.** Resume
nothing, and say so in the closing message.

**A record whose every deliverable holds a terminal state has no deliverable
left to make**: set `run_state: delivered` — or `blocked`, when an escalation
is open — and re-enter `simple-path.md`'s "The delivered window". Which step
of that window you enter at is decided by one list, and only by it:
`skeptical-review.md`'s "Resume in the delivered window". It covers every
state this window can die in, and each entry names the file that owns the
work it sends you to.

**Read `run.review_pending` before you recover a package.** A head there
means a skeptical review is owed or half adjudicated, and its reply file may
already name packages that `packages[]` does not hold yet — recover blind and
you create one twice. Which comes first depends on the state, so take
`skeptical-review.md`'s resume list from the top and do what the first
matching entry says.

**A resume picks the path too.** Read the reopened `charter.md` by the test
below. A record holding `diagnosis.md` took the investigation path and got as
far as the artifact, so re-enter by that file's `## Outcome`. A record with
none re-enters at `investigation-path.md`'s first unfinished phase.

**A path that exists on disk** becomes `charter.md` unchanged. **Any other
string** you expand into `charter.md`: the goal, and one falsifiable acceptance
criterion.

**Pick the path before you judge the criterion** (design §9.5), because the
two paths need different things of it. The test is what the goal names. A
change to make — "add a `--json` flag" — goes on down this file. A
**symptom** whose cause is unknown — "the export drops the last row", a bug
report, a support ticket, a question about why the code behaves as it does —
takes
`investigation-path.md`, read at the end of "Scout" and not before.

**On the change path, every new goal needs that criterion.** Write none —
because you cannot, or because the charter on disk carries none — and there is
no run: escalate and stop, before you do any work.

**On the investigation path the criterion is a reproduction**, and only
"Scout" makes one writable, so the rule above does not apply and a charter
carrying a bare symptom is correct. Write the symptom so that some future
command could falsify it, and `investigation-path.md` Phase 1 writes the
command. Escalation trigger 1 fires there instead of here when no reproduction
can be written.

Then the record: `<record-root>/<slug>-<4 hex chars>/`, the suffix generated
once; `record-format.md` says where the root is. Write `charter.md`, then
`crew-record.py init` with `$CLAUDE_CODE_SESSION_ID` — read it, never invent
it — and `run set principal` with the `from-name` you kept above when the goal
arrived by message.

**Write `run.repo` in the same turn**: `git rev-parse --show-toplevel`, the
clone this session was launched in. It is the path every worktree command of
the run works from, and the first thing that reads it can run before any
branch exists — a replacement for the spec review, below (`record-format.md`).

**A replacement the principal named is written down here, before any step
runs.** Read the goal, `charter.md` and what the principal typed at launch for
a named replacement of a review step. Write each one to
`run.substitutions_requested` as `{step, replacement, source}`, `source` being
`goal`, `charter` or `launch`. A resumed session reads that field and nothing
else, because the words that named the replacement are not in its context. "A
step the principal replaced" below owns what you then do with it.

**The path you picked is the first entry in `decisions.md`**, once the record
exists. It is a precedent-route entry in `record-format.md`'s full shape,
every field included, and its `Citation:` quotes the words in the goal you
read the path off. Nothing else in the record says an investigation run was
chosen rather than fallen into.

## Scout

Four questions, answered from this repo before any spec exists. Does an
analogous implementation exist? Do tests cover this surface? What runs the
suite? Which instruction files apply?

Dispatch `crew:scout` subagents at `haiku` and read their answers. The reading
stays out of your own context. `band-rubric.md` says why Haiku runs only this
agent.

On the investigation path, read `investigation-path.md` now and run its phases.
It sends you back to "Write the spec", or it ends the run itself.

## Size the work

The scout's answers say how big the change is. You size the work from the
scout's report and `charter.md` (design §15.88). Ask four questions, and
answer each from those two:

1. Is the change one package — one file set one IC can hold?
2. Is the charter's acceptance criterion the whole specification: runnable as
   a command, with nothing in it left to interpret?
3. Does `band-rubric.md` band the work `light` or `standard`?
4. Is every preference question already settled by the charter or by this
   repo's own instruction files?

**Write the answer down first, whichever way it goes.** One `decisions.md`
entry, the second in the record, on the precedent route, naming the answer that
decided it. A run that leaves no entry cannot be told from one that never ran
this step.

**Four yeses take the light path.** Read `simple-path.md`'s "The light path".
It owns the rest of the run: no `spec.md`, no spec critic, one IC, and your
own verification of the package.

**Any no goes on down this file**, to "Write the spec". A no is the safe
answer: the spec costs a few dispatches, and work that needed one and did not
get one costs the run.

## Write the spec

`spec.md` is done when it carries the requirements, an acceptance criterion per
requirement that a command or a checklist can fail, the global constraints in
full (version floors, dependency limits, naming rules, platform requirements),
and the non-goals.

State requirements, never implementations. A constraint points at a file; it
never enumerates the file's contents, because a closed list is one missed item
from a critic round (design §15.50).

**Your output is the run's most expensive.** So outline the spec yourself, have
an unnamed `general-purpose` subagent at `sonnet` write the prose, and revise
what it returns. The spec is yours.

## Have the spec reviewed

Dispatch `crew:spec-critic`, unnamed, with `spec.md`, `charter.md`, the repo
path, `review-output.md` whole, and the absolute path it writes its findings
to: `reviews/spec-critic-r<n>.md`, `<n>` being one more than the highest on
disk. Every review dispatch in this run names its path this way and returns the
short result `review-output.md` defines; open the file only when the count says
there is something to adjudicate.

`Verdict: re-spec needed` means adjudicate, revise `spec.md`, and dispatch
again. Three re-specs is the cap; escalate at it.

**This review runs on every spec.** `band-rubric.md` says which later steps a
band skips, and the spec critic is not one of them: the split has not run yet,
so no package has a band. A light-path run writes no spec, which is a
different thing and the same file states it.

**A replacement named for this step runs in its place.** "A step the principal
replaced" below owns that case. Read it before you dispatch.

**Every review in this run is adjudicated the same way**, at every stage:
restate each finding in your own words, verify it against the repo, and push
back in writing where it is wrong here. **A finding is a claim, not a verdict.**

## A step the principal replaced

The goal text, `charter.md`, or the principal at launch can name another
reviewer for a review step, in plain language: "use Codex for the spec
review". Two steps take a replacement, and no other step does — the spec
critic, and the skeptical review (design §15.94d). "Take the goal" above
recorded each one in `run.substitutions_requested`; this section runs it.

### What the replacement is told

Give the replacement what the step's own reviewer would have had:

| The step | What the replacement gets |
|---|---|
| spec critic | the whole body of `agents/spec-critic.md` below its frontmatter, `review-output.md` whole, and the absolute paths of `spec.md` and `charter.md` |
| skeptical review | the instructions file `skeptical-review.md` has you assemble, which already carries `review-output.md`, plus the branch at `run.review_pending.head` and the base ref |

**The spec critic's whole body, never the seven checks alone.** The scope
limit, the over-specification checks, the rule against a re-spec for one
missed item and the two verdict strings all sit around those checks, and a
replacement given the checks by themselves loses every one of them.

**Add one sentence, and only this one**: it tells the replacement to return
the complete report as its output. For the skeptical review that sentence
**overrides** the two instructions in `skeptical-review.md`'s block that tell
the reviewer to write the report file itself and to return nothing by any
other path. It overrides them for the replacement alone, and the block is
otherwise unchanged. Write the whole of what you assembled to
`<record-dir>/reviews/<prefix>-r<n>-instructions.md`, the shape
`skeptical-review.md` already defines for its own file.

**`<prefix>` is the step's file prefix, and the step name is not always it:**

| The step | `<prefix>` |
|---|---|
| `spec-critic` | `spec-critic` |
| `skeptical-review` | `skeptical` |

Every file this section names uses `<prefix>`, so a substituted skeptical
review writes the same names the rest of the run already looks for
(`record-format.md`, and `skeptical-review.md`'s resume list).

### Running it

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
`run.repo` for a spec review, and the detached worktree `skeptical-review.md`
cuts for a skeptical review. And **never put the instructions inside a
double-quoted shell string**: they are markdown, and one backtick in them ends
the command.

**`-result.txt` and `-result.exit` sit where `-result.json` would.** A
skeptical review the Claude runner ran saves its own JSON output; a
replacement saves the runner's output as text and its status beside it, under
the round's name, and a retry retires all of them the same way
(`record-format.md`). A resumed session reads the same list in
`skeptical-review.md`'s "Resume in the delivered window", with those two files
standing in for `-result.json` wherever entries 9 and 10 name it. **A
`-result.txt` with no `-result.exit` is an incomplete attempt**: the shell
never reached the status write, so entry 10's rule holds — retire the attempt
and retry the round.

### The lifecycle holds; three checks change

`skeptical-review.md` owns that step whole, and a replacement changes none of
it: the detached worktree, the pending head, the round reserved before the
review starts, the `Reviewed:` first line, the two verdict lines, the one
retry on a failure, and the adjudication that clears `review_pending`. Three
of its four checks in "Check the review before you read it" are the Claude
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

### You write the report file

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

### One worked example

The principal types "use Codex for the spec review" at launch, and "Take the
goal" writes that to `run.substitutions_requested`. At "Have the spec
reviewed" you assemble the instructions, then run Codex in place of
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
headless session. A slash command passed as the positional prompt does run,
which is what the default skeptical review does. And a replacement you run
inside this session spends your own context. A separate process keeps its
working turns out of it, and the report you read back still costs you.

## Sweep for preference questions

Escalate every question in `charter.md` and `spec.md` that the repo cannot
answer, as one batch, before you split. `autonomy-contract.md` owns the
rule.

## Choose the shape

| The work is | You |
|---|---|
| One package, short enough to run unattended | Read `references/simple-path.md`. It owns the rest of the run. |
| More than one package, or work long enough to need steering | Read `references/full-path.md`. It owns the rest of the run. |

Size adds no third row here. A run that reached this table did not take the
light path at "Size the work", and a one-line change is one package on the
simple path, dispatched like any other. You edit a file in the target repo at
"Integrate", where the shared files live, and at the fix-round breaker your
path file names (design §9.3, §10). Nowhere else.

# Plan review

This file owns the plan review, the step with id `plan-review`. One reviewer
outside the run reads every implementation plan of the run together, with the
charter, the spec and the split, before any code exists. You label and route
each finding, then give the start word.

The reviewer is the Codex CLI. Its instructions are `plan-reviewer.md`.
`scripts/plan-review.py` injects that file whole into the runner's stdin. You
do not follow it.

**The step never blocks a run.** Every failure is a skip with a reason, and a
skip asks the principal nothing.

## When the plan review runs

Every run that writes a spec and dispatches its first package gets the plan
review: the simple path and the full path, at any band and any size. The
investigation path's fix package is a simple-path package, so it gets the
review too.

**The step is on by default.** The first dispatch of each IC carries `Plan
stop: on`, with no word from the principal. Only a `Plan review` standing
instruction with the value `off` turns the step off, as the charter line `Plan
review: off`. `SKILL.md`'s "Standing instructions" resolves that section. With
`off`, no dispatch carries a plan stop, no review runs, and "The record" below
says what you write.

The light path gets no plan review. Its IC still writes a plan, and does not
stop. Write a `steps_skipped` entry with step `plan-review`, as
`band-rubric.md`'s "What the light path skips" says.

A promotion off the light path depends on the IC's first commit:

- **Before the first commit**, remove the `plan-review` entry from
  `steps_skipped`. The promoted run's next dispatch carries `Plan stop: on`,
  and the review runs.
- **After the first commit**, the entry stays, and no review runs.

Two dispatches skip the step:

- A package that the delivered window adds, a change request or a patch
  round, gets no plan review.
- A fix-round dispatch gets no plan stop.

These packages are small patches to code that exists, with no new design.

One review runs per run. No second round runs, and nothing reviews a revised
plan.

## The planning stop

`ic-contract.md`'s "Write your plan first" owns what the IC does with `Plan
stop: on`. On the simple path, the IC writes the plan of its one package. On
the full path, each IC writes one plan for each package of its territory, and
every territory plans in parallel. Write `run.plan_review` with `status:
planning` at the first of these dispatches ("The record").

**Wait for every IC.** Go on to "Run the review" only when every IC stopped, or
when the nudge below gave up on it.

**A stop is the final message `Plans written: <absolute paths>`.** Check that
each path exists. When the message opens with `Plans written: denied`, the
record write was denied, and the message carries each plan whole. Transcribe
each plan to `plans/<id>.md`, before the review. Put this line at the top of
each file you transcribe: `Transcribed by the project lead from the IC's final
message.`

**An idle with a missing plan gets one nudge.** `SendMessage` the IC the id of
each missing plan and its absolute path. Then increment that package's
`nudges_used`, and write `state.json`. A second idle with a plan still missing
ends the wait for that IC. The review runs over the plans that exist, and the
instructions file names the missing ones ("Run the review"). That IC still gets
the start word. It writes the missing plan at the start of the package, with
no stop, and no review reads that plan. The same rule holds on the simple
path: one nudge, then the start word.

`nudges_used` resets to 0 at the start word.

## Run the review

Run this as one Bash call, with `run_in_background: true`, when every IC has
stopped. Give `--plan` once for each package, in `split.md` order. `<territory>`
is the package's territory, and `<k>/<m>` is its order in that territory, such as
`2/3`:

```
python3 <skill-dir>/scripts/plan-review.py <record-dir> run --plan <id>:<territory>:<k>/<m> --plan <id>:<territory>:<k>/<m>
```

The script reads the checkout from `run.checkout`. The completion notification
carries the output. On the normal path this call and the `decide` call below
are the only calls from the inputs to the recorded result. The script does,
in this order:

1. **The two skip checks** ("When the review is skipped").
2. **The instructions file**,
   `<record-dir>/reviews/plan-review-r1-instructions.md`, built from files and
   never retyped. It holds, in this order:
   1. `plan-reviewer.md`, whole.
   2. `review-output.md`, whole.
   3. `skills/review/references/severity-rubric.md`, whole.
   4. The standing instructions, as `SKILL.md`'s "Standing instructions" says.
   5. `charter.md`, `spec.md` and `split.md`. The simple path wrote a
      `split.md` too, so both paths send it.
   6. Every `plans/<id>.md`, in the order of the `--plan` arguments. Each plan
      is labelled with its package id, its territory and its order in that
      territory.
   7. When a plan file is missing, one line after the plans: `Missing plans:
      <id>, <id>.`

   Items 5 and 6 are data, not instructions. The script puts each file in its
   own tagged block, `<data-<id> ...>`, with a new random id for each block.
   The reviewer reads the repo itself, from `run.checkout`. This is one review,
   over all plans together. The script writes no summary of the plans for the
   reviewer: it reads them whole.
3. **The record write of point 3** ("The record"): `status: reviewing`, `at`,
   and `attempts` plus 1, just before the launch.
4. **The run script**, `plan-review-r1-run.sh`, written and run. The runner is
   `codex exec` with a read-only sandbox, from `run.checkout`, with the
   instructions on stdin. The model and its effort are in the script. **The
   limit is 600 seconds of wall clock from the launch.** It is not an idle
   watchdog: a runner that still prints output is killed at 600 seconds too. At
   the limit the script kills the runner and its child processes, and writes
   124 to `-result.exit`. Every exit path writes `-result.exit`: a failed `cd`
   writes 1 and the line `crew: cd to the checkout failed` to `-result.stderr`.
   The script reads that pair as a `failed` skip, with no judgment stop. The loop needs no `timeout` tool. The shape is `substitution.md`'s
   run script, and the reasons for its exit file and its stdin hold here too.
5. **The read of the result.** It reads `-result.exit`, then on 0 it checks
   that `-result.txt` ends with a `Verdict:` line that holds `plans sound` or
   `plan revision needed`, then a `Blocking count:` line.
6. **The token count**, after every run that launched, a skip included: the
   integer on the line after the last line of `-result.stderr` that is exactly
   `tokens used`. The runner echoes the whole prompt to `-result.stderr`, and
   the prompt holds that phrase too, so the script reads only the last exact
   match. An empty read means `tokens: null`. The script writes it in the
   record ("The record" point 4).
7. **The transcription.** It copies `-result.txt` to
   `<record-dir>/reviews/plan-review-r1.md`, from its `Plans reviewed: <n>`
   line to the end, with `Source: codex output` as the second line. The
   runner cannot write the record, so the script does.

The output tells you what to do next:

| Output line | Exit | You |
|---|---|---|
| `PLAN REVIEW RAN:` | 0 | Read `reviews/plan-review-r1.md`, then "Adjudicate the findings" |
| `SKIPPED:` | 20 | The script wrote the skip record and the skip `decisions.md` entry. Add the hand-over line ("The hand-over"), then give the start word with no findings ("The start word") |
| `QUOTA CHECK:` | 21 | The runner exited non-zero, and the script printed the last 20 lines of `-result.stderr`. Decide as "When the review is skipped" says, then run `skip` |
| `RECORD ERROR:` | 14 | A `crew-record.py` call failed. Fix the cause, then run the command again |

A command with a missing or wrong argument exits 2 and says why.

## When the review is skipped

The script runs these two checks before it writes anything:

```
command -v codex
timeout 15 codex login status
```

`review-runner.md`'s "The startup check and the cap" names the `timeout` tool:
`timeout` or `gtimeout`. With neither, the script runs `codex login status`
with no limit. **The script never reads a credential file.** `codex login
status` is the only login check.

| Reason | When | Who decides |
|---|---|---|
| `absent` | `command -v codex` prints nothing | the script |
| `not logged in` | `codex login status` exits non-zero | the script |
| `timeout` | `-result.exit` holds 124 | the script |
| `quota` | `-result.exit` is non-zero, and the last lines of `-result.stderr` name a usage limit or a rate limit | you |
| `failed` | any other non-zero exit, a `-result.txt` with no verdict pair, or a second attempt that died ("Resume in the planning step") | the script, except a non-zero exit |

**For a non-zero exit that is not 124, you decide.** No file holds a list of
strings, so you read the 20 lines that the script printed. Then run:

```
python3 <skill-dir>/scripts/plan-review.py <record-dir> skip --reason quota --evidence "<the stderr line>"
```

With `--reason failed`, the evidence is the exit status or the line that shows
the failure. The command writes the skip record and the skip `decisions.md`
entry.

**A skip does four things, in this order.** It writes the record ("The
record"). It writes one `decisions.md` entry that names the reason ("Adjudicate
the findings"). The script does both. Then you add the hand-over line ("The
hand-over"), and give the start word with no findings ("The start word"). **A
skip asks the principal no question.**

## Adjudicate the findings

Read `reviews/plan-review-r1.md`. Adjudicate each finding and label it again
yourself, as `SKILL.md`'s "Every review in this run is adjudicated the same
way" says. The labels come from `severity-rubric.md`, and `plan-reviewer.md`
gives what `blocking` means for a plan. That section's action table names the
actions for a critic and for the goal check. This section owns the
actions for the plan review in its place:

- **An accepted `blocking` finding.** The IC revises that plan before it
  writes code. It appends `## Revised after the plan review` to
  `plans/<id>.md`, and names each finding and what changed. No second review
  runs.
- **An accepted `suggestion` or `nit`.** The IC applies it as it writes the
  package. It does not revise the plan.
- **A declined finding, with any label, and every `don't post` and `not
  real`.** `decisions.md` only.
- **An `unsure` finding.** One question to the principal, by
  `autonomy-contract.md`'s escalation rules. The start word does not wait for
  the answer. When the answer makes the finding `blocking`, it goes where the
  package then is. Before you accept the package, send it to the IC by
  message as an accepted `blocking` finding; `simple-path.md`'s "Verify before
  you believe" then checks it. After the package is integrated, it is a
  finding from the principal in the delivered window.

**Then run `decide`**, once every finding has your label. It writes the
record first: `outcome: ran`, the `labels` counts by your label, `accepted`
(the findings you send to an IC) and `recommendations` (the "The record" point
4 write). Then it writes one `decisions.md` entry. Give one `--finding` for
each finding and one `--refactor` for each refactor recommendation, in report
order:

```
python3 <skill-dir>/scripts/plan-review.py <record-dir> decide --finding "Finding: F1 blocking (reviewer: blocking) — sent to <ic name>" --finding "Finding: F2 don't post (reviewer: suggestion) — declined: <reason>" --refactor "Refactor: <ticket title>"
```

Each finding line has the form `Finding: F<k> <project lead label> (reviewer:
<label>) — sent to <ic name> | declined: <reason>`. `F<k>` numbers the
findings in report order. `crew-record.py`'s `--line` key takes letters only,
so the number goes in the text, not in the key. The script counts the labels
and the `sent to` lines from these arguments. The entry has the title `Plan
review: which findings does the run act on?`, the answer `<k> of <n> findings
sent to the ICs`, the citation `reviews/plan-review-r1.md` and the confidence
`high`.

On a skip, the entry has the same title and the answer `skipped: <reason>`.
The citation is the evidence: the empty `command -v`, the exit status, or the
stderr line.

## The start word

After the `decisions.md` entry, send one `SendMessage` to each IC:

```
Start <package id>

<each accepted finding on this IC's plans, verbatim from reviews/plan-review-r1.md, with the line "Project lead label: <label>" under its title>
```

`<package id>` is the first package of the IC's territory. An IC with no
accepted finding gets `Start <package id>` alone. After a skip, every IC gets
`Start <package id>` alone.

**An IC whose record write is denied sends its revision by message.** It
sends the text of `## Revised after the plan review` to you. Append that text
to `plans/<id>.md`, under the transcription line of "The planning stop".

Set `nudges_used` to 0 on each package that a start word names. When the start word has gone to every IC,
write `status: started` ("The record").

**A respawn after the review carries the plan review in its brief.** Three
causes respawn an IC after the start word: a compaction that
`run.compactions` names, four finished packages, and fix rounds 4 and 5. The
new IC's brief carries the absolute paths of its territory's plans, every
accepted finding on them, and `Plan stop: off`.

## The record

`record-format.md` owns `run.plan_review`: every key and every value. The script
writes the whole object each time, through `crew-record.py run set
plan_review`. It writes at these points:

1. **At the first planning dispatch**, you run `plan-review.py <record-dir>
   planning`: `status: planning`, `outcome: null`, `reason: null`, `at: null`,
   `started_at: null`, `attempts: 0`, every `labels` count 0, `accepted: 0`,
   `recommendations: 0`, `tokens: null`.
2. **At a skip before the launch** (`absent` or `not logged in`), `run` writes
   `outcome: skipped` and the `reason`.
3. **Just before the launch**, `run` writes `status: reviewing`, `at` the launch
   time, and `attempts` plus 1.
4. **After the run exits**, `run` writes the `tokens` count. On a skip it
   writes `outcome: skipped` and the `reason`. On a review, `decide` writes,
   once you labelled every finding and before the `decisions.md` entry:
   `outcome: ran`, the `labels` counts by your own label, `accepted` and
   `recommendations`. A crash between this write and the entry leaves `status:
   reviewing` with the exit file present, so the resume adjudicates again.
5. **When the start word has gone to every IC**, you run `plan-review.py
   <record-dir> started`: `status: started` and `started_at`.

**With `Plan review: off`**, run `plan-review.py <record-dir> off` once, at the
first dispatch. It writes `status: started`, `outcome: off`, `started_at` the
dispatch time, and the initial values of point 1 for the rest.

A light-path run writes no `run.plan_review`. Its `steps_skipped` entry is
its whole record of the step.

The files of the step sit under `reviews/`: `plan-review-r1-instructions.md`,
`plan-review-r1-run.sh`, `plan-review-r1-result.txt`,
`plan-review-r1-result.stderr`, `plan-review-r1-result.exit`, and the report
`plan-review-r1.md`.

## The hand-over

The closing report of `simple-path.md`'s "End the run" carries two items for
this step.

**One plan-review line**, in one of three forms:

```
Plan review: ran — <n> findings (<n> blocking, <n> suggestion, <n> nit, <n> unsure, <n> don't post, <n> not real), <n> sent to the ICs.
Plan review: skipped — <reason>.
Plan review: off.
```

**The heading `Refactor recommendations`**, with each refactor recommendation
of the report under it as the reviewer wrote it: a ticket title and two
lines. Leave the heading out when the report has none.

## Resume in the planning step

A record with no `run.plan_review` takes the ordinary resume of its path.
Otherwise read `run.plan_review` and `decisions.md`, and take the first case
that matches:

1. **`status` is `started`.** The ordinary resume of the path:
   `full-path.md`'s "Resume after a kill", or `resume.md` on the simple path.
2. **`decisions.md` holds the entry `Plan review: which findings does the run
   act on?`, and `status` is not `started`.** Send the start word. A
   split-pane IC that still runs gets it by message. Respawn every other IC
   with a fresh name, as `SKILL.md`'s "Every dispatch is named" says. Its
   brief carries the absolute paths of its territory's plans, the
   accepted findings on them, and `Plan stop: off`. Then write `status:
   started`.
3. **`status` is `reviewing`.** Run the `run` command again. The script
   follows this rule. When `-result.exit` is present, it reads it and goes on:
   you adjudicate, or the script skips. When it is absent, the script checks
   first that no `plan-review-r1-run.sh` process still runs (`pgrep -f`). If one
   runs, it waits for the exit file. If none runs, the script died with the
   session. The script retires each file of the attempt that exists:

   | File | Retired name |
   |---|---|
   | `plan-review-r1.md` | `plan-review-r1-attempt1.md` |
   | `plan-review-r1-instructions.md` | `plan-review-r1-instructions-attempt1.md` |
   | `plan-review-r1-result.txt` | `plan-review-r1-result-attempt1.txt` |
   | `plan-review-r1-result.stderr` | `plan-review-r1-result-attempt1.stderr` |
   | `plan-review-r1-result.exit` | `plan-review-r1-result-attempt1.exit` |

   With `attempts` at 1, it builds the instructions file again, writes
   `plan-review-r1-run.sh` again, and runs the script once more. The run script
   is not retired. With `attempts` at 2, it skips with reason `failed`. This
   rerun is not a second review, because no review finished.
4. **`status` is `planning`.** A split-pane IC can still run, so check first,
   as `full-path.md`'s "Resume after a kill" says. A territory with every plan
   on disk is done. Respawn the IC of each other territory with a fresh name
   and `Plan stop: on`, to write only its missing plans. Wait as "The planning
   stop" says, then run the review.

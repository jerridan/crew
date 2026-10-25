# Review runner

This file owns the mechanics of a headless review. It says how any caller
cuts the detached worktree, writes the instructions file, launches the
runner, checks the result and records the session. The caller supplies its
round `<n>`, its goal text and where it reads that text, its base ref, its
pending head, its suite command and its output path
(`<record-dir>/reviews/skeptical-r<n>.md`). `skeptical-review.md`, "The
inputs", is the table that lists every value and where it is read from. The
body names its files `skeptical-r<n>`. `skeptical-review.md` is the first
caller.

## Never review in the run's own checkout

A probe watched one finder agent run `git checkout main` inside the repo
under review (design §15.94c). The review reads and tests; it must not be
able to move the run's branch. So cut a worktree of its own, detached at the
pending sha, once per deliverable:

```
git -C <run.repo> worktree add --detach <record-dir>/review-worktrees/<deliverable-id> <review_pending.head>
```

**Every later round moves the same worktree to its pending head**, in place.
A resumed reviewer works in the directory its session started in ("Resume
the reviewer" below), so the path never changes:

```
git -C <record-dir>/review-worktrees/<deliverable-id> switch --detach --discard-changes <review_pending.head>
```

Remove it at the ship word, never after a round:

```
git -C <run.repo> worktree remove --force <record-dir>/review-worktrees/<deliverable-id>
git -C <run.repo> worktree prune
```

**`run.repo`, never `run.checkout`.** "End the run" removes a checkout the
run cut for itself, and a review that runs after that would have no repo to
work from. `run.repo` is the target-repo clone, and it outlives the run
(`record-format.md`).

**Detached, and at the pending sha.** A named branch in a second worktree is
a branch two trees can move. The sha is what the review was asked about, and
detaching it keeps the run's own branch out of reach.

**You alone make and remove these worktrees.** No IC and no review agent
touches `review-worktrees/`, and nothing registers there in `worktrees.json`,
which holds the run's own worktrees only (`record-format.md`).

**Check the worktree before every round.** A killed session can leave the
directory without its registration, or the registration without the
directory. Before you move the worktree, run:

```
git -C <run.repo> worktree prune
git -C <record-dir>/review-worktrees/<deliverable-id> rev-parse --git-dir
```

When the second command fails, run the removal above, delete what is left at
the path, and cut the worktree again at the same path.

`--force` and `--discard-changes` are right on a review worktree and nowhere
else in this run. The tree is detached at a sha the branch already holds, it
holds no work except the setup command's output, and every piece of evidence
the review produced is in the record. The rule that protects an IC worktree
(`simple-path.md`'s "End the run") is protecting something this tree never
has. Ignore a removal that fails because the path is already gone.

## The default command

Write the instructions file first, then launch, from the review worktree:

```
cd <record-dir>/review-worktrees/<deliverable-id> && printf '%s\n' "Review the finished change on this detached head, following every instruction in your system prompt. Write your report to the absolute path your instructions name." | claude -p --model opus --effort high --output-format json --session-id <uuid> --append-system-prompt-file <record-dir>/reviews/skeptical-r<n>-instructions.md --allowedTools "Read,Glob,Grep,Bash(git diff *),Bash(git log *),Bash(git show *),Bash(git rev-parse *),Bash(<gate part> *),<one more such rule per gate part>,Bash(npm view *),Bash(npm ls *),Bash(pnpm ls *),Bash(pnpm why *),Bash(yarn why *),Bash(pip show *),Edit(//<record-dir>/reviews/**)" > <record-dir>/reviews/skeptical-r<n>-result.json 2> <record-dir>/reviews/skeptical-r<n>-result.stderr; echo $? > <record-dir>/reviews/skeptical-r<n>-result.exit
```

**The prompt rides on stdin, never as a positional argument.**
`--allowedTools` takes a variadic list, so a prompt placed after it is read as
one more tool name, and the process exits 1 with "Input must be provided
either through stdin or as a prompt argument" (design §15.98b). Piping the
prompt on stdin keeps the tool list closed. "Check the review before you read
it" below catches a prompt that still did not arrive.

**No slash command runs.** The bundled pull-request reviewer the skeptical
review used to invoke reads a base ref as the commit to review, not the whole
diff against the goal, and even retargeted at the right commit it wrote no
report file and no verdict pair (design §15.98b). The stance
`skeptical-review.md` states is what the printed line and the appended system
prompt carry instead.

**Redirect every piece of evidence to the record, and read it from there.**
The checks below run against `-result.json`, so a session that dies between
the exit and the checks finds the same evidence a live one had. It also holds
the report itself when the fallback applies. `-result.stderr` is the runner's
own error output, kept beside it for the same reason. `-result.exit` is the
process's own exit status, the same protocol the substituted runner already
uses (`substitution.md`) — check 1 below reads it rather than trusting the
JSON's own shape when the process died before writing one.

## Resume the reviewer

**Round 1 of a deliverable launches as above. Every later round resumes the
reviewer session of the round before it**, so the reviewer keeps what it read
and does not inspect the whole PR again. Resume when all three hold:

- `run.review_sessions[skeptical-r<n-1>]` exists, and its `runner` is the
  runner this round uses.
- The head round `<n-1>` reviewed, the `Reviewed:` line of
  `reviews/skeptical-r<n-1>.md`, is an ancestor of the pending head: `git
  merge-base --is-ancestor <previous head> <review_pending.head>` exits 0. A
  force-push, and a round on another deliverable, fail this check.
- No `reviews/skeptical-r<n>-resume-attempt<k>.md` exists. A retired resume
  attempt means a resume of this round failed once, and the round now
  launches fresh.

Otherwise launch as round 1 does. Take the session id from the record, never
from a runner's `--last`. A fresh launch at a later round takes the base that
`/crew:review`'s "Find the base of a later round" sets for it.

**Write the resume prompt** to `<record-dir>/reviews/skeptical-r<n>-resume.md`.
Write the instructions file as well, as every round does. Fill this block:

```
The change has a new head. In this session you reviewed <previous head sha>.
This working directory is now a detached checkout at <pending head sha>.

The change since your last review is `git diff <previous head sha>..HEAD`.
Read it first. Read the whole change, `git diff <deliverable base>..HEAD`,
again only where that delta touches code you did not review. Follow your
first instructions on the suite.

<one of the two literal lines below>

<the file that line names, verbatim>

Give a verdict on the whole change as it now stands, not on the delta alone.
Use the same report shape and the same two verdict strings as before. Open
the report with this line, and nothing before it:

Reviewed: <pending head sha>

Above the two verdict lines, write one line that starts `Beyond the
findings:`. Write `Beyond the findings: none` when every hunk of the delta
answers one of the findings in your last report. Otherwise, after the colon,
name each hunk that does not.

<the output sentence>

Do not write to <previous round's absolute report path>. That file is the
report of your last round.
```

**A resumed round writes its report to its own round's path,
never to the previous round's path.** The resumed session still holds the
path its first instructions named. A reviewer that writes there overwrites
the last round's report, so the block names both paths.

The literal line is "This is the project lead's reply to your last report.
It says which findings it accepted, and why it declined or pushed back on the
others:", followed by `reviews/skeptical-r<n-1>-reply.md`. When that round
has no reply file, because its report had no finding to dispose of, the line
is "Your last report had no finding to answer. This is that report:",
followed by `reviews/skeptical-r<n-1>.md`.

The output sentence is "Write your whole report to <absolute output path>
before you finish." for the default runner, and the replacement sentence in
"Reviewer instructions" below for a replacement.

**One runner call per round.** The pushback rides in the resume prompt. A
second call per round would double the runner's spend, and the reviewer needs
the context, not a dialogue.

**The resume commands.** The default runner keeps "The default command" with
two changes: `--resume <session id>` in place of `--session-id <uuid>`, and
the resume prompt on stdin in place of the `printf` line:

```
cd <record-dir>/review-worktrees/<deliverable-id> && claude -p --resume <session id> --model opus --effort high --output-format json --append-system-prompt-file <record-dir>/reviews/skeptical-r<n>-instructions.md --allowedTools "<the same list>" < <record-dir>/reviews/skeptical-r<n>-resume.md > <record-dir>/reviews/skeptical-r<n>-result.json 2> <record-dir>/reviews/skeptical-r<n>-result.stderr; echo $? > <record-dir>/reviews/skeptical-r<n>-result.exit
```

A replacement keeps `substitution.md`'s run script, with this `codex exec`
line. The resumed session keeps the directory it started in:

```
  codex exec resume -c sandbox_mode=read-only <session id> - \
    < <record-dir>/reviews/skeptical-r<n>-resume.md \
    2>&1 > <record-dir>/reviews/skeptical-r<n>-result.txt
```

**Record the round's session** in `run.review_sessions[skeptical-r<n>]`,
with `crew-record.py <record-dir> run set review_sessions.skeptical-r<n>
'<json>'`. A resumed round writes `resumed_from: "skeptical-r<n-1>"` and
`fresh_reason: null`. A round that launches fresh writes `resumed_from:
null`, and `fresh_reason` names the condition above that failed, or `null` on
round 1. A retry overwrites the round's entry.

- **The default runner** writes the entry before the launch. A resumed
  session keeps its id, which `run.review_session_ids` already holds, so
  append nothing to that list.
- **A replacement** prints `session id: <uuid>` on stderr. Write the entry
  after the run, from `sed -n 's/^session id: //p'
  <record-dir>/reviews/skeptical-r<n>-result.stderr | head -1`. With no such
  line, write no entry, and the next round launches fresh. Never put this id
  in `run.review_session_ids`: `spend.py` prices Claude sessions alone.

**A resume that exits non-zero launches fresh, in the same round.** The
session can be gone, or a runner upgrade cannot read it. Retire the attempt
as `skeptical-review.md`'s "Retiring an attempt before you retry it" says,
write `fresh_reason: "resume exited <status>"`, and launch as round 1 does.
That launch is not the failure path's retry. A resume that exits 0 and fails
a check below takes the failure path, and its retry launches fresh. Before
either fresh launch, replace the previous-head base the resume used. First,
recompute the merge base, as `/crew:review`'s "Find the base of a later
round" does for a round that is not resumed. Then write it to
`deliverable.base`. Then write the round's instructions file again, with the
whole-PR range `git diff <merge base>..HEAD`.

This rule is for the skeptical review alone. A spec critic, replaced or not,
and every in-process critic, start fresh each round (design §15.108).

## The permissions the review needs

**Without an allow list the review returns nothing.** The same probe found
that under default headless permissions every command the review has to run,
and its report write, are denied: the reviewer runs no test, writes no
report, and prints its findings into the JSON `result` field instead.

Each rule buys one thing the review cannot work without:

| Rule | What it buys |
|---|---|
| `Read`, `Glob`, `Grep` | reading the tree the review is about |
| `Bash(git diff *)`, `Bash(git log *)`, `Bash(git show *)` | the history and the diff |
| `Bash(git rev-parse *)` | the sha the reviewer opens its report with (`git rev-parse HEAD`) |
| `Bash(<gate part> *)`, one rule per part of each gate | every verification gate the scout recorded, not the suite alone: tests, types, lint and build. The suite run is the one `skeptical-review.md`'s stance requires. Under the no-suite outcome, leave every gate rule out |
| `Bash(npm view *)`, `Bash(npm ls *)`, `Bash(pnpm ls *)`, `Bash(pnpm why *)`, `Bash(yarn why *)`, `Bash(pip show *)` | read-only package probes: which version is installed, and why. When the scout's setup command uses another package manager, add its read-only equivalent |
| `Edit(//<record-dir>/reviews/**)` | the report file, which sits in the record and not in the worktree |

**The list adds capabilities and removes none.** Headless mode already allows
reading in the working directory and its read-only commands. Everything the
list does not name prompts instead, and a prompt with nobody to answer it is
a denial — which is how the reviewer is kept from editing the code. It
reports; you decide.

**One comma-separated argument.** The flag also accepts space-separated
rules, but each one then needs its own shell quoting, and a rule that loses
its quotes silently becomes a different rule.

**`Edit(...)` is what governs the report write, not `Write(...)`.** A path
rule on `Write` is accepted and never consulted, so a review given
`Write(<path>/**)` cannot write its report. The `//` at the front of the
rule is the absolute-path anchor: the record directory's own leading slash
is not doubled, it is written after the anchor. The rule is scoped to
`reviews/`, so this buys the report file and no code edit anywhere.

**A headless run refuses a write under ~/.claude, whatever the allow list
grants.** Claude Code treats that tree as a sensitive path, and the default
record root, `~/.claude/crew/`, is inside it. A run whose `CREW_RECORD_ROOT`
points outside ~/.claude avoids the refusal. When the write is refused
anyway, the result-field fallback in "Check the review before you read it"
is the documented path.

**`node -e`, `python -c` and every install command stay off the list.**
`node -e` and `python -c` run any code they get, so either one lets the
review do more than report. An install changes the tree the review reads,
and you already ran the setup command ("Prepare the worktree before you
launch").

**`Bash(<prefix> *)` matches the start of the command string, not a git
subcommand.** The probe showed `Bash(git log *)` allow `git log --oneline`
and deny `git -C <path> log --oneline`, because the second does not begin
with `git log`. The review runs with its worktree as the working directory
for exactly this reason: the commands it needs start with `git`, with no
`-C` in front.

**A compound gate command takes one rule per part.** Split the recorded
invocation on `&&`, `;`, `||` and `|`, and write a `Bash(<part> *)` rule for
each part, trimmed. One rule for the whole string matches only the first
command the reviewer runs, and the rest are denied one at a time.

**A denied suite component fails the review; it never becomes a finding.** A
reviewer that could not run the tests has not done the job
`skeptical-review.md`'s stance asks for, and a finding built on a suite it
could not run is a guess. Check 2 below catches it, and the failure path is
where it goes.

## Prepare the worktree before you launch

**Run the repo's setup command yourself, in the review worktree.** A fresh
worktree has the repo's files and none of its installed dependencies, so the
suite fails there for a reason that has nothing to do with the diff. The
scout records that command beside the suite command (`SKILL.md`, "Scout").
Run it as the project lead, in the worktree, before the launch — never by
granting the child a rule for it, which would let the review install
whatever it liked. A setup that ran adds the line "Dependencies are
installed. Do not install." to the instructions ("Reviewer instructions").

**A setup that fails is an environment failure, not a finding.** Record it in
`decisions.md`, and run that round with the no-suite outcome: the reviewer is
told there is no suite, and reads the diff without one. Say so in the round's
report header when you adjudicate, so nobody reads a thin review as a clean
one.

**A file, never an inline string.** The block below is long, and it carries
the principal's own words, so passing it inline puts a quote or a backtick
one shell layer away from breaking the command. The file also lands in the
record, where a reader can see exactly what the reviewer was told
(`record-format.md`).

**For the model, pass exactly `--model opus --effort high`.** A separate
process with its own model and effort flag is what keeps the review's cost
apart from `band-rubric.md`'s pick for the run's own ICs (design §15.94c).

**The review edits nothing but its own report.** The only `Edit` rule it
carries is scoped to `reviews/`, so whatever it decides, it can make no code
edit. The findings come back to you, and you decide what each one earns.

## Reviewer instructions

**You assemble this file; you do not copy a second copy of the report
shape.** It has two parts, in this order:

1. **`review-output.md`, verbatim.** It owns the severity tags, the
   `Cannot verify` rule, the report-never-fix rule and the two closing lines,
   and it is the same text every review dispatch injects. The child process
   reads no file of this plugin, so a reference by name would not resolve.
2. **The block below**, with its bracketed values filled in. It holds what is
   this review's own and nothing that part 1 already states: the goal text,
   the diff range, the suite and the line that says the dependencies are
   installed (or the no-suite sentence), the output path, and the pending
   head.

Write the two into
`<record-dir>/reviews/skeptical-r<n>-instructions.md` and pass that path to
`--append-system-prompt-file`.

```
You are reviewing one finished change, and you are the only reader it gets.

The goal, in the principal's own words, with every constraint the principal
stated: <goal text>

You are already on the change: this working directory is a detached checkout
at <pending head sha>. Read `git diff <base>..HEAD` against that goal and
against this repository. The charter's acceptance criteria go in as
supplementary evidence, never on their own. Do not look for a specification
document, and do not treat any file in the repository as the statement of
what this change owed.

Assume the change is wrong, and look for how. A clean pass is a finding you
failed to make, not a result.

<the suite paragraph, one of the two literal blocks below>

Write your whole report to <absolute output path> before you finish. This
process has no caller reading its output, so anything you print to the
terminal and do not also write to that path is lost with it — except your
very last message, which is captured whole. So: write the report to that
path. If, and only if, that write is denied, return the complete report as
your final message instead, in the same shape, so the one thing that is
captured is the report itself.

Open the report with this line, and nothing before it:

Reviewed: <pending head sha>

That is `git rev-parse HEAD` in this working directory, and it is how the
reader knows which tree your findings describe.

Then the findings, in the shape those rules give, ending with their two
closing lines. Your two verdict strings are `accepted` and
`patch round needed`. Use "accepted" when you found nothing that must change
before this ships, and "patch round needed" when you found at least one
[Critical], or a [Concern] serious enough that shipping without a fix would
be wrong.

Add one section, titled "Checked and found nothing", listing what you looked
for and did not find. A check you never ran does not go in it.
```

**Fill the suite paragraph with one of these two literal blocks, verbatim
except their own brackets.** With a suite:

```
Run the suite yourself, and report what you saw: <suite command>, run in
<the directory it runs in>. A passing run somebody else reported is a claim
about another tree.
```

When you ran the setup command, add this line after that block, verbatim:

```
Dependencies are installed. Do not install.
```

Under the no-suite outcome, this replaces the whole paragraph — never a
"run the suite" sentence with nothing to run:

```
This repository has no suite. Read the diff without running one.
```

**A replacement for the skeptical review receives this same file, plus one
sentence that names the report path and asks for the output too**
(`substitution.md`). It replaces the block's rule that returns the report
only when the write is denied. That sentence is the only addition:

```
For a replacement runner: write the complete report to <absolute output
path>, and also return it whole as your output, `Reviewed: <sha>` first and
the two verdict lines last, whether or not the write succeeded.
```

## Check the review before you read it

Four checks, on the JSON the process printed and on the record directory.
All four pass, or this is the failure path below:

1. **`-result.exit` reads `0`**, and the JSON's own `is_error` is false.
2. **The outcome.** Check 2 fails on outcomes, not on denials. It fails in
   three cases:
   - No report came back, from the file or from the `result` field.
   - The suite did not run. A denied suite component is this case. So is a
     report with no suite output when the review had a suite.
   - The report marks a check `Cannot verify`, and that check bears on the
     verdict.

   Every other denial passes this check. Write the `tool_input` of each
   denial in `permission_denials` to `denied`, below. Read the entries by
   their `tool_name` and `tool_input` and no more: the shape of an entry is
   not documented, so anything else about it can change.
3. **The report file exists** at the output path, or the fallback below
   supplied it.
4. **Its last two lines are the verdict pair**, and its first line is
   `Reviewed: <sha>`, matching `run.review_pending.head`. On a resumed
   round, the previous round's report must also still open with its own
   `Reviewed:` sha, the previous head sha that the resume prompt names.

**A `Reviewed:` mismatch fails the round.** Take the failure path below:
retire the attempt and rerun it. A resumed round that fails this way reruns
fresh, as "Resume the reviewer" says. When the previous round's report opens
with another sha, the resumed reviewer overwrote it. Restore it from the
`result` field of `skeptical-r<n-1>-result.json` when that text ends with
the two verdict lines. Use the fallback layout below, with the previous
head sha on the `Reviewed:` line. Otherwise, record the loss in
`decisions.md` with the round number, and go on. The current round still
fails and reruns fresh.

**Write the outcome down.** These checks decide whether a report may be
adjudicated, so their result belongs in the record and not in your context:
`run.review_results[<n>] = {exit, denials_ok, report_ok, denied, at}`
(`record-format.md`). A resumed session adjudicates a report only when that
entry exists and passes. With no entry it runs the four checks again from the
saved JSON, rather than trusting the report it finds. When you adjudicate,
read `denied` beside the report. A finding that rests on a denied command is
unverified.

**When the report file is missing, read `result` in the saved JSON.** A
reviewer denied its report write prints the report there. When that text ends
with the two verdict lines, it is the report. Write the file yourself, in
this layout, so every report on disk opens the same way:

```
Reviewed: <sha>
Source: result field

<the result text>
```

Take the `Reviewed:` sha from the text when it carries one, and from
`run.review_pending.head` when it does not — that is the sha the review was
launched against. The review counts and its round stands.

**Otherwise the review failed.** Record the failure in `decisions.md`. Retire
the attempt as `skeptical-review.md`'s "Retiring an attempt before you retry
it" says. Then run it once more, and **do not increment `run.review_rounds`
for the retry** — no review happened, so the cap has nothing to count. A
second failure is an escalation to the principal (`autonomy-contract.md`): say
the review could not produce a report, and hand over what the branch holds.

**A prompt that never reached the child is a failed launch.** The signs are
an empty `result` in `-result.json`, or an empty file, and
`Input must be provided` in `-result.stderr`. Take the failure path above,
and put the whole command line you ran in its `decisions.md` entry. Its one
retry is the rerun, not an extra one, and a second failure escalates as it
says.

## Record the review's session id

**Generate the id before you launch a fresh round.** `uuidgen` prints one. Pass it as
`--session-id <uuid>`, and append it to `state.json`'s
`run.review_session_ids` **before** the command runs. A review killed
halfway then still prices into the run; an id read out of the result
afterwards is lost with the process that died. A resumed round generates
none, as "Resume the reviewer" says.

`spend.py` prices those transcripts into the run, and `crew-stats.py` reports
them. **Never put one in `run.session_ids`**: `hooks/session-end.py` marks
the whole run `interrupted` when an id in that field ends, so a finished
review would fake a dead run (`record-format.md`, design §15.90h).

**Measure the spend again once the review returns.** The canonical figure is
`autonomy-contract.md`'s, and it names the review as one of the moments to
run it. A figure taken before the review misses it.

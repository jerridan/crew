# Review runner

This file owns the mechanics of a headless review. It says how any caller
cuts the detached worktree, writes the instructions file, launches the
runner, checks the result and records the session. The caller supplies its
round `<n>`, its goal text, its base ref and its pending head. The body
names its files `skeptical-r<n>`. `skeptical-review.md` is the first caller.

## Never review in the run's own checkout

A probe watched one finder agent run `git checkout main` inside the repo
under review (design §15.94c). The review reads and tests; it must not be
able to move the run's branch. So cut a worktree of its own, detached at the
pending sha:

```
git -C <run.repo> worktree add --detach <record-dir>/review-worktrees/r<n> <review_pending.head>
```

Remove it in the same turn the review returns:

```
git -C <run.repo> worktree remove --force <record-dir>/review-worktrees/r<n>
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

**Clean up before you cut a new worktree.** A killed session leaves the
directory and its registration behind, and `worktree add` then fails on a
path that already exists. So on every resume in `delivered`, whatever is on
disk and whether or not a report exists, clear
`<record-dir>/review-worktrees/r<n>` — the reserved round, never
`review_rounds`, which still names the round before it:

```
git -C <run.repo> worktree remove --force <record-dir>/review-worktrees/r<n>
git -C <run.repo> worktree prune
```

`--force` is right on a review worktree and nowhere else in this run — the
removal above takes it too. The tree is detached at a sha the branch already
holds, every piece of evidence the review produced is in the record, and a
refusal here would strand a directory that the next round has to reuse. The
rule that protects an IC worktree (`simple-path.md`'s "End the run") is
protecting something this tree never has. Ignore a removal that fails because
the path is already gone, then prune.

## The default command

Write the instructions file first, then launch, from the review worktree:

```
cd <record-dir>/review-worktrees/r<n> && printf '%s\n' "Review the finished change on this detached head, following every instruction in your system prompt. Write your report to the absolute path your instructions name." | claude -p --model opus --effort high --output-format json --session-id <uuid> --append-system-prompt-file <record-dir>/reviews/skeptical-r<n>-instructions.md --allowedTools "Read,Glob,Grep,Bash(git diff *),Bash(git log *),Bash(git show *),Bash(git rev-parse *),Bash(<suite command> *),Edit(//<record-dir>/reviews/**)" > <record-dir>/reviews/skeptical-r<n>-result.json 2> <record-dir>/reviews/skeptical-r<n>-result.stderr; echo $? > <record-dir>/reviews/skeptical-r<n>-result.exit
```

**The prompt rides on stdin, never as a positional argument.**
`--allowedTools` takes a variadic list, so a prompt placed after it is read as
one more tool name, and the process exits 1 with "Input must be provided
either through stdin or as a prompt argument" (design §15.98b). Piping the
prompt on stdin keeps the tool list closed.

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
| `Bash(<suite command> *)` | the suite run `skeptical-review.md`'s stance requires. `<suite command>` is the one the scout recorded; under the no-suite outcome there is no such command, so leave this rule out |
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

**`Bash(<prefix> *)` matches the start of the command string, not a git
subcommand.** The probe showed `Bash(git log *)` allow `git log --oneline`
and deny `git -C <path> log --oneline`, because the second does not begin
with `git log`. The review runs with its worktree as the working directory
for exactly this reason: the commands it needs start with `git`, with no
`-C` in front.

**A compound suite command takes one rule per part.** Split the recorded
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
whatever it liked.

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
   the diff range, the suite (or the no-suite sentence), the output path, and
   the pending head.

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

Under the no-suite outcome, this replaces the whole paragraph — never a
"run the suite" sentence with nothing to run:

```
This repository has no suite. Read the diff without running one.
```

**A replacement for the skeptical review receives this same file, plus one
sentence that overrides the block's file rule** (`substitution.md`). That
sentence is the only addition:

```
For a replacement runner, this invocation replaces the file rule above: do
not write the report file; return the complete report as your output,
`Reviewed: <sha>` first and the two verdict lines last, and the project lead
writes the file.
```

## Check the review before you read it

Four checks, on the JSON the process printed and on the record directory.
All four pass, or this is the failure path below:

1. **`-result.exit` reads `0`**, and the JSON's own `is_error` is false.
2. **The predicate**: `permission_denials` is empty, except for exactly one
   denied write to the named report path when the fallback below then
   supplied a conforming report. Any other denial fails this check — a suite
   component above all — because the review could not do what you asked, and
   the findings are worth less than they look. Read the entries by their
   `tool_name` and `tool_input` and no more: the shape of an entry is not
   documented, so anything else about it can change.
3. **The report file exists** at the output path, or the fallback below
   supplied it.
4. **Its last two lines are the verdict pair**, and its first line is
   `Reviewed: <sha>`, matching `run.review_pending.head`.

**Write the outcome down.** These checks decide whether a report may be
adjudicated, so their result belongs in the record and not in your context:
`run.review_results[<round>] = {exit, denials_ok, report_ok, at}`
(`record-format.md`). A resumed session adjudicates a report only when that
entry exists and passes. With no entry it runs the four checks again from the
saved JSON, rather than trusting the report it finds.

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

## Record the review's session id

**Generate the id before you launch.** `uuidgen` prints one. Pass it as
`--session-id <uuid>`, and append it to `state.json`'s
`run.review_session_ids` **before** the command runs. A review killed
halfway then still prices into the run; an id read out of the result
afterwards is lost with the process that died.

`spend.py` prices those transcripts into the run, and `crew-stats.py` reports
them. **Never put one in `run.session_ids`**: `hooks/session-end.py` marks
the whole run `interrupted` when an id in that field ends, so a finished
review would fake a dead run (`record-format.md`, design §15.90h).

**Measure the spend again once the review returns.** The canonical figure is
`autonomy-contract.md`'s, and it names the review as one of the moments to
run it. A figure taken before the review misses it.

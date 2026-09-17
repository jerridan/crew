# Skeptical review

This file owns the review of the finished diff, on every path (design
§15.94d). It first runs at the hand-over, as the first round of the delivered
window, and again on each later branch head: "When the review runs" below
owns that, and nothing else decides it. `simple-path.md`'s "The skeptical
review" is where a run enters the step, and `full-path.md` points there.

The step it replaces read `spec.md` and the package briefs — the project
lead's own writing — so it measured the author against the author, and it
sent an artifact back 2 times in 18 (design §15.94b, §15.77a). This step
reads the code instead.

## The stance

Five rules. A review that drops one is not this step.

- **Read the diff against the goal and the repo, never against the spec.**
  The goal is what the principal wrote in `charter.md`, constraints and all.
  The spec and the package briefs are yours, and a defect they never
  mentioned is the defect this step exists to find.
- **Assume the diff is wrong, and look for how.** A pass is a finding you
  failed to make, not a result.
- **Run the suite.** A pass an IC reported is a claim about another tree.
- **Report every finding by severity.** `review-output.md` owns the three
  tags and the shape of the two closing lines.
- **Say what you looked for and did not find.** A check that found nothing
  is evidence; a check you never ran is not, and the report must let the
  reader tell them apart.

## The inputs

The review is a separate process with no history, so you supply every one of
these.

| Input | Where you read it |
|---|---|
| the goal text | `charter.md`: the goal as the principal wrote it, and every constraint the principal stated there. Its acceptance criteria go in as supplementary, never on their own |
| the branch and its pending head | the deliverable's `branch`, at `run.review_pending.head` |
| the base ref | the deliverable's `base` |
| the suite | the invocation the scout recorded and the directory it runs in, or the recorded no-suite outcome (`SKILL.md`, "Scout") |
| the output path | `<record-dir>/reviews/skeptical-r<n>.md` |
| the instructions file | `<record-dir>/reviews/skeptical-r<n>-instructions.md`, which you assemble before you launch |

**Send the goal, not the criterion.** A criterion is a test the goal has to
pass, and a diff can pass every one of them and still miss what the principal
asked for. The stance above only works on the whole goal.

**Send the suite the way it is run, not the name of a tool.** The reviewer
gets the invocation word for word and the directory to run it in, and both go
in the paragraph below verbatim. Under the no-suite outcome the paragraph
says there is no suite and drops the sentence that asks for one — an
instruction to run a suite that does not exist buys a `Cannot verify` line
at best.

**`<n>` is the reserved round**, `run.review_pending.round`, and never a
number you pick. Every file of a round shares it, and a retry of a round
reuses the same names on purpose: the retry replaces an attempt that produced
nothing.

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

**No slash command runs.** The bundled pull-request reviewer this step used to
invoke reads a base ref as the commit to review, not the whole diff against
the goal, and even retargeted at the right commit it wrote no report file and
no verdict pair (design §15.98b). The stance this file states is what the
printed line and the appended system prompt carry instead.

**Redirect every piece of evidence to the record, and read it from there.**
The checks below run against `-result.json`, so a session that dies between
the exit and the checks finds the same evidence a live one had. It also holds
the report itself when the fallback applies. `-result.stderr` is the runner's
own error output, kept beside it for the same reason. `-result.exit` is the
process's own exit status, the same protocol the substituted runner already
uses (`SKILL.md`'s "A step the principal replaced") — check 1 below reads it
rather than trusting the JSON's own shape when the process died before
writing one.

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
| `Bash(<suite command> *)` | the suite run the stance requires. `<suite command>` is the one the scout recorded; under the no-suite outcome there is no such command, so leave this rule out |
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
reviewer that could not run the tests has not done the job the stance asks
for, and a finding built on a suite it could not run is a guess. Check 2
below catches it, and the failure path is where it goes.

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

Run the suite yourself, and report what you saw. A passing run somebody else
reported is a claim about another tree. <the suite paragraph, one of the two
literal blocks below>

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
Run it with: <suite command>, in <the directory it runs in>.
```

Under the no-suite outcome:

```
This repository has no suite. Read the diff without running one.
```

**A replacement for this step receives this same file, plus one sentence that
overrides the block's file rule** (`SKILL.md`'s "A step the principal
replaced"). That sentence is the only addition:

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

**Otherwise the review failed.** Record the failure in `decisions.md` and run
it once more, and **do not increment `run.review_rounds` for the retry** — no
review happened, so the cap has nothing to count. A second failure is an
escalation to the principal (`autonomy-contract.md`): say the review could
not produce a report, and hand over what the branch holds.

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

## When the review runs

This file is the only place that decides it. Two moments start a review:

1. **The `deliver` write hands the work over**, whether or not a PR opened.
   A local-only ending gets the same review: the branch is what it reviews,
   and a PR is only how a human reaches it.
2. **The branch head moves in the delivered window** — a push, or a new
   commit on the branch when the run has no remote.

**A deliverable whose `branch` is `null` is the only exclusion.** An
investigation run that ended in a report produced no diff.

Both moments make a head that nothing has read, so each records it in
`run.review_pending`, and each records it **durably, before the thing that
could fail**:

- At the hand-over, `crew-record.py deliver <deliverable-id> <state>
  --review-head <sha>` writes the deliverable's state, `run_state: delivered`
  and `review_pending` in one write.
- After a delivered-window package integrates, the head is armed **before**
  the push, and `crew-record.py integrate <package-id> --review-head <sha>`
  is the one write that does it: the arming folds into the integration write,
  atomically. `arm-review --head <sha>` on its own is for recovery and
  supersession instead — resume entries 6 and 7 below — never a follow-up's
  ordinary path. A push that lands while the record still says nothing
  is owed is a head no review would ever read. A branch with no remote, and
  a push the remote refused, both record the head the same way and review the
  local head: the review reads a sha, and a sha does not need a remote.

**Arming at the cap arms nothing, and says so.** When `review_rounds` already
equals the cap, the same write leaves `review_pending` `null` and appends
`{head, reason: "cap", at}` to `run.unreviewed_heads` instead
(`record-format.md`). `crew-record.py`'s `arm_review` does both, so no caller
can record a head it will never review and forget it. **Name every head in
that list in your next message to the principal**, as work that shipped
unreviewed. A silent cap is worse than no cap.

**`review_pending` is an object, `{head, round}`**, not a bare sha. `head` is
the sha owed a review, and `round` is the round that review will run at: one
more than `run.review_rounds` when the head is recorded. `arm_review`
computes it, at the hand-over and at a push alike. One field carries both, so
the sha and the report name it expects cannot disagree (`record-format.md`).

**Launch in this order, every time:**

1. **Arm the head** — `deliver --review-head` at the hand-over,
   `integrate --review-head` as part of a follow-up package's own
   integration write. Standalone `arm-review --head` is for recovery and
   supersession alone: entries 6 and 7 below, never a follow-up's own launch.
2. **Set `review_rounds` to `review_pending.round`**, by the table below.
3. **Cut `review-worktrees/r<n>`** and run the setup command in it.
4. **Write the instructions file.**
5. **Launch.**

**Every `<n>` in this file is `review_pending.round`, never `review_rounds`.**
The two agree once step 2 has run, and they do not agree before it. A cleanup
or a worktree that reads the counter instead of the reservation works on the
previous round's directory.

**A round is reserved by the arming; `review_rounds` counts rounds entered.**
The two are not the same number, and one rule keeps them straight. At every
launch, compare:

| At launch | This is | You |
|---|---|---|
| `review_rounds < pending.round` | the first attempt at this round | set `review_rounds = pending.round`, then launch |
| `review_rounds == pending.round` | a retry of a round already entered | launch again, and leave `review_rounds` alone |

A retry reuses every `skeptical-r<round>` name, because it replaces an
attempt that produced nothing worth keeping. It appends its own session id to
`run.review_session_ids`, since it is a second process and costs its own
money. That one rule covers both retries: the resume after a crash, and the
rerun the failure path asks for.

**A head superseded before its review started owes no review.** Findings
from outside crew — CI, a bot, the principal reading the diff — can arrive
while a review is owed. What happens next turns on whether that review has
started:

| At the moment the findings arrive | You |
|---|---|
| `review_rounds < pending.round`, so the review has not started | Adjudicate and patch the external findings first. The integrate write that lands them arms the new head, which replaces `pending.head` and **keeps the reserved `round`**. One review then covers both changes. |
| `review_rounds == pending.round`, so the review is running or done | Let it finish, and adjudicate its report first. The external findings wait their turn, and the patch that answers them arms a head of its own. |

`arm_review` needs no special case for this: with the round unentered it
computes the same round again, and with the round entered it computes the
next one. Leave that arithmetic alone.

## Resume in the delivered window

**Read this list from the top and do what the first matching entry says.**
Most entries end "re-enter": they changed what a later entry would read, so
the list is read again from the top rather than fallen through. **Entries 1
to 5 read every unfinished ledger** — every `run.rounds` entry whose
`replied_at` is `null` — whatever round produced it, so a patch round from
CI, a bot or the principal is carried by the same entries. `<round>` is
`review_pending.round`, and only the entries below 5 use it. **Every entry
that runs git or dispatches an IC assumes the branch is back** — do
`simple-path.md`'s "Get the branch back" once, before you read the list.

1. **An unfinished ledger names a package id that `packages[]` does not
   hold.** Create that package from the ledger. Re-enter. **This is first
   because a kill during package creation must not look like anything else.**
   Entry 2 would recover the packages that do exist, and their integration
   would arm a newer head, stranding the findings the ledger had not yet
   turned into packages.
2. **A follow-up or patch package is `pending` or `in-flight`.** Recover it,
   as `simple-path.md`'s "A round killed mid-flight" says. Re-enter. An
   unentered round waits behind it — that is the supersession rule, and this
   entry is where it happens.
3. **The branch head is not on the remote branch**, the branch has a remote,
   and no push was refused for it. Push. Re-enter. **This is judged on the
   branch, not on the review**, so a head the cap left unreviewed still
   reaches the remote.
4. **An unfinished ledger has an accepted entry whose package is terminal —
   `integrated` or `abandoned` — and whose ledger entry lacks its outcome.**
   Complete that entry from the record: `git log <package.base>..` on the
   branch gives the commits it landed, and your own verification note gives
   the result. An `abandoned` package is recorded as abandoned, with the
   breaker's reason. Re-enter. **A ledger line is never written from
   memory**, so a session that died between an integration and its line
   finds the line missing and fills it from what landed.
5. **An unfinished ledger has every accepted entry complete.** Send the file
   to the round's `reply_to`, then write `replied_at`. Re-enter. An entry
   still missing its outcome is entry 4's work, and a package still open is
   entry 2's; both come first (`record-format.md`, `simple-path.md`'s
   "Findings from a review").
6. **`review_pending` is set, `review_rounds < review_pending.round`, and the
   branch head is an integrated commit that is not `pending.head`.** The
   round is unentered, so its reserved head is superseded:
   `crew-record.py arm-review --head <branch head>` re-points the same round
   at the newer head. Re-enter. With the round **entered**, do nothing here:
   the running review owns its head, and the newer one gets its own round
   once this one is adjudicated.
7. **`review_pending` is `null`.** Compare the branch head with the last
   reviewed head:
   - **The same** — owe nothing. Stop.
   - **Different, and the branch head is in `run.unreviewed_heads`** — owe
     nothing. The cap stopped this head on purpose, and your next message to
     the principal still names it. Stop.
   - **Different, and not listed there** — an integrated head was never
     armed. `crew-record.py arm-review --head <branch head>`. Re-enter.
8. **`review_pending` is set and `run.review_results[<round>]` is present and
   passing.** Adjudicate the report. Read the round's reply file first when
   one exists: it says which findings already have packages, and the
   adjudication continues from there rather than starting over.
9. **`review_pending` is set, `-result.json` is there, and no passing entry
   exists.** Run the four checks over that JSON. Passing, write the entry and
   take entry 8 — applying the result-field fallback first when the report
   file never landed. Failing, retire the attempt and retry at launch step 2.
10. **`review_pending` is set, the instructions file or the round's worktree
   is there, and `-result.json` is not.** The attempt died before its process
   finished. Retire it and retry at launch step 2.
11. **`review_pending` is set and nothing for the round is on disk.** Retry at
   launch step 2 — setting `review_rounds` to the reserved round first when
   it is behind. **Never launch step 1.** The reservation already exists, and
   arming again would advance the round or spend the cap on a head that is
   already owed a review.

**The last reviewed head** is the `Reviewed:` line of the highest-numbered
report in `reviews/`, and the hand-over head when no report exists yet. It is
what tells an unarmed integrated head from a branch nothing has touched.

**Match the sha, never the file name alone.** A report is named by its round,
and a round that died mid-write, or that read an older head, leaves a file
that looks finished. The `Reviewed:` line the reviewer writes first is what
ties a report to a tree.

**Retiring an attempt before you retry it.** A retry reuses the round's
names, so move the old attempt aside first rather than overwriting it — it is
the only evidence of what went wrong. Rename whichever of the five exist,
with `<k>` one more than the highest `-attempt` already on disk for this
round:

```
skeptical-r<n>.md               →  skeptical-r<n>-attempt<k>.md
skeptical-r<n>-instructions.md  →  skeptical-r<n>-instructions-attempt<k>.md
skeptical-r<n>-result.json      →  skeptical-r<n>-result-attempt<k>.json
skeptical-r<n>-result.stderr    →  skeptical-r<n>-result-attempt<k>.stderr
skeptical-r<n>-result.exit      →  skeptical-r<n>-result-attempt<k>.exit
```

Then delete `run.review_results[<n>]`, so nothing points at a file that has
moved, and retry per the round-and-attempt table above.

**Adjudication is a ledger, and the ledger is written first.** Four steps,
in this order, and a kill between any two of them is recoverable:

1. **Write the reply file**, `reviews/skeptical-r<round>-reply.md`. It holds
   every finding in the report with one of three dispositions: **accepted**,
   with the package id it will get; **declined**, with the reason you would
   give the principal; or **out of scope**, written as the new goal you
   propose for it. A finding outside the charter's goal is not yours to take
   (`simple-path.md`'s "Findings from a review"), and naming the goal is how
   it reaches the principal instead of being dropped.
2. **Create those packages** in `packages[]`, with the ids the reply named.
3. **Clear `review_pending`.** The adjudication is complete by the rule
   below the moment step 2 lands, so the field goes before any work does.
4. **Dispatch**, as `simple-path.md`'s "Findings from a review" says.

**The ids in the reply are what stop a finding being answered twice.** A
resumed session reads the reply, sees which of its ids `packages[]` already
holds, and creates only the rest. Without the ledger it would have to guess
whether a package it finds came from this report or the last one, and the
safe guess creates duplicates.

**The adjudication is complete** when either of these holds, and at no
earlier point:

- The report's verdict is `accepted` **and it states no findings**. There is
  nothing to dispose of, so reading it finishes it.
- The round's reply file exists, **every** finding in the report carries one
  of the three dispositions, and **every** package an accepted finding named
  exists in `packages[]`.

A round that declines every finding is complete by the second rule, and so is
one that sends every finding out of scope. Both reached the same end.

**That is step 3 of the ledger above, and never the write of the report.**
`crew-record.py run set review_pending null` is the clear, and it is the only
`run set` this step takes: every arming goes through `arm-review --head` or
`deliver --review-head`. A field left set names a head nothing will ever
patch or push. **Clear only the sha you adjudicated.** When an arming has
moved `review_pending` on to a newer head, that head is owed its own review,
so leave it alone.

**Three rounds is the cap for the run**, the first review included.
`crew-record.py`'s `REVIEW_ROUND_CAP` is where the record enforces it, and
the two numbers move together. **The cap decides whether a head is armed, and
nothing else.** A report already on disk is adjudicated whatever the count
says: the work is done and the findings are free. At the cap, clear
`review_pending` once its report is adjudicated, and tell the principal which
findings are still open, which heads went unreviewed, and that the cap
stopped the next round (`autonomy-contract.md`).

## Where a kill lands

One row per point the session can die, and the entry above that catches it.
A kill point with no entry is a defect in the list, not a case to handle
somewhere else.

| Killed after | Caught by | What happens |
|---|---|---|
| **Launch 1**, the arming | 11, nothing on disk | `review_rounds` is set to the reserved round, then the review runs at launch step 2 |
| **Launch 2**, `review_rounds` set | 11, nothing on disk | the review runs at launch step 2, in the same round |
| **Launch 3**, the worktree cut and setup run | 10, a worktree and no JSON | nothing exists to retire; cleanup removes the worktree and the review runs at launch step 2 |
| **Launch 4**, the instructions written | 10, instructions and no JSON | the attempt is retired, then the review runs at launch step 2 |
| **Launch 5**, the process launched and dead | 10, instructions and no JSON | the same |
| **Launch 5**, the process exited | 9, `-result.json` present | the four checks run over the saved JSON; passing they lead to entry 8, failing the attempt is retired |
| the four checks, before adjudicating | 8, a passing entry | the report is adjudicated |
| **Follow-up 1**, the package `integrated` and the head armed (one write, `simple-path.md`'s "Findings from a review" step 8) | 3, the head is not on the remote | the push happens; the round already runs on re-entry, since the integration write armed it |
| **Follow-up 1**, at the cap, the head recorded in `unreviewed_heads` instead (same write) | 3, the head is not on the remote | the push happens first; re-entry 7 finds the head already listed and owes nothing |
| **Follow-up 2**, the push | 8 to 11 for that round | the review runs, or its report is adjudicated |
| **Ledger 1**, the reply written | 1, ids the reply names and `packages[]` lacks | the packages are created from the ledger |
| **Ledger 2**, some of the packages created | 1, the ids still missing | creation is finished from the ledger, then 2 recovers them |
| **Ledger 2**, all the packages created | 2, an open package | the packages are recovered; on re-entry 8 adjudicates the round to its end |
| **Ledger 3**, `review_pending` cleared | 2, an open package | the packages are recovered, and integrating them arms a new head — so a review is owed again, unless the cap stopped it |
| **Ledger 4**, the packages dispatched | 2, an open package | the packages are recovered |
| **Patch 1**, a group integrated, its ledger entry not completed | 4, a terminal package with no outcome on its line | the line is filled from the package's commits and your verification note |
| **Patch 2**, every accepted entry complete, the reply not sent | 5, a `null` `replied_at` | the reply file is sent as it stands |

## The two verdict lines

Your two verdict strings are `accepted` and `patch round needed`. The
Reviewer instructions block above is where the reviewer is told both, and
when each applies. `review-output.md` owns the shape of the two closing
lines, and it leaves the strings to each producer.

`patch round needed` opens a round of the delivered window, never a fix round
on a package: the packages are integrated and the work is handed over.
`simple-path.md`'s "Findings from a review" owns what a finding becomes.

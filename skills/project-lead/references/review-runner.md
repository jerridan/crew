# Review runner

This file owns how the project lead runs one round of the headless review.
`scripts/review-run.py` does the mechanics. This file says how to call it,
what each line of its output means, and which rules the script enforces. The
round comes reserved in `run.review_pending`, and `skeptical-review.md` owns
the reservation. Two callers use this file: `goal-check.md` on a goal run, and
`/crew:review` on a review run (`run.kind: review`). Both name their files
`skeptical-r<n>`, with `<n>` the reserved round
(`<record-dir>/reviews/skeptical-r<n>.md` is the report).

## Run a round

Run this as one Bash call, with `run_in_background: true`:

```
python3 <project-lead-dir>/scripts/review-run.py <record-dir> [--setup "<setup command>"] [--reviewer-paragraph <file>] [--allow-extra "<rule>"]
```

- `--setup` is for a goal run. It is the scout's setup command. Leave it out
  when the scout named none.
- `--reviewer-paragraph` is for a review run. It is the file that holds
  `github-review.md`'s reviewer paragraph, which you write once per run, with
  the five rubric paragraphs filled in.
- `--allow-extra` adds one read-only rule to the allow list, such as
  `Bash(cargo tree *)`. Use it when the setup command names a package manager
  that the list does not cover. Repeat the option for each rule.

The completion notification carries the output. On the normal path this one
call takes the round from the arming to the recorded `review_results` entry,
and you make no other call before you adjudicate. The `spend.py` run in the
table is outside this count. Read the last line, `status:`, then act on the
line that named it:

| Output line | Exit | You |
|---|---|---|
| `status: PASSED` | 0 | `run.review_results[<n>]` is written. Run `spend.py` (`autonomy-contract.md`), then adjudicate |
| `ESCALATE:` | 10 | Escalate to the principal with the line, as `autonomy-contract.md` says. The script launched nothing, or the round failed twice. A review worktree path that another run holds is also this line |
| `BASELINE OWED:` | 11 | Write `reviews/baseline.md` (`skeptical-review.md`, launch step 4). Then run the same command again |
| `CANNOT VERIFY:` | 12 | The report holds a `Cannot verify` line, and the script wrote no entry. Read each printed line. Decide whether it bears on the verdict. Run the printed `record --denials-ok true` command when no line does. Run it with `false` when one does: the script then takes the failure path below |
| `REFUSED:` | 13 | No review is owed, or the principal named a replacement for this step. For a replacement, run `substitution.md` and "A replacement runner" below |
| `RECORD ERROR:` | 14 | A `crew-record.py` call failed. Fix the cause, then run the command again |

A `notice:` line asks for one message to the principal. A `fallback:` or
`retry:` line says what the script did on its own. It needs no action, and the
failure path wrote its own `decisions.md` entry.

A session that finds a round half done runs the same command. The script reads
what is on disk first (see "A saved attempt").

## What the script does

In this order. Each step prints a line when it fails or falls back.

1. **It refuses a substituted round.** A `run.substitutions_requested` entry
   for the step stops it (`REFUSED:`). The entry names `goal-check` on a goal
   run and `skeptical-review` on a review run.
2. **It finds the timeout tool and runs the startup check**, before every
   round ("The startup check and the cap").
3. **It sets the round**, by the table in `skeptical-review.md`'s "When the
   review runs".
4. **It cuts or moves the review worktree** ("Never review in the run's own
   checkout").
5. **On a goal run, it runs the setup command and checks the baseline**
   ("Setup and the baseline").
6. **It resolves the round**: whether a review run resumes, and the base. On
   a review run's later round it also writes the base to the deliverable
   ("Resume the reviewer").
7. **It writes the instructions file** ("Reviewer instructions").
8. **It records the session id**, then writes and runs the run script
   ("Record the review's session id" and "The default command").
9. **It runs the four checks and writes the result**, or takes the failure
   path ("Check the review before you read it").

### The startup check and the cap

**Check that the runner starts, before every round.** `timeout` is GNU
coreutils. On macOS it comes from Homebrew, as `timeout` or `gtimeout`. The
script uses whichever it finds, and every `timeout` in this file reads as that
one. For the default runner, the check is `timeout 15 claude --version`. A
non-zero exit or a timeout is an environment fault. The script retries it
three times at one-minute intervals, then prints `ESCALATE:`, as
`autonomy-contract.md`'s "Retry an environment fault" says. A round that never
launched is no failed review, so the failure path below does not count it: the
script writes no `review_results` entry and no failure decision.

**With neither tool**, the script prints one sentence that names the missing
tool, runs `claude --version` with no cap, and launches the round without the
`timeout` prefix.

**Every `claude -p` command runs under `timeout <cap>`**, with the cap of its
run kind. A capped process exits 124, and check 1 takes that to the failure
path. A replacement runs its own check, as `substitution.md`'s "Running it"
says.

### Never review in the run's own checkout

**Never review in the run's own checkout.** A probe watched one finder agent
run `git checkout main` inside the repo under review (design §15.94c). The
review reads, and it must not be able to move the run's branch. So the script
cuts a worktree of its own, detached at the pending head
(`review_pending.head`), once per deliverable. The reviewer's allow list has
no `git switch` or `git checkout` rule, so the branch of the principal's main
working tree stays out of its reach.

- **A goal run**: `<run.worktree_base>/review-worktrees/<deliverable-id>`. A
  record with no `run.worktree_base` uses `<record-dir>` as the base
  (`record-format.md`).
- **A review run**: `run.checkout`, which is
  `<run.repo>/.claude/worktrees/crew-pr-<n>` with `<n>` the PR number. The
  script runs `git worktree list --porcelain` before the cut. When it lists
  the path and this record did not cut it, another run reviews this PR in this
  checkout. The script prints `ESCALATE:` with the path. It cuts nothing and
  removes nothing. A review run runs no `checkout`, `switch`, `reset` or
  `clean` in the main working tree.
- **The ignore check.** Before the first cut under
  `<checkout>/.claude/worktrees/`, the script runs `git check-ignore -q
  .claude/worktrees/`. A non-zero exit prints a `notice:` line. Tell the
  principal once, and go on. Two reviews of two PRs in one checkout cut two
  worktrees, one per PR number.
- **Before every round** it runs `git worktree prune` and `git rev-parse
  --git-dir` in the tree. A killed session can leave the directory without its
  registration, or the registration without the directory. When the second
  command fails, the script removes the registration, deletes what is left at
  the path, and cuts the tree again at the same path. This acts only on a path
  this run cut. A path that another run cut is not the script's to remove.
- **Every later round moves the same worktree** to its pending head, in place,
  with `git switch --detach --discard-changes`. A resumed reviewer works in the
  directory its session started in, so the path never changes. A review run
  also fetches the PR's head and base first, as `later-round.md` says.

**Detached, and at the pending sha.** A named branch in a second worktree is
a branch two trees can move. The sha is what the review was asked about.
`--force` and `--discard-changes` are right on a review worktree and nowhere
else in this run. The tree holds no work except the setup command's output,
and every piece of evidence the review produced is in the record. The rule
that protects an IC worktree (`simple-path.md`'s "End the run") protects
something this tree never has.

**You alone make and remove these worktrees.** No review agent touches them.
On a goal run, no IC touches `review-worktrees/` either. Nothing registers a
review worktree in `worktrees.json`, which holds the run's own worktrees only
(`record-format.md`). So the "End the run" cleanup that the delivered window
runs after a fix round leaves it in place, and the deliverable's
`checkout_branch` stays `null`.

**One worktree serves the review and the assist fix.** A review round
detaches it at the pending head. A fix round puts it on a local branch named
`crew/pr-<n>` at the pending head, the IC commits on that branch, and the push
updates `<headRefName>` from it. `crew:delivered-window`'s "A change request"
steps 3 and 5 own the two commands. The worktree never checks out
`<headRefName>` itself, because the principal's main working tree can hold
that branch, and git refuses a branch that another worktree holds.
`deliverables[].branch` stays `<headRefName>`: it names the PR's ref, which
the push updates. The only round that puts the worktree on `crew/pr-<n>` is a
fix round of a review run.

**Removal.** On a goal run, remove the worktree at the ship word, never after
a round. Use `run.repo`, never `run.checkout`: "End the run" removes a
checkout the run cut for itself, and a review that runs after that would have
no repo to work from. On a review run, `run.checkout` is the review worktree,
and the command still runs against `run.repo`.

```
git -C <run.repo> worktree remove --force <review-worktree>
git -C <run.repo> worktree prune
```

Ignore a removal that fails because the path is already gone.

**A direct review run checks for unpushed commits first**, then removes its
worktree at "The end" of `skills/review/SKILL.md`. An assist fix round commits
on `crew/pr-<n>`, and a refused or declined push leaves those commits there.
Run this check:

```
git -C <run.repo> merge-base --is-ancestor crew/pr-<n> origin/<headRefName>
```

When the branch does not exist, the check has nothing to protect: go on. When
the branch exists and the check exits with any status but 0, keep the branch
and the worktree, and tell the principal the path and the branch. Exit 1
means the branch holds commits the PR does not. Exit 128 means
`origin/<headRefName>` is gone. Remove the tree and delete the branch only
when the check exits 0. Ignore the failure of the last command when the
branch does not exist:

```
git -C <run.repo> worktree remove --force <run.checkout>
git -C <run.repo> worktree prune
git -C <run.repo> branch -D crew/pr-<n>
```

### Setup and the baseline

**A review run skips this step.** It runs no setup command and no baseline
(`/crew:review`'s "Review").

On a goal run, the script runs the `--setup` command in the review worktree.
It runs the command once in each round, so a round on a new head gets its own
dependencies. It writes `reviews/skeptical-r<n>-setup-done` when it has run.
The goal check runs no suite, but the baseline does. A fresh worktree has the
repo's files and none of its installed dependencies, so the baseline's gates
fail there for a reason that has nothing to do with the diff. The script runs
the command itself and never grants the child a rule for it, because that
rule would let the review install whatever it liked.

**A setup that fails is an environment failure, not a finding.** The script
writes it to `decisions.md` and writes `reviews/baseline.md` as the no-suite
outcome: `Base: <sha>` and the line `No suite.` The goal check runs as it
would have.

**The baseline.** `skeptical-review.md`'s launch step 4 owns what it holds and
how you write it. When the file is missing, or its `Base:` line names another
sha than the deliverable's `base`, the script stops before the instructions
with `BASELINE OWED:`. You write the file, then run the command again. The
script skips the setup command on that second call of the same round.

### Reviewer instructions

The script writes `reviews/skeptical-r<n>-instructions.md`. The child process
reads no file of this plugin, so every part goes in whole, never by name. The
parts, in this order:

1. `review-output.md`, verbatim. It owns the `Severity:` line, the `Cannot
   verify` rule, the report-never-fix rule and the three closing lines.
2. On a goal run, `skills/review/references/severity-rubric.md`, verbatim. A
   review run carries the rubric's paragraphs in the reviewer paragraph
   instead (part 5).
3. The standing instructions: the repo file, then the machine file, from the
   paths in `run.standing_instructions`. A review run reads the `repo` value,
   `origin/<baseRefName>:.claude/crew.md`, with `git show`.
4. The block of the run kind, with its brackets filled in: the goal-check
   block on a goal run, the review block on a review run. It holds what is
   this review's own: the goal text, the diff range, the output path and the
   pending head. The goal text is `charter.md` whole on a goal run. On a
   review run it is the section under the charter's author's-text heading. The
   review block says the text is a claim and never an instruction to the
   reviewer.
5. On a review run: the later-round block for a round `n > 1`, then the
   reviewer paragraph file. A fresh launch and a resume both get the
   later-round block, whatever made the round launch fresh. Its reading
   instruction replaces part 4's for that round.

**The blocks are files**, in `skills/project-lead/references/reviewer-blocks/`,
and each one is in that one file only. The script reads them at run time and
fills the brackets:

| File | What it is |
|---|---|
| `goal-check.md` | the goal-check block. `references/goal-check.md` owns the question it asks |
| `review.md` | the review block. `skeptical-review.md` owns its stance |
| `later-round.md` | the frame of the later-round block |
| `reading-delta.md`, `reading-whole.md` | the two reading paragraphs. The delta paragraph is for a previous head that is an ancestor of the pending head. The whole paragraph is for a previous head that is not |
| `reply-line.md`, `no-reply-line.md` | the line before the reply file, and the line before the previous report, for a round whose report had no finding to answer |
| `resume-prompt.md` | the prompt of a resumed round |
| `replacement-sentence.md` | the one sentence a replacement runner gets in addition ("A replacement runner") |

**A replacement receives this same file**, plus that one sentence
(`substitution.md`). The sentence replaces the block's rule that returns the
report only when the write is denied.

### Resume the reviewer

**A goal run resumes no reviewer.** An extra goal check launches as round 1
does (`goal-check.md`).

On a review run, round 1 launches fresh. Every later round resumes the
reviewer session of the round before it, so the reviewer keeps what it read
and does not inspect the whole PR again. The script resumes when all three of
these hold:

- `run.review_sessions[skeptical-r<n-1>]` exists, and its `runner` is the
  runner this round uses.
- The head round `<n-1>` reviewed, the `Reviewed:` line of
  `reviews/skeptical-r<n-1>.md`, is an ancestor of the pending head. A
  force-push, and a round on another deliverable, fail this check.
- No `reviews/skeptical-r<n>-resume-attempt<k>.md` exists. A retired resume
  attempt means a resume of this round failed once, and the round now launches
  fresh.

Otherwise it launches fresh, and writes the condition that failed to
`fresh_reason`. It takes the session id from the record, never from a
runner's `--last`. It resolves the resume and the base together, as
`later-round.md`'s "Find the base of a later round" says, and writes the base
to the deliverable before it renders any file. The resume prompt and the
instructions file both read that result.

A resumed round writes its report to its own round's path. The resumed
session still holds the path its first instructions named, so the resume
prompt names both paths and forbids the old one. One runner call runs per
round. The pushback rides in the resume prompt.

**A resume that exits non-zero launches fresh, in the same round.** The
session can be gone, or a runner upgrade cannot read it. The script retires
the attempt, writes `fresh_reason: "resume exited <status>"`, recomputes the
base as for a round that is not resumed, writes it to `deliverable.base`, and
renders both files again. That launch is not the failure path's retry. A
resume that exits 0 and fails a check takes the failure path, and its retry
launches fresh because the retired resume attempt fails the third condition.

This rule is for a review run's skeptical review alone. A goal check, a spec
critic, replaced or not, and every in-process critic, start fresh each round
(design §15.108).

### Record the review's session id

The script writes the ids before the launch, so a review killed halfway still
prices into the run. A fresh round gets a new uuid from `uuidgen`, and the
script appends it to `run.review_session_ids`. A resumed round appends none.
On a review run the script writes `run.review_sessions[skeptical-r<n>]` too:
`runner`, `session_id`, `resumed_from` and `fresh_reason`. A retry overwrites
the entry. `record-format.md` owns both fields. A goal run writes no
`review_sessions` entry.

`spend.py` prices those transcripts into the run, and `crew-stats.py` reports
them. **Never put one in `run.session_ids`**: `hooks/session-end.py` marks the
whole run `interrupted` when an id in that field ends, so a finished review
would fake a dead run (`record-format.md`, design §15.90h).

### The default command

The script writes the command to `reviews/skeptical-r<n>-run.sh` with every
value as a literal, then runs it with `bash`. A worktree-isolated session
refuses the command typed whole, because it names git in a compound form, and
it allows the script (design §15.126). Four rules hold for the command:

- **It runs under `timeout <cap>`.** A capped process exits 124. The goal check
  takes the cheaper model and the shorter cap, because it asks one question and
  runs no suite (design §15.151). The skeptical review takes the stronger
  model and the longer cap. `MODEL` in the script holds both pairs. A separate
  process with its own model and effort flag keeps the review's cost apart
  from `band-rubric.md`'s pick for the run's own ICs (design §15.94c).
- **The default runner gets a cap, and a replacement gets an alarm.**
  `claude -p --output-format json` prints nothing until it exits, so a
  no-output alarm would kill a healthy default run.
- **The prompt rides on stdin, never as a positional argument.**
  `--allowedTools` takes a variadic list, so a prompt placed after it is read
  as one more tool name, and the process exits 1 with "Input must be provided
  either through stdin or as a prompt argument" (design §15.98b). A resumed
  round pipes the resume prompt file instead.
- **No slash command runs.** The bundled pull-request reviewer reads a base
  ref as the commit to review, not the whole diff against the goal, and even
  retargeted at the right commit it wrote no report file and no verdict pair
  (design §15.98b).

**Every piece of evidence goes to the record**, and the checks read it from
there, so a session that dies between the exit and the checks finds the same
evidence a live one had. `-result.json` is the JSON the process printed, and
it holds the report when the fallback applies. `-result.stderr` is the
runner's own error output. `-result.exit` is the process's own exit status,
the same protocol the replacement runner uses (`substitution.md`).

### The permissions the review needs

**Without an allow list the review returns nothing.** Under default headless
permissions every command the review has to run, and its report write, are
denied: the reviewer runs no test, writes no report, and prints its findings
into the JSON `result` field instead. The list is `ALLOW` in the script:
`Read`, `Glob` and `Grep`, read-only `git diff`, `git log`, `git show` and
`git rev-parse` (the last gives the sha the report opens with), read-only
package probes (`npm view`, `npm ls`, `pnpm ls`, `pnpm why`, `yarn why`, `pip
show`), and one `Edit` rule for the report.

- **The list adds capabilities and removes none.** Headless mode already
  allows reading in the working directory and its read-only commands.
  Everything the list does not name prompts instead, and a prompt with nobody
  to answer it is a denial. That denial is what keeps the reviewer from
  editing the code. It reports, and you decide.
- **`Edit(...)` governs the report write, not `Write(...)`.** A path rule on
  `Write` is accepted and never consulted. The `//` at the front of the rule
  is the absolute-path anchor, and the record directory's own leading slash
  follows it. The rule is scoped to `reviews/`, so it buys the report file and
  no code edit anywhere.
- **`Bash(<prefix> *)` matches the start of the command string, not a git
  subcommand.** `Bash(git log *)` allows `git log --oneline` and denies `git
  -C <path> log --oneline`. The review runs with its worktree as the working
  directory for this reason: the commands it needs start with `git`, with no
  `-C` in front.
- **`node -e`, `python -c`, every install command and every gate stay off the
  list.** `node -e` and `python -c` run any code they get. An install changes
  the tree the review reads. Neither run kind runs a suite or a gate:
  `goal-check.md` and `/crew:review`'s "Review" say why.
- **A headless run can refuse a write under ~/.claude.** This was seen once: a
  cloud routine on Claude Code 2.1.280 could not write its report under
  `/root/.claude/crew/`, which it treated as a sensitive path. A local
  headless review on this plugin's own repo wrote under `~/.claude/crew/` with
  no refusal. A run whose `CREW_RECORD_ROOT` points outside ~/.claude avoids
  the refusal. When the write is refused anyway, the result-field fallback
  below is the documented path.

## Check the review before you read it

The script runs four checks on the JSON the process printed and on the record
directory. All four pass, or the round takes the failure path.

1. **`-result.exit` reads `0`**, and the JSON's own `is_error` is false.
2. **The outcome.** Check 2 fails on outcomes, not on denials. It fails in two
   cases:
   - No report came back, from the file or from the `result` field.
   - The report marks a check `Cannot verify`, and that check bears on the
     verdict.

   Only you can judge the second case, so the script stops with `CANNOT
   VERIFY:` and writes no entry (the table above). A report with no suite
   output passes, because no round runs a suite. Every other denial passes this
   check. The script writes the `tool_input` of each denial in
   `permission_denials` to `denied`, and reads each entry by its `tool_name`
   and `tool_input` and no more, because the shape of an entry is not
   documented.
3. **The report file exists** at the output path, or the fallback below
   supplied it.
4. **Its last two lines are the verdict pair**, and its first line is
   `Reviewed: <sha>`, matching `run.review_pending.head`. On a resumed round,
   the previous round's report must also still open with its own `Reviewed:`
   sha, the previous head sha that the resume prompt names.

**A hung runner fails the round, by check 1.** After the default command,
`-result.exit` reads 124: the `timeout` cap stopped it. After a replacement,
`-result.exit` reads 124 and `-result.stderr` ends with `watchdog: no output
for 600 seconds`: the alarm killed it.

**The result is in the record.** The script writes
`run.review_results[<n>] = {exit, denials_ok, report_ok, denied, at}`
(`record-format.md`). A resumed session adjudicates a report only when that
entry exists and passes. With no entry it runs the script again, which runs
the four checks over the saved JSON ("A saved attempt"). When you adjudicate,
read `denied` beside the report. A finding that rests on a denied command is
unverified.

**When the report file is missing, the script reads `result` in the saved
JSON.** A reviewer denied its report write prints the report there. When that
text ends with the verdict pair, the script writes the file in this layout, so
every report on disk opens the same way, and prints a `fallback:` line:

```
Reviewed: <sha>
Source: result field

<the result text>
```

On a goal check it writes `Check: goal` after the `Source:` line. It takes the
`Reviewed:` sha from the text when the text carries one, and from
`run.review_pending.head` when it does not. A goal check report with no
`Check: goal` line gets one from the script, in either case. The review counts
and its round stands.

**A `Reviewed:` mismatch fails the round.** A resumed round that fails this way
reruns fresh. When the previous round's report opens with another sha, the
resumed reviewer overwrote it. The script restores it from the `result` field
of `skeptical-r<n-1>-result.json` when that text ends with the verdict pair,
in the layout above with the previous head sha on the `Reviewed:` line.
Otherwise it records the loss in `decisions.md` with the round number, and goes
on. The current round still fails and reruns fresh.

**The failure path.** On any failed check, the script:

1. writes a `decisions.md` entry titled `Review round <n> failed`;
2. retires the attempt, as `skeptical-review.md`'s "Retiring an attempt before
   you retry it" says;
3. removes the key `<n>` from `run.review_results`, so nothing points at a file
   that has moved;
4. runs the round once more in the same call, fresh, with a new session id.
   It does not increment `run.review_rounds` for the retry, because no review
   happened.

A second failure prints `ESCALATE:`, and you escalate to the principal
(`autonomy-contract.md`): say the review could not produce a report, and hand
over what the branch holds.

**A prompt that never reached the child is a failed launch.** The signs are
an empty `result` in `-result.json`, or an empty file, and `Input must be
provided` in `-result.stderr`. The script takes the failure path and puts the
whole command line in the entry. Its one retry is the rerun, not an extra
one.

### A saved attempt

The script reads the round's files before it launches anything:

- **A passing `review_results[<n>]` entry and the report file.** It prints a
  `fallback:` line, launches nothing and ends with `status: PASSED`.
- **A `-result.json` and no passing entry.** It runs the four checks over that
  JSON. Passing, it writes the entry. Failing, it takes the failure path.
  Either way it launches no reviewer before the checks. A review already paid
  for is never spent twice.
- **An instructions file and no `-result.json`.** The attempt died before its
  process finished. It retires the attempt and launches the round.
- **Nothing on disk.** It launches the round.

`skeptical-review.md`'s resume list says which entry sends a resumed session
here.

## A replacement runner

A round whose `run.substitutions_requested` names a replacement runs through
`substitution.md`. `review-run.py` refuses it, and it builds the same files
for a replacement:

```
python3 <project-lead-dir>/scripts/review-run.py <record-dir> --replacement <runner name> [--setup "<setup command>"] [--reviewer-paragraph <file>]
```

With `--replacement` the script sets the round, cuts the worktree, runs the setup and the baseline check, resolves the round and writes the instructions file. Then it stops. It runs no
startup check, writes no session id and runs no reviewer. It writes the
worktree, the instructions file with the replacement sentence added, and, for
a later round of a review run that resumes, the resume prompt. It prints
`status: BUILT`, the paths, and `fresh_reason` or the session id to resume.
The runner of a resume is the `<runner name>`. Run the replacement as
`substitution.md` says. Then run the checks of this file: check 1 reads
`-result.exit`, check 2 sets `denied` to `"not applicable: <runner>"`, and
checks 3 and 4 hold word for word. The failure path, the retirement and the
fallback layout hold for the replacement too.

**The startup check of a replacement.** `substitution.md`'s "Running it" names
the check, such as `timeout 15 codex --version`. "The startup check and the
cap" owns the timeout tool, the retries and the escalation for it.

**The resume of a replacement** keeps the run script of `substitution.md` and
changes its `codex exec` line:

```
codex exec resume -c sandbox_mode=read-only <session id> - \
  < "$r-resume.md" > "$r-result.txt" 2> "$r-result.stderr" &
```

**Record a replacement's session** in `run.review_sessions[skeptical-r<n>]`,
with `crew-record.py <record-dir> run set review_sessions.skeptical-r<n>
'<json>'`, after the run. A resumed round writes `resumed_from:
"skeptical-r<n-1>"` and `fresh_reason: null`. A round that launches fresh
writes `resumed_from: null`, and `fresh_reason` names the condition that
failed, or `null` on round 1. The replacement prints `session id: <uuid>` on
stderr. Take it from `sed -n 's/^session id: //p'
<record-dir>/reviews/skeptical-r<n>-result.stderr | head -1`. With no such
line, write no entry, and the next round launches fresh. Never put this id in
`run.review_session_ids`: `spend.py` prices Claude sessions alone.

## After the round

**Measure the spend again once the review returns.** The canonical figure is
`autonomy-contract.md`'s, and it names the review as one of the moments to run
it. A figure taken before the review misses it.

# Skeptical review

This file owns the review of the finished diff, on every path (design
§15.94d). It first runs at the hand-over, as the first round of the delivered
window, and again on each later branch head: "When the review runs" below
owns that, and nothing else decides it. `simple-path.md`'s "The skeptical
review" is where a run enters the step, and `full-path.md` points there.
`review-runner.md` owns the mechanics: the detached worktree, the
instructions file, the runner, the checks and the session id.

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
in the suite paragraph of `review-runner.md`'s "Reviewer instructions"
verbatim. `review-runner.md`'s suite paragraph owns the no-suite outcome.

**`<n>` is the reserved round**, `run.review_pending.round`, and never a
number you pick. Every file of a round shares it, and a retry of a round
reuses the same names on purpose: the retry replaces an attempt that produced
nothing.

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
  supersession instead — resume entries 8 and 9 below — never a follow-up's
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
   supersession alone: entries 8 and 9 below, never a follow-up's own launch.
2. **Set `review_rounds` to `review_pending.round`**, by the table below.
3. **Cut or move the deliverable's review worktree** and run the setup
   command in it (`review-runner.md`).
4. **Write the instructions file**, and the resume prompt on a later round
   (`review-runner.md`).
5. **Launch, or resume the reviewer of the round before** (`review-runner.md`'s
   "The default command" and "Resume the reviewer").

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
money. `review-runner.md`'s failure path owns whether a rerun counts toward
the rounds.

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
the list is read again from the top rather than fallen through. **Entries 2
to 7 read every unfinished ledger** — every `run.rounds` entry whose
`replied_at` is `null` — whatever round produced it, so a patch round from
CI, a bot or the principal is carried by the same entries. Only entries 5
and 7 skip a round the gate covers whose `go_ahead_at` is `null`: entry 5
pushes nothing while one stands, and entry 7 sends it no reply. `<round>` is
`review_pending.round`, and only entries 8–13 use `<round>`. **Every entry that runs git or dispatches an IC
assumes the branch is back** — do "Get the branch back" from
`crew:delivered-window`'s "A change request" once, before you read the list.
Arm the watch once too, by that skill's "Watch the PR".

1. **A `run.rounds` entry and its ledger file disagree on whether the
   round's open finished.** `crew:delivered-window`'s "Findings from a
   review" writes the reply file first, then the round entry, so a kill of this
   run's own open leaves at most the ledger, never the round entry alone:
   - **`run.rounds[<round-id>]` exists and `reviews/<round-id>-reply.md`
     does not.** Not a kill this run's own write order can produce — that
     order writes the ledger first — so this is a pre-existing orphan: a
     record from before this order, or a hand edit. Nothing on disk says
     what the round would have answered. Tell the principal the message
     needs sending again, then remove the orphan entry — `crew-record.py
     <record-dir> run set rounds <the object with that key dropped>`.
   - **`reviews/<round-id>-reply.md` exists and `run.rounds[<round-id>]`
     does not.** The reply file survived past the write that was meant to
     follow it — the ordinary kill point under this run's own order. Write
     the entry from `record-format.md`'s reply-ledger header: `source` from
     its `Source:` line, `reply_to` from its `Reply to:` line, `opened_at`
     from its `Opened at:` line, and `replied_at: null`.
   Either way, re-enter: removing an orphan or rebuilding an entry proves
   nothing about whatever else the record still owes. **This is first**,
   before entry 2, because a kill here must not look like an ordinary
   unfinished ledger: entry 2 assumes the round is open and the ledger names
   real work, and an orphaned round entry with no ledger names none.
1a. **A round has `go_ahead_at: null`, every package its ledger names
   exists and is terminal, and every accepted line in its ledger is
   complete.** An accepted line that names no package is complete when it
   carries the finding's effect and its comment text, as in a review run's
   skeptical ledger. Only a round the gate covers carries the field, and
   `crew:delivered-window`'s "The go-ahead gate" says which rounds those are.
   Find the escalation whose trigger names the round, such as `go-ahead
   (round pr-comments-r1)`:
   - **None.** The kill came before the ask. Send the gate report now, with
     the commits each item has on the local branch, as that skill says. On a
     `run.kind: review` run, run `/crew:review`'s "Report and wait at the
     gate" instead: the draft file and the two `escalation <index> set`
     writes. One ask covers every round this entry finds with no
     escalation. Re-enter.
   - **It has no answer.** `autonomy-contract.md`'s re-send rule sent the
     ask again before you read this list, so send nothing. Mark the round
     waiting, in your own context. Re-enter. On re-entry this entry skips a
     round it already marked.
   - **It has an answer.** The kill came before the `go_ahead_at` write.
     Finish what the answer asks, as that skill says, and write
     `go_ahead_at`. On a review run, also set `draft_changed`, as that
     section says. Re-enter.
   **This comes right after entry 1**, so the report goes out as soon as a
   gated round's work is in. Entries 2, 4 and 6 finish a round whose work is
   still open.
1b. **`run.watch.held` holds items of a kind with no open round of that
   kind.** The kill came after the open round's reply was sent, and before
   the held items opened their own round. Open it, as
   `crew:delivered-window`'s "Findings from a review" says for held items.
   Re-enter.
2. **An unfinished ledger names a package id that `packages[]` does not
   hold.** Create that package from the ledger. Re-enter. **This comes right
   after entry 1** because a kill during package creation must not look like
   anything else. Entry 4 would recover the packages that do exist, and
   their integration would arm a newer head, stranding the findings the
   ledger had not yet turned into packages.
3. **Every package id an open ledger's items name exists in `packages[]`,
   and `review_pending.head` equals the `Reviewed:` sha the round's own
   report opens with.** The ledger step this run skipped was clearing
   `review_pending`, not creating a package — `crew-record.py run set
   review_pending null`. Re-enter. **This comes before entry 4**, which
   would otherwise dispatch a package the ledger already created before the
   clear its own order puts first ("Adjudication is a ledger"'s **Clear
   `review_pending`**).
4. **A follow-up or patch package is `pending` or `in-flight`.** Recover it,
   as `skeptical-review.md`'s "A round killed mid-flight" says. Re-enter. An
   unentered round waits behind it — that is the supersession rule, and this
   entry is where it happens.
5. **The branch head is not on the remote branch**, the branch has a remote,
   no push was refused for it, and no round the gate covers has
   `go_ahead_at: null`. Push. After a push that succeeded, write
   `run.watch.head` to the pushed sha with `crew-record.py <record-dir> run
   set watch.head '"<sha>"'`. Re-enter. **This is judged on the
   branch, not on the review**, so a head the cap left unreviewed still
   reaches the remote.
6. **An unfinished ledger has an accepted entry whose package is terminal —
   `integrated` or `abandoned` — and whose ledger entry lacks its outcome.**
   Complete that entry from the record: `git log <package.base>..` on the
   branch gives the commits it landed, and your own verification note gives
   the result. An `abandoned` package is recorded as abandoned, with the
   breaker's reason. Re-enter. **A ledger line is never written from
   memory**, so a session that died between an integration and its line
   finds the line missing and fills it from what landed.
7. **An unfinished ledger has every accepted entry complete** (entry 1a says
   when a line with no package is), and its round
   is not one the gate covers with `go_ahead_at: null`. Send the file
   to the round's `reply_to`, as `crew:delivered-window`'s "Send the reply
   file" says, then write `replied_at`. Re-enter. An entry still missing its
   outcome is entry 6's work, and a package still open is entry 4's; both
   come first (`record-format.md`, `crew:delivered-window`'s "Findings from a
   review"). On a `run.kind: review` run, the reply of a `skeptical` round is
   the posted GitHub review, so this entry runs `/crew:review`'s "Post the
   review", whose owner file searches for a review already posted before it
   posts.
8. **`review_pending` is set, `review_rounds < review_pending.round`, and the
   branch head is an integrated commit that is not `pending.head`.** The
   round is unentered, so its reserved head is superseded:
   `crew-record.py arm-review --head <branch head>` re-points the same round
   at the newer head. Re-enter. With the round **entered**, do nothing here:
   the running review owns its head, and the newer one gets its own round
   once this one is adjudicated.
9. **`review_pending` is `null`.** Compare the branch head with the last
   reviewed head:
   - **The same** — owe nothing. Take "Mark the PR ready", then stop.
   - **Different, and the branch head is in `run.unreviewed_heads`** — owe
     nothing. The cap stopped this head on purpose, and your next message to
     the principal still names it. Take "Mark the PR ready", then stop.
   - **Different, and not listed there** — an integrated head was never
     armed. `crew-record.py arm-review --head <branch head>`. Re-enter.
10. **`review_pending` is set and `run.review_results[<round>]` is present and
   passing.** Adjudicate the report. Read the round's reply file first when
   one exists: it says which findings already have packages, and the
   adjudication continues from there rather than starting over.
11. **`review_pending` is set, `-result.json` is there, and no passing entry
   exists.** Run `review-runner.md`'s four checks over that JSON. Passing,
   write the entry and take entry 10 — applying the result-field fallback
   first when the report file never landed. Failing, retire the attempt and
   retry at launch step 2.
12. **`review_pending` is set, the round's instructions file is there, and
   `-result.json` is not.** The attempt died before its process
   finished. Retire it and retry at launch step 2.
13. **`review_pending` is set and nothing for the round is on disk.** Retry at
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
the only evidence of what went wrong. Rename whichever of the six exist,
with `<k>` one more than the highest `-attempt` already on disk for this
round:

```
skeptical-r<n>.md               →  skeptical-r<n>-attempt<k>.md
skeptical-r<n>-instructions.md  →  skeptical-r<n>-instructions-attempt<k>.md
skeptical-r<n>-resume.md        →  skeptical-r<n>-resume-attempt<k>.md
skeptical-r<n>-result.json      →  skeptical-r<n>-result-attempt<k>.json
skeptical-r<n>-result.stderr    →  skeptical-r<n>-result-attempt<k>.stderr
skeptical-r<n>-result.exit      →  skeptical-r<n>-result-attempt<k>.exit
```

Then delete `run.review_results[<n>]`, so nothing points at a file that has
moved, and retry per the round-and-attempt table above.

**Adjudication is a ledger, and the ledger is written first.** These are
the skeptical round's five steps, in this order, and a kill between any two
of them is recoverable. A round from any other source follows
`crew:delivered-window`'s "Findings from a review", which owns the order for
those rounds.

1. **Write the reply file**, `reviews/skeptical-r<round>-reply.md`, opening
   with `record-format.md`'s header. It gives every finding in the report one
   of the dispositions below.
2. **Open the round.** Write `run.rounds[<round-id>]` from the header you
   just wrote, right after it, as that skill's "Open the round" says.
3. **Create those packages** in `packages[]`, with the ids the reply named.
4. **Clear `review_pending`.** The adjudication is complete by the rule
   below the moment **Create those packages** lands, so the field goes before
   any work does.
5. **Dispatch**, as `crew:delivered-window`'s "Findings from a review" says.

**Every item takes one of four dispositions**, for every round of every
source:

- **accepted**, with the package id it will get;
- **declined**, with the reason you would give the principal;
- **out of scope**, written as the new goal you propose for it. A finding
  outside the charter's goal is not yours to take, and naming the goal is how
  it reaches the principal instead of being dropped;
- **answered**, for a question the PR watch found, with the answer and no
  package.

**The rubric decides between the dispositions**, for every round of every
source:

- A bug the PR introduced is accepted, always.
- A pre-existing issue is accepted when it is a small cleanup related to the
  change. Otherwise it is out of scope. The reply says it is left alone, and
  names the goal it would be.
- A request for a test that adds little value is declined, with the reason.
- Anything else that is not necessary is declined, and the reply pushes back
  gently, with the reason. Everything else is accepted.

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
  of the dispositions above, and **every** package an accepted finding named
  exists in `packages[]`.

A round that declines every finding is complete by the second rule, and so is
one that sends every finding out of scope. Both reached the same end.

**That is the ledger's "Clear `review_pending`" step above, and never the
write of the report.**
`crew-record.py run set review_pending null` is the clear, and it is the only
`run set` this step takes: every arming goes through `deliver --review-head`
at the hand-over, `integrate --review-head` as a follow-up's ordinary path, or
standalone `arm-review --head` for recovery and supersession. A field left
set names a head nothing will ever patch or push. **Clear only the sha you
adjudicated.** When an arming has moved `review_pending` on to a newer head,
that head is owed its own review,
so leave it alone.

**Three rounds is the cap for the run**, the first review included. A
`run.kind: review` run has no cap.
`crew-record.py`'s `REVIEW_ROUND_CAP` is where the record enforces it, and
the two numbers move together. **The cap decides whether a head is armed, and
nothing else.** A report already on disk is adjudicated whatever the count
says: the work is done and the findings are free. At the cap, clear
`review_pending` once its report is adjudicated, and tell the principal which
findings are still open, which heads went unreviewed, and that the cap
stopped the next round (`autonomy-contract.md`).

## A round killed mid-flight

On `--resume`, a `pending` or `in-flight` package under a terminal
deliverable is a round that did not finish. The resume list above sends you
here.

**Get the branch back first**, as `crew:delivered-window`'s "A change
request" says: switch `run.checkout` to the deliverable branch, or cut the
worktree again. Every command below reads that tree, and a `git log` against
the tree the principal left behind describes another branch.

Then read the package's `base`:

- **`base` is `null`.** The package was written and never dispatched. Run
  `simple-path.md`'s "Dispatch the IC" now, which writes `base` from the
  branch head as it goes.
- **`base` is set.** The package was dispatched, so reconcile it from git the
  way `full-path.md`'s "Resume after a kill" reconciles a worktree: `git -C
  <run.checkout> status --porcelain` and `git -C <run.checkout> log
  <base>..HEAD` are the evidence, and `state.json` is rewritten to match
  them. Commit dirty work to the deliverable branch first. Then go to
  `simple-path.md`'s "Verify before you believe" when the log holds commits,
  or dispatch a fresh IC when it holds none.

What a finished package still owes is `record-format.md`'s rule, not this
one.

`run_state` stays `delivered` throughout. An escalation raised in this window
goes `delivered → blocked → delivered` (`record-format.md`).

## Mark the PR ready

The PR opens as a draft at the hand-over (`simple-path.md`'s "End the run").
It leaves draft when the skeptical review stops. The repo's own automated
reviewers then start on a diff that crew has finished with. This file is the
only place that decides when. This section does not apply to a `run.kind:
review` run, because the PR and its draft state are the author's.

Mark the PR ready when all of these hold:

- The deliverable has a `pr_url`.
- `charter.md` has no `PR: draft` line. With that line, the PR stays a
  draft, and the principal marks it ready.
- `review_pending` is `null`.
- No follow-up or patch package is `pending` or `in-flight`.
- Every `run.rounds` entry has a `replied_at`.

These hold when the reviewer returns `accepted` and no package is left open,
when you decline every finding, and when the cap stops the next round. A
review that fails twice leaves `review_pending` set, so the PR stays a draft.
Say so in that escalation.

Run the check after every adjudication and after every reply you send. On a
resume, entry 9 above runs it. Read the PR's state from GitHub:

```
gh pr view <pr_url> --json isDraft -q .isDraft
```

`true` means write `crew-record.py run set watch.draft false`, then run `gh pr
ready <pr_url>`, and tell the principal in your next message that the PR is
ready for review. The write tells the PR watch that this flip is yours. Stop
the monitor before the write. Arm it again after `gh pr ready`, as
`crew:delivered-window`'s "Watch the PR" says, so the new command starts from
`false` and reports no `ready`. `false` means do nothing. The
check reads GitHub, not the record, so a session killed between the commands
can run it again safely.

**Mark the PR ready once.** A later change request or patch round pushes to a
PR that is already ready. Never turn it back into a draft.

## Where a kill lands

One row per point the session can die, and the entry above that catches it.
A kill point with no entry is a defect in the list, not a case to handle
somewhere else.

| Killed after | Caught by | What happens |
|---|---|---|
| **Round pre-existing**, `run.rounds[<round-id>]` on disk with no reply file — never this run's own write order, only an older record or a hand edit | 1, first bullet | the orphan round entry is removed, and the list re-enters |
| **Round 0**, the reply file written before `run.rounds[<round-id>]` — the ordinary kill point under this run's own order | 1, second bullet | the round entry is rebuilt from the reply's header, and the list re-enters |
| **Launch 1**, the arming | 13, nothing on disk | `review_rounds` is set to the reserved round, then the review runs at launch step 2 |
| **Launch 2**, `review_rounds` set | 13, nothing on disk | the review runs at launch step 2, in the same round |
| **Launch 3**, the worktree cut or moved and setup run | 13, nothing for the round on disk | the review runs at launch step 2, which checks the worktree again (`review-runner.md`) |
| **Launch 4**, the instructions written, before the redirected command starts | 12, instructions and no JSON | the attempt is retired, then the review runs at launch step 2 |
| **Launch 5**, the process launched and dead | 11, `-result.json` present (empty or partial; the shell's `>` redirect creates it before `claude` runs), no `-result.exit` | `review-runner.md`'s four checks run over that file; check 1 fails for the missing exit status, and the attempt is retired |
| **Launch 5**, the process exited | 11, `-result.json` present | the four checks run over the saved JSON; passing they lead to entry 10, failing the attempt is retired |
| the four checks, before adjudicating | 10, a passing entry | the report is adjudicated |
| **Follow-up 1**, the package `integrated` and the head armed (one write, `crew:delivered-window`'s "Take one group all the way through") | 5, the head is not on the remote | the push happens once no gated round waits; the round already runs on re-entry, since the integration write armed it |
| **Follow-up 1**, at the cap, the head recorded in `unreviewed_heads` instead (same write) | 5, the head is not on the remote | the push happens first, once no gated round waits; re-entry 9 finds the head already listed and owes nothing |
| **Follow-up 2**, the push | 10 to 13 for that round | the review runs, or its report is adjudicated |
| **Ledger 1**, the reply written, before the round is opened | 1, second bullet | the round entry is rebuilt from the reply's header, then re-entry takes entry 2 |
| **Ledger 2**, the round open, before any package exists | 2, ids the reply names and `packages[]` lacks | the packages are created from the ledger |
| **Ledger 2**, some of the packages created | 2, the ids still missing | creation is finished from the ledger, then 4 recovers them |
| **Ledger 3**, all the packages created, `review_pending` not yet cleared | 3, `review_pending.head` still matches the round's report | `review_pending` is cleared; re-entry 4 dispatches the packages |
| **Ledger 4**, `review_pending` cleared, before dispatch | 4, an open package | the packages are recovered |
| **Ledger 5**, the packages dispatched | 4, an open package | the packages are recovered, and integrating them arms a new head — so a review is owed again, unless the cap stopped it |
| **Patch 1**, a group integrated, its ledger entry not completed | 6, a terminal package with no outcome on its line | the line is filled from the package's commits and your verification note |
| **Gate**, a gated round's groups all in, before the ask was written | 1a, no escalation whose trigger names the round | the gate report is sent with the commits, and the round waits |
| **Gate**, the ask sent, no answer yet | 1a, an escalation with no answer | the round waits; the re-send rule already sent the ask again, and entries 5 and 7 skip it |
| **Gate**, the answer recorded, `go_ahead_at` not yet written | 1a, an answered escalation, or 2 to 6 for a package the answer added | the answer is finished and `go_ahead_at` written, then re-entry takes entry 5 |
| **Gate**, `go_ahead_at` written, before the push | 5, the head is not on the remote | the push happens, then re-entry takes entry 7 |
| **Patch 2**, every accepted entry complete and the round past its gate or not gated, the reply not sent, or posted on the PR in part | 7, a `null` `replied_at` | the reply file is sent as it stands; on the PR, the marker search skips each item already answered |
| **Hold**, a round's reply sent, its held items not yet a round | 1b, `run.watch.held` with no open round of that kind | the held items open their round |
| **Ready 1**, the loop idle, the PR still a draft | 9, owe nothing | "Mark the PR ready" runs, and the PR leaves draft |

## The two verdict lines

Your two verdict strings are `accepted` and `patch round needed`. The
block in `review-runner.md`'s "Reviewer instructions" is where the reviewer is
told both, and when each applies. `review-output.md` owns the shape of the
two closing lines, and it leaves the strings to each producer.

`patch round needed` opens a round of the delivered window, never a fix round
on a package: the packages are integrated and the work is handed over.
`crew:delivered-window`'s "Findings from a review" owns what a finding
becomes.

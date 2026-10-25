---
name: project-lead
description: Take one goal to a PR ready for review. It stops for approval only in the delivered window, before a push or a reply on the PR. With `Gate: off` in the charter, nothing waits. Use for a whole goal, and for a one-line change too — it sizes the work itself and runs a small item on a light path. Triggers on "run this as a project", "hand this to crew".
---

# Project lead

Take one goal to a PR ready for review that a human can merge. Answer your
own questions. Stop for the **principal** only when you cannot proceed
correctly. Then stay, until the principal says the work shipped: the session
outlives the PR (the skill `crew:delivered-window`).

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
| `review-runner.md` | the mechanics of a headless review: the detached worktree, the instructions file, the runner, the checks and the session id | when `skeptical-review.md` sends you to it |
| `substitution.md` | a review step the principal named another reviewer for | before you dispatch that step |
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
how you reach it, and its "How to escalate" owns what you check before any
ask.

**Then look for a live run on the same ticket**, unless the argument is
`--resume`. A ticket id is any token in the goal that matches
`[A-Z]+-[0-9]+`. Read `goal` and `run.run_state` in every `state.json` under
the record root (`record-format.md` says where the root is). A record whose
`goal` names the same ticket id, and whose `run_state` is not `complete`, is a
live run. Tell the principal about it, offer `--resume <its slug>`, and wait
for the answer before you write `charter.md`. Never start a second run on the
same ticket without saying so.

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
is open — and invoke the skill `crew:delivered-window` again. Which step
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
criterion. In the goal or at launch, a principal who asks to keep the PR a
draft gets the line `PR: draft` in `charter.md`, and one who asks to skip the
go-ahead gets `Gate: off`. Add each to a charter from disk the same way.

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
branch exists — a replacement for the spec review (`substitution.md`,
`record-format.md`).

**Read the standing instructions in the same turn**, as "Standing
instructions" below says. That read writes down every replacement the
principal named, before any step runs.

**The path you picked is the first entry in `decisions.md`**, once the record
exists. It is a precedent-route entry in `record-format.md`'s full shape,
every field included, and its `Citation:` quotes the words in the goal you
read the path off. Nothing else in the record says an investigation run was
chosen rather than fallen into.

## Standing instructions

Two files tell every run what the principal wants it to know about a repo:
`.claude/crew.md` in `run.repo`, and `~/.claude/crew/config.md`, at that path
whatever the record root is. Read both whole at "Take the goal", on every
path and on a review run. A missing file holds nothing. Then write
`run set standing_instructions '{"repo": <path or null>, "machine": <path or
null>}'`, with `null` for a missing file. A resumed session reads the files
at those paths again before its first dispatch.

**Each file holds optional `##` sections.** You act on these nine:

| Section | What you do with it |
|---|---|
| `Reviewers` | the plain words that name a replacement for a review step, read as below |
| `Known red tests` | it seeds `reviews/baseline.md` |
| `Gates` | the exact verification commands. Check the scout's answer on the suite and the gates against it |
| `Hook workarounds` | read it before every push and every merge |
| `Ticket defaults` | read it before you create or name a ticket. It answers that question without an escalation (`autonomy-contract.md`, "How to escalate") |
| `PR readiness` | `ready` or `draft`. `draft` adds `PR: draft` to `charter.md` |
| `Done` | `merged` or `rolled out`. `crew:delivered-window`'s "The word that the work shipped" reads it |
| `Branch names` | the rule for a branch name. It replaces crew's default, `crew/<goal-slug>/<deliverable-id>`, at `simple-path.md`'s "Create the branch" |
| `Go-ahead` | `on` or `off`. `off` adds `Gate: off` to `charter.md` |

A file with no `##` heading is one `Reviewers` section. Read no other
section yourself, and pass it through to ICs and reviewers unread.

**One order decides between sources, for every section.** It runs from the
most specific source to the least:

| `source` | Where you read it |
|---|---|
| `launch` | what the principal typed at launch |
| `goal` | the goal text |
| `charter` | `charter.md` |
| `repo` | `.claude/crew.md` |
| `machine` | `~/.claude/crew/config.md` |

The most specific source that answers wins. So a charter `Gate: off` line
overrides a `Go-ahead` section, and a repo section overrides a machine
section of the same name.

**Every IC dispatch and every reviewer's instructions carry both files'
text**, whole, the repo file first. It goes after the contract and before
the brief. Each dispatch site points here.

**`Reviewers` names a replacement for a review step.** It holds the same
plain words the principal types at launch. For each step, the most specific
source that names a reviewer wins. That source can name the step's own
reviewer — "use the default skeptical review" — and then it cancels a
replacement from a source below it.

Write each replacement that wins to `run.substitutions_requested` as `{step,
replacement, source}`. A resumed session reads that field and nothing else,
because the words that named the replacement are not in its context, and a
file can change after the run starts. `references/substitution.md` owns what
you then do with it.

## Every dispatch is named

**This rule covers what you, the project lead, dispatch.** An agent's own
lookup subagents — a researcher's `Explore` hops, an IC's `Explore` check —
stay unnamed: a teammate cannot spawn a teammate, so a name gives one of
them nothing, and its result returns to its parent as an ordinary tool
result regardless of the flag.

Every agent you dispatch, on every path, gets a `name`, unique among the
agents of the current session. A resumed run is a new session — the
previous session's agents ended with it, so a counter that restarts from 1
here collides with nothing. The critics' and ICs' round numbers keep
advancing across a resume because they are read from the record, which
survives; a scout, a spec writer or a lookup keeps no such counter, and
needs none. Whether a name makes the agent a teammate follows from
`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` alone, never from the path or the
role: set, a named agent launches as a teammate, in its own pane under a
display mode (`--teammate-mode tmux` or `iterm2`); unset, it launches as a
plain subagent and the name changes nothing.

**A compaction resets your own count, not the record's.** A scout, a spec
writer, a lookup, a researcher or an advocate keeps its counter only in your
own context, and a compaction of your session loses it, so a name chosen
after one can repeat a name chosen before it. Read `record-format.md`'s
`run.compactions` before your first dispatch after a compaction — `k` is its
length — and restart that role's counter at 1, with the suffix `-c<k>`
appended to the name (`k = 0` takes no suffix). A session about to name its
next lookup `lookup-2` names it `lookup-1-c1` instead if a compaction lands
first. The critics' and ICs' round numbers need no such fix: they are
already read from the record, which a compaction does not touch.

**The name shape**, `<role>-<id>`:

| Role | Name |
|---|---|
| Scout | `scout-<n>` |
| Spec writer | `spec-writer-r<n>` |
| Spec critic | `spec-critic-r<n>` |
| Split critic | `split-critic-<deliverable id>-r<n>` |
| Advocate | `advocate-c<council n>-<position>` |
| Researcher | `researcher-<n>` |
| Lookup | `lookup-<n>` |
| IC | `ic-<package id>-r<n>` |

Every `<n>` counts from 1 in this session, and is what keeps two dispatches
of the same role from sharing a name: the question for a scout or a
researcher, the round for a critic, a review or the spec writer, and the
dispatch for an IC — a fresh IC per fix round is still one package, so its
round counts from that package's first dispatch, giving `r1`, `r2`, and on.
A lookup's `<n>` counts every lookup dispatch in this session, `Explore` or
otherwise. An advocate's id pairs its council number with its position, so a
second council in the same run — the investigation path can run more than
one — never collides with the first. The critics' and the ICs' round
numbers are the one exception: reading them from the record, not counting
in-session, is what lets them keep advancing across the resume described
above.

**Read the result from the idle notification's final message, when the name
made a teammate.** A named agent's answer arrives there, not as a tool
result. With the flag unset, the same agent is a plain subagent and its
result returns as an ordinary tool result instead — read it from there.
Where an agent also writes a record file — a critic, an IC, a review — that
file stays the durable copy either way; read the idle notification or the
tool result for the answer, and the file for the evidence.

**A teammate cannot spawn a teammate.** An in-process teammate's own
subagents run in the foreground, so a researcher's own lookups run one at a
time.

**Never request `run_in_background` for a dispatch.** It is unsupported for
a teammate.

**Permission prompts surface here.** Any dispatch's prompt reaches this
session, for you to approve. Pre-approve what the run needs, or a
no-prompt run stalls on the first one.

**Check the flag before your first dispatch.** `echo
$CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS` must print `1` on the full path,
always — `full-path.md` sends an IC its next package, a fix round and a
nudge by `SendMessage`, which only a teammate can receive. On every other
path the check is needed only when the launch is meant to run under a
display mode; with the flag unset there, every dispatch still runs — as a
plain subagent, with no pane and no messaging between agents.
`full-path.md`'s "Check the launch conditions" points here for this check;
its other conditions are its own.

Every reference and agent description below points at this section rather
than restate it.

## Scout

Four questions, answered from this repo before any spec exists. Does an
analogous implementation exist? Do tests cover this surface?
What runs the suite, and what other gates does CI run: types, lint, build?
Which instruction files apply? The scout records each gate command and the
setup command word for word.

Dispatch `crew:scout` subagents at `haiku`, named `scout-<n>` for the
question number, and read each answer as "Every dispatch is named" above
says. The reading stays out of your own context. `band-rubric.md` says why
Haiku runs only this agent.

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
a `general-purpose` subagent at `sonnet`, named `spec-writer-r<n>` for the
draft's round, write the prose, and revise what it returns. The spec is
yours.

## Have the spec reviewed

**Reserve the round before you dispatch.** A critic whose write is denied
returns its report only in its final message, so no file with its number
ever lands — reading `reviews/` for the highest round after the fact can
then repeat a number a live dispatch already holds. Write
`reviews/spec-critic-r<n>-instructions.md` first, `<n>` one more than the
highest `<n>` across both filename shapes `record-format.md`'s `reviews/`
listing names for this role: the report and the reservation file itself.
That write is what reserves the round.

Then dispatch `crew:spec-critic`, named `spec-critic-r<n>` for the same
round, with `spec.md`, `charter.md`, the repo path, `review-output.md`
whole, the standing instructions as "Standing instructions" above says, and
the absolute path it writes its findings to:
`reviews/spec-critic-r<n>.md`. Every review dispatch in this run reserves
and names its round the same way, and returns the short result
`review-output.md` defines, read as "Every dispatch is named" above says;
open the file only when the count says there is something to adjudicate.

`Verdict: re-spec needed` means adjudicate, revise `spec.md`, and dispatch
`spec-writer-r<n>` again for the next round. The critic's next round reads
the whole spec. **Two rounds is the cap.** At the cap, apply every open
finding you accept to `spec.md` yourself, log the rest in `decisions.md` as
declined with reasons, and go on to the split. Do not ask.

**A `[Concern]` or `[Nit]` on the spec is a wording fix.** Apply it to
`spec.md` yourself, and dispatch no spec writer and no critic round for it.
**A spec-critic or split-critic round with no `[Critical]` finding is
finished when the project lead applies the findings it accepts inline.** No
writer and no critic round follows it. A `ready to split` round with
findings ends this way.

**This review runs on every spec.** `band-rubric.md` says which later steps a
band skips, and the spec critic is not one of them: the split has not run yet,
so no package has a band. A light-path run writes no spec, which is a
different thing and the same file states it.

**A replacement named for this step runs in its place.**
`references/substitution.md` owns that case. Read it before you dispatch.

**Every review in this run is adjudicated the same way**, at every stage:
restate each finding in your own words, verify it against the repo, and push
back in writing where it is wrong here. **A finding is a claim, not a verdict.**

## A step the principal replaced

`references/substitution.md` owns this case: the spec critic or the skeptical
review that the principal named another reviewer for. Read it before you
dispatch that step.

## Sweep for preference questions

Before you split, take every question in `charter.md` and `spec.md` that
the repo cannot answer. Decide each one the reversible rule allows, and
escalate the rest as one batch. `autonomy-contract.md`'s "The preference
sweep" owns both rules.

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

# crew

A Claude Code plugin that takes your goals to PRs ready for review. It does
not stop for approval until the PR is open. Then it watches the PR and CI,
and fixes what lands. When another person comments on the PR, it waits for
your go-ahead before it pushes or replies.

You hand a goal to a project lead. It reads its repo, writes the spec, splits
the work, picks a model for each piece, dispatches implementers, checks each
piece itself, integrates the work and hands it over as a PR. Only then
is the whole diff reviewed. A separate session reads it against your goal and
assumes it is wrong. What that session finds comes back as patch rounds on the
same PR. When that review is done, the PR leaves draft. Merge it when you
are ready, or tell the project lead to merge it. The project lead stays until
its work ships, so you can ask it about the change before the merge, or ask
for a change to the PR after. The work ships when its deploy succeeds, or soon
after the merge when the repo has no deploy.
It watches the PR and CI the whole time. It assesses each comment and failed
check that lands, and fixes what it accepts on the branch at once. It tells
you what it fixed or declined and why. When another person commented, it
waits for your go-ahead before it pushes or replies on the PR. A comment from
a bot, a failed check and a comment from your own GitHub account take no
go-ahead.

Two entry points:

| Command | Use it for |
|---|---|
| `/crew:project-lead` | One goal, run in the session you are in. It sizes the work itself and brings you every question it cannot answer. |
| `/crew:review` | One colleague's PR. It reviews the PR as a skeptical staff reviewer, posts the review on GitHub, and stays with the PR to the merge. |

Crew is experimental. It has taken real goals to draft PRs, and the plugin
changes often. `/crew:review` has not run yet.

## Install

```
/plugin marketplace add jerridan/crew
/plugin install crew@crew
```

## Run one goal in your session

Start Claude Code in a clone of the target repo, or in a worktree of one:

```
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude --model fable --effort high --permission-mode auto
```

Add `--teammate-mode tmux` from inside tmux to give every agent the project
lead dispatches its own pane:

```
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude --model fable --effort high --permission-mode auto --teammate-mode tmux
```

Then hand over the goal:

```
/crew:project-lead add a --json flag to the export command
```

The argument is one of four:

| Argument | What happens |
|---|---|
| A goal | The project lead writes a charter with one acceptance criterion it can test, then runs. |
| A symptom, such as `the export drops the last row` | The investigation path: reproduce it, find the cause, then fix it or report the diagnosis. |
| A path to a charter file | That file is the charter, unchanged. |
| `--resume <goal-slug>` | Reopens a killed run from its record and continues. The slug is the record directory's name. |

For two goals in one clone, tell the second run that the clone is taken:

```
/crew:project-lead another crew run holds this checkout. add a --json flag to the export command
```

It then cuts a worktree of its own instead of switching the branch under the
first run.

You can name your own reviewer for either of the two review steps — the spec
review, and the review of the finished diff. Say it in plain words with the
goal:

```
/crew:project-lead add a --json flag to the export command. use Codex for the spec review
```

The run calls what you named in that step's place, writes its report into the
record with the others, and records what ran and what it used.

To name a reviewer for every run, write the same words in a file:

| File | Applies to |
|---|---|
| `~/.claude/crew/config.md` | every run on this machine |
| `.claude/crew.md` in the repo | every run in that repo |

```
use Codex via tmux for the skeptical review
```

Words with the goal win over the repo file, and the repo file wins over the
machine file. To turn off a replacement from a file for one run, say "use the
default skeptical review" with the goal.

The run sizes the work itself and picks a path:

| Path | When | What runs |
|---|---|---|
| Light | A small item whose acceptance criterion is the whole spec | One implementer, checked by the project lead. No spec. |
| Simple | One package | Spec, spec critic, one implementer on one branch, checked by the project lead. |
| Full | Several packages | Spec, both critics, one implementer per package in its own worktree, a merge per package. |
| Investigation | A symptom | Reproduce, gather evidence, diagnose. Then a spec and a fix, or a report with no change. |

The result is a branch named `crew/<goal-slug>/<deliverable-id>` and a
draft PR from it. The PR leaves draft when crew's own review of it is done,
so your automated reviewers start after that. To keep it a draft, say so in
the goal. The run restores your checkout to the branch it started on, and the
session stays. In that session you can ask about the change, or ask for a
change to the same PR. You do not paste review findings: the project lead
finds each review, comment and failed CI check on the PR itself. It verifies
each one, and fixes what it accepts on the branch. Then it tells you what it
fixed or declined, and why. When another person commented, it waits for your
go-ahead, then pushes and replies to each one on the PR. A comment from a
bot, a failed check and a comment from your own GitHub account are pushed and
answered with no go-ahead. You can still send findings from anywhere else,
and they wait for your go-ahead too.
After a merge, crew watches GitHub for the deploy of the merge commit. When
that deploy succeeds, the run closes with no word from you. A repo with no
deploy closes 10 minutes after the merge, or at the merge with `Deploy: none`. If the deploy fails or does not finish in time,
crew tells you, and the run stays open until you say the work shipped. With
`Deploy: manual`, the run also waits for your word. Closing the
session instead leaves the run recorded as interrupted, which is fine for a
run you merged yourself.

To let the run push and reply on the PR with no go-ahead, say so in the goal,
or put this line in your charter file:

```
Gate: off
```

Then nothing waits for your go-ahead, from the PR or from you.

A question comes to you in the same session. The triggers are fixed: no
testable acceptance criterion, a preference the repo cannot settle, a council
that cannot decide, an action outside the deliverable branch, a fix loop that
ran out, and the go-ahead before a push or a reply on the PR. Answer in the
session and the run continues.

### Review a colleague's PR

Start Claude Code in a clone of the PR's repo, with `gh` signed in as you.
Then give the PR's URL:

```
/crew:review https://github.com/<owner>/<repo>/pull/<n>
```

Or give its number, with plain words to ask for more:

```
/crew:review 123 fix the blockers yourself
```

The PR must be open. "Fix the blockers yourself" lets crew push fixes to the
PR's branch, and it does not work on a PR from a fork.

With "fix the blockers yourself", two more phrases set how crew works. The
first sets how many fix rounds crew runs before it stops and lists what is
left. The default is 3. The second skips the review of crew's own push when
that push changes only prose files, or fewer than 20 lines:

```
/crew:review 123 fix the blockers yourself, 2 fix rounds
/crew:review 123 fix the blockers yourself, skip the re-review when prose-only or under 20 lines
```

In a review run, crew waits for your go-ahead before it posts a review with a
finding. It shows you the draft first. You can change any finding or the
text, or mark a finding "no reply". A review with no findings posts with no
wait. A later review that raises nothing new posts with no wait. A later
review with a new finding waits for you again.

Put the test and setup commands in `.claude/crew.md`, under `Gates` and
`Setup`. Crew then runs them with no scout.

Replies and pushes in a review run follow the same rule as in a goal run.
Crew waits when another person commented. A comment from a bot, a failed
check and a comment from your own GitHub account take no go-ahead. To turn
every wait off, say `post without asking` with the command.

Crew does not run a fork's tests or setup unless you say
`run the suite on this fork`.

Crew gives each finding one label:

| Label | What it means | What crew posts |
|---|---|---|
| `blocking` | Merging as it is harms a user, a customer or the business. | A comment, and a review that requests changes. With "fix the blockers yourself", crew fixes it first. |
| `suggestion` | Real and worth a comment. The author decides. | A comment. |
| `nit` | Correct but minor. | A comment, only when a one-line suggestion fixes it. |
| `unsure` | The repo cannot settle it. | A question. The review stays a comment. |

A finding that is true but not worth the author's time, or not real, does not
post. A defect that the PR did not add stays out of the review. Crew lists it
for you as a possible new goal. On your own PR, the review posts as a
comment.

A new review that approves or comments clears an earlier "changes
requested" that crew posted.

Crew reviews each new push on the PR the same way. It leaves the merge to the
PR's author. With "fix the blockers yourself", it approves only after its
fixes are pushed, and it merges when you tell it to. The run ends when the PR
merges or closes. When the PR leaves the merge queue without a merge, crew
tells you, with the reason.
To use another reviewer, say so in plain words, as for a goal:
`use Codex for the review`.

## What a run needs

| Requirement | How | Which runs |
|---|---|---|
| Permissions that never stop for a human | `--permission-mode auto`, or your own allow rules | every run |
| Agent teams | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, and an interactive session | required for the full path; required for a pane per dispatched agent on any path; optional otherwise |
| A remote to push to | The clone has an `origin` | every run |
| The GitHub CLI, signed in | `gh auth status` passes | every run that opens a PR |
| A clone of the PR's repo, with `gh` signed in as you | Start `/crew:review` inside the clone | every `/crew:review` run |
| tmux, for a pane per dispatched agent | `--teammate-mode tmux` from inside tmux; without a split-pane display mode (tmux or iTerm2) every dispatched agent runs in the sidebar | optional, every path |
| Standing instructions | `.claude/crew.md` in the repo, or `~/.claude/crew/config.md` for every repo on this machine | optional, every run |

Crew never widens your permissions itself. Without the teams variable, the
light, simple and investigation paths still work: every named agent launches
as an ordinary subagent, so you keep the per-package model and the isolated
context, and you lose the messaging between agents and the shared task list.
The full path requires the variable.

Crew reads both standing-instruction files whole at launch, and gives their
text to every agent it dispatches. Each file holds optional sections, each
under a `##` heading with one of these names:

| Section | What to write |
|---|---|
| `Reviewers` | the reviewer to use in place of a review step, in plain words |
| `Known red tests` | the tests that already fail on the main branch, and why |
| `Gates` | the exact commands CI runs: tests, types, lint and build |
| `Setup` | the one command that installs what the tests need in a fresh clone |
| `Auto-review` | the GitHub login of the repo's review bot, such as `claude[bot]`. A review run checks that bot's blocking findings too |
| `Hook workarounds` | what to do when a git hook stops a push or a merge |
| `Ticket defaults` | where a new ticket goes, such as its team |
| `PR readiness` | `ready` or `draft` |
| `Done` | `merged` or `rolled out`. In a review run, `rolled out` makes crew wait for the deploy of the merge, or for your word under `Deploy: manual`, not for the merge alone |
| `Branch names` | your rule for a branch name |
| `Go-ahead` | `on` or `off`: whether crew waits for you before it pushes and replies on the PR |
| `Deploy` | how crew sees that a merge is live: `environment: <name>`, `workflow: <name>`, `none` (the repo has no deploy, so the run closes at the merge) or `manual` (the repo deploys where GitHub cannot see, so crew waits for your word), and an optional `timeout: <minutes>` (default 180). With no section, crew looks for a successful production deployment, or a deploy or release workflow run, on GitHub. It closes 10 minutes after the merge when it finds neither |

```
## Known red tests
test_search_emits_analytics fails on main while the local search flag is on.

## Gates
yarn test
yarn check-types-strict
```

## How it works

```
   one goal
      │
      ▼
   ┌───────────────────────────────────────────────┐
   │ PROJECT LEAD   scout, size, spec, split       │
   └───────────────────────────────────────────────┘
      │
      ▼
   ┌───────────────────────────────────────────────┐
   │ CRITICS        reject a bad spec or split     │
   └───────────────────────────────────────────────┘
      │
      │   each package gets a band:  light / standard / deep
      │
      ├────────────────┬────────────────┐
      ▼                ▼                ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ IC         │  │ IC         │  │ IC         │
   │ one        │  │ one        │  │ one        │
   │ worktree   │  │ worktree   │  │ worktree   │
   └────────────┘  └────────────┘  └────────────┘
      │                │                │
      └────────────────┴────────────────┘
      │
      ▼
   ┌───────────────────────────────────────────────┐
   │ PROJECT LEAD   run the tests, read the diff   │
   └───────────────────────────────────────────────┘
      │                  │
      │ passed           └──▶  a failure goes back to that IC,
      ▼                        up to five fix rounds
   ┌───────────────────────────────────────────────┐
   │ PROJECT LEAD   integrate, hand over as a      │
   │                draft PR                       │
   └───────────────────────────────────────────────┘
      │
      ▼
   ┌───────────────────────────────────────────────┐
   │ SKEPTICAL      reads the whole diff against   │
   │ REVIEW         your goal, in its own checkout │
   └───────────────────────────────────────────────┘
      │                  │
      │ accepted         └──▶  patch rounds on the same PR,
      ▼                        up to three reviews, unless you ask
   you merge it, or tell the run to, and say when it shipped
```

A package is dispatchable only with four things: its own acceptance
criterion, a file set disjoint from every sibling, a written interface
contract with those siblings, and a model band. An IC works in its own
worktree and cannot see its siblings' work, so that contract is the only
channel between packages.

The project lead checks every package itself. It runs the acceptance test and
the suite, and a failure sends the package back, up to five times. Review
comes after the work is handed over: a separate session reads the whole diff
against your goal, assumes it is wrong, and runs the tests in a checkout of
its own. What it finds goes on the same PR as a patch round. So does what
your reviewers and CI post on the PR, and anything you send yourself. Each
finding gets a reply that says what changed or why the run disagreed. The
project lead patches the branch at once. It waits for your go-ahead before it
pushes or replies when another person commented, or when you sent the finding
yourself.

Crew's own review runs up to three times. A review that approves with only
suggestions is the last one: after the suggestions land, no further review
runs. To get one more review past that limit, say:

```
run one more review
```

A question with no precedent goes to a council, where each advocate argues an
assigned position, so the project lead weighs arguments instead of counting
votes. A question about what you want is never debated. It comes to you.

The PR is the end of the work. Crew merges only when you tell it to. The
project lead stays until you say the work shipped.

A review run takes these steps:

| Step | What happens |
|---|---|
| Take the PR | Reads the PR, refuses one that is not open, and opens the record. |
| Read the test commands from `.claude/crew.md`, or scout when it has none | Finds the test and setup commands. |
| Review | A separate session reads the diff against the PR's description and the repo. |
| Adjudicate | Crew checks each finding and gives it a label, and drops findings that do not post and defects that were already there. |
| Report and wait | Crew sends you the draft and waits for your go-ahead. |
| Post | Crew posts the review on the PR, with one inline comment per finding. |
| Watch | Crew watches the PR for a new push and for the merge. |
| Later rounds | Each new push is reviewed again. A finding whose code is gone is marked resolved. A review that raises nothing new posts with no wait. |
| The assist path | With "fix the blockers yourself", crew fixes the `blocking` findings and pushes them to the PR's branch, after your go-ahead. It approves only after the fix. |
| The end | The run closes when the PR merges. A PR that is closed without a merge also ends the run. A PR that leaves the merge queue is reported, with the reason. |

## Models

A package is `light`, `standard` or `deep`. Both `light` and `standard` run on
`sonnet`; `deep` runs on `opus`. `standard` is the default. An IC that reports
blocked is re-dispatched one band up. The band picks the model and nothing
else: every package takes the same steps.

| Agent | Model | Reasoning effort |
|---|---|---|
| Project lead | your session's: use `fable` | your session's: use `high` |
| IC, Instruction IC | the package's band: sonnet or opus | your session's |
| Scout | haiku | your session's |
| Council advocate | sonnet, or opus for a deep decision | high |
| Researcher | sonnet, or opus for a deep question | high |
| Spec critic | opus | high |
| Decomposition critic | opus | high |
| Skeptical review | opus | high |

The project lead, the ICs and the scouts take your session's effort, so set
it before the run starts.

## The record

Every run writes one directory outside your repo. Read it to audit a run, and
to see every judgment call with its citation.

```
~/.claude/crew/<goal-slug>/
├── charter.md      the goal and its acceptance criterion
├── spec.md         the spec
├── split.md        packages, interfaces and bands
├── state.json      package states, band history, spend, escalations
├── decisions.md    every judgment call, with its citation
├── reports/        one report per package
├── plans/          one plan per package
├── reviews/        every critic and reviewer output, and the reply to each
└── diffs/          one diff per deliverable
```

`reviews/baseline.md` lists the tests and checks that already fail before
the change. Reviewers do not raise them.

A review run's directory is `pr-<owner>-<repo>-<n>-<hex>/`. Its drafts are
`reviews/github-r<n>.md`, one per round.

Set `CREW_RECORD_ROOT` to move the root.

To see what runs cost, from a checkout of this repo:

```
python3 skills/project-lead/scripts/crew-stats.py
```

It prints cost per band, fix rounds, promotions, councils, reviews, the
review catch rate and the finding labels the reviewers proposed for each
review kind, over every record.

## Roles

| Role | What it does |
|---|---|
| Project lead | Runs one goal in your session: scouts, sizes the work, writes the spec, splits it, dispatches workers, integrates, opens the PR. Then stays until the work ships: it watches the PR and CI, fixes what lands, and waits for your go-ahead before it answers another person's comment or a finding you sent. It answers your questions and takes your changes too. |
| IC | Implements one package of code, in its own worktree, test-first. |
| Instruction IC | Implements one package of prose, such as a `CLAUDE.md`, a rule file, a `SKILL.md` or an agent definition, where a checklist decides done. |
| Spec critic | Reviews the spec before any work starts. |
| Decomposition critic | Reviews the work split before any IC starts. |
| Skeptical review | Reads the whole diff against your goal once the work is handed over, in a checkout of its own. |
| Researcher | Answers one open question across several hops, with citations. |
| Scout | Answers one lookup for the project lead, then exits. |
| Advocate | Argues one assigned position in a council. |

## Help and contributing

Open an issue on this repo for a bug or a question. To learn how crew works
and why, read [`docs/design.md`](docs/design.md). It is the spec, and it
records what every run so far found.

## Credit

Crew's process is adapted from the `superpowers` plugin: spec, plan, critique,
test-driven implementation, review, integrate. Several of its checklists are
copied word for word so they stay easy to re-sync. Crew never invokes a
superpowers skill: each one stops for a human, and removing that stop is the
point of crew.

## License

MIT. See [LICENSE](LICENSE).

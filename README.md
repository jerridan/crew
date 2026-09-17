# crew

A Claude Code plugin that takes your goals to reviewable draft PRs, and does
not stop for approval on the way.

You hand a goal to a project lead. It reads its repo, writes the spec, splits
the work, picks a model for each piece, dispatches implementers, checks each
piece itself, integrates the work and hands it over as a draft PR. Only then
is the whole diff reviewed. A separate session reads it against your goal and
assumes it is wrong. What that session finds comes back as patch rounds on the
same PR. You merge it when you are ready. The project lead stays until you say
its work shipped, so you can ask it about the change before you merge, ask for
a change to the PR after, or send it a review's findings and get a reply on
each one.

One entry point:

| Command | Use it for |
|---|---|
| `/crew:project-lead` | One goal, run in the session you are in. It sizes the work itself and brings you every question it cannot answer. |

Crew is experimental. It has taken real goals to draft PRs, and the plugin
changes often.

## Install

```
/plugin marketplace add jerridan/crew
/plugin install crew@crew
```

## Run one goal in your session

Start Claude Code in an ordinary clone of the target repo, not a worktree:

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

The run sizes the work itself and picks a path:

| Path | When | What runs |
|---|---|---|
| Light | A small item whose acceptance criterion is the whole spec | One implementer, checked by the project lead. No spec. |
| Simple | One package | Spec, spec critic, one implementer on one branch, checked by the project lead. |
| Full | Several packages | Spec, both critics, one implementer per package in its own worktree, a merge per package. |
| Investigation | A symptom | Reproduce, gather evidence, diagnose. Then a spec and a fix, or a report with no change. |

The result is a branch named `crew/<goal-slug>/<deliverable-id>` and a draft
PR from it. The run restores your checkout to the branch it started on, and
the session stays. In that session you can ask about the change, ask for a
change to the same PR, or paste what a reviewer found — CI, a bot, or your
own reading of the diff. The run patches the findings on the same branch and
answers each one. When the work is merged and deployed, say so, and the run
closes. Closing the session instead leaves the run recorded as
interrupted, which is fine for a run you merged yourself.

A question comes to you in the same session. The triggers are fixed: no
testable acceptance criterion, a preference the repo cannot settle, a council
that cannot decide, an action outside the deliverable branch, a fix loop that
ran out. Answer in the session and the run continues.

## What a run needs

| Requirement | How | Which runs |
|---|---|---|
| Permissions that never stop for a human | `--permission-mode auto`, or your own allow rules | every run |
| Agent teams | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, and an interactive session | required for the full path; required for a pane per dispatched agent on any path; optional otherwise |
| An ordinary clone | Start outside any worktree | the full path |
| A remote to push to | The clone has an `origin` | every run |
| tmux, for a pane per dispatched agent | `--teammate-mode tmux` from inside tmux; without it every dispatched agent runs in the sidebar | optional, every path |

Crew never widens your permissions itself. Without the teams variable, the
light, simple and investigation paths still work: every named agent launches
as an ordinary subagent, so you keep the per-package model and the isolated
context, and you lose the messaging between agents and the shared task list.
The full path requires the variable.

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
      ▼                        up to three reviews in all
   you merge it, and say when it shipped
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
its own. What it finds, and anything you send yourself, goes on the same PR
as a patch round, with a reply on each finding saying what changed or why the
run disagreed. A run takes three reviews at most. A question with no
precedent goes to a council, where each advocate argues an assigned position,
so the project lead weighs arguments instead of counting votes. A question
about what you want is never debated. It comes to you.

The draft PR is the end of the work. Crew never merges. The project lead
stays until you say the work shipped.

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
| Skeptical review | opus | not set |

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
├── reports/        one report per package, and the reply to each reviewer
├── plans/          one plan per package
├── reviews/        every critic and reviewer output
└── diffs/          one diff per deliverable
```

Set `CREW_RECORD_ROOT` to move the root.

To see what runs cost, from a checkout of this repo:

```
python3 skills/project-lead/scripts/crew-stats.py
```

It prints cost per band, fix rounds, promotions, councils, reviews and the
review catch rate, over every record.

## Roles

| Role | What it does |
|---|---|
| Project lead | Runs one goal in your session: scouts, sizes the work, writes the spec, splits it, dispatches workers, integrates, opens the draft PR. Then stays for questions, changes and review findings until the work ships. |
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

# crew

A Claude Code plugin that takes your goals to reviewable draft PRs, and does
not stop for approval on the way.

You hand your goals to a lead. It starts one project lead per goal. Each
project lead reads its repo, writes the spec, splits the work, picks a model
for each piece, dispatches implementers, has each piece reviewed by an agent
that did not write it, and opens the draft PR. You merge it. The lead brings
you every question the runs cannot answer, in one batch. Each project lead
stays until you say its work shipped, so you can ask it about the change
before you merge, and hand it a follow-up after.

Two entry points:

| Command | Use it for |
|---|---|
| `/crew:lead` | The main entry point. Hand it every goal. It runs one project-lead session per goal and brings you every question in one batch. |
| `/crew:project-lead` | One goal, run directly in the session you are in. |

Crew is experimental. Both entry points have taken real goals to draft PRs,
and the plugin changes often.

## Install

```
/plugin marketplace add jerridan/crew
/plugin install crew@crew
```

## Run your goals through a lead

A lead holds a portfolio and starts one project-lead session per goal. It
reads no code and sizes nothing: the project lead does that. One goal or ten
take the same steps.

Start Claude Code inside tmux, in a directory that is not a repo checkout:

```
claude --model fable --effort high
```

Then start the lead:

```
/crew:lead
```

Type the goals as your next message. Give each one the absolute path of its
repo:

```
Add a --json flag to the export command in /Users/me/src/kit. Then fix the flaky retry test in /Users/me/src/client.
```

The lead opens one tmux window per goal. In iTerm2, set `CREW_LAUNCH=iterm2`
for a native tab per goal instead: install the `iterm2` package for your
`python3` and turn on the Python API in iTerm2's settings.

What to expect:

- Each target repo must be one you have opened in Claude Code before. The
  lead checks, and asks you to open a new one once.
- Questions arrive in the lead's pane, in one batch, with a push
  notification. Answer in that pane and nowhere else.
- Add a goal at any time by typing it in the pane.
- A goal in stages takes one item per stage. Name the stages and the command
  that checks each one. The lead holds the next stage until you say go.
- A project lead stays in its window after its PR opens. Ask the lead to pass
  it a question or a follow-up, or type in its window yourself. When the PR
  is merged and deployed, tell the lead the item shipped, and it closes the
  session.
- If the lead session dies, start Claude Code again in the same directory and
  run `/crew:lead`. It finds the open portfolio and continues, and it resumes
  any project lead that died with it.

## Run one goal in your session

This is what the lead does for each goal. Do it yourself when you want to
watch one run, or when you have no tmux.

Start Claude Code in an ordinary clone of the target repo, not a worktree:

```
CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1 claude --model fable --effort high --permission-mode auto
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

The run sizes the work itself and picks a path:

| Path | When | What runs |
|---|---|---|
| Light | A small item whose acceptance criterion is the whole spec | One implementer, one review. No spec. |
| Simple | One package | Spec, spec critic, one implementer on one branch, one review. |
| Full | Several packages | Spec, both critics, one implementer per package in its own worktree, a merge per package. |
| Investigation | A symptom | Reproduce, gather evidence, diagnose. Then a spec and a fix, or a report with no change. |

The result is a branch named `crew/<goal-slug>/<deliverable-id>` and a draft
PR from it. The run restores your checkout to the branch it started on, and
the session stays. Ask about the change, or hand it a follow-up on the same
PR, in that session. When the work is merged and deployed, say so, and the
run closes. Closing the session instead leaves the run recorded as
interrupted, which is fine for a run you merged yourself.

A question comes to you in the same session. The triggers are fixed: no
testable acceptance criterion, a preference the repo cannot settle, a council
that cannot decide, an action outside the deliverable branch, a fix loop that
ran out. Answer in the session and the run continues.

## What a run needs

| Requirement | How | Which runs |
|---|---|---|
| Permissions that never stop for a human | `--permission-mode auto`, or your own allow rules | every run |
| Agent teams | `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, and an interactive session | the full path |
| An ordinary clone | Start outside any worktree | the full path |
| A remote to push to | The clone has an `origin` | every run |
| A trusted directory | Open each target repo in Claude Code once | every run a lead launches |
| tmux, or iTerm2 with `CREW_LAUNCH=iterm2` | See above | `/crew:lead` |

Crew never widens your permissions itself. Without the teams variable a run
still works, but a named agent becomes an ordinary subagent: you keep the
per-package model and the isolated context, and you lose the messaging between
agents and the shared task list.

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
      │   each package gets a band:  haiku / sonnet / opus
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
   │ REVIEWER       did not write what it reviews  │
   └───────────────────────────────────────────────┘
      │                  │
      │ accepted         └──▶  findings go back to that IC,
      ▼                        up to five fix rounds
   ┌───────────────────────────────────────────────┐
   │ PROJECT LEAD   merge, re-run the suite        │
   └───────────────────────────────────────────────┘
      │
      ▼
   draft PR   ──▶   you merge it
```

`/crew:lead` sits one level above this diagram. It writes a charter per goal
and starts one project lead per charter.

A package is dispatchable only with four things: its own acceptance
criterion, a file set disjoint from every sibling, a written interface
contract with those siblings, and a model band. An IC works in its own
worktree and cannot see its siblings' work, so that contract is the only
channel between packages.

Review is independent: the reviewer gets the brief and the diff, and never saw
the work happen. A question with no precedent goes to a council, where each
advocate argues an assigned position, so the project lead weighs arguments
instead of counting votes. A question about what you want is never debated. It
comes to you.

The draft PR is the end of the work. Crew never merges. The project lead
stays until you say the work shipped.

## Models

A package is `light` (haiku), `standard` (sonnet) or `deep` (opus).
`standard` is the default. An IC that reports blocked is re-dispatched one
band up. A `light` package skips the plan gate and, on three conditions, the
deliverable review.

| Agent | Model | Reasoning effort |
|---|---|---|
| Lead | your session's: use `fable` | your session's: use `high` |
| Project lead | your session's: use `fable` | your session's: use `high` |
| IC, Instruction IC | the package's band: haiku, sonnet or opus | your session's |
| Scout | haiku or sonnet | your session's |
| Council advocate | sonnet, or opus for a deep decision | high |
| Package reviewer | sonnet | high |
| Researcher | sonnet, or opus for a deep question | high |
| Spec critic | opus | high |
| Decomposition critic | opus | high |
| Deliverable reviewer | opus | high |

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
├── reports/        one report per package, from its IC
├── plans/          one plan per package
├── reviews/        every critic and reviewer output
└── diffs/          one diff per review
```

A lead writes `~/.claude/crew/lead-<date>-<hex>/` beside them, with the
portfolio, its charters, and each goal's record under `runs/`. Set
`CREW_RECORD_ROOT` to move the root.

To see what runs cost, from a checkout of this repo:

```
python3 skills/project-lead/scripts/crew-stats.py
```

It prints cost per band, fix rounds, promotions, councils, reviews and the
review catch rate, over every record.

## Roles

| Role | What it does |
|---|---|
| Lead | Holds a portfolio. Writes a charter per goal, starts one project-lead session per goal, answers what its record settles, and brings you the rest in one batch. Passes your questions, follow-ups and the word that an item shipped down to its project lead. |
| Project lead | Runs one goal in your session: scouts, sizes the work, writes the spec, splits it, dispatches workers, integrates, opens the draft PR. Then stays for questions and follow-ups until the work ships. |
| IC | Implements one package of code, in its own worktree, test-first. |
| Instruction IC | Implements one package of prose, such as a `CLAUDE.md`, a rule file, a `SKILL.md` or an agent definition, where a checklist decides done. |
| Spec critic | Reviews the spec before any work starts. |
| Decomposition critic | Reviews the work split before any IC starts. |
| Package reviewer | Reviews one finished package against its brief. |
| Deliverable reviewer | Reviews the whole deliverable before the draft PR opens. |
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

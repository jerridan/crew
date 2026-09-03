# crew

**A team of agents that takes one goal to a reviewable draft PR.** You hand the
goal to a project lead. It investigates, splits the work across implementers,
has each piece reviewed by an agent that did not write it, and opens the PR. It
asks you only when it cannot proceed.

> **Status: it runs, councils included.**
> One goal to a draft PR, either as a single package or split across parallel
> worktrees. Both paths have been driven end to end against a real repo. See
> [What exists today](#what-exists-today).

## Why

Most agent tooling scales one agent up: a longer context, a bigger model, a
better prompt. `crew` scales sideways, to a team with an org chart.

Four things follow that one agent cannot get alone:

- **Review is independent.** An agent that checks its own work grades its own
  homework. A reviewer handed the brief and the diff, which never saw the work
  happen, is a real gate.
- **Disagreement is designed in.** Two agents on one base model agree because
  they share priors, not because they are right. A council assigns opposing
  positions, so the project lead weighs arguments instead of counting votes.
- **Work happens at once.** Packages carry disjoint file sets, so several
  implementers run without colliding.
- **Effort is sized per piece.** Each package takes the cheapest model that can
  do it, chosen after investigation rather than before.

It also moves the stops. A session today interrupts you after brainstorming,
after the spec, after the plan, after the plan review — because you are its only
reviewer. Give it a team and that review happens inside the run, recorded as it
goes. You audit the judgment calls at the end instead of approving them one at a
time.

## How it works

```
   one goal
      │
      ▼
   ┌───────────────────────────────────────────────┐
   │ PROJECT LEAD   investigate, spec, split       │
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

A package is dispatchable only with four things: its own acceptance criterion, a
file set disjoint from every sibling beside it, a written interface contract
with those siblings, and a model band. An IC works in its own worktree and
cannot see its siblings' work, so that contract is the only channel between
packages.

The draft PR is the terminus. Autonomous merging is out of scope on purpose.

## What exists today

| Piece | State |
|---|---|
| `/crew:project-lead`, one package | built, and driven end to end |
| `/crew:project-lead`, several packages | built, and driven end to end |
| `crew:ic`, `crew:ic-instructions` | built, dispatched |
| `crew:spec-critic`, `crew:package-reviewer`, `crew:deliverable-reviewer` | built, dispatched |
| `crew:split-critic` | built, dispatched by the parallel path |
| `crew:researcher` | built, not dispatched yet |
| The record, band rubric, IC contract, writing standard | built |
| Question routing and `decisions.md` | built |
| `crew:council-advocate`, and councils | built, convened in a run |
| Hooks | `SessionEnd` and `PreCompact` built; the rest deferred |

Every run is on the record. The first was hand-driven and its plans, reports
and reviews are kept verbatim in [`docs/stage-2-run/`](docs/stage-2-run). Later
runs drove `/crew:project-lead` itself, against a real library with a test
suite: one package to a draft PR, then two packages in parallel worktrees, then
a run that survived a forced fix round and a mid-run crash.

Design [§15](docs/design.md) records what each run found, including the defects
they exposed in crew itself.

## The mechanics

**Bands.** A package is `light` (haiku), `standard` (sonnet), or `deep` (opus).
`standard` is the default and `deep` needs a written justification. An IC that
reports blocked is re-dispatched one band up with no human involvement. Every
prediction and promotion is logged, which turns the rubric into a measurement.

**What each agent runs on.** A reviewer or critic sets its own model and effort, and the project lead overrides neither. An advocate sets its own effort, and moves to opus only when the whole council does. An IC takes its model from its package's band, and no agent definition can set effort for an IC.

| Agent | Model | Reasoning effort |
|---|---|---|
| Project lead | your session's | your session's |
| IC, Instruction IC | the package's band: haiku, sonnet or opus | your session's |
| Scout | haiku or sonnet | your session's |
| Council advocate | sonnet, or opus for a deep decision | high |
| Package reviewer | sonnet | high |
| Researcher | sonnet, or opus for a deep question | high |
| Spec critic | opus | high |
| Decomposition critic | opus | high |
| Deliverable reviewer | opus | high |

**Set your session effort before you start a run.** Effort cannot be passed to an agent at dispatch, so an IC and a scout work at the effort of the session you launched.

**An audit trail instead of an approval gate.** One directory per goal, outside
your repo, holding the spec, the plan, every IC's report, every reviewer's
findings, and every judgment call with its citation. A decision recorded at high
confidence with no citation is a defect.

**A contract for when to ask you.** Questions route three ways: precedent, a
council, or you. The project lead escalates on a fixed set of triggers — a goal
with no falsifiable acceptance criterion, a council it cannot settle, a crossed
spend ceiling. Questions about what *you* want are never debated, because a
council always names a winner and would bury "we do not know what you want" as
"we established you want X".

**Reports are claims; git is evidence.** A teammate's output never returns to
the project lead, so every IC completion is checked against `git log` in its
worktree first. The suite re-runs after each merge, not once at the end, so a
failure belongs to one package with no bisect.

## Roles

| Role | What it does | Built |
|---|---|---|
| Project lead | Runs the whole goal in your session: investigates, writes the spec, splits the work, dispatches workers, integrates, opens the draft PR. | yes |
| IC | Implements one package of code, in its own worktree, test-first. | yes |
| Instruction IC | Implements one package whose deliverable is prose — a `CLAUDE.md`, a rule file, a `SKILL.md`, an agent definition — where a checklist decides done, not a test. | yes |
| Spec critic | Reviews the spec before any work starts. | yes |
| Decomposition critic | Reviews the work split before any IC starts. | yes |
| Package reviewer | Reviews one finished package against its brief. | yes |
| Deliverable reviewer | Reviews the whole deliverable before the draft PR opens. | yes |
| Researcher | Answers one open question across several hops, and returns a brief with citations. | yes |
| Scout | Answers one lookup for the project lead, then exits. | yes |
| Advocate | Argues one assigned position in a council. | yes |

## Install

```
/plugin marketplace add jerridan/crew
/plugin install crew@crew
```

### What a parallel run needs

Four things. Miss any one and the run stops.

| Requirement | How |
|---|---|
| Agent teams | Set `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, and run interactively |
| An unisolated checkout | Start from an ordinary clone |
| A display mode | Nothing to do — in-process by default. tmux or iTerm2 adds split panes |
| Permissions that never stop for a human | A permission mode that approves automatically, or your own allow rules |

The single-package path needs none of them. It runs one subagent on your
current branch.

Crew never widens your permissions itself. Without the teams variable it still
runs, but a named agent becomes an ordinary subagent: you keep the isolated
context, the per-package model and a returned result, and you lose the
independent session, the messaging between agents, and the shared task list.

## Credit

`crew`'s process — spec, plan, critique, test-driven implementation, review,
integrate — is adapted from the `superpowers` plugin. Several of its checklists
are copied word for word rather than paraphrased, so they stay easy to re-sync.

`crew` never invokes a superpowers skill directly. Every superpowers process
skill stops and waits for a human, and removing that stop is the point of
`crew`.

## Reading the docs

[`docs/design.md`](docs/design.md) is the living spec. Read it to know how
`crew` is meant to work, and §15 for what is still open.

[`docs/implementation-plan.md`](docs/implementation-plan.md) and
[`docs/stage-2-run/`](docs/stage-2-run) record how the first stages were built.
`crew` was built inside a larger plugin repo, so their paths suit that layout
and name a few plugins that live there. They are kept unedited because they are
evidence.

## License

MIT. See [LICENSE](LICENSE).

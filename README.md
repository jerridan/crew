# crew

**A team of agents that takes one goal to a reviewable draft PR.** You hand the
goal to a lead. It investigates, splits the work across implementers, has each
piece reviewed by an agent that did not write it, and opens the PR. It asks you
only when it genuinely cannot proceed.

> **Status: partly built. Installing it will not get you a run.**
> The worker agents exist and have been driven by hand. The lead that
> dispatches them does not — `/crew:lead` is a stub. See
> [What exists today](#what-exists-today).

## Why

Most agent tooling scales one agent up: a longer context, a bigger model, a
better prompt. `crew` scales sideways. It hands the goal to a team with an org
chart — a lead that plans and delegates, implementers working in parallel in
isolated worktrees, critics that review work they did not do, and advocates
that argue assigned sides of a judgment call.

The structure buys four things one agent cannot get alone:

- **A review is independent.** An agent that checks its own work grades its
  own homework. A reviewer handed the brief and the diff, which never saw the
  work happen, is a real gate.
- **Disagreement is designed in.** Two agents on the same base model agree
  because they share priors, not because they are right. A council assigns
  opposing positions, so the lead weighs arguments instead of counting votes.
- **Work happens at once.** Packages carry disjoint file sets, so several
  implementers run at the same time without colliding.
- **Effort is sized per piece.** Once the work is split, each piece can take
  the cheapest model that can do it, decided after investigation rather than
  before.

It also moves the stops. A session today interrupts you after brainstorming,
after the spec, after the plan, after the plan review — because you are the
only reviewer it has. Give it a team and that review happens inside the run,
recorded as it goes, so you audit the judgment calls at the end instead of
approving them one at a time.

## How it works

```
   one goal
      │
      ▼
   ┌───────────────────────────────────────────────┐
   │ LEAD      investigate, spec, split the work   │   not built
   └───────────────────────────────────────────────┘
      │
      ▼
   ┌───────────────────────────────────────────────┐
   │ CRITICS   reject a bad spec or a bad split    │   not built
   └───────────────────────────────────────────────┘
      │
      │   each package gets a band:  haiku / sonnet / opus
      │
      ├────────────────┬────────────────┐
      ▼                ▼                ▼
   ┌────────────┐  ┌────────────┐  ┌────────────┐
   │ IC         │  │ IC         │  │ IC         │   built
   │ one        │  │ one        │  │ one        │
   │ worktree   │  │ worktree   │  │ worktree   │
   └────────────┘  └────────────┘  └────────────┘
      │                │                │
      └────────────────┴────────────────┘
      │
      ▼
   ┌───────────────────────────────────────────────┐
   │ REVIEWER  did not write the code it reviews   │   built
   └───────────────────────────────────────────────┘
      │                  │
      │ accepted         └──▶  findings go back to that IC,
      ▼                        up to five fix rounds
   ┌───────────────────────────────────────────────┐
   │ LEAD      merge, re-run the suite, integrate  │   not built
   └───────────────────────────────────────────────┘
      │
      ▼
   draft PR   ──▶   you merge it
```

Only the middle of that pipeline exists today. The workers are built; nothing
dispatches them yet.

A package is dispatchable only when it has four things: its own acceptance
criterion, a file set disjoint from every sibling running beside it, a written
interface contract with those siblings, and a model band. An IC works in its
own git worktree and cannot see its siblings' work at all, so that contract is
the only channel between packages.

The draft PR is the terminus. Autonomous merging is out of scope on purpose.

## What exists today

| Piece | State |
|---|---|
| `crew:ic`, `crew:ic-instructions`, `crew:package-reviewer` | built, and driven end to end by hand |
| The record format, band rubric, IC contract, writing standard | built |
| `/crew:lead` — the loop that dispatches all of it | **stub** |
| Spec critic, decomposition critic, deliverable reviewer | not built |
| Council, question routing, `decisions.md` | not built |
| Hooks | not built |

One hand-driven run exercised the worker agents. A code package added real test
coverage to a sibling plugin; a prose package wrote a README. Both reached
`Verdict: accepted` from `crew:package-reviewer`. That run's plans, reports and
reviews are kept verbatim in [`docs/stage-2-run/`](docs/stage-2-run).

That run also found that a headless IC cannot get a `git commit` approved, and
that a lead running inside a worktree cannot reach a sibling worktree at all.
Both block the full path. §15 of the design doc records both, among eighteen
open questions in all.

## The mechanics

**Bands, and a rubric that measures itself.** A package is `light` (haiku),
`standard` (sonnet), or `deep` (opus). `standard` is the default and
`deep` needs a written justification. An IC that reports blocked is
re-dispatched one band up with no human involvement, and every prediction and
promotion is logged — which turns the rubric from a guess into a measurement.

**An audit trail instead of an approval gate.** One directory per goal, kept
outside your repo, holding the spec, the plan, every IC's report, every
reviewer's findings, and every judgment call with its citation. A decision
recorded at high confidence with no citation is a defect.

**A contract for when to ask you.** Questions route three ways: precedent, a
council, or you. The lead escalates on a fixed set of triggers, among them a
goal with no falsifiable acceptance criterion, a balanced council on an
architecture-moving question, and a crossed spend ceiling. Questions about
what *you* want are never debated: a council always names a winner, and would
bury "we do not know what you want" as "we established you want X".

**Reports are claims; git is evidence.** A teammate's output never returns to
the lead, so every IC completion is checked against `git log` in its worktree
before the lead believes it. The suite is re-run after each merge, not once at
the end, so a failure is attributable to one package with no bisect.

## Roles

| Role | What it does | Built |
|---|---|---|
| Lead | Runs the whole goal in your session: investigates, writes the spec, splits the work, dispatches workers, integrates, opens the draft PR. | stub |
| Scout | Answers one research question for the lead, then exits. | needs the lead |
| Advocate | Argues one position in a council, when the lead needs a second opinion on a judgment call. | needs the lead |
| Spec critic | Reviews the lead's spec before any work starts. | no |
| Decomposition critic | Reviews the work split before any IC starts, to catch a bad split early. | no |
| IC | Implements one package of code, in its own worktree, test-first. | yes |
| Instruction IC | Implements one package whose deliverable is prose — a `CLAUDE.md`, a rule file, a `SKILL.md`, an agent definition — where a checklist decides done, not a test. | yes |
| Package reviewer | Reviews one finished package against its brief before the lead accepts it. | yes |
| Deliverable reviewer | Reviews the whole deliverable, after every package merges, before the draft PR opens. | no |

## Install

```
/plugin marketplace add jerridan/crew
/plugin install crew@crew
```

This gets you the agents above. Nothing dispatches them yet, so today this is
worth doing only to read them or drive one by hand.

When the lead does land, it will dispatch ICs as named teammates, and teammate
spawning needs a working display mode — iTerm2 with its Python API enabled, a
session inside tmux, or `teammateMode: "in-process"` in your settings.

## Credit

`crew`'s process — spec, plan, critique, test-driven implementation, review,
integrate — is adapted from the `superpowers` plugin. Several of its
checklists are copied word for word rather than paraphrased, so they stay easy
to re-sync later.

`crew` never invokes a superpowers skill directly. Every superpowers process
skill stops and waits for a human. Removing that stop is the whole point of
`crew`.

## Reading the docs

[`docs/design.md`](docs/design.md) is the living spec. Read it first if you
want to know how `crew` is meant to work, and §15 for what is still open.

[`docs/implementation-plan.md`](docs/implementation-plan.md) and
[`docs/stage-2-run/`](docs/stage-2-run) are a record of how stages 0 through 2
were built. `crew` was built inside a larger plugin repo, so their paths are
relative to that layout, and they name a few plugins that live there. They are
kept unedited because they are evidence.

## License

MIT. See [LICENSE](LICENSE).

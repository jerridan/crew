# crew

An autonomous project lead. You give it one goal. It takes that goal to a
reviewable draft PR. No human checks in at each stage. It picks the
cheapest model for each piece of work.

`crew` is still under active build-out. Some pieces this README describes
are not wired up yet.

## Install

```
/plugin marketplace add jerridan/crew
/plugin install crew@crew
```

## Before you run this

`crew` dispatches ICs (implementers) as named teammates, and teammate
spawning needs a working display mode. Without one, dispatching an IC
fails.

Set up one of these before you run `crew`:

- iTerm2, with its Python API enabled, or
- a session running inside tmux, or
- `teammateMode: "in-process"` in your settings.

## Start a run

```
/crew:lead <goal>
```

This starts a run in your own session. The lead investigates the goal and
writes a spec. It splits the work and dispatches workers. It integrates
the result into a draft PR.

## Roles

| Role | What it does |
|---|---|
| Lead | Runs the whole goal in your session: investigates, writes the spec, splits the work, dispatches workers, integrates, and opens the draft PR. |
| Scout | Answers one research question for the lead, then exits. |
| Advocate | Argues one position in a council, when the lead needs a second opinion on a judgment call. |
| Spec critic | Reviews the lead's spec before any work starts. |
| Decomposition critic | Reviews the work split before any IC starts, to catch a bad split early. |
| IC | Implements one package of code, in its own worktree, test-first. |
| Instruction IC | Implements one package whose deliverable is prose — a `CLAUDE.md`, a rule file, a `SKILL.md`, or an agent definition — where a checklist decides "done," not a test. |
| Package reviewer | Reviews one finished package against its brief before the lead accepts it. |
| Deliverable reviewer | Reviews the whole deliverable, after every package merges, before the draft PR opens. |

## Credit

`crew`'s process — spec, plan, critique, test-driven implementation,
review, integrate — is adapted from the `superpowers` plugin. Several of
its checklists are copied word for word rather than paraphrased, so they
stay easy to re-sync later.

`crew` never invokes a superpowers skill directly. Every superpowers
process skill stops and waits for a human. Removing that stop is the whole
point of `crew`.

## About `docs/`

`docs/design.md` is the living spec. Read it first if you want to know how
`crew` is meant to work, and §15 for what is still open.

`docs/implementation-plan.md` and `docs/stage-2-run/` are a record of how
stages 0 through 2 were built. `crew` was built inside a larger plugin
repo, so their paths are relative to that layout, and they name a few
plugins that live there. They are kept unedited because they are evidence:
`stage-2-run/` holds the real plans, reports and reviews from the first
hand-driven run of these agents.

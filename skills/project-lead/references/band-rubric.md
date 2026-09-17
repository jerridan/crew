# Band rubric

This file decides what a package or a council gets for its band: the model
(design §8, §6.1), and, for a package, which review steps run (design §15.77).

**A band sets a model, never an effort, and a spawn-time `model` overrides an
agent's frontmatter.** `reasoning_effort` cannot travel that way — a teammate
inherits the project lead's effort (design §12). Do not add an effort column to
this rubric. This file is the only place a model is chosen.

## Bands

| Band | Model | The package looks like |
|---|---|---|
| light | sonnet | Follows an existing repo pattern verbatim. Tests already cover the surface. |
| **standard** | **sonnet** | **Default.** |
| deep | opus | A new interface others depend on. A concurrency, security, migration, or data-shape change. Or the project lead had to *interpret* the acceptance criterion rather than read it off the charter. |

`light` and `standard` share a model. Keep them as two bands: `crew-stats.py`
counts a promotion from a band change, not from a model change, and the
`light` band still names the package shape that the light path (see below)
and the simple path both read.

## Haiku runs only an agent whose tools need no approval

Auto mode is not supported for Haiku
(https://code.claude.com/docs/en/permission-modes). A Haiku agent's calls
that need approval — `Bash`, `Write`, or `Edit` — fall back to a prompt in
the project lead's session, and a run nobody watches stalls on the first one.
`Read`, `Glob` and `Grep` inside the repo are approved without a prompt in
the normal case.

Today `crew:scout` is the only agent built from `Read`, `Glob` and `Grep`
alone, so it is the only agent Haiku runs. Every IC, instruction IC, critic,
researcher, and advocate carries `Bash`, `Write`, or `Edit`, and takes
`sonnet` as its floor.

## Observable inputs

Answer these from the package's file set and acceptance criterion before you
assign a band:

- Does an analogous implementation already exist in this repo?
- Do tests already cover the surface this package touches?
- Does the package define a new interface that other packages depend on?
- Is this a concurrency, security, migration, or data-shape change?
- Did the project lead have to interpret the acceptance criterion, rather than
  read it directly off the charter?

Any "yes" past the first two is a signal toward `deep`.

## Rules

- Assign `light` when the first two observable inputs are both yes and every
  other one is no.
- Assign `standard` by default — every other case, including a `light`
  candidate that fails on any one of its two conditions.
- Assigning `deep` requires a written justification in `split.md`. An
  unjustified `deep` assignment is a defect.
- **Size never changes who does the work.** A one-line change is a package
  like any other. It takes a band from the rules above, and an IC does it
  (design §9.1).
- **Promotion.** Re-dispatch a package one band up, with no human
  involvement, when its IC reports `BLOCKED` with a `capability` cause,
  exhausts its fix rounds, or goes idle without meeting its acceptance
  test (design §8). A `deep` package cannot promote further — at the top
  band, the fix-round breaker escalates instead (design §6 trigger 5).
- **An `environment` block never promotes.** A bigger model hits the same
  denied permission or missing tool. The project lead fixes the
  environment or performs the blocked action itself — `ic-contract.md`'s
  `BLOCKED` row owns the two causes.
- Log every prediction and every promotion into `state.json`'s
  `band_history` (see `record-format.md`'s `band_history` row for its
  fields). Logging it turns the rubric from a guess into a measurement.
- **A territory runs at the band of the package it starts on**, and keeps
  that model for every package the same IC carries, whatever those
  packages' own bands say. A `deep` first package therefore puts the whole
  territory on opus, and the context the IC keeps is what pays for it: one
  run so ordered took zero fix rounds where a fresh-IC run took fifteen
  (design §15.50). Order the territory's packages with that in mind. The
  IC respawns at the new package's band only when `full-path.md`'s "The
  territory's next package" says to respawn.

## What a band skips

**No band skips a review step.** The spec critic is the only review step a
band could reach, and it runs on every spec.

| Step | `light` | `standard` | `deep` |
|---|---|---|---|
| spec critic | runs | runs | runs |

**The spec critic never skips a spec.** The run writes `spec.md` before the
split, so no package has a band yet when the critic reads it (`SKILL.md`'s
order). It also earns its cost: it sent a spec back on 9 of 27 reviews across
the records, and on 1 of the 3 that ran over a `light` package (design §15.77).
No band takes this step away. Only the light path does, by writing no spec at
all — see the section below.

**The skeptical review takes no band either** (`skeptical-review.md`).

## What the light path skips

The light path is a path, not a band. It takes the spec critic away at every
band it carries (design §15.88). `simple-path.md`'s "The light path" states
when a run takes it; this file states what it drops.

| Step | On the light path |
|---|---|
| spec critic | skipped — the run writes no `spec.md`, so the critic has nothing to read |

**Your own verification of the package is what makes the spec critic safe to
drop.** You verify every package yourself, at every band and on every path.
`simple-path.md`'s "Verify before you believe" owns what that runs, for a code
package and for a prose one, and its "Fix rounds" owns what a failure costs.

**Record every skip.** A run writes it to `state.json`'s `run.steps_skipped`
(`record-format.md` owns the field). A step with no review file and no entry
there reads as a step that failed to run.

## Critics and reviewers take their own model

A band is for a **package**. `crew:spec-critic` and `crew:split-critic` are
not packages, and neither of them gets a band. The skeptical review is not a
package either, and `skeptical-review.md` names the model its command passes.

**Pass no spawn-time `model` when you dispatch one.** Each definition already
carries the model its job needs, and a spawn-time value silently overrides it
(design §12). Dispatching a critic at the package's band is the easy mistake:
it reads like consistency and it quietly downgrades the check (design §15.35).

## Researcher model rules (design §3)

A research question has no file set and no acceptance criterion, so the
observable inputs above cannot score it. Band a `crew:researcher` dispatch
on the question instead:

- **sonnet** by default, for every question.
- **opus** when the question belongs to a `deep`-band package, or when its
  answer will move an interface, a data shape, or a decomposition.
- Never haiku. A weak synthesis over several hops reads as an answer and is
  not one.

`agents/researcher.md` carries `model: sonnet` as that default; the `opus`
case is a spawn-time override.

## Council model rules (design §6.1)

- Every advocate in a council runs **sonnet**.
- Every advocate in **one** council runs the **same** model. Mismatched
  advocates measure model strength, not argument strength, and the project
  lead then picks a side for the wrong reason.
- **Sonnet is the floor.** Haiku produces weak cases, which corrupts the
  adjudication the same way a mismatch does.
- Raise every advocate to **opus**, together, when the decision belongs to a
  `deep`-band package. A council of one adversary takes the same promotion:
  that one advocate runs opus.
- Record which model the advocates ran, on the council entry's `Models:` line
  (`record-format.md`). This is what lets promotion data cover councils, not
  only packages.

`agents/council-advocate.md` carries `model: sonnet` as that default; the
`opus` case is a spawn-time override, passed on every advocate dispatch the
council makes.

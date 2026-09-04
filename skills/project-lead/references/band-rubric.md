# Band rubric

This file decides which model a package or a council gets (design §8, §6.1).

**A band sets model only, and a spawn-time `model` overrides an agent's
frontmatter.** `reasoning_effort` cannot travel that way — a teammate inherits
the project lead's effort (design §12) — so a band cannot set effort. Do not
add an effort column to this rubric. This file is the only place a model is
chosen.

## Bands

| Band | Model | The package looks like |
|---|---|---|
| light | haiku | Follows an existing repo pattern verbatim. Tests already cover the surface. |
| **standard** | **sonnet** | **Default.** |
| deep | opus | A new interface others depend on. A concurrency, security, migration, or data-shape change. Or the project lead had to *interpret* the acceptance criterion rather than read it off the charter. |

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
- **Promotion.** Re-dispatch a package one band up, with no human
  involvement, when its IC reports `BLOCKED` with a `capability` cause,
  exhausts its fix rounds, or goes idle without meeting its acceptance
  test (design §8). A `deep` package cannot promote further — at the top
  band, the fix-round breaker escalates instead (design §6 trigger 6).
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
  IC respawns at the new package's band only when `full-path.md` step 8a
  says to respawn.

## Critics and reviewers take their own model

A band is for a **package**. `crew:spec-critic`, `crew:split-critic`,
`crew:package-reviewer` and `crew:deliverable-reviewer` are not packages, and
none of them gets a band.

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
  `deep`-band package.
- Record which model the advocates ran, on the council entry's `Models:` line
  (`record-format.md`). This is what lets promotion data cover councils, not
  only packages.

`agents/council-advocate.md` carries `model: sonnet` as that default; the
`opus` case is a spawn-time override, passed to every advocate in the batch.

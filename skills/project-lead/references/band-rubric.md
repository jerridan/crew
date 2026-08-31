# Band rubric

This file decides which model a package or a council gets (design §8, §6.1).

A band sets model only. A teammate inherits the project lead's `reasoning_effort`
(design §12), so a band cannot set effort. Do not add an effort column to
this rubric.

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

## Researcher model rules (design §3)

A research question has no file set and no acceptance criterion, so the
observable inputs above cannot score it. Band a `crew:researcher` dispatch
on the question instead:

- **sonnet** by default, for every question.
- **opus** when the question belongs to a `deep`-band package, or when its
  answer will move an interface, a data shape, or a decomposition.
- Never haiku. A weak synthesis over several hops reads as an answer and is
  not one.

`agents/researcher.md` carries `model: sonnet` in its frontmatter as that
default. A spawn-time model overrides it (design §12), which is how the
`opus` case is dispatched.

## Council model rules (design §6.1)

- Every advocate in a council runs **sonnet**.
- Every advocate in **one** council runs the **same** model. Mismatched
  advocates measure model strength, not argument strength, and the project
  lead then picks a side for the wrong reason.
- **Sonnet is the floor.** Haiku produces weak cases, which corrupts the
  adjudication the same way a mismatch does.
- Raise every advocate to **opus**, together, when the decision belongs to a
  `deep`-band package.
- When you record the council's decision in `decisions.md`, note which model
  every advocate ran. This is what lets promotion data cover councils, not
  only packages.

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

A `light` package can skip two steps: the plan gate and the deliverable review.
Every other step runs at every band, the package review included — it is the
check the bounded edit used to skip (design §15.73).

| Step | `light` | `standard` | `deep` |
|---|---|---|---|
| spec critic | runs | runs | runs |
| plan gate | simple path: skipped. Full path: the two checks below. | the two checks below | read the plan in full |
| package review | runs | runs | runs |
| deliverable review | skipped on the three conditions below | runs | runs |

**The two checks** are that every file the plan names is in the file set, and
that the plan changes no `produces` signature. A plan gate that read every plan
in full cost a run a round trip per package for no finding (design §15.50).

**The spec critic never skips a spec.** The run writes `spec.md` before the
split, so no package has a band yet when the critic reads it (`SKILL.md`'s
order). It also earns its cost: it sent a spec back on 9 of 27 reviews across
the records, and on 1 of the 3 that ran over a `light` package (design §15.77).
No band takes this step away. Only the light path does, by writing no spec at
all — see the section below.

**A skipped plan gate keeps the plan.** The IC still writes `plans/<id>.md`, and
it does not stop for a go-ahead, so you dispatch it once instead of twice. Say
in the dispatch prompt that the gate is skipped — `ic-contract.md`'s "The plan
gate" branches on it, and it also says where the plan goes when the record
write is denied. Leave `plan_approved_at` at `null`: no gate ran.

**The deliverable review skips on three conditions, and all three must hold.**
The deliverable holds this one package, its package review reads
`Verdict: accepted`, and you edited no shared file at "Integrate". One package
leaves the seam check and the conflict check nothing to read. An accepted
package review means the diff already had a reader. No shared-file edit rules
out the one defect class this reviewer caught that the package reviewer could
not reach (design §15.77). Fail any one condition and the review runs.

## What the light path skips

The light path is a path, not a band, and it takes two steps away at every
band it carries (design §15.88). `simple-path.md`'s "The light path" states
when a run takes it; this file states what it drops.

| Step | On the light path |
|---|---|
| spec critic | skipped — the run writes no `spec.md`, so the critic has nothing to read |
| plan gate | the table above decides it, by band |
| package review | runs |
| deliverable review | skipped — one package, no `split.md`, and no shared file you edited yourself |

**The package review is what makes the rest safe to drop.** It is the one
reader of the diff, and it runs at every band and on every path. Its fix rounds
are `simple-path.md`'s, unchanged.

**The deliverable review's three conditions all hold here by construction.**
One package, an accepted package review, and no shared file you edited at
"Integrate" — the light path's shared file sits in the package's file set and
the IC edits it. So the skip is the rule and not a judgment, and it still takes
its record entry below.

**Record every skip.** A run writes it to `state.json`'s `run.steps_skipped`
(`record-format.md` owns the field). A step with no review file and no entry
there reads as a step that failed to run.

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
  `deep`-band package. A council of one adversary takes the same promotion:
  that one advocate runs opus.
- Record which model the advocates ran, on the council entry's `Models:` line
  (`record-format.md`). This is what lets promotion data cover councils, not
  only packages.

`agents/council-advocate.md` carries `model: sonnet` as that default; the
`opus` case is a spawn-time override, passed on every advocate dispatch the
council makes.

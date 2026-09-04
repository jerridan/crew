# crew — design

**A project lead that takes one goal to reviewable draft PRs without the human in
the loop, and picks the cheapest model that can do each piece.**

Status: design. Date: 2026-08-24, amended 2026-08-27 and 2026-08-29.

This document says what to build and why. It is the first stage of the
"Personal Agent Org" PRD (`~/.claude/plans/recently-read-a-blurb-pure-piglet.md`),
scoped down to one tier.

---

## 1. Purpose

Today a session stops for the human at every stage: after brainstorming, after
the spec, after the plan, after the plan review. Each stop costs attention, and
the work waits. The model is also chosen before any investigation happens, so
almost everything runs on Opus at high effort — including the parts that did not
need it.

`crew` removes both problems for one goal at a time. You hand a goal to the
project lead. The project lead investigates, writes a spec, has it critiqued,
splits the work, assigns a model per piece, dispatches workers, integrates the
result, and opens draft PRs. It records every judgment call it made on your
behalf so you can audit them at review time.

### In scope

- One goal per run. One project lead, in your session.
- Autonomous progress from hand-off to draft PR.
- Model chosen per unit of work, after investigation.
- A durable record you can read, audit, and resume from.

### Out of scope

- **Autonomous merging.** The draft PR is the terminus. A human merges.
- **A tier above the project lead.** No router, no roster, no `lead` tier
  (§15 items 19, 21, 22). Item 22 names what stage 4 must build so that
  tier can attach later without a rewrite.
- **Concurrent goals.** One goal per project lead session. Run more sessions
  for more.
- **An org-wide view.** No dashboard, no cross-session sweep, no supervision.
- **Replacing CI review.** The existing reviewer fleet stays the quality gate.
  `crew` feeds it.

---

## 2. Relationship to superpowers

`crew` is heavily inspired by the `superpowers` plugin. The process spine — spec,
plan, critique, TDD, review, integrate — comes from there, and several checklists
are copied rather than paraphrased so they stay easy to re-sync.

`crew` is not a wrapper. It never invokes a superpowers skill, because every
superpowers process skill is built to stop and wait for a human, and removing
those stops is the whole point. Section 14 lists every deliberate deviation.

---

## 3. Roles

| Role | Mechanism | Model | Lifetime |
|---|---|---|---|
| **Project lead** | `/crew:project-lead <goal>` in your session | your session's | the run |
| **Scout** | unnamed subagent (`Explore`), briefed inline | haiku or sonnet | one question |
| **Advocate** | unnamed subagent, new `crew:council-advocate` | sonnet | one position |
| **Researcher** | unnamed subagent, new `crew:researcher` | per band | one question |
| **Spec critic** | unnamed subagent, new `crew:spec-critic` | opus / high | one review |
| **Split critic** | unnamed subagent, new `crew:split-critic` | opus / high | one review |
| **IC** | **named teammate** `crew:ic`, or unnamed subagent | per band | a territory |
| **Instruction IC** | **named teammate** `crew:ic-instructions` | per band | a territory |
| **Package reviewer** | unnamed subagent, new `crew:package-reviewer` | sonnet / high | one review |
| **Deliverable reviewer** | unnamed subagent, new `crew:deliverable-reviewer` | opus / high | one review |

### The naming rule

A **named** agent becomes a teammate. A teammate's output never returns to the
project lead, so everything that must return a parseable result stays **unnamed**.

Only ICs get names, because only ICs need two things names provide: resume with
context intact for fix rounds, and graceful stand-down on a direction change.

### What each role may not do

The prohibitions bound cost and blast radius, so they matter more than the
duties.

- The **project lead** does not read code broadly. It dispatches scouts. It
  writes no implementation code except bounded edits (section 9.3).
- An **IC** does not touch files outside its declared set, does not renegotiate
  its own scope, does not push to a remote, and does not spawn a reviewer or
  another implementer. It may spawn read-only lookup subagents only.
- A **critic** or **reviewer** does not edit code. It reports.

---

### 3.1 Specialist ICs

`crew:ic-instructions` is the first specialist. It owns any package whose
deliverable is an instruction file — `CLAUDE.md`, a `.claude/rules/` file, a
`SKILL.md`, or an agent definition — or reader-facing prose that is a
deliverable in its own right, such as a README (§15.17).

It exists because the **acceptance mechanism differs**, not because the subject
matter does. A code IC runs test-first and "green" means a passing test. No test
can be run against a `SKILL.md`. An instruction package's acceptance criterion is
a checklist, verified by a reviewer, so the TDD contract does not apply to it and
forcing prose through that contract produces theatre.

Its contract replaces red-green-refactor with:

1. Pick the container, cheapest one that still reaches the audience.
2. Draft.
3. Revise down — expect to lose about a third.
4. Self-check against the checklist.
5. Commit.

It holds **no copy** of the standard. `writing-standard.md`, under
`skills/project-lead/references/`, is canonical, and the IC's brief tells it
to read that file before writing anything. It is a plain reference file, not a
skill invocation, so there is no fork risk: the IC reads it with its own
`Read` tool, into its own context, every time — and the standard's own rule
applies to itself: a second copy of a rule is worse than no copy, because
nothing decides which copy wins.

It covers all five container types this IC owns directly, with no hand-off to
another skill for two of the five.

`crew:package-reviewer` reviews its work as usual, with the checklist as the
rubric instead of a diff-and-tests review. The project lead passes it the
checklist's path, so there is still one copy.

**The IC is judged on its output, not on how it obtained the standard.** That
keeps the contract intact when an IC forgets to read the file, or reads a stale
copy.

This is the general rule for adding a specialist later: **split an IC when the
definition of done changes, not when the subject changes.** A new language or
framework is a generalist's job. A different acceptance mechanism is not.

Building `crew` is itself almost entirely instruction files, so this specialist
does most of the packages in crew's own construction — which makes it the natural
way to prove stage 2 works.

## 4. The record

One directory per goal, outside the target repo so the repo stays clean:

```
~/.claude/crew/<goal-slug>/
├── charter.md        goal + falsifiable acceptance criterion
├── spec.md           the spec the project lead wrote after scouting
├── split.md          deliverables → packages, with interfaces and bands
├── state.json        deliverables, per-package state, band history, spend, escalations
├── decisions.md      every judgment call, with its citation or reasoning
├── worktrees.json    IC name → worktree path → branch → session ids → orphaned
├── reports/          one report per package, written by its IC
├── plans/            one plan per package, written by its IC
└── reviews/          raw critic and reviewer output
```

`state.json` is **authoritative for the plan** — which packages exist, their
bands, their file sets, their contracts, and what the project lead intended.
Messages between agents are notifications only; a lost message costs latency,
never correctness. Nothing in the design may treat the agent-team task list as
the source of truth, because that is what keeps a later move to independent
sessions cheap.

**The worktrees are authoritative for progress.** After a crash `state.json` can
be stale — it may call a package in-flight that an IC actually finished, or the
reverse. Git cannot lie about what landed, so recovery reconciles against the
worktrees rather than trusting the record (section 10.1).

The project lead writes `state.json` after **every** state transition, not
batched at package boundaries. A crash then loses at most one transition.

At the end, the project lead copies `spec.md` and `decisions.md` into the
draft PR body. That is where you review them.

### `decisions.md`

Every entry records: the question, how it was routed (section 6), the answer, and
either the exact instruction that resolved it or the reasoning that produced it.

```markdown
## Should the version bump be part of package 2?
Route: precedent
Answer: No — the project lead bumps versions at integration.
Citation: CLAUDE.md "Development Workflow" step 3 requires both plugin.json and
marketplace.json to change, which no two packages can own disjointly.
Confidence: high
```

An entry with high confidence and no citation is a defect.

---

## 5. Decomposition

### Two levels

- A **goal** splits into 1..N **deliverables**. One deliverable is one branch and
  one draft PR. Deliverables run **sequentially**, because a later one may build
  on an earlier one.
- A deliverable splits into 1..M **packages**. Packages run **in parallel**.
  The one exception is §9.5's report ending: a deliverable whose product is a
  diagnosis and no change holds no package and no branch.

The project lead decides both counts after scouting. A goal that is too large
for one PR gets several deliverables; that judgment is the project lead's to
make.

### Territories

Packages are grouped into **territories** — regions of the file tree. One IC owns
one territory and works every package in it, in order, in one worktree.

This follows the agent-team guidance of 3-5 workers with several tasks each,
rather than one worker per task. It also means fewer spawns, an IC that keeps its
accumulated repo knowledge across packages, and one merge per IC instead of one
per package.

### Package right-sizing

Copied from `superpowers:writing-plans`:

> A task is the smallest unit that carries its own test cycle and is worth a
> fresh reviewer's gate. Fold setup, configuration, scaffolding, and
> documentation steps into the task whose deliverable needs them; split only
> where a reviewer could meaningfully reject one task while approving its
> neighbor.

### The invariant

A package is dispatchable only when it has all four:

1. Its own acceptance criterion, which is satisfied by only its own changes.
   That is **an executable test** for code, or **a written checklist verified by
   a named reviewer** for a package that produces prose (section 3.1).
2. A file set disjoint from every concurrent sibling.
3. A written interface contract with its siblings.
4. A band (section 8).

Packages that cannot be made disjoint are serialized or merged.

### Interface contracts

Copied from `superpowers:writing-plans`. Every package records:

- **Consumes:** what it uses from earlier packages — exact signatures.
- **Produces:** what later packages rely on — exact names, parameter and return
  types.

The rationale is stronger here than in superpowers: an IC works in an isolated
worktree and **cannot see its siblings' work at all**. This block is the only
channel between packages.

### Global constraints

`split.md` carries a `Global Constraints` section: project-wide requirements
copied verbatim from the spec — version floors, dependency limits, naming rules,
platform requirements. Every package's requirements implicitly include it, and
the project lead injects it into every IC spawn prompt.

### Shared files belong to the project lead

Version manifests, lockfiles, barrel and `index` files, and shared config are
never in a package's file set. The project lead edits them at integration.

In this repo that means `plugin.json` and `marketplace.json` specifically:
`CLAUDE.md` requires both to change for any content change, so no two packages
could ever own them disjointly.

### The critic

`crew:split-critic` reviews `split.md` before any IC is dispatched. It checks
only the invariant, and nothing else:

1. Is every file set disjoint from its concurrent siblings? Look hardest at
   shared config, barrel and `index` files, test helpers, snapshots, lockfiles,
   and version manifests. The shared files below belong to the project lead and
   never to a package. A test helper or a snapshot two packages both touch is a
   collision too, but it belongs to one of them.
2. Is every interface contract written, with exact signatures and types?
3. Can each acceptance test pass with only its own package's changes?
4. Is anything mis-split — two packages that should be one, or one that must be
   serialized behind another?
5. Is any "parallel" set a dependency chain in disguise?
6. **Type consistency:** do names, signatures, and types used by a later package
   match what an earlier package defines? A function called `clearLayers()` in
   one package and `clearFullLayers()` in another is a bug.
7. Does any package reference a type, function, or method that no package
   defines?

This is one cheap Opus call that prevents days of wasted IC work. It is skipped
only on the simple path (section 9.1), where there is one package and nothing to
check.

---

## 6. The autonomy contract

The project lead answers its own questions. It asks you only when it genuinely
cannot proceed correctly.

### Routing

Every question is classified and **the routing is logged to `decisions.md`
before it is answered**, so an audit can catch a pivotal question that was
wrongly routed. Routing without a recorded reason is a defect.

| Route | For | How |
|---|---|---|
| **Precedent** | "How does this work here?" / anything an instruction covers | Section 6.2 |
| **Council** | Judgment with a determinable answer, and **every** question touching a data model, public interface, service boundary, or cross-cutting pattern | Section 6.1 |
| **Preference** | What the human wants, where evidence cannot decide: opt-in or not, match old behavior or fix it, is this worth doing | Resolve from `CLAUDE.md`, `.claude/rules/`, or an explicit prior decision. Otherwise **escalate**. Never debate. |

The preference route exists because a council will always name a winner, grounded
in precedent — and precedent is the wrong guide when the point is to change
something deliberately. Debating a preference question converts "I do not know
what you want" into "we established you want X", buried in a record instead of
surfaced as a question. That is worse than asking.

A question may be answered inline only when the project lead can cite why every
alternative is implausible. An inline answer with no citation is suspect; when in
doubt, route to a council.

**The council is discretionary.** The ladder is: confident → answer it and record
why; unsure → convene a council; council inconclusive → flag it for the human.
The project lead is not obliged to spin up a council for a question it can already
answer.

The one constraint on that discretion: **an architecture-moving question answered
inline must cite why the alternatives are implausible.** That is what stops the
"mis-framed as trivial, so never debated" blind spot from returning. Confidence
without a citation is not confidence, and it routes to a council.

### 6.1 Council

Adapted from the `resolve-ticket` plugin.

1. Frame 2 or more candidate positions. Cap at 3.
2. Dispatch one `crew:council-advocate` per position, unnamed, in parallel, in
   a single batch. The definition carries the rules: argue **for** your
   assigned position, gather cited evidence from code and docs, make the
   strongest case, and name the strongest objection to your own side.
3. The project lead adjudicates and picks a winner.
4. Record the decision, the losing arguments, the citations, and a confidence
   level. Never record high confidence without a citation.

A council is adversarial advocacy with one judge, not a poll. Agreement between
agents from the same base model measures shared priors, not correctness, which is
why positions are assigned rather than discovered.

**When a council is balanced** — the project lead cannot pick a winner at medium
confidence or better — **and the question is architecture-moving, the project lead
escalates.** It does not flag and continue.

This differs from `resolve-ticket`, deliberately. There, one ticket produces one
PR a human reviews. Here, a wrong architecture-moving call propagates into the
decomposition and then into every IC in parallel, so it costs the whole run.
Same machinery, higher threshold, because the blast radius is larger.

**Models.** Advocates run **sonnet**. The project lead adjudicates at its own
model. Advocacy is evidence-gathering and synthesis; the judgment is the
expensive part, so the capable model goes on the judging, not the gathering.

Two rules on top:

- **Every advocate in one council runs the same model.** Mismatched advocates
  measure model strength rather than argument strength, and the adjudicator then
  picks a side for the wrong reason.
- **Sonnet is the floor.** Haiku produces weak cases, which corrupts the
  adjudication in the same way.

Raise every advocate to opus together when the decision is `deep`-band. Record
which model a council used, so promotion data covers councils too.

Council spend is logged. It is expected to be the largest single line item in a
run.

### 6.2 Precedent and competing patterns

Repos carry several patterns for the same job, and some of them are patterns the
team is moving away from. Volume is not evidence. Search in this order and stop
at the first answer:

1. **An explicit instruction** — `CLAUDE.md`, then `.claude/rules/`, then any
   nested `CLAUDE.md` closer to the files being changed.
2. **An explicit prior decision** recorded in `decisions.md` this run.
3. **Repo precedent.**

**An instruction is the final word.** When an instruction says not to use a
pattern and the repo is full of that pattern, the instruction wins. The
project lead records the conflict — the instruction, and the fact that
precedent contradicts it — so the volume of old usage never looks like a
reason to ignore the rule.

Treat these as deprecation signals with the same weight as an instruction: a lint
rule against the pattern, a `deprecated` marker, a migration document, or a
codemod in the repo.

**When precedent is split and no instruction resolves it**, do not pick the
more common one. Check whether the split tracks age: if new files use one
pattern and old files use the other, the newer one is the direction of travel,
and that is real evidence — record it and proceed. If the split does not track
age, the project lead has no basis to choose, and this becomes a
**preference** question.

Escalate it, and make the escalation productive:

```
Two patterns exist for <job> and no instruction covers it:

A. <pattern> — <N> usages, e.g. <path:line>
B. <pattern> — <M> usages, e.g. <path:line>
Age: <does the split track age, or not>
My recommendation: <which, and why>

Which should crew use? Want me to record the answer in <CLAUDE.md or the right
.claude/rules/ file> so this never comes back?
```

The project lead **proposes** the instruction text and never writes it without
your explicit approval — instructions are configuration, and changing them is
your decision, not a side effect of a run.

This is the one escalation that pays for itself. Every answer becomes an
instruction that resolves the same question in every future run, so the question
rate should fall over time instead of staying flat.

**ICs never escalate to the human — they escalate to the project lead.** An IC
that hits pattern ambiguity inside a package messages the project lead. The
project lead answers it if an instruction covers it, and otherwise batches it
for you.

**An IC does not wait for the answer.** A message to a busy project lead sits
until the project lead is between actions, so an IC that stops and goes idle
turns one question into a stalled worktree. In order of preference, an asking
IC:

1. Proceeds under a stated assumption, records it, and names it in its report.
   The project lead corrects it in a fix round if the assumption was wrong —
   cheap, because messaging the same IC keeps its context.
2. Moves to the next package in its territory, if that package does not depend on
   the answer.
3. Stops only when the question is load-bearing for the whole package and it
   cannot write any code without it.

This is the same rule the project lead follows one level up: do everything
that does not depend on the answer first, then ask once.

An IC must never go idle with an unanswered question and no stated assumption.
The project lead enforces this: it verifies every IC before it accepts a
package (section 7), and messages an IC that idles without one (section 13.1).

**Blocking rule.** A pattern choice that changes the decomposition or an
interface contract blocks — the project lead cannot split the work without it.
Any other pattern choice is batched: the project lead does everything that
does not depend on the answer first, then asks once.

### 6.3 The preference sweep

Between the spec and the split, the project lead reads the charter and the spec
again, lists every open question in them that turns on what the principal wants,
and escalates the list as one batch. One interruption, before any IC runs.

A preference question is one the repo cannot answer: no instruction, no prior
decision this run, and no precedent settles it. A split precedent that does not
track age (section 6.2) is one. So is a deliberate change, where the charter
asks to change what the repo does and the existing pattern is what is being
replaced — "the repo already does X" does not answer "should it still do X?".

The sweep exists because the preference route was passive. Six runs escalated
nothing, and in the §15.50 A/B both project leads settled the one question the
answer key marked as the principal's by calling it precedent. Nothing made the
project lead look for such a question while asking was still cheap, and after
the split the answer costs a fix round.

A run whose sweep finds no preference question escalates nothing. It records
the sweep either way, so an audit can tell "none found" from "never looked".
`autonomy-contract.md` owns the rule and `record-format.md` the entry.

### Escalation triggers

**This list is a floor, not a ceiling.** These are the cases where the project
lead *must* stop. It is never forbidden from asking about anything else.

A project lead that reads "narrow triggers" as "never ask" is the failure this
paragraph exists to prevent. No human in the loop is the goal, not the rule. A
question costs one interruption; a project built in the wrong direction costs
a day, and the assumption trail only shows you that after the fact. So when
the cost of being wrong is high and confidence is low, ask — and record that
the ask was a judgment call rather than a trigger.

Each answer you give can then be written into `CLAUDE.md` or `.claude/rules/`
(section 6.2), which retires that question for every future run. The right
number of escalations early is higher than the right number later.

Triggers are batched into one interruption where possible.

1. No falsifiable acceptance criterion can be written for the goal. The
   project lead aborts before doing any work.
2. A **preference** question that no instruction resolves — including a split
   precedent that does not track age (section 6.2).
3. A **balanced council** on an architecture-moving question.
4. Any action outside an isolated workspace: the main branch, production, or
   credentials.
5. The charter's budget is exceeded (section 8).
6. A package reached the fix-round breaker at the top band.

Everything else the project lead settles itself and records — unless it judges
that getting it wrong would take the work off the rails, in which case it asks
anyway.

### 6.4 Instruments

A target repo can carry its own investigation skills or agents — a database
query, an internal endpoint lookup — with access crew must never hold on its
own. Crew ships none of these, discovers none by scanning the repo, and never
dispatches one that the charter does not name.

**The principal names the list at hand-off.** The charter carries an explicit
list of repo-local skills or agents this run may dispatch, called its
instruments. `record-format.md` owns the charter's `Instruments:` field and
what it means for a run to have none.

**Only the project lead or a researcher may dispatch a listed instrument**,
and only during scouting or research, before any package is split out. An IC
may not: its worktree and file set are already the bound on what it can touch
(section 3, "What each role may not do"), and an instrument's access was
vetted for the dispatch that named it, not for whatever an IC's territory
turns out to need.

**An instrument's output is a claim, not evidence**, treated exactly like an
IC's report (section 7): the project lead restates it, checks it against
whatever the repo or the record can confirm, and never acts on it unverified.
An instrument that returns a fact no other source confirms is a lead to
follow, not a fact to build on.

Every dispatch of a listed instrument is recorded in the run's record.
`record-format.md` owns where the entry lives.

---

## 7. Verification

The project lead's hardest rule, copied from
`superpowers:verification-before-completion`:

> **NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.**

This matters more here than in a normal session, because a teammate's output
never reaches the project lead at all. So:

| Claim | Requires | Not sufficient |
|---|---|---|
| An IC finished | `git -C <worktree> log` and `diff` show the work, on the right branch | the IC's report |
| Tests pass | a fresh run's output, 0 failures | a previous run, "should pass" |
| Requirements met | a line-by-line check against the charter | tests passing |
| A new test proves the change | the acceptance criterion fails at the commit that adds the test, on a run the project lead performed itself | the criterion passing at the branch head |

**"Passes after" is half a criterion.** A test that never failed satisfies row
2 and proves nothing. So when a package's acceptance criterion is a test the
package adds, the IC writes that test first and commits it red, before it
writes the code that makes it pass (`ic-contract.md`). The project lead runs
the criterion at that commit when it verifies the package, and a criterion
that passes there sends the package back to a fix round. A reviewer reading
the diff is not what catches this.

Two criteria need no red commit, and neither is a test the package adds. A
reviewer checklist for an instruction package is not executable (section 5,
invariant 1). A test that already exists and already fails was proved before
the dispatch — the investigation path's reproduction is that case, and
`diagnosis.md` holds its failing output (section 9.5).

**An IC's report is a claim, not evidence.** Every IC completion is checked
against its worktree before the project lead believes it. That check also
catches an IC that drifted out of its assigned worktree (section 12).

A green run only proves the tree it ran on, so the project lead re-runs after
every merge.

### Adjudication

The project lead receives findings from reviewers. Adapted from
`superpowers:receiving-code-review`:

1. Read the whole set without acting.
2. Restate each finding in its own words.
3. Verify it against the codebase.
4. Evaluate whether it is right **for this codebase**.
5. Push back with technical reasoning where it is not, and record the pushback.
6. Fix one at a time, in order: blocking, then simple, then complex.

**Assuming the reviewer is right is a mistake, not deference.** If a finding
is unclear, the project lead does not dispatch a fix round on it — it requests
a clarified re-review first. That is what stops review-loop thrash.

Before "implementing properly", grep for real usage. Unused means remove it.

---

## 8. Model and cost policy

Model is chosen **per package, after scouting**. Effort cannot be set per
teammate — a teammate inherits the project lead's effort — so bands are model
only.

| Band | Model | The package looks like |
|---|---|---|
| light | haiku | Follows an existing repo pattern verbatim; tests already cover the surface |
| **standard** | **sonnet** | **default** |
| deep | opus | A new interface others depend on; concurrency, security, migration, or a data-shape change; or the project lead had to *interpret* the acceptance criterion rather than read it off the charter |

Rules:

- The default is `standard`. Choosing `deep` requires a written justification in
  `split.md`.
- **Promotion:** an IC that reports `BLOCKED`, exhausts its fix rounds, or goes
  idle without meeting its acceptance test is re-dispatched one band up. No human
  involvement.
- Every promotion is logged with predicted band, actual band, and cause. That
  turns the rubric from a guess into a measurement.
- A charter may name a budget in dollars. Exceeding it escalates.

Spend is measured from the transcripts. Every session that runs from the
checkout — the project lead's own, each teammate, each subagent — writes its
per-request usage to `~/.claude/projects/<checkout>/`, and
`skills/project-lead/scripts/spend.py` prices all of it at list price into
`spend.transcript`. `autonomy-contract.md` says when the project lead runs
it.

`skills/project-lead/scripts/crew-stats.py` reads the whole record root and
prints cost per package by band, fix rounds by band, promotions, councils and
their spend, escalations, compactions and review counts. It imports
`spend.py` for the prices, so there is one price table. A person runs it; no
agent does. It turns this section's rubric into a measurement, and it gives a
charter `Budget:` a number to start from (§15.51).

The token ceiling this section once required is gone (§15.50). It counted
subagent completion notifications only, which missed the project lead's own
session and every teammate — 90% of a measured run — so it never fired in
seven runs, and the one time spend mattered the user's subscription limit
fired first. A dollar figure from the transcripts is the whole of what
remains, and a charter `Budget:` line is the only gate on it.

One `crew:ic` definition serves all three bands, because a spawn-time `model`
overrides the definition's frontmatter (section 12).

**The project lead runs on Fable 5.1 at high effort.** The seat is the run's
judgment, not its volume: it writes the spec and the split, decides the
order of work, and adjudicates every review. §15.50 measured the two
candidates on one full-path goal. The Fable project lead cost two thirds of
the Opus arm, did the lead's own work in a third of the turns, took no fix
rounds where Opus took fifteen, and made the process choices — harness
first, fewer packages, one IC carrying its context — that produced that
result. The per-token price difference was not the reason; the order of
work was. Fable's cache-read price only starts to pay in a session over a
few hundred turns, which a project lead reaches and an IC does not. ICs,
reviewers and critics keep their bands and their own models.

---

## 9. The execution loop

### 9.1 Choosing the shape

After scouting, the project lead picks the shape. **Mechanism follows the need
for a conversation, not the size of the work.**

| Situation | Shape |
|---|---|
| A bounded edit: 1-2 tool calls, no file reading needed | The project lead does it itself |
| One simple package | **Simple path:** one unnamed subagent, no worktree, working directly on the deliverable branch. No critic, no merge, no cleanup. Its result returns as a normal tool result. |
| Several packages, or work long enough to need steering | **Full path:** IC teammates in worktrees |

The simple path is much cheaper and is expected to be the common case for
small goals. The project lead is idle while the subagent works, so sharing the
tree costs nothing.

The project lead does work itself only for bounded edits. Its own context is
the most expensive place to do anything: it runs at your model and effort, and
everything it reads inflates every later turn.

This table assumes the goal names a change. A goal that names a symptom takes
the investigation path first (§9.5), and comes back to this table only when it
has a diagnosis to build from.

### 9.2 Full path, per deliverable

1. Create a worktree and branch per IC. Record them in `worktrees.json`.
2. Spawn IC teammates at their band. The spawn prompt carries: the package
   brief, the declared file set, the worktree path, the interface contracts, the
   acceptance test, and the global constraints. A teammate inherits no
   conversation history, so the prompt must be self-contained.
3. Require plan approval. Today this means the fallback: the IC plans in
   read-only mode, writes its plan into the record, and waits for the project
   lead's go-ahead by message — see section 12's `PROBE PENDING` entry on plan
   approval. Native plan approval is the pending upgrade; swap to it once that
   probe confirms it works. Autonomous either way.
4. The IC implements test-first, **commits after every green step**, self-reviews,
   and writes its report into the record.
5. The project lead verifies the worktree (section 7), then writes the diff to
   a file (`git diff > <path>`) and dispatches `crew:package-reviewer` with
   the **path**. The diff never enters the project lead's context.
6. Fix rounds, five maximum. Rounds 1-3 message the same IC, so it keeps its
   context. Rounds 4-5 respawn a fresh IC one band up. Then the breaker: fix,
   park with recorded reasoning, or defer.
7. Repeat for the IC's next package in its territory.

### 9.3 Integration

All ICs branch from the same base — the deliverable branch head — so integration
is a merge, not a rebase.

```
git merge --squash <ic-branch> && git commit -m "<package one-liner>"
<run the suite>
```

One squashed commit per package gives a narrative a reviewer can read, and the
IC's per-green-step commits stay on its own branch for resume safety.

**Test after each merge, not after all of them.** A failure is then attributable
to one package for free, with no bisect.

Then the project lead edits the shared files itself, bumps both version
fields, and dispatches `crew:deliverable-reviewer` over the whole diff. That
dispatch carries `spec.md` and this deliverable's `split.md` with the diff.
Four of the reviewer's seven checks read the record, not the diff, so a
diff-only dispatch cannot run them (§15.24). The project lead then adjudicates
the findings, pushes, and opens a **draft** PR with `spec.md` and
`decisions.md` in the body.

Textual conflicts should be impossible: disjoint file sets leave git nothing
to conflict on, and the project lead owns every shared file. What remains is
the semantic conflict — two packages that merge cleanly and break at runtime —
which the per-merge test run catches.

### 9.4 Cleanup

The project lead removes each IC worktree when the deliverable closes, and
prunes stale registrations. Copied from
`superpowers:finishing-a-development-branch`:

**Never force a worktree removal.** A refusal means files exist nowhere else.
Commit them to the IC branch or surface them. Clean up only worktrees `crew`
created.

### 9.5 The investigation path

§9.1 assumes the goal names a change. A bug report and a support ticket do
not. They name a symptom, and the cause is unknown. Most of the work is
diagnosis, and such a run can end correctly with no code change at all.

**Pick the path at `SKILL.md` step 1, from the charter.** The test is what
the goal names: a change to make, or a symptom whose cause is unknown. "The
export drops the last row" is a symptom. "Add a `--json` flag" is a change.
The project lead reads the charter at that step anyway, so this costs no
extra turn.

#### The bug charter

The acceptance criterion is a **reproduction**: one test or one command that
fails now and passes after the fix. Both clauses are required. A criterion
that only says "passes after" is satisfied by a test that never failed. §7's
table carries the row that checks the "fails now" clause. On this path the
reproduction fails before the IC is dispatched, so the evidence is
`diagnosis.md`, and §7 exempts the fix package from a red commit.

**The reproduction is written twice.** At step 1 the charter carries the
symptom, stated so that some future command could falsify it. The command
itself comes out of Phase 1 below, because writing it needs what step 2's
scouting finds — what runs the suite, and where the surface is. Step 1 cannot
produce a failing command in a repo it has not read yet.

When Phase 1 ends with no way to make the symptom happen on demand, the run
has no falsifiable criterion. §6 trigger 1 fires and the run stops, having
spent one scouting pass and nothing more. "Gather more data" is the
escalation, not a hypothesis.

#### The checklist

Copied word for word from `superpowers:systematic-debugging` (§2, §14). The
project lead follows it, and so does every IC it dispatches on this path.

> ```
> NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST
> ```

> | Phase | Key Activities | Success Criteria |
> |-------|---------------|------------------|
> | **1. Root Cause** | Read errors, reproduce, check changes, gather evidence | Understand WHAT and WHY |
> | **2. Pattern** | Find working examples, compare | Identify differences |
> | **3. Hypothesis** | Form theory, test minimally | Confirmed or new hypothesis |
> | **4. Implementation** | Create test, fix, verify | Bug resolved, tests pass |

> If you catch yourself thinking:
> - "Quick fix for now, investigate later"
> - "Just try changing X and see if it works"
> - "Add multiple changes, run tests"
> - "Skip the test, I'll manually verify"
> - "It's probably X, let me fix that"
> - "I don't fully understand but this might work"
> - "Pattern says X but I'll adapt it differently"
> - "Here are the main problems: [lists fixes without investigation]"
> - Proposing solutions before tracing data flow
> - **"One more fix attempt" (when already tried 2+)**
> - **Each fix reveals new problem in different place**
>
> **ALL of these mean: STOP. Return to Phase 1.**
>
> **If 3+ fixes failed:** Question the architecture (see Phase 4.5)

Phase 1 is scouting with a different question. §9.1's step 2 asks what the
repo already does; here the project lead dispatches `Explore` subagents and
`crew:researcher` to ask where the value goes wrong. `crew:researcher` exists
for the hop-by-hop question a one-shot scout cannot answer (§3), and this path
is its first caller.

Evidence is a file, not a memory. Each scout writes what it found to the
record, and the project lead reads the paths. The same rule as a review diff
(§9.2 step 5), for the same reason: the reading must not inflate the judge's
context.

#### Competing hypotheses go to a council

Phase 3 tells one debugger to hold one hypothesis at a time. Crew has several
agents and one judge, so it tests the survivors against each other instead.

When Phase 2 leaves **more than one** hypothesis standing, the project lead
convenes a council (§6.1) with three assigned advocates — §6.1's cap, and its
full shape rather than a single adversary. Competing root causes over one body
of evidence is what assigned positions are for. One surviving hypothesis is
not a council. The project lead tests it under Phase 3 and moves on.

T22 in `docs/tickets.md` narrows the full council to two cases, and this is
its second. That ticket is open, so §6.1 does not yet carry the narrowing. If
T22 lands with a different case list, this paragraph is one of the places it
has to reach.

Three rules on top of §6.1:

- **Every advocate reads the same evidence set.** The project lead names the
  paths in the spawn prompt. An advocate that gathers its own evidence is
  arguing about a different bug.
- **An advocate may concede.** A design council has no true answer, so a
  losing case is still worth making. A root cause does have one, and an
  advocate that argues a refuted hypothesis anyway hands the judge a case
  built on nothing. An advocate that finds its assigned hypothesis
  contradicted reports that, with the citation that contradicts it.
- **The winner is a claim until a change proves it.** The adjudication picks
  the hypothesis to test first. Phase 3 tests it minimally, and a failed test
  returns to Phase 1 with what the failure taught, never to the runner-up by
  default.

#### The diagnosis artifact

The project lead writes `diagnosis.md` into the record: the reproduction, the
evidence with its paths, the root cause, and every hypothesis it ruled out
with the evidence that ruled it out. `record-format.md` owns the name and the
fields.

The ruled-out list is the part that pays. A later run on the same symptom
reads it as precedent (§6.2) and does not re-run the councils this one paid
for.

**A diagnosis is verified like any other claim.** §7 forbids a completion
claim with no fresh evidence, and a report ending produces no diff, so neither
the package reviewer nor the deliverable reviewer can run over it. The project
lead's own artifact would otherwise be its own evidence. So before it writes
`Outcome: no change`, it dispatches one `crew:council-advocate` over the same
evidence set to argue that the root cause is wrong. A conclusion the project
lead cannot defend in writing against that case is an escalation, not a
finished run. This is T22's default adversary, applied to the artifact instead
of to a question, and it is one sonnet call.

#### Where the path rejoins, and where it stops

A diagnosed fix is normal work. The project lead goes back to §9.1's table
with it, and a fix is usually one package on the simple path. Two things
carry across:

- The reproduction is the package's acceptance criterion (§5 invariant 1). It
  already fails, so the "fails now" clause is evidence, not a claim.
- `diagnosis.md` goes into the IC's spawn prompt and into the PR body. An IC
  that gets the symptom without the cause fixes the symptom.

A run that finds no change to make still finishes. The diagnosis is the
deliverable: the project lead ends it `work-complete` with `pr_url: null`,
and the record is what the principal is handed. That covers the bug that is
not a bug, the bug whose fix belongs to another team, and the question the
principal asked to have answered rather than fixed.

**A report ending is §5's one exception to a deliverable holding at least one
package.** It holds none, and it needs no branch either: nothing is edited, so
`branch`, `base`, `checkout_branch` and `checkout_restored` are all `null`,
and `SKILL.md` step 14's checkout restore has nothing to put back.
`record-format.md` carries each of those `null` cases in the field row that
owns it. The moment a fix package exists the deliverable is a normal one, and
step 7 creates its branch as usual.

**A run does not choose the report ending to avoid the work.** It ends there
only when the diagnosis says there is no change to make in this repo, and
`diagnosis.md` says which. Every other ending is a fix.

---

## 10. Intervention and re-planning

You can interrupt the project lead at any point, and you can open any IC in
the agent panel and message it directly.

A direction change may revise the spec, recompute the decomposition, and replace
work in flight. Two rules:

- **Stand down, never kill.** An IC that is being replaced is asked to commit
  what it has and stop. Work in progress is retained.
- **Distinguish the states.** A package is `pending`, `in-flight`, `integrated`,
  or `abandoned`. A deliverable follows the same states, except its terminal
  values are `draft-pr-opened` and `work-complete`, not `integrated` —
  `record-format.md` owns what separates the two, and no deliverable state
  ever means the deliverable reached `main`. A re-plan cares about the first
  three: integrated work cannot be revised in place — it needs new corrective
  work. A re-plan that treats all
  packages alike produces a spec that no longer describes what already landed.
  `abandoned` is the terminal state for a package the breaker parked or
  deferred, or a re-plan dropped, and it is never revived; new work gets a
  new package (§15 item 7).

### 10.1 Recovery after a kill

A whole team dies at once — teammates are in-process, so a crash, a closed
terminal, a reboot, or a `/resume` takes all of them down together. What survives
is every IC's worktree: its commits, **and its uncommitted edits**, because a
worktree is a directory on disk. What is lost is each IC's live context and any
message in flight.

`/crew:project-lead --resume <goal-slug>` reconciles. For every worktree in
`worktrees.json`:

| Worktree state | Meaning | Action |
|---|---|---|
| Has commits, clean | The IC may have finished | Verify against the package's acceptance test before believing it. Do not re-run work that already passes. |
| Has commits, **dirty** | Died mid-package | **Commit the dirty work first**, then respawn. Never discard it. |
| Clean, no commits | Nothing was done | Respawn from the original brief |
| Recorded `integrated` and still present | Already merged | Safe to prune |

Three rules make this work:

1. **Never discard a dirty worktree.** Commit it before anything else. This is
   the crash-time form of "stand down, never kill" (section 10). Uncommitted work
   is the only thing in the system that exists in exactly one place.
2. **Reconcile from git, then correct the record.** `git -C <wt> log <base>..HEAD`
   and `git -C <wt> status --porcelain` are the evidence. `state.json` is
   rewritten to match them, not the other way round.
3. **A respawned IC is a new IC.** It holds no context, so its brief must
   describe what is already in its worktree — `git log --oneline` plus
   `git diff --stat` is enough — and say which steps are done. Its acceptance
   test tells it when to stop, which is what keeps a respawn idempotent.

The deliverable branch needs the same reconciliation: if the project lead died
after merging two of four packages, `git log` on that branch shows which.
Already-merged packages are `integrated` and cannot be revised in place — they
need new corrective work (section 10).

Pruning an orphaned worktree never forces (section 9.4). If a worktree holds
uncommitted files, the project lead commits them to that IC's branch and says
so, rather than removing it.

Known recovery detail: a project lead killed mid-commit can leave a stale
`index.lock` in a worktree. Resume clears one only when no process holds it.

---

## 11. Overriding the "monitor and steer" guidance

The agent-teams documentation warns that letting a team run unattended increases
the risk of wasted effort, and recommends monitoring and steering. `crew`
overrides that deliberately.

The premise of this design is that the **project lead** is the monitor, not
you. The check-ins are the plan-approval gate, the per-package review, the
per-merge test run, and the record. If those are not enough, the answer is to
strengthen them — not to put the human back in the loop, which restores the
original problem.

The documentation also recommends starting with research and review rather than
parallel implementation. So the first real run should be a small, familiar goal.

---

## 12. Verified platform constraints

Measured by probe, not assumed. Each one shapes a requirement above.
Everything above the `Skill`-tool rows was probed on 2026-08-24. The three
`Skill`-tool rows were probed on 2026-08-27, on Claude Code 2.1.247, from
`--output-format stream-json --verbose` transcripts.

| Constraint | Consequence |
|---|---|
| `isolation: "worktree"` creates a real separate worktree and branch | Isolation is available for subagents |
| Without the flag, an agent shares the project lead's tree | Isolation is never automatic |
| Passing `isolation` **downgrades a named agent to a subagent** | An IC cannot be both a teammate and harness-isolated. The project lead builds worktrees itself. |
| A project lead **can** run `git worktree add` from inside a worktree, and a teammate can work, write, and commit there with no guard, provided the driving session is not itself worktree-isolated (§15 item 10) | The workaround holds |
| **The shell cwd resets after every Bash call.** `cd` holds only within one invocation. | Every IC command must carry its own `cd <worktree> &&`. An IC that forgets works on the wrong checkout with **no error**. Detection is the project lead's verification step. |
| Spawn-time `model` overrides frontmatter `model:`; frontmatter applies when no override is passed | One `crew:ic` definition serves all bands |
| `reasoning_effort` is frontmatter only, and teammates inherit the project lead's effort | Bands are model only |
| A teammate's output never returns to the dispatcher | ICs write reports into the record |
| A teammate does not know its own model | Band assignment cannot be verified by asking |
| Task tools are off by default on Opus 5 and Sonnet 5 | The project lead session must be launched with `--allowedTools TaskCreate TaskGet TaskList TaskUpdate` to get the shared task list and dependency blocking |
| `hooks` in agent frontmatter is **ignored for teammates**, and plugin agents cannot use `hooks` at all | IC behavior cannot be hook-enforced without a global hook. See section 13. |
| Teammates cannot spawn teammates; a teammate's subagents run in the foreground | An IC may use read-only lookup subagents, but they block it |
| `claude -p` cannot spawn teammates | A future detached project lead must be interactive |
| Teammate spawning needs a working display mode | `it2` installed plus the iTerm2 Python API enabled, or run inside tmux, or `teammateMode: "in-process"` |
| Plain headless `-p` mode auto-rejects the `Skill` tool with no surface to approve it (`tool_result_meta` shows `user-rejected`) | A headless session cannot exercise a skill-invocation path. The model falls back to `Read`/`Bash` and can still produce a plausible answer. A probe that relies on this path passes vacuously. |
| Under `--permission-mode bypassPermissions`, the `Skill` tool executes. It labels its result `(forked execution)` regardless of the skill's `context:` setting. In one run its result text was stale and wrong. | The `Skill` tool's own result text is not evidence of how a skill executed, or of the tree's current state. |
| In headless mode, `subagent_stats.spawned` and `parent_tool_use_id` were identical — `0` and `null` — for a skill with no `context:` key and for one with `context: fork` | The harness exposes no signal for fork-vs-inline skill execution. The frontmatter is the only available ground truth. |

**PROBE PENDING — plan approval, load-bearing.** The plan-approval flow in
section 9.2 is taken from the documentation, not from a probe. Test it before
stage 5: spawn a teammate requiring plan approval, confirm the request reaches
the project lead, and confirm the project lead can reject it with feedback and
have the teammate revise. Run this probe from an interactive session. `claude
-p` cannot spawn a teammate. A subagent cannot run this probe either. Only an
interactive project lead can spawn one.

Until the probe runs, `crew:ic` is written against the fallback. The IC writes
its plan into the record and waits for the project lead's go-ahead by message,
instead of using native plan approval. If the probe later shows native plan
approval works, swapping to it is a small, localized change.

**RESOLVED — the fork-vs-inform question no longer applies.** Section 3.1
originally needed a canonical *skill* to run in the IC's own context rather
than fork to a subagent. `writing-standard.md` is a plain reference file
instead, read with the IC's own `Read` tool, so there is no invocation to
fork and nothing left to probe here.

---

## 13. Build order

Staged so each stage is independently useful and independently abandonable.

| # | Deliverable | Done when |
|---|---|---|
| 0 | Write crew's own `writing-standard.md` (open question 6) | Crew's own prompts have one standard to be written against |
| 1 | Plugin skeleton, record format, band rubric, IC contract reference | Later stages agree on a format |
| 2 | `crew:ic` + `crew:ic-instructions` + `crew:package-reviewer`, driven by hand | One package of each kind reaches a reviewed, accepted result with zero prompts |
| 3 | `crew:split-critic` + `split.md` format | A bad split is caught before dispatch |
| 4 | `crew:deliverable-reviewer` + `/crew:project-lead`, simple path first | One simple goal reaches a draft PR with zero prompts |
| 5 | Full path: worktrees, territories, merges, promotion | One multi-package goal reaches a draft PR with zero prompts — **done 2026-09-01**, over three runs (§15.30, §15.35, §15.36). `SessionEnd` closed the stage on 2026-09-02 (§15.38). |
| 6 | Council + routing + `decisions.md` | An architecture-moving question is resolved and audited without a prompt — routing and `decisions.md` **done 2026-08-31** (T4); `crew:council-advocate` and the council procedure **done 2026-09-02** (§15.41), and a run convened one the same day (§15.47) |

### 13.1 Hooks

`crew` ships its own `hooks/hooks.json`, the way `auto-approve` and
`session-memory` do. The restriction found in section 12 is on **agent
frontmatter** `hooks`, which is ignored for teammates and banned for plugin
agents. A plugin's own hook file has no such limit.

Plugin hooks are active in every session, so the deciding question for each one
is how often it fires when no crew run is happening.

| Hook | Fires | Job | Stage |
|---|---|---|---|
| `TeammateIdle` | only when a teammate goes idle — never in a session with no teammates | Was to exit 2 and reject an IC that idles with no report | **cut** — the project lead does this by message (below, §15.29) |
| `SessionEnd` | once per session; it exits at once on a machine with no `crew/` directory, and on one that has it, reads a few small JSON files and returns | **Writes only.** Marks the run interrupted in `state.json` and lists its worktrees as orphaned. Deletes nothing. | **built** — `hooks/session-end.py` (§15.38) |
| `PreCompact` | once per compaction, in any session; same guard and cost as `SessionEnd` | **Writes only.** Appends the session id and trigger to `run.compactions` when the session belongs to a live run, so the project lead learns that an IC lost the context it planned in (§15.50). | **built** — `hooks/pre-compact.py`; not yet observed firing for an in-process teammate (T19) |
| `PreToolUse` on `Bash` | **every Bash call in every session** | Auto-prefix `cd <worktree> &&` to kill the cwd hazard — non-git commands only; a `cd` before git is denied (§15 item 23b) | **deferred** |
| `PreToolUse` on `Agent` | every agent spawn | Provision a worktree at spawn time | **not needed** — the project lead does this itself |

The `Bash` hook is the only one with a real cost, and it is the one deferred.
Its value is also the most replaceable: the project lead already detects
worktree drift when it verifies each IC against `git -C <worktree> log`
(section 7). Revisit it once an IC is actually observed wandering.

**No hook ever deletes a worktree.** Three reasons, any one of which is enough:

1. **Path patterns are not ownership.** Manual worktrees live in
   `.claude/worktrees/` too, alongside crew's, and several sessions may hold live
   workspaces there at once. A hook keyed on a directory would delete another
   session's work. Only `worktrees.json`, matched to the run's own session id, is
   proof of ownership — and a hook firing on an unrelated session has no run to
   match against.
2. **A hook cannot ask.** A refused removal means files exist nowhere else
   (section 9.4). `SessionEnd` cannot surface that choice, so it can only force
   and destroy silently, or skip. Neither is acceptable in a hook that runs in
   every session.
3. **`SessionEnd` must be fast** or it blocks session shutdown. Removing several
   worktrees is not fast.

So `SessionEnd` records and never destroys. Marking the run interrupted is the
part that carries real value: without it, a resume cannot tell a live run from a
dead one.

Removal happens where an agent can reason about it and you can see it: on
`/crew:project-lead --resume`, which prunes the orphaned worktrees this run
registered, and never forces.

**`TeammateIdle` is cut. The project lead nudges by message instead.** The hook
was to exit 2 when an IC idles with no report, and push it back to work. T5
probed the mechanism and it does work (§15.29), but the same probe and its
audit priced it, and it does not pay.

What the hook was worth: one saved dispatch. §7 already catches an IC that
idles with no report, because the project lead verifies every IC's claim
against `git` and the report file before it accepts a package. The hook only
changed who fixes the miss — the IC in place, instead of a fix round.

What it cost: a blocking hook that fires for every teammate on the machine,
five guard rules, a refusal counter that needed a new file in the record with
its own lifecycle, a payload whose published documentation is already wrong for
this event, and a deprecated field in that payload. Crew has never observed the
failure it prevents.

And the risk was the wrong shape. The harness stops a refusal loop only after
several *consecutive* blocks, and any tool call resets that count (§15.29). So
a working IC can be refused forever, and the only thing standing between a bug
in crew's counter and a teammate stuck in a loop was crew's own cap. That is a
poor trade for a saved dispatch.

The replacement is one message. A project lead that sees an IC idle with no
report sends it one: what is missing, and where to write it. **Probed
2026-08-31:** a teammate replied `FIRST` and went idle, its project lead sent
`SendMessage`, and the teammate re-engaged and replied `SECOND` 1.5 seconds
later, with its context intact. Same one-turn save, no hook, no marker, and
nothing that fires in a session crew is not running. §7 owns the check; §9.2
owns the nudge that follows it.

`SessionEnd` is unaffected and shipped in stage 5. Nothing else marks a
dead run, so it never depended on `TeammateIdle`.

---

## 14. Deviations from superpowers

Copied as-is, so it stays easy to re-sync: the `Interfaces` block, the
`Global Constraints` block, task right-sizing, the no-placeholders list, the
verification table, the adjudication procedure, the worktree cleanup guard,
and the debugging checklist in section 9.5.

The debugging checklist comes from `superpowers:systematic-debugging` at
plugin version 6.3.0, commit `b36e0829c6d0140e93cfef2ca599b1b07d4a7797`.
Re-sync against that file, not against a paraphrase of it.

Deliberately different:

| superpowers | crew | Why |
|---|---|---|
| Every stage stops for human approval; brainstorming has a hard gate | No gates. The project lead self-approves and records the decision. | The gates are the problem being removed |
| The spec review gate is the human's | The crew-owned spec critic plus the council are the review | Independence without a stop |
| `writing-plans` offers an execution choice | The project lead picks the shape itself (section 9.1) | No prompt |
| `finishing-a-development-branch` presents a 3-option integration menu | Hardcoded to push and open a **draft** PR | Not autonomous merging; not a menu either |
| No cost policy beyond "promote on fix rounds 4-5" | Per-package bands, a rubric, promotion logging, a spend ceiling | Section 8 is a primary motive |
| SDD keeps a progress ledger | A record with an assumption trail, per-package state, and resume | Autonomy is only acceptable if auditable |
| Subagents throughout | Teammates for ICs, subagents for everything one-shot | Steering and attach |
| One plan, one branch | Goal → deliverables → packages | A goal too large for one PR |
| One worker per task | One IC per territory, several packages each | Agent-team guidance; fewer spawns |
| `systematic-debugging` Phase 3: one debugger forms one hypothesis at a time | More than one surviving hypothesis goes to a three-advocate council over one shared evidence set (section 9.5) | Several agents and one judge; assigned positions beat one agent's prior |
| `systematic-debugging` Phase 4.5: after 3 failed fixes, "discuss with your human partner" | The fix-round breaker at five rounds, then escalation trigger 6 (sections 9.2, 6) | A later stop, reached by a rule instead of a conversation. Rounds 4 and 5 promote a band, which is crew's answer to "question the architecture" |
| `systematic-debugging` Phase 4 invokes the TDD and verification skills | Section 7 and `ic-contract.md` carry the equivalents | crew never invokes a superpowers skill (section 2) |
| `systematic-debugging` reads its human partner's wording for signs it is off track | The record: the evidence paths, the ruled-out list, and the council entry (section 9.5) | Nobody is watching a no-prompt run |
| Every superpowers workflow ends in a change | An investigation run can end at `diagnosis.md` with no change, as `work-complete` | A diagnosis is a deliverable |

---

## 15. Open questions

1. **Plugin name.** `crew`, with `/crew:project-lead` as the entry point.
   Rename now if another name reads better; it is cheap today and annoying
   later.
2. **Resolved: the spec critic is crew-owned.** `crew` is now distributed alone, which
   forces the decision the earlier draft deferred: the spec critic cannot
   depend on another plugin's agent. Stage 3, which builds the split critic,
   must also supply a crew-owned spec critic — its own agent definition,
   reviewing the spec on crew's own terms, with no dependency outside this
   plugin.

   Built 2026-08-30 (T2): `agents/spec-critic.md`, unnamed, opus at high
   effort, seven checks against the charter, no dependency outside crew. It
   reports and never edits, and its review lands at
   `reviews/spec-critic-r<n>.md`. Nothing dispatches it until stage 4.
3. **The spend ceiling value.** Unknowable until the first runs produce
   cost-per-package data. Start deliberately low and raise it.

   Decided 2026-08-31 (T4): the default is 2,000,000 tokens, set by
   `SKILL.md` step 1 when the principal names no ceiling. It is a
   placeholder chosen low on purpose, not a measurement. Raise it from the
   first runs' `spend.by_agent` totals.
4. **Whether the shared task list earns its launch flag.** It brings dependency
   blocking, at the cost of tool definitions in every agent's context. Measure
   once stage 5 runs.
5. **Territory count.** Guidance says 3-5 workers. Whether that holds for a
   repo this small is untested.
6. **How general crew's writing standard needs to be.** Resolved:
   `writing-standard.md` is crew's own, written directly for the container
   types this plugin's IC owns (five as of T10, §15.17) — the
   container-routing table, the reader-context section, the frontmatter
   block, the revise-down rule, and the final checklist. It is not split
   from, or a pointer into, any other repo's internal standard. `crew` keeps
   no copy of anything external and carries no repo-specific layer to strip
   out, so it can ship and sync on its own.
7. **Is a "parked" package ever recoverable?** §9.2's breaker (line 601-602)
   gives three outcomes — fix, park with recorded reasoning, or defer — but
   §10 (line 655-656) maps only "defer" to `abandoned` and calls `abandoned`
   terminal and never revived. Nothing says what state a "parked" package
   holds or whether it can later resume. If park also means `abandoned`, the
   state set needs no change; if a parked package can later resume, the state
   set needs a fourth, non-terminal value, and §10's transitions need it too.

   Decided 2026-08-29: park is `abandoned`. Park and defer land in the same
   state and differ only in the recorded reasoning. The state set does not
   change, and reviving parked work is what §10 already prescribes: a new
   package.
8. **The plan gate collides with the idle hook.** Every IC must stop and wait
   after writing its plan (§9.2 step 3), but the `TeammateIdle` check must
   find a *report* on disk before it lets an IC idle, not a plan (§13.1's
   report-on-disk rule; `record-format.md` lines 36-37). The two collide by
   construction. The hook is stage 5, and was unprobed when this item opened
   (probed 2026-08-31, §15.29), so neither file could resolve this alone;
   `ic-contract.md` only names the post-plan wait as an expected pause, not an
   idle to fix.

   Decided 2026-08-29: the record carries the gate. `record-format.md` adds
   `plan_approved_at` per package, `null` until the project lead's
   go-ahead. The idle check lets an idle pass while
   `plans/<id>.md` exists and `plan_approved_at` is `null`. The collision
   dissolves: a post-plan wait is visible in the record, not inferred.

   Still true after the hook was cut (§15.29): the check now runs in the
   project lead, which reads the same two record fields before it nudges an
   idle IC. The gate moved; the fields it reads did not.
9. **`decisions.md` needs a `Models:` line for councils.** §6.1 requires
   recording which model a council used (lines 373-374), and council spend
   is logged (lines 376-377) with its field, `spend.council_tokens`, defined
   in `record-format.md` (lines 161, 187, 427). Today the model is recorded
   as free text inside the entry. `decisions.md` is
   already a labelled-line format, so the fix is one more labelled line —
   this belongs in stage 6, when councils exist and advocate-spend
   attribution is known. Do not add this field to `band-rubric.md` ahead of
   that; an unowned field name there would be the exact class of mismatch
   this document works to avoid.

   Decided 2026-09-02 (T8): `record-format.md` owns the field, in a new
   council-entry shape. A council entry carries four extra lines, not one —
   `Positions`, `Losing`, `Models` and `Spend`. `Models` is one value, not one
   per advocate, because every advocate in one council runs the same model.
   `band-rubric.md` names the line and points at the file that defines it.
10. **§12's "the workaround holds" row does not hold when the driving
    session is itself worktree-isolated.** Task 10's stage-2 run dispatched
    `crew:ic` from a headless `claude -p` session launched from inside this
    repo's own worktree-isolated checkout. Every `git` command that named
    another worktree — `git -C <path>`, a literal `cd <path> && git ...`,
    and `--git-dir`/`--work-tree` — was refused outright by the harness,
    independent of `--permission-mode` and of `dangerouslyDisableSandbox`.
    This blocked the exact operation §7's verification table requires
    (`git -C <worktree> log` and `diff`, line 498) and the exact operation
    §12's own row claims works ("a teammate can work, write, and commit
    there with no guard", line 731). That row's probe must have run from a
    session that was not itself worktree-isolated. Stage 5's full path
    (separate IC worktrees, §9.2) could not be exercised at all in this
    run for that reason; only the simple path (§9.1, one package on the
    current branch, no separate worktree) could be driven end to end. Any
    project lead session that itself runs inside a worktree — which is exactly how
    this project's own sessions are normally launched — needs a different
    verification mechanism than `git -C <ic-worktree>`, or needs to run
    unisolated.
11. **`--add-dir` widens file access but not `git commit`, and the two are
    separate failures.** Widening a headless IC's allowed directories with
    `--add-dir <worktree> --add-dir <record-root>` let `Read`/`Write`/`Edit`
    succeed against an assigned worktree outside the launch directory —
    confirmed by a modified test file actually landing on disk. It did not
    help the `git commit` failure in finding 12 below; that denial persists
    with or without `--add-dir`. A future project lead cannot treat these as one
    problem with one fix.
12. **`--permission-mode acceptEdits` does not cover `git commit` in
    headless mode, so no IC dispatch can commit its own work.** Both packages
    in this run reproduced this independently: `git status`, `git log`, `git
    diff`, and `git add` all ran; every `git commit` form — plain, `-m`,
    heredoc-quoted, with `dangerouslyDisableSandbox: true` — returned a denial
    with no human present to approve it. The literal acceptance command
    (`python`, as opposed to `python3`) hit the same denial pattern for one
    package. This means `ic-contract.md`'s Commit discipline ("Commit after
    every green step", line 66-70) cannot execute at all under this exact
    dispatch shape — not a corner case, the normal case. Both ICs behaved
    correctly: they did not fabricate a commit, did not retry indefinitely,
    and reported the block precisely (`BLOCKED` and `DONE_WITH_CONCERNS`). The
    project lead, played by hand, verified each staged diff against its brief
    and reviewer verdict and committed it directly — which is consistent with
    the project lead already owning integration commits (§9.3), but §9.2 step
    4 assumes the *IC* commits, and nothing in the design currently says the
    project lead must be ready to commit on an IC's behalf as the normal path
    rather than the exception.
13. **`ic-contract.md` has no branch for "I cannot write my report."** The
    first, full-path attempt at the code package (before this run pivoted
    to the simple path — see finding 10) hit a session whose sandbox
    permitted no writes at all into either the assigned worktree or the
    record root. The contract's own words are "Never go idle with no
    report on disk" (line 93-95), but this IC had no writable path to any
    disk location the contract names. It behaved correctly — it returned
    its full diagnosis as its final output instead of fabricating a file or
    silently stopping — but the contract does not anticipate this state.
    Recommend a documented fallback: when the record root is confirmed
    unwritable, the IC's final message *is* the report, and it must say so
    explicitly. Without this, §13.1's planned `TeammateIdle` hook — which
    checked for a report file on disk, not a message — would have rejected
    such an IC's idle forever, with no way for it to comply. The hook is now
    cut (§15.29), which removes the trap but not the need for the fallback:
    the project lead applies the same file check by hand (§7).
14. **No IC used `SendMessage` to reach a live project lead, and one attempt named
    a target that does not exist.** Design §6.2 gives an IC exactly one
    escalation path: "`SendMessage` the project lead... ICs never escalate to
    the human" (lines 427-429, 433). In this run's dispatch shape — a headless
    `claude -p` invocation using the `Agent` tool to spawn `crew:ic` or
    `crew:ic-instructions`, named or unnamed — neither IC had a reachable
    project lead to message. One tried `SendMessage` to an agent literally
    named `"project lead"` and got `No agent named "project lead" is
    reachable`; the other concluded up front that no `to` target existed for a
    live project lead session and skipped the attempt entirely, stating that
    assumption in its report instead. Both ICs then correctly wrote their
    concern into the report rather than stalling. This does not by itself
    disprove §6.2's mechanism for a genuinely interactive, long-lived project
    lead session (stage 4's actual build), but it means the mechanism has not
    been shown to work in any shape tested so far, and the fallback behavior
    it forces — write the concern into the report and proceed — is worth
    keeping as the documented default regardless of whether `SendMessage` ever
    works.
15. **A denied literal command can have a working substitute, and that is
    easy to miss.** One package's acceptance criterion named `python`
    literally; that exact invocation was denied in the headless session,
    while `python3` against the identical script ran and produced identical
    output. The IC noticed, named the substitution as an assumption, and
    the reviewer independently re-ran both forms to confirm they were
    behavior-identical before accepting. An IC that treated the one
    successful form as proof of general capability, without flagging the
    substitution, would have been trusting an environment quirk rather
    than its actual acceptance criterion.
16. **The dispatch mechanism's real cost is wall-clock opacity, not just
    token spend.** Driving one code package and one instruction package
    through plan → implement → report → review → lead-commit took eight
    separate headless `claude -p` invocations (one mechanism probe, two
    code-IC attempts, one code-package review, one chained
    instruction-IC-plus-review run, plus the retries the cwd-hazard and
    permission findings above forced) over roughly 45-50 minutes of wall
    clock. Every invocation had to be waited on from outside the session,
    because a headless `-p` process reports nothing until it exits — no
    partial progress, no indication of which step it is on. Stage 4 builds
    an autonomous loop directly on top of this primitive; its cost and
    timeout model needs to budget for that opacity per dispatch, not only
    for the token totals design §8 already tracks.
17. **A README is not one of `crew:ic-instructions`'s four container
    types.** §3.1 gives that specialist exactly four containers:
    `CLAUDE.md`, a `.claude/rules/` file, a `SKILL.md`, and an agent
    definition. Task 10 dispatched it on `plugins/crew/README.md` anyway,
    to dogfood the specialist, and its own package review flagged the
    mismatch: the README passed the acceptance checklist on the merits,
    but the checklist's container-choice item did not apply to it. Either
    the specialist's container list should grow to include a README and
    other reader-facing prose, or a README needs a different owner. This
    document does not decide which.

    **Decided 2026-09-02 by council** (§15.43), in the two halves the council
    forced:

    - **A README, and any reader-facing file that is a deliverable in its own
      right, goes to `crew:ic-instructions` as a fifth container type.** §3.1's
      own rule decides it: split an IC when the definition of done changes, not
      when the subject changes. The definition of done does not change — a
      written checklist verified by a reviewer, either way. One checklist item
      is skipped and the prose rules invert, and `writing-standard.md` already
      carries both branches in one file.
    - **A PR body, an issue and a comment stay with the project lead.** They
      are written after every package merges, out of `spec.md` and
      `decisions.md`, so they have no sibling to be disjoint from and nothing
      downstream consumes them. §5's dispatchability invariants cannot be met
      by them, and §9.3 already has the project lead write the PR body.

    T10 still owns the file alignment this implies, and one sub-question the
    council raised: a specialist named `ic-instructions` whose container list
    now includes non-instructions may need a different name.

    **Decided: the name stays.** T10 aligned §3.1, `agents/ic-instructions.md`
    and `writing-standard.md`'s README note with the council's decision above.
    A rename touches every dispatch pointer to `crew:ic-instructions`, and the
    name still fits four of the five containers. **This item is Decided.**
18. **Should an environmental block and a capability block get the same
    `BLOCKED` response?** `ic-contract.md`'s `BLOCKED` row directs the project
    lead to promote the package one band up, or stop the run at a breaker.
    Item 12 above is an environmental block — no human present to approve a
    `git commit` — not a capability gap, and promoting a band over it spends
    money climbing toward `deep` before any breaker fires. The run's own
    project lead deviated from that mandated response and committed the
    package on the IC's behalf instead of promoting it. Whether the `BLOCKED`
    row should split into an environmental case and a capability case is a
    design decision above this fix wave; this item does not decide it.

    Decided 2026-08-29: the causes split. A `BLOCKED` report names its
    cause, `capability` or `environment`. Capability promotes
    (`band-rubric.md`). Environment never does — the project lead fixes the
    environment or performs the blocked action itself, and item 23's
    pre-approval rules make that case rare. `ic-contract.md` and
    `band-rubric.md` carry the split.
19. **`lead` is reserved for a tier that does not exist yet.** Decided: the
    hierarchy is **lead → project leads → ICs**. What this plugin builds is a
    **project lead**. `lead` names the tier above it, which delegates to
    project leads and stays out of scope here (§1).

    Done: prose across this plugin says "project lead" throughout (184
    renamed uses), the entry point is `/crew:project-lead`, and its files
    moved to `skills/project-lead/`. The bare word `lead` now appears only
    where it means the tier above. `docs/implementation-plan.md`,
    `docs/stage-2-run/` and `docs/pr-body.md` keep the old wording — they are
    the frozen record of a run that happened under it.
20. **The agent-teams docs contradict five rows of §12, and settle two probes.**
    Read against `code.claude.com/docs/en/agent-teams` and `.../sub-agents`
    (fetched 2026-08-29, docs current to ~v2.1.234). §12's rows were probed
    2026-08-24 and some describe behaviour that has since changed or was
    never quite right. Corrections, each of which changes a design decision:

    a. **Teammates are gated on an experimental flag.** Agent teams are off
       by default and need `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` in
       settings `env` or the environment. With it unset, naming an agent does
       *not* produce a teammate — it launches an ordinary subagent. §3's
       naming rule ("a named agent becomes a teammate") therefore holds only
       when the flag is on, and nothing in this plugin currently checks it.

    b. **A teammate's output does reach the project lead.** §12 says it
       "never returns to the dispatcher". The docs say a teammate that
       finishes and goes idle "automatically notifies the lead and includes
       its final answer in the notification". It is not a parseable tool
       result, so the record is still the durable channel — but the stated
       reason for writing reports is wrong, and §3's naming rule rests on it.

    c. **Display mode needs no setup.** §12 requires iTerm2 + `it2`, tmux, or
       an explicit `teammateMode`. Since v2.1.179 the default is
       `in-process`, which works in any terminal. Split panes are the
       optional upgrade, and are unsupported in VS Code's terminal, Windows
       Terminal and Ghostty.

    d. **An agent definition means different things by display mode.** For an
       in-process teammate the definition's body is *appended* to the default
       system prompt; for a split-pane teammate it *replaces* it. A
       split-pane teammate also ignores the definition's `model`, and neither
       mode applies its `skills`. `crew:ic` is written as a whole system
       prompt, so it is a different agent in the two modes.

    e. **`CLAUDE_CODE_SUBAGENT_MODEL` outranks a spawn-time model.** The
       order is that variable, then the spawn prompt, then (in-process only)
       the definition's `model`, then the lead's model. Set to anything but
       `inherit` it silently flattens every band in §8.

    Two `PROBE PENDING` entries in §12 are now answered. **`TeammateIdle`
    exit 2 works** — the hook "runs when a teammate is about to go idle. Exit
    with code 2 to send feedback and keep the teammate working" — so §13.1's
    mechanism stands. §15.29 later probed it and found the block bounded: it
    holds for a number of refusals, then lets the teammate idle. **Native plan
    approval is not a review gate**: a
    teammate's plan request is approved in the lead's session "as soon as the
    request arrives, without the lead reviewing it". §9.2 step 3's fallback —
    plan to the record, wait for a message — is therefore the *only* way to
    get a reviewed plan gate, not a stopgap. Do not swap to native approval.

    Also newly relevant and not recorded anywhere: teammate permission
    prompts surface in the lead's session for a human to approve, which is
    the mechanism behind item 12's `git commit` denials; `/resume` does not
    restore in-process teammates, which §10.1 recovery must assume; and
    subagents nest three layers deep by default while teammates cannot nest
    at all (§15.21).
21. **A three-tier hierarchy cannot be nested teams. Decided: every tier
    boundary is a session boundary.** Teammates cannot spawn teammates ("no
    nested teams"), the lead is fixed for a session's lifetime, and a
    session has exactly one team. So project leads cannot be teammates of a
    lead *and* have IC teammates of their own. Worse, an in-process
    teammate's subagents are forced to the foreground, so a project-lead
    teammate could only run one IC at a time — which removes the
    parallelism §5 exists to provide. (Whether a split-pane teammate is
    likewise forced is not stated in the docs; unprobed.)

    Decided 2026-08-29: the hierarchy is one interactive session per
    project lead. The future lead is a session. Each project lead is its
    own session — exactly the thing this plugin already builds. ICs are
    that session's teammates on the full path, or its subagents on the
    simple path (§9.1). No file in this plugin changes shape for this;
    the decision is that none has to. Two alternatives were rejected:

    - **An all-subagent tree.** Subagents nest three deep by default
      (`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`), so the shape fits the
      platform. But a subagent holds no conversation, and the working
      pattern this hierarchy serves splits the human's attention across
      tiers — most on the lead, some on project leads, a little on ICs.
      A project-lead subagent forecloses that middle share, and §9.1's
      own rule — mechanism follows the need for a conversation — already
      names the reason.
    - **A workflow script.** The documented pattern for large parallel
      fan-out, but the script decides what runs, not a conversation. The
      same §9.1 rule puts every tier above the ICs out of its reach.

    The channel between a lead and its project leads exists now:
    cross-session messaging (`code.claude.com/docs/en/cross-session-messaging`,
    v2.1.224+, fetched 2026-08-29). Local sessions on one machine discover
    each other with `ListAgents` and message each other with `SendMessage`,
    over per-session sockets. §12 predates this capability and does not
    record it. The durable interface between tiers stays the record (§4):
    a lost message costs latency, never correctness — the same rule that
    already governs project-lead-to-IC messages, applied one tier up.
22. **What stage 4 must build so a lead tier can attach later.** The lead
    tier stays out of scope (§1), and building it before the project-lead
    loop exists would stack a new tier on a stub. But the project lead is
    the tier a future lead will drive, so its entry points are the
    interface. Three requirements, each cheap now and expensive to
    retrofit:

    a. **Accept a written charter, not only a goal string.**
       `/crew:project-lead <goal>` covers a human's hand-off. A lead hands
       off a charter it already wrote. Stage 4's skill takes either form:
       a goal string it expands into `charter.md`, or a path to a charter
       file it adopts as `charter.md` unchanged.

    b. **Escalate to the principal, not to "the human".** The escalation
       ladder is already tier-recursive: an IC escalates to its project
       lead, which answers what it can and escalates the rest upward
       (§6.2). Generalize the top rung: a project lead escalates to
       whoever handed it the goal — today the human in its session, later
       the lead by cross-session message. Stage 6's escalation format must
       not hard-code the human as the only principal.

    c. **A project-lead session must be spawnable by rule.** It runs
       interactive, because `claude -p` cannot spawn teammates (§12). It
       launches outside any worktree, or §15.10's refusals block IC
       verification. Its permissions are pre-approved, or the first prompt
       stalls a session nobody watches (§15.20, item 12) — item 23 gives
       the verified mechanism. A human obeys these three rules by hand
       today; a lead automates the same three rules later, for example
       with `tmux new-window 'claude ...'`.

    Until a lead exists, the human is the lead: they hold the portfolio,
    write or approve charters, and answer escalations. That is the target
    division of attention already, minus the automation.
23. **Items 10-12 dissolve under the right idiom and allow rules — probed.**
    Probed 2026-08-29 on Claude Code 2.1.251: nested headless `claude -p`
    dispatches in a linux container, against a scratch repo with a linked
    worktree, each result verified with `git log` rather than the inner
    model's claim. Cross-checked against `permissions.md`,
    `permission-modes.md`, `worktrees.md`, and `hooks-guide.md` (fetched
    the same day). Six findings:

    a. **Item 12's commit denial is a missing allow rule, not a wall.**
       `acceptEdits` auto-approves only file edits plus `mkdir`, `touch`,
       `rm`, `rmdir`, `mv`, `cp`, `sed` — never `git commit`. Headless, a
       call that would prompt is denied instead. With one rule —
       `--allowedTools "Bash(git commit:*)"` — the probe committed.
    b. **A cd-before-git guard denies every `cd <path> && git ...`
       headless, allow rules or not** — including read-only
       `cd <wt> && git status` under broad `Bash(cd:*)` plus `Bash(git:*)`
       rules. The denial text names the reason: a `cd` before git can
       execute untrusted hooks from the target directory. This made the
       old worktree rule — every command carries `cd <worktree> &&` —
       unrunnable unattended for git. `ic-contract.md` now splits the
       idiom: `git -C <worktree>` for git, the `cd` prefix for everything
       else. Compound non-git commands are safe: the matcher splits on
       shell operators and checks each part against its own rule.
    c. **A path-scoped rule is the sanctioned pre-approval.**
       `--allowedTools "Bash(git -C <worktree> *)"` — the exact worktree
       path, wildcard after — let the probe commit into that worktree on
       its branch, unattended. A wildcard before the subcommand
       (`Bash(git -C * commit *)`) also matched but draws a startup
       warning naming `-c`/`--exec-path` injection. So a dispatch can
       grant one IC git rights over exactly its own worktree.
    d. **Headless `-p` does not load the project's `.claude/settings.json`**
       (untrusted workspace). User settings, managed settings,
       `--settings`, and `--allowedTools` still apply. An interactive
       session — stage 4-5's shape, teammate prompts included — honors
       repo settings. So pre-approval travels with the spawn: per-dispatch
       `--allowedTools` for a headless IC, repo settings for a run inside
       an interactive project-lead session.
    e. **Item 11 confirmed from the docs side.** `--add-dir` widens file
       tools and the file commands Claude Code recognizes (`cat`, `head`,
       `tail`, `sed`). Git is an arbitrary subprocess, outside that
       system. The two failures are two systems, as item 11 suspected.
    f. **Item 10 narrows to isolation, not location.** The docs document
       git isolation for sessions in Claude Code's own worktree isolation:
       no `git -C`, `--git-dir`, `GIT_DIR`/`GIT_WORK_TREE`, or cd-into
       reaching the main checkout or siblings. A plain session whose cwd
       merely sits in a linked worktree is not in that state: the probe
       read and committed into the sibling checkout under a broad allow
       rule. Item 22c's launch rule — unisolated — stands and is
       sufficient.

    Two limits on these probes: the container ran as root, so
    `bypassPermissions` stayed untested — and unwanted anyway; and no
    probe covered an interactive session, where the same guard in (b)
    surfaces as a prompt a human can approve. The zero-prompt goal makes
    the idiom split right regardless.

24. **The deliverable reviewer works from the split, not from the diff
    alone — validated 2026-08-30 (T3).** `agents/deliverable-reviewer.md`
    is built: unnamed, opus at high effort, `Read Glob Grep Bash`. It
    keeps the package reviewer's posture — report never fix, `git -C
    <worktree>` for git, the same two verdict lines — and takes five
    inputs: `spec.md`, `split.md`, the worktree and base ref, the merged
    diff, and the accepted package reviews.

    A hand dispatch over a seeded two-package deliverable found all seven
    planted flaws and split one of them correctly into two: a dropped
    spec criterion, two ends of one broken seam (a keyword argument the
    producer never took, and a dataclass indexed as a dict), a version
    skew across two project-lead-owned shared files, an edit to a file
    the global constraints put out of scope, a stray scratch file, the
    merged suite failing, and a debug print. It returned `Verdict: fix
    round needed` with a critical count. The dispatch was repeated
    against the corrected agent body after review, over the same seeded
    deliverable, and returned the same seven criticals and the same
    verdict.

    What the run showed: four of the seven checks read the record, not
    the diff. Spec coverage needs `spec.md`. The seam check reads the
    `Produces`/`Consumes` pair at both ends in `split.md`. The
    shared-file check needs the split's list of project-lead-owned
    files, and the scope-leak check subtracts the union of the
    `file_set`s plus that list from the diff's file list. Only three
    findings were reachable from the diff alone: the debug print, the
    failing suite, and the stray scratch file — and the scratch file
    only through the PR-readiness check, not the scope-leak check that
    reported it. So the project lead sends the record with the diff.

    Both ICs reported their acceptance test passing, and both were
    telling the truth — each suite was written against a different idea
    of `load_config`. Only the merged run exposed it. That is the case
    §9.3's per-merge test run exists for, and the reason this reviewer
    re-runs the suite itself instead of reading the package reviews.

    A third dispatch measured the other direction: the same deliverable
    with every seeded flaw repaired. It returned `Verdict: accepted` and
    a critical count of zero, so the seven checks do not invent a
    blocker. It still reported one `[Concern]` — the consuming package
    never handles the error the producing package's contract says it
    raises, so a missing file exits the cli with a traceback. Each end
    is correct alone, which is why neither package reviewer could see
    it. That is the class of defect this reviewer exists for.

    The first attempt at that clean run did not come back accepted, and
    the reason is worth keeping: the repaired deliverable carried a
    test that asserted nothing. It set the environment variable, called
    the entry point, and checked only the return code, which was the
    same either way. The reviewer called it `[Critical]` against the
    spec criterion the test claimed to prove. A criterion is met by a
    test that can fail, not by a test that passes — so this reviewer
    reads the test body, and a green suite is not evidence on its own.
    The run also caught that the branch under review was not the branch
    `split.md` names.
25. **The simple path needs three rules the full path does not — built
    2026-08-31 (T4).** `skills/project-lead/SKILL.md` now carries the
    stage-4 loop: charter, scout, spec, spec critic, one package, package
    review, fix rounds, integration, deliverable review, draft PR. Writing
    it forced three decisions the design had not stated.

    a. **The plan gate is two dispatches on the simple path.** §9.2 step 3
       has the IC write its plan and wait for the project lead's go-ahead
       by message. A subagent has no message channel — ending its turn is
       the only wait it can perform. So the first dispatch writes
       `plans/<id>.md` and stops, the project lead reads it and sets
       `plan_approved_at`, and a second dispatch implements it and is told
       to read the plan first. `ic-contract.md`'s plan gate carries this
       branch. The full path keeps the message form, because a teammate
       does have the channel.

    b. **The simple path still writes `split.md`, and still runs the
       deliverable reviewer.** §9.1 skips the critic, the merge and the
       cleanup, but item 24 showed four of the deliverable reviewer's
       seven checks read `split.md` and `spec.md` rather than the diff.
       The project lead also edits the shared files itself at integration
       (§9.3), and no package reviewer ever sees those edits. So one
       package is not a reason to skip either one.

    c. **Two caps the design left open.** A spec that keeps failing its
       critic loops forever, so `SKILL.md` caps re-specs at three and then
       escalates. Fix rounds already had §9.2's cap of five. Neither cap is
       measured; both are placeholders, like the spend ceiling in item 3.

    A code review over the finished loop then found eight defects a
    reading of the design had missed, and every one was a control-flow gap
    rather than a wrong rule: the bounded-edit route skipped the branch it
    then tried to push; the deliverable never passed through `in-flight`,
    so every simple-path record was invalid against its own state machine;
    the deliverable reviewer got the pre-integration diff, which omits the
    shared-file edits its check 3 exists to read; the fix-round loop had no
    return edge and no exit; the package reviewer got one of the five
    inputs its own definition demands; the plan gate read a file that
    item 26b says is usually never written; and the spend rule said to
    write `measured: true` for a number that item 26d says never arrives.
    All eight are fixed. The lesson worth keeping: a loop written as prose
    hides a missing edge the way a diagram does not, and the checks that
    caught these were "follow the arrow and see where it lands", not "is
    this rule right".

    A fourth decision was not needed: routing, the escalation triggers and
    spend counting moved into a fifth reference,
    `skills/project-lead/references/autonomy-contract.md`, because
    `SKILL.md` would otherwise pass the writing standard's 200-line limit.
    That file owns §6 and §8's spend rules; nothing else copies them.
26. **The first simple-path run: four environment findings and one
    contract that held — 2026-08-31 (T4).** `/crew:project-lead`'s simple
    path was exercised end to end by hand, on a real backlog goal (T13's
    researcher agent), driving every agent through nested headless
    `claude -p` dispatches. The run reached a draft PR. Five agent
    dispatches, one re-dispatch, zero fix rounds, zero escalations.

    a. **A dispatch must carry the record root, and reading it is a
       separate grant from writing it.** The record lives at
       `~/.claude/crew/<goal-slug>/`, outside the launch directory, so
       the first `crew:spec-critic` dispatch could not read its own
       inputs and correctly refused to review — "Cannot verify from spec"
       against all eight checks, rather than a guess. `--add-dir
       <record-root>` fixed the reads. It did not fix the writes.

    b. **An IC cannot write into the record root at all under `~/.claude`.**
       Both IC dispatches were denied every write to `plans/` and
       `reports/`, with `--permission-mode acceptEdits`, with
       `--allowedTools Write`, with `--add-dir`, and with the sandbox
       override. The second denial named its reason: the path is treated
       as a **sensitive file**, because it sits under a dotfile directory
       in the user's home. This is not item 11's `--add-dir` gap and not
       item 12's `git commit` gap — it is a third, separate mechanism, and
       no allow rule tested here defeats it. Design §4 puts the record
       outside the target repo on purpose, so the two requirements
       collide. Whoever builds T6 must either find the grant that covers
       a sensitive path, or move the record somewhere that is not one.

    c. **`ic-contract.md`'s denied-record-root fallback earned its
       place.** Written for item 13, it was used twice in one run, by two
       fresh ICs with no shared context. Each returned its plan or report
       as its final message, said so in the first line, and named the
       denied path. Neither fabricated a file and neither stopped
       silently. The project lead transcribed both into the record and
       verified the report's git claims before any review ran. A design
       branch written for a case that had happened once is now a branch
       that carries the normal case in this environment.

    d. **Spend cannot be measured through a nested headless dispatch.**
       Design §8 reads `total_tokens` off each subagent's completion
       notification. A nested `claude -p` process returns only its final
       text, so not one of the five agents reported a number, and
       `state.json` marks every one unmeasured. §8 assumes the project
       lead spawns its subagents directly — true for the real interactive
       shape, false for every probe run so far. The ceiling has never
       actually been exercised.

    What the run also showed, on the loop rather than the environment:
    the plan gate works as two dispatches; the deliverable reviewer found
    three project-lead-owned files stale that no package reviewer could
    have seen (`CLAUDE.md`'s agent count, a silent ticket status, a
    README table), which is check 3 doing exactly its job; and the
    adjudication step earned its keep, because one of that reviewer's
    five findings was wrong and was pushed back on with a §12 citation
    rather than fixed.
27. **The researcher's first dispatch, and what it found — 2026-08-31
    (T13).** `crew:researcher` was dispatched unnamed against this repo with
    one question: does `CLAUDE.md`'s "a rule lives in exactly one file" hold
    today? The dispatching session read only the returned brief and did no
    research of its own, which is what T13's "Done when" asks for.

    The brief came back in the required shape: `path:line` citations
    throughout, a stated confidence, and a named list of what it could not
    determine. It reported reading every file under `agents/`, `skills/`,
    `CLAUDE.md` and `README.md` — 2,159 lines — and said so with the command
    that proved the count, rather than claiming coverage bare.

    **The answer is no, and it is worth acting on.** Six rules are stated in
    more than one place, and three have already drifted: the `[Concern]`
    definition splits two ways across the four review agents; the shared-file
    enumeration appears six times and `split-critic.md`'s copy silently
    broadened it with "test helpers, snapshots"; and the "Cannot verify" line
    disagrees on whether it governs a *check* or an *item*. Two of those
    three were spot-checked against the tree and matched exactly, line
    numbers included. T15 carries the fix.

    The sharper finding is structural: the four review agents each hold a
    full copy of one findings convention, and no file in `CLAUDE.md`'s
    Authority list owns it. The rule that forbids a second copy has no
    canonical home for the thing being copied. That is the failure the rule
    exists to prevent, sitting inside the plugin that states the rule.

    Two notes on the agent itself. Its confidence came back `medium-high`,
    which is not one of the three values `agents/researcher.md` requires —
    the definition names `high`, `medium` or `low`, and the brief invented a
    fourth. The agent should reject a value outside its own list. And the
    brief's own unknowns were well chosen: it flagged that it could not tell
    whether `README.md` is meant to be exempt, which is exactly the question
    T10 already holds open.

28. **The review-output convention gets a fifth reference — decided 2026-08-31
    (T15).** Item 27's audit found the four review agents each holding a full
    copy of one findings convention, owned by no file in `CLAUDE.md`'s
    Authority list. `skills/project-lead/references/review-output.md` now owns
    it: the three severity tags, the `Cannot verify` escape, the
    report-never-fix rule, the no-`SendMessage` return path, and the shape of
    the two verdict lines.

    Each agent keeps its own two verdict strings inline — `ready to split`,
    `dispatchable`, `accepted`, and their opposites. Those strings are
    agent-specific, so each is still stated once, and the project lead parses
    them. The failure the reference buys off is drift, which had already
    happened three times.

    The project lead injects the reference **whole** into every review dispatch
    (`SKILL.md` steps 4, 10 and 13), the idiom step 8 already uses for
    `ic-contract.md`. A path was the first design and is wrong: a review agent's
    cwd is the target repo, so a plugin-relative path resolves to nothing on
    every run against a repo other than `crew`, and all four agents would then
    invent their own severity tags under the project lead's `[Critical]` gate.
    `agents/ic-instructions.md`'s path idiom works because its reference is a
    quality standard, not a parsed contract.

    One rule is deliberately stated twice. `crew:package-reviewer` and
    `crew:deliverable-reviewer` hold `Bash`, so each restates "never edit a
    file" in its own body as well. The reference owns the rule; the inline copy
    is a guard on a capability that can change the tree under review. A
    duplicated sentence is the cheaper failure.

    **Verified by dispatch, 2026-08-31.** `crew:spec-critic` was hand-dispatched
    twice against the same fixture — a spec with five seeded flaws — through
    `claude -p --plugin-dir`, with the fixture as cwd so the agent ran outside
    the plugin, the condition a path would have failed in.

    With the reference injected, the agent named every seeded flaw, tagged each
    finding `[Critical]`, `[Concern]` or `[Nit]`, wrote `Cannot verify from the
    checkout` with the source named, and closed with the two verdict lines and
    `Critical count: 4`.

    Without it, the agent said in its first line that its prompt did not carry
    the convention, then improvised: it invented `[Note]` for the third tag and
    tagged a check that passed, which the reference forbids. `[Critical]` and
    `[Concern]` survived, and so did both verdict lines, so the project lead's
    gate still keys on tags that mean what it thinks. That is the predicted
    degradation, measured rather than reasoned. The fix is not a fourth copy of
    the tag list in each agent — that is the drift this item removes. The
    injection is the project lead's job, and `SKILL.md` steps 4, 10 and 13 say
    so.

    The three drifts item 27 named are gone. Two resolved by moving the rule
    into the new reference: the `[Concern]` definition is now
    "likely to cause a problem" everywhere, and the `Cannot verify` line now
    governs a *check* and names the source it lacked. The third was a real
    error, not just a wording split: `split-critic.md` listed "test helpers,
    snapshots" among the shared files, which would have handed the project lead
    files that belong to a package. §5 owns the shared-file list, and check 1
    now cites §5 and says plainly that a test helper two packages both touch is
    a collision inside the split, not a project-lead file.

    Left open on purpose: `agents/researcher.md` accepting `medium-high` as a
    confidence value (item 27's other note). It is not a duplication, so T15
    does not carry it.
29. **`TeammateIdle`: exit 2 blocks the idle, and only the harness's own cap
    ends the loop — probed 2026-08-31 (T5), corrected the same day by an
    audit.** The probe ran on Claude Code 2.1.252, in an
    interactive session inside `tmux` with
    `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. A temporary hook dumped its
    stdin, wrote `crew probe: refusing idle` to stderr, and exited 2. One
    teammate, `probe-bot`, was spawned with one instruction: reply `READY` and
    stop. The registration was removed as soon as the run ended.

    The three questions, answered:

    1. **Exit 2 does block the idle.** `probe-bot` replied `READY`, tried to
       idle, and was re-invoked instead. The hook fired 11 times between
       21:53:53Z and 21:54:20Z.
    2. **The stderr line reaches the teammate, word for word, inside a wrapper
       the harness writes.** The IC receives
       `TeammateIdle hook feedback:` on one line, then
       `[<path to the hook script>]: <the stderr>`. Two consequences: crew's
       stderr need not say a hook is blocking, because the harness already
       said so; and the hook's own script path is shown to the IC. The
       teammate's transcript carries the refusal 11 times, once per firing.
    3. **The payload names the idling teammate.** Every dump carried
       `teammate_name` (`probe-bot`), `team_name` (`session-<parent sid>`),
       `session_id`, `cwd`, `transcript_path`, `permission_mode` and
       `prompt_id`. The fail-open fallback in §13.1 stays as a guard, but the
       scoping rule it protects is buildable as designed: name the teammate,
       find its package, read its report file.

       Two traps in that payload. `team_name` is marked deprecated in the
       2.1.252 schema — key nothing on it. And `transcript_path` names the
       **parent** session's transcript, not the teammate's: the IC's own turns
       live in `<parent transcript dir>/subagents/agent-a<name>-<hash>.jsonl`,
       a path the payload never gives. A hook cannot read the idling IC's
       conversation.

       The published hook documentation is wrong for this event in 2.1.252. It
       lists `agent_type` as the only event-specific field and omits
       `teammate_name`. The observed payload carries no `agent_type`, and the
       binary's schema marks `teammate_name` required. Believe the probe.

    **The finding that changes the design, and the correction that changes it
    again.** The probe saw 11 refusals in 27 seconds and then an idle, and
    concluded the block is bounded. That conclusion was wrong. An audit the
    same day found the mechanism in the 2.1.252 binary: a cap on *consecutive*
    blocks, shared by `Stop`, `SubagentStop`, `TaskCompleted` and
    `TeammateIdle` — `CLAUDE_CODE_STOP_HOOK_BLOCK_CAP??8`, overriding on the
    ninth, counted in `stopHookBlockingCount`, and **reset to zero on any tool
    call**. The observed 11 is 2 blocks, then `probe-bot` made a tool call
    which reset the counter, then 9 more. The refusals speeding up from 6
    seconds to 1 is not a backoff either — `probe-bot`'s replies simply got
    shorter, ending as the bare word `READY.`

    So the block is bounded only for a teammate that does nothing but emit
    text. **A real IC that answers a refusal by running a test or reading a
    file resets the counter every round, and the loop never ends by itself.**
    Nothing in the documentation carries this cap, and an undocumented
    implementation detail can change between versions. Crew must not depend on
    it in either direction.

    **Decided 2026-08-31: the hook is cut.** The probe proved the mechanism
    works and then priced it, and it does not pay. Its whole value was one
    saved dispatch, because §7 already catches an IC that idles with no report.
    Against that: a blocking hook in every session on the machine, five guard
    rules, a refusal counter needing a new record file with its own lifecycle,
    published documentation that is wrong for this event, a deprecated field in
    the payload, and a failure crew has never observed. The cap finding makes
    it worse, not better — with the harness bound gone for any working IC, a
    bug in crew's own counter holds a teammate in a loop with nothing to stop
    it. §13.1 carries the decision and what replaces it.

    **The replacement, probed the same day.** A project lead can re-engage an
    idle teammate with one message. `nudge-bot` replied `FIRST` and went idle
    at 00:34:11Z; its project lead sent `SendMessage` at 00:34:18Z; the
    teammate re-engaged and replied `SECOND` at 00:34:19Z, with its context
    intact. One message, 1.5 seconds, and the same one-turn save the hook was
    built for — without a hook that fires in sessions crew is not running.

    Two things this probe leaves for whoever builds §9.2's idle handling. The
    project lead must notice the idle, which it does today only when it reads
    the idle notification, so the nudge belongs beside its §7 verification, not
    in a separate watcher. And a nudge can be ignored just like a refusal: cap
    it at one per dispatch, and let §7 fail the package if the second idle is
    still empty.

    Two details worth keeping even though the hook is gone, because any future
    hook meets them. `team_name` is deprecated in the payload. And an IC
    blocked by a hook rather than a reviewer has no rule in `ic-contract.md`
    telling it what to do — `probe-bot` asked its project lead to remove the
    hook, and the project lead refused because the config belonged to another
    session. That was judgment, not instruction.
30. **The full path is written — five decisions the design had not stated,
    2026-09-01 (T6).** `skills/project-lead/references/full-path.md` carries
    the loop for a deliverable with more than one package: launch conditions,
    the split critic, worktrees, named IC teammates, the plan gate by
    message, per-package squash merges with a suite run each, promotion,
    cleanup and `--resume` recovery. `SKILL.md` branches to it at step 5 and
    keeps the simple path in its own steps 6 to 14. Writing it forced five
    decisions.

    a. **The full path is a sixth reference, not more `SKILL.md`.** The body
       was already at the writing standard's 200-line cap, and the full path
       is longer than the simple path it replaces. Splitting it also matches
       how it runs: a simple-path run never reads it. Trimming `SKILL.md`
       back under the cap removed three rules it stated twice — the `BLOCKED`
       promotion rule (`band-rubric.md` owns it), the council row
       (`autonomy-contract.md` owns it), and the draft-PR step, which
       `full-path.md` now points at rather than repeats.

       It bends the writing standard's reference-depth check, which says no
       reference points to a second reference. `full-path.md` names
       `record-format.md`, `band-rubric.md` and `ic-contract.md` as owners of
       rules it will not restate. That is the existing idiom, not a new
       exception — `band-rubric.md` already names `ic-contract.md`'s
       `BLOCKED` row and `record-format.md`'s `band_history` row the same
       way. The check bars a reader hop the file cannot avoid; naming the
       owner of a rule the project lead has already read at step 1 is not
       one.

    b. **Withdrawn — a full-path IC writes to the record root, like every
       other IC.** This item first routed the IC's plan and report to a
       `.crew/` directory inside its worktree, to dodge item 26b's
       sensitive-path denial. Item 31 probed the denial and it did not
       reproduce, so the detour bought nothing and cost a copy hop. Its
       stated reason was also wrong: it claimed a teammate's final message
       has no reader, when §12 only says the message is not a parseable tool
       result. It still arrives, in the idle notification, which item 31c
       confirms. The `ic-contract.md` fallback therefore covers both paths,
       and one write location serves both.

    c. **Withdrawn with (b), and it would not have worked.** The plan was to
       hide `.crew/` in the worktree's `.git/info/exclude`. A linked
       worktree's `.git` is a **file**, not a directory, so that path cannot
       be appended to at all; and git reads exclude patterns from
       `$GIT_COMMON_DIR/info/exclude`, so a pattern written to the
       per-worktree git dir is never consulted. Verified three ways in a
       scratch repo on 2026-09-01. The lesson is narrow and worth keeping: a
       command written from memory about worktree internals is a claim like
       any other, and this one shipped in a first draft unrun.

    d. **Superseded by §15.37f — the root moved out of the target repo.**
       This item put worktrees at
       `<repo>/.claude/worktrees/crew/<goal-slug>/<territory-slug>`, and the
       hazard it names in its last sentence is the one that fired on the first
       repo tried (§15.35b). The root is now `<record-root>/worktrees`. The
       reasoning below stands except for the location it chose.
       `record-format.md` previously showed `~/.claude/worktrees/crew/<name>`,
       which item 26b's sensitive-path finding makes suspect for the same
       reason it blocks the record root, and which has no goal segment to keep
       two concurrent goals apart. A repo-local root is proven writable — this
       repo's own sessions run in one — and git omits a registered worktree
       from its parent's `git status`, so nothing there reads as untracked
       work. The one hazard is a test runner that walks the directory;
       `full-path.md` step 3 says to move the root out of the repo and record
       why when that happens.

    e. **Launch conditions are a step, not a preamble.** Three of the four —
       the teams flag, an unisolated session, a working display mode — cannot
       be fixed once a run is under way, and the fourth, the permission
       grants, is configuration the project lead may not write for itself
       (§15.12, §15.20). So `full-path.md` step 0 checks all four and
       escalates, and `autonomy-contract.md`'s trigger 7 changed from "the
       full path is not built" to a missing launch condition.

    **Not yet exercised.** T6's "Done when" is a real multi-package run with
    a forced fix round and a kill-and-resume, and that needs an interactive,
    unisolated session with the teams flag. The session that wrote this was
    worktree-isolated, which item 10 already names as the one shape that
    cannot drive the full path. T6 stays open until the run happens. Item 31
    probed the environment the run needs and corrected (b) and (c) before any
    run; what stays unprobed is the loop itself, and the plan-approval
    question §12 has listed as pending since stage 3 — the full path is the
    first place an IC has a message channel to be gated on, so it is the
    first place that probe can run.
31. **The full-path environment probe: nothing was denied, and two of T6's
    own rules were wrong — 2026-09-01.** One teammate, `probe-ic`, spawned
    from `crew:ic` at sonnet by an interactive session on Claude Code 2.1.257
    with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, inside tmux, in a throwaway
    worktree. It was told to attempt four things and to record rather than
    work around each failure. Nothing failed. Five findings.

    a. **Under an auto-approving permission mode the grant set is empty.**
       Not one permission prompt surfaced in the driving session while the
       teammate worked — not for its writes, not for `git -C <worktree>
       status`, not for its commit. §15.12's hazard is real, and a
       classifier that answers prompts removes it as completely as a
       pre-approved allow list does. So the requirement is a property, not a
       mechanism: nothing in the run stops for a human. The probe yields no
       grant strings, because none were ever requested — a run that means to
       satisfy the property with settings instead still needs its list built
       some other way.

       **Crew cannot detect which mechanism is in play, and does not try.** A
       session cannot read its own permission mode, and the only direct probe
       — issue a command that would prompt — fails by stalling, which is the
       outcome the check exists to avoid. So the property is a launch
       requirement named in the README, owned by whoever starts the run, and
       `full-path.md` step 0 lists it apart from the three conditions the
       project lead can actually verify. The project lead's own defence is to
       fail fast: if the first dispatch stalls, escalate as an `environment`
       block rather than spawning the remaining territories behind it.

       Nothing else in either path branches on permission mode, so this is
       the only place it enters the design.

    b. **Item 26b does not reproduce for an interactive teammate.** The write
       to `~/.claude/crew/probe-t6/reports/probe.md` was allowed, and the
       agent created the missing `reports/` directory on the way. Item 26b's
       denial came from a nested headless `claude -p` dispatch, so it is a
       property of that shape and not of the path. The record root is
       writable from the shape stage 5 actually uses, which is what withdrew
       item 30b.

    c. **A teammate's final answer does reach the project lead.** It arrived
       in full, as prose in the idle notification, exactly as §12 and
       `CLAUDE.md` describe — not a parseable tool result, but readable.
       `ic-contract.md`'s "your final message is your report" fallback
       therefore has a reader on both paths. Item 30b claimed otherwise and
       was wrong.

    d. **`git -C <worktree>` commits unattended from a teammate.** Confirms
       §15.23c from the interactive side, which the container probe could not
       reach. The idiom split in `ic-contract.md` — `git -C` for git, a `cd`
       prefix for everything else — needs no change.

    e. **A worktree cannot carry its own `info/exclude`.** The probe caught
       T6's step 3 command as unrunnable, and a scratch-repo test confirmed
       it three ways: a linked worktree's `.git` is a file, so
       `<worktree>/.git/info/exclude` is not a writable path; a pattern
       written to `$GIT_DIR/info/exclude` under `.git/worktrees/<name>` is
       never consulted; only `$GIT_COMMON_DIR/info/exclude` — the shared
       `.git/info/exclude` — takes effect, and it applies to every worktree
       of that repo. Withdrawing item 30c removed the need, but the fact
       stands for anything later that wants to hide a file inside one
       worktree.

    The probe is not the T6 exercise. It proves the environment a full-path
    run needs, not the loop that runs in it.
32. **A project lead in plan mode plans instead of dispatching — observed
    2026-09-01, at the T6 exercise launch.** The skill loaded, read its own
    step 1, and said: "Plan mode is on, so I'll research and plan first rather
    than dispatching the crew loop." The operator switched the session to auto
    mode a moment later and the run proceeded normally, so **what the run
    would have produced was never seen.** What is established is narrower than
    it first looked, and worth keeping at that size.

    a. **The project lead can detect plan mode, and acts on it unprompted.**
    Unlike permission mode (§15.31a), which a session cannot read at all, this
    one reported its own mode before anyone asked and correctly changed what
    it was going to do. That makes plan mode a check the project lead can
    genuinely perform, which is why `SKILL.md` step 1 now tells it to stop and
    say so rather than plan.

    b. **It applies to both paths**, so the rule belongs in `SKILL.md` step 1
    and not beside `full-path.md` step 0's teammate conditions. Plan mode
    forbids the writes and the spawns that every step of either path is made
    of.

    c. **The risk, not yet observed:** a condition that degrades into "asks
    you for approval" produces no error and a plausible plan, so it reads as
    the product working correctly — in exactly the runs meant to prove no
    approval was needed. This is why the rule is worth having even though the
    failure was cut short. Do not cite it as a measured outcome.

    A first draft of this item claimed the run "stopped before it dispatched
    anything" and described what it produced instead. Neither was observed;
    both were inferred from one line of transcript caught while the operator
    was mid-switch. The lesson generalizes past this item: a finding written
    from a live pane is a claim like any other, and the pane is not a
    completed run.
33. **The first simple-path run against a repo with a real test suite —
    2026-09-01, `convert-keys-js`.** Run as the setup for T6's exercise, from
    an interactive session in auto mode. It reached a draft PR
    (jerridan/convert-keys-js#6) with no escalation and no fix round: charter,
    scout, spec, spec critic, split, branch, plan gate, IC, package review,
    integration, deliverable review, PR. Every prior run had been against
    crew itself, which has no suite, so several rules were executing for the
    first time.

    a. **Spend was measured in full, for the first time.** All six agents
       reported `total_tokens` with `measured: true`, totalling 227,766
       against the 2,000,000 ceiling. Item 26d recorded that spend cannot be
       measured through a nested headless dispatch; this run shows that gap
       belongs to that shape and not to §8. A project lead that spawns its own
       subagents gets the number §8 assumes. This is also the first real
       datum for item 3's placeholder ceiling: one small simple-path run costs
       roughly 230k, so 2,000,000 buys about eight or nine of them.

    b. **An acceptance criterion can be green without covering the work.**
       `yarn check-types` exits 0, and `tsconfig.json` sets
       `"files": ["src/index.ts"]`, so it type-checks only the graph reachable
       from the barrel. Until the project lead added the export lines at
       integration, the two new modules were unreachable and that pass was
       vacuous — ts-jest was doing the real checking. The project lead noticed
       unprompted, recorded the limit in its package-review adjudication, and
       deferred the meaningful run to after the index edit. §7 says a green
       run only proves the tree it ran on. The sharper form this run found:
       a green run may not have read your files at all, and nothing in the
       output says so. Worth carrying into any acceptance criterion that
       names a type-check, a lint or a coverage gate over a file list.

    c. **`<path>` had no owner.** `SKILL.md` step 10 and `full-path.md` step 7
       both said to write the review diff to `<path>`, and no file said where.
       The project lead invented `diff-converters-r0.patch` at the record
       root. Sensible, but every run would invent its own name and a later
       round could overwrite the diff an earlier review actually read.
       `record-format.md` now owns a fourth output directory, `diffs/`, with
       `diffs/<id>-r<n>.patch` and `diffs/<deliverable-id>-final.patch`. This
       is a T4 defect that only appears against a repo whose diff is worth
       writing down.

    d. **The project lead read the target repo's conventions instead of
       crew's.** It updated `package.json`'s `description`, put the entries
       under the CHANGELOG's `Added` heading, and left `version` at 1.1.0 —
       correct for a Keep a Changelog repo that bumps at release. Crew's own
       `CLAUDE.md` requires a version bump on every content change, and none
       of that leaked into someone else's project.

    e. **The reviewers cleared a pre-existing bug rather than charging it.**
       `require('dist/index.js')` throws `ReferenceError: self is not
       defined`. The deliverable reviewer reproduced it at base `d744e8a` in
       an isolated worktree, listed it under observations it explicitly did
       not raise as findings, and the project lead named it in the PR body
       instead of fixing it. That is a real bug in the published package and
       is out of this goal's scope.

    **What it did not test.** The goal was picked to split into two packages
    and did not: both converters must register in `src/utils/ConvertKey.ts`,
    so their file sets could not be disjoint, and §5's merge rule correctly
    collapsed them into one. That was a flaw in the goal, not in the
    decomposition — but it means this run exercised the simple path, and T6's
    full path is still unexercised. A goal that splits in this repo needs one
    code package and one package outside `src/`, because every converter
    funnels through the same registry and the same barrel.
34. **Branch names collided between two runs in one repo — 2026-09-01.** The
    first `convert-keys-js` run created `crew/deliverable-1`. Deliverable ids
    restart at 1 in every run, so the next run in the same repo would generate
    the same name and fail at `git switch -c`. The same held for a full-path
    IC branch, `crew/<territory-slug>`: two runs whose splits pick the same
    territory name collide the same way.

    Item 4's goal-slug rule already solved this for the record directory —
    "`<kebab-case-slug>-<4 lowercase hex chars>`, generated once, always, not
    only on a collision", precisely so two goals cannot occupy one directory.
    The rule was written for the record and never carried to the branch names,
    which need it for the same reason and against the same failure. Branches
    are now `crew/<goal-slug>/<deliverable-id>` and
    `crew/<goal-slug>/<territory-slug>`.

    Found by preparing a second run rather than by running one — the first
    run's own branch was still sitting in the repo. Worth noting as the shape
    of the bug: crew has been exercised as a series of first runs, each in a
    fresh state, so anything that only breaks on the *second* run in one repo
    has never been reachable. `worktrees.json` pruning, record-directory
    reuse and PR-branch cleanup all share that property and none has been
    tested.
35. **The full path ran, and four rules were wrong — 2026-09-01, T6's
    exercise on `convert-keys-js`.** Goal: add a `toDotCase` converter and
    write `docs/USAGE.md` for the three existing converters. The project lead
    split it into two territories, `src` and `docs`, dispatched
    `crew:split-critic` for the first time in the plugin's life, created two
    worktrees, and ran `crew:ic` and `crew:ic-instructions` as teammates side
    by side. Findings recorded while the run was still in flight.

    a. **§12's plan-approval probe is closed. The message form works.** Both
       ICs wrote `plans/<id>.md`, notified the project lead and went idle
       waiting. The project lead read each plan and sent a go-ahead by
       message, and both gates opened. It did not rubber-stamp either: each
       approval carried added requirements — `ic-src` was told to add a test
       that `objectKey`, `object_key` and `object-key` all converge on
       `object.key`, because a case-for-case copy of the kebab spec would
       never produce that case, and `ic-docs` was told to verify its nine
       examples by running the library rather than by hand. That is
       approve-with-feedback, which is the half of the gate the fallback
       cannot do. `ic-contract.md` keeps both branches: a teammate waits on
       its channel, a subagent ends its turn.

    b. **The worktree root default is wrong, and its escape hatch fired on
       the first repo tried.** `full-path.md` step 3 defaults to
       `<repo>/.claude/worktrees/crew/<goal-slug>` and says to move out when
       the target repo's test runner walks that directory. This repo's does:
       `jest.config.js` sets no `testPathIgnorePatterns`, so `yarn test` at
       the root collected every worktree's specs and reported 12 suites and
       189 tests instead of 4 and 63. `.claude/` also showed as untracked,
       because the repo's `.gitignore` does not name it. The project lead
       detected both, moved the root, and recorded why. A default that breaks
       on the first repo it meets is not a default: the root belongs outside
       the target repo, and repo-local should be the exception.

    c. **A worktree has no `node_modules`, and nothing said whose problem
       that is.** Neither IC could run its acceptance criterion — a fresh
       worktree carries tracked files only. The project lead symlinked the
       repo's own install into each worktree and justified it from the
       contract: environment setup is the project lead's job, and an IC
       blocked on a missing tool is an `environment` block, which never
       promotes. Correct, and reached unaided. Every JS, Python and Rust repo
       has this problem, and `full-path.md` step 3 creates a worktree and
       hands it over without a word about dependencies.

    d. **Both critics ran at sonnet, though their definitions say opus.**
       `agents/spec-critic.md` and `agents/split-critic.md` carry
       `model: opus`; both reviews report `sonnet`. A spawn-time model
       overrides frontmatter (§12), and no file told the project lead not to
       pass one — `band-rubric.md` covered packages, councils and researchers
       and never mentioned critics, so the frontmatter was the only authority
       and it lost silently. Dispatching a critic at the package's band reads
       like consistency and quietly downgrades the check.
       `band-rubric.md` now says a critic or reviewer takes its own model and
       gets no spawn-time override. This was only visible because these
       reviews record the model they ran at; the earlier run's did not.

    e. **`worktrees.json` was written in a shape `record-format.md` does not
       define.** The reference specifies a map keyed by IC name. The run
       wrote `{"worktrees": [ {...,"ic_name":...} ]}`. The array is arguably
       the better shape, but §10.1's recovery reads this file, and a format
       that varies per run is one recovery cannot depend on. Undecided:
       either the reference adopts the array or the loop is held to the map.

    f. **The state machine has no word for "reviewed, not yet merged".** Both
       packages passed through `accepted`, a value `record-format.md` does not
       define, between `in-flight` and `integrated`. It is not a slip: it
       happened twice, in the same place, because the full path genuinely has
       that state and the simple path does not. Merges happen one at a time
       at step 9, after every package is reviewed, so a package really is
       finished and waiting. On the simple path nothing merges and step 12
       marks the package `integrated` in place, so the four states were
       designed against a shape where review and integration are one moment.
       The window is short but it is exactly when a crash is likeliest — the
       project lead is running merges and suites — and `--resume` would then
       read a state its own table does not define. Recommend adding
       `in-flight -> accepted -> integrated`, because recovery is the
       argument: with `accepted` recorded, resume knows the review already
       passed and does not redo it, which `git log` alone cannot tell it.

    g. **"Commit after every green step" does not hold unless the project
       lead repeats it.** `ic-docs` made four commits, one per section plus a
       proofread pass; `ic-src` made one commit for 204 lines. Same contract,
       same session, same run. The difference is that the project lead's plan
       approval told `ic-docs` to commit per section and told `ic-src`
       nothing. So the contract's own Commit-discipline line did not carry
       the behaviour on its own. That line's stated purpose — bounding crash
       loss to one increment — is a recovery property, which is what T6
       depends on, so either `ic-contract.md` states it more strongly or
       `full-path.md` step 5 makes it part of every plan approval. Isolating
       this needed two ICs running in parallel under different instructions;
       one package could never have shown it.

    h. **The deliverable reviewer caught a defect in the project lead's own
       shared-file edit.** Its README sentence promised "a worked example of
       each converter" under a list of four functions, while `docs/USAGE.md`
       covers three by the run's own decision D5. No package reviewer could
       have seen it: the file belongs to no package and the edit happened
       after both package reviews. Item 24 predicted this from the simple
       path; the full path confirms it, and it is the clearest argument the
       deliverable reviewer has yet produced for its own existence.

    i. **Cleanup worked.** Both worktrees were removed and deregistered after
       the PR opened, `worktrees.json` was emptied with a note, and the IC
       branches were retained because their commits are squashed onto the
       deliverable branch. Nothing was forced.

    **What the run did not exercise.** No fix round — both package reviews
    returned `accepted` first time — and no kill-and-resume. §10.1's recovery
    is the one part of the full path still unproven, and finding (g) makes it
    more urgent rather than less: an IC that commits once at the end turns a
    crash into a large dirty worktree, which is the branch of §10.1's table
    that has never run.
36. **T6 closed: the fix round and the kill-and-resume, on the third run —
    2026-09-01, `convert-keys-js` PR #8.** Goal: a `toTitleCase` converter and
    `docs/OVERRIDES.md`. Two packages, two territories, two IC teammates, one
    forced fix round, one crash, one resume, one draft PR. Claude Code 2.1.258
    — a version newer than item 35's run, which updated itself between the
    two.

    a. **The forced fix round ran on a real defect the reviewer missed.**
       `titleCase` mapped each word to `word.charAt(0).toUpperCase() +
       word.slice(1).toLowerCase()`, and `lodashSnakeCase` returns lowercase
       by contract, so that `.toLowerCase()` could never fire. The package
       review returned `accepted` with no findings. Forced by a message to the
       project lead, the round removed the dead call in one commit, wrote
       `diffs/titlecase-converter-r1.patch`, re-reviewed, and returned
       `accepted` with `fix_rounds_used` persisted at 1. The loop's return
       edge — every round goes back through verification and review, and the
       step exits only on `accepted` — is the control-flow gap item 25 found
       by reading. It is now confirmed by running.

    b. **Recovery works, and it was tested against a record that lied.** The
       pane was killed with `overrides-docs` merged and `titlecase-converter`
       merged seconds later, while `state.json` still called both `in-flight`
       and the run `active`. A fresh session read git rather than the record,
       corrected both packages to `integrated`, kept `fix_rounds_used`,
       re-dispatched nothing, and finished the run. Rule 2 of §10.1 —
       reconcile from git, then correct the record — is the rule that carried
       it, and it carried it against a two-package divergence rather than a
       toy one.

    c. **The append-only session rule held in both files.** `--resume` added
       its session id to `run.session_ids` and to every entry in
       `worktrees.json`, overwriting neither. That rule exists because resume
       runs under a new id and ownership matching would otherwise fail on the
       first resume — the exact case that had never been exercised.

    d. **`interrupted` and `orphaned` remain unproven, and that belongs to
       T7.** Nothing marked the dead run interrupted or its worktrees
       orphaned, because the `SessionEnd` hook that writes both does not
       exist. So `record-format.md`'s `interrupted -> active` transition has
       still never fired, and §10.1's "clear `orphaned` once reconciled" step
       had nothing to clear. This makes the run a harder test rather than an
       easier one: recovery had to work from a record that claimed the dead
       run was live.

    e. **The escalation path fired for the first time, on a council-route
       question.** The project lead could not settle what `toTitleCase` should
       produce for `object_key` from the repo or any instruction, and it
       escalated rather than guessing — recorded with all four fields, an
       answer, and `run_state` back to `active`. It classified the trigger
       correctly as §6 trigger 3, a council-route question it could not answer
       with a citation, not a preference question: the output shape of a new
       exported function is a public-interface judgment. Councils are not
       built, so the contract's degraded row sent it to a human. With T8 it
       would have been answered inside the run. This is the first concrete
       case where the missing stage cost an interruption.

    f. **The re-spec loop fired for the first time too.** `crew:spec-critic`
       returned `re-spec needed` with one `[Critical]`: R1's acceptance
       criterion said mirror `toCamelCase.spec.ts`, and R3 required inputs
       that file does not contain, so the two could not both hold. The project
       lead revised the spec, re-dispatched, and got `ready to split` on r2 —
       before any IC was spawned, which is the gate's whole purpose.

    g. **No adjudication was written anywhere in this run.** Neither spec
       review nor the deliverable review carries the "Adjudication by the
       project lead" section that both earlier runs appended to every review,
       and `decisions.md` has no entry for the `[Critical]` either. `SKILL.md`
       step 4 requires pushing back in writing but never says where an
       adjudication is written; the first two runs invented the convention of
       appending it to the review file and this one did not. The gap is in the
       instruction, not in the run. `review-output.md` is the file that should
       own the location, since it already owns the shape of what a review
       returns.

    h. **Artifact names keep drifting wherever `record-format.md` is
       silent.** The acceptance checklist a prose package needs — design §5
       invariant 1's "a written checklist verified by a named reviewer" —
       landed at `reviews/overrides-docs-checklist.md`, while item 35's run
       put its equivalent at `diffs/usage-guide-r0-checklist-target.md`. They
       are not even the same artifact: one is the checklist, the other a copy
       of the finished document. Both are required by the design and neither
       has a defined home. Same class as the `<path>` gap in item 33, and the
       same fix: name it, or every run invents something reasonable and
       different.

    i. **Worktree and IC naming drifted from a rule that does exist.**
       `full-path.md` step 3 says the worktree directory, the branch and the
       IC name all take the **territory** slug. This run used package ids —
       `worktrees/titlecase-converter`, `ic-titlecase-converter` — where item
       35's run correctly used `worktrees/src` and `ic-src`. Harmless while
       each territory holds one package, wrong the moment a territory holds
       several, which is the case territories exist for.

    j. **A run's model choices are unverifiable.** Item 35d found three
       opus-defined critics silently dispatched at sonnet, and could only find
       it because that run's reviews happened to record the model. This run's
       reviews record none, so whether the `band-rubric.md` fix took effect
       cannot be confirmed from the record — only weakly inferred from the
       absence of a model label in the transcript. A rule nothing can audit is
       a weak rule: `review-output.md` should require every review to state
       the model it ran at.
37. **A code review of the T6 branch found what three runs could not — the
    multi-package territory — 2026-09-01.** Fifteen findings, two of them
    `[Critical]`, and every one held on verification. Ten were fixed; the rest
    were already recorded as deferrals. Both `[Critical]`s came from one
    mistake: **`full-path.md` was written as though a territory holds exactly
    one package.** Design §5 says the opposite — a territory is a region one IC
    owns and works *several* packages in, and fewer spawns with retained
    context is the reason territories exist. All three runs happened to give
    each territory one package, so the loop's central case never ran.

    a. **A package had no `base`, so every package after the first in a
       territory was doomed to a false scope finding.** Step 7 diffed
       `<base>..HEAD` where `base` is the deliverable's — the only base any
       record field carried. A territory's packages are sequential commits on
       one branch, so package 2's review diff contained package 1's files, and
       `package-reviewer.md` is required to flag a file outside the declared
       `file_set` as scope drift. That is a guaranteed `[Critical]` and a
       wasted fix round on every package after the first. `packages[]` now
       carries its own `base`, written at dispatch and rewritten when the IC is
       sent its next package, and steps 6 and 7 range from it.

    b. **`merge --squash` of a territory branch cannot give one commit per
       package.** The branch holds every package the territory has finished, so
       a three-package territory produced one squashed commit and one suite
       run — losing both benefits §9.3 claims, per-package attribution with no
       bisect and a narrative a reviewer can read. Step 9 now applies the
       package's own range, `git cherry-pick -n <package-base>..<package-head>`
       followed by one commit, as each package is accepted.

    c. **`--resume` fell through into new-run setup.** The resume paragraph was
       followed unconditionally by "create `~/.claude/crew/<slug>-<4 hex>/`",
       so a resumed run would mint a second record directory beside the one it
       had just reconciled, rewrite the spec, re-dispatch the spec critic, and
       fail at `git switch -c` on a branch that already exists. The §15.36 run
       never reached it because the resumed session re-entered mid-loop. Step 1
       now stops the resume path before setup and says to re-enter at the first
       unfinished step.

    d. **The fix-round counter was incremented after the files named by it.**
       Steps 6 and 7 name `diffs/<id>-r<n>.patch` and
       `reviews/<id>-package-review-r<n>.md` from `fix_rounds_used`, and the
       increment came last, so round 1 would overwrite round 0's diff and
       review — the two artifacts `record-format.md` declares are never
       overwritten. Both files now increment first.

    e. **Rounds 4 and 5 promoted with no top-band guard**, contradicting
       `band-rubric.md`'s "a `deep` package cannot promote further". Both files
       now escalate instead.

    f. **The worktree root default is inverted.** §15.35b concluded the root
       belongs outside the target repo and the files still defaulted to
       repo-local with an escape hatch. Now the default is
       `<record-root>/worktrees` and repo-local needs a recorded reason.

    g. **Removing trigger 7's old wording removed the only stop for a
       multi-deliverable goal.** It used to read "the goal needs more than one
       package. The full path is not built", which caught a goal too large for
       one deliverable as a side effect. `full-path.md` runs one deliverable
       and nothing reads `split.md`'s `Depends on`, so such a goal had no path
       and no escalation. That is now trigger 8.

    h. **Two worked examples in `record-format.md` still taught the branch
       name §15.34 had just fixed**, and a third instance the review did not
       catch. An example is an instruction: an agent copying it would recreate
       the collision the slug segment exists to prevent.

    i. **A crew-specific rule had leaked into a target-repo instruction.** Step
       9 said "bump both version fields", which is crew's own two-manifest rule
       and wrong for most repos — and §15.33d had praised an earlier run
       precisely for *not* applying it to someone else's project.

    The lesson is narrower than "review found bugs". Running the loop three
    times proved the paths those runs took. It could say nothing about the
    paths they did not, and the reading found the worst defects in exactly
    those: the multi-package territory, the resume that re-enters at step 1,
    the fourth fix round. Runs and reviews cover different surfaces, and a
    green run is not evidence about an untaken branch.
38. **`SessionEnd` ships, and it cannot tell a crash from a clean exit —
    T7, probed 2026-09-02.** `hooks/hooks.json` registers one hook,
    `hooks/session-end.py`. It marks every `active` or `blocked` run whose
    `run.session_ids` hold the ending session's id as `interrupted`, and sets
    `orphaned: true` on that run's worktrees with the same id. It writes two
    files and deletes nothing.

    **The probe.** A record was seeded under `~/.claude/crew/` with
    `run_state: active` and one worktree, both carrying a chosen uuid. A
    headless session ran with that uuid and this checkout loaded:
    `claude -p --session-id <uuid> --plugin-dir <repo>`. The session ended, and
    the record read `interrupted` with the worktree `orphaned: true`. A second
    worktree in the same record, owned by a different session id, stayed
    `false`, and the four real records on the machine were untouched. Bench
    cases covered the rest: an unknown session id, a malformed payload, and a
    missing `crew/` directory each exit 0 and write nothing.

    Three things this settles.

    a. **`--session-id` makes a hook testable headlessly.** `TeammateIdle`
       needed an interactive session in tmux (§15.29). A hook that keys on the
       session id needs only a seeded record and a chosen uuid, so this one was
       proved end to end in a `-p` run.

    b. **The hook fires on every session end, clean or not.** Nothing in the
       payload separates a crash from a normal exit, and `reason` does not
       carry it either. So `run_state: complete`, written by the project lead
       when it opens the draft PR, is the only thing that protects a finished
       run from being marked interrupted. A run the project lead left `active`
       gets `interrupted` even when the human simply closed the terminal —
       which is correct: nothing finished that run, and `--resume` moves it
       back.

    c. **The hook is the repo's first executable file.** It is `python3` and
       stdlib only, because it edits JSON and a shell script cannot do that
       without `jq`. A machine with no `python3` loses the marker and nothing
       else — the run is unaffected, and recovery reconciles from git as it
       always did (§10.1). Every failure inside the script is swallowed and
       exits 0, because this hook runs in every session on the machine.

    **What is still unproven.** The idle nudge itself (`full-path.md` step 5a)
    is written from §15.29's probe, not from a run: no crew run has produced a
    teammate that idled with no report, so the nudge, its one-per-dispatch cap
    and the `BLOCKED` fallback on a second empty idle have never fired against
    a real IC. §15.40 records two runs built to provoke exactly that and
    failing to. The plan-gate exemption is exercised (§15.40c), and the hook
    now has a run-written record behind it (§15.40b).
39. **The project lead invented its session id, so the `SessionEnd` hook
    would have matched nothing — found 2026-09-02, by a run that was probing
    something else.** A full `/crew:project-lead` run against a scratch repo
    wrote `"session_ids": ["session_01MDcB7zHedJbJEZXGtZn75j"]` into
    `state.json`. That session's real id was
    `8154734d-d163-4d22-8946-83c3b12cb6f2`, which is what names its transcript
    under `~/.claude/projects/`. The id in the record was plausible and wholly
    invented.

    **Why it matters.** §15.38's hook matches `run.session_ids` against the
    payload's `session_id` by exact string. An invented id matches nothing, so
    the hook marks no run interrupted and no worktree orphaned, silently, on
    every real run. `--resume` loses its only proof of worktree ownership at
    the same time (§13.1).

    **The cause is a missing instruction, not a bad model.** Nothing in
    `record-format.md`, `SKILL.md` or `full-path.md` said where a session's own
    id comes from, and `record-format.md`'s worked examples used `sess-3f9a`,
    `sess-a001` and `sess-b002` — short fake ids that read as a format to
    imitate rather than a value to read. Given a field to fill and no source,
    the model produced something shaped like the examples.

    **The fix.** `$CLAUDE_CODE_SESSION_ID` is set in every Claude Code session
    and equals the transcript filename. `record-format.md` now says to run
    `echo $CLAUDE_CODE_SESSION_ID` and never to invent the value, and its
    worked examples carry real uuids so the shape cannot mislead.

    **What this says about §15.38's verification.** That probe seeded the
    record by hand with the true session id and then asserted the hook matched
    it. It proved the hook's mechanism and nothing about the record a real run
    writes, because the same author wrote both sides of the comparison. A hook
    that keys on a value some other agent must produce is only proved by a run
    that produces it. This is §15.37's lesson again: a green probe says nothing
    about the branch it did not take.
40. **Two runs built to catch the idle nudge caught four other things and
    never caught the nudge — 2026-09-02, T7's verification.** A scratch repo
    (`string-kit`, a helper library with a `node --test` suite) was built to
    provoke an IC that idles with no report. Its own `CLAUDE.md` carried the
    bait, under a `## Reporting` heading: reply with a one-line summary, and
    write no status files, task reports, plans or logs. Nothing in it mentions
    crew, so a project lead meets the fault the way it would meet a real
    repo's house style.

    **Run 1 took the simple path**, because two helpers read as one package.
    No teammate, no idle, nothing to nudge. The charter was too small, which is
    a lesson about writing a probe, not about crew: the shape is chosen from
    the work, so a probe that needs the full path must carry work that earns
    it.

    **Run 2 took the full path** on a charter of seven helpers in two subject
    areas — two territories, two worktrees, `ic-case` and `ic-path` as
    teammates, a split critic, a squash merge and suite run per package, and
    zero fix rounds. It cost $12.14 and about 25 minutes.

    Four things it settled, none of them the nudge:

    a. **§15.39's fix works.** The record carried
       `"session_ids": ["efec9753-02fb-4c8e-85d6-0cf0f851d5ac"]`, the session's
       real id, written by a project lead reading
       `$CLAUDE_CODE_SESSION_ID` as `record-format.md` now tells it to.

    b. **`SessionEnd` fires against a record a run wrote.** With `run_state`
       hand-set back to `active` to stand in for a crash — that flip is the
       only synthetic part — ending the session moved it to `interrupted`,
       matching on the id the project lead had recorded itself. §15.38's probe
       had matched an id this author seeded; this one matched an id crew
       produced.

    c. **The plan gate takes no nudge, on a real run.** Both ICs wrote
       `plans/<id>.md` and idled with `plan_approved_at` null. Both were
       approved and neither was nudged, `nudges_used` staying 0 through the
       whole run. That branch of `full-path.md` step 5a is now exercised.

    d. **The bait failed, twice, because `ic-contract.md` held.** Both ICs
       wrote `reports/<id>.md` in full, against their repo's explicit
       instruction not to. That is the right outcome and it is the reason the
       nudge stays unproven: the failure it handles is hard to provoke even
       when a probe is built to provoke it. It is direct evidence for §13.1's
       reason for cutting `TeammateIdle` — crew has never observed the failure
       that hook prevented, and two attempts to manufacture it did not.

    **Two defects the runs exposed, both outside T7.**

    e. **The scope boundary is implicit, and both ICs read it correctly
       anyway. No change made.** The bait was aimed at crew's record, not at
       the repo — "do not write status files" in a repo's own `CLAUDE.md`
       means do not litter that checkout. Both ICs read it that way, wrote
       their reports to the record root outside the repo, and carried on.
       Nothing in `ic-contract.md` states that repo instructions govern the
       worktree while this contract governs the record; the ICs inferred it
       from the record root being an absolute path outside the repo. Stating
       it was considered and dropped: two runs show the inference holds, and
       a rule whose absence causes no mistake is one the writing standard
       says to delete. Revisit only if an IC is seen getting it wrong.

    f. **A deliverable that cannot open a PR has no honest terminal state.**
       The scratch repo has no git remote, so `git push` and `gh pr create`
       could not run. The project lead escalated correctly, took the answer,
       and then recorded `state: "draft-pr-opened"` with `pr_url: null` — a
       state that claims a PR nobody opened. `record-format.md`'s vocabulary
       has no state for finished-without-a-PR. T11 already needs exactly such
       a state for an investigation that ends in a report; this is a second
       caller for it.

       **Decided 2026-09-02 (T16).** The new terminal deliverable state is
       named `work-complete`. It serves two callers: a deliverable whose push
       or draft PR is impossible or refused, and T11's investigation path,
       which ends in a report rather than a change. A council chose it over
       `closed-no-pr` and `handed-off`; `record-format.md` owns the
       definition.

    **What the probe cost, and what it bought.** $17.43 over two runs to prove
    one line of a hook and disprove nothing about the nudge. Worth it anyway:
    a and b are the difference between a hook that works and a hook that never
    matches, and neither was reachable by a probe whose author wrote both
    sides.

41. **The advocate got its own agent definition, which revises §3 —
    2026-09-02, T8.** §3's `Advocate` row said `general-purpose` subagent,
    briefed inline. It now says `crew:council-advocate`.

    The deciding argument is the tool boundary. A `general-purpose` dispatch
    carries every tool, including `Write`, `Edit` and an unrestricted `Bash`,
    and a council runs two or three of them in parallel while ICs hold
    worktrees. An advocate that can edit is a hazard with no upside — it
    argues, it never builds. `writing-standard.md` states the rule this rests
    on: `tools` is a capability boundary, not a formality. Every other crew
    role that must not edit already carries its own definition and its own
    tool list: `spec-critic`, `split-critic`, `package-reviewer`,
    `deliverable-reviewer`, `researcher`. The advocate is the same shape, and
    it was the only one of the six left inline.

    The second argument is drift. Six rules are the same in every council —
    argue the assigned side, cite every claim, an instruction beats precedent,
    volume is not evidence, name the strongest objection to your own side,
    edit nothing. Retyped into two or three spawn prompts per council, they
    are the exact duplication `CLAUDE.md` bans.

    The cost is one more file the plugin loads, and one more place a council
    rule could be stated twice. `band-rubric.md` still owns the model, and
    `autonomy-contract.md` still owns the procedure. The definition owns only
    how one advocate argues.

42. **Closed by §15.47 the same day: a run convened a council.** Left here for
    the standard it set, which §15.47 then met.

    **Stage 6 is built and no run has convened a council — 2026-09-02, T8.**
    T8's "done when" asks for an architecture-moving question resolved by a
    council in a real run. The build landed; that clause did not. It stays
    open the way T7's nudge clause does, and it closes from a real run rather
    than from a rig, because a council convened to test councils frames its
    own question and proves less than it appears to.

43. **The first council ran, by hand, and the mechanism worked — 2026-09-02,
    T8.** Three advocates, one batch, on a real open question from this repo:
    T10's owner for reader-facing prose. Positions were assigned, not
    discovered — A grow `crew:ic-instructions`, B add a second prose
    specialist, C the project lead owns it. §15.17 carries the decision.

    **What the shape produced.** Every advocate returned the definition's
    report shape without being shown it in the prompt — it read the file. Every
    citation was checked against the repo, and every one held but a truncated
    sentence in C's evidence list. No advocate hedged toward the middle, and
    each named a genuine objection to its own side. Two of those objections did
    real work: C's admitted its strongest citation was the PR body and
    transferred to a README only by analogy, which is what the adjudication
    turned on, and A's proposed a rename rather than defending the name. The
    `Confidence` line paid for itself: B's `medium`, with its stated reason
    (no repo precedent that a split is how this codebase resolves a forked
    acceptance mechanism), was a more useful signal than its argument.

    **The adjudication split the question rather than picking a side.** A won
    for a README; C won for a PR body, an issue and a comment. No advocate
    framed that split, because an advocate argues its assignment. This is the
    judge's job working as §6.1 intends, and it is the argument against ever
    reading a council as a vote.

    **Spend: 169,257 tokens across three sonnet advocates**, 54k / 54k / 61k,
    with the adjudication on top. One council on one question already costs
    what a small package costs. §6.1's claim that a council is the largest
    single line item in a run now has one measurement behind it.

    **The defect the exercise found is in the dispatch shape, not the
    council.** The advocates ran as `general-purpose` subagents told to read
    `agents/council-advocate.md`. That injects the body and drops the
    frontmatter: `model: sonnet` held only because it was passed as a spawn
    override, and `reasoning_effort: high` was never applied. A hand-dispatch
    of any crew agent, from a session that has not loaded the plugin,
    exercises the text and nothing else — not the model, not the effort, not
    the tool boundary. This is §15.35's defect in a new place: the value in the
    definition loses silently. Exercise an agent through
    `claude --plugin-dir <repo>` whenever the frontmatter is part of what is
    being tested.

    **What stays unproven.** No `/crew:project-lead` run has convened a
    council. Nothing here exercised the routing that reaches one, the
    `decisions.md` write, or the balanced-council escalation — all three
    advocates were decisive and the judge was not balanced.

44. **An advocate at medium effort writes a better-reading case that the judge
    cannot verify — 2026-09-02, T8.** The council in §15.43 ran by hand, which
    dropped the definition's frontmatter, so nothing had yet tested the
    `reasoning_effort: high` that `agents/council-advocate.md` carries. This
    probe tested it directly.

    **The rig, which is the reusable part.** `claude -p --plugin-dir <repo>
    --agent crew:council-advocate --effort <level> --output-format json` runs
    the session **as** the agent, with its frontmatter in force: the JSON came
    back on `claude-sonnet-5` with no `model` passed, which is the definition's
    own value. `--effort` overrides the session's effort, so one definition can
    be run at two levels with nothing else changed. The JSON also carries
    `usage.output_tokens_details.thinking_tokens`, which is what makes the
    comparison measurable. `--effort` was confirmed to do something first: the
    same problem drew 57 thinking tokens at `low` and 153 at `high`. On a
    trivial prompt both levels were identical, so a probe of the flag needs a
    question with room to think.

    **The result, one position argued twice.** High: 5,204 thinking tokens,
    8,441 output, $0.19, and every one of nine `path:line` anchors landed on
    the line it quoted. Medium: 2,042 thinking tokens, 5,324 output, $0.16, and
    every anchor checked pointed somewhere else — usually a nearby section
    header. Medium's **quotes were genuine**; the text it quoted is in the
    repo. Only the anchors missed.

    **Why that is disqualifying rather than untidy.** §6.1 puts citation
    checking on the judge, and the judge is the most expensive agent in the
    run. An advocate whose quotes are real and whose anchors are wrong does not
    save the judge the search — it hides that the search still has to happen.
    Medium's prose was, if anything, the stronger read: its self-objection
    named the exact reading the real adjudication turned on. That is the trap.
    A case that reads better than it verifies is worse than one that reads
    worse, because the failure is invisible until the judge clicks.

    **The saving is 3 cents an advocate, about 16%.** Against §15.43's measured
    169,257-token council, that is not a trade. `reasoning_effort: high` stays
    in `agents/council-advocate.md`.

    **How far this evidence goes.** One paired comparison, one position, one
    question. It is directional, not established. §15.45's four later runs do
    not strengthen it and do not weaken it — none of them ran at medium.

    **The confound, which §15.45 exposed.** Every run that anchored correctly
    said it looked the numbers up, with `grep -n` or `sed -n`. The medium run
    inferred them. So the variable may be whether the agent verifies rather
    than how deeply it reasons, and effort may only change how likely it is to
    bother. `agents/council-advocate.md` now says to look each line up, which
    makes the outcome hold either way. Keep `high` as well: it costs 3 cents an
    advocate, and the instruction is untested at medium.

45. **A spawn-time model does not cost an agent its effort; whether a subagent
    inherits effort is still unknown — 2026-09-02, T8.** Two probes in
    §15.44's rig, four runs.

    **Probe 1, answered.** `band-rubric.md` tells the project lead to raise
    every advocate to opus together for a `deep` decision, which means passing
    `model` at spawn. Design §12 establishes that `reasoning_effort` cannot be
    *sent* at spawn; it does not say whether a sent `model` clobbers the
    definition's own effort. Two dispatches of `crew:council-advocate` from a
    plugin-loaded headless parent, same question, one passing `model: sonnet`
    and one passing nothing: both returned every `path:line` anchor correct,
    including `CLAUDE.md:81`, the line §15.44's medium run had placed at 44-45.
    A spawn-time `model` is safe. The raise-to-opus rule keeps its effort.

    **Probe 2, inconclusive, and closed as not worth settling.** The question
    was whether an agent with no declared effort — an IC's exact shape —
    inherits the parent session's. Identical citation task, `general-purpose`
    subagent, parent at `low` and at `high`. **Both scored six of six.** A
    probe whose arms both max out measures nothing.

    §15.46 then tried it on a real teammate and could not separate the causes
    either. Stop here: **crew takes §12's claim as given — an IC and a scout
    run at the effort of the session that launched the run.** No action depends
    on proving it. Effort cannot be set per-agent either way, so the only move
    available is to set the session's effort before starting, which the README
    now says. A probe that changes no decision is not worth its cost.

    **What no probe here can reach.** Design §12's claim is about a
    **teammate**, and headless `-p` cannot spawn one. Probe 2 tested a
    subagent. The teammate case stays open and needs an interactive session
    with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`.

    **The rig, worth reusing.** `claude -p --plugin-dir <repo> --agent
    <name> --effort <level> --output-format json` runs a session **as** a crew
    agent with its frontmatter in force, and the JSON reports
    `usage.output_tokens_details.thinking_tokens`, `modelUsage` per model, and
    `subagent_stats.by_type` — enough to prove which agent and which model
    actually ran. Confirm `--effort` bites before trusting it: on a trivial
    prompt `low` and `high` were identical, and only a question with room to
    think separated them (57 against 153 thinking tokens).

46. **A project lead reported citation drift that was not there — 2026-09-02,
    T8.** An interactive tmux session at `--effort low`, with
    `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`, spawned `crew:council-advocate`
    as a **named teammate** and gave it §15.43's question. Three things came
    out of it, only one of which was the one being looked for.

    **A teammate cannot see its own effort.** Asked directly, it answered
    "nothing in my system prompt, environment, or context states a reasoning
    effort level or thinking budget." So no self-report can settle §15.45's
    inheritance question, and the behavioural route is closed too: the teammate
    anchored every citation correctly under a `low` parent, which is equally
    explained by it keeping the definition's `high` and by §15.44's new
    look-it-up rule working at `low`. The causes cannot be separated. §15.45
    closes the question instead.

    **The finding that matters was accidental.** The project lead session
    reviewed the teammate's case and reported "line numbers are off by a few",
    naming two. Checked against the files, **all seven anchors were correct**.
    The project lead judged them by eye, from a file it had read earlier, and
    was wrong — in the direction that penalises an advocate that did its job.
    §6.1 puts citation checking on the judge, and a judge that skims is worse
    than no check, because it produces a confident wrong verdict rather than an
    absent one. `autonomy-contract.md`'s adjudication step now says to look
    each cited line up and never judge an anchor by eye.

    **The teammate mechanism itself worked.** A named `crew:ic` teammate
    spawned at a spawn-time model, replied, went idle, took a follow-up message
    and replied again — the re-engagement §15.29 relies on. The one permission
    prompt was a write outside the worktree, which is what §15.12 predicts.

47. **A run convened a council on its own, and its judge caught what the
    hand-run's judge missed — 2026-09-02, T8's closing evidence.** Goal: T16,
    the missing terminal state for a deliverable that finishes its work and
    opens no PR. Interactive tmux session, `--effort high`, agent teams on,
    plugin loaded from the checkout. Record
    `~/.claude/crew/no-pr-terminal-state-9a32/`. Result: draft PR #16,
    `run_state: complete`, **zero escalations**, 744,244 measured tokens
    against a 2,000,000 ceiling, one forced fix round on its own package.
    $20.75.

    **T8's open clause closes here.** The project lead routed "what is the
    fourth terminal state called?" to a council itself — correctly, since
    record vocabulary is a cross-cutting pattern — framed three positions,
    dispatched three advocates in one batch, and adjudicated. The entry carries
    every field the format defines, including `Models: 3 advocates, sonnet.
    Adjudicated at opus.` and `Spend: 126168 tokens`. Nothing was staged: the
    goal was a real open ticket, and the question is one T16 could not be built
    without answering.

    **The routing was written before the answer.** `decisions.md` held
    `Route: council`, the three positions and `Answer: pending` while the
    advocates ran. That is the audit property `autonomy-contract.md` asks for,
    observed rather than asserted.

    **The judge caught a losing advocate's bad anchors.** Its `Losing` line
    reads, of position A: "Two of its anchors also missed
    (`docs/tickets.md:470-471` and `479-480` do not hold the quoted text; it
    sits at 473-475 and 489-490)." §15.46 added the look-each-line-up rule
    hours earlier, after a project lead reported drift that was not there. Here
    a project lead found drift that was, named where the text actually sits,
    and weighed it against that advocate. The rule works in both directions,
    which is what makes it worth its cost.

    **The winner beat the position listed first, on the losers' own
    arguments.** `closed-no-pr` lost to a collision its own advocate raised —
    GitHub's `closed` means opened and then closed, the reverse of this case.
    `handed-off` lost because `design.md:31` already uses "hand-off" for the
    start of a run, so the name would carry two meanings. A council that only
    ratified the first-listed option would be evidence of nothing; this one did
    not.

    **Second spend measurement.** 126,168 tokens for three sonnet advocates,
    against §15.43's 169,257 for the same shape. A council costs about what a
    small package costs, and §6.1's claim that it is a run's largest single
    line item holds on two runs.

    **The defect it exposed: every `Timestamp` was `00:00:00Z`.** Both entries,
    written minutes apart, are stamped midnight, so the decision trail cannot
    be ordered. The project lead wrote the date from context instead of reading
    the clock. `record-format.md` now says to run `date -u`. This is §15.39's
    invented-session-id failure again, in a field that looks harmless enough
    that nobody checked it.

    **A second defect, in the simple path.** The run switched the checkout onto
    its own deliverable branch and left it there when it finished. A person, or
    another session, working in that directory then finds itself on a branch it
    did not choose — the T8 session's next two edits landed on the run's branch
    by accident. §9.1 puts the simple path on the current checkout by design,
    so the fix is to say who restores the original branch and when. Unowned
    today.

    **One process note.** PR #16 branches from T8's own branch, so it carries
    T8's commits and merges after PR #15.

48. **A code review of the T8 branch found ten defects reading could not —
    2026-09-02.** `/code-review high` over `main...ticket-t8-council`. Every
    finding held. Three classes, and the third is the one worth keeping.

    **Stale status claims, three of them, all written by the session that then
    disproved them.** The README's banner and status row still said no run had
    convened a council; §13's stage-6 row said the procedure was unexercised;
    §15.42 asserted an open clause that §15.47, five entries later, opens by
    closing. The same session wrote both halves within an hour. Noticing one
    stale claim (`CLAUDE.md`'s) does not prompt a sweep for the rest — only a
    grep does.

    **Two missed version bumps.** `026abbc` and `1ecca45` each changed a file
    under `skills/`, which the plugin loads, with no bump. An installed copy at
    0.1.22 held neither the look-it-up rule nor the read-the-clock rule, and
    `/plugin update` saw nothing to pull. The bump rule is stated in
    `CLAUDE.md` and was followed for the first two commits of the same branch,
    which is what makes the miss instructive: a rule obeyed early in a branch
    reads as already handled.

    **Four rules that contradict another rule in the same change.** These are
    the ones no amount of rereading finds, because each half is correct alone.

    a. `council-advocate.md` mandated looking every line number up with
       `grep -n` or `sed -n`, and three sections later restricted `Bash` to
       "`git log`, `git blame`, and nothing else". The verification the file
       exists to require was outside the tool boundary the same file sets.

    b. `record-format.md` ordered `Positions` "winner first", while
       `autonomy-contract.md` orders that same line written **before** dispatch,
       when there is no winner. Following both means silently reordering the
       line after adjudication — which also destroys the evidence §15.47 relied
       on to say the council did not simply ratify its first option. Now: the
       order they were framed, never reordered.

    c. `council_tokens` was defined as the advocates' spend **plus the project
       lead's own adjudication**, inside a claim that it is a line item within
       `measured_tokens`. Nothing reports the project lead's own tokens, so the
       sum could exceed the total it sits inside. §15.47's run had already
       ignored the instruction and logged the advocates only. Now: advocates
       only, with the gap stated rather than guessed.

    d. `autonomy-contract.md` said "two of them exist only for a council" where
       `record-format.md` names four, and the two it omitted included
       `Positions` — the field the other file calls load-bearing for an audit,
       and the one step 1 already told the project lead to write.

    **What this says about verifying an instruction repo.** Reading finds a
    rule that is wrong. It does not find two rules that are each right and
    disagree, because checking that costs a pass per pair. A diff-wide review
    is the cheapest thing that does, and on this branch it found four.

49. **An independent review found six defects in crew's own output that crew's
    own reviewers passed — 2026-09-02.** `/code-review high` over PR #16, the
    T16 work produced by the §15.47 run. That run had a `crew:package-reviewer`
    pass, a forced fix round, and a `crew:deliverable-reviewer` pass. Six
    findings survived all of it, three of them substantive.

    **The one that mattered: `work-complete` had no evidence outside the
    record.** Design §10.1 reconciles from git and rewrites the record to
    match. Every other terminal state is provable outside the record —
    `integrated` by a merge, `draft-pr-opened` by a `pr_url`. A
    `work-complete` deliverable looks exactly like an `in-flight` one that died
    just before step 14: commits on a branch, clean tree, no PR. A resume would
    have re-entered step 14 and **opened the very PR the principal refused**.
    The state invented to stop the record lying would have caused the run to
    override a human decision. `record-format.md` now names the `escalations`
    answer as its evidence, forbids moving out of `work-complete` on git
    evidence alone, and requires the deliverable and run writes to land
    together so a crash cannot strand it under a live `run_state`.

    **Two more that reading passed.** Step 14 told the project lead to escalate
    and then set `run_state: complete`, a transition `record-format.md`'s own
    table does not have — and it closed the run with the escalation
    unanswered, which is the opposite of what T16 asked for. And the whole
    procedure was copied into `full-path.md` step 11, in a paragraph that opens
    by naming `SKILL.md` step 14 as its owner.

    **What this says about crew's review layer.** Its reviewers check a package
    against its brief and a deliverable against its spec. They do not check a
    new state against the recovery path that has to survive it, because nothing
    in the brief mentions recovery. The defect was not in the code the package
    wrote; it was in what the package's addition implies for a file it never
    touched. That is the class §15.48 named a diff-wide review as the cheapest
    way to catch, and it holds for crew's own output as much as for a person's.

    **Do not read this as the run failing.** The run produced a correct state
    vocabulary, a correct diagram, a council-chosen name, and threading through
    four files, at $20.75 and one fix round. It produced defects a specialist
    review found in twenty minutes. Both are true, and the second is an
    argument for adding a review, not for distrusting the run.
50. **An A/B of the project-lead seat, Opus 5 against Fable 5.1, on two
    goals — 2026-09-02 and 2026-09-03.** The question was whether a Fable
    project lead does better than an Opus one on quality and on cost, now
    that Fable prices cache reads at a quarter of Opus and everything else
    at double. Same charter, same plugin (`main` at c82d451), same bands,
    `--effort high`, agent teams on, one fresh clone per arm, capture off in
    the user's session-memory plugin so neither arm learned from the other.
    The full protocol, the charters, the scoring scripts and the per-arm
    results are in `~/src/ab/` on the machine that ran it; the two records
    are `~/.claude/crew/graduate-pages-v3-b7d4/` (Opus) and
    `~/.claude/crew/graduate-pages-v3-85b3/` (Fable).

    **Goal 1, simple path, `convert-keys-js`:** two new key converters with
    tests and docs. Both leads took the simple path, dispatched one sonnet
    IC, needed zero fix rounds and zero escalations, and produced
    near-identical diffs. Fable: 22 minutes, $7.07, 34 project-lead turns. Opus: 24
    minutes, $6.40, 65 project-lead turns. Too easy to separate them. It did expose
    one defect: the Fable project lead read every background agent's result through
    `TaskOutput`, which carries no usage, so its record had
    `measured_tokens: 0` and its ceiling could never fire. The ceiling and
    that count are gone (below); `Spend:` on a council entry still reads the
    notification.

    **Goal 2, full path, the `websites` monorepo:** graduate a seven-page
    static prototype into Next.js app routes, following a sibling site's
    conventions, with a fidelity criterion of under 3% pixel difference per
    page at three widths. Both arms hit the user's subscription usage limit
    once and were resumed with one identical principal message. Both
    reached a draft PR that passes every gate. Dollars are Anthropic list
    prices computed over every transcript under each arm's project
    directory by `scripts/spend.py`.

    | | Opus 5 project lead | Fable 5.1 project lead |
    |---|---|---|
    | Draft PR | #23, 106 files | #24, 118 files |
    | Arm total | $215 | $144 |
    | Project lead's own session | $113, 350 turns, peak context 827k | $38, 130 turns, peak context 481k |
    | Packages | 10 in 4 territories, parallel | 5 in 1 territory, sequential |
    | Fix rounds | 15 | 0 |
    | Reviews | 17 | 10 |
    | Decisions | 17, one council | 23, no council |
    | Escalations | 0 | 0 |
    | Independent fidelity check, worst pair | 0.30% | 2.60%, 18 of 21 at 0.00% |
    | Tests, a11y | 221 pass, clean | 249 pass, clean |
    | Record's own notification count | 1.56M | 1.21M |
    | Transcript tokens | 389M | 187M |

    **What separated them was the order of work, not the model's price.**
    Fable built the fidelity harness as package one, proved it deterministic
    against prototype-versus-prototype pairs, ported the prototype CSS as
    global CSS, and then every page passed review first time. Opus translated
    to Tailwind utilities, built the harness last, and paid fifteen fix rounds
    to converge on the same fidelity. Fable also cut half as many packages,
    kept one IC teammate across all five so the ported CSS and the harness
    were learned once, and did the project lead's work in a third of the turns. At
    Opus prices the same Fable session would have cost about $34 against its
    $38, and at Fable prices the Opus session about $93 against its $113. The
    price sheet moved a few dollars; the turn count moved the rest.

    **Neither project lead escalated the question the answer key marked as the
    principal's** — whether `/book` gets per-book routes. Both resolved it
    from precedent the same way. No judgment difference showed on the open
    questions.

    **Fable followed a rule that has a cost.** `full-path.md` step 4 spawns a
    territory at the band of its first package, so a `deep` harness put all
    five packages on opus, three of them `standard`. That is $102 of Fable's
    $144. It was probably the right trade here — zero fix rounds against
    fifteen — but nothing in the rubric said so; `band-rubric.md` now does,
    and step 8a says when to respawn instead.

    **The 2.60% pair is a real difference the harness hid.** Fable's covers
    use `next/image`, which lazy-loads, where the prototype's `<img>` is
    eager, so three below-the-fold covers render blank at 390px until
    scrolled near. Fable's harness scrolls every page end to end before
    capture, so it reported 0.00% there. Under the charter's bound, and a
    reminder that a harness the IC writes measures what the IC thought to
    measure.

    **The IC teammate reached 66% of its window without compacting.** 560
    turns, 659k tokens peak. Neither the project lead nor the IC can read that
    number, so the reuse decision was blind to it. The `PreCompact` hook now
    records a compaction into the run, and step 8a respawns after four
    packages as the proxy the project lead can count.

    **The record's spend count is an order of magnitude short.** Opus's
    record said 1.56M tokens; its transcripts held 389M, of which 232M were
    the lead's own cache reads. The lead's session and the teammates were
    never counted, and the 2M default ceiling could not have protected the
    user's limit, which fired first in both arms. The token ceiling and its
    per-agent bookkeeping are removed; `scripts/spend.py` prices the
    transcripts in dollars, and a charter `Budget:` line is the only gate.

    **Both arms left a `next start` listening on port 3002.** The first one
    served HTML pointing at chunks from an earlier build, so the stylesheet
    500'd and the independent check saw an unstyled page until the server was
    killed. `ic-contract.md` and `SKILL.md` step 14 now sweep processes.

    **One leak in the protocol.** The Fable project lead's first decision records
    that it found the Opus record and PR #23 by listing `~/.claude/crew/`,
    and that it read nothing from them. Its split, its CSS strategy and its
    harness differ enough from Opus's to make that credible, but the record
    root should have been isolated per arm. `CREW_RECORD_ROOT` now exists for
    that.

    **Inefficiencies this exposed, and what changed for each:**

    | Inefficiency | Evidence | Change |
    |---|---|---|
    | The project lead's context is the bill | 232M cache-read tokens, $116 of $215 | Review agents write their report to the record and return three lines (`review-output.md`); diffs already stay out |
    | The most expensive model writes the longest documents | 324-line spec, 273-line split, as project-lead output | A sonnet subagent drafts from the lead's outline (`SKILL.md` step 3) |
    | Fix rounds as the quality mechanism | 15 rounds vs 0, decided by harness order | Verification tool is package one; ICs run it before reporting (`full-path.md` step 1, `ic-contract.md`) |
    | Record bookkeeping by hand | hundreds of heredoc turns; the invented session id | `scripts/crew-record.py` |
    | Critic rounds on enumerations | 3 spec rounds, each one item missing from a closed list | `[Critical]` redefined; enumerations are `[Concern]` (`review-output.md`, `agents/spec-critic.md`, `SKILL.md` step 3) |
    | Plan gate round trip per package | late idle notices, no findings | Two-check approval for `standard` and `light` (`full-path.md` step 5) |
    | Package count | 10 packages vs 5 for one goal | Fewer, larger packages per territory (`full-path.md` step 1) |
    | Spend blind spots | 1.56M recorded vs 389M real | Token ceiling removed; `scripts/spend.py`, `spend.transcript`, charter `Budget:` |
    | Compaction invisible | 66% of window, unobserved | `PreCompact` hook records the compacting agent's name, `run.compactions`, respawn rule |
    | Time-versus-spend unstated | parallel cost 15 rounds; sequential cost hours | Charter `Favour:` line (`record-format.md`) |
    | Stale processes | `next start` on 3002 in both arms | Process sweep in `ic-contract.md` and `SKILL.md` step 14 |
    | Prior run visible | Fable saw Opus's record | `CREW_RECORD_ROOT` |

    **Recommendation.** Fable for project leads. On the goal that could
    separate them it was cheaper, cleaner and as faithful, and its process
    choices were the better ones. The changes above matter more than the
    model choice, because they cost more than the difference between the
    models. Two of them are unverified until a run exercises them: that
    `PreCompact` fires for an in-process teammate (T19), and that a review
    agent's write to the record root is allowed in the sandboxes that deny
    an IC's (T20).

51. **`crew-stats.py` reads every record, and it reproduces §15.50's counts
    but not its Opus dollars — 2026-09-03, T25.**
    `skills/project-lead/scripts/crew-stats.py` walks the record root and
    prints one row per run, a by-band table, a review table and the totals.
    It imports `spend.py` for the price table and the transcript pricing, so
    the two scripts cannot drift apart. It writes nothing.

    **Counts that match §15.50 exactly.** Packages 10 against 5, fix rounds
    15 against 0, reviews 17 against 10, decisions 17 against 23, councils 1
    against 0, escalations 0 against 0. Every one of those comes out of
    `state.json`, `decisions.md` and `reviews/`.

    **Dollars, and why a run's price needs an end as well as a start.**
    `spend.py`'s command line takes a start and no end, which is right for
    the run it is pricing while that run is live. It is wrong across runs: two
    goals worked in one checkout each absorb the other's transcripts, and a
    priced figure keeps growing every time anyone opens any session in that
    checkout. `spend.collect` therefore takes an optional `until`, applied at
    the entry level, and `crew-stats.py` passes each run's own end —
    `run.completed_at`, or the latest `state_changed_at` in the record. The
    command line is unchanged and still prices open-ended.

    Bounded, the Opus arm is $213.91 and the Fable arm $142.37. Open-ended
    today they are $224.29 and $144.36, against $215.39 and $144 recorded in
    §15.50. Three numbers, and none of them is wrong:

    - The **open-ended figure is an upper bound that grows**. The Opus session
      was left open after §15.50's figure was taken, and three more opus
      messages and 0.8M more one-hour cache writes landed in its transcript.
      The sonnet half is byte-identical across both measurements, which pins
      the drift to that open session. The A/B's own `~/src/ab/spend.py` now
      returns $224.29 for that arm too, so the script agrees with the tool it
      is checked against.
    - The **bounded figure is a lower bound**. It stops at the last write to
      the record, so it drops the run's own tail — the turns that open the PR
      and write the closing summary after the last `state_changed_at`. That
      tail is $10.38 for Opus and $1.99 for Fable.
    - §15.50's figure sits between them, because it was taken by hand shortly
      after each arm finished.

    Nothing distinguishes a run's own tail from the next unrelated session in
    the same checkout, so the bound is the only rule available and it
    under-counts by the tail. **Prefer the bounded figure across runs and
    treat it as a floor.** Two rules follow. Take a transcript price only
    after the session that wrote it is closed. And `run.completed_at` needs an
    owner: one of eleven records carries it, `record-format.md` does not
    document it, and nothing writes it, so a completed run has no end but its
    last state write. That is a ticket, not a change made here.

    **Per-package cost is an estimate, not a measurement.** A run's dollars
    cover the whole run, and nothing in the record attributes them to one
    package. The by-band table splits each priced run's cost evenly over its
    packages, and the header says so. Over the two priced runs the bands come
    out near each other — light $21.39, standard $23.75, deep $24.22 per
    package — which is what an even split must produce, so it says nothing
    about the bands yet. A per-package figure needs an IC's own transcript
    mapped to the package it worked, which `ic_name` and `worktrees.json`
    make possible and this script does not yet do.

    **Nine of eleven records cannot be priced.** They carry neither
    `spend.transcript` nor a checkout path, because both fields are newer
    than the runs. The script counts them everywhere else and names each one
    in a `Skipped` block. `--repo <slug>=<checkout>` supplies the missing
    path by hand, which is how the Opus arm was priced above.

    Review catch rate is not in the script. T23 defines it; one comment
    marks where it goes.

    **A code review of the script found eight defects, and the two that
    mattered were both about the shape of the data, not the code.** The
    unbounded pricing window above is one. The other is that a council entry
    can say `Spend: unmeasured`, or carry no `Spend:` line at all before its
    adjudication, and the token total then reads short with nothing to say
    so; the script now names each such entry. The rest were hardening: a
    malformed `created_at`, a `state.json` that parses to a list, a scalar
    where a list belongs, and a checkout path holding `~` — zsh does not
    expand a tilde after `=`, so the documented `--repo slug=~/path` form
    priced nothing at all until the script expanded it itself.

52. **The stale-status-claim sweep, and why the project lead owns it —
    2026-09-03 (T18).** §15.48 and §15.49 each caught a claim about what is
    built that the same session had already falsified. `CLAUDE.md` and
    `writing-standard.md` carried the rule for both. The gap was not the
    rule; nothing ran at the end, when the claims had changed.

    **The owner is the project lead, at `SKILL.md` step 12.** That is where
    it already edits the shared files a stale claim lives in, and it is the
    only seat that sees the whole diff before the PR opens.
    `crew:deliverable-reviewer` does not get an eighth check: two owners for
    one check means each one can assume the other ran it.

    **The vocabulary list lives in `writing-standard.md`**, in a
    `## Keep the status true` section, with the runnable block beside it —
    one `pattern` variable, one grep over the change's added lines, one
    `git grep` over the repo. `SKILL.md` step 12 and `full-path.md` step 9
    both point at that section. One copy of the pattern, so a term added
    later reaches every caller.

    The sweep reads the change's own diff. When the change lands a stage it
    also reads the whole repo, because §15.48's stale README sentence was
    stale for a change in another directory.

    **A run then exercised it — 2026-09-04.** The record is
    `~/.claude/crew/truncate-helper-bfa8/`: a simple-path run on a
    string-kit fixture, a Fable project lead at `--effort high`, one
    `standard` package, zero fix rounds. The charter asked for "stage 2 of
    the roadmap", a `truncate` helper. Two files carried a claim that stage 2
    was unbuilt — the fixture's `README.md` roadmap row and its `CLAUDE.md`
    line "Stage 2, `truncate`, is not yet built, so callers cut strings by
    hand." Neither file was in the IC's file set, so no IC and no package
    reviewer could have seen them. The project lead ran the sweep at step 12,
    fixed both in "Export truncate and mark roadmap stage 2 built" on
    `crew/truncate-helper-bfa8/deliverable-1`, and left the stage 3
    `slugify` rows alone: "The remaining stale-status hits are about
    slugify, which is still true." Its `decisions.md` entry "Which file
    changes belong to the project lead at integration?" cites
    `writing-standard.md`'s "Keep the status true" and both file lines.

    **The owner decision is the part the run confirms.** A claim outside
    every file set is invisible to the two reviewers that read a file set.
    Only the seat that owns the shared files finds it.

53. **The preference sweep: one batched ask between the spec and the split —
    2026-09-03, T21.** Six runs produced zero escalations. In the §15.50 A/B
    both project leads answered the one question the answer key marked as the
    principal's — whether each book gets its own route — by calling it
    precedent. §6's preference route already forbids that. Nothing made the
    project lead look for such a question at the moment asking is still cheap.

    `SKILL.md` gains step **4a**, between the spec review and the shape
    choice: read `charter.md` and `spec.md` again, list every question the
    repo cannot answer, and escalate the list as one batch.
    `autonomy-contract.md` owns the rule, under The preference sweep, and
    `record-format.md` owns the `decisions.md` entry that records the sweep
    ran, including on a run that found nothing.

    a. **A lettered step, not a renumbering.** Numbering the step `5` and
       pushing the rest down would have invalidated about thirty citations of
       a `SKILL.md` step number, most of them in this section, where they are
       evidence and must stay true. `full-path.md` already carries steps 5a
       and 8a for the same reason.

    b. **The step sits in the shared prefix.** `full-path.md` replaces
       `SKILL.md` steps 6 to 14 and runs steps 1 to 5 first, so both paths
       inherit step 4a and the rule stays in one file.

    c. **No new timeout.** An unanswered batch expires by the mechanism that
       already exists: `SessionEnd` marks the dead run `interrupted`, and
       `--resume` reopens it `blocked` on the same `escalations` entries.

    d. **A diff-wide review found four defects in the first draft**, which is
       §15.48's finding holding again. The definition of a preference question
       said any question the repo answers is a precedent question, which
       re-licensed the exact failure the sweep exists to stop — §6.2's split
       precedent and a deliberate change both look answered. The sweep blocked
       before `full-path.md` step 0's launch checks, so a full-path run would
       have interrupted the principal twice. The `decisions.md` entry recorded
       a count and never the answers. And "write one `escalations` entry per
       question" had no append command: `run set escalations` replaces the
       list, so the batch would have dropped every earlier ask.
       `crew-record.py` now has `escalation add` and `escalation answer`.

    e. **Both runs behaved as T21 asks — 2026-09-04.** Simple path on a
       string-kit fixture, a small node library with a `node --test` suite, a
       Fable project lead at `--effort high`, the plugin loaded from a local
       stack of this branch with T17 and T18.

       **The run with nothing to ask** is `truncate-helper-bfa8/`: a charter
       for a `truncate` helper. The sweep entry reads `Answer: none`, no
       preference entry reached `escalations`, and the run went to the split
       without stopping. The one question the charter left open — which
       ellipsis character — went to a council earlier in the run and was
       settled from the charter's own "never longer than maxLength"
       invariant. That is a repo answer, so the sweep was right to pass it
       over: the sweep filters for what the repo cannot say, not for what is
       merely unstated.

       **The run with one to ask** is `slugify-stage-3-fa89/`: a charter for
       a `slugify` helper that said input can carry accented letters such as
       `café` and never said what to return for them. After spec critic round
       2 the project lead ran the sweep, wrote one `escalations` entry with
       trigger "preference question with no instruction (trigger 2)" at
       2026-09-04T03:14:57Z, set `run_state: blocked`, and asked one question
       with two readings and a recommendation — before any split. The
       principal answered "strip diacritics first". The `decisions.md` entry
       carries `Questions:` and `Answer:` with that answer, and cites
       `charter.md`, `CLAUDE.md`, `README.md` and the three existing helpers
       as holding no rule on non-ASCII text. The run then split, built,
       passed both reviews with zero fix rounds, and ended `work-complete` at
       $7.23 list.

       **The ask landed where it is cheapest.** Requirement 4 and a non-goal
       both turned on the answer, and the spec critic's round-2 findings on
       them were left open until the sweep settled it. One interruption
       rewrote two spec lines; after the split it would have been a fix
       round.

54. **Both paths now put the checkout back on the branch it started on, and
    two runs proved it — 2026-09-04, T17.** §9.1 puts the simple path on the
    current checkout by design, and nothing switched it back, so the §15.47 run
    left the T8 session on the run's branch. The run now records the branch it
    found in `deliverables[].checkout_branch`, and switches back at every end,
    the `work-complete` one included. Two cases stop the switch: a dirty tree,
    which is the principal's work, and a principal who keeps the deliverable
    branch. Either case writes the reason to `deliverables[].checkout_restored`,
    and the last message names both branches, so one command undoes it.

    **Two simple-path runs, one fixture checkout.** Fable at `--effort high`,
    the plugin loaded from a local stack of this branch with T18 and T21.
    `~/.claude/crew/truncate-helper-bfa8/` records `checkout_branch: "main"`
    and `checkout_restored: true` on a `work-complete` deliverable — the
    fixture has no remote, so the principal chose `work-complete` in session.
    The checkout was on `main` and clean afterwards, and the project lead's
    last message named both branches: "The checkout is back on main", and the
    deliverable branch `crew/truncate-helper-bfa8/deliverable-1`. The second
    run, `~/.claude/crew/slugify-stage-3-fa89/`, started in that same directory
    from `main`, recorded the same two fields and ended the same way. That
    second start is T17's "a second run in the same directory starts from a
    known branch", observed rather than argued.

    **The full path has the same defect, and takes the same rule.** T17 read
    the worktrees as the reason the full path was safe. They are not: its ICs
    work in worktrees, but `full-path.md` step 3 switches the project lead's
    own checkout the same way §9.1's simple path does. No run has exercised
    the full path's restore.

    **The rule still lives in one file.** Its text is in `SKILL.md` steps 7
    and 14. `full-path.md` carries two pointers instead of a copy — one at
    step 3, to record the branch, and one at step 11, to restore it — which is
    the shape this repo uses wherever one path borrows another's step.

55. **Instruments are designed, not yet dispatched — 2026-09-04, T14.** §6.4
    gives a target repo's own investigation skills or agents a name and a
    gate: the charter's optional `Instruments:` line lists them, and only the
    project lead or a researcher may dispatch one, during scouting or
    research, never an IC. `record-format.md` owns the charter line and the
    `run.instruments_used` field that logs every dispatch. Nothing in crew
    dispatches an instrument yet — that work folds into T4's territory, per
    T14's own ticket, and stays there until a run needs one.

56. **The investigation path is designed, and five choices in it were not
    obvious — 2026-09-04, T11.** §9.5 is the section, §14 carries the five
    deviations, and `record-format.md` owns `diagnosis.md`. Nothing runs it
    yet; T12 implements it, and T31 and T32 are the two pieces it needs
    first. Recorded here is what the design decided and why, so T12 does not
    reopen it.

    **The copy is from an installed skill, not from GitHub.**
    `superpowers:systematic-debugging` at plugin version 6.3.0, commit
    `b36e0829c6d0140e93cfef2ca599b1b07d4a7797`, found on this machine under
    `~/.claude/plugins/cache/`. §14 records the commit so a re-sync compares
    against the same text. Three blocks are copied whole: the Iron Law, the
    Quick Reference table of four phases, and the Red Flags list. The rest of
    that skill is examples and rationalisation tables, which a capable model
    does not need.

    **The path is chosen at `SKILL.md` step 1, not at step 5.** §9.1's table
    is the shape choice and it runs after scouting. This choice has to come
    before scouting, because it changes what the scouts are asked. The test is
    what the charter names — a change to make, or a symptom whose cause is
    unknown. An earlier draft tested the acceptance criterion instead ("a goal
    whose criterion cannot be written yet"), which a review showed was
    self-defeating: every run that test selected would then abort on §6
    trigger 1 for the same reason. That is also why the reproduction is
    written in two stages. The charter carries the symptom at step 1; the
    failing command comes out of Phase 1, because step 1 cannot write a
    command in a repo it has not scouted.

    **A report ending needs its own verification, and it is one adversary.**
    §7 forbids a completion claim with no fresh evidence. Both review agents
    read a diff, and a run that ends at `diagnosis.md` produces none, so the
    project lead's own artifact would be its only evidence. One
    `crew:council-advocate` argues the root cause is wrong over the same
    evidence, and writes `reviews/diagnosis-adversary.md`. That is T22's
    default adversary aimed at an artifact instead of at a question, and it
    costs one sonnet call. `Outcome: fix` needs none — the fix package carries
    a normal review.

    **A report ending is §5's one exception to a deliverable holding a
    package.** It holds none, and it opens no branch, so `branch`, `base`,
    `checkout_branch` and `checkout_restored` are all `null`. §5 and each of
    those four field rows say so where they are defined. T17 landed the last
    two one commit earlier, and their text asserted that every run switches
    the checkout; this is the first ending that does not.

    **No new deliverable state.** T16's `work-complete` already reads "the
    work is complete and trusted but no PR was opened", and its `pr_url` row
    already anticipated a run that ends in a report. The only edits needed
    were to the two transition arrows and to the evidence rule: a resume
    proves a diagnosis run's `work-complete` from `diagnosis.md`'s
    `Outcome: no change`, where a blocked-push run proves it from the
    `escalations` answer. A second state would have split one meaning across
    two names for no gain.

    **The advocate may concede, and that is new.** §6.1 assigns positions on
    purpose, because agreement between agents from one base model measures
    shared priors. That argument holds for a design question, which has no
    true answer. A root cause does have one. An advocate assigned a
    hypothesis the evidence refutes, and forbidden to say so, hands the judge
    a case built on nothing — and the three cases are the judge's whole
    input. T31 adds the third report shape. This is the first place where
    crew's council rules split by question type.

    **The ruled-out list is the artifact's payload.** Evidence and a root
    cause are what the fix needs, and a run could stop there. The rejected
    hypotheses are what the *next* run needs: §6.2 reads them as precedent,
    so an empty `## Ruled out` costs the next run on the same symptom the
    councils this one already paid for. That is the same reason §8 logs a
    band promotion nobody reads until later.

    **What the design did not settle.** Whether the fix rejoins as a package
    in the same run or as a second deliverable is left to T12 — one run has
    to happen before that is anything but a guess. §9.5 says only that the
    fix goes back to §9.1's table.

57. **The review layer's catch rate: 4 of 32 package reviews sent a package
    back, and package reviews drove 5 of 17 fix rounds — 2026-09-04, T23.**
    `crew-stats.py` now prints a catch-rate table. The numbers below come from
    the thirteen records under `~/.claude/crew/`: 29 packages, 72 reviews and
    17 fix rounds. The script's review total reads 73, because one file under
    a `reviews/` directory is an acceptance checklist, which it counts as
    `other`.

    **How a catch is counted.** A review "acted" when its `Verdict:` line is
    the second of its agent's two verdict strings — `fix round needed`,
    `re-spec needed` or `re-split needed`. That line is the only statement the
    record makes, per review, about whether the review changed anything.

    | kind | reviews | acted | rate |
    |---|---|---|---|
    | package review | 32 | 4 | 12.5% |
    | spec critic | 20 | 7 | 35.0% |
    | split critic | 7 | 3 | 42.9% |
    | deliverable review | 13 | 1 | 7.7% |

    By band, package reviews act at 0.0% on `light` (1 review), 12.0% on
    `standard` (25) and 16.7% on `deep` (6). The band here is the
    **package's**, not the reviewer's: `band-rubric.md` gives a reviewer no
    band, so every one of these 32 reviews ran on sonnet.

    Two of the 72 reviews score as neither acted nor clean, and the script
    names both. `fidelity-harness-package-review-r2.md` states no verdict.
    `no-pr-terminal-state-9a32/spec-critic-r2.md` states `spec accepted`,
    which is neither of `crew:spec-critic`'s two strings — a drifted verdict,
    counted as unscored rather than silently as clean.

    **The deliverable reviewer's 7.7% is the metric failing, not the agent.**
    Nine of the thirteen deliverable reviews returned `accepted` and still
    listed tagged findings. `no-pr-terminal-state-9a32`'s listed four, and its
    own adjudication line records all four accepted and fixed in commit
    `195d823`. The verdict answers "does this block the next step", not "did
    this change the code".

    **Findings that led to a commit, counted by hand.** Five package reviews
    across the thirteen records produced a commit. They raised fourteen
    findings between them, and eleven of the fourteen led to a commit. Only
    one of the five was adjudicated down: `authors-route`'s reviewer raised
    four findings, and the project lead applied one and overruled three. The
    other four package reviews had every finding applied. The remaining 27
    package reviews changed nothing, and 24 of the 29 packages went through
    package review without one line of their code changing because of it.

    **What drove the seventeen fix rounds.** Read from the IC reports, which
    name the trigger at the top of each `## Fix round` section.

    | trigger | rounds |
    |---|---|
    | a package review finding | 5 |
    | the fidelity gate, or the project lead's own measurement | 5 |
    | the IC re-checking its own merged work | 2 |
    | a ruling the project lead reversed mid-run | 2 |
    | a lint rule that fires only after the merge | 1 |
    | not recorded | 2 |

    One of those five measurement rounds produced no commit at all:
    `home-route`'s round 2 reported the bug already fixed before the
    measurement reached the IC.

    **Against the defects found later, the package reviewer caught none.**
    §15.49's six defects came out of `no-pr-terminal-state-9a32`. That run's
    package review caught two findings and its deliverable review caught four.
    All six escapes were about what the package implied for a file it never
    touched. In §15.50's Opus arm, seven routes served one identical
    `<title>`. The deliverable reviewer found it, and wrote that no package
    reviewer could see it, because each route was a separate package. In the
    Fable arm all five package reviews returned `accepted`, and an independent
    check at 390px found the 2.60% fidelity pair afterwards.

    **The decision: nothing changes.** Both proposed changes fail against
    these numbers.

    - **A green `standard` package does not earn a skip.** Three of the five
      commit-producing package reviews sat on `standard` packages. In all
      three the package's own acceptance criterion was already green when the
      review found its defect. `submissions-route` reported "Fix applied
      before green", then took two more from review. `authors-route` was green
      on tests, lint and types after every commit. `work-complete-state`'s
      reviewer confirmed R1 through R11 before it raised its two. A green tool
      does not predict a clean review, so the skip would drop catches with no
      signal to drop them by.
    - **Opus for the package reviewer buys the wrong thing.** Every defect
      found later needed a wider scope, not a stronger reader. The highest
      value catch on the record came from a sonnet reviewer at `high` effort
      that wrote its own probe. `fidelity-harness` r1 built a 900 by 900 image
      against a 390 by 901 one, ran the harness on the pair, and demonstrated
      a false pass in the instrument. The review file records that the defect
      had survived six rounds of the harness's own use. The escapes sit
      outside one package's diff, where no model in that seat can reach them.

    So `agents/package-reviewer.md` keeps `model: sonnet`, `band-rubric.md`
    keeps its rule that a reviewer takes no band, and both paths keep the
    review. The layer that caught the cross-package class is the deliverable
    review, which already has the scope.

    **What the record could not tell me.** Four gaps, all in the record
    format rather than in the runs.

    a. **No per-finding adjudication.** Nothing states, per finding, whether
       the project lead accepted it and whether a commit followed. The
       fourteen-against-eleven count above is hand-read from IC reports and
       review prose, and it is not reproducible by a script.

    b. **Earlier review rounds are not always on disk.** `graduate-pages-v3-b7d4`
       records 15 fix rounds but holds 11 package review files, and three
       packages hold only their final round. `books-route`'s round 2 says "All
       four review findings addressed" against a review file that does not
       exist.

    c. **A verdict string can drift, and a report can be a transcript.** Three
       files in `two-string-kit-helpers-ea68` carry a project-lead transcript
       whose verdict sits mid-line, and one `spec-critic` file states `spec
       accepted` where the agent names `ready to split`. The script reads the
       first shape and flags the second. Only a review agent writing its own
       report keeps both shapes out of the record.

    d. **Two fix rounds have no recorded cause.** `titlecase-converter`'s
       round removed a dead `.toLowerCase()` after a review that found
       nothing, and `about-route`'s round 1 is absent from its report. Neither
       record says who found the defect.

58. **`run.completed_at` has an owner, and `crew-stats.py`'s `abandoned`
    disagreement was its own bug — 2026-09-04, T28.** §15.51 found the field
    unwritten, undocumented, and consulted by only one script. `crew-record.py`
    now stamps it with the current UTC time on every write that sets
    `run_state` to `complete` — the `close` command, `run state complete`, and
    `run set run_state complete` — and `record-format.md` documents it beside
    `created_at`: its consumer, the order rule against `spend.py --write`, and
    that an `interrupted` run never gets one and `--resume` never sets one.

    **The `abandoned` disagreement was `crew-stats.py`'s bug, not
    `record-format.md`'s.** `crew-stats.py`'s `run_end` treated `abandoned` as
    a terminal `run_state`, alongside `complete`. Nothing in the codebase ever
    sets `run_state` to `abandoned` — `crew-record.py`'s only writers of that
    field write `active` (`init`) or a caller-supplied string, and every
    caller that sets it to something besides `active` or `blocked` sets
    `complete`. `abandoned` is a `packages[].state` and `deliverables[].state`
    value only (design §10, §11), which `record-format.md`'s `run_state`
    table (`active`, `blocked`, `interrupted`, `complete`) already got right.
    `run_end` now checks only `complete`.

    **A live simple-path run, `truncate-stage-2-efa7`.** Opus 5 at
    `--effort high`, plugin loaded from this ticket's worktree, against the
    string-kit fixture. `state.json`'s `run` block ended:

    ```json
    "run_state": "complete",
    "completed_at": "2026-09-04T13:41:11Z",
    "spend": {
      "transcript": {
        "measured_at": "2026-09-04T13:41:11Z",
        "total_tokens": 5208784,
        "usd_list_price": 4.87
      }
    }
    ```

    `completed_at` and `spend.transcript.measured_at` land in the same
    second here, because `SKILL.md`'s closing steps run `close` immediately
    before `spend.py --write` with no other work between them — the order
    rule holds even when the two timestamps round together.
    `scripts/crew-stats.py --record-root <this run's root>` priced it with no
    open-ended-cost skip line:

    ```
    run                    pkgs  fixes  promos  decis  councils  escal  compact  reviews   usd
    truncate-stage-2-efa7     1      0       0      7         0      0        0        3  4.87
    ```

59. **The simple path is its own reference now, and a run read it — 2026-09-04,
    T27.** `SKILL.md` had sat at the writing standard's 200-line cap since T18,
    and each new rule was paid for with a sentence that was not a rule. Steps 6
    to 14 moved to `skills/project-lead/references/simple-path.md`. `SKILL.md`
    keeps the shared prefix — the reference list, steps 1 to 5 with 4a, and the
    shape table — and its body is 96 lines. Both paths are now reference files
    that step 5 routes to, which is the shape item 30a chose for the full path.

    a. **The step numbers did not move.** `simple-path.md` starts at step 6 and
       ends at step 14, so about thirty citations of a `SKILL.md` step number
       stay true. What changed is the file name in front of the number:
       `full-path.md`, `record-format.md`, `writing-standard.md` and
       `docs/tickets.md` now cite `simple-path.md` for steps 7, 12 and 14, and
       `SKILL.md` for steps 1 and 4. This section keeps its own citations
       unedited — they are dated evidence, and item 53a's reason for a lettered
       step applies to renaming them as well.

    b. **Three sentences came back.** "A finding is a claim, not a verdict"
       (step 4), "Your output is the run's most expensive" (step 3) and "Your
       own context is the most expensive place to work" (after the step 5
       table) were all cut for space and were in no file the project lead reads
       at runtime. All three sit in the prefix, which is where the decisions
       they govern are made. The other cuts stay pointers, because their rules
       have owners: `autonomy-contract.md`, `record-format.md` and
       `writing-standard.md`.

    c. **`writing-standard.md` rule 4 now has three numbers, not one.** 200
       lines is a target for a `SKILL.md` body, 500 is the limit the skill
       guidance sets, and a reference file has no cap because it loads only
       when a step sends the reader to it. The old rule read as one hard cap,
       and a hard cap is what made a new rule cost an old sentence.

    d. **The run read `simple-path.md` and never opened `full-path.md`.**
       `truncate-stage-2-0722/`, an Opus 5 project lead at `--effort high` on
       the string-kit fixture, with the plugin loaded from this branch. It
       reached draft PR 2 on the fixture repo in 19 minutes and 92 turns, with
       zero escalations, zero fix rounds, zero re-specs and $6.27 at list
       price. `checkout_restored` is `true`. The transcript holds three tool
       calls naming `simple-path.md` — one `cat` of the whole file, and two
       later citations of its steps 11 and 12 — and none naming
       `full-path.md`.

    e. **The lead read every reference up front, before step 5 routed it.**
       The `cat` of `simple-path.md` sits in the same command as
       `autonomy-contract.md` and `band-rubric.md`, six minutes before the
       shape table was reached. So the split's saving on this run was the file
       it did not read, not a delayed read of the one it did. A project lead
       that front-loads its references pays for both path files unless the
       route comes first, and T26's A/B is the next thing to measure that
       against.

61. **The IC owns the red commit, and the project lead re-runs it — 2026-09-04,
    T32.** §7's table has a fourth row: a new test proves nothing until the
    criterion fails at the commit that adds it. `ic-contract.md` owns the step
    that produces the evidence, and both path files own the check that reads
    it — `simple-path.md` step 9 and `full-path.md` step 6, each beside the
    "criterion passes on a fresh run" check it pairs with.

    **Why the IC, and not the project lead at dispatch.** The ticket offered
    both. A project lead that runs the criterion before the IC starts runs it
    against a test file that does not exist yet, so the failure it records is
    a missing path, not a reproduced defect. That failure is satisfied by any
    test the IC later writes, which is the hole the row exists to close. The
    IC is the only party that can run the criterion at the moment the test
    exists and the fix does not. The "an IC cannot fake it" argument for the
    other owner survives anyway: the IC's report is a claim, and the project
    lead runs the criterion at the sha itself, as §7 requires of every claim.

    **No `state.json` field.** The red commit is in `git log`, and the failing
    output goes in the IC's report. `record-format.md`'s `reports/` entry says
    so. A field would hold a claim the project lead re-runs anyway.

    **Two criteria are exempt.** A reviewer checklist for an instruction
    package is not executable. The investigation path's reproduction already
    failed before dispatch, and `diagnosis.md`'s `## Reproduction` holds that
    output — §9.5 said this before the row existed.

    a. **A live simple-path run followed every half of the rule.**
       `encodequery-skip-nullish-7e8f`, an Opus 5 project lead at
       `--effort high` with a Sonnet 5 IC, plugin loaded from this ticket's
       worktree, against the string-kit fixture. The goal was a bug fix with
       a new test: `encodeQuery` encoded a `undefined` or `null` value as
       literal text. Each of the three new rules reached the run without a
       prompt. `split.md`'s acceptance criterion ended "and the new test
       fails at the red commit". The IC's plan named a red commit, and its
       report carried the sha and the failing output the report contract now
       asks for. The project lead ran the check itself:

       ```
       git -C $REPO switch --detach 864cb73 -q
       cd $REPO && npm test ...
       node -e '...' ; echo "cmd1 exit=$?"
       git -C $REPO switch -q crew/encodequery-skip-nullish-7e8f/deliverable-1
       ```

       ```
       ℹ tests 11
       ℹ pass 10
       ℹ fail 1
       cmd1 exit=1
       crew/encodequery-skip-nullish-7e8f/deliverable-1
       ```

       The package reviewer then ran the same check its own way — a
       disposable `git worktree` at `864cb73`, so the reviewed tree stayed
       where it was — and got the same failure. That is the safer procedure
       where it works, and it is not what `ic-contract.md` asks for, because
       a fresh worktree holds no installed dependencies: in a repo that needs
       an install, the criterion would fail there for a reason that is not
       the bug.

    b. **The rejection is proved against a seeded record, not against that
       run.** A live run cannot be made to produce a package whose new test
       passed from the start without telling the IC to break its own
       contract, so the negative case was seeded: a clone of the fixture on
       `crew/seed-t32/d1`, a "red commit" `3a44d62` whose added test asserts
       behaviour the unfixed helper already had, a fix commit `14ded5e`, and
       a report claiming the criterion failed at `3a44d62`. Running
       `simple-path.md` step 9 over it: the criterion passes at the branch
       head, and at `3a44d62` it exits 0 with `pass 4, fail 0`. The step
       rejects the package there. Nothing about the diff looks wrong, which
       is why a reviewer was never the thing that caught it.

    c. **The check is per criterion, not per test.** The live run's red
       commit held two test blocks, and only one of them was red — the IC
       said so in its report, unprompted. `npm test` fails when any one test
       fails, so the criterion still failed and the package still passed the
       check. A test added green inside a red commit is invisible to this
       row. Splitting a criterion per test block would cost a suite run per
       block, which buys too little for the price.

    d. **The rule had to reach `agents/ic.md`, which the code review caught.**
       That file's loop ended a test-first cycle with one `Commit` after the
       code went green, so an IC that followed its own definition would have
       produced no red commit at all and earned a fix round for it. The loop
       now commits the criterion's failing test alone first. The live run
       still produced a red commit because `ic-contract.md` reaches the IC in
       the spawn prompt and it is the contract that governs — but a
       split-pane teammate reads the agent body in place of its default
       prompt (§15.20d), so the two had to agree.

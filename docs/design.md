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
| **Advocate** | unnamed subagent (`general-purpose`) | sonnet | one position |
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
deliverable is an instruction file: `CLAUDE.md`, a `.claude/rules/` file, a
`SKILL.md`, or an agent definition.

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

It covers all four container types this IC owns directly, with no hand-off to
another skill for two of the four.

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
2. Dispatch one advocate per position, in parallel, in a single batch. Each is
   told: argue **for** your position, gather cited evidence from code and docs,
   make the strongest case, and name the strongest objection to your own side.
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
The `TeammateIdle` hook enforces this (section 13.1).

**Blocking rule.** A pattern choice that changes the decomposition or an
interface contract blocks — the project lead cannot split the work without it.
Any other pattern choice is batched: the project lead does everything that
does not depend on the answer first, then asks once.

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
5. The spend ceiling is crossed.
6. A package reached the fix-round breaker at the top band.

Everything else the project lead settles itself and records — unless it judges
that getting it wrong would take the work off the rails, in which case it asks
anyway.

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
- Each run has a spend ceiling. Crossing it escalates.

Spend is measured from the `usage` block on each subagent's completion
notification, which carries `total_tokens` per agent. A teammate's spend is
not reported this way, so the project lead records an estimate for teammates
and marks it as such. This is a known weakness of the ceiling: it undercounts
exactly the agents that cost the most. Treat the first runs' numbers as a
floor.

One `crew:ic` definition serves all three bands, because a spawn-time `model`
overrides the definition's frontmatter (section 12).

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
  value is `draft-pr-opened`, not `integrated` — no deliverable state ever
  means the deliverable reached `main`. A re-plan cares about the first
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
| 5 | Full path: worktrees, territories, merges, promotion | One multi-package goal reaches a draft PR with zero prompts |
| 6 | Council + routing + `decisions.md` | An architecture-moving question is resolved and audited without a prompt |

### 13.1 Hooks

`crew` ships its own `hooks/hooks.json`, the way `auto-approve` and
`session-memory` do. The restriction found in section 12 is on **agent
frontmatter** `hooks`, which is ignored for teammates and banned for plugin
agents. A plugin's own hook file has no such limit.

Plugin hooks are active in every session, so the deciding question for each one
is how often it fires when no crew run is happening.

| Hook | Fires | Job | Stage |
|---|---|---|---|
| `TeammateIdle` | only when a teammate goes idle — never in a session with no teammates | Exit 2 to reject an IC that goes idle without a green test run, a written report, or a stated assumption — probed, §15.29. Keeps it working, once per package. | **5** |
| `SessionEnd` | once per session; a guard clause exits at once when no crew record exists | **Writes only.** Marks the run interrupted in `state.json` and lists its worktrees as orphaned. Deletes nothing. | 5 |
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

**`TeammateIdle` ships in stage 5, not stage 2, with `SessionEnd`.** Exit 2
blocks the idle — probed, §15.29 — so the two hooks are halves of one
mechanism. The hook blocks an idle while a package is `in-flight`. Only
`SessionEnd`'s `run_state: interrupted` marks a dead run's packages as no
longer in flight. Shipping the blocking half alone would leave a single
crashed run blocking teammates in every future session on the machine, with no
diagnosis path.

Four rules for it, all cheap, none optional:

- **Scope to the idling teammate, and fail open.** If the payload cannot identify
  which teammate is idling, exit 0. A coarse "any package in flight" rule
  livelocks a multi-IC run — an IC that legitimately finished is told to keep
  working because a *different* IC is still busy, and it has nothing to do.
- **Check the report file on disk**, not a `state.json` field. The project
  lead owns `state.json`, so an IC cannot unblock itself through it.
- **Ship a kill switch** — `CREW_DISABLE_IDLE_HOOK=1` — and a staleness cutoff
  that ignores any run whose `state.json` has not been written for hours.
- **Refuse at most once per package.** The block is a nudge, not a gate: the
  probe measured 11 refusals in 27 seconds, then the teammate idled anyway
  (§15.29). A hook that refuses the same teammate again and again burns tokens
  and still loses. Refuse once, write the reason, and let the second idle pass
  to the project lead's own verification (§7).

**Probed 2026-08-31 (T5).** Exit 2 blocks the idle, the stderr line reaches the
teammate word for word, and the payload names the idling teammate. §15.29
holds the payload, the retry behavior, and what each answer changes.

---

## 14. Deviations from superpowers

Copied as-is, so it stays easy to re-sync: the `Interfaces` block, the
`Global Constraints` block, task right-sizing, the no-placeholders list, the
verification table, the adjudication procedure, the worktree cleanup guard.

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
   `writing-standard.md` is crew's own, written directly for the four
   container types this plugin's IC owns — the container-routing table, the
   reader-context section, the frontmatter block, the revise-down rule, and
   the final checklist. It is not split from, or a pointer into, any other
   repo's internal standard. `crew` keeps no copy of anything external and
   carries no repo-specific layer to strip out, so it can ship and sync on
   its own.
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
   find a *report* on disk before it lets an IC idle, not a plan (line
   842-843; `record-format.md` lines 36-37). The two collide by construction.
   The hook was stage 5 and unprobed when this item opened (probed 2026-08-31,
   §15.29), so neither
   file could resolve this alone; `ic-contract.md` only names the post-plan
   wait as an expected pause, not an idle to fix.

   Decided 2026-08-29: the record carries the gate. `record-format.md` adds
   `plan_approved_at` per package, `null` until the project lead's
   go-ahead. The `TeammateIdle` check lets an idle pass while
   `plans/<id>.md` exists and `plan_approved_at` is `null`. The collision
   dissolves: a post-plan wait is visible in the record, not inferred.
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
    checks for a report file on disk, not a message (line 842-843) — would
    reject such an IC's idle forever, with no way for it to comply.
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
    mechanism stands. §15.29 later probed it and found the block bounded:
    it holds for a number of refusals, then lets the teammate idle. **Native plan approval is not a review gate**: a
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
29. **`TeammateIdle`: exit 2 blocks the idle, but only for a while — probed
    2026-08-31 (T5).** §13.1's probe ran on Claude Code 2.1.252, in an
    interactive session inside `tmux` with
    `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. A temporary hook dumped its
    stdin, wrote `crew probe: refusing idle` to stderr, and exited 2. One
    teammate, `probe-bot`, was spawned with one instruction: reply `READY` and
    stop. The registration was removed as soon as the run ended.

    The three questions, answered:

    1. **Exit 2 does block the idle.** `probe-bot` replied `READY`, tried to
       idle, and was re-invoked instead. The hook fired 11 times between
       21:53:53Z and 21:54:20Z.
    2. **The stderr line reaches the teammate, word for word.** `probe-bot`
       quoted `crew probe: refusing idle` back to its project lead and named
       the hook as the reason it could not stop. The session transcript carries
       the string 7 times. So the hook's stderr is the whole message an IC
       gets: it must say what is missing and where to write it.
    3. **The payload names the idling teammate.** Every dump carried
       `teammate_name` (`probe-bot`), `team_name` (`session-<parent sid>`),
       `session_id`, `cwd`, `transcript_path`, `permission_mode` and
       `prompt_id`. The fail-open fallback in §13.1 stays as a guard, but the
       scoping rule it protects is buildable as designed: name the teammate,
       find its package, read its report file.

    **The finding that changes the design: the block is not permanent.** After
    11 refusals in 27 seconds, `probe-bot` idled anyway, on the same second as
    the 11th firing. The refusals also tightened, from 6 seconds apart to 1.
    Whether 11 is a fixed cap, a time budget, or something else is not
    probed — the run measured one number, once.

    Two consequences for stage 5 (T7):

    - **A refusal is a nudge, not a gate.** The hook cannot hold an IC that has
      nothing left to do. §13.1 now caps it at one refusal per package. The
      real gate stays where §7 already puts it: the project lead verifies each
      IC's claim against `git` and the report file, and an IC that idles with
      no report fails that check whether the hook stopped it or not.
    - **A refused IC with no work left burns tokens.** Each refusal re-invokes
      the model. Eleven refusals cost eleven turns to reach the same idle. That
      is the whole argument for the cap.

    One thing the probe did not settle: `probe-bot` messaged its project lead
    to ask that the hook be removed. The project lead refused, because the hook
    is config owned by another session. That is the right answer, and it is
    luck rather than design — no rule in `ic-contract.md` tells an IC what to
    do when a hook, not a reviewer, is what blocks it. T7 should say.

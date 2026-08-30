# Record format

One directory per goal, outside the target repo (design §4):

```
~/.claude/crew/<goal-slug>/
├── charter.md        goal + falsifiable acceptance criterion
├── spec.md           the spec the project lead wrote after scouting
├── plan.md           deliverables → packages, with interfaces and bands
├── state.json        deliverables, per-package state, band history, spend, escalations
├── decisions.md      every judgment call, with its citation, confidence, and timestamp
├── worktrees.json    IC name → worktree path → branch → session ids → orphaned
├── reports/          one report per package, written by its IC
├── plans/            one plan per package, written by its IC
└── reviews/          raw critic and reviewer output
```

Every relative path named in `state.json` resolves against this directory
root. `worktrees.json`'s `worktree` field is the one path that is already
absolute.

## `reports/`, `plans/`, and `reviews/`

Three directories hold per-run output. Each has one writer and a fixed
naming convention. Do not mix their contents.

- **`reports/`** — one file per package, `reports/<id>.md`. Only that
  package's own IC writes here. `state.json`'s `report_path` for a package
  always equals `reports/<id>.md`.
- **`plans/`** — one file per package, `plans/<id>.md`. The IC writes its
  implementation plan here and waits for the project lead's go-ahead (design
  §9.2 step 3, §12's plan-approval fallback). `state.json`'s `plan_path`
  always equals `plans/<id>.md`. This stays separate from `reports/` because
  `plan.md` at the record root is the project lead's own decomposition — an IC
  told to "write its plan into the record" with no named target could
  overwrite it — and separate because §13.1's `TeammateIdle` check must find a
  *report* on disk before it lets an IC go idle, not a plan.
- **`reviews/`** — raw output from every critic and reviewer, one file per
  review, never overwritten by a later one: `reviews/<id>-package-review-r<n>.md`
  (`<n>` is the fix round, from `fix_rounds_used`),
  `reviews/<deliverable-id>-decompose-critic-r<n>.md` (`<n>` here counts
  re-plans of this deliverable, since design §10's re-plan can rerun the
  critic on the same deliverable),
  `reviews/<deliverable-id>-deliverable-review.md`. Design §9.2 allows up to
  five review rounds per package, and a goal can hold several deliverables —
  a shared filename per kind would let a later round, a later deliverable,
  or a later re-plan silently destroy an earlier review, which is this run's
  only audit trail. The project lead writes every file under `reviews/`, from the
  reviewer's returned findings — a reviewer agent has no `Write` tool and
  returns its findings as a tool result.

The project lead never has to parse a review to find a report or a plan. It reads
`report_path` or `plan_path` from `state.json` and opens that file directly.

## Goal-slug uniqueness

The project lead appends a short random suffix to every goal slug at creation
time, always — not only on a collision:

```
<kebab-case-slug>-<4 lowercase hex chars>
```

Example: `add-request-logging-a1b2`. The project lead generates the suffix
once, when it creates the record directory, and never regenerates it. Design
§1 runs several goals in parallel sessions with no shared lock, so a
fixed-format slug with no randomness lets two similar goals collide. A random
suffix avoids the collision without needing a lock or an existence check.

## `state.json`

Top-level keys: `goal`, `goal_slug`, `deliverables`, `run`, `packages`.

### Deliverables

One entry per deliverable (design §5):

| Field | Meaning |
|---|---|
| `id` | referenced by each package's `deliverable` field |
| `branch` | the deliverable branch every package's IC branches from (design §9.3) |
| `base` | the commit sha at the deliverable branch's head when it was created — the `<base>` in `git -C <wt> log <base>..HEAD` (design §10.1) |
| `state` | one of `pending`, `in-flight`, `draft-pr-opened`, `abandoned`. `draft-pr-opened` is a deliverable's own terminal state, not `integrated` — design §9.3 and §11 stop at opening a draft PR, so no crew state ever means a deliverable reached `main`. |
| `state_changed_at` | ISO-8601 UTC timestamp of this deliverable's last `state` transition |
| `pr_url` | the draft PR opened in `draft-pr-opened` (design §9.3); `null` until then |

Deliverables run sequentially (design §5), so at most one is ever
`in-flight`.

### Per-package fields

| Field | Meaning |
|---|---|
| `id` | the package's identity. Used to name its files: `reports/<id>.md`, `plans/<id>.md`, `reviews/<id>-package-review-r<n>.md`. |
| `deliverable` | the `id` of the deliverable this package belongs to, from the `deliverables` list above |
| `territory` | the file-tree region this package's IC owns (design §5) |
| `state` | one of `pending`, `in-flight`, `integrated`, `abandoned`. See State transitions below. |
| `state_changed_at` | ISO-8601 UTC timestamp of this package's last `state` transition |
| `band` | one of `light`, `standard`, `deep`. `band-rubric.md` is the authority for what a band means and when to promote one; this field only stores the current value. |
| `band_history` | a list of `{predicted, actual, cause, at}` entries: one when the band is first predicted, and one more per promotion after that (design §8). `at` is an ISO-8601 UTC timestamp. |
| `file_set` | the package's declared, disjoint file list (design §5 invariant 2). `decompose-critic` checks disjointness against this field. |
| `interface_contract` | `{consumes, produces}` with exact signatures (design §5 invariant 3). The only channel between isolated ICs. |
| `acceptance_criterion` | the executable test or reviewer checklist that proves the package is done (design §5 invariant 1). Also what makes a respawn idempotent after a crash (design §10.1). |
| `fix_rounds_used` | integer, capped at five (design §9.2). After a crash, design §10.1 respawns an IC from its worktree. Without this persisted, the round count resets and the breaker never fires. |
| `ic_name` | the name of the teammate assigned to this package. Cross-references `worktrees.json`, which maps this name to a worktree path. Without it, nothing maps a package back to the worktree that must verify it. |
| `plan_path` | always `plans/<id>.md`. The IC's plan, written before its report (design §9.2 step 3, §12). |
| `plan_approved_at` | ISO-8601 UTC timestamp of the project lead's go-ahead on the plan (design §9.2 step 3); `null` until then. While it is `null` and `plans/<id>.md` exists, the IC's post-plan idle is an expected pause — the `TeammateIdle` check (design §13.1) lets it pass (design §15.8). |
| `report_path` | always `reports/<id>.md`. Points into `reports/`. |

### State transitions

```
pending ──▶ in-flight ──▶ integrated   (terminal)
   │             │
   └────┬────────┘
        ▼
    abandoned                          (terminal)
```

- `pending → in-flight`: the project lead dispatches an IC for the package.
- `in-flight → integrated`: the package's diff merges and passes review.
- `pending → abandoned` or `in-flight → abandoned`: a re-plan drops the
  package, or the fix-round breaker parks it (design §9.2, §10).
- `integrated` and `abandoned` are both terminal. Neither has an outgoing
  transition (design §10). Correcting integrated work never revises the same
  record — it creates a new package in `pending`.

A deliverable follows the same shape, with `draft-pr-opened` in place of
`integrated`:

```
pending ──▶ in-flight ──▶ draft-pr-opened   (terminal)
   │             │
   └────┬────────┘
        ▼
    abandoned                              (terminal)
```

- `pending → in-flight`: the project lead dispatches the deliverable's first
  package.
- `in-flight → draft-pr-opened`: every package integrates and the project lead
  opens the draft PR (design §9.3).
- `pending → abandoned` or `in-flight → abandoned`: a re-plan drops the
  deliverable (design §10).

These arrows are **transitions**: one-way project lead decisions. A
**reconciliation** is different — after a crash, design §10.1 rewrites
`state.json` to match git, and that correction may move a wrongly recorded
value in either direction, including out of a mistaken `integrated` or
`draft-pr-opened`.

### At creation

A new package starts `pending`, with `band_history: []`, `fix_rounds_used: 0`,
`ic_name: null`, and `plan_approved_at: null`. `plan_path` and `report_path`
name files that do not exist yet. On the simple path (design §9.1) the project lead never writes
`worktrees.json`: there is one package, no territory, and `ic_name` stays
`null` for the run.

### Per-run fields (inside `run`)

| Field | Meaning |
|---|---|
| `run_state` | one of `active`, `blocked`, `interrupted`, `complete`. See `run_state` transitions below. |
| `session_ids` | a list, not a single id. The project lead's own session id, appended to on every `--resume`, for the same reason as `worktrees.json`'s `session_ids` below. |
| `spend` | `{ceiling, measured_tokens, estimated_tokens, council_tokens, by_agent}`. See Spend below. |
| `escalations` | a list of questions the project lead asked the human (design §6 triggers). See Escalations below. |

### `run_state` transitions

| From | To | Trigger |
|---|---|---|
| `active` | `blocked` | the project lead hits an escalation trigger (design §6) |
| `blocked` | `active` | the human answers; the project lead records it in `escalations` |
| `active` or `blocked` | `interrupted` | `SessionEnd` fires on a crash (design §13.1) |
| `interrupted` | `blocked` | `--resume`, when an `escalations` entry has no `answer` yet |
| `interrupted` | `active` | `--resume`, when no `escalations` entry is missing an `answer` |
| `active` | `complete` | the project lead finishes the run |

### Spend

Design §8 requires a teammate's spend to be recorded as an **estimate**,
marked as such, because it is not reported the way a subagent's is; design
§6.1 requires council spend as its own line item, expected to be the
largest in a run.

| Field | Meaning |
|---|---|
| `ceiling` | the run's spend ceiling (design §8). Crossing it escalates. |
| `measured_tokens` | sum of `total_tokens` from subagent completion notifications (design §8) |
| `estimated_tokens` | the project lead's estimate of teammate spend, which is not reported this way |
| `council_tokens` | tokens attributed to council advocacy and adjudication (design §6.1) |
| `by_agent` | a list of `{agent, total_tokens, measured}`. `total_tokens` here is design §8's own per-agent name; `measured` is `false` for a teammate's estimate. |

### Escalations

| Field | Meaning |
|---|---|
| `trigger` | which design §6 trigger fired |
| `question` | what the project lead asked |
| `asked_at` | ISO-8601 UTC timestamp |
| `answer` | `null` until the human responds; a non-`null` value flips `run_state` from `blocked` back to `active` |

### Worked example

One run, two packages, in different states:

```json
{
  "goal": "Add structured request logging",
  "goal_slug": "add-request-logging-a1b2",
  "deliverables": [
    {
      "id": "deliverable-1",
      "branch": "crew/deliverable-1",
      "base": "a1b2c3d",
      "state": "in-flight",
      "state_changed_at": "2026-08-24T14:05:00Z",
      "pr_url": null
    }
  ],
  "run": {
    "run_state": "active",
    "session_ids": ["sess-3f9a"],
    "spend": {
      "ceiling": 5000000,
      "measured_tokens": 812000,
      "estimated_tokens": 150000,
      "council_tokens": 0,
      "by_agent": [
        { "agent": "decompose-critic", "total_tokens": 210000, "measured": true },
        { "agent": "ic-logging-middleware", "total_tokens": 0, "measured": false }
      ]
    },
    "escalations": [
      {
        "trigger": "preference question with no instruction",
        "question": "Should log level names be lowercase or SCREAMING_CASE?",
        "asked_at": "2026-08-24T15:02:00Z",
        "answer": "lowercase, to match the existing config file's convention"
      }
    ]
  },
  "packages": [
    {
      "id": "logging-middleware",
      "deliverable": "deliverable-1",
      "territory": "src/middleware",
      "state": "integrated",
      "state_changed_at": "2026-08-24T16:40:00Z",
      "band": "standard",
      "band_history": [
        { "predicted": "standard", "actual": "standard", "cause": null, "at": "2026-08-24T14:10:00Z" }
      ],
      "file_set": ["src/middleware/logging.ts", "src/middleware/logging.test.ts"],
      "interface_contract": {
        "consumes": [],
        "produces": ["export function requestLogger(req: Request): void"]
      },
      "acceptance_criterion": "npm test -- src/middleware/logging.test.ts exits 0",
      "fix_rounds_used": 1,
      "ic_name": "ic-logging-middleware",
      "plan_approved_at": "2026-08-24T14:25:00Z",
      "plan_path": "plans/logging-middleware.md",
      "report_path": "reports/logging-middleware.md"
    },
    {
      "id": "logging-config",
      "deliverable": "deliverable-1",
      "territory": "src/config",
      "state": "in-flight",
      "state_changed_at": "2026-08-24T16:05:00Z",
      "band": "deep",
      "band_history": [
        { "predicted": "standard", "actual": "standard", "cause": null, "at": "2026-08-24T14:10:00Z" },
        { "predicted": "standard", "actual": "deep", "cause": "BLOCKED: log level schema is a new interface other packages depend on", "at": "2026-08-24T15:50:00Z" }
      ],
      "file_set": ["src/config/logging-config.ts"],
      "interface_contract": {
        "consumes": ["export function requestLogger(req: Request): void"],
        "produces": ["export type LogLevel = \"debug\" | \"info\" | \"warn\" | \"error\""]
      },
      "acceptance_criterion": "npm test -- src/config/logging-config.test.ts exits 0",
      "fix_rounds_used": 2,
      "ic_name": "ic-logging-config",
      "plan_approved_at": "2026-08-24T16:20:00Z",
      "plan_path": "plans/logging-config.md",
      "report_path": "reports/logging-config.md"
    }
  ]
}
```

`logging-config`'s `band_history` shows both cases the table above
describes: the initial prediction, then a promotion with its cause.

## `worktrees.json`

IC name → worktree path → branch → `session_ids` → `orphaned`.

**`session_ids` is a list, not a single id.** Design §13.1 makes the session
id the only proof of worktree ownership, but `--resume` runs in a *new*
session with a *new* id. If resume overwrote the field, ownership matching
would fail on the very first resume — the exact case the field exists to
serve. Resume appends; it never overwrites. `state.json`'s `run.session_ids`
follows the same append-only rule, for the same reason.

**`orphaned`** is a boolean. `SessionEnd` (design §13.1) sets it `true` for
every worktree the dying run registered. `--resume` (design §10.1) reads it
to decide which worktrees to prune, and clears it once a worktree is
reconciled.

### Worked example

```json
{
  "ic-logging-middleware": {
    "worktree": "~/.claude/worktrees/crew/logging-middleware",
    "branch": "crew/logging-middleware",
    "session_ids": ["sess-a001"],
    "orphaned": false
  },
  "ic-logging-config": {
    "worktree": "~/.claude/worktrees/crew/logging-config",
    "branch": "crew/logging-config",
    "session_ids": ["sess-b002", "sess-b003"],
    "orphaned": false
  }
}
```

`ic-logging-config` shows a resumed IC: two session ids because the worktree
survived a crash and was resumed once.

## `decisions.md`

Every entry records the question, its route, the answer, either the exact
instruction that resolved it or the reasoning that produced it, a confidence
level, and a timestamp. `Route` is one of `precedent`, `council`,
`preference` (design §6 capitalizes these only as prose labels; the record's
own values are lowercase, as design §4's worked example shows). `Confidence`
is one of `high`, `medium`, `low`.

Design §4's worked example, with a `Timestamp` line added:

```markdown
## Should the version bump be part of package 2?
Route: precedent
Answer: No — the project lead bumps versions at integration.
Citation: CLAUDE.md "Development Workflow" step 3 requires both plugin.json and
marketplace.json to change, which no two packages can own disjointly.
Confidence: high
Timestamp: 2026-08-24T14:32:00Z
```

An entry with high confidence and no citation is a defect.

## Authority rule

`state.json` is authoritative for the plan: which packages exist, their bands,
file sets, and contracts. The worktrees are authoritative for progress: what
actually landed, proven by `git log` and `git status`, not by the record
(design §4, §10.1). The project lead writes `state.json` after **every** state
transition, never batched, so a crash loses at most one transition.

---

## Name inventory

Every name this file defines, with what consumes it.

**Layout entries (design §4, this file's directory tree)**
- `charter.md` — consumer: stage 4 (project lead writes it after scouting)
- `spec.md` — consumer: stage 4 (project lead writes it); Task 11 (copied into the PR body)
- `plan.md` — consumer: stage 3 (`crew:decompose-critic` and the `plan.md` format)
- `state.json` — consumer: stage 4 (project lead loop); stage 5 (recovery, design §10.1)
- `decisions.md` — consumer: stage 6 (council + routing); Task 11 (copied into the PR body)
- `worktrees.json` — consumer: stage 5 (full path: worktrees, merges, recovery)
- `reports/` — consumer: Task 6 (`ic-contract.md` report contract); Task 9 (`crew:package-reviewer` reads a package's report)
- `plans/` — consumer: Task 6 (`ic-contract.md`, IC plan-approval step); Task 7 (`crew:ic`, design §9.2 step 3, §12)
- `reviews/` — writer: the project lead, from each reviewer's returned findings. Consumer: Task 9 (`crew:package-reviewer` output); stage 3 (`decompose-critic` output); stage 4 (`crew:deliverable-reviewer` output)

**`state.json` top-level keys**
- `goal` — consumer: stage 4 (project lead records the original goal text); Task 11 (PR body)
- `goal_slug` — consumer: stage 4 (record directory name); this file's Goal-slug uniqueness rule
- `deliverables` — consumer: stage 5 (per-deliverable integration and recovery, design §9.3, §10.1)
- `run` — consumer: stage 4/5 (project lead loop); stage 6 (spend, escalations)
- `packages` — consumer: stage 4 (project lead dispatch loop); stage 5 (recovery, design §10.1)

**`state.json` `deliverables` entry fields**
- `id` (deliverable) — consumer: `packages[].deliverable` cross-reference; `reviews/<deliverable-id>-*` filenames
- `branch` (deliverable) — consumer: stage 5 (merge target, design §9.3)
- `base` — consumer: stage 5 (recovery, `git log <base>..HEAD`, design §10.1)
- `state` (deliverable) — consumer: stage 5 (integration and re-plan, design §9.3, §10); shares `pending`/`in-flight`/`abandoned` with a package's `state`, but not `integrated`
- `state_changed_at` (deliverable) — consumer: a human auditing the record's timeline; stage 6
- `pr_url` — consumer: stage 4 (draft PR opened in `draft-pr-opened`, design §9.3); Task 11

**`state.json` per-package fields**
- `id` — consumer: this file's `reports/<id>.md`, `plans/<id>.md`, `reviews/<id>-package-review-r<n>.md` naming; stage 3 (`decompose-critic` identifies packages)
- `deliverable` — consumer: stage 5 (per-deliverable integration, design §9.3); cross-references `deliverables[].id`
- `territory` — consumer: stage 5 (one IC dispatched per territory, design §5)
- `state` — consumer: stage 4 (project lead loop); stage 5 (re-planning and recovery, design §10)
- `state_changed_at` — consumer: a human auditing the record's timeline; stage 6
- `band` — consumer: Task 5 (`band-rubric.md` defines what each value means and when to promote)
- `band_history` — consumer: Task 5 (band-rubric.md's promotion-logging rule); stage 5 (promotion on `BLOCKED`/exhausted fix rounds/idle)
- `file_set` — consumer: Task 7 (`crew:ic` self-review checks its diff against this); stage 3 (`decompose-critic` disjointness check)
- `interface_contract` — consumer: stage 3 (`decompose-critic` type-consistency check); Task 7/Task 8 (IC spawn prompt carries it, design §9.2 step 2)
- `acceptance_criterion` — consumer: Task 6 (`ic-contract.md`, tells the IC when to stop); Task 9 (`crew:package-reviewer` checks work against it)
- `fix_rounds_used` — consumer: stage 5 (the fix-round breaker, design §9.2 step 6)
- `ic_name` — consumer: `worktrees.json` (this file); stage 5 (project lead finds the worktree to verify)
- `plan_path` — consumer: Task 6 (`ic-contract.md`, plan-approval step); Task 7 (`crew:ic` writes it, design §9.2 step 3)
- `plan_approved_at` — consumer: stage 5 (`TeammateIdle` check, design §13.1, §15.8); stage 4/5 (project lead writes it at the plan go-ahead)
- `report_path` — consumer: Task 6 (`ic-contract.md` report contract); Task 9 (`crew:package-reviewer` reads it)

**`state.json` state values** (shared by `packages[].state` and
`deliverables[].state`, except `integrated` and `draft-pr-opened`)
- `pending` — consumer: stage 4/5 (project lead loop dispatches from this state)
- `in-flight` — consumer: stage 5 (project lead loop, `TeammateIdle` hook)
- `integrated` (package only) — consumer: stage 5 (integration step, design §9.3); design §10 (re-plan rule)
- `draft-pr-opened` (deliverable only) — consumer: stage 4 (project lead opens the draft PR, design §9.3); Task 11 (PR body)
- `abandoned` — consumer: design §10 (re-plan and breaker outcome); stage 5

**`state.json` band values** (canonical definitions live in Task 5's
`band-rubric.md`)
- `light` — consumer: Task 5 (`band-rubric.md`)
- `standard` — consumer: Task 5 (`band-rubric.md`); this file's worked example
- `deep` — consumer: Task 5 (`band-rubric.md`); this file's worked example

**`state.json` per-run fields**
- `run_state` — consumer: design §13.1 `SessionEnd` hook, stage 5
- `run_state` values `active`, `blocked`, `interrupted`, `complete` — consumer: this file's `run_state` transitions table; design §13.1, stage 5, stage 6
- `run.session_ids` — consumer: stage 5 (resume, matches this run's project lead sessions)
- `spend` — consumer: design §8 spend ceiling, stage 6 (escalation on crossing it)
- `spend.ceiling` — consumer: stage 6 (spend ceiling check, design §8)
- `spend.measured_tokens` — consumer: stage 6 (spend ceiling check, design §8)
- `spend.estimated_tokens` — consumer: stage 6 (spend ceiling check, design §8's teammate-estimate rule)
- `spend.council_tokens` — consumer: stage 6 (council spend line item, design §6.1)
- `spend.by_agent` — consumer: stage 6 (per-agent spend detail)
- `spend.by_agent[].agent` — consumer: stage 6
- `spend.by_agent[].total_tokens` — consumer: stage 6 (design §8's per-agent usage name)
- `spend.by_agent[].measured` — consumer: stage 6 (marks an estimate as such, design §8)
- `escalations` — consumer: stage 6 (design §6 triggers); this file's `run_state` transitions table
- `escalations[].trigger` — consumer: stage 6
- `escalations[].question` — consumer: stage 6; the human answering it
- `escalations[].asked_at` — consumer: stage 6 (ordering, this file's timestamp rule)
- `escalations[].answer` — consumer: stage 6 (flips `run_state` back to `active`)

**`state.json` `band_history` entry fields**
- `predicted` — consumer: Task 5 (`band-rubric.md`'s promotion-logging rule); stage 5
- `actual` — consumer: Task 5 (`band-rubric.md`'s promotion-logging rule); stage 5
- `cause` — consumer: Task 5 (`band-rubric.md`'s promotion-logging rule); stage 5
- `at` — consumer: a human auditing the record's timeline; stage 6

**`worktrees.json` fields**
- `worktree` (path) — consumer: stage 5 (project lead verifies an IC against this path, design §7)
- `branch` — consumer: stage 5 (merge step, design §9.3)
- `session_ids` (per IC) — consumer: stage 5 (ownership matching, design §13.1); the `TeammateIdle` hook
- `orphaned` — consumer: design §13.1 `SessionEnd` (writer); stage 5 `--resume` (prunes on it, design §10.1)

**`decisions.md` entry fields**
- `Route` — consumer: stage 6 (question routing, design §6)
- `Route` values `precedent`, `council`, `preference` — consumer: stage 6
- `Answer` — consumer: stage 6; Task 11 (copied into the PR body)
- `Citation` — consumer: stage 6 (the confidence rule)
- `Confidence` — consumer: stage 6 (the confidence rule)
- `Confidence` values `high`, `medium`, `low` — consumer: stage 6
- `Timestamp` — consumer: a human auditing the record's timeline; stage 6

**Goal-slug format**
- `<kebab-case-slug>-<4 lowercase hex chars>` — consumer: stage 4 (project lead generates it when creating the record directory)

**Filename conventions**
- `reports/<id>.md` — consumer: Task 6 (`ic-contract.md` report contract); Task 9 (`crew:package-reviewer` reads it)
- `plans/<id>.md` — consumer: Task 6 (`ic-contract.md`); Task 7 (`crew:ic`, design §9.2 step 3, §12)
- `reviews/<id>-package-review-r<n>.md` — consumer: Task 9 (`crew:package-reviewer` output, one file per fix round)
- `reviews/<deliverable-id>-decompose-critic-r<n>.md` — consumer: stage 3 (`decompose-critic` output, one file per re-plan of this deliverable); stage 6 (re-plan, design §10)
- `reviews/<deliverable-id>-deliverable-review.md` — consumer: stage 4 (`crew:deliverable-reviewer` output)

# Record format

One directory per goal, outside the target repo (design §4):

```
~/.claude/crew/<goal-slug>/
├── charter.md        goal + falsifiable acceptance criterion
├── spec.md           the spec the project lead wrote after scouting
├── split.md          deliverables → packages, with interfaces and bands
├── state.json        deliverables, per-package state, band history, spend, escalations
├── decisions.md      every judgment call, with its citation, confidence, and timestamp
├── worktrees.json    IC name → worktree path → branch → session ids → orphaned
├── reports/          one report per package, written by its IC
├── plans/            one plan per package, written by its IC
├── diffs/            one diff per review dispatch, written by the project lead
└── reviews/          raw critic and reviewer output
```

Every relative path named in `state.json` resolves against this directory
root. `worktrees.json`'s `worktree` field is the one path that is already
absolute.

## `reports/`, `plans/`, `diffs/`, and `reviews/`

Four directories hold per-run output. Each has one writer and a fixed
naming convention. Do not mix their contents.

- **`reports/`** — one file per package, `reports/<id>.md`. It holds that
  package's own IC's report and nothing else. `state.json`'s `report_path`
  for a package always equals `reports/<id>.md`.
- **`plans/`** — one file per package, `plans/<id>.md`. It holds the IC's
  implementation plan, written before the project lead's go-ahead (design
  §9.2 step 3, §12's plan-approval fallback). `state.json`'s `plan_path`
  always equals `plans/<id>.md`. This stays separate from `reports/` because
  the project lead's idle check must find a *report* on disk before it accepts
  a package, not a plan (design §13.1). The project lead's own decomposition is
  `split.md` at the record root, named apart from `plans/` so that an IC told
  to "write its plan into the record" cannot overwrite it.
- **`diffs/`** — the diff a review dispatch reads, written by the project
  lead so it never enters its own context. `diffs/<id>-r<n>.patch` for a
  package review, `<n>` being `fix_rounds_used`. **The counter moves before
  the round runs**, or round 1 writes over round 0's diff and review, which
  are a reviewer's only audit trail;
  `diffs/<deliverable-id>-final.patch` for the deliverable review, rewritten
  after integration so it carries the shared-file edits. A diff is evidence
  of what a reviewer actually saw, so a later round never overwrites an
  earlier one.
- **`reviews/`** — raw output from every critic and reviewer, one file per
  review, never overwritten by a later one: `reviews/<id>-package-review-r<n>.md`
  (`<n>` is the fix round, from `fix_rounds_used`),
  `reviews/spec-critic-r<n>.md` (`<n>` counts re-specs of this goal; the spec
  is per goal, so this name carries no deliverable id),
  `reviews/<deliverable-id>-split-critic-r<n>.md` (`<n>` here counts
  re-plans of this deliverable, since design §10's re-plan can rerun the
  critic on the same deliverable),
  `reviews/<deliverable-id>-deliverable-review.md`. Design §9.2 allows up to
  five review rounds per package, and a goal can hold several deliverables —
  a shared filename per kind would let a later round, a later deliverable,
  or a later re-plan silently destroy an earlier review, which is this run's
  only audit trail. A package review reads its `<n>` from `fix_rounds_used`.
  The spec and split critics have no counter in `state.json`, so their `<n>`
  is one more than the highest already on disk under that same name. Reading
  it from disk is what keeps a resumed run from overwriting a review it wrote
  before the crash. The project lead writes every file under `reviews/`, from the
  reviewer's returned findings — a reviewer agent has no `Write` tool and
  returns its findings as a tool result.

The project lead never has to parse a review to find a report or a plan. It reads
`report_path` or `plan_path` from `state.json` and opens that file directly.

**The IC writes both files, on either path.** When a sandbox denies the
write, the IC returns the contents as its final message and the project lead
transcribes them — as a tool result from a subagent, or in the idle
notification from a teammate. A transcribed file says so, so an audit can
tell a first-hand file from a copy.

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

## `split.md`

The project lead's decomposition, in markdown, one file per goal. It is what
`crew:split-critic` reads before any IC is dispatched. It holds one section
per deliverable, in run order, and one subsection per package, with the
packages of one territory listed together in the order that territory's IC works
them.

```markdown
# Split: <goal>

## Global Constraints

Project-wide requirements, copied verbatim from `spec.md` — version floors,
dependency limits, naming rules, platform requirements (design §5). Every
package's requirements include these, and the project lead injects this section
into every IC spawn prompt.

## Deliverable <deliverable-id> — <title>

Branch: crew/<goal-slug>/<deliverable-id>
Depends on: <deliverable-id> | nothing

### Package <package-id>

Territory: <file-tree region>
Band: <light | standard | deep>[ — <justification, required for deep>]
File set:
- <path>
- <path>
Consumes:
- <exact signature, or "nothing">
Produces:
- <exact signature>
Acceptance criterion: <executable test, or the reviewer checklist path>
```

Rules the format carries:

- **Every package states all four invariants** (design §5): an acceptance
  criterion satisfied by its own changes, a file set disjoint from every
  concurrent sibling, a written interface contract, and a band. A package
  missing one of the four is not dispatchable.
- **`Consumes` and `Produces` carry exact signatures**, not descriptions. An IC
  cannot see its siblings' worktrees, so this block is the only channel between
  packages.
- **A `deep` band needs a written justification** on the `Band` line (design
  §8). `light` and `standard` do not.
- **Territories set what runs in parallel**, not the deliverable. Territories
  run beside each other; the packages inside one territory run in order, top to
  bottom as listed, in one IC's worktree (design §5). `Depends on` orders the
  deliverables, which run sequentially.
- **`Consumes` names an earlier package, never a concurrent one.** A package may
  consume a package listed earlier in its own territory, a package from an
  earlier deliverable, or code the repo already holds. An entry naming a package
  in a concurrent territory is a serialization bug, and `crew:split-critic`
  check 5 rejects it.
- **Shared files never appear in a file set.** Version manifests, lockfiles,
  barrel and `index` files, and shared config belong to the project lead at
  integration (design §5).

`state.json` stays authoritative for the plan (see Authority rule below). Every
package here has a `packages[]` entry whose `id`, `territory`, `band`,
`file_set`, `interface_contract`, and `acceptance_criterion` hold the same
values. `split.md` adds what `state.json` does not carry: the global
constraints, the band justifications, and the deliverable order. When the two
disagree, `state.json` wins and the project lead rewrites `split.md` to match.

A re-plan (design §10) overwrites `split.md` in place. The critic's reviews are
the audit trail of earlier splits, one file per re-plan:
`reviews/<deliverable-id>-split-critic-r<n>.md`.

## `state.json`

Top-level keys: `goal`, `goal_slug`, `deliverables`, `run`, `packages`.

### Deliverables

One entry per deliverable (design §5):

| Field | Meaning |
|---|---|
| `id` | referenced by each package's `deliverable` field |
| `branch` | the deliverable branch every package's IC branches from (design §9.3). Always `crew/<goal-slug>/<deliverable-id>`. The slug carries the run's random suffix, which is what keeps two runs in one repo from generating the same branch name — deliverable ids restart at 1 every run (design §15.34). |
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
| `file_set` | the package's declared, disjoint file list (design §5 invariant 2). `split-critic` checks disjointness against this field. |
| `interface_contract` | `{consumes, produces}` with exact signatures (design §5 invariant 3). The only channel between isolated ICs. |
| `acceptance_criterion` | the executable test or reviewer checklist that proves the package is done (design §5 invariant 1). Also what makes a respawn idempotent after a crash (design §10.1). |
| `base` | the sha in this package's worktree when the project lead dispatched it. For a territory's first package that equals the deliverable's `base`; for each package after it, the worktree head when the previous package was accepted. `<base>..HEAD` is what makes a review diff cover this package and not its predecessors in the same worktree (design §15.37a). |
| `fix_rounds_used` | integer, capped at five (design §9.2). After a crash, design §10.1 respawns an IC from its worktree. Without this persisted, the round count resets and the breaker never fires. |
| `nudges_used` | integer, capped at one per dispatch (`full-path.md` step 5a). Counts the current dispatch only, so every re-dispatch of the package resets it to 0. Persisted because a resumed session holds no memory of a nudge it already sent. The simple path leaves it 0: a subagent has no message channel to nudge. |
| `ic_name` | the name of the teammate assigned to this package. Cross-references `worktrees.json`, which maps this name to a worktree path. Without it, nothing maps a package back to the worktree that must verify it. |
| `plan_path` | always `plans/<id>.md`. The IC's plan, written before its report (design §9.2 step 3, §12). |
| `plan_approved_at` | ISO-8601 UTC timestamp of the project lead's go-ahead on the plan (design §9.2 step 3); `null` until then. While it is `null` and `plans/<id>.md` exists, the IC's post-plan idle is an expected pause — the project lead's idle check (design §13.1) lets it pass (design §15.8). |
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
- `in-flight → integrated`: the package passed review, and its work is on the deliverable branch with the suite green there. On the full path that is its own merge and suite run; on the simple path the work is already on the branch, so it is the suite run alone.
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
`nudges_used: 0`, `ic_name: null`, `base: null` until it is dispatched, and
`plan_approved_at: null`. `plan_path` and `report_path`
name files that do not exist yet. On the simple path (design §9.1) the project lead never writes
`worktrees.json`: there is one package, no territory, and `ic_name` stays
`null` for the run.

### Per-run fields (inside `run`)

| Field | Meaning |
|---|---|
| `run_state` | one of `active`, `blocked`, `interrupted`, `complete`. See `run_state` transitions below. |
| `session_ids` | a list, not a single id. The project lead's own session id, read from `$CLAUDE_CODE_SESSION_ID` (see below), appended to on every `--resume`, for the same reason as `worktrees.json`'s `session_ids` below. |
| `spend` | `{ceiling, measured_tokens, estimated_tokens, council_tokens, by_agent}`. See Spend below. |
| `escalations` | a list of questions the project lead asked the human (design §6 triggers). See Escalations below. |

**Read the session id, never invent it.** `echo $CLAUDE_CODE_SESSION_ID`
prints this session's own id, and it is the same string the `SessionEnd` hook
matches against. Run it. A plausible-looking id you wrote yourself matches
nothing, so the hook silently marks no run, and `--resume` cannot prove which
worktree it owns (design §15.39). This holds on both paths: the simple path
writes no `worktrees.json`, but it still writes `run.session_ids`.

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
      "branch": "crew/add-request-logging-a1b2/deliverable-1",
      "base": "a1b2c3d",
      "state": "in-flight",
      "state_changed_at": "2026-08-24T14:05:00Z",
      "pr_url": null
    }
  ],
  "run": {
    "run_state": "active",
    "session_ids": ["8154734d-d163-4d22-8946-83c3b12cb6f2"],
    "spend": {
      "ceiling": 5000000,
      "measured_tokens": 812000,
      "estimated_tokens": 150000,
      "council_tokens": 0,
      "by_agent": [
        { "agent": "split-critic", "total_tokens": 210000, "measured": true },
        { "agent": "ic-middleware", "total_tokens": 0, "measured": false }
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
      "base": "a1b2c3d",
      "fix_rounds_used": 1,
      "nudges_used": 0,
      "ic_name": "ic-middleware",
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
      "base": "e4f5a6b",
      "fix_rounds_used": 2,
      "nudges_used": 1,
      "ic_name": "ic-config",
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

IC name → worktree path → branch → `session_ids` → `orphaned`. The project
lead writes it on the full path only; the simple path creates no worktree.

**The path convention** is `<record-root>/worktrees/<territory-slug>`, and
the IC on it is named `ic-<territory-slug>`. The root sits outside the target
repo: a test runner that globs collects every worktree's tests as well as the
repo's own, so a repo-local root makes the suite measure the wrong tree
(design §15.35b, §15.37f).

An IC writes its plan and its report into the record root, not into its
worktree, so a worktree holds only the package's own work. That keeps
`git status --porcelain` meaning exactly what the recovery check reads it to
mean: uncommitted work, and nothing else.

**`session_ids` is a list, not a single id.** Design §13.1 makes the session
id the only proof of worktree ownership, but `--resume` runs in a *new*
session with a *new* id. If resume overwrote the field, ownership matching
would fail on the very first resume — the exact case the field exists to
serve. Resume appends; it never overwrites. `state.json`'s `run.session_ids`
follows the same append-only rule, for the same reason.

**`orphaned`** is a boolean. Its only writer is crew's `SessionEnd` hook.
It marks a worktree only when that worktree's own run is being interrupted —
the run's `run_state` was `active` or `blocked` and its `session_ids` hold the
ending session's id — and then only the worktrees carrying that same id. A run
already `complete` is left alone whatever its worktrees say, because a
finished run's leftovers are step 12's cleanup, not an orphan. `--resume` clears it once a worktree is reconciled. It is a
hint, not evidence: the hook fails open, so recovery still decides from git
and from a recorded `integrated`, never from this field alone.

### Worked example

```json
{
  "ic-middleware": {
    "worktree": "/Users/x/.claude/crew/add-request-logging-a1b2/worktrees/middleware",
    "branch": "crew/add-request-logging-a1b2/middleware",
    "session_ids": ["8154734d-d163-4d22-8946-83c3b12cb6f2"],
    "orphaned": false
  },
  "ic-config": {
    "worktree": "/Users/x/.claude/crew/add-request-logging-a1b2/worktrees/config",
    "branch": "crew/add-request-logging-a1b2/config",
    "session_ids": ["8154734d-d163-4d22-8946-83c3b12cb6f2", "43227fc9-c61f-488e-afbd-20737f7a3650"],
    "orphaned": false
  }
}
```

`ic-config` shows a resumed IC: two session ids because the worktree
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

**Read the clock for `Timestamp`, never write one from memory.** `date -u
+%Y-%m-%dT%H:%M:%SZ` prints it. A run that guesses stamps every entry at
midnight, which makes a decision trail a human cannot order (design §15.47).
This is the same failure as an invented session id (§15.39), in a field that
looks harmless.

### A council entry

A council-route entry carries four more lines (design §6.1). `Positions` and
`Losing` are what let an audit see the whole council rather than its winner.

- `Positions:` — every position the project lead framed, the winner first.
- `Losing:` — one line per losing position: the best argument it made, and why
  it lost.
- `Models:` — the model every advocate ran, as `<n> advocates, <model>`. Every
  advocate in one council runs the same model (`band-rubric.md`), so this is
  one value, not one per advocate. Name your own adjudicating model after it.
- `Spend:` — the tokens this council added to `spend.council_tokens`.

```markdown
## Where does the retry budget live: the client or the call site?
Route: council
Positions: A. the client owns it. B. each call site owns it. C. a policy object both read.
Answer: A — the client owns it.
Citation: src/http/client.ts:44 already holds the timeout and the backoff, and
CLAUDE.md "HTTP" says one place owns transport policy.
Losing: B argued call sites vary (src/sync/push.ts:80 retries 5 times), which
the client's per-request override already covers. C added a type no caller
asks for.
Confidence: high
Models: 3 advocates, sonnet. Adjudicated at opus.
Spend: 41200 tokens
Timestamp: 2026-08-24T14:32:00Z
```

A balanced council is not an entry to finish alone. When the project lead
cannot pick a winner at medium confidence or better and the question is
architecture-moving, it escalates (`autonomy-contract.md`), and the entry's
`Answer` is the principal's.

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
- `split.md` — consumer: stage 3 (`crew:split-critic` and the `split.md` format)
- `state.json` — consumer: stage 4 (project lead loop); stage 5 (recovery, design §10.1)
- `decisions.md` — consumer: stage 6 (council + routing); Task 11 (copied into the PR body)
- `worktrees.json` — consumer: stage 5 (full path: worktrees, merges, recovery)
- `reports/` — consumer: Task 6 (`ic-contract.md` report contract); Task 9 (`crew:package-reviewer` reads a package's report)
- `plans/` — consumer: Task 6 (`ic-contract.md`, IC plan-approval step); Task 7 (`crew:ic`, design §9.2 step 3, §12)
- `reviews/` — writer: the project lead, from each reviewer's returned findings. Consumer: Task 9 (`crew:package-reviewer` output); stage 3 (`split-critic` output); stage 4 (`crew:deliverable-reviewer` output)

**`split.md` sections and fields**
- `Global Constraints` — consumer: stage 4/5 (project lead copies it into every IC spawn prompt, design §5)
- `Deliverable <id>` section — consumer: stage 3 (`split-critic` reviews one deliverable's packages); cross-references `deliverables[].id`
- `Branch` (deliverable) — consumer: stage 5 (merge target, design §9.3); mirrors `deliverables[].branch`
- `Depends on` (deliverable) — consumer: stage 4/5 (deliverable run order, design §5)
- `Package <id>` subsection — consumer: stage 3 (`split-critic` checks the four invariants); mirrors `packages[].id`
- `Territory` — consumer: stage 5 (one IC per territory); mirrors `packages[].territory`
- `Band` and its justification — consumer: Task 5 (`band-rubric.md`); design §8 (a `deep` band needs the written justification)
- `File set` — consumer: stage 3 (disjointness check); mirrors `packages[].file_set`
- `Consumes` / `Produces` — consumer: stage 3 (contract and type-consistency checks); mirrors `packages[].interface_contract`
- `Acceptance criterion` — consumer: stage 3 (self-contained-acceptance check); mirrors `packages[].acceptance_criterion`

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
- `id` — consumer: this file's `reports/<id>.md`, `plans/<id>.md`, `reviews/<id>-package-review-r<n>.md` naming; stage 3 (`split-critic` identifies packages)
- `deliverable` — consumer: stage 5 (per-deliverable integration, design §9.3); cross-references `deliverables[].id`
- `territory` — consumer: stage 5 (one IC dispatched per territory, design §5)
- `state` — consumer: stage 4 (project lead loop); stage 5 (re-planning and recovery, design §10)
- `state_changed_at` — consumer: a human auditing the record's timeline; stage 6
- `band` — consumer: Task 5 (`band-rubric.md` defines what each value means and when to promote)
- `band_history` — consumer: Task 5 (band-rubric.md's promotion-logging rule); stage 5 (promotion on `BLOCKED`/exhausted fix rounds/idle)
- `file_set` — consumer: Task 7 (`crew:ic` self-review checks its diff against this); stage 3 (`split-critic` disjointness check)
- `interface_contract` — consumer: stage 3 (`split-critic` type-consistency check); Task 7/Task 8 (IC spawn prompt carries it, design §9.2 step 2)
- `acceptance_criterion` — consumer: Task 6 (`ic-contract.md`, tells the IC when to stop); Task 9 (`crew:package-reviewer` checks work against it)
- `base` (package) — consumer: stage 5 (the review diff and the verification range, `<base>..HEAD`)
- `fix_rounds_used` — consumer: stage 5 (the fix-round breaker, design §9.2 step 6)
- `nudges_used` — consumer: the project lead's idle nudge (`full-path.md` step 5a)
- `ic_name` — consumer: `worktrees.json` (this file); stage 5 (project lead finds the worktree to verify)
- `plan_path` — consumer: Task 6 (`ic-contract.md`, plan-approval step); Task 7 (`crew:ic` writes it, design §9.2 step 3)
- `plan_approved_at` — consumer: stage 5 (the project lead's idle check, design §13.1, §15.8); stage 4/5 (project lead writes it at the plan go-ahead)
- `report_path` — consumer: Task 6 (`ic-contract.md` report contract); Task 9 (`crew:package-reviewer` reads it)

**`state.json` state values** (shared by `packages[].state` and
`deliverables[].state`, except `integrated` and `draft-pr-opened`)
- `pending` — consumer: stage 4/5 (project lead loop dispatches from this state)
- `in-flight` — consumer: stage 5 (project lead loop, idle check)
- `integrated` (package only) — consumer: stage 5 (integration step, design §9.3); design §10 (re-plan rule)
- `draft-pr-opened` (deliverable only) — consumer: stage 4 (project lead opens the draft PR, design §9.3); Task 11 (PR body)
- `abandoned` — consumer: design §10 (re-plan and breaker outcome); stage 5

**`state.json` band values** (canonical definitions live in Task 5's
`band-rubric.md`)
- `light` — consumer: Task 5 (`band-rubric.md`)
- `standard` — consumer: Task 5 (`band-rubric.md`); this file's worked example
- `deep` — consumer: Task 5 (`band-rubric.md`); this file's worked example

**`state.json` per-run fields**
- `run_state` — consumer: crew's `SessionEnd` hook (writer, `hooks/session-end.py`); stage 5
- `run_state` values `active`, `blocked`, `interrupted`, `complete` — consumer: this file's `run_state` transitions table; crew's `SessionEnd` hook; stage 5, stage 6
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
- `worktree` (path) — consumer: stage 5 (project lead verifies an IC against this path, design §7); `<record-root>/worktrees/<territory-slug>`
- `branch` — consumer: stage 5 (merge step, design §9.3)
- `session_ids` (per IC) — consumer: stage 5 (ownership matching, design §13.1); crew's `SessionEnd` hook (matches a worktree to the ending session)
- `orphaned` — consumer: crew's `SessionEnd` hook (writer); stage 5 `--resume` (prunes on it, design §10.1)

**`decisions.md` entry fields**
- `Route` — consumer: stage 6 (question routing, design §6)
- `Route` values `precedent`, `council`, `preference` — consumer: stage 6
- `Answer` — consumer: stage 6; Task 11 (copied into the PR body)
- `Citation` — consumer: stage 6 (the confidence rule)
- `Confidence` — consumer: stage 6 (the confidence rule)
- `Confidence` values `high`, `medium`, `low` — consumer: stage 6
- `Positions` — consumer: stage 6 (council entries only, design §6.1)
- `Losing` — consumer: stage 6 (council entries only, design §6.1)
- `Models` — consumer: stage 6 (council entries only); Task 5 (`band-rubric.md`'s promotion data covers councils, design §15.9)
- `Spend` — consumer: stage 6 (council entries only); mirrors `spend.council_tokens`
- `Timestamp` — consumer: a human auditing the record's timeline; stage 6

**Goal-slug format**
- `<kebab-case-slug>-<4 lowercase hex chars>` — consumer: stage 4 (project lead generates it when creating the record directory)

**Filename conventions**
- `reports/<id>.md` — consumer: Task 6 (`ic-contract.md` report contract); Task 9 (`crew:package-reviewer` reads it)
- `plans/<id>.md` — consumer: Task 6 (`ic-contract.md`); Task 7 (`crew:ic`, design §9.2 step 3, §12)
- `reviews/<id>-package-review-r<n>.md` — consumer: Task 9 (`crew:package-reviewer` output, one file per fix round)
- `reviews/<deliverable-id>-split-critic-r<n>.md` — consumer: stage 3 (`split-critic` output, one file per re-plan of this deliverable); stage 6 (re-plan, design §10)
- `reviews/<deliverable-id>-deliverable-review.md` — consumer: stage 4 (`crew:deliverable-reviewer` output)

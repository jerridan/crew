# Record format

This file owns two records. **The goal record** is one directory per goal,
written by the project lead, and it is everything down to "Authority rule".
**The portfolio record** is one directory per lead, written by the lead, and
`## The portfolio record` near the end owns it.

One directory per goal, outside the target repo (design §4):

```
~/.claude/crew/<goal-slug>/
├── charter.md        goal + falsifiable acceptance criterion
├── spec.md           the spec the project lead wrote after scouting
├── diagnosis.md      investigation path only: repro, evidence, root cause, ruled out
├── split.md          deliverables → packages, with interfaces and bands
├── state.json        deliverables, per-package state, band history, spend, escalations
├── decisions.md      every judgment call, with its citation, confidence, and timestamp
├── worktrees.json    IC name → worktree path → branch → session ids → orphaned
├── reports/          one report per package, written by its IC
├── plans/            one plan per package, written by its IC
├── diffs/            one diff per deliverable, written by the project lead
├── evidence/         investigation path only: one file per evidence dispatch
├── review-worktrees/ one throwaway checkout per skeptical review, removed after
└── reviews/          raw critic and reviewer output
```

Every relative path named in `state.json` resolves against this directory
root. `worktrees.json`'s `worktree` field is the one path that is already
absolute.

The root is `$CREW_RECORD_ROOT` when that variable is set, and
`~/.claude/crew/` otherwise. Both hooks check both places. Set it to keep
two runs of one charter apart, as an experiment does (design §15.50).

**Write `state.json` with `scripts/crew-record.py`**, beside this skill:

```
python3 <skill-dir>/scripts/crew-record.py <record-dir> init "<goal>" <goal-slug> "$CLAUDE_CODE_SESSION_ID"
python3 <skill-dir>/scripts/crew-record.py <record-dir> session-id "$CLAUDE_CODE_SESSION_ID"
python3 <skill-dir>/scripts/crew-record.py <record-dir> deliverable add '<json object>'
python3 <skill-dir>/scripts/crew-record.py <record-dir> deliverable <id> state in-flight
python3 <skill-dir>/scripts/crew-record.py <record-dir> deliverable <id> set checkout_restored '"dirty tree, 3 files modified"'
python3 <skill-dir>/scripts/crew-record.py <record-dir> package add '<json object>'
python3 <skill-dir>/scripts/crew-record.py <record-dir> package <id> state in-flight
python3 <skill-dir>/scripts/crew-record.py <record-dir> package <id> set fix_rounds_used 1
python3 <skill-dir>/scripts/crew-record.py <record-dir> run state blocked
python3 <skill-dir>/scripts/crew-record.py <record-dir> escalation add "<trigger>" "<question>"
python3 <skill-dir>/scripts/crew-record.py <record-dir> escalation answer <index> "<answer>"
python3 <skill-dir>/scripts/crew-record.py <record-dir> integrate <package-id> --review-head <sha> [--published]
python3 <skill-dir>/scripts/crew-record.py <record-dir> deliver <deliverable-id> draft-pr-opened --pr-url <url>
python3 <skill-dir>/scripts/crew-record.py <record-dir> ship
```

**Never write `escalations` with `run set`.** That command replaces the key,
so it drops every ask already in the list. `escalation add` appends one ask,
stamps `asked_at`, and prints the index that `escalation answer` takes. A
batch of questions is one call per question.

`init` creates the file with `created_at`. `integrate` writes a package
`integrated` and, with `--review-head`, `run.review_pending` in the same
write, which the delivered window requires (`simple-path.md`). Its
`--published` flag stamps `pushed_at` in that same write, for a branch with
no remote, where the commit is the publication. `deliver`
writes the deliverable's terminal state and `run_state: delivered` together,
which the `work-complete` exception below requires, and stamps
`delivered_at`. `ship`
writes `run_state: complete` and stamps `completed_at`. Every write stamps
`state_changed_at` and replaces the file in one step. The script checks no
transition; this file owns those. Rewriting the whole file by hand costs a turn of output per
transition and is where the invented session id came from (design §15.39,
§15.50).

A `set` value is JSON, so a string carries its own quotes inside the shell
quotes, as the `checkout_restored` line above shows. A bare sentence fails to
parse and writes nothing.

## `charter.md`

The goal and its falsifiable acceptance criteria, as the principal wrote
them or as the project lead expanded a goal string. Two optional lines,
each on its own, anywhere in the file:

- `Favour: time` or `Favour: spend` — what the split optimises. `time`
  splits into parallel territories; `spend` keeps one territory and one IC
  that carries its context from package to package. `spend` is the default
  (design §15.50).
- `Instruments: <name>, <name>, ...` — the repo-local skills or agents this
  run may dispatch (design §6.4). Comma-separated, each the exact name the
  principal would type to invoke that skill or agent in the target repo — a
  slash command without its leading `/`, or an agent's frontmatter `name`.
  Without this line the run has none, and the project lead never dispatches
  one it finds in the repo but the charter does not name.

## `diagnosis.md`

The investigation path's artifact (design §9.5). Written by the project lead,
absent from every other run. Five headings, in this order:

- `## Reproduction` — the test or command that fails now, with the failing
  output. This is the charter's acceptance criterion, and it becomes the fix
  package's `acceptance_criterion` when the run goes on to build one.
- `## Evidence` — one line per finding, each naming the `evidence/` file that
  holds it and the repo path or command that produced it. A finding with no
  path is a memory, not evidence.
- `## Root cause` — one paragraph, with the citation that proves it.
- `## Ruled out` — one line per rejected hypothesis, each with the evidence
  that rejected it. A later run reads this as precedent (design §6.2), so an
  empty entry costs the next run a council.
- `## Outcome` — `fix`, with one line naming the change to make, or
  `no change`, with the reason. Nothing here names a deliverable: the fix's
  deliverable does not exist when this file is written. `no change` is what
  ends the run at `work-complete`.

A council on competing hypotheses writes its own entry to `decisions.md` as
usual. `diagnosis.md` names the winner and points there; it holds no second
copy of the losing arguments.

An `Outcome: no change` needs the adversary review design §9.5 requires:
`reviews/diagnosis-adversary.md`, the case one `crew:council-advocate` made
against the root cause. The project lead copies that case into the file — an
advocate writes no file (`agents/council-advocate.md`). An `Outcome: fix`
needs none, because the fix package's own acceptance test covers it.

## `reports/`, `plans/`, `diffs/`, `evidence/`, and `reviews/`

Five directories hold per-run output. Each has one writer and a fixed
naming convention. Do not mix their contents.

- **`reports/`** — one file per package, `reports/<id>.md`. It holds that
  package's own IC's report and nothing else. A patch round's reply is not
  here — it sits under `reviews/`, beside the findings it answers. `state.json`'s `report_path`
  for a package always equals `reports/<id>.md`. It is also where the "fails
  before" evidence is kept (design §7): the IC's report names the red commit's
  sha and carries the criterion's failing output at it. No `state.json` field
  holds either — the commit is in `git log`, and the project lead re-runs the
  criterion at it rather than trusting a field. On the investigation path the
  evidence is `diagnosis.md`'s `## Reproduction` instead, and the fix package
  needs no red commit.
- **`plans/`** — one file per package, `plans/<id>.md`. It holds the IC's
  implementation plan (`ic-contract.md`'s "Write your plan first").
  `state.json`'s `plan_path` always equals `plans/<id>.md`. This stays separate
  from `reports/` because the project lead's idle check must find a *report* on
  disk before it accepts a package, not a plan (design §13.1). The project
  lead's own decomposition is `split.md` at the record root, named apart from
  `plans/` so that an IC told to "write its plan into the record" cannot
  overwrite it.
- **`diffs/`** — the record's copy of the deliverable's whole change,
  written by the project lead so it never enters its own context:
  `diffs/<deliverable-id>-final.patch`, written after integration so it
  carries the shared-file edits. It is evidence of what the hand-over
  shipped.
- **`evidence/`** — what one evidence dispatch found on the investigation
  path, `evidence/<n>-<slug>.md`, absent from every other run. It has two
  writers, and `investigation-path.md` Phase 1 says which writes when: a
  `crew:researcher` writes its own brief at the absolute path its dispatch
  names, and the project lead writes the file itself for an `Explore`
  subagent, which carries no `Write` tool. `<slug>` names the question the
  dispatch answered. `<n>` counts up from the highest already on disk, and
  **the project lead allocates one `<n>` per dispatch before it sends a
  batch** — several dispatches go out in one message, so a writer that reads
  the counter off disk for itself would give every file in the batch the same
  number. The counter keeps a later dispatch from overwriting an earlier
  finding, and a resumed run reads it off disk because no `state.json` field
  holds it. These files are the evidence set every advocate in an
  investigation council is given (`autonomy-contract.md`), and
  `diagnosis.md`'s `## Evidence` points at them.
- **`reviews/`** — raw output from every critic and reviewer, one file per
  review, never overwritten by a later one:
  `reviews/spec-critic-r<n>.md` (`<n>` counts re-specs of this goal; the spec
  is per goal, so this name carries no deliverable id),
  `reviews/<deliverable-id>-split-critic-r<n>.md` (`<n>` here counts
  re-plans of this deliverable, since design §10's re-plan can rerun the
  critic on the same deliverable),
  four files per skeptical review round, all named by the round `<n>` and none
  by a deliverable id, because the review is per branch head:
  `reviews/skeptical-r<n>.md`, the report, whose **first line is
  `Reviewed: <sha>`** — the head that review read, which a resumed run matches
  against `run.review_pending.head` rather than trusting the file name, and
  whose second line is `Source: result field` when the fallback supplied it;
  `reviews/skeptical-r<n>-instructions.md`, the text the review was launched
  with; `reviews/skeptical-r<n>-result.json`, the child process's own JSON
  output, which the checks read; and `reviews/skeptical-r<n>-reply.md`, the
  project lead's adjudication of that report, one line per finding with its
  disposition — accepted with the package id it became, declined with its
  reason, or out of scope with the goal proposed for it. A retry of a round does
  not overwrite these: it renames the attempt it replaces to
  `skeptical-r<n>-attempt<k>.md`, `skeptical-r<n>-instructions-attempt<k>.md`
  and `skeptical-r<n>-result-attempt<k>.json`, `<k>` counting up from the
  highest already there, so the evidence of a failed attempt survives. **A
  review a replacement ran saves `skeptical-r<n>-result.txt` and
  `skeptical-r<n>-result.exit` in place of the `.json`**, holding the runner's
  own output and its exit status, and the two retire under the same rule as
  `skeptical-r<n>-result-attempt<k>.txt` and
  `skeptical-r<n>-result-attempt<k>.exit`. A `.txt` with no `.exit` beside it
  is an attempt whose shell never finished (`SKILL.md`'s "A step the principal
  replaced").
  `crew-stats.py` counts none of the renamed files as a review. **A patch
  round from any other source writes the same reply file under its own
  `<round-id>`**: `reviews/<round-id>-reply.md`, where `<round-id>` is
  `<kind>-r<n>` — `ci-r1`, `pr-comments-r2`, `principal-r1` — with `<n>` one
  more than the highest already on disk under that name. Only a skeptical
  round carries the other three files, because only it runs a review
  (`simple-path.md`'s "Findings from a review"). Then
  `reviews/diagnosis-adversary.md` for the one advocate that argues against a
  report ending's root cause (design §9.5; the diagnosis is per goal, so this
  name carries no deliverable id). A goal can hold several deliverables, and a
  critic can run twice over one of them — a shared filename per kind would let
  a later deliverable or a later re-plan silently destroy an earlier review,
  which is this run's only audit trail. The spec and split critics have no
  counter in `state.json`, so their `<n>` is one more than the highest already
  on disk under that same name. Reading
  it from disk is what keeps a resumed run from overwriting a review it wrote
  before the crash. The review agent writes its own file, at the absolute
  path the dispatch names (`review-output.md`); the project lead transcribes
  it when the write was denied, and whenever a replacement runs the step,
  because a replacement returns its report instead of writing one
  (`SKILL.md`'s "A step the principal replaced").

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
Acceptance criterion: <executable test, or the checklist path>
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
- **The verification tool is the first package.** When an acceptance criterion
  needs a tool the repo does not have — a screenshot diff, an audit, a
  comparison — build it first, and have its IC prove it deterministic against a
  known-equal pair before any package that uses it starts. Then every later
  brief names the tool, and `ic-contract.md` makes the IC run it before
  reporting (design §15.50).
- **Shared files never appear in a package's file set.** Version manifests,
  lockfiles, barrel and `index` files, and shared config belong to the project
  lead at integration (design §5). The light path is the one exception: it has
  one IC and merges nothing, so its package may name the one shared file the
  repo's instruction file marks as a registration point
  (`simple-path.md`, design §15.83).

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
| `branch` | the deliverable branch every package's IC branches from (design §9.3). Always `crew/<goal-slug>/<deliverable-id>`. The slug carries the run's random suffix, which is what keeps two runs in one repo from generating the same branch name — deliverable ids restart at 1 every run (design §15.34). `null` on an investigation run that ends in a report: nothing is edited, so no branch is created (design §9.5). |
| `base` | the commit sha at the deliverable branch's head when it was created — the `<base>` in `git -C <wt> log <base>..HEAD` (design §10.1). `null` when `branch` is `null`. |
| `state` | one of `pending`, `in-flight`, `draft-pr-opened`, `work-complete`, `abandoned`. `draft-pr-opened` and `work-complete` are a deliverable's own terminal states, not `integrated` — design §9.3 and §11 stop at opening a draft PR, so no crew state ever means a deliverable reached `main`. `work-complete` means the work is complete and trusted but no PR was opened; `abandoned` means the work is not trusted. |
| `state_changed_at` | ISO-8601 UTC timestamp of this deliverable's last `state` transition |
| `pr_url` | the draft PR opened in `draft-pr-opened` (design §9.3); `null` until then. Stays `null` in `work-complete`. There, the `branch` name is what the principal gets instead — or, for an investigation run that ends in a report and not a change, `diagnosis.md` (design §9.5). |
| `checkout_branch` | the branch the checkout was on before the run switched it, so the run can put it back. Both paths switch it and both write this field: `simple-path.md`'s "Create the branch" on the simple path, `full-path.md`'s "Create the branch and the worktrees" on the full path. `base` holds the sha at the deliverable branch's head, which is not the same thing. `null` for a detached head, and `null` on an investigation run that ends in a report, which never switches the checkout (design §15.54, §9.5). |
| `checkout_restored` | `null` until the run ends. `true` when the run switched the checkout back to `checkout_branch`, as `simple-path.md`'s "End the run" says. Otherwise one sentence naming why it did not — a dirty tree, or a principal who keeps the deliverable branch. Stays `null` when `checkout_branch` is `null`: there was nothing to restore. |

Deliverables run sequentially (design §5), so at most one is ever
`in-flight`.

### Per-package fields

| Field | Meaning |
|---|---|
| `id` | the package's identity. Used to name its files: `reports/<id>.md` and `plans/<id>.md`. |
| `deliverable` | the `id` of the deliverable this package belongs to, from the `deliverables` list above |
| `territory` | the file-tree region this package's IC owns (design §5) |
| `state` | one of `pending`, `in-flight`, `integrated`, `abandoned`. See State transitions below. |
| `state_changed_at` | ISO-8601 UTC timestamp of this package's last `state` transition |
| `band` | one of `light`, `standard`, `deep`. `band-rubric.md` is the authority for what a band means and when to promote one; this field only stores the current value. |
| `band_history` | a list of `{predicted, actual, cause, at}` entries: one when the band is first predicted, and one more per promotion after that (design §8). `at` is an ISO-8601 UTC timestamp. |
| `file_set` | the package's declared, disjoint file list (design §5 invariant 2). `split-critic` checks disjointness against this field. |
| `interface_contract` | `{consumes, produces}` with exact signatures (design §5 invariant 3). The only channel between isolated ICs. |
| `acceptance_criterion` | the executable test, or the checklist the project lead applies itself, that proves the package is done (design §5 invariant 1). Also what makes a respawn idempotent after a crash (design §10.1). |
| `base` | the sha in this package's worktree when the project lead dispatched it. For a territory's first package that equals the deliverable's `base`; for each package after it, the worktree head when the previous package was accepted. `<base>..HEAD` is what makes a review diff cover this package and not its predecessors in the same worktree (design §15.37a). |
| `fix_rounds_used` | integer, capped at five (design §9.2). After a crash, design §10.1 respawns an IC from its worktree. Without this persisted, the round count resets and the breaker never fires. |
| `nudges_used` | integer, capped at one per dispatch (`full-path.md`'s "The idle nudge"). Counts the current dispatch only, so every re-dispatch of the package resets it to 0. Persisted because a resumed session holds no memory of a nudge it already sent. The simple path leaves it 0: a subagent has no message channel to nudge. |
| `ic_name` | the name of the teammate assigned to this package. Cross-references `worktrees.json`, which maps this name to a worktree path. Without it, nothing maps a package back to the worktree that must verify it. |
| `round` | the `<round-id>` of the patch round that wrote this package, a key into `run.rounds`. The round holds the source and the reply, so the package holds neither. Absent on every other package, and that absence is what says the package belongs to no round. |
| `pushed_at` | ISO-8601 UTC timestamp of this package's **publication**, `null` until it happens. A branch with a remote is published by a push that succeeded, and the project lead stamps this right after it — never before, and never after one that failed. A branch with no remote is published when the work commits, so `crew-record.py integrate --published` stamps it in the integration write and no push is ever owed. One push can carry several packages of one round, and it stamps each. |
| `plan_path` | always `plans/<id>.md`. The IC's plan, written before its report (design §9.2 step 3, §12). |
| `report_path` | always `reports/<id>.md`. Points into `reports/`. |

### State transitions

```
pending ──▶ in-flight ──▶ integrated   (terminal)
   │             │
   └────┬────────┘
        ▼
    abandoned                          (terminal)
```

- `pending → in-flight`: the project lead dispatches an IC for the package. Every package gets one, however small the change is (design §9.1).
- `in-flight → integrated`: the project lead's verification passed (`simple-path.md`'s "Verify before you believe"), and the package's work is on the deliverable branch with the suite green there, or with the no-suite outcome `simple-path.md`'s "Verify before you believe" defines. On the full path that is its own merge and suite run; on the simple path the work is already on the branch, so it is the suite run alone. In the delivered window one write does it: `crew-record.py integrate <package-id> --review-head <sha>` marks the package and writes `run.review_pending` together, and the publication that follows is a timestamp on the package, not a state (`simple-path.md`).
- `pending → abandoned` or `in-flight → abandoned`: a re-plan drops the
  package, or the fix-round breaker parks it (design §9.2, §10).
- `integrated` and `abandoned` are both terminal. Neither has an outgoing
  transition (design §10). Correcting integrated work never revises the same
  record — it creates a new package in `pending`.

A deliverable follows the same shape, with `draft-pr-opened` and
`work-complete` in place of `integrated`:

```
                        ┌──▶ draft-pr-opened   (terminal)
pending ──▶ in-flight ──┤
   │            │       └──▶ work-complete     (terminal)
   │            │
   └─────┬──────┘
         ▼
     abandoned                                 (terminal)
```

- `pending → in-flight`: the project lead dispatches the deliverable's first
  package. On the investigation path a diagnosis deliverable has no package,
  so the first evidence dispatch moves it (design §9.5).
- `in-flight → draft-pr-opened`: every package integrates and the project lead
  opens the draft PR (design §9.3).
- `in-flight → work-complete`: every package passed the project lead's own
  verification, and the push or the draft PR was impossible or refused
  (`simple-path.md`'s "End the run"). The skeptical review is not a
  precondition — it runs after this write, on the local head, like any other
  hand-over (`skeptical-review.md`). This state is terminal: a review and its
  patch rounds leave the deliverable `work-complete`. Or the run took the
  investigation path and its `diagnosis.md` `Outcome` is `no change`, so there
  was never a PR to open (design §9.5).
- `pending → abandoned` or `in-flight → abandoned`: a re-plan drops the
  deliverable (design §10).

`draft-pr-opened`, `work-complete`, and `abandoned` are all terminal. None
has an outgoing transition (design §10).

These arrows are **transitions**: one-way project lead decisions. A
**reconciliation** is different — after a crash, design §10.1 rewrites
`state.json` to match git, and that correction may move a wrongly recorded
value in either direction, including out of a mistaken `integrated` or
`draft-pr-opened`.

**`work-complete` is the exception, because git cannot prove it.** Every other
terminal state has evidence outside the record: `integrated` has a merge,
`draft-pr-opened` has a `pr_url`. A `work-complete` deliverable looks exactly
like an `in-flight` one that died just before "End the run" — commits on a branch,
a clean tree, no PR. A resume that reconciles from git alone would re-enter
"End the run" and open the very PR the principal refused.

So the evidence for `work-complete` lives in the record, and a resume reads it
there: the `escalations` entry whose `answer` records what the principal said,
or, on the investigation path, `diagnosis.md`'s `Outcome: no change`.
**Never move a deliverable out of `work-complete` on git evidence alone.**
Move it only when the principal says to.

Write the deliverable's `work-complete` and the run's `delivered` in **one**
write, against the usual rule of one write per transition. The one write keeps
the record true. Split across two, a crash between them leaves `work-complete`
under an `active` `run_state` — a record that says the run is still working on
a deliverable it closed. The resume rule reads the deliverable's state, not
the run's (`SKILL.md`, "Take the goal"), so it enters the delivered window
either way. The one write protects the record, not the resume.

### At creation

A new package starts `pending`, with `band_history: []`, `fix_rounds_used: 0`,
`nudges_used: 0`, `ic_name: null`, and `base: null` until it is dispatched.
A package written in the delivered window starts with `pushed_at: null` as
well, and carries a `round` only when a patch round wrote it.
A record written before T58 can also carry `plan_approved_at`, from the plan
gate that step retired (design §15.94d). Read it as history, and write it on
no new package.
`plan_path` and `report_path` name files that do not exist yet. On the simple
path (design §9.1) there is one package and no territory, so `ic_name` stays
`null` for the run. The project lead writes `worktrees.json` there only when
it cut the deliverable a checkout of its own (`worktrees.json` below).

### What a delivered-window round still owes

A resume in `delivered` reads two obligations here, and infers no third from
a `null` field:

- **A package owes a dispatch** when its `base` is `null`. It was written
  and never sent, so dispatch it (`simple-path.md`'s "Dispatch the IC").
- **A package owes a publication** when it is `integrated`, its `pushed_at`
  is `null`, its branch has a remote and its round carries no
  `push_refused`. `skeptical-review.md`'s resume table sends you here for
  the same push, from the head's side. Push, then stamp `pushed_at`. A branch with no remote owes
  nothing, because the integration stamped it, and a round that records
  `push_refused` owes nothing either — the principal was told the head is
  unpublished. A package with no `round` came from a change request, so
  nothing records a refusal for it and a resume simply tries the push again.
- **A run owes a reply** when an entry in `run.rounds` holds a `null`
  `replied_at` and every accepted entry in its reply file is complete. The
  file is already on disk, so `reviews/<round-id>-reply.md` is sent as it
  stands and `replied_at` follows. A resumed session reaches this through
  entry 5 of `skeptical-review.md`'s resume list, which owns the order, and
  entry 4 there fills a ledger line the kill left empty.

Two obligations sit outside this rule. `run.review_pending` is
`skeptical-review.md`'s alone. A package still `pending` or `in-flight`
belongs to `simple-path.md`'s "A round killed mid-flight".

### Per-run fields (inside `run`)

| Field | Meaning |
|---|---|
| `run_state` | one of `active`, `blocked`, `delivered`, `interrupted`, `complete`. See `run_state` transitions below. `delivered` means every deliverable holds a terminal state and the session stays up for questions, changes to the PR, a review's findings and the principal's word that the work shipped (`simple-path.md`'s "The delivered window"). `complete` means that word came. |
| `session_ids` | a list, not a single id. The project lead's own session id, read from `$CLAUDE_CODE_SESSION_ID` (see below), appended to on every `--resume`, for the same reason as `worktrees.json`'s `session_ids` below. It is also what prices the run: `spend.py` reads each id's transcript subtree (Spend below). |
| `review_rounds` | an integer: how many skeptical review rounds this run has entered. Starts at 0, and absent means 0. It names the round whose files are `reviews/skeptical-r<n>.*`. `skeptical-review.md` owns when it moves, what caps it, and why a retry leaves it where it is. |
| `review_pending` | `{head, round}` — the branch head sha a skeptical review is owed on, and the round reserved for it — or `null` when none is owed. One object, not two fields, so the sha and the round it names cannot disagree. Every arming goes through `crew-record.py`'s `arm_review`, reached by `deliver --review-head` at the hand-over, by `integrate --review-head` when a delivered-window package integrates, and by `arm-review --head` on its own; `run set review_pending null` is for clearing it and nothing else. `skeptical-review.md` owns every transition and what a set value means to a resumed run. |
| `unreviewed_heads` | a list of `{head, reason, at}`, one per branch head that was handed over or pushed with no review owed for it. `reason` is `cap` today, the only case that produces one. Appended by `arm_review` in the same write that would have armed the head. Absent until the first one. A head here shipped unreviewed, and `skeptical-review.md` says who has to be told. |
| `review_results` | an object keyed by round number, each value `{exit, denials_ok, report_ok, at}`: the outcome of the four checks the project lead runs over a finished review. A round with no entry has not been checked, whatever sits in `reviews/`. Absent until the first check. `skeptical-review.md` owns the checks and what a passing entry permits. |
| `review_session_ids` | a list of session ids, one per skeptical review this run started. The project lead generates each id itself and appends it **before** it launches that review, then passes it to the review as `--session-id`, so a review that dies halfway is still priced (`skeptical-review.md` owns the procedure). `spend.py` prices these transcripts into the run and `crew-stats.py` reports them. **Both hooks ignore this field.** An id here is a foreign session, so it never goes in `run.session_ids`, whose ending marks the whole run `interrupted` (`hooks/session-end.py`, design §15.90h). Absent until the first review. |
| `repo` | the absolute path to the target-repo clone the project lead was launched in, written at `SKILL.md`'s "Take the goal" from `git rev-parse --show-toplevel`, before any step can need it — a replacement for the spec review runs from it and no branch exists yet (`SKILL.md`'s "A step the principal replaced"). On a free checkout the two are equal; on a held one, `checkout` is the worktree this run cut and `repo` is the clone it was cut from. **It is the path that outlives the run's own worktrees**, so every `worktree add`, `remove` and `prune` runs against it — the removal at "End the run", and every skeptical review (`skeptical-review.md`). Every run has one: "Take the goal" writes it before the path is chosen. |
| `rounds` | an object keyed by `<round-id>`, one entry per patch round, written by the project lead when it opens the round and before it writes any package (`simple-path.md`'s "Findings from a review"). Each value holds: `source`, the `{kind, ref}` pair below; `reply_to`, where the reply goes; `opened_at`, an ISO-8601 UTC timestamp; `replied_at`, the timestamp of the send that delivered `reviews/<round-id>-reply.md`, `null` until it happens; and `push_refused`, a `{at, reason}` written only when the remote refused this round's push twice. A round entry with a `null` `replied_at` is the one thing that says a reply is still owed, and a round with no package at all still has one, so an all-declined round knows its own reader. Absent until the first patch round. |
| `rounds[].source` | `{kind, ref}`. `kind` is one of `ci`, `pr-comments`, `principal` and `skeptical`. `ref` names the one source of that kind: the CI run's URL, the PR review thread's URL, the principal's session name or `"typed"`, or `skeptical-r<n>`. |
| `rounds[].reply_to` | where this round's reply is sent, decided by `kind` and written when the round opens. `pr-comments` is the review thread its `ref` names. **`ci` is the PR conversation**, because a CI run holds no thread to answer: the reply is a PR comment that links the run URL. `principal` is the channel the message arrived on. `skeptical` is the record alone — the reply file is the reply, and the next status message to the principal names its path. |
| `checkout` | the absolute path this run does its git work in, written at `simple-path.md`'s "Create the branch". It is the target repo the charter named, unless another run already held that checkout — then it is the worktree this run cut, registered in `worktrees.json`. Every git command, the test suite and the push run against it. It is not where the run's transcripts live: those follow the session's own working directory, which the launch fixed (design §15.90). Absent on an investigation run that ends in a report, which creates no branch. |
| `principal` | who to send an escalation to, when the goal did not arrive in this session. Set it with `run set principal '"<name>"'` from the `from-name` attribute of the `<cross-session-message>` that carried the goal — `from` only when there is no `from-name`, because `from` is a socket path that dies with its process (`autonomy-contract.md`, design §15.72f). Absent when a human typed the goal in this session, and a `--resume` session that finds it absent escalates in its own pane. |
| `created_at` | ISO-8601 UTC timestamp written by `crew-record.py init`. `spend.py` counts transcripts from it when it has to price from a checkout. |
| `delivered_at` | ISO-8601 UTC timestamp `crew-record.py` stamps once, on the first write that sets `run_state` to `delivered` — the `deliver` command, `run state delivered`, or `run set run_state delivered`. It is when the work was handed over: the PR opened, or the report ended. A later `blocked → delivered` or `interrupted → delivered` never moves it, and a run that goes `delivered → complete` keeps it, so the two stamps bound the whole delivered window. |
| `completed_at` | ISO-8601 UTC timestamp `crew-record.py` stamps on every write that sets `run_state` to `complete` — the `ship` command, `run state complete`, and `run set run_state complete`. `crew-stats.py` prices a run through this bound, or the latest `state_changed_at` when it is absent, so a `complete` run without it prices short of its own tail (design §15.51). An `interrupted` or `delivered` run never gets one, and `--resume` never sets one — only the principal's ship word does. |
| `spend` | `{transcript}`. See Spend below. |
| `escalations` | a list of questions the project lead asked the human (design §6 triggers). See Escalations below. |
| `compactions` | a list of `{session_id, agent_id, agent, trigger, at}`, appended by the `PreCompact` hook whenever a session in this run compacts. `agent` is the teammate's or subagent's name, resolved from its transcript's `.meta.json`; `null` means the project lead's own session compacted. `full-path.md`'s "Verify before you believe" and "The territory's next package" consume it. Absent until the first compaction. |
| `steps_skipped` | a list of `{step, package, deliverable, reason, at}`, one entry per step the light path let the run skip. `step` is `spec-critic`, and nothing else: a `spec-critic` entry leaves both `package` and `deliverable` `null`, because the run writes no spec and the skip belongs to the whole run. A record written before T58 or T59 can also carry a `plan-gate` or a `deliverable-review` entry, from the two steps those tickets retired (design §15.94d). Read one as history, and write neither on a new skip. Two keys, not one, because a package id and a deliverable id are not the same id space and a later session filters on one of them. `reason` is one line naming the path and the conditions that held, and `at` is an ISO-8601 UTC timestamp you write yourself — `run set` stamps nothing. `band-rubric.md`'s "What the light path skips" decides what may go in here, and nothing else may. Absent until the first skip, which is what makes an absent field mean "every step ran". Write it with `run set steps_skipped <json>`, the whole list each time. **A promotion off the light path removes the `spec-critic` entry.** The promoted run writes `spec.md` and dispatches the critic, so the step ran, and an entry that stays says a step was skipped that a review file on disk proves ran. `decisions.md`'s promotion entry holds the history of the skip. The write above sends the whole list, so the removal costs one call (design §15.91). |
| `steps_substituted` | a list of `{step, round, replacement, at, usage}`, **one entry per invocation of a replacement**, a retry included (`SKILL.md`'s "A step the principal replaced"). `step` is `spec-critic` or `skeptical-review`, and nothing else: no other step takes a replacement. `round` is the review round this invocation ran at, the same `<n>` as its report file. `replacement` is the principal's own words for what ran, such as `"use Codex for the spec review"` — crew holds no list of runners to name it from. `at` is an ISO-8601 UTC timestamp you write yourself, because `run set` stamps nothing. `usage` is an object with two optional keys, `tokens` (an integer) and `usd` (a number), holding whatever the runner reported; `null` when it reported neither. `crew-stats.py` prices `usd` and nothing else, so an entry carrying only `tokens` prints as unmeasured. **A substituted step is not a skipped step.** The step ran, and its report sits at the step's own path under `reviews/`, so `steps_skipped` gets no entry for it. Absent until the first invocation. Write it with `run set steps_substituted <json>`, the whole list each time. |
| `substitutions_requested` | a list of `{step, replacement, source}`, one entry per review step the principal named a replacement for, written at `SKILL.md`'s "Take the goal" before any step runs. `step` is `spec-critic` or `skeptical-review`. `replacement` is the principal's words. `source` is `goal`, `charter` or `launch`, naming where those words arrived. **This field is the request, and `steps_substituted` is what ran.** A resumed session reads this one, because the words that named the replacement are in no later session's context. Absent when the principal named none. Write it with `run set substitutions_requested <json>`, the whole list each time. |
| `instruments_used` | a list of `{instrument, dispatched_by, purpose, at}`, appended each time the project lead or a researcher dispatches a charter-listed instrument (design §6.4). `instrument` is the name from the charter's `Instruments:` line, `dispatched_by` is `project-lead` or `researcher`, and `purpose` is one line naming the question the dispatch answered. Absent until the first dispatch. |

**Read the session id, never invent it.** `echo $CLAUDE_CODE_SESSION_ID`
prints this session's own id, and it is the same string the `SessionEnd` hook
matches against. Run it. A plausible-looking id you wrote yourself matches
nothing, so the hook silently marks no run, and `--resume` cannot prove which
worktree it owns (design §15.39). This holds on both paths: a simple-path run
that cut no worktree still writes `run.session_ids`, and that list is what
prices it.

### `run_state` transitions

| From | To | Trigger |
|---|---|---|
| `active` or `delivered` | `blocked` | the project lead hits an escalation trigger (design §6) |
| `blocked` | `active` or `delivered` | the principal answers; the project lead records it in `escalations`. Back to `delivered` when every deliverable holds a terminal state, and to `active` otherwise |
| `active`, `blocked` or `delivered` | `interrupted` | `SessionEnd` fires on a crash (design §13.1) |
| `interrupted` | `blocked` | `--resume`, when an `escalations` entry has no `answer` yet |
| `interrupted` | `delivered` | `--resume`, when no answer is missing and every deliverable holds a terminal state |
| `interrupted` | `active` | `--resume`, when no answer is missing and a deliverable is still open |
| `active` | `delivered` | the project lead hands the work over: the draft PR opens, or the run ends in `work-complete` (`simple-path.md`'s "End the run"). `crew-record.py deliver` takes `--review-head <sha>` here and writes `run.review_pending` in the same write, so the hand-over cannot land without the review it owes (`skeptical-review.md`) |
| `delivered` | `complete` | the principal says the work shipped, and the project lead writes `ship` (`simple-path.md`'s "The delivered window") |

An `interrupted` run whose deliverables all hold a terminal state, and that
nobody resumes — a principal who typed the goal and closed the pane after the
merge — stays `interrupted` with its `delivered_at`, and `crew-stats.py`
prices it through its latest stamp.

A round of the delivered window moves `run_state` nowhere: the run stays
`delivered` while an IC works, and `decisions.md` holds what the change
request or the finding was. Only an escalation moves it, to `blocked` and
back.

**Write `delivered` before the hand-over's `spend.py --write`, and `complete`
before the last one.** The `complete` write stamps `completed_at` before the
pricing run starts, so `spend.transcript.measured_at` lands after
`completed_at`. `crew-stats.py` prefers a stored `spend.transcript` over
recomputing one, so a run priced in this order keeps its own tail — the turns
that answered the last question and wrote the closing summary. The figure
written at the hand-over is what the closing report states; the one written
at `ship` adds the delivered window, and it is the one that stands.

### Spend

Spend is measured from the transcripts, not from agent notifications, because
the transcripts are the only count that includes the project lead's own
session and the teammates (design §8, §15.50).

No figure gates a run. `spend` is a report the closing summary states and
`crew-stats.py` totals, and nothing stops on it (design §8, §15.76).

| Field | Meaning |
|---|---|
| `transcript` | written by `scripts/spend.py --write`: `{measured_at, total_tokens, usd_list_price, by_model}` over the transcripts of this run's own sessions — each id in `run.session_ids`, with the subagents and in-process teammates under it, plus each id in `run.review_session_ids`. `autonomy-contract.md` says when to run it. |

**A run is priced by its sessions, not by its checkout.** Claude Code names a
transcript directory for the session's working directory, so two runs launched
into one checkout write into one directory and a directory-wide count bills
each for the other's work — $8.85 and $9.71 for two runs that cost $4.52 and
$5.51 (design §15.88f, §15.90). A session subtree holds one run and nothing
else, so it is the bound that holds however many runs share a tree. A worktree
does not separate transcripts: the session's directory was fixed at launch.

`spend.py` falls back to the checkout for a record whose sessions wrote no
transcript, and `crew-stats.py` then closes the window at `completed_at`
(design §15.51).

### Escalations

| Field | Meaning |
|---|---|
| `trigger` | which design §6 trigger fired |
| `question` | what the project lead asked |
| `asked_at` | ISO-8601 UTC timestamp |
| `answer` | `null` until the human responds; a non-`null` value flips `run_state` from `blocked` back to the state it left, `active` or `delivered` |

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
      "pr_url": null,
      "checkout_branch": "main",
      "checkout_restored": null
    }
  ],
  "run": {
    "run_state": "active",
    "session_ids": ["8154734d-d163-4d22-8946-83c3b12cb6f2"],
    "created_at": "2026-08-30T14:02:11Z",
    "checkout": "/Users/dev/src/app",
    "spend": {
      "transcript": {
        "measured_at": "2026-08-30T16:40:03Z",
        "total_tokens": 41200000,
        "usd_list_price": 23.10,
        "by_model": { "opus": { "messages": 140, "input": 300, "cache_write_5m": 0, "cache_write_1h": 420000, "cache_read": 38000000, "output": 90000, "usd": 20.35 }, "sonnet": { "messages": 60, "input": 120, "cache_write_5m": 310000, "cache_write_1h": 0, "cache_read": 2400000, "output": 12000, "usd": 2.75 } }
      }
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

**One entry per worktree the run cut, on either path.** The full path cuts one
per territory, keyed by the IC's name. Either path cuts one for the
deliverable when another run already held the checkout, and that entry is
keyed by the deliverable id, because no IC owns it (`simple-path.md`, "Create
the branch"). A run that cut none writes no file. **A review worktree is not one of these.**
It lives under `<record-dir>/review-worktrees/`, the project lead alone makes
and removes it, and nothing registers it here (`skeptical-review.md`).

**An entry lives exactly as long as its worktree.** The step that removes a
worktree deletes the entry. Never add a field that says the worktree is gone:
the entry is what proves a worktree is this run's to remove, and a removed
worktree needs no proof. A run that removed every worktree it cut leaves the
file holding `{}` (design §15.90g).

**The path convention** is `<record-dir>/worktrees/<territory-slug>`, or
`<record-dir>/worktrees/<deliverable-id>` for a deliverable checkout, and
the IC on a territory is named `ic-<territory-slug>`. `<record-dir>` is the
goal directory this file opens with — `<record-root>/<goal-slug>/` — and not
the record root itself, whose goal directories two runs of one charter share.
The goal slug carries the run's random suffix, so the path is unique per run
(design §15.34, §15.90). The root sits outside
the target repo: a test runner that globs collects every worktree's tests as
well as the repo's own, so a repo-local root makes the suite measure the wrong
tree (design §15.35b, §15.37f).

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
the run's `run_state` was `active`, `blocked` or `delivered` and its
`session_ids` hold the ending session's id — and then only the worktrees
carrying that same id. A run already `complete` is left alone whatever its
worktrees say, because a finished run's leftovers are work for
`full-path.md`'s "Clean up", not an orphan. `--resume` clears it once a worktree is reconciled. It is a
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

### A preference-sweep entry

`autonomy-contract.md`'s sweep writes one entry before the split, on every
run, including a run that found nothing.

**A sweep entry starts like a council entry.** Before the ask it carries the
questions and `Answer: pending`, which proves the routing came first. The
principal's reply completes each answer: one `Answer:` line per question, each
naming the question it settles, so `decisions.md` holds what was decided and
not only that something was asked. A sweep that found nothing is finished in
one write, with `Answer: none`.

`Citation:` names the files the sweep read. Each escalated question also gets
its own `escalations` entry, written with `escalation add` above, so one
batch reads as one interruption in `state.json` too.

```markdown
## Preference sweep: what does the principal want that the repo cannot say?
Route: preference
Questions: 1. Does each book get its own route? 2. Is the old URL kept?
Answer: 1. Yes, one route per book — recorded in CLAUDE.md. 2. No — not recorded.
Citation: charter.md and spec.md hold no other open question that an
instruction, a prior decision or repo precedent settles.
Confidence: high
Timestamp: 2026-08-24T14:32:00Z
```

`Questions:` is the sweep's own field, and it holds every question the sweep
escalated, in the order it asked them. An entry with `Answer: none` needs no
`Questions:` line.

**Each answer ends with where it was written back**: the target repo file
that now carries it as a rule, or `not recorded` when the principal refused
(`autonomy-contract.md`). That lets an audit tell a refusal from a step the
run skipped.

That makes the sweep entry the one entry written three times. The reply
completes every answer; the file name lands later, at integration, because
that is when the rule is written and the container check can move it. Reopen
the entry there and finish the line.

### A council entry

A council-route entry carries five more lines (design §6.1). `Prior`,
`Positions` and `Losing` are what let an audit see the whole council rather
than its winner.

**A council entry is written twice.** `autonomy-contract.md` has the project
lead write the question, `Route: council`, `Prior` and `Positions` **before**
it dispatches, which is what proves the routing came first. At that point no
answer exists, so `Answer` and `Confidence` both read `pending`, and
`Citation`, `Losing`, `Models`, `Spend` and `Timestamp` are absent. The
adjudication fills them in. `pending` is the only sanctioned placeholder, and
the no-citation-at-high-confidence check does not apply to an entry still
holding it.

- `Prior:` — the project lead's own answer, and the confidence it held that
  answer at, as `<the answer> (<high | medium | low>)`. Every council entry
  carries it. An investigation council with no leading hypothesis writes
  `Prior: none`. Never rewrite it to match the winner: the whole point of the
  line is that a later pass can compare it with `Answer:`.
- `Positions:` — every position the project lead framed, in the order they
  were framed. An adversary council holds two: the prior, and the position the
  advocate argued against it. Never reorder them once the winner is known. On
  a three-advocate entry that order is what shows an audit the council did not
  simply ratify its first option. On an adversary entry the prior sits first
  by construction, so `Prior:` carries that evidence instead: it says what the
  project lead held before the advocate reported.
- `Losing:` — one line per losing position: the best argument it made, and why
  it lost. On an adversary entry whose prior survived, this line is the
  project lead's written rebuttal of the adversary's strongest point. A
  position whose advocate conceded (design §9.5) made no argument, so its line
  reads `conceded` and carries the citation that contradicted it.
- `Models:` — the model every advocate ran, as `1 advocate, <model>` or
  `<n> advocates, <model>`.
  Every advocate in one council runs the same model (`band-rubric.md`), so
  this is one value, not one per advocate. Name your own adjudicating model
  after it.
- `Spend:` — the advocates' `total_tokens`, summed from their completion
  notifications; `unmeasured` when a dispatch shape reported none.

The default shape, one adversary against the project lead's prior:

```markdown
## Where does the retry budget live: the client or the call site?
Route: council
Prior: the client owns it (medium)
Positions: A. the client owns it. B. each call site owns it.
Answer: A — the client owns it.
Citation: src/http/client.ts:44 already holds the timeout and the backoff, and
CLAUDE.md "HTTP" says one place owns transport policy.
Losing: B argued call sites vary (src/sync/push.ts:80 retries 5 times). The
client's per-request override at src/http/client.ts:61 already covers that,
so the variation costs no second owner.
Confidence: high
Models: 1 advocate, sonnet. Adjudicated at opus.
Spend: 14800 tokens
Timestamp: 2026-08-24T14:32:00Z
```

A three-advocate council (`autonomy-contract.md` names the two cases that earn
one) writes the same fields. `Positions` then holds three, `Losing` one line
per loser, and `Prior` the low-confidence answer that triggered it.

A balanced council is not an entry to finish alone. When the project lead
cannot pick a winner at medium confidence or better and the question is
architecture-moving, it escalates (`autonomy-contract.md`), and the entry's
`Answer` is the principal's.

## The portfolio record

One directory per lead, beside the goal records under the same root (design
§1, §15.70):

```
<record-root>/lead-<YYYY-MM-DD>-<4 hex chars>/
├── portfolio.json    every item, its state, and what the lead expects next
├── decisions.md      every answer the principal gave, and every call the lead made
├── charters/         one charter per item, charters/<item-id>.md
└── runs/<item-id>/   the item's own record root, one directory per item
```

The suffix rule is the goal slug's (Goal-slug uniqueness above), and for the
same reason: two leads on one machine share no lock.

**A lead finds its portfolio by glob, never by memory.** Every start reads
`<record-root>/*/portfolio.json` and takes the one whose `lead.state` is not
`closed`. Two open portfolios is a question for the principal, not a guess.
That glob is what makes the record the ledger and the context a cache of it
(`skills/lead/SKILL.md`).

**`runs/<item-id>/` is the item's `CREW_RECORD_ROOT`.** The lead exports it
when it launches the item's project-lead session, so the run's own record
lands under the portfolio and the lead finds it with one glob. A launcher
never learns the session id of the session it launched (design §15.72b), and
the goal slug carries a random suffix, so a predictable root is the only
thing that maps an item to its record without a message.

**Write `portfolio.json` with `scripts/crew-portfolio.py`**, beside the lead
skill:

```
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> init "<title>" <portfolio-slug> "$CLAUDE_CODE_SESSION_ID"
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> session-id "$CLAUDE_CODE_SESSION_ID"
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> lead state closed
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> lead set principal '"jerridan"'
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> item add '<json object>'
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> item <id> state running
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> item <id> set record_dir '"/abs/path"'
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> item <id> set gate.cleared_at '"2026-09-11T18:04:11Z"'
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> item <id> expect "<one line>"
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> escalation add <item-id> "<question>"
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> escalation answer <index> "<answer>"
```

The rules are `crew-record.py`'s, for the same reasons: never write
`escalations` with `lead set`, which replaces the whole list; a `set` value
is JSON and carries its own quotes; and the script checks no field and no
transition, because this file owns both. Both `set` verbs take a dotted field
and create the objects on the way to it, so a gate's fields are written one
call at a time; a path through anything that is not an object exits with a
message. `expect` is the exception that takes plain text, because it is
rewritten every turn. `init` also creates
`charters/` and an empty `decisions.md`, and `item add` refuses an id the
portfolio already holds. Every call stamps `lead.updated_at`.

**Never rewrite `portfolio.json` by hand.** Both hooks append to it, and a
whole-file write from the lead drops whatever a hook wrote since the lead read
it — a `lead.compactions` entry above all, which the lead reads a turn later
to learn its own context was cut. The script does the same read and write, but
in one process and in milliseconds rather than across a turn. That narrows the
window; it does not close it, and no lock exists to.

### Per-lead fields (inside `lead`)

| Field | Meaning |
|---|---|
| `state` | one of `active`, `interrupted`, `closed`. `interrupted` is written by `SessionEnd` when a live lead session ends; the next `/crew:lead` sets it back to `active`. `closed` is the principal's word that the portfolio is finished, and it is what takes the portfolio out of the glob above. |
| `session_ids` | a list, appended to on every start, never overwritten — `run.session_ids`' rule, for `SessionEnd`'s sake. |
| `principal` | who to send an escalation to, by `autonomy-contract.md`'s "Reach the principal". Absent when the human typed the brief in this session, which is the usual case. |
| `created_at` | ISO-8601 UTC, written by `init`. |
| `updated_at` | ISO-8601 UTC, stamped on every write. It says when the portfolio last moved; it never chooses between two open portfolios, which is a question for the principal (above). |
| `escalations` | a list of `{item, question, asked_at, answer}` — what the lead asked the principal, and what came back. `item` names the item the question belongs to, in place of the goal record's `trigger`: a lead's questions come from its items, not from design §6's trigger list. An entry with `answer: null` is open, and a restarted lead re-sends it. |
| `compactions` | a list of `{session_id, agent_id, agent, trigger, at}`, appended by the `PreCompact` hook, in `run.compactions`' shape. Absent until the first compaction. It is how a lead learns its context was cut rather than merely short. |
| `spend` | what the lead's own sessions cost, in `run.spend.transcript`'s shape: `{measured_at, total_tokens, usd_list_price, by_model}`. Written by `scripts/lead-spend.py --write`, not by `crew-portfolio.py`. See Lead spend below. |

### Lead spend

A lead runs from no checkout and writes no `state.json`, so `spend.py` cannot
find it and the tier's own cost goes uncounted — 20%, 30% and 47% of the
three portfolios measured (design §15.76, §15.80h). `scripts/lead-spend.py` prices the lead
instead, from the transcripts of the sessions in `lead.session_ids`:

```
python3 <lead-skill-dir>/scripts/lead-spend.py <portfolio-dir> [--write]
```

It prices whole sessions, because every turn of a lead session belongs to the
portfolio. It imports `spend.py` for the price table, so there is one table.

**Run it with `--write` each time an item reaches `done` or `abandoned`**, and
again before `lead state closed`. The figure covers the portfolio to that
moment, so a later item raises it. A lead that never runs it leaves
`lead.spend` absent, and `crew-stats.py` prints the portfolio's runs with no
lead cost beside them.

**Only the lead's own seat is in this figure.** Every item runs under a
project-lead session of its own, and that session's `state.json` holds what the
item cost. The two figures add up, and neither holds the other.

The last write always reads short by its own turn: the tokens the closing
turn spends after the measurement land in no figure (design §15.76). Nothing
fixes that from inside the session being measured.

This is the one figure the lead keeps in `portfolio.json` about spend. A
run's own cost stays in its `state.json` (Authority rule below).

### Per-item fields

| Field | Meaning |
|---|---|
| `id` | the item's identity. Names its charter (`charters/<id>.md`), its record root (`runs/<id>/`) and the session that runs it. |
| `title` | one line, from the principal's brief. |
| `repo` | the absolute path to the target-repo checkout this item runs in. |
| `charter` | `charters/<id>.md`, relative to the portfolio directory. |
| `record_dir` | the absolute path to this item's own record — the single directory under `runs/<id>/`. `null` until the run creates it. |
| `session_name` | the `--name` the item's project-lead session was launched under. It is the address `SendMessage` takes, and it survives a restart, which a socket path does not (design §15.72f). |
| `state` | one of `pending`, `held`, `running`, `blocked`, `delivered`, `done`, `abandoned`. See the transitions below. |
| `state_changed_at` | ISO-8601 UTC timestamp of this item's last `state` transition. |
| `expect` | one line: what the lead expects next on this item, and what it will do when that arrives. It is the ledger — a restarted lead reads this line and knows what its own last turn was waiting for. |
| `outcome` | the PR url, or the terminal state the run reported; `null` until the item is `delivered` or `abandoned`. |
| `depends_on` | the id of the item this one waits for, or `null`. It is how one goal becomes several stages in dependency order (design §15.87). |
| `gate` | the condition that must hold before this item starts. Absent unless the principal named one. The gate record below owns its fields. |

An item's `state` is the **lead's** view of the item, not the run's. The run's
own state lives in `record_dir`'s `state.json`, and that file stays
authoritative for the run (Authority rule below). The lead never copies a
package, a band or a run's spend into `portfolio.json`; it reads them where
they live. `lead.spend` is not an exception: it is the lead's own cost, and
no `state.json` holds it.

**Every item holds the same fields.** The lead does not size an item, so
nothing here branches on size and no item carries a second shape beside the
run record (design §15.88). A portfolio written before that rule can still hold
an `items[].task` object; nothing reads it now.

### Item state transitions

```
        ┌──▶ held ──┐
        │           ▼
pending ┴──────▶ running ──▶ delivered ──▶ done       (terminal)
                   │  ▲          │  ▲
                   ▼  │          ▼  │
                blocked        blocked

any non-terminal state ──▶ abandoned                  (terminal)
```

- `pending → running`: the charter is written, a project-lead session is
  launched, and the charter is handed to it.
- `pending → held`: this item carries a `gate`, and the item its `depends_on`
  names reached `delivered`. The gate fires when the upstream PR opens, not at
  the ship word. Only a gated item enters `held`.
- `held → running`: the principal cleared the gate, and `gate.cleared_at` says
  when. Nothing else opens a gate — a check whose output matched is still not
  the go (design §15.87e).
- `running → blocked` or `delivered → blocked`: the item is waiting on an
  answer only the principal can give. The matching `escalations` entry is what
  says which question.
- `blocked → running` or `blocked → delivered`: the lead sent the answer on.
  The item goes back to the state it left.
- `running → delivered`: the run's `state.json` shows `run_state: delivered`.
  The work is handed over — `outcome` holds the PR url or the state — and the
  session stays up for questions and follow-ups (`skills/lead/SKILL.md`, "A
  delivered item keeps its session").
- `delivered → done`: the principal said the work shipped, the lead passed the
  word down, and the run's `state.json` shows `run_state: complete`.
- `delivered → abandoned`: the principal dropped the item after the hand-over.
  Its run stays `delivered` in its own record until the hook marks it
  `interrupted`, and the lead kills the delivered window
  (`session-launch.md`, "Closing it").
- any non-terminal state `→ abandoned`: the principal dropped the item, or the
  run failed in a way no resume fixes. A `held` item whose gate the principal
  will never clear ends here. So does an item whose `depends_on` ended
  `abandoned`: the stage it was built on is not coming, its gate can never
  fire, and a `pending` item with a dead upstream would sit in the portfolio
  for good.

A check's output moves no state. Whatever `gate.check_output` holds, only the
principal's go takes an item out of `held` (`skills/lead/SKILL.md`).

**A `delivered` or `done` item needs the record, not a message.** A project
lead's closing report can be lost — the send fails when the lead session has
restarted (design §15.72g) — so the lead confirms `delivered` and `complete`
by reading `record_dir`'s `state.json`, never by waiting for a report.

### The gate record

A gate is what the principal wants true before a stage starts (design §15.87).
An item carries a `gate` object only when the principal named one. The gate
sits on the item that waits, never on the item that runs first, so the last
stage of a goal carries none.

| Field | Meaning |
|---|---|
| `condition` | one line, in the principal's own words: what must be true before this item starts. |
| `check` | the shell command the principal named, run verbatim from the portfolio directory; `null` when the principal named no command. The lead never writes one itself and never edits one. |
| `expect_output` | what the principal said that command's output should hold; `null` when there is no command. It is the only comparison the lead may make. |
| `checked_at` | ISO-8601 UTC of the last run of `check`; `null` until the first run, and `null` for the life of a gate whose `check` is `null`. |
| `check_output` | what that run printed, trimmed to 500 characters, or the error it failed with. It is evidence for the principal to read, never a verdict. `null` beside a `null` `check`. |
| `cleared_at` | ISO-8601 UTC of the principal's go; `null` while the gate holds. |
| `escalation` | the index in `lead.escalations` of the ask that carries the gate report. That entry's `answer` is the go. |

Write the object whole at `item add` time, then one field per call. A
whole-object rewrite drops what the last call put there:

```
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> item <id> state held
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> item <id> set gate.check_output '"state: MERGED"'
python3 <lead-skill-dir>/scripts/crew-portfolio.py <portfolio-dir> item <id> set gate.cleared_at '"2026-09-07T18:04:11Z"'
```

A gated item, held:

```json
{
  "id": "slugify-path-4b7c",
  "title": "Add slugifyPath, built on stage 1's slugify",
  "depends_on": "slugify-2e19",
  "state": "held",
  "state_changed_at": "2026-09-07T17:58:02Z",
  "expect": "the principal's go on the stage 1 merge; then launch this stage",
  "outcome": null,
  "gate": {
    "condition": "the stage 1 PR is merged into main",
    "check": "gh pr view 31 --repo jerridan/crew-fixture-string-kit --json state",
    "expect_output": "MERGED",
    "checked_at": "2026-09-07T17:58:44Z",
    "check_output": "{\"state\":\"MERGED\"}",
    "cleared_at": null,
    "escalation": 0
  }
}
```

### `decisions.md`

The portfolio's own decision log, in the goal record's `decisions.md` shape
and with its rules: one entry per question, `Route`, `Answer`, `Citation`,
`Confidence`, `Timestamp`, and the clock read rather than remembered.

Two things go in it, and nothing else:

- **Every answer the principal gives.** `Route: preference`, and the
  `Citation:` names the item the question came from. A restarted lead reads
  this file before it asks anything, so it never asks twice.
- **Every call the lead makes for a project lead** — a question it answered
  from a charter or a record instead of passing on. `Route: precedent`, and
  the `Citation:` names the charter line or the record path that settled it.

A size call is not one of them. The project lead sizes its own work and writes
that entry into its own `decisions.md` (design §15.88).

A preference the principal states in passing — "always squash", "never touch
the changelog" — is an entry too. It is the answer to the next question, and
nothing else in the portfolio holds it.

### Worked example

```json
{
  "title": "Wednesday: string-kit roadmap",
  "portfolio_slug": "lead-2026-09-05-a1b2",
  "lead": {
    "state": "active",
    "session_ids": ["3355ca2a-1f0e-4c22-9c31-6b0d51a9e004"],
    "created_at": "2026-09-05T13:02:11Z",
    "updated_at": "2026-09-05T13:44:52Z",
    "spend": {
      "measured_at": "2026-09-05T17:12:40Z",
      "total_tokens": 21400000,
      "usd_list_price": 12.29,
      "by_model": { "fable": { "messages": 62, "input": 1400, "cache_write_5m": 480000, "cache_write_1h": 0, "cache_read": 20800000, "output": 24000, "usd": 12.29 } }
    },
    "escalations": [
      {
        "item": "truncate-7f31",
        "question": "Does truncate count the ellipsis inside the limit?",
        "asked_at": "2026-09-05T13:31:09Z",
        "answer": "Yes — the result is never longer than the limit."
      }
    ]
  },
  "items": [
    {
      "id": "truncate-7f31",
      "title": "Add truncate to the string-kit roadmap",
      "repo": "/tmp/string-kit",
      "charter": "charters/truncate-7f31.md",
      "record_dir": "/Users/x/.claude/crew/lead-2026-09-05-a1b2/runs/truncate-7f31/truncate-a75d",
      "session_name": "crew-pl-truncate-7f31",
      "state": "running",
      "state_changed_at": "2026-09-05T13:44:52Z",
      "expect": "the closing report with a PR url; then read state.json and set delivered",
      "outcome": null
    },
    {
      "id": "pad-start-9c04",
      "title": "Add padStart to string-kit, with one test",
      "repo": "/tmp/string-kit",
      "charter": "charters/pad-start-9c04.md",
      "record_dir": "/Users/x/.claude/crew/lead-2026-09-05-a1b2/runs/pad-start-9c04/pad-start-5e12",
      "session_name": "crew-pl-pad-start-9c04",
      "state": "running",
      "state_changed_at": "2026-09-05T13:40:03Z",
      "expect": "the closing report with a PR url; then read state.json and set delivered",
      "outcome": null
    }
  ]
}
```

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
- `diagnosis.md` — writer: the project lead on the investigation path (design §9.5). Consumer: the fix package's spawn prompt and the PR body; a later run reading `## Ruled out` as precedent (design §6.2)
- `diagnosis.md` headings `Reproduction`, `Evidence`, `Root cause`, `Ruled out`, `Outcome` — consumer: design §9.5
- `Outcome` values `fix` and `no change` — consumer: design §9.5; this file's `in-flight → work-complete` transition
- `split.md` — consumer: stage 3 (`crew:split-critic` and the `split.md` format)
- `state.json` — consumer: stage 4 (project lead loop); stage 5 (recovery, design §10.1)
- `decisions.md` — consumer: stage 6 (council + routing); Task 11 (copied into the PR body)
- `worktrees.json` — consumer: stage 5 (full path: worktrees, merges, recovery); `simple-path.md`'s "End the run" (the deliverable checkout it removes, design §15.90)
- `reports/` — consumer: Task 6 (`ic-contract.md` report contract); `simple-path.md` and `full-path.md` "Verify before you believe"; design §7 (the red commit's sha and its failing output)
- `plans/` — consumer: Task 6 (`ic-contract.md`, "Write your plan first"); Task 7 (`crew:ic`)
- `evidence/` — writer: a `crew:researcher`, at the path its dispatch names; the project lead itself for an `Explore` subagent's finding, and for a researcher whose write was denied. Consumer: `investigation-path.md` Phases 1 to 3; every advocate in an investigation council (design §9.5); `diagnosis.md`'s `## Evidence`
- `reviews/` — writer: each review agent, at the path its dispatch names (`review-output.md`); the project lead transcribes a report whose write was denied, and writes the report itself for a substituted step (`SKILL.md`). Consumer: stage 3 (`split-critic` output); `simple-path.md`'s "The skeptical review" (the skeptical review's report)
- `charter.md` `Favour:` line — consumer: `full-path.md`'s "Write the split" (split shape)
- `charter.md` `Instruments:` line — consumer: design §6.4 (what the project lead or a researcher may dispatch)
- `run.checkout` — writer: the project lead, at `simple-path.md`'s "Create the branch". Consumer: every later git command of the run, and a human asking which tree the work happened in (design §15.90)
- `run.session_ids` — writer: the project lead, at `init` and on every `--resume`. Consumer: `hooks/session-end.py` and `hooks/pre-compact.py` (which run this session belongs to); `scripts/spend.py` (the transcripts that price the run, design §15.90)
- `run.repo` — writer: the project lead, at `SKILL.md`'s "Take the goal". Consumer: a replacement for the spec review, which runs from it (`SKILL.md`); `simple-path.md`'s "End the run" (the worktree it removes); `skeptical-review.md` (every review worktree)
- `run.review_rounds` — writer: the project lead, on first entry into a round (`skeptical-review.md`). Consumer: `skeptical-review.md` (the cap, and the round's file names)
- `run.unreviewed_heads` — writer: `crew-record.py`'s `arm_review`, through either command, when the cap stops a head being armed. Consumer: the project lead's next report to the principal (`skeptical-review.md`)
- `run.review_results` — writer: the project lead, after the four checks over a finished review. Consumer: `skeptical-review.md` (whether a report may be adjudicated)
- `run.review_pending` — writer: `crew-record.py`'s `arm_review`, through `deliver --review-head`, `integrate --review-head` and `arm-review --head`; the project lead clears it with `run set`. Consumer: `skeptical-review.md` (whether a resumed run owes a review, and on which head)
- `run.rounds` — writer: the project lead, when it opens a patch round, again at a push or a refusal, and again at the reply's send (`simple-path.md`'s "Findings from a review"). Consumer: this file's "What a delivered-window round still owes"; `packages[].round` points into it
- `run.review_session_ids` — writer: the project lead, before it launches each skeptical review (`skeptical-review.md`). Consumer: `scripts/spend.py` and `scripts/crew-stats.py` (the transcripts that price the review into the run). Neither hook reads it
- `run.created_at` — writer: `crew-record.py init`. Consumer: `scripts/spend.py` (the checkout fallback only)
- `run.delivered_at` — writer: `crew-record.py`, on the first `deliver`, `run state delivered`, or `run set run_state delivered`. Consumer: `scripts/crew-stats.py` (the end of an `interrupted` run that has delivered); a human, or a later session, asking when the work was handed over and how long the delivered window ran
- `run.completed_at` — writer: `crew-record.py`, on `ship`, `run state complete`, and `run set run_state complete`. Consumer: `scripts/crew-stats.py` (`run_end`, design §15.51)
- `run.compactions` — writer: `hooks/pre-compact.py`. Consumer: `full-path.md`'s "Verify before you believe" (re-verify after an IC compacts) and "The territory's next package" (respawn)
- `run.instruments_used` — writer: the project lead or a researcher, on every instrument dispatch. Consumer: design §6.4 (audit of instrument use)
- `run.substitutions_requested` — writer: the project lead, at `SKILL.md`'s "Take the goal". Consumer: `SKILL.md`'s "A step the principal replaced" (which step takes a replacement, in this session and in every resumed one)
- `run.steps_substituted` — writer: the project lead, at each substitution `SKILL.md`'s "A step the principal replaced" allows. Consumer: `scripts/crew-stats.py` ("Steps the principal replaced"); a human, or a later session, asking what ran in a review step's place (design §15.94d)
- `run.steps_skipped` — writer: the project lead, at each skip `band-rubric.md`'s "What the light path skips" allows. Consumer: `scripts/crew-stats.py` ("Steps skipped by rule"); a human, or a later session, asking which steps ran (design §15.77)
- `run.spend.transcript` — writer: `scripts/spend.py`. Consumer: `scripts/crew-stats.py`, the closing report, design §8

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
- `state` (deliverable) — consumer: stage 5 (integration and re-plan, design §9.3, §10); shares `pending`/`in-flight`/`abandoned` with a package's `state`. `integrated` is a package's alone; `draft-pr-opened` and `work-complete` are a deliverable's alone
- `state_changed_at` (deliverable) — consumer: a human auditing the record's timeline; stage 6
- `pr_url` — consumer: stage 4 (draft PR opened in `draft-pr-opened`, design §9.3); Task 11
- `checkout_branch` — consumer: stage 4 (`simple-path.md`'s "End the run" switches the checkout back to it, design §15.54)
- `checkout_restored` — consumer: a human, or a next session, asking why the checkout is on the deliverable branch (design §15.54)

**`state.json` per-package fields**
- `id` — consumer: this file's `reports/<id>.md` and `plans/<id>.md` naming; stage 3 (`split-critic` identifies packages)
- `deliverable` — consumer: stage 5 (per-deliverable integration, design §9.3); cross-references `deliverables[].id`
- `territory` — consumer: stage 5 (one IC dispatched per territory, design §5)
- `state` — consumer: stage 4 (project lead loop); stage 5 (re-planning and recovery, design §10)
- `state_changed_at` — consumer: a human auditing the record's timeline; stage 6
- `band` — consumer: Task 5 (`band-rubric.md` defines what each value means and when to promote)
- `band_history` — consumer: Task 5 (band-rubric.md's promotion-logging rule); stage 5 (promotion on `BLOCKED`/exhausted fix rounds/idle)
- `file_set` — consumer: Task 7 (`crew:ic` self-review checks its diff against this); stage 3 (`split-critic` disjointness check)
- `interface_contract` — consumer: stage 3 (`split-critic` type-consistency check); Task 7/Task 8 (IC spawn prompt carries it, design §9.2 step 2)
- `acceptance_criterion` — consumer: Task 6 (`ic-contract.md`, tells the IC when to stop); `simple-path.md` and `full-path.md` "Verify before you believe" (the project lead runs it)
- `base` (package) — consumer: stage 5 (the review diff and the verification range, `<base>..HEAD`)
- `fix_rounds_used` — consumer: stage 5 (the fix-round breaker, design §9.2 step 6)
- `nudges_used` — consumer: the project lead's idle nudge (`full-path.md`'s "The idle nudge")
- `ic_name` — consumer: `worktrees.json` (this file); stage 5 (project lead finds the worktree to verify)
- `plan_path` — consumer: Task 6 (`ic-contract.md`, "Write your plan first"); Task 7 (`crew:ic` writes it)
- `report_path` — consumer: Task 6 (`ic-contract.md` report contract); the project lead at "Verify before you believe"
- `round` — consumer: `simple-path.md`'s "Findings from a review" (which round's reply and source this package belongs to); this file's `run.rounds`
- `pushed_at` — consumer: this file's "What a delivered-window round still owes" (a package that still owes a publication)

**`state.json` state values** (shared by `packages[].state` and
`deliverables[].state`, except `integrated`, `draft-pr-opened`, and
`work-complete`)
- `pending` — consumer: stage 4/5 (project lead loop dispatches from this state)
- `in-flight` — consumer: stage 5 (project lead loop, idle check)
- `integrated` (package only) — consumer: stage 5 (integration step, design §9.3); design §10 (re-plan rule)
- `draft-pr-opened` (deliverable only) — consumer: stage 4 (project lead opens the draft PR, design §9.3); Task 11 (PR body)
- `work-complete` (deliverable only) — consumer: stage 4 (`simple-path.md`'s "End the run"); stage 5 (`full-path.md`'s "Open the draft PR"); the investigation path's report ending (design §9.5)
- `abandoned` — consumer: design §10 (re-plan and breaker outcome); stage 5

**`state.json` band values** (canonical definitions live in Task 5's
`band-rubric.md`)
- `light` — consumer: Task 5 (`band-rubric.md`)
- `standard` — consumer: Task 5 (`band-rubric.md`); this file's worked example
- `deep` — consumer: Task 5 (`band-rubric.md`); this file's worked example

**`state.json` per-run fields**
- `run_state` — consumer: crew's `SessionEnd` hook (writer, `hooks/session-end.py`); stage 5
- `run_state` values `active`, `blocked`, `delivered`, `interrupted`, `complete` — consumer: this file's `run_state` transitions table; both crew hooks; `skills/lead/SKILL.md` (`delivered`, which sets the item `delivered`); stage 5, stage 6
- `run.session_ids` — consumer: stage 5 (resume, matches this run's project lead sessions)
- `run.repo` — consumer: stage 5 (every worktree command of the run)
- `run.review_rounds` — consumer: `skeptical-review.md` (the cap)
- `run.unreviewed_heads` — consumer: the principal, told which heads shipped unreviewed
- `run.review_results` — consumer: stage 5 (resume, which adjudicates only a checked report)
- `run.review_pending` — consumer: stage 5 (resume in `delivered`, which owes a review on `head` when it is set)
- `run.review_session_ids` — consumer: `scripts/spend.py` (pricing); never the hooks
- `run.principal` — consumer: `autonomy-contract.md` (The principal); stage 5 (resume, which reads it instead of a message it no longer has)
- `spend` — consumer: design §8, `scripts/crew-stats.py`
- `escalations` — consumer: stage 6 (design §6 triggers); this file's `run_state` transitions table
- `escalations[].trigger` — consumer: stage 6
- `escalations[].question` — consumer: stage 6; the human answering it
- `escalations[].asked_at` — consumer: stage 6 (ordering, this file's timestamp rule)
- `escalations[].answer` — consumer: stage 6 (flips `run_state` back to the state it left, `active` or `delivered`)

**`state.json` `band_history` entry fields**
- `predicted` — consumer: Task 5 (`band-rubric.md`'s promotion-logging rule); stage 5
- `actual` — consumer: Task 5 (`band-rubric.md`'s promotion-logging rule); stage 5
- `cause` — consumer: Task 5 (`band-rubric.md`'s promotion-logging rule); stage 5
- `at` — consumer: a human auditing the record's timeline; stage 6

**`worktrees.json` fields**
- `worktree` (path) — consumer: stage 5 (project lead verifies an IC against this path, design §7); `<record-dir>/worktrees/<territory-slug>`
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
- `Prior` — consumer: stage 6 (council entries only, design §6.1); a later pass measuring whether the adversary moved the answer
- `Positions` — consumer: stage 6 (council entries only, design §6.1)
- `Losing` — consumer: stage 6 (council entries only, design §6.1)
- `Models` — consumer: stage 6 (council entries only); Task 5 (`band-rubric.md`'s promotion data covers councils, design §15.9)
- `Spend` — consumer: stage 6 (council entries only)
- `Timestamp` — consumer: a human auditing the record's timeline; stage 6

**Goal-slug format**
- `<kebab-case-slug>-<4 lowercase hex chars>` — consumer: stage 4 (project lead generates it when creating the record directory)

**Filename conventions**
- `reports/<id>.md` — consumer: Task 6 (`ic-contract.md` report contract); the project lead at "Verify before you believe"
- `plans/<id>.md` — consumer: Task 6 (`ic-contract.md`); Task 7 (`crew:ic`)
- `reviews/<deliverable-id>-split-critic-r<n>.md` — consumer: stage 3 (`split-critic` output, one file per re-plan of this deliverable); stage 6 (re-plan, design §10)
- `reviews/skeptical-r<n>.md` — writer: the skeptical review's own headless session, or the project lead when the fallback supplies it (`skeptical-review.md`). Consumer: `simple-path.md`'s "The skeptical review"; `scripts/crew-stats.py` (the review kind and its catch rate)
- `reviews/skeptical-r<n>-instructions.md` — writer: the project lead, before it launches that review. Consumer: `--append-system-prompt-file` on the review's own command; a human asking what the reviewer was told
- `reviews/skeptical-r<n>-result.json` — writer: the shell redirect on the review's own command. Consumer: the project lead's four checks, live and on a resume
- `reviews/skeptical-r<n>-result.txt` — writer: the shell redirect on a replacement's own command, in place of the `.json` (`SKILL.md`). Consumer: the project lead, which reads the report out of it and runs the checks the runner supports
- `reviews/skeptical-r<n>-result.exit` — writer: the same shell line, one line holding the runner's exit status. Consumer: the project lead's exit check, live and on a resume; its absence marks an attempt that never finished (`SKILL.md`)
- `reviews/skeptical-r<n>-reply.md` — writer: the project lead, before it creates any package from that report. Consumer: a resumed session, which reads it to see which findings already have packages (`skeptical-review.md`)
- `reviews/<round-id>-reply.md` — the same file for a patch round from any other source, with `<round-id>` from `run.rounds`. Writer and consumer as above; the send that closes it is `simple-path.md`'s "Findings from a review"
- `evidence/<n>-<slug>.md` — consumer: `investigation-path.md` Phases 1 to 3 (the project lead reads the path, never the reading); an investigation council's spawn prompts
- `reviews/diagnosis-adversary.md` — writer: the project lead, copying the case one `crew:council-advocate` returned on the investigation path; an advocate writes no file (`agents/council-advocate.md`). Consumer: design §9.5 (a report ending's only verification evidence, design §7)

**The portfolio record** (writer: the lead, through
`skills/lead/scripts/crew-portfolio.py`, except where noted)
- `lead-<YYYY-MM-DD>-<4 hex chars>/` — consumer: `skills/lead/SKILL.md` ("Start from the record"), which globs the root for it
- `portfolio.json` — consumer: `skills/lead/SKILL.md`; both hooks
- `charters/<item-id>.md` — consumer: the item's project-lead session, which adopts it as `charter.md` (design §15.22a)
- `runs/<item-id>/` — consumer: the item's run, as its `CREW_RECORD_ROOT`; the lead, which globs it for `record_dir`
- `decisions.md` (portfolio) — consumer: `skills/lead/SKILL.md` (a restarted lead reads it before it asks anything)
- `lead.state` and its values `active`, `interrupted`, `closed` — writer: the lead; `hooks/session-end.py` writes `interrupted`. Consumer: `skills/lead/SKILL.md`'s portfolio glob
- `lead.session_ids` — consumer: both hooks (they match a portfolio to the ending or compacting session)
- `lead.principal` — consumer: `autonomy-contract.md` ("Reach the principal")
- `lead.created_at`, `lead.updated_at` — consumer: a person, and `skills/lead/SKILL.md`, reading when the portfolio last moved
- `lead.escalations` — consumer: `skills/lead/SKILL.md` ("Batch what only the principal can answer"); a restarted lead re-sends every entry with `answer: null`
- `lead.compactions` — writer: `hooks/pre-compact.py`. Consumer: `skills/lead/SKILL.md`
- `lead.spend` — writer: `skills/lead/scripts/lead-spend.py`. Consumer: `skills/project-lead/scripts/crew-stats.py`; a person reading what the tier costs (design §8)
- `items[].id`, `title`, `repo`, `charter`, `record_dir`, `session_name`, `state`, `state_changed_at`, `expect`, `outcome` — consumer: `skills/lead/SKILL.md`; `skills/lead/references/session-launch.md` reads `session_name` and `repo`
- `items[].state` values `pending`, `held`, `running`, `blocked`, `done`, `abandoned` — consumer: this file's item transitions
- `items[].depends_on` and `items[].gate` with its fields `condition`, `check`, `expect_output`, `checked_at`, `check_output`, `cleared_at`, `escalation` — writer and consumer: `skills/lead/SKILL.md` ("A gate holds the next stage"); `autonomy-contract.md` owns what the gate's ask carries (design §15.87)

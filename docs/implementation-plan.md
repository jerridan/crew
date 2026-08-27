# crew — Implementation Plan (stages 0-2)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the parts of `crew` that can be driven by hand — the instruction
standard, the plugin skeleton, the shared conventions, and the three worker
agents — ending when one code package and one instruction package each reach a
reviewed, accepted result with no human prompts.

**Architecture:** A new `crew` plugin holds agent definitions and shared
reference docs. Stages 0-2 build no orchestrator and no hooks: a human plays the
lead by hand, so each agent is proven before the skill that dispatches them
exists. Reference docs live under the (stubbed) lead skill directory so their
paths never move.

**Tech Stack:** Markdown agent and skill definitions; `git worktree`; Claude Code
agent teams. No executable code ships in stages 0-2.

**Spec:** `plugins/crew/docs/design.md`

## Global Constraints

Copied from `CLAUDE.md`, the spec, and the CI script. Every task's requirements
include these.

- Always edit in the **`crew-plugin-spec` worktree** at
  `<worktree-root>/agent-teams`, never
  in `~/.claude/plugins/cache/` and never in the main checkout at
  `~/src/claude-config` (which sits on `main` and has no `crew`).
- **Every "run it and see" step must load this branch**, not the installed
  plugins. Point `--plugin-dir` at each plugin's directory, not the repo root,
  and repeat for several plugins:
  ```
  claude --plugin-dir <worktree-root>/agent-teams/plugins/crew \
    --plugin-dir <worktree-root>/agent-teams/plugins/jq
  ```
  Without it, a step exercises the cached merged plugins and passes vacuously. The
  repo-root form looks plausible because `enabledPlugins` in `~/.claude/settings.json`
  is an allowlist: an already-installed plugin like `jq` still resolves from cache even
  when the flag points to the wrong directory. The `Skill` **tool** is auto-rejected in
  headless `-p` mode, so a step may check that a skill is *listed* but cannot *invoke*
  one.
- Any plugin with changed content needs a higher version in **both**
  `plugins/<name>/.claude-plugin/plugin.json` and `.claude-plugin/marketplace.json`.
- **Content means everything under `plugins/<name>/` except `README.md`,
  `CLAUDE.md`, `CONTRIBUTING.md` and `LICENSE` — including `docs/`.** Verified
  against `is_doc()` at `.github/scripts/check-plugin-versions.py:65-69`. This
  does not bite in this PR, because `crew` is new on `main` and
  `check_bump` takes its `base_text is None` branch. It bites from stage 3
  onward: every later plan edits `design.md` and will need a `crew` bump.
- Verify with `python .github/scripts/check-plugin-versions.py --base origin/main`
  before pushing.
- Feature branch with a PR to main. One-liner commit messages.
- **No hooks ship in stages 0-2.** `TeammateIdle` and `SessionEnd` are halves of
  one mechanism and both land in stage 5 (design §13.1).
- Instruction files are written per `writing-standard.md` **after Task 1**.

---

### Task 1: Write crew's own writing standard

First, because it governs how every later task writes prose. It has no
dependency on anything else, and no dependency on any other plugin.

**Files:**
- Create: `plugins/crew/skills/lead/references/writing-standard.md`

**Interfaces:**
- Consumes: nothing external
- Produces: a reference file that **loads by direct read**, not by skill
  invocation, and covers all four container types `crew:ic-instructions`
  owns. Its final checklist is the acceptance rubric for every instruction
  package, so its heading is exactly `## Before you open the PR`.

- [ ] **Step 1: Write the standard from scratch, covering all four containers**

`CLAUDE.md`, `.claude/rules/`, `SKILL.md`, and agent definitions, in one file,
with no hand-off to another skill for any of them. Required sections:

```markdown
## Pick the container
## Write for what the reader already has
## Frontmatter
## Revise down
## Before you open the PR
```

- [ ] **Step 2: Settle the ASD-STE100 question**

The user's global `CLAUDE.md` requires ASD-STE100 for all prose. Decide
whether the exemption travels into the new standard, and record the decision
in the file. This governs every later task.

- [ ] **Step 3: Write the checklist as a gate, not guidance**

Each item under `## Before you open the PR` must be a concrete pass/fail
assertion a reviewer can answer *no* to. Cover at minimum: container choice,
duplicated or contradicting rules, reference depth, size, and ASD-STE100
prose. Pick specific numbers for size and reference depth and own them.

- [ ] **Step 4: Verify**

```bash
python .github/scripts/check-plugin-versions.py --base origin/main
```

Expected: exit 0. `crew` is new on `main`, so this task needs no version
bump of its own.

- [ ] **Step 5: Commit**

```bash
git add plugins/crew/skills/lead/references/writing-standard.md
git commit -m "crew: write the instruction-writing standard"
```

---

### Task 2: Probe the unverified platform behaviors

A spike. Output is an answer recorded in the spec, not code. Task 7 branches on
its plan-approval finding; stage 5's hook depends on the rest.

**Files:**
- Modify: `plugins/crew/docs/design.md` (sections 12 and 13.1)

**Interfaces:**
- Consumes: nothing
- Produces: a decided IC gate mechanism (Task 7), and the facts stage 5's hook
  needs before it can be designed.

- [ ] **Step 1: Confirm teammate spawning works**

```bash
it2 app version
```

Expected: an iTerm2 version string. **If it errors**, either enable the iTerm2
Python API, run inside tmux, or set `teammateMode: "in-process"` in
`~/.claude/settings.json` — the last needs no tooling and works in any terminal.
Do not proceed until a teammate spawns.

- [ ] **Step 2: Probe plan approval**

Spawn a named teammate requiring plan approval on a task that forces a plan.
Record: does an approval request reach the lead; can the lead reject with
feedback; does the teammate revise and resubmit.

- [ ] **Step 3: Probe the `TeammateIdle` payload AND whether exit 2 blocks**

The design asserts exit 2 rejects an idle. That is documented, not verified, and
exit-code semantics differ per hook event. If exit 2 does not block, stage 5's
hook is a no-op and needs redesigning.

Register a temporary hook that does both — dumps stdin and returns 2:

```bash
mkdir -p /tmp/crew-probe
cat > /tmp/crew-probe/probe.sh <<'EOF'
#!/bin/bash
cat >> /tmp/crew-probe/teammate-idle-payload.json
echo "crew probe: refusing idle" >&2
exit 2
EOF
chmod +x /tmp/crew-probe/probe.sh
```

Register it as a `TeammateIdle` hook in `~/.claude/settings.json`, spawn a
teammate, let it finish, then **remove the hook registration**.

- [ ] **Step 4: Answer three questions from the dump**

1. Does exit 2 actually prevent the teammate from idling?
2. Does the stderr string reach the teammate?
3. Does the payload identify **which** teammate, and does it carry a session id
   or cwd? Without one, a hook cannot scope to a run and must fail open.

- [ ] **Step 5: Update the spec**

Move the findings into section 12's table. Update section 13.1's `TeammateIdle`
row with the check that is actually possible. If plan approval does not work,
update section 9.2 to the written-plan fallback.

- [ ] **Step 6: Commit**

```bash
git add plugins/crew/docs/design.md
git commit -m "crew: record probe results for plan approval and TeammateIdle"
```

---

### Task 3: Create the crew plugin skeleton

**Files:**
- Create: `plugins/crew/.claude-plugin/plugin.json`
- Create: `plugins/crew/skills/lead/SKILL.md`
- Modify: `.claude-plugin/marketplace.json`

No `README.md`. It is deliberately held back so that Task 10 has a real
instruction package to dogfood, per design §3.1.

**Interfaces:**
- Consumes: nothing
- Produces: the plugin root and the stable path
  `plugins/crew/skills/lead/references/` that Tasks 4-6 write into.

- [ ] **Step 1: Write plugin.json**

```json
{
  "name": "crew",
  "description": "Autonomous project lead — takes one goal to reviewable draft PRs and picks the cheapest model per unit of work",
  "version": "0.1.0",
  "author": {
    "name": "Jerridan Quiring"
  }
}
```

- [ ] **Step 2: Add the marketplace entry**

Append to the `plugins` array in `.claude-plugin/marketplace.json`:

```json
{
  "name": "crew",
  "source": "./plugins/crew",
  "description": "Autonomous project lead — takes one goal to reviewable draft PRs and picks the cheapest model per unit of work",
  "version": "0.1.0"
}
```

Both files change in this one task, so `check_sync` never sees a plugin.json
without a marketplace entry.

- [ ] **Step 3: Stub the lead skill**

Real frontmatter, and a body saying the loop is not built yet and pointing at the
design doc. Stage 4 replaces the body; the frontmatter and path stay.

```yaml
---
name: lead
description: Take one goal to reviewable draft PRs without stopping for approval. Use when handing off a whole goal rather than a single task. Triggers on "run this as a project", "hand this to crew", "take this to a draft PR".
---
```

- [ ] **Step 4: Verify the plugin loads from this branch**

```bash
claude --plugin-dir <worktree-root>/agent-teams/plugins/crew \
  --model haiku --strict-mcp-config \
  -p "Do not use any tools. From your system prompt only, answer tersely: list every skill name you can see that begins with 'crew'. If none, say NONE."
```

Expected: `crew:lead` is listed. The main checkout has no `crew`, so using the
installed plugins would report exactly the failure this step exists to rule out.

- [ ] **Step 5: Commit**

```bash
git add plugins/crew .claude-plugin/marketplace.json
git commit -m "crew: add plugin skeleton and stubbed lead skill"
```

---

### Task 4: Write the record format reference

**Files:**
- Create: `plugins/crew/skills/lead/references/record-format.md`

**Interfaces:**
- Consumes: design §4, §5, §7, §9.2, §10.1
- Produces: every field name and enum value that Tasks 5-10 use. Nothing defined
  here may go unconsumed, and nothing consumed later may be undefined here.

- [ ] **Step 1: Define the directory layout**

All eight entries from design §4: `charter.md`, `spec.md`, `plan.md`,
`state.json`, `decisions.md`, `worktrees.json`, `reports/`, `reviews/`.

`reports/` holds one report per package, written by its IC. `reviews/` holds
critic and reviewer output. They are different things and must not share a
directory — the lead has to find a report without parsing review output.

- [ ] **Step 2: Define `state.json` with a complete worked example**

Not a schema sketch. Per package, all of:

| Field | Why it must exist |
|---|---|
| `id`, `deliverable`, `territory` | identity |
| `state` | one of `pending`, `in-flight`, `integrated`, `abandoned` |
| `band`, `band_history` | design §8 promotion logging |
| `file_set` | design §5 invariant 2; `decompose-critic` checks disjointness against it |
| `interface_contract` | design §5 invariant 3; the only channel between isolated ICs |
| `acceptance_criterion` | design §5 invariant 1, and what makes a respawn idempotent |
| `fix_rounds_used` | design §9.2 caps at five. After a crash §10.1 respawns from the worktree, and without this the budget silently resets and the breaker never fires |
| `ic_name` | `worktrees.json` maps IC → worktree; without this nothing maps package → IC, so the lead cannot tell which worktree to verify a package against |
| `report_path` | points into `reports/` |

Per run: `run_state` (`active`, `interrupted`, `complete`), `session_ids`,
`spend`.

Design §4 says `state.json` is authoritative for the plan including file sets and
contracts, so they live here, not only in `plan.md`.

- [ ] **Step 3: Define `worktrees.json`**

IC name → worktree path → branch → `session_ids`.

**A list, not a single id.** Design §13.1 makes the session id the only proof of
worktree ownership, but `--resume` runs in a *new* session with a *new* id. If
resume overwrites, ownership matching fails on the first resume — the exact path
the field exists to serve. Resume appends.

- [ ] **Step 4: Define goal-slug uniqueness**

Nothing currently makes `<goal-slug>` unique, and design §1 encourages running
several goals in parallel sessions. Two similar goals derive one slug and share
one `state.json` with no locking. Append a short random suffix, or define the
collision behavior explicitly.

- [ ] **Step 5: Define the `decisions.md` entry format**

Copy design §4's worked example verbatim. State the rule: high confidence with no
citation is a defect.

- [ ] **Step 6: State the authority rule**

`state.json` is authoritative for the plan; the worktrees are authoritative for
progress. Written after every transition, not batched.

- [ ] **Step 7: Verify — name reconciliation**

The acceptance criterion for this task, and it is mechanical:

Dispatch a subagent with this file, `band-rubric.md`, `ic-contract.md`, and this
plan. Pass condition: **every field name, state value, band name and status
string used anywhere in Tasks 5-10 appears verbatim in one of the three
reference files, and no reference file defines a name that nothing consumes.**

- [ ] **Step 8: Commit**

```bash
git add plugins/crew/skills/lead/references/record-format.md
git commit -m "crew: define the record format"
```

---

### Task 5: Write the band rubric reference

**Files:**
- Create: `plugins/crew/skills/lead/references/band-rubric.md`

**Interfaces:**
- Consumes: design §8, §6.1
- Produces: band names `light`, `standard`, `deep`, used verbatim by
  `state.json`'s `band` field (Task 4).

- [ ] **Step 1: Write the band table**

Copy design §8's table. Bands are model only, because a teammate inherits the
lead's effort.

- [ ] **Step 2: Write the observable inputs**

Does an analogous implementation already exist; do tests already cover the
surface; does the package define a new interface others depend on; is it
concurrency, security, migration, or a data-shape change; did the lead have to
interpret the acceptance criterion.

- [ ] **Step 3: Write the rules**

Default `standard`. `deep` needs written justification in `plan.md`. Promotion on
`BLOCKED`, exhausted fix rounds, or idle-without-acceptance. Log predicted band,
actual band, cause.

- [ ] **Step 4: Write the council model rules**

Advocates all sonnet; same model within one council; sonnet is the floor; raise
together to opus for a `deep` decision.

- [ ] **Step 5: Verify**

Get an independent plan review with this file and design §8. Pass condition: no
`[Critical]` findings.

- [ ] **Step 6: Commit**

```bash
git add plugins/crew/skills/lead/references/band-rubric.md
git commit -m "crew: define the model band rubric"
```

---

### Task 6: Write the shared IC contract

**Files:**
- Create: `plugins/crew/skills/lead/references/ic-contract.md`

**Interfaces:**
- Consumes: design §3, §6.2, §9.2, §12; `report_path` and `reports/` from Task 4
- Produces: the text the lead injects into every IC spawn prompt, and the four
  report status strings. Must be self-contained — a teammate inherits no
  conversation history.

- [ ] **Step 1: Write the prohibitions**

No files outside the declared set. No scope renegotiation. No pushing to a
remote. No spawning a reviewer or another implementer. Read-only lookup
subagents only, and they run in the foreground so they cost wall-clock.

- [ ] **Step 2: Write the worktree rule verbatim**

The single most dangerous constraint in the design:

```
The shell working directory resets after EVERY Bash call. `cd` holds only
within one invocation. Every command you run must carry its own
`cd <your-worktree> &&` prefix. A command without it runs against the wrong
checkout and reports no error.
```

- [ ] **Step 3: Write the commit rule**

Commit after every green step. This is what bounds crash loss to one increment.

- [ ] **Step 4: Write the question protocol**

From design §6.2: `SendMessage` the lead, never the human; do not wait; prefer
proceeding under a stated assumption and naming it in the report; else move to
the next package in the territory; stop only when the question blocks the whole
package.

- [ ] **Step 5: Define the four statuses AND the lead's response to each**

A status with no defined consumer behavior is decoration. Define both halves:

| Status | Meaning | What the lead does |
|---|---|---|
| `DONE` | complete, no reservations | verify against git, then review |
| `DONE_WITH_CONCERNS` | complete, but the IC flagged doubts | read the concerns first; correctness or scope concerns are resolved before review, observations are noted and review proceeds |
| `NEEDS_CONTEXT` | missing information, work not complete | supply it and re-dispatch. Distinct from the §6.2 asking-IC protocol, which is for an IC that *can* continue |
| `BLOCKED` | cannot complete | promote one band (design §8) or hit the breaker |

- [ ] **Step 6: Write the report contract**

Report goes to `report_path` under `reports/`. Required fields: status, commits
made, assumptions taken, questions raised.

- [ ] **Step 7: Verify**

Get an independent plan review with this file and design §3, §6.2, §9.2. Pass
condition: no `[Critical]` findings, and every status string has a defined lead
response.

- [ ] **Step 8: Commit**

```bash
git add plugins/crew/skills/lead/references/ic-contract.md
git commit -m "crew: define the shared IC contract"
```

---

### Task 7: Write the `crew:ic` agent

**Files:**
- Create: `plugins/crew/agents/ic.md`

**Interfaces:**
- Consumes: `ic-contract.md` (Task 6); the plan-approval finding (Task 2)
- Produces: agent type `crew:ic`, dispatched named so it runs as a teammate, with
  the model passed at spawn time.

- [ ] **Step 1: Write the frontmatter**

No `model:` key — the band is passed at spawn, and design §12 confirms spawn-time
model wins. No `hooks:` key: ignored for teammates and banned for plugin agents.

```yaml
---
name: ic
description: Implement one work package test-first inside an assigned git worktree, commit after every green step, and report to the lead. Dispatched by the crew lead, one per territory.
tools: Read, Write, Edit, Glob, Grep, Bash, Agent, Skill, SendMessage
---
```

`SendMessage` is required — design §6.2 makes messaging the lead the IC's only
escalation path, and without it the IC is forced down the assumption path every
time. `Agent` and `Skill` are granted to both ICs identically; design §3 gives
every IC read-only lookup subagents.

- [ ] **Step 2: Write the role and the TDD loop**

Red-green-refactor per package: write the failing test, run it and see it fail,
write the minimal implementation, run it and see it pass, commit.

- [ ] **Step 3: Apply Task 2's plan-approval finding**

Both branches, spelled out:

- **If plan approval works:** the body says the IC plans in read-only mode and
  submits for the lead's approval before implementing.
- **If it does not:** the body says the IC writes its plan to the record and
  waits for the lead's go-ahead by message before implementing.

Pick the branch Task 2 established and write only that one.

- [ ] **Step 4: Restate nothing from the contract**

The body says the contract arrives in the spawn prompt and must be followed. Do
not copy it — a second copy of a rule is worse than no copy.

- [ ] **Step 5: Write the self-review step**

Before reporting: re-read the acceptance criterion, check the diff against the
declared file set, confirm every command used its `cd` prefix.

- [ ] **Step 6: Verify**

Get an independent plan review with this file, `ic-contract.md`, and design §3. Pass
condition: no `[Critical]` findings, and no rule duplicated from the contract.

- [ ] **Step 7: Commit**

```bash
git add plugins/crew/agents/ic.md
git commit -m "crew: add the ic implementer agent"
```

---

### Task 8: Write the `crew:ic-instructions` agent

**Files:**
- Create: `plugins/crew/agents/ic-instructions.md`

**Interfaces:**
- Consumes: `ic-contract.md` (Task 6); `writing-standard.md` (Task 1)
- Produces: agent type `crew:ic-instructions`. Same report contract and status
  strings as `crew:ic`, so the lead handles both identically.

- [ ] **Step 1: Write the frontmatter**

```yaml
---
name: ic-instructions
description: Write or edit instruction files — CLAUDE.md, .claude/rules, SKILL.md, agent definitions — inside an assigned git worktree. Dispatched by the crew lead for packages whose deliverable is prose rather than code.
tools: Read, Write, Edit, Glob, Grep, Bash, Agent, Skill, SendMessage
---
```

Identical tool list to `crew:ic`. The two differ in process, not capability.

- [ ] **Step 2: Write the loop that replaces red-green-refactor**

From design §3.1: pick the container, draft, revise down, self-check against the
checklist, commit. State plainly that no test is run and the checklist is the
acceptance criterion.

- [ ] **Step 3: Point at the canonical standard**

Read `writing-standard.md` before writing anything. Hold no copy of the
standard. This depends on Task 1 having produced a file that covers all four
container types — if it does not, this agent cannot work as designed.

- [ ] **Step 4: Write the judged-on-output rule**

The IC is judged on its output meeting the checklist, not on how it obtained
the standard. This keeps the contract intact if the file is missing or stale.

- [ ] **Step 5: Verify**

Get an independent plan review with this file, `ic-contract.md`, and design §3.1.
Pass condition: no `[Critical]` findings.

- [ ] **Step 6: Commit**

```bash
git add plugins/crew/agents/ic-instructions.md
git commit -m "crew: add the ic-instructions specialist agent"
```

---

### Task 9: Write the `crew:package-reviewer` agent

**Files:**
- Create: `plugins/crew/agents/package-reviewer.md`

**Interfaces:**
- Consumes: the four status strings from Task 6
- Produces: agent type `crew:package-reviewer`, dispatched **unnamed** so its
  findings return as a tool result. Takes three paths in its prompt: the package
  brief, the IC's report, and either a diff file or a checklist file.

- [ ] **Step 1: Write the frontmatter**

```yaml
---
name: package-reviewer
description: Review one completed work package against its brief and acceptance criterion. Dispatched unnamed by the crew lead so its findings return as a tool result.
model: sonnet
reasoning_effort: high
tools: Read, Glob, Grep, Bash
---
```

`reasoning_effort` is frontmatter-only (design §12) and this agent is dispatched
unnamed, so it applies. Design §3's roles table specifies sonnet / high.

- [ ] **Step 2: State the no-fix rule in the body, not the frontmatter**

`Bash` is granted for running tests, and `Bash` can write files — so the tool
list does not enforce "reports, does not fix". Say it in the body, where it is
actually load-bearing.

- [ ] **Step 3: Write the two review modes**

Code package: read the diff from the given path, check against the brief and the
tests. Instruction package: check the output against the checklist file given.

- [ ] **Step 4: Write the finding format**

`[Critical]` / `[Concern]` / `[Nit]`, crew's own severity vocabulary — no
dependency on another plugin's agent. This agent carries no `SendMessage`;
its findings return only as this agent's tool result.

- [ ] **Step 5: Write the cannot-verify rule**

A reviewer that cannot confirm a requirement from what it was given says
`Cannot verify from diff` rather than guessing. The lead resolves those itself.

- [ ] **Step 6: Verify**

Get an independent plan review with this file and design §3, §7. Pass condition: no
`[Critical]` findings.

- [ ] **Step 7: Commit**

```bash
git add plugins/crew/agents/package-reviewer.md
git commit -m "crew: add the package reviewer agent"
```

---

### Task 10: Drive one package of each kind by hand

The stage-2 acceptance test. No orchestrator exists, so a human plays the lead.
Both packages are **real work this repo needs**, not toys.

**Files:**
- Create: `plugins/crew/README.md` (produced by `crew:ic-instructions`)
- Modify: `plugins/auto-approve/scripts/test-auto-approve.py` (produced by
  `crew:ic`)
- Modify: `plugins/auto-approve/.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json` (bump — the lead's job, per design §5)
- Modify: `plugins/crew/docs/design.md` (findings)

**Interfaces:**
- Consumes: every prior task
- Produces: evidence the agents work before stage 4 builds a loop on them.

- [ ] **Step 1: Create a record and two worktrees by hand**

```bash
mkdir -p ~/.claude/crew/probe-run/reports ~/.claude/crew/probe-run/reviews
git worktree add <worktree-root>/crew-code -b crew-probe-code
git worktree add <worktree-root>/crew-docs -b crew-probe-docs
```

- [ ] **Step 2: Record the lead's own tree state, for the drift check**

```bash
git -C <worktree-root>/agent-teams log --oneline -1 > /tmp/crew-probe/lead-head-before
git -C <worktree-root>/agent-teams status --porcelain > /tmp/crew-probe/lead-status-before
```

- [ ] **Step 3: Dispatch the code package**

`crew:ic`, named, with a model, contract injected. Package: add a test case to
`plugins/auto-approve/scripts/test-auto-approve.py` covering a Tier 1 chained-command
edge case. That file is stdlib-only and runs standalone, so the acceptance
criterion is executable:

```bash
python plugins/auto-approve/scripts/test-auto-approve.py
```

- [ ] **Step 4: Run the real cwd-drift check**

`git -C <worktree>` can only show what *is* in that worktree — it cannot show
work that leaked elsewhere, so an empty log is indistinguishable from "the IC did
nothing". The check has to look at the tree the IC would have drifted *into*:

```bash
git -C <worktree-root>/agent-teams status --porcelain
git -C <worktree-root>/agent-teams log --oneline -1
```

Expected: identical to the `before` files from Step 2. Anything new means the IC
lost its `cd` prefix. This is the only defense against the cwd hazard until
stage 5's hook, so it must actually work.

Then confirm the work landed where it should:

```bash
git -C <worktree-root>/crew-code log --oneline
```

- [ ] **Step 5: Review the code package**

```bash
git -C <worktree-root>/crew-code diff main...HEAD > ~/.claude/crew/probe-run/reviews/code-diff.patch
```

Dispatch `crew:package-reviewer` **unnamed** with that path plus the brief and
the IC's report. Confirm findings return as a tool result.

- [ ] **Step 6: Dispatch the instruction package**

`crew:ic-instructions` writes `plugins/crew/README.md` — real work, held back
from Task 3 for exactly this. Design §14 requires it to cover what crew does, the
roles table, the launch command, the display-mode prerequisite, and the
superpowers credit.

Confirm it reads `writing-standard.md` and that it gets **Task 1's file**, not
a stale copy from an earlier run.

- [ ] **Step 7: Review the instruction package with the checklist**

Dispatch `crew:package-reviewer` with the path to `## Before you open the PR`
instead of a diff. Pass condition: no `[Critical]` findings.

- [ ] **Step 8: Merge both probe branches**

The work is real and is kept. Merging also makes Step 10's cleanup safe, because
a merged branch deletes without force.

```bash
git merge --squash crew-probe-code && git commit -m "auto-approve: add a chained-command tier 1 test case"
python plugins/auto-approve/scripts/test-auto-approve.py
git merge --squash crew-probe-docs && git commit -m "crew: add the plugin README"
```

Bump `auto-approve` in both files — its content changed, and the version bump is
the lead's job, never an IC's (design §5).

- [ ] **Step 9: Preserve the evidence before deleting the record**

The record is the proof the acceptance criterion was met. Copy it out first.

```bash
mkdir -p plugins/crew/docs/stage-2-run
cp -R ~/.claude/crew/probe-run/reports ~/.claude/crew/probe-run/reviews plugins/crew/docs/stage-2-run/
```

- [ ] **Step 10: Clean up without forcing**

```bash
git worktree remove <worktree-root>/crew-code
git worktree remove <worktree-root>/crew-docs
git branch -d crew-probe-code
git branch -d crew-probe-docs
rm -rf ~/.claude/crew/probe-run
```

`-d`, never `-D`. `-d` refuses to delete unmerged commits, which is the point —
if it refuses, Step 8's merge did not happen and the work would have been
destroyed. Never force a worktree removal either; if one refuses, commit what is
there first.

- [ ] **Step 11: Record what broke**

Any behavior contradicting the design goes into the spec's open questions before
stage 3 starts.

- [ ] **Step 12: Commit**

```bash
git add plugins/crew plugins/auto-approve .claude-plugin/marketplace.json
git commit -m "crew: record findings from the hand-driven stage 2 run"
```

---

### Task 11: Update the repo's own instructions and open the PR

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:**
- Consumes: every prior task
- Produces: a merged-ready PR.

- [ ] **Step 1: Update the Repo Structure tree**

`CLAUDE.md:5-27` gains `crew/`. `resolve-ticket/` is also missing from it — add
both. A PR whose subject is instruction quality is a poor place to leave the
repo's own instructions stale.

- [ ] **Step 2: Leave the hook list alone**

`CLAUDE.md:87` enumerates hook-bearing plugins. `crew` ships no hooks in stages
0-2, so this line is correct as written. It changes in stage 5.

- [ ] **Step 3: Verify**

```bash
python .github/scripts/check-plugin-versions.py --base origin/main
```

Expected: `auto-approve` bumped, `crew: new plugin at 0.1.0`, exit 0.
`CLAUDE.md` is a doc under `is_doc()`, so it needs no bump.

- [ ] **Step 4: Open the PR**

`gh pr create` with no `--title` or `--body` prompts interactively and will hang.
Supply both.

```bash
git push -u origin crew-plugin-spec
gh pr create --draft --base main \
  --title "crew: plugin scaffolding, worker agents, and the instruction standard" \
  --body-file plugins/crew/docs/pr-body.md
```

The body covers why, the approach, risk and testing, and carries the one
follow-up this plan defers: stage 5's `TeammateIdle` plus `SessionEnd` pair.

---

## Stages 3-6

Out of scope; each gets its own plan once stage 2 proves the agents.

| Stage | Delivers |
|---|---|
| 3 | `crew:decompose-critic` and the `plan.md` format |
| 4 | `/crew:lead` — the loop, simple path first, plus `crew:deliverable-reviewer` |
| 5 | Full path: worktrees, territories, merges, promotion, **and the `TeammateIdle` + `SessionEnd` hook pair** |
| 6 | The council, question routing, and `decisions.md` |

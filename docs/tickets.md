# Tickets

The build backlog, from the current state (stages 0-2 built, nothing
dispatches them) to the target state: a working three-tier hierarchy —
lead → project leads → ICs (design §15.21).

How to take a ticket:

1. Read `CLAUDE.md` first, then the ticket's **Read first** list.
2. Work only that ticket. Branch, commit, open a draft PR (`CLAUDE.md`
   workflow). One ticket per PR.
3. Set the ticket's `Status` line in your PR: `in-progress` when you
   start, `done` when the PR merges.
4. Record what you learn in `docs/design.md` §15, not here. This file
   holds work, not findings.

Dependencies name tickets, not stages. A ticket with an unmet dependency
is not takeable.

---

## T1 — Decomposition critic and the `plan.md` format

Status: open
Depends on: nothing
Stage: 3 (design §13)

Build `agents/decompose-critic.md`: an unnamed agent (opus, high effort —
design §3) that reviews the project lead's `plan.md` against the seven
checks in design §5 "The critic", and nothing else. Define the `plan.md`
format it reviews: deliverables → packages, with the four dispatchability
invariants (§5), interface contracts, global constraints, and band
justifications. The format definition lives in
`skills/project-lead/references/record-format.md`, which owns the record.

Done when: a hand-dispatched review of a deliberately bad split — an
overlapping file set, a missing contract, a hidden dependency chain —
names every seeded flaw.

Read first: design §5, §3; `record-format.md`;
`skills/project-lead/references/writing-standard.md`.

## T2 — Spec critic

Status: open
Depends on: nothing
Stage: 3 (design §15.2)

Build `agents/spec-critic.md`: an unnamed agent (opus, high effort) that
reviews the project lead's `spec.md` before decomposition. Crew-owned, no
dependency outside this plugin. It reports findings; it does not edit.

Done when: a hand-dispatched review of a spec with a seeded flaw — an
unfalsifiable acceptance criterion, a contradiction, a missing constraint
from the charter — names the flaw.

Read first: design §15.2, §3, §7 (adjudication); `writing-standard.md`.

## T3 — Deliverable reviewer

Status: open
Depends on: nothing
Stage: 4 (design §13)

Build `agents/deliverable-reviewer.md`: an unnamed agent (opus, high
effort) that reviews a whole deliverable's diff after every package
merges, before the draft PR opens (design §9.3). Same posture as
`agents/package-reviewer.md`: report, never fix; git via
`git -C <worktree>`; end with the same two verdict lines.

Done when: a hand-dispatched review over a multi-package diff returns
findings and a verdict in the required format.

Read first: design §9.3, §7; `agents/package-reviewer.md`;
`writing-standard.md`.

## T4 — `/crew:project-lead`, simple path

Status: open
Depends on: T1, T2, T3
Stage: 4 (design §13)

Replace the stub in `skills/project-lead/SKILL.md` with the loop for one
simple goal: accept a goal string or a charter file path (design §15.22a),
scout, write the spec, have T2's critic review it, run one package as an
unnamed subagent on the deliverable branch (§9.1 simple path — no
worktree, no teammate), review it with `crew:package-reviewer`, run fix
rounds, integrate, bump both versions, and open a draft PR with `spec.md`
and `decisions.md` in the body. Write the record per `record-format.md`
after every transition. Escalate to the principal, not a hard-coded human
(§15.22b).

Done when: one simple, familiar goal reaches a draft PR with zero
permission prompts, and the record audits cleanly.

Read first: design §9.1, §9.3, §6, §7, §15.22; `record-format.md`;
`ic-contract.md`; `band-rubric.md`.

## T5 — Probe: `TeammateIdle`

Status: open
Depends on: nothing
Stage: pre-5 (design §13.1)

Run the probe procedure in design §13.1: does exit 2 block a teammate's
idle, does stderr reach the teammate, and does the payload identify the
idling teammate and carry a session id or cwd? Needs an interactive
session with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — headless `-p`
cannot spawn a teammate (design §12). Remove the probe hook registration
right after.

Done when: all three §13.1 questions have probed answers recorded in
design §15 as a new finding.

Read first: design §13.1, §12, §15.8.

## T6 — Full path: worktrees, territories, teammates

Status: open
Depends on: T4, T5
Stage: 5 (design §13)

Extend `/crew:project-lead` with the full path (§9.2): worktrees and
branches per IC, territories, IC teammates spawned at their band with
per-dispatch git grants scoped to their worktree (§15.23c-d), the plan
gate with `plan_approved_at`, worktree verification (§7), squash merges
with a test run per merge (§9.3), promotion (`band-rubric.md`), and
recovery via `--resume` (§10.1). Re-verify §15.23's probe findings on the
machine that runs this, if its Claude Code version has drifted far from
2.1.251.

Done when: one multi-package goal reaches a draft PR with zero prompts,
including one forced fix round and one kill-and-resume.

Read first: design §9.2-9.4, §10, §10.1, §15.10-12, §15.23;
`record-format.md`; `ic-contract.md`.

## T7 — Hooks: `TeammateIdle` and `SessionEnd`

Status: open
Depends on: T5, T6
Stage: 5 (design §13.1)

Ship `hooks/hooks.json` with the two stage-5 hooks, exactly as §13.1
specifies: `TeammateIdle` blocks an idle only for the idling IC's own
unreported, approved, in-flight package — and lets a plan-gate pause pass
(`plan_approved_at` null, design §15.8); `SessionEnd` marks the run
interrupted and its worktrees orphaned, writes only, deletes nothing.
Include the kill switch and the staleness cutoff. No hook ever removes a
worktree.

Done when: a crashed run's next `--resume` finds `run_state: interrupted`,
and an IC idling without a report is rejected while a plan-gate pause is
not.

Read first: design §13.1, §15.8; `record-format.md`.

## T8 — Council, routing, `decisions.md`

Status: open
Depends on: T4
Stage: 6 (design §13)

Build question routing (§6): precedent, council, preference, with every
routing logged before it is answered. Councils per §6.1 — assigned
positions, one batch, sonnet advocates, adjudication at the project
lead's model — with spend logged to `spend.council_tokens`. Add the
`Models:` line to `decisions.md` entries (design §15.9) and its
definition to `record-format.md`.

Done when: an architecture-moving question in a real run is resolved by a
council, recorded with citations, models, and spend, with no human
prompt.

Read first: design §6, §6.1, §6.2, §15.9; `record-format.md`;
`band-rubric.md` council rules.

## T9 — The lead tier

Status: open
Depends on: T6
Stage: beyond crew (design §1, §15.21-22)

Build the tier above: a session that holds a portfolio of goals, writes
charters, spawns one project-lead session per goal under §15.22c's three
launch rules, messages them by cross-session `SendMessage`, reads their
records under `~/.claude/crew/`, answers their escalations, and batches
what only the human can decide. First decision inside the ticket: does it
live in this repo or as a sibling plugin? Design §1 scopes it out of
crew, so building it here revises §1 — say so in the PR.

Done when: two concurrent goals run in two project-lead sessions from one
lead session, and every escalation reaches the human through the lead.

Read first: design §15.21, §15.22, §1, §4.

## T10 — Decide the README container owner

Status: open
Depends on: nothing
Stage: any (design §15.17)

`crew:ic-instructions` owns four container types; a README is none of
them, and the writing standard flags its routing as unsettled. Decide:
grow the specialist's list to cover reader-facing prose, or name a
different owner. Record the decision in design §15.17 and align §3.1,
`agents/ic-instructions.md`, and `writing-standard.md`'s README note.

Done when: the four files agree and §15.17 reads "Decided".

Read first: design §15.17, §3.1; `writing-standard.md`.

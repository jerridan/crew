# Tickets

The build backlog, from the current state (stages 0-4 built: the simple
path runs) to the target state: a working three-tier hierarchy —
lead → project leads → ICs (design §15.21).

How to take a ticket:

1. Read `CLAUDE.md` first, then the ticket's **Read first** list.
2. Work only that ticket. Branch, commit, open a draft PR (`CLAUDE.md`
   workflow). One ticket per PR.
3. `Status` is `open` or `done`. Set it to `done` in the PR that
   finishes the ticket, so the merge and the status land together. An
   open PR is what says the work is under way.
4. Record what you learn in `docs/design.md` §15, not here. This file
   holds work, not findings.

Dependencies name tickets, not stages. A ticket with an unmet dependency
is not takeable.

---

## T1 — Split critic and the `split.md` format

Status: done
Depends on: nothing
Stage: 3 (design §13)

Build `agents/split-critic.md`: an unnamed agent (opus, high effort —
design §3) that reviews the project lead's `split.md` against the seven
checks in design §5 "The critic", and nothing else. Define the `split.md`
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

Status: done
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

Status: done
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

Status: done
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

Routing and `decisions.md` landed early, in T4:
`skills/project-lead/references/autonomy-contract.md` carries the three
routes and the rule that every routing is logged before it is answered, and
the simple path writes `decisions.md`. T4 could not run without them. What
remains here is the council.

Build councils per §6.1 — assigned positions, one batch, sonnet advocates,
adjudication at the project lead's model — with spend logged to
`spend.council_tokens`. Replace `autonomy-contract.md`'s council row, which
says councils are not built and routes such a question to an inline answer
or an escalation. Add the `Models:` line to `decisions.md` entries (design
§15.9) and its definition to `record-format.md`.

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

## T11 — Design the investigation path

Status: open
Depends on: nothing
Stage: design (`docs/design.md`)

Crew's loop assumes the goal is a change: spec, split, implement, draft
PR. A bug or a support ticket starts from an unknown — most of the work
is diagnosis, and a run can legitimately end with no code change. Write
the design section for an investigation path:

- A bug charter: the acceptance criterion is a reproduction — a test or
  command that fails now and must pass after the fix.
- A diagnosis artifact in the record — evidence, root cause, ruled-out
  hypotheses — and a terminal deliverable state for a run that ends in a
  report instead of a PR. `record-format.md` owns both names.
- Competing root-cause hypotheses run as a council (§6.1): advocates
  argue assigned hypotheses over the same evidence, the project lead
  adjudicates.
- A debugging checklist copied word for word from superpowers (§2, §14):
  reproduce before touching code; no fix without the root cause.
- Where the path rejoins the build loop: a diagnosed fix is usually one
  package on the simple path (§9.1), with the repro as its acceptance
  test.

Done when: `docs/design.md` carries the section, §14 records the new
deviations, and the implementation tickets it implies are added here.

Read first: design §2, §5 (invariant 1), §6.1, §9.1, §14; the
superpowers debugging skill the checklist copies from.

## T12 — Implement the investigation path

Status: open
Depends on: T4, T11
Stage: after 4

Extend `/crew:project-lead` with T11's design: accept a bug-shaped
charter, run the diagnosis loop — scouts gather evidence, a council
weighs hypotheses when more than one survives — write the diagnosis
artifact, then either stop at the report or hand the fix to the simple
path with the reproduction as its acceptance test.

Done when: one real bug goes from ticket text to a draft PR whose new
test reproduces the bug and passes after the fix, with zero prompts; and
one no-code-change question ends in a recorded diagnosis instead of a
PR.

Read first: T11's design section; design §9.1; `record-format.md`.

## T13 — Researcher agent

Status: done
Depends on: nothing
Stage: any (usable from stage 4 on)

A scout answers one question in one shot (design §3). A hard question —
"figure out why X happens", "map how subsystem Y really works" — needs
several lines of inquiry followed across hops, then synthesis, and today
that synthesis lands in the project lead's own context. Build
`agents/researcher.md`: an unnamed agent that takes one open question,
fans out its own read-only lookup subagents in parallel (subagents nest
three deep — design §15.20), follows leads, and returns one brief with
citations, a confidence level, and what it could not determine. It edits
nothing. Banded like any package: sonnet default, opus when the question
is deep. Add its row to design §3; scouts stay for single lookups.

`agents/researcher.md` and the design §3 row landed on 2026-08-31, built by
the first `/crew:project-lead` simple-path run. The dispatch exercise ran
the same day; design §15.27 records what it returned.

Done when: a hand-dispatched researcher answers a genuinely multi-hop
question about a real repo with citations and a stated unknown, and the
dispatching session read only the brief.

Read first: design §3, §9.1, §15.20; `writing-standard.md`.

## T14 — Design run instruments

Status: open
Depends on: nothing
Stage: design (`docs/design.md`); implementation folds into T4

Some target repos carry their own investigation skills with access crew
must never own — a database, internal endpoints. Design the instruments
mechanism: the charter carries an explicit list, named by the principal
at hand-off, of repo-local skills or agents this run may dispatch. Crew
ships none, auto-discovers none, and never invokes one not listed. Every
use is recorded in the run's record. The design section says who may use
an instrument (the project lead, a researcher, an IC?) and how its
output is treated (a claim to verify, like an IC report — design §7).
Nothing environment-specific enters this repo, not even as an example.

Done when: design.md carries the section, the charter format names the
field, and T4's ticket lists it.

Read first: design §6.2, §7, §15.22a; `record-format.md`.

## T15 — Consolidate the duplicated agent boilerplate

Status: open
Depends on: nothing
Stage: any

`crew:researcher`'s first dispatch audited this plugin against `CLAUDE.md`'s
"a rule lives in exactly one file" and found six rules stated in more than
one place, three of them already drifted (design §15.27). Fix the three that
drifted, and decide an owner for each rule that has none:

- The `[Concern]` definition reads "likely to cost a fix round" in
  `spec-critic.md` and `split-critic.md`, and "likely to cause a problem" in
  `package-reviewer.md` and `deliverable-reviewer.md`.
- `split-critic.md`'s shared-file list adds "test helpers, snapshots"; the
  other five copies of that list do not.
- The "Cannot verify" line disagrees on whether it applies to a *check* or
  an *item*, and on whether the project lead "resolves" it.

The four review agents each hold a full copy of the same findings
convention — severity tags, the "Cannot verify" escape, the no-`SendMessage`
line, the two verdict lines. No file in `CLAUDE.md`'s Authority list owns
it. Decide: a fifth reference that owns the review-output convention, or an
accepted exception with a stated reason. A reference the agents read costs
each dispatch a `Read`; four copies cost a drift. Say which cost this
project takes.

Done when: the three drifts are gone, every rule the audit named has one
owner or a recorded exception, and `CLAUDE.md`'s Authority list matches.

Read first: design §15.27; `writing-standard.md`; the four agents under
`agents/` that carry the findings convention.

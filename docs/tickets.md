# Tickets

The build backlog, from the current state (stages 0-6 built: both paths
run) to the target state: a working three-tier hierarchy —
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

Note (T14): the charter's optional `Instruments:` line, and the
`run.instruments_used` record field it feeds, are `record-format.md`'s
(design §6.4). This does not reopen T4.

## T5 — Probe: `TeammateIdle`

Status: done
Depends on: nothing
Stage: pre-5 (design §13.1)

Run the probe procedure design §13.1 carried until this ticket closed
(the procedure is in the git history now): does exit 2 block a teammate's
idle, does stderr reach the teammate, and does the payload identify the
idling teammate and carry a session id or cwd? Needs an interactive
session with `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` — headless `-p`
cannot spawn a teammate (design §12). Remove the probe hook registration
right after.

Done when: all three questions have probed answers recorded in design §15
as a new finding.

The probe ran on 2026-08-31 on Claude Code 2.1.252. All three answers are in
design §15.29, with two findings the ticket did not ask for. The refusal loop
ends at a harness cap on consecutive blocks that any tool call resets, so a
working IC can be refused forever. And a project lead can re-engage an idle
teammate with one message, which does the hook's whole job. §13.1 cuts the
hook on that evidence; T7 builds the nudge.

Read first: design §15.29, §13.1, §12, §15.8.

## T6 — Full path: worktrees, territories, teammates

Status: done
Depends on: T4
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

The loop landed on 2026-09-01 as
`skills/project-lead/references/full-path.md`; design §15.30 records the five
decisions it forced, and §15.31 the environment probe that corrected two of
them.

It then ran, the same day, on `jerridan/convert-keys-js` — two packages, two
territories, two IC teammates, a squash merge each with a suite run, and a
draft PR (#7) with zero escalations. Design §15.35 records what that proved
and the nine things it found. §12's plan-approval probe is closed: the
message form works, and the project lead approved with added requirements
rather than rubber-stamping.

A third run on the same repo closed the remaining two clauses the same day —
`toTitleCase` plus `docs/OVERRIDES.md`, draft PR #8. A fix round was forced on
a real defect the package reviewer had missed (a dead `.toLowerCase()` that
`lodashSnakeCase` makes unreachable): fixed, re-diffed as `-r1`, re-reviewed,
accepted, with `fix_rounds_used` persisted at 1. The pane was then killed with
one package merged and the record stale on both; a fresh session reconciled
from git, corrected both packages to `integrated`, appended rather than
overwrote the session ids in `state.json` and `worktrees.json`, re-dispatched
nothing, and carried the run to the PR. Design §15.36 records that run.

Two transitions stay unproven and belong to T7, not here: `run_state` never
became `interrupted` and no worktree was ever marked `orphaned`, because the
`SessionEnd` hook that writes both does not exist. Recovery was therefore
tested against a record that still claimed the dead run was `active`, which is
the harder case, not the easier one.

Read first: design §9.2-9.4, §10, §10.1, §15.10-12, §15.23, §15.30;
`record-format.md`; `ic-contract.md`; `full-path.md`.

## T7 — Hooks: `SessionEnd`, and the idle nudge that replaces `TeammateIdle`

Status: done
Depends on: T6
Stage: 5 (design §13.1)

Ship `hooks/hooks.json` with one hook: `SessionEnd` marks the run interrupted
and its worktrees orphaned, writes only, deletes nothing. Include the guard
clause that exits at once when no crew record exists. No hook ever removes a
worktree.

`TeammateIdle` is cut (design §13.1, §15.29). Its job moves into the project
lead: when an IC idles with no report, the project lead messages it with what
is missing and where to write it. Build that beside the §7 verification, which
is where the project lead already reads the IC's report file and `git` log. Let
a plan-gate pause pass — `plans/<id>.md` written and `plan_approved_at` null
(§15.8) — and send at most one nudge per dispatch; a second empty idle fails
the package instead.

Add the rule §15.29 found missing, which outlives the hook: what an IC does
when a mechanism, not a reviewer, is what blocks it. `ic-contract.md` owns it.

Done when: a crashed run's next `--resume` finds `run_state: interrupted`, and
an IC that idles without a report gets one nudge and finishes, while a
plan-gate pause gets none.

`hooks/hooks.json` and `hooks/session-end.py` landed on 2026-09-02. The hook was
probed end to end: a seeded record plus `claude -p --session-id <uuid>
--plugin-dir <repo>` left the run `interrupted` and its worktree `orphaned`,
and left another session's worktree and a `complete` run untouched. Design
§15.38 records the probe and three things it settles.

The nudge is `full-path.md` step 5a, with `nudges_used` in the record and the
mechanism-block rule in `ic-contract.md`.

Two runs against a scratch repo then tested it (§15.40). They found that a
project lead invented its session id rather than reading it, which would have
stopped the hook matching any real run — fixed in `record-format.md`, and
§15.39 records it. They proved the plan-gate branch takes no nudge, and that
the hook fires against a record a run wrote rather than one seeded by hand.

The nudge itself stays unproven. Both runs baited an IC to idle with no report
and both ICs wrote their reports anyway, because `ic-contract.md` held. That is
evidence for §13.1's reason for cutting `TeammateIdle`, not a gap to keep
hunting: the failure is hard to provoke on purpose. Leave the clause open and
close it from a real run that hits it, not from a better rig.

One defect the runs exposed belongs to its own ticket, not here: a deliverable
that cannot open a PR has no honest terminal state (§15.40f, which T11 also
needs).

Read first: design §13.1, §15.8, §15.29, §15.38-40, §7; `record-format.md`;
`ic-contract.md`.

## T8 — Council, routing, `decisions.md`

Status: done
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

The council landed on 2026-09-02. `agents/council-advocate.md` argues one
assigned position; `autonomy-contract.md` owns the procedure — framing, the
single batch, adjudication, the balanced-council escalation, and
`spend.council_tokens`. `record-format.md` owns the council entry, which adds
`Positions`, `Losing`, `Models` and `Spend`. Design §15.9 is decided, and
§15.41 records why the advocate got its own agent definition rather than an
inline `general-purpose` brief — a revision to design §3's Advocate row.

A council then ran by hand, the same day, on T10's open question — three
advocates in one batch, every citation checked, and a decision that split the
question rather than picking one advocate's side. §15.43 records what it
proved, what it cost (169,257 tokens for three sonnet advocates), and the
defect it found: a hand-dispatch drops an agent's frontmatter, so neither the
model nor the effort in the definition was in force.

A follow-up probe then tested the effort the hand-dispatch had skipped, in a
rig where the frontmatter does apply (§15.44). At medium effort an advocate
quoted real text under line anchors that miss, which costs the judge the
search the citation exists to save, for a 16% saving. `reasoning_effort: high`
stays, and the advocate now has to look each line number up — §15.45 found
that the runs which anchored correctly all did, so the variable may be
verification rather than reasoning depth.

Two more probes ran in the same rig (§15.45). A spawn-time `model` does not
cost an agent the effort in its frontmatter, so `band-rubric.md`'s
raise-to-opus rule is safe. Whether a subagent inherits its parent's effort is
still unknown: both arms scored full marks, so the probe measured nothing. The
teammate form of that question needs an interactive session and stays open.

The "in a real run" clause closed the same day (§15.47). A
`/crew:project-lead` run on T16 routed a naming question to a council itself,
framed three positions, dispatched three advocates in one batch, adjudicated at
opus, and reached draft PR #16 with zero escalations and one forced fix round.
The council cost 126,168 tokens of the run's 744,244. Its judge caught a losing
advocate's two bad line anchors and named where the text actually sits, which
is §15.46's rule working in the direction that earns its cost.

Two defects that run exposed are open and unowned: every `decisions.md`
`Timestamp` was midnight, now fixed in `record-format.md`; and the simple path
leaves the checkout on the run's own branch when it finishes. The
balanced-council escalation stays unexercised — both judges so far were
decisive.

Read first: design §6, §6.1, §6.2, §15.9, §15.41; `record-format.md`;
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

Status: done
Depends on: nothing
Stage: any (design §15.17)

`crew:ic-instructions` owns four container types; a README is none of
them, and the writing standard flags its routing as unsettled. Decide:
grow the specialist's list to cover reader-facing prose, or name a
different owner. Record the decision in design §15.17 and align §3.1,
`agents/ic-instructions.md`, and `writing-standard.md`'s README note.

The decision is made. T8's first council settled it on 2026-09-02: a README
goes to `crew:ic-instructions` as a fifth container type, and a PR body, an
issue and a comment stay with the project lead. §15.17 carries it and §15.43
the council. What remains here is the alignment — §3.1,
`agents/ic-instructions.md` and `writing-standard.md`'s README note — and one
sub-question the council raised: whether a specialist named `ic-instructions`
whose container list now includes non-instructions needs a different name.

Done when: the four files agree and §15.17 reads "Decided".

Read first: design §15.17, §15.43, §3.1; `writing-standard.md`.

## T11 — Design the investigation path

Status: done
Depends on: nothing
Stage: design (`docs/design.md`)

Crew's loop assumes the goal is a change: spec, split, implement, draft
PR. A bug or a support ticket starts from an unknown — most of the work
is diagnosis, and a run can legitimately end with no code change. Write
the design section for an investigation path:

- A bug charter: the acceptance criterion is a reproduction — a test or
  command that fails now and must pass after the fix.
- A diagnosis artifact in the record — evidence, root cause, ruled-out
  hypotheses — and `work-complete`, the terminal deliverable state for a run
  that ends in a report instead of a PR (T16). `record-format.md` owns both
  names.
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

Landed 2026-09-04 as design §9.5, five §14 rows, and `diagnosis.md` in
`record-format.md` (§15.55). The tickets it implies are T12 below, T31 and
T32.

## T12 — Implement the investigation path

Status: open
Depends on: T4, T11, T31, T32
Stage: after 4

Extend `/crew:project-lead` with design §9.5. Four pieces, in the order a
run meets them:

1. **The choice at step 1.** §9.5 picks the path from the charter, before
   scouting, not at step 5's shape table. A goal whose acceptance criterion
   cannot be written until something is diagnosed is a symptom. Step 1
   already writes that criterion, so this is a branch in an existing step,
   not a new one.
2. **The diagnosis loop.** `Explore` subagents and `crew:researcher` gather
   evidence to files; the project lead reads the paths, never the reading.
   This is `crew:researcher`'s first caller — nothing dispatches it today.
   More than one surviving hypothesis convenes a three-advocate council
   (§6.1, T22 case 2) over one named evidence set.
3. **`diagnosis.md`.** Five headings, in `record-format.md`'s order. A
   diagnosis deliverable holds no package, so the first evidence dispatch is
   what moves it `in-flight`.
4. **The two endings.** `Outcome: fix` rejoins step 5's table with the
   reproduction as the package's acceptance criterion and `diagnosis.md` in
   the IC spawn prompt and the PR body. `Outcome: no change` runs the
   adversary review first (`reviews/diagnosis-adversary.md`), then ends the
   run `work-complete` with `pr_url: null` and four `null` branch and
   checkout fields.

`SKILL.md` is at its size limit and T27 splits it, so the loop's text goes
in a reference, not in the body. Decide with T27 whether that is
`simple-path.md` or a file of its own. §9.5's three council rules belong in
`autonomy-contract.md`, which owns the council; the loop file points at
them.

Done when: one real bug goes from ticket text to a draft PR whose new
test reproduces the bug and passes after the fix, with zero prompts; and
one no-code-change question ends in a recorded diagnosis instead of a
PR.

Read first: design §9.5, §9.1, §6.1, §14; `record-format.md`
`diagnosis.md` and the deliverable transitions; `autonomy-contract.md`;
`SKILL.md` steps 1 and 5; T27, T31, T32.

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

Status: done
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

Status: done
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

`skills/project-lead/references/review-output.md` landed on 2026-08-31 and owns
the convention. Each agent keeps only its own two verdict strings. Design §15.28
records the decision and the cost it takes.

Read first: design §15.27; `writing-standard.md`; the four agents under
`agents/` that carry the findings convention.

## T16 — A terminal deliverable state for a run that opens no PR

Status: done
Depends on: nothing
Stage: any

A deliverable has four states: `pending`, `in-flight`, `draft-pr-opened` and
`abandoned`. None of them fits a deliverable that finished its work and could
not open a PR, so a project lead in that position has to record something
untrue. Both probe runs on 2026-09-02 did: the scratch repo had no git remote,
so `git push` and `gh pr create` could not run, and each run closed with
`state: "draft-pr-opened"` and `pr_url: null` — a state that names a PR nobody
opened (design §15.40f).

`abandoned` is not the answer. It means a re-plan dropped the deliverable or a
breaker parked it, and it says the work is not to be trusted. Here the work is
complete, reviewed and green.

Add the fourth terminal state and thread it through:

- `record-format.md` owns the vocabulary: name the state, add it to the
  deliverable field table, to the state-transition diagram and its arrow list,
  and to the consumer index. Say what `pr_url` holds in it, and that the branch
  name is what the principal is handed instead.
- `SKILL.md` step 14 and `full-path.md` step 11 both say to push and open a
  draft PR. Each needs the branch for when that is impossible or refused.
- Keep the escalation. Both runs asked the principal before closing, and that
  was right — this ticket changes what gets recorded after the answer, not
  whether to ask.

Two callers need it, so pick a name that serves both: a run blocked by the
environment, and T11's investigation path, which ends in a diagnosis report
rather than a change and needs the same terminal state.

Done when: a run in a repo with no remote reaches a truthful terminal state
with `pr_url: null`, `record-format.md`'s transition diagram covers it, and
T11's ticket names it as the state its report path ends in.

`work-complete` landed on 2026-09-02, written by a `/crew:project-lead` run on
this ticket (design §15.47). The name came from a council. Two of the three
clauses are met: the diagram covers it, and T11 names it.

The first clause is not. **No run has reached `work-complete`**, so the path
that writes it is unexercised — the same shape as T7's nudge clause. An
independent review then found six defects in the run's own output, three of
them substantive, including a recovery hazard that would have re-opened a
refused PR (§15.49). Those are fixed here. Close the last clause from a run in
a repo with no remote.

Read first: design §15.40f, §15.47, §15.49, §9.3, §10; `record-format.md`
deliverable states and transitions; T11.

## T17 — Restore the checkout's branch when a simple-path run ends

Status: done
Depends on: nothing
Stage: any

The simple path works on the current checkout by design (§9.1) — no worktree,
one deliverable branch, `git switch -c` at step 7. Nothing switches back. A run
that finishes leaves the checkout on `crew/<goal-slug>/<deliverable-id>`, and
the next person or session in that directory is on a branch it did not choose.

This is not hypothetical. The §15.47 run left the T8 session on the run's
branch, and that session's next two edits landed there before it noticed
(design §15.47). The cost is silent: a commit on the wrong branch looks exactly
like a commit on the right one.

Decide who restores it and when, then write it into the file that owns the
step:

- Record the branch the checkout was on **before** step 7, so the run can put
  it back. `record-format.md` owns the field name; `deliverables[].base`
  already records the sha, which is not the same thing as the branch name.
- Say what happens when the tree is dirty at the end, or when the principal
  wants to stay on the deliverable branch to look at it. Switching a checkout
  out from under a person is its own failure.
- Both paths switch the checkout: `SKILL.md` step 7 on the simple path, and
  `full-path.md` step 3 on the full path, whose ICs work in worktrees but whose
  project lead does not. The rule's text lives in `SKILL.md`, and `full-path.md`
  points at it twice, rather than carrying a copy.

Done when: a simple-path run ends with the checkout on the branch it started
on, or with a recorded reason why it did not, and a second run in the same
directory starts from a known branch.

2026-09-04: done. `SKILL.md` step 7 records `deliverables[].checkout_branch`
and step 14 switches back; `deliverables[].checkout_restored` holds `true` or
the reason it did not. `full-path.md` points at those two steps from its own
step 3 and step 11. Two simple-path runs in one fixture checkout proved it:
`~/.claude/crew/truncate-helper-bfa8/` and, from the same directory,
`~/.claude/crew/slugify-stage-3-fa89/`. Both record `checkout_branch: "main"`
and `checkout_restored: true`, and both left the checkout on `main` and clean
(design §15.54). No run has exercised the full path's restore.

Read first: design §9.1, §15.47; `record-format.md` deliverable fields;
`SKILL.md` steps 7 and 14.

## T18 — Sweep for stale status claims before a change lands

Status: done
Depends on: nothing
Stage: any

Every file that says what is built goes stale the moment a stage lands, and the
session that lands it is the session least likely to notice — it has just spent
its context on the change, not on the sentences the change falsified.

Three instances in one day, 2026-09-02: the README's banner and status row
still said no run had convened a council after §15.47's run did; design §13's
stage-6 row said the procedure was unexercised in the same file that recorded
the run; and crew's own `crew:ic-instructions`, in a fix round, reintroduced
"Councils are not built" into `SKILL.md` (§15.48, §15.49). Two were caught by a
code review, one by a rebase conflict. None by reading.

`CLAUDE.md` and `writing-standard.md` already carry the rule — keep every "not
built" claim true whenever a stage lands. The rule is not the gap. The gap is
that nothing runs at the end, when the claims have actually changed.

Build the check:

- A grep over the change's own diff for the vocabulary that dates: "not built",
  "no run has", "unexercised", "not yet", "stub", "does not exist yet",
  "deferred". The list belongs in one file, not in each agent's head.
- Say who runs it. The project lead at integration (`SKILL.md` step 12) is the
  natural owner, because that is where it already edits shared files. An IC
  cannot own it: an IC sees one package's file set, and a claim in `README.md`
  is stale because of a change in `agents/`.
- Decide whether `crew:deliverable-reviewer` gets it as an eighth check
  instead. It already reads the whole diff against the spec, which is the same
  shape of work. One owner, not two.

Done when: a run that lands a stage leaves no file claiming that stage is
unbuilt, and the check is stated in exactly one place.

Read first: design §15.48, §15.49; `writing-standard.md`'s "Keep the status
true"; `SKILL.md` step 12; `agents/deliverable-reviewer.md`.

2026-09-04, done. `writing-standard.md`'s "Keep the status true" holds the
vocabulary list and the commands; `SKILL.md` step 12 runs them;
`crew:deliverable-reviewer` got no eighth check. The terms quoted in the
first bullet above are this ticket's original ask, not a second list —
`writing-standard.md` is the one that counts, and it has grown three terms
since. A run then landed a stage with the sweep on:
`~/.claude/crew/truncate-helper-bfa8/`, a simple-path run on a string-kit
fixture. At step 12 the project lead found two stale claims that no IC file
set held — the fixture's `README.md` roadmap row and its `CLAUDE.md` line
about `truncate` — fixed both, and left the still-true `slugify` rows. Design
§15.52 holds the evidence.


## T19 — Probe: `PreCompact` for an in-process teammate

Status: open
Depends on: nothing
Stage: any (design §13.1, §15.50)

`hooks/pre-compact.py` appends to `run.compactions` when the compacting
session belongs to a live run, matched by `run.session_ids` or a worktree's
`session_ids`. It was tested with a seeded payload and a record copy. Nothing
has shown that the harness fires `PreCompact` for an in-process teammate at
all, or that its payload carries `agent_id` and a `transcript_path` whose
sibling `.meta.json` names the teammate, which is how the hook attributes it.

Done when: an IC teammate is driven past its compaction threshold in an
interactive session with agent teams on, and `run.compactions` holds an
entry whose `agent` is that IC's name, as `full-path.md` step 6 matches it. Record the payload
shape in design §15.

Read first: design §13.1, §15.50; `hooks/pre-compact.py`; `full-path.md`
steps 6 and 8a.

## T20 — Probe: a review agent's write to the record root

Status: open
Depends on: nothing
Stage: any (design §15.50)

`review-output.md` now has every review agent write its report to the path
its dispatch names and return three lines. An IC's record writes are denied
in some dispatch shapes (design §15.26b, §15.31b), and the same may hold for
an unnamed reviewer. The fallback is in place — the whole report returns when
the write is denied — but the saving only lands when the write succeeds.

Done when: one run on each path shows a `reviews/` file written by the
reviewer itself, or the denial is recorded in design §15 with the dispatch
shape that produced it.

Read first: design §15.26, §15.31, §15.50; `review-output.md`.

## T21 — Batch the principal's questions before the split

Status: done
Depends on: nothing
Stage: any (design §6, §15.50)

Six runs, zero escalations. In the A/B both leads answered a question the
charter left open on purpose and that only the principal could answer —
whether `/book` gets per-book routes — by calling it precedent (§15.50).
`autonomy-contract.md` says a question about what the principal wants is
never debated, but nothing makes the project lead look for one at the
moment it can still ask cheaply.

Add a step between the spec and the split: list every open question in the
charter and the spec that turns on the principal's preference rather than
on the repo, and escalate them as one batch. One interruption, before any
IC runs. A lead session answers the batch by message; a human answers it in
the session. `autonomy-contract.md` owns the routing rule; `SKILL.md` gains
the step.

Done when: a run on a charter with one seeded preference question escalates
it before the split, and a run on a charter with none escalates nothing.

2026-09-04: done. `SKILL.md` step 4a sweeps `charter.md` and `spec.md` before
the split, `autonomy-contract.md` owns the rule under The preference sweep,
`record-format.md` owns the entry, and `crew-record.py` gained `escalation
add` so a batch appends instead of replacing the list. Both runs behaved as
this ticket asks: `~/.claude/crew/slugify-stage-3-fa89/` escalated one seeded
question before the split, and `~/.claude/crew/truncate-helper-bfa8/` found
none and recorded `Answer: none` (design §6.3, §15.53).

Read first: design §6, §6.2, §15.22b, §15.50, §15.53; `autonomy-contract.md`.

## T22 — Redesign the council: one adversary by default, three advocates by exception

Status: open
Depends on: T21
Stage: any (design §6.1, §15.43, §15.47, §15.50)

Three councils have run: a README owner, a state name, and a CSS strategy.
The third question was settled from precedent by the other arm of the same
experiment. No council has yet produced an answer the record shows the
project lead would not have reached alone, and the one judgment failure both
A/B leads shared — answering a preference question as if it had precedent —
is one a council would have buried, not caught (§15.50). A Fable project lead
finds precedent reliably and judges sonnet advocates from above, so three
advocates is the wrong shape for most questions.

Change three things, in `autonomy-contract.md`, which owns routing and the
council, and `record-format.md`, which owns the entry:

1. **No council for a question with repo precedent.** Route it to precedent
   with the citation. Preference questions go to T21's batch, never to a
   council.
2. **The default council is one adversary.** The project lead writes its own
   answer and confidence to the entry as `Prior:` first, then dispatches one
   `crew:council-advocate` to argue the opposite with citations. A prior the
   project lead cannot rebut in writing is an escalation. Same entry shape,
   `Positions` holding two.
3. **Three assigned advocates stay for two cases only.** The first is a
   choice that is both costly to reverse and unclear in the moment: the
   project lead's `Prior:` carries low confidence, and the repo holds no
   precedent. Both conditions, not either. A low-confidence choice that is
   cheap to reverse is a fix round, not a council; a costly choice the
   project lead is confident in gets one adversary. The second is T11's
   investigation path, where competing root-cause hypotheses over one body
   of evidence is what assigned positions are for. Beyond those two, a full
   council is not worth its cost (§15.50, and the 2026-09-04 runs under
   T21: two advocates settled an ellipsis character the charter's own
   invariant already answered).

Then measure: after ten adversary entries, compare `Prior:` with the
adjudication. If the adversary never moved the answer, cut it and keep only
case 3.

Done when: the two references carry the three rules, `agents/council-advocate.md`
argues one position against a stated prior as well as one of several, and
the next council that runs is an adversary entry with `Prior:` filled.

Read first: design §6.1, §6.2, §15.43, §15.47, §15.50; `autonomy-contract.md`;
`record-format.md` council entry; `agents/council-advocate.md`; T11, T21.

## T23 — Measure the review layer's catch rate

Status: open
Depends on: T25
Stage: any (design §7, §15.49, §15.50)

Package reviews are the largest fixed cost per package: 17 in one arm of the
A/B, 10 in the other. In the Opus arm several pages passed review with zero
findings and then failed the fidelity harness; §15.49's six defects passed
two reviews and were found by an outside code review. The record holds every
review and every fix round, so the catch rate is computable: findings that
led to a commit, by reviewer, by band, against defects found later.

Compute it with T25's script over every record on the machine. Then decide,
with the numbers: whether a `standard` package with a green acceptance tool
skips package review and relies on the deliverable review; whether the
package reviewer moves to opus; or whether nothing changes.

Done when: the catch rate is in design §15 with the decision it supports.

Read first: design §7, §15.49, §15.50; `agents/package-reviewer.md`;
`review-output.md`.

## T24 — Recommend a launch model for the project lead

Status: done
Depends on: nothing
Stage: any (design §8, §15.50)

`README.md`'s model table says the project lead runs on "your session's"
model and never says which to choose. §15.50 measured two: on the goal that
could separate them, the Fable 5.1 lead cost two thirds of the Opus 5 lead,
took no fix rounds, and made the better process choices.

Decide whether the README names a recommended launch model and effort, and
whether design §8 records the reasoning. The principal owns this call: the
model is billed to the principal's account, and Fable is not the default on
any plan.

Done when: the README's model table and its launch example agree with each
other and with §8, and neither presents "your session's" as the only answer.

Decided 2026-09-03 on §15.50's evidence: the project lead launches on Fable
5.1 at high effort. `README.md` carries the launch command and the model
table row; design §8 carries the reasoning.

Read first: design §8, §15.50; `README.md` "What each agent runs on".

## T25 — A stats script over every record

Status: done
Depends on: nothing
Stage: any (design §8, §15.50)

Design §8 promised the band rubric would turn from a guess into a
measurement. The data now exists: `band_history`, `fix_rounds_used`,
`spend.transcript`, `run.compactions`, and every review
and report file. Nothing reads it across runs.

Add `skills/project-lead/scripts/crew-stats.py`: over every record under the
record root, print cost per package by band, fix rounds by band, promotions,
councils and their spend, escalations, compactions, review counts and, once
T23 defines it, review catch rate. Use it to give a principal a defensible
`Budget:` figure for a goal of a given size.

Done when: the script runs over the records on the machine that ran the A/B
and its numbers for the two §15.50 runs match the ones recorded there.

Done 2026-09-03: `skills/project-lead/scripts/crew-stats.py`. Every count for
the two §15.50 runs matches, decisions included. The dollars need a run end as
well as a start, which `spend.py` did not take: bounded to each run, the arms
price at $213.91 and $142.37, against $215.39 and $144 recorded. §15.51
records why the bounded figure is a floor and the open-ended one a rising
ceiling.

Read first: design §8, §15.50, §15.51; `record-format.md`; `scripts/spend.py`.

## T26 — A/B a goal-and-constraints form of `SKILL.md` on Fable

Status: open
Depends on: nothing
Stage: any (design §8, §15.50)

The project lead now runs on Fable 5.1 (T24). Fable's own guidance says
prompts written for prior models are often too prescriptive and reduce
output quality, and that stating the goal and constraints beats enumerating
steps. `SKILL.md` is a fourteen-step numbered loop and `full-path.md` a
thirteen-step one. The evidence so far cuts the other way: a Fable project lead ran
the numbered loop in 130 turns with zero fix rounds (§15.50). So this is a
measurement, not a rewrite.

Crew's files already sort by reader. The project lead's files are read by
Fable; `ic-contract.md`, the IC and review agents, `review-output.md` and the
advocate are read by sonnet and opus, which do better with explicit steps.
Only the project lead's files are candidates, and no file gets two variants —
a second copy of a rule is the drift `CLAUDE.md` forbids.

Write a goal-and-constraints form of `SKILL.md` that keeps every rule and
every pointer to a reference, under a temporary second skill name so both
forms load. Run one simple-path goal with each, on Fable at high effort, in
fresh clones, with `CREW_RECORD_ROOT` set per arm. Compare lead turns, lead
spend from `scripts/spend.py`, decisions, critic rounds, fix rounds and the
independent check of the two PRs.

Done when: design §15 records the comparison and the decision. If the goal
form wins, it replaces `SKILL.md` and the same treatment goes to
`full-path.md` under its own A/B. If it does not, the numbered form stays and
the entry says why.

Read first: design §8, §15.50; `writing-standard.md`; `SKILL.md`;
`full-path.md`; the Fable 5.1 prompting guidance the `claude-api` skill
carries under "Long-running agent recommendations".

## T27 — Move the simple-path loop out of `SKILL.md`

Status: open
Depends on: nothing
Stage: any (design §15.25, §15.29a)

`SKILL.md`'s body has sat at the writing standard's 200-line cap since T18
landed. T17, T18 and T21 each paid for a new rule by cutting a sentence that
was not a rule: "A finding is a claim, not a verdict" and "Your own context is
the most expensive place to work" are both gone. The cap is crew's own
(`writing-standard.md` rule 4); Anthropic's skill guidance says under 500
lines, and says that a workflow that grows large moves into its own file
which the skill tells the reader to load by task.

The full path already works this way: `full-path.md` replaces steps 6 to 14
when the shape is more than one package (§15.29a). The simple path has no
such file, so every rule added to the run loop lands in the fullest file.

Do the same for the simple path:

- Add `references/simple-path.md` holding steps 6 to 14, the same shape as
  `full-path.md`. `SKILL.md` keeps the shared prefix — the reference list,
  steps 1 to 5 with 4a, and the shape table — which then points at one of the
  two path files.
- Steps 12 to 14 are shared between the two paths. Keep each in one file and
  point at it from the other, as `full-path.md` already does for step 14.
- Put back what the cap cost. Three sentences are in no file the project
  lead reads at runtime: "A finding is a claim, not a verdict" (step 4, the
  heuristic behind the adjudication rule; §15.46 is why it matters), "Your
  own context is the most expensive place to work" (after the step 5 table;
  design §9.1 and `review-output.md` say it, and neither is the project
  lead's file), and "Your output is the run's most expensive" (step 3, the
  reason a sonnet subagent writes the spec prose). Restore all three. The
  other cuts moved to their owners and stay pointers: the principal's
  definition (`autonomy-contract.md`), the write-every-transition rule
  (`record-format.md`), the hard-wrap rule (`writing-standard.md`), and
  `checkout_restored: null` at creation (`record-format.md` documents the
  default).
- Rewrite `writing-standard.md` rule 4: 200 lines is a target for a
  `SKILL.md` body, 500 is the limit the skill guidance sets, and a reference
  file has no cap. Say why in one sentence.
- Every citation of a `SKILL.md` step number in `full-path.md`,
  `record-format.md`, `autonomy-contract.md`, `writing-standard.md` and
  `docs/tickets.md` still resolves: keep the step numbers, so §15's findings
  stay true.

Do this before T26. If the goal-and-constraints form wins that A/B, it is the
path files that shrink, and the split should already be in place.

Done when: `SKILL.md`'s body is under 120 lines, a simple-path run reads
`simple-path.md` and reaches a draft PR with zero prompts, and no rule has two
copies.

Read first: design §15.25, §15.29a, §15.50; `writing-standard.md` rule 4;
`SKILL.md`; `full-path.md`.

## T28 — Give `run.completed_at` an owner

Status: open
Depends on: nothing
Stage: any (design §8, §15.51)

`crew-stats.py` bounds a run's cost at `run.completed_at`, or at the latest
`state_changed_at` in the record when that field is absent. One of eleven
records carries it, `record-format.md` does not document it, and nothing
writes it (§15.51). So every priced run is bounded at its last state write,
which drops the run's own tail: the turns that open the PR and write the
closing summary. That tail was $10.38 on the Opus arm and $1.99 on the Fable
arm.

Make the field real:

- `crew-record.py` stamps `run.completed_at` with the current time on every
  write that sets `run_state` to `complete` — the `close` command and
  `run set run_state complete`. The project lead writes nothing extra; the
  transition is the trigger.
- `record-format.md` documents the field beside `created_at`, names its
  consumer (`crew-stats.py`), and adds it to the name inventory. Say that an
  `interrupted` run has no `completed_at`, and that `--resume` never sets one.
- Order at the end of a run: the `complete` write comes before
  `spend.py --write`, so `spend.transcript.measured_at` sits after
  `completed_at`. `crew-stats.py` prefers a stored `spend.transcript` when
  one exists, so a run priced at its end keeps its tail; say so in the field's
  row.
- `crew-stats.py` treats `abandoned` as a terminal `run_state`, and
  `record-format.md`'s transitions table has no such value. Decide which file
  is right and fix the other.

Done when: a simple-path run ends with `run.completed_at` set by the script,
not by the project lead, and `crew-stats.py` prices that run without printing
its open-ended-cost skip line.

Read first: design §15.51; `record-format.md` `run_state` transitions and
`created_at`; `scripts/crew-record.py` `close`; `scripts/crew-stats.py`
`run_end`.

## T29 — Check for a remote before the run starts

Status: open
Depends on: nothing
Stage: any (design §6, §15.52, §15.53)

Both 2026-09-04 runs under T21 ran the whole loop, then escalated at step 14:
the fixture had no git remote, so the push and `gh pr create` could not run.
That was knowable at step 1 from one `git -C <repo> remote` call. A run with a
preference question and no remote interrupts the principal twice, which is
what T21's batch exists to prevent; a run with no preference question spends
its whole budget before it asks whether a PR is possible at all.

Add "can this run push and open a draft PR" to the checks that run before the
preference batch. `full-path.md` step 0 owns the launch checks and T21's rule
in `autonomy-contract.md` already folds them into the batch; add the remote
check beside them, so it applies on both paths. The question to the principal
offers the same three ends step 14 offers today: add a remote, keep the work
local as `work-complete`, or stop. An answer given at the start is recorded
once and step 14 never asks again.

Done when: a run on a checkout with no remote asks about the PR in the same
batch as its preference questions, before the split, and step 14 ends the run
without a second ask.

Read first: design §15.52, §15.53; `autonomy-contract.md` "The preference
sweep"; `full-path.md` step 0; `SKILL.md` step 14.

## T30 — Write a preference answer into the target repo as precedent

Status: open
Depends on: nothing
Stage: any (design §6, §15.53)

Run B under T21 asked the principal what `slugify` does with `café`, got
"strip the accents first", and recorded the answer in the run's `decisions.md`
and `escalations`. Nothing wrote it into the target repo. The next run on
that repo will find no precedent and ask the same question. The project lead
saw this and, in its closing message, proposed one line for the repo's
`CLAUDE.md`. Make that a step, so each preference question is asked of a
repo once.

The rule: when the principal answers a preference question, the answer
becomes an instruction package in the split. Its brief carries the answer;
its deliverable is one rule in the target repo's instruction files; its
acceptance is `writing-standard.md`'s checklist. That checklist is what keeps
the addition short, keeps it from competing with a rule the repo already has,
and puts it in the right container: a rule that applies to one area of the
repo goes in a `.claude/rules/` file scoped to that path, not in the root
`CLAUDE.md`. The container-choice check decides. `crew:ic-instructions` owns
instruction packages (design §3.1), and this is one; decide whether a
one-line package earns a dispatch or whether the project lead writes it at
integration under the same checklist, and say why in `autonomy-contract.md`.

Done when: a run that escalates a preference question ends with the answer
in the target repo's instruction files, in the container the checklist
chooses, and a second run on that repo with the same question resolves it as
precedent with a citation and escalates nothing.

Read first: design §3.1, §6, §15.53; `autonomy-contract.md` "The preference
sweep" and the routing table; `writing-standard.md` container rules;
`agents/ic-instructions.md`.

## T31 — Let a council advocate argue a root cause, and concede one

Status: open
Depends on: T22
Stage: after 4 (design §6.1, §9.5)

Design §9.5 sends competing root causes to a three-advocate council. That is
T22's second exception, and `agents/council-advocate.md` cannot serve it yet.
Two things are different from a design council.

**The evidence set is given, not gathered.** A design advocate searches the
repo for its own citations. A root-cause advocate must argue over the same
evidence as its two siblings, or the three cases are about different bugs.
The dispatch names the evidence paths from `diagnosis.md`, and the advocate
cites those files. It may read the repo to understand a path it was given; it
may not go looking for a fact nobody else has.

**An advocate may concede.** A design question has no true answer, so the
strongest case for a losing position is still worth writing. A root cause has
one. An advocate that argues a refuted hypothesis anyway hands the judge a
case built on nothing, and the judge's whole input is these three cases. Give
the agent a third report shape: the assigned hypothesis is contradicted, with
the citation that contradicts it. That shape is a finding, not a failure.

Keep it one agent. A second definition would hold two copies of the advocacy
rules, and `review-output.md` already shows how one output shape serves
several callers.

Done when: `agents/council-advocate.md` takes an evidence set and an assigned
hypothesis, a hand-dispatched advocate over a seeded bug cites only the given
evidence, and an advocate assigned a hypothesis the evidence refutes concedes
with the citation instead of arguing.

Read first: design §6.1, §9.5; `agents/council-advocate.md`;
`record-format.md` `diagnosis.md` and the council entry; T22.

## T32 — Prove the reproduction fails before the fix

Status: open
Depends on: nothing
Stage: any (design §7, §9.5)

Design §9.5 makes the reproduction the fix package's acceptance criterion,
and it requires two clauses: the test fails now, and it passes after. Crew
checks only the second. `SKILL.md` step 9 runs the acceptance criterion after
the IC reports, and §7's verification table has no "before" row. A test that
never failed passes that check and proves nothing.

This is not only the investigation path's problem. Any package whose
acceptance criterion is a new test has it, which is why the rule belongs in
§7 and `ic-contract.md` rather than in §9.5.

Decide who runs the failing case and where the output lands:

- The IC writes the test first and commits it red, which `ic-contract.md`
  already implies but never states. A commit whose suite is red is the
  evidence, and `git log` holds it.
- Or the project lead runs the criterion at dispatch, before the IC starts,
  and records the failure. That costs a suite run and cannot be faked by an
  IC, which is the argument for it.

Pick one, and say in `record-format.md` where the failing output is kept. Do
not add a second `state.json` field if a commit already proves it.

Done when: §7's table carries the "fails before" row, the file that owns the
step says who runs it, and a package whose new test passed from the start is
rejected by that check rather than by a reviewer noticing.

Read first: design §7, §9.5, §5 (invariant 1); `ic-contract.md`;
`SKILL.md` steps 8 and 9; `record-format.md` `acceptance_criterion`.

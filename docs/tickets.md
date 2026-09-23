# Tickets

The build backlog, from the current state (stages 0-6 built: both paths
run) to the target state: a project lead that takes one goal to a draft PR
and dispatches its own ICs (design §15.95).

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

The nudge is `full-path.md`'s "The idle nudge", with `nudges_used` in the
record and the
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

## T9 — The lead tier: two goals from one lead session

Status: done
Depends on: T37
Stage: 7 (design §1, §15.21-22, §15.70)

The proof of the tier T36 and T37 build. Run two goals concurrently from one
lead session: the lead writes both charters, spawns one project-lead session
per goal, reads both records under `~/.claude/crew/`, answers what it can,
and batches for the human what only the human can decide.

Split 2026-09-04 (§15.70): the decision the ticket carried is made — the
lead lives in this repo and this plugin — and the mechanism and the build
are T36 and T37. This ticket is the end-to-end proof only.

Two more things the run must show, added 2026-09-05 after T37's run
(§15.74): kill one project-lead session mid-run and let the lead notice and
resume it, since T37 killed only the lead and `session-launch.md`'s resume
step has not run; and compact the lead by hand once, with `/compact` in its
pane mid-portfolio, so that `PreCompact` on a portfolio and the lead's
re-read after it are proven without a run long enough to compact on its own.

Done when: two concurrent goals run in two project-lead sessions from one
lead session, every escalation reaches the human through the lead, a killed
project lead is resumed by the lead with no human turn, and the lead has
been compacted by hand once and continued from the record. Record what the
run showed in design §15.

Read first: design §15.70, §15.21, §15.22, §1, §4; T36's and T37's §15
entries.

Landed 2026-09-06 as design §15.80. One Fable lead took two goals from one
typed message to draft PRs #21 and #22 on the fixture, in 33 minutes and two
human turns. All four clauses are met: two concurrent project-lead sessions,
one question carried to the human and answered through the lead, a killed
project lead relaunched and resumed with no human turn, and a hand `/compact`
that `PreCompact` logged and the lead read past from the record. The run found
one gap — nothing wakes a lead when a project lead dies, filed as T44 — and
one rule fix, in `skills/lead/SKILL.md`: a batch of one still writes
`lead.escalations` before it sends.

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
`record-format.md` (§15.56). The tickets it implies are T12 below, T31 and
T32.

## T12 — Implement the investigation path

Status: done
Depends on: T4, T11, T31, T32
Stage: after 4

Extend `/crew:project-lead` with design §9.5. Four pieces, in the order a
run meets them:

1. **The choice at "Take the goal".** §9.5 picks the path from the charter,
   before scouting, not at "Choose the shape"'s table. A goal whose acceptance
   criterion cannot be written until something is diagnosed is a symptom.
   That rule already writes that criterion, so this is a branch in an
   existing step, not a new one.
2. **The diagnosis loop.** `Explore` subagents and `crew:researcher` gather
   evidence to files; the project lead reads the paths, never the reading.
   This is `crew:researcher`'s first caller — nothing dispatches it today.
   More than one surviving hypothesis convenes a three-advocate council
   (§6.1, T22 case 2) over one named evidence set.
3. **`diagnosis.md`.** Five headings, in `record-format.md`'s order. A
   diagnosis deliverable holds no package, so the first evidence dispatch is
   what moves it `in-flight`.
4. **The two endings.** `Outcome: fix` rejoins "Choose the shape"'s table with
   the
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
`SKILL.md`'s "Take the goal" and "Choose the shape"; T27, T31, T32.

Landed 2026-09-04 as the path choice in `SKILL.md`'s "Take the goal" and
"Scout", the new
`references/investigation-path.md`, the three council rules in
`autonomy-contract.md`, and `record-format.md`'s `evidence/` directory
(§15.68). The loop got a file of its own, a fix rejoins at "Write the spec", and
`crew-record.py` needed no new command. Both runs the Done when asks for
landed on `jerridan/crew-fixture-string-kit`: a seeded bug reached draft PR
#10 with a test that fails without the fix, and a question about
`encodeQuery` ended `work-complete` with a recorded diagnosis and no PR.

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
- `simple-path.md`'s "End the run" and `full-path.md`'s "Open the draft PR"
  both say to push and open a
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
one deliverable branch, `git switch -c` at "Create the branch". Nothing
switches back. A run
that finishes leaves the checkout on `crew/<goal-slug>/<deliverable-id>`, and
the next person or session in that directory is on a branch it did not choose.

This is not hypothetical. The §15.47 run left the T8 session on the run's
branch, and that session's next two edits landed there before it noticed
(design §15.47). The cost is silent: a commit on the wrong branch looks exactly
like a commit on the right one.

Decide who restores it and when, then write it into the file that owns the
step:

- Record the branch the checkout was on **before** "Create the branch", so the
  run can put
  it back. `record-format.md` owns the field name; `deliverables[].base`
  already records the sha, which is not the same thing as the branch name.
- Say what happens when the tree is dirty at the end, or when the principal
  wants to stay on the deliverable branch to look at it. Switching a checkout
  out from under a person is its own failure.
- Both paths switch the checkout: `simple-path.md`'s "Create the branch" on the
  simple path, and
  `full-path.md`'s "Create the branch and the worktrees" on the full path,
  whose ICs work in worktrees but whose
  project lead does not. The rule's text lives in `simple-path.md`, and `full-path.md`
  points at it twice, rather than carrying a copy.

Done when: a simple-path run ends with the checkout on the branch it started
on, or with a recorded reason why it did not, and a second run in the same
directory starts from a known branch.

2026-09-04: done. `simple-path.md`'s "Create the branch" records
`deliverables[].checkout_branch` and "End the run" switches back;
`deliverables[].checkout_restored` holds `true` or
the reason it did not. `full-path.md` points at those two steps from its own
"Create the branch and the worktrees" and "Open the draft PR". Two simple-path
runs in one fixture checkout proved it:
`~/.claude/crew/truncate-helper-bfa8/` and, from the same directory,
`~/.claude/crew/slugify-stage-3-fa89/`. Both record `checkout_branch: "main"`
and `checkout_restored: true`, and both left the checkout on `main` and clean
(design §15.54). T35's two full-path runs then exercised the full path's
restore, and design §15.71 records them.

Read first: design §9.1, §15.47; `record-format.md` deliverable fields;
`simple-path.md`'s "Create the branch" and "End the run".

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
- Say who runs it. The project lead at integration (`simple-path.md`'s
  "Integrate") is the
  natural owner, because that is where it already edits shared files. An IC
  cannot own it: an IC sees one package's file set, and a claim in `README.md`
  is stale because of a change in `agents/`.
- Decide whether `crew:deliverable-reviewer` gets it as an eighth check
  instead. It already reads the whole diff against the spec, which is the same
  shape of work. One owner, not two.

Done when: a run that lands a stage leaves no file claiming that stage is
unbuilt, and the check is stated in exactly one place.

Read first: design §15.48, §15.49; `writing-standard.md`'s "Keep the status
true"; `simple-path.md`'s "Integrate"; `agents/deliverable-reviewer.md`.

2026-09-04, done. `writing-standard.md`'s "Keep the status true" holds the
vocabulary list and the commands; `simple-path.md`'s "Integrate" runs them;
`crew:deliverable-reviewer` got no eighth check. The terms quoted in the
first bullet above are this ticket's original ask, not a second list —
`writing-standard.md` is the one that counts, and it has grown three terms
since. A run then landed a stage with the sweep on:
`~/.claude/crew/truncate-helper-bfa8/`, a simple-path run on a string-kit
fixture. At "Integrate" the project lead found two stale claims that no IC file
set held — the fixture's `README.md` roadmap row and its `CLAUDE.md` line
about `truncate` — fixed both, and left the still-true `slugify` rows. Design
§15.52 holds the evidence.


## T19 — Probe: `PreCompact` for an in-process teammate

Status: closed, not run
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
entry whose `agent` is that IC's name, as `full-path.md`'s "Verify before you
believe" matches it. Record the payload
shape in design §15.

Read first: design §13.1, §15.50; `hooks/pre-compact.py`;
`full-path.md`'s "Verify before you believe" and "The territory's next
package".

Closed 2026-09-05 without a run. A teammate cannot be told to compact, so
this probe needs an IC to compact on its own, which is the expensive case,
and the hook fails open: if it does not fire, the record misses one log
line and the run is unaffected. Reopen only if a real run shows a
compaction the record cannot explain.

## T20 — Probe: a review agent's write to the record root

Status: done
Depends on: nothing
Stage: any (design §15.50)

`review-output.md` now has every review agent write its report to the path
its dispatch names and return four lines. An IC's record writes are denied
in some dispatch shapes (design §15.26b, §15.31b), and the same may hold for
an unnamed reviewer. The fallback is in place — the whole report returns when
the write is denied — but the saving only lands when the write succeeds.

Done when: one run on each path shows a `reviews/` file written by the
reviewer itself, or the denial is recorded in design §15 with the dispatch
shape that produced it.

2026-09-04: done, as design §15.67. The write is allowed, so there is no
denial to record. Ten runs made 33 review dispatches after the Return path
rule, and every reviewer wrote its own file. Two runs answered this ticket
directly: `~/.claude/crew/add-truncate-and-slugify-9140/` on the simple path
and `~/.claude/crew/add-titlecase-decodequery-b150/` on the full path, the
second holding the first `crew:split-critic` file written under the rule. The
PR also removed every stale copy of the result's shape: `SKILL.md`'s "Have the
spec reviewed", `full-path.md`'s "Review the package", and the `description`
of all four review agents.

Read first: design §15.26, §15.31, §15.50, §15.67; `review-output.md`.

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

2026-09-04: done. `SKILL.md`'s "Sweep for preference questions" sweeps
`charter.md` and `spec.md` before
the split, `autonomy-contract.md` owns the rule under The preference sweep,
`record-format.md` owns the entry, and `crew-record.py` gained `escalation
add` so a batch appends instead of replacing the list. Both runs behaved as
this ticket asks: `~/.claude/crew/slugify-stage-3-fa89/` escalated one seeded
question before the split, and `~/.claude/crew/truncate-helper-bfa8/` found
none and recorded `Answer: none` (design §6.3, §15.53).

Read first: design §6, §6.2, §15.22b, §15.50, §15.53; `autonomy-contract.md`.

## T22 — Redesign the council: one adversary by default, three advocates by exception

Status: done
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

2026-09-04: done. `autonomy-contract.md` and `record-format.md` carry the
three rules, `record-format.md` owns the new `Prior:` field, and
`agents/council-advocate.md` has a two-shape section. The next council ran
the same day: `slugify-helper-d1ad/` framed one adversary against a
medium-confidence `Prior:`, kept the prior on the signature, and dropped its
unknown-key guard on the adversary's evidence. It cost 16,027 tokens against
a three-advocate council's 126,168 to 169,257 (design §6.1, §15.64).
The measurement this ticket asks for needs ten adversary entries, and one
exists. T34 owns it.

Read first: design §6.1, §6.2, §15.43, §15.47, §15.50; `autonomy-contract.md`;
`record-format.md` council entry; `agents/council-advocate.md`; T11, T21.

## T23 — Measure the review layer's catch rate

Status: done
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

Done 2026-09-04: `crew-stats.py` prints a catch-rate table, and §15.57 holds
the numbers. Package reviews act on 4 of 32, and drive 5 of the 17 fix rounds.
Nothing changes: a green acceptance tool does not predict a clean review, and
every escape sits outside one package's diff, where opus in that seat cannot
reach it either.

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

Status: done
Depends on: nothing
Stage: any (design §8, §15.50)

The project lead now runs on Fable 5.1 (T24). Fable's own guidance says
prompts written for prior models are often too prescriptive and reduce
output quality, and that stating the goal and constraints beats enumerating
steps. `SKILL.md` and `simple-path.md` are a fourteen-step numbered loop, and
`full-path.md` a thirteen-step one. The evidence so far cuts the other way: a Fable project lead ran
the numbered loop in 130 turns with zero fix rounds (§15.50). So this is a
measurement, not a rewrite.

Crew's files already sort by reader. The project lead's files are read by
Fable; `ic-contract.md`, the IC and review agents, `review-output.md` and the
advocate are read by sonnet and opus, which do better with explicit steps.
Only the project lead's files are candidates, and no file gets two variants —
a second copy of a rule is the drift `CLAUDE.md` forbids.

Write a goal-and-constraints form of `SKILL.md` and `simple-path.md` that
keeps every rule and every pointer to a reference, under a temporary second
skill name so both forms load. Run one simple-path goal with each, on Fable at high effort, in
fresh clones, with `CREW_RECORD_ROOT` set per arm. Pass `--model fable` on
each launch: the two 2026-09-04 runs under T27 and T28 launched with
`--effort high` and no model flag, and both ran on Opus 5 (§15.58, §15.59),
so a run that omits the flag measures the wrong seat. Compare lead turns, lead
spend from `scripts/spend.py`, decisions, critic rounds, fix rounds and the
independent check of the two PRs.

Done when: design §15 records the comparison and the decision. If the goal
form wins, it replaces `SKILL.md` and the same treatment goes to
`full-path.md` under its own A/B. If it does not, the numbered form stays and
the entry says why.

Read first: design §8, §15.50; `writing-standard.md`; `SKILL.md`;
`simple-path.md`; `full-path.md`; the Fable 5.1 prompting guidance the `claude-api` skill
carries under "Long-running agent recommendations".

Done 2026-09-04: the numbered form stays, and that PR deleted its temporary
skill `skills/project-lead-goal/` before it merged, so nothing in `skills/`
changed. T35 recreated that directory for its own A/B and deleted it again.
Both
arms ran the same goal on the fixture on Fable 5.1 at high effort, in
parallel from separate clones, and both reached an accepted draft PR with one
spec-critic round, zero fix rounds and zero escalations. The goal form spent
$1.05 less in the project lead's own seat and $0.73 more on its subagents,
for arm totals of $6.31 against $6.61. Design §15.69 holds the table, the
length confound the two loaded forms could not remove, and what would decide
the question: the full path, not another simple-path goal.

## T27 — Move the simple-path loop out of `SKILL.md`

Status: done
Depends on: nothing
Stage: any (design §15.25, §15.30a)

`SKILL.md`'s body has sat at the writing standard's 200-line cap since T18
landed. T17, T18 and T21 each paid for a new rule by cutting a sentence that
was not a rule: "A finding is a claim, not a verdict" and "Your own context is
the most expensive place to work" are both gone. The cap is crew's own
(`writing-standard.md` rule 4); Anthropic's skill guidance says under 500
lines, and says that a workflow that grows large moves into its own file
which the skill tells the reader to load by task.

The full path already works this way: `full-path.md` replaces the loop after
the shape
when the shape is more than one package (§15.30a). The simple path has no
such file, so every rule added to the run loop lands in the fullest file.

Do the same for the simple path:

- Add `references/simple-path.md` holding the loop after the shape, the same
  shape as
  `full-path.md`. `SKILL.md` keeps the shared prefix — the reference list,
  the goal, the scouting, the spec, the spec review, the preference sweep and
  the shape table — which then points at one of the
  two path files.
- Integration, the deliverable review and the end of the run are shared
  between the two paths. Keep each in one file and point at it from the other,
  as `full-path.md` already does for the end of the run.
- Put back what the cap cost. Three sentences are in no file the project
  lead reads at runtime: "A finding is a claim, not a verdict" ("Have the spec
  reviewed", the
  heuristic behind the adjudication rule; §15.46 is why it matters), "Your
  own context is the most expensive place to work" (after the shape table;
  design §9.1 and `review-output.md` say it, and neither is the project
  lead's file), and "Your output is the run's most expensive" ("Write the
  spec", the
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

Read first: design §15.25, §15.30a, §15.50; `writing-standard.md` rule 4;
`SKILL.md`; `full-path.md`.

2026-09-04: done. `simple-path.md` holds the loop after the shape,
`SKILL.md`'s body is
96 lines, and the step numbers did not move. The three sentences are back in
"Write the spec", "Have the spec reviewed" and "Choose the shape".
`writing-standard.md` rule 4 now carries a 200-line target,
the 500-line limit and no cap for a reference. A run proved it:
`truncate-stage-2-0722/` read `simple-path.md`, never opened `full-path.md`,
and reached draft PR 2 on the fixture repo with zero prompts, zero fix rounds
and $6.27 at list price (design §15.59).

## T28 — Give `run.completed_at` an owner

Status: done
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

Status: done
Depends on: nothing
Stage: any (design §6, §15.52, §15.53)

Both 2026-09-04 runs under T21 ran the whole loop, then escalated at "End the
run":
the fixture had no git remote, so the push and `gh pr create` could not run.
That was knowable at "Take the goal" from one `git -C <repo> remote` call. A
run with a
preference question and no remote interrupts the principal twice, which is
what T21's batch exists to prevent; a run with no preference question spends
its whole budget before it asks whether a PR is possible at all.

Add "can this run push and open a draft PR" to the checks that run before the
preference batch. `full-path.md`'s "Check the launch conditions" owns the
launch checks and T21's rule
in `autonomy-contract.md` already folds them into the batch; add the remote
check beside them, so it applies on both paths. The question to the principal
offers the same three ends "End the run" offers today: add a remote, keep the
work
local as `work-complete`, or stop. An answer given at the start is recorded
once and "End the run" never asks again.

Done when: a run on a checkout with no remote asks about the PR in the same
batch as its preference questions, before the split, and "End the run" ends the
run
without a second ask.

Read first: design §15.52, §15.53; `autonomy-contract.md` "The preference
sweep"; `full-path.md`'s "Check the launch conditions"; `simple-path.md`'s "End
the run".

## T30 — Write a preference answer into the target repo as precedent

Status: done
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

Status: done
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

Landed 2026-09-04 as `agents/council-advocate.md`'s third shape and its
concession report, plus `record-format.md`'s `conceded` line on `Losing:` and
`autonomy-contract.md`'s concession exception to the rebuttal rule (§15.66).
Two hand-dispatched advocates over a seeded bug proved both halves. The
citation clause passed with one exception: the arguing advocate cited a line
in an evidence file's own subject that no evidence line points at (§15.66d).

## T32 — Prove the reproduction fails before the fix

Status: done
Depends on: nothing
Stage: any (design §7, §9.5)

Design §9.5 makes the reproduction the fix package's acceptance criterion,
and it requires two clauses: the test fails now, and it passes after. Crew
checks only the second. `simple-path.md`'s "Verify before you believe" runs the
acceptance criterion after
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
`simple-path.md`'s "Dispatch the IC" and "Verify before you believe";
`record-format.md` `acceptance_criterion`.

Landed 2026-09-04 as design §7's fourth row, `ic-contract.md`'s "Write the
failing test first", the red-commit check in both path files, and
`record-format.md`'s `reports/` entry (§15.61). The IC owns the red commit.

## T33 — Give a bounded edit a package entry, or take `split.md` out of its path

Status: done
Depends on: nothing
Stage: any (design §9.1, §15.59)

`SKILL.md`'s shape table sends a bounded edit to `simple-path.md`'s "Create
the branch", then to "Integrate", "Review the deliverable" and "End the run".
No `split.md` is written and no `packages[]` entry exists, yet "Integrate"
marks a package `integrated` and "Review the deliverable" hands `split.md`
to the deliverable reviewer. Nothing has run this row; the gap was found by
T27's code review, which left it because fixing it changes what a bounded
edit does.

Decide which of the two is right, and make the other file agree. Either a
bounded edit writes a one-package `split.md` and its `packages[]` entry
before the branch, so "Integrate" and "Review the deliverable" hold as
written, or the row skips "Integrate" and "Review the deliverable" takes a
bounded edit with no `split.md`. `record-format.md` owns
what the entry and the review need; design §9.1 owns what a bounded edit is.

Done when: a bounded-edit run reaches a draft PR with zero prompts, every
field "Integrate", "Review the deliverable" and "End the run" write exists in
its record, and the row and the rules it
names agree.

Read first: design §9.1, §15.59; `SKILL.md` shape table;
`simple-path.md`'s "Create the branch", "Integrate", "Review the
deliverable" and "End the run"; `record-format.md` `split.md` and `packages[]`.

## T34 — Decide whether the adversary earns its dispatch

Status: open
Depends on: T22
Stage: any (design §6.1, §15.64)

T22 made one adversary the default council and design §6.1 put it on
probation: after ten adversary entries exist, compare each `Prior:` with its
`Answer:`. Nothing carries that trigger today. `crew-stats.py` counts a
`Route: council` entry but reads neither `Prior:` nor whether the entry held
one advocate or three, so the tenth entry can land with nobody watching.

Two pieces:

1. **Count them.** `crew-stats.py` gains a council column that reads `Prior:`
   and `Models:` over every record, and reports adversary entries, how many
   kept their prior whole, how many changed it in part, and how many the
   advocate overturned. §15.64d is entry one: prior kept, guard dropped, so a
   two-state count is not enough.
2. **Decide with the numbers.** An adversary that never moved an answer is
   cut, and §6.1's default becomes an inline answer with a citation, leaving
   only the two three-advocate cases. An adversary that moved answers stays,
   and the probation clause comes out of §6.1.

Done when: ten adversary entries are counted, and design §15 holds the
decision the numbers support.

Read first: design §6.1, §15.64; `autonomy-contract.md` Council;
`record-format.md` council entry; `skills/project-lead/scripts/crew-stats.py`.

Part 1 landed 2026-09-04: `crew-stats.py` reads `Prior:`, `Positions:` and
`Answer:` on every council entry and reports each one-advocate entry as
kept whole, changed in part, or overturned (§15.65). Part 2 does not: the
record root holds zero adversary entries the script can count today, ten
short of the threshold, so no decision follows from the numbers yet. Status
stays open until a run adds enough entries to count.

## T35 — A/B the goal-and-constraints form on the full path, and retire the step numbers

Status: done
Depends on: nothing
Stage: any (design §15.69)

T26 ran the goal-and-constraints form against the numbered form on one
simple-path goal. The two arms could not be separated: both reached an
accepted draft PR with one spec-critic round, zero fix rounds and zero
escalations, and the arm totals were 4.5% apart. The numbered form stays
(§15.69). Two things kept that run from answering the question.

The goal was too easy. The project lead's judgment was never the bottleneck,
so the form it reads could not show. §15.50 hit the same wall with its first
goal, and only the full-path goal separated Opus from Fable.

The variant had to carry scaffolding. Both forms were loaded at once, so the
goal form spent about 350 words saying where the shared references live and
mapping every cited step number to the rule that owns it. Gross, it was 22%
longer than the form it was measured against; net, about 5%. A result that
turns on length is not a result about form.

So: run the same A/B on a full-path goal, with the losing form deletable.
Retire the step numbers in the same change instead of mapping them.
`record-format.md`, `full-path.md`, `investigation-path.md`,
`autonomy-contract.md` and `writing-standard.md` cite `SKILL.md` and
`simple-path.md` by step number in more than twenty places, `docs/tickets.md`
in fifteen more, and `investigation-path.md` is the one an investigation run
reads at runtime. Each citation becomes the name of the rule it means.

Done when: design §15 records the full-path comparison and the decision, no
file cites a project-lead step by number, and only one form of the project
lead is left in `skills/`.

Read first: design §8, §15.50, §15.69; `writing-standard.md`; `SKILL.md`;
`simple-path.md`; `full-path.md`; `investigation-path.md`; the Fable 5.1
prompting guidance the `claude-api` skill carries under "Long-running agent
recommendations".

2026-09-05: done. **The goal-and-constraints form is now the project lead**,
and the numbered form is deleted. The step numbers came out of every citation
first, in their own commit, so both arms answered the same pointers and the
variant carried no step map — 4.6% longer than the control, against T26's
22%. Both arms then ran one full-path goal on the fixture: four helpers
across `src/text/` and `src/url/`, `Favour: time`, two territories, two IC
teammates, zero fix rounds and zero escalations each. The goal form cost
$10.70 against $11.98, saved $1.42 in the project lead's own seat, and
finished fifteen seconds apart on twenty-nine minutes. It also shipped the
better artefact: the numbered arm's `parseQuery` silently drops a `__proto__`
pair, and its own spec critic had raised the case — the numbered lead
narrowed the requirement to exclude the key, while the goal-form lead's
deliverable reviewer produced the counter-example and the lead fixed the
code. Design §15.71 holds the table, the one deviation the goal form bought
(it read an eleven-file repo itself instead of dispatching `Explore`), and
what the run does not prove.

## T36 — Probe: one session drives another

Status: done
Depends on: nothing
Stage: 7 (design §15.21, §15.22c, §15.70)

The lead tier stands on two things no crew run has exercised: a session
launching a project-lead session by rule, and the two talking by
cross-session message. Prove both before anything is built on them.

From one interactive session, launch a second `claude` session under
§15.22c's three rules — interactive, outside any worktree, with its
permissions pre-approved — for example with `tmux new-window`. Then:

- Find it with `ListAgents` and send it a charter path by `SendMessage`. It
  must start `/crew:project-lead <charter path>` on that message alone.
- Have the charter carry a seeded preference question. The project lead's
  sweep (`autonomy-contract.md`) must send the escalation to the session
  that handed it the goal, not to the human in its own pane, and the first
  session must receive it, answer it by message, and see the run continue.
- Kill the first session mid-run and confirm the record, not the message
  channel, is what the run stands on (§15.21: a lost message costs latency,
  never correctness).

Record in design §15 what fired, what did not, the exact launch command and
env that worked, and the message shapes both directions. If `SendMessage`
cannot reach a session that is mid-turn, or the escalation cannot name a
session as its principal, say so: that decides T37's design.

Done when: a charter sent by message starts a run, an escalation comes back
by message and its answer unblocks the run, and design §15 holds the payloads.

Read first: design §15.21, §15.22, §15.70, §6.2; `autonomy-contract.md`
escalation section; `record-format.md` `escalations`.

Landed 2026-09-05 as design §15.72, `autonomy-contract.md`'s "Reach the
principal the way the goal arrived" and its send step for every trigger,
`record-format.md`'s `run.principal`, and `SKILL.md`'s note on who handed the
goal over. Both directions fired: a charter sent by message started a run with
nothing typed in that session's pane, and the escalation came back by message
in under two seconds. The kill test held — the run finished on the record after
its principal died, and only the closing report was lost. Two things the probe
found that the design did not have: a launch into an untrusted directory blocks
on the folder-trust dialog before the session can register, which §15.22c does
not cover, and mid-turn delivery is still untested. Both go to T37.

## T37 — Build the lead skill

Status: done
Depends on: T36
Stage: 7 (design §1, §15.70)

Build `/crew:lead` in this plugin: a session that holds a portfolio of
goals and drives one project-lead session per goal. Four pieces:

1. **The portfolio record.** One directory per lead session under the record
   root, listing each goal, its charter path, its project-lead record and
   session id, and its state. `record-format.md` owns it, in the same style
   as `state.json`.
2. **Charters.** The lead writes `charter.md` for each goal from the
   principal's brief, in the shape `record-format.md` already defines, and
   hands the path by message (§15.22a).
3. **Spawning and steering.** One project-lead session per goal, launched
   the way T36 proved, with `--resume` on a dead one. The lead reads records,
   never transcripts.
4. **Escalations.** The lead answers what its charters and the records
   settle, and batches for the human what only the human can decide, in one
   message per batch (§15.22b). The human is the lead's principal, so
   `autonomy-contract.md`'s ladder gains its top rung without a second copy
   of the rules.
5. **The ledger.** The principal keeps one lead session open all day and
   does most of their interfacing through it, so the lead's context will be
   compacted or cleared many times. The portfolio record is the ledger and
   the context is a cache of it. Three rules: every turn ends with the
   record updated, including one line per goal or task that says what the
   lead expects next; `/crew:lead` starts from the record, not from memory,
   whether fresh, after `/clear` or after a compaction, so it reads the
   portfolio, calls `ListAgents` to see which project-lead sessions are
   alive, resumes the dead ones and re-sends any open escalation; and every
   answer or preference the principal gives lands in the portfolio's
   decisions file, so a resumed lead never asks twice. `hooks/pre-compact.py`
   logs a compaction into the portfolio the way it does into a run. Keep the
   lead's skill short, because it is re-read after every compaction.

The bare word `lead` has meant this tier since §15.19; the skill and its
files take that name. `CLAUDE.md`'s hierarchy line and README's status table
change with it. Whatever T36 found impossible, design around here and say so
in §15.

Done when: one goal runs from brief to draft PR through the lead with no
human turn except the batch it sends, and the portfolio record shows it; and
a lead killed mid-portfolio and started again continues from the record with
no human turn.

Read first: design §15.70, §15.21, §15.22, §1, §4, §6.2; T36's §15 entry;
`record-format.md`; `autonomy-contract.md`. T39 adds the triage step
that sends a small task to one IC instead of a project-lead session; design
the portfolio record so a task-shaped run fits it.

Landed 2026-09-05. `/crew:lead` is `skills/lead/SKILL.md` with one reference,
`session-launch.md`, and one script, `crew-portfolio.py`. It is written in the
goal-and-constraints form (§15.71) and runs at `fable`, high effort.
`record-format.md` owns the portfolio record — `portfolio.json`,
`decisions.md`, `charters/` and `runs/<item-id>/` — and every item carries a
`kind` of `goal` or `task`, so T39's task-shaped run needs no new shape.
`autonomy-contract.md` gained the top rung and no second copy of the ladder.
Both hooks reach the portfolio: `SessionEnd` marks a dead lead `interrupted`,
`PreCompact` appends to `lead.compactions`. `CLAUDE.md`'s hierarchy line,
README's status, roles and model tables, and design §1 and §15.22 all say the
tier is built. §15.74 records the six design calls, the trust-dialog fix
§15.72a left open among them.

Both "Done when" clauses are met. A live run on 2026-09-05 took a one-line
brief to fixture draft PR #17 through a project-lead session the lead launched
itself, and a lead killed mid-portfolio started again from the record and asked
nothing. Four human turns: the brief, the batch answer, a bare `/crew:lead`
after the kill, and one word answering a budget escalation. Neither lead read
or edited a file in the target repo. §15.74g to §15.74l record the run.

Two things it left open. The trust dialog for the lead's **own** working
directory comes back on every launch from it, which the lead's check does not
cover (§15.74j). And `Budget: 10` fired twice on a $13.75 run whose fable seat
was $12.29, with the lead's estimate of the remaining spend wrong by a factor
of ten (§15.74k) — a lead cannot price the tail of a run it is not in.
`PreCompact`'s half of the ledger is unexercised: neither lead compacted.

## T38 — Take the bounded edit away from the project lead

Status: done
Depends on: nothing
Stage: any (design §9.1, §15.60, §15.68m)

Design §9.1's shape table has one row where the project lead does work
itself: a bounded edit of one or two tool calls. Every other row dispatches.
The principal's rule for the hierarchy is that a lead of any tier does not
work — it triages, dispatches, reads the record and answers questions — and
a lead that is editing code is a lead that is busy, and expensive at its own
seat. §15.68m shows the row in use: a diagnosed fix on the investigation path
read as bounded, the project lead made the edit, and no package review ran.

Remove the row. A bounded edit is one package on the simple path, dispatched
to one unnamed IC at the `light` band, with the package review it now skips.
The `light` band already exists for exactly this size of work
(`band-rubric.md`). The three exceptions `simple-path.md` carries for a
bounded edit — in "Write the split", "Create the branch" and "Review the
deliverable" — come out with it, and so does the exemption
`investigation-path.md`'s `Outcome: fix` ending names. Design §9.1 loses the
row and the sentence "The project lead does work itself only for bounded
edits"; the paragraph after it, on the cost of the project lead's own
context, is the reason and stays.

Keep the shared-file pass. Integration edits — the barrel file, a version in
two places, an instruction file's status line — stay with the project lead
(§9.3, `record-format.md`). Those are not the bounded edit; they are the seam
no package owns.

Done when: no file in `skills/` sends the project lead to edit a file in the
target repo outside integration, a one-line goal reaches a draft PR through
one `light` IC with a package review, and design §15 records the cost of
that dispatch against the bounded edit it replaced.

Read first: design §9.1, §9.3, §15.60, §15.68m; `SKILL.md` "Choose the
shape"; `simple-path.md`; `band-rubric.md`; `investigation-path.md`
"Ending one".

Landed 2026-09-05. Design §9.1 lost the row and the sentence, and §3 now names
integration and the fix-round breaker as the project lead's only edits.
`SKILL.md`'s shape table is two rows, `simple-path.md` lost all three
exceptions, `investigation-path.md`'s `Outcome: fix` ending now forbids the
edit, `band-rubric.md` bands a small package like any other,
`record-format.md` gives every package an IC, and
`agents/deliverable-reviewer.md` no longer expects a package with no review
(§15.73). §15.60 is marked superseded. `crew-stats.py` needed no change: it
counted no bounded-edit field.

All three "Done when" clauses are met. A live run on 2026-09-05 took a
one-line goal to a draft PR through one `light` IC with a package review, no
prompt and no escalation, and the project lead's transcript holds no `Edit` or
`Write` call at all. §15.73a records the run and its cost: the IC and the
package review together cost under $0.45 of $7.69, and the project lead's own
seat is 82 percent of the run.

The fix-round breaker still lets the project lead edit at the five-round cap.
That is design §10's rule, out of this ticket's scope, and every file that
states the prohibition now names it as the exception (§15.73b).

## T39 — The lead triages by size: a task gets one IC, a goal gets a project lead

Status: done
Depends on: T37
Stage: 7 (design §1, §15.70, §15.72)

T37 builds a lead that spawns one project-lead session per goal. Handed a
small task — rename a flag, fix a typo in a doc, add one test — that shape
engages the whole crew: a Fable project-lead session, a spec, a critic, an IC
and two reviews, for work one Sonnet agent finishes in a minute. The
principal wants to hand any size of work to the lead and trust it is taken
care of, without paying for a project lead it does not need.

Give the lead a triage step before it dispatches anything. Two outcomes:

- **A goal** — work that needs a spec, or more than one package, or a
  judgment call the charter leaves open — gets a charter and its own
  project-lead session, as T37 builds.
- **A task** — one package, one file set, a criterion the lead can write in
  one line — gets one unnamed IC, dispatched by the lead itself as a
  background subagent at `band-rubric.md`'s `light` or `standard` band, in
  a fresh clone or branch of the target repo, followed by the same verify
  step and package review the simple path runs. The record is a minimal
  one under the lead's portfolio: charter, the package entry, the report,
  the review, the PR.

Two rules hold on both outcomes. The lead never reads code and never edits
a file in a target repo: triage is done from the task text, the repo's
instruction files and the record, and a task the lead cannot size from
those is a goal. And every turn of the lead ends quickly — dispatch, then
end the turn — because a message reaches a session only when it is idle
(§15.72i), and a lead that is mid-turn cannot be handed the next task.

Write the sizing test into the lead's skill, with the reasons a task is
promoted to a goal. `autonomy-contract.md` owns what a task-shaped run may
escalate; `record-format.md` owns the minimal record.

Done when: a one-line task handed to the lead by message reaches a draft PR
through one IC and no project-lead session, a goal handed the same way
reaches one through a project-lead session, the lead's portfolio record
shows both, and neither run had the lead read or edit a file in the target
repo.

Read first: design §1, §9.1, §15.70, §15.72; T37 and its §15 entry; T38;
`band-rubric.md`; `record-format.md`; `autonomy-contract.md`.

Landed 2026-09-05. `skills/lead/SKILL.md` gains two sections: "Triage every
item by size" — the four-question sizing test, the five promotion reasons, and
the rule that an answer needing the code read is a "no" — and "A task runs
under you", six steps of one turn each. The task steps point at
`simple-path.md` for the dispatch, the verify step, the package review and the
fix rounds, and copy none of them. "You never touch a target repo" keeps no
`Read`, `Edit` or `Write` in any checkout, and carries two carve-outs:
read-only git anywhere, and `git`, the criterion, the suite and `gh` in a
task's own worktree.
`autonomy-contract.md` owns what a task escalates — three things, against
promotion for every question about what the work is — and `record-format.md`
owns the minimal record: the `task` object's twelve fields, the four
subdirectories under `runs/<item-id>/`, a triage entry in the portfolio's
`decisions.md`, and a `done` proved by an accepted review and a PR url.
`crew-portfolio.py`'s `item set` takes a dotted field, so one call writes one
`task` field. §15.79 records the six design calls.

Every "Done when" clause is met. A live run on 2026-09-06 handed one lead a
one-line task and a goal as two typed messages. The task reached fixture draft
PR #19 through one IC and one package review with no project-lead session, in
9 minutes 26 seconds; the goal reached PR #20 through a session the lead
launched itself; the portfolio shows both kinds, with a `task` object and no
`state.json` on one and a full goal record on the other; and the lead made
zero `Read`, `Edit` or `Write` calls in either checkout. Its own seat was 46.7
percent of the $11.97 run, against 82 percent for a project lead on a one-line
change (§15.73a). §15.79g to §15.79j record the run.

It changed one rule. The two items shared a repo path, so the lead's read-only
`git status` and `branch --show-current` checks landed in "the goal's
checkout", which the first draft banned. Read-only git reports git's own state
and not the code, so it is now allowed in any item's checkout, and every
write, every test run and `gh` stay inside a task's own worktree (§15.79h).

Two things the run leaves open. The task's IC did not re-export the new helper
from the barrel file, because a barrel is shared: the lead flagged it in the
PR body as follow-up, so a task that adds a helper to this fixture leaves a
human that last edit (§15.79i). And "End every turn quickly" is still
unexercised — the task ran inside one long turn, and no message arrived
mid-turn to be delayed (§15.72i, §15.79j).

Superseded in part by T51, filed 2026-09-11. The sizing test and the
task loop move out of the lead: the project lead sizes the work after it
scouts the repo, and a small item runs on a light path inside its own
project-lead session. The lead keeps one shape for every item.

## T40 — Probe: launch a project-lead session as a native iTerm2 tab

Status: done
Depends on: T37
Stage: 7 (design §15.22c, §15.72)
Priority: low

`session-launch.md` opens every project-lead session with `tmux new-window`,
so the principal watches the crew through tmux. iTerm2 users get the same
view today through `tmux -CC`, which shows each tmux window as a native tab.
This probe asks whether the lead can skip tmux and open the tab itself
through iTerm2's Python API, so a principal who lives in iTerm2 never
starts a tmux server.

Find out four things:

1. Whether a session started from an iTerm2 Python API script registers
   with `ListAgents` under its `--name`, the same as one started by tmux.
2. Whether the four launch rules in `session-launch.md` hold unchanged, in
   particular the folder-trust rule.
3. What a full-path project lead in that tab does for its IC teammates: the
   teammate display mode it picks, and whether split panes read an agent
   definition as design §15.20d describes.
4. What the lead needs to kill or resume a tab, since `tmux kill-window` and
   the window name no longer apply.

If it works, `session-launch.md` gains one alternative launch block behind a
setting, and nothing else changes: the launch command is one rule in one
file. If it does not, record why in §15 and close.

Done when: one goal reaches a draft PR through a project lead launched as an
iTerm2 tab, or §15 says why it cannot.

Read first: design §15.22c, §15.72, §15.20d, §15.21; `session-launch.md`;
the iTerm2 Python API documentation on creating tabs and running commands.

It works. Design §15.89 holds the run and the four answers.
`session-launch.md` carries the alternative launch behind `CREW_LAUNCH=iterm2`.
§15.89e supersedes §15.20d's split-pane claim on Claude Code 2.1.268: both
display modes append the agent definition to the default system prompt.

## T41 — Push a batch to the principal

Status: done
Depends on: T37
Stage: 7 (design §15.74)

T37's run left a batch of questions in the lead's pane for over an hour and
a budget question for two, because nobody was watching the pane. The
principal's intent is to hand work to the lead and walk away, so the lead
must reach them when it has a question, not wait to be looked at.

When the lead sends a batch, it also sends one `PushNotification` naming the
portfolio, the item and the number of questions, and saying the answer goes
in the lead's pane. The pane stays the only channel for the answer. The lead
never sends a cross-session message to a session the principal is working
in: a question that lands inside someone else's session is an interruption
the principal did not ask for, and the principal has said so.

The record already holds the ask (`lead.escalations`), so this is the
delivery step only. `autonomy-contract.md` owns the rule; `skills/lead/`
carries the mechanism.

Done when: a batch from a live lead arrives as a push notification, the
answer typed in the pane clears it, and no other session received anything.

Read first: design §15.74; `skills/lead/SKILL.md` "Answer what you can";
`autonomy-contract.md`.

## T42 — Review effort in proportion to the band

Status: done
Depends on: nothing
Stage: any (design §15.73, §15.74)

T38's run took a one-line `light` package through two spec-critic rounds, a
plan gate and two reviews for $7.69, and T37's took `truncate` at `standard`
through the same for $13.75. In both, the project lead's own seat was over
80 percent of the cost, and most of those turns were ceremony around a small
dispatch, not the dispatch. The IC and its package review were under $0.50.

Decide from the record which steps a `light` package skips. Candidates: the
spec critic (the charter's criterion is the spec), the plan gate, and the
deliverable review when the package review already accepted the only
package. Keep the package review: it is the check the bounded edit used to
skip (§15.73). Write the rule into `band-rubric.md`, which owns what a band
gets, and make the path files read it.

Then measure. `crew-stats.py`'s catch rate (T23) is the number that says
whether a skipped step was catching anything. Compare runs before and after
over the fixture, and record the figures in §15.

Done when: a `light` package runs with the reduced set, the record shows
which steps ran, and §15 holds the cost and the catch rate against the full
set.

Read first: design §15.73, §15.74, §15.23 (catch rate); `band-rubric.md`;
`simple-path.md`; `crew-stats.py`.

## T43 — Count the lead's own cost, and remove the budget

Status: done
Depends on: T37
Stage: 7 (design §8, §15.50, §15.74k)

Two things about spend, both from T37's run.

**The lead is not priced.** `spend.py` prices a goal record from the
transcripts of the sessions that ran from its checkout. The lead runs from
no checkout and has no `state.json`, so nothing prices it, and the tier's
overhead is unknown. Give the portfolio a `lead.spend` field in the shape of
`spend.transcript`, priced from the lead's own session transcripts by
`spend.py` or a sibling, written when an item closes. `record-format.md`
owns the field; `crew-stats.py` reports it.

**The budget goes.** The charter's `Budget:` line is the last piece of the
token-ceiling design §15.50 removed. The principal decided on 2026-09-05 to
remove it: the loops that could run away are already bounded by the
fix-round cap, the nudge cap and one-band promotion; the list-price figure
is not what the principal pays, and the subscription limit fires first when
spend matters (§15.50); the lead has no basis to set a figure, and the one
time the gate fired (T37) it cost two interruptions for a $3.75 overrun on a
run one push from done. Spend stays measured and logged, because that is
what makes the band rubric a measurement, and the closing report states the
run's spend. Nothing stops a run on cost.

Remove: `Budget:` from `record-format.md`'s charter shape and `spend.budget`
from `state.json`; trigger 5 from `autonomy-contract.md`'s escalation list
and its "Trigger 5 is the budget" paragraph; the headroom rule T37 added to
`skills/lead/SKILL.md` ("The brief's budget figure is a ceiling") and the
budget line in its charter rule; the README sentence on an exceeded budget;
and design §8's "A charter may name a budget in dollars. Exceeding it
escalates." Mark §15.51's "gives a charter `Budget:` a number to start from"
and §15.74k as superseded. A brief that names a dollar figure is a
preference the lead records in `decisions.md` and reports against; it is not
a charter line.

Done when: no file in `skills/`, `agents/` or `README.md` names a budget, a
closed portfolio item shows the lead's spend beside the run's, and
`crew-stats.py` prints both.

Read first: design §8, §15.50, §15.51, §15.74k; `autonomy-contract.md`
"Spend"; `record-format.md`; `skills/lead/SKILL.md` "One charter per item";
`spend.py`; `crew-stats.py`.

Done in PR #56, plugin 0.1.50, design §15.76. A live lead ran two items to
`closed` on 2026-09-06 and wrote `lead.spend` from inside its own turn each
time an item closed: lead $5.59 against runs $6.38, a 46.7% lead share, no
`double counted` line, and the goal run closed with no budget escalation and
no `spend.budget` key.

## T44 — Wake the lead when a project lead dies

Status: done
Depends on: T9
Stage: 7 (design §15.80e)

`SessionEnd` marks a dead run `interrupted` in its `state.json` and tells
nobody. The lead learns of the death on its next turn, and an idle lead has
no next turn until some other session sends it one. T9's run showed the cost:
a project lead died at about 04:23 and the lead noticed at 04:33, when an
unrelated goal reported. A portfolio whose other items are slow, or whose only
item is the dead one, waits for the human instead.

Make the hook send. `SessionEnd` already reads the run's record; the portfolio
above it holds the item's `session_name` and the lead's own session id. Decide
what carries the message — a cross-session message from the hook, or a field
the lead polls — and where the rule lives. A hook that messages must still
fail open: this hook runs in every session on the machine, and a send that
hangs or errors changes nothing (design §13.1).

Done when: a project-lead session killed mid-run gives the lead a turn within
seconds, the lead resumes it from that turn, and no other session is needed to
wake it. Record what the run showed in design §15.

Read first: design §15.80e, §15.21, §15.38, §13.1; `hooks/session-end.py`;
`skills/lead/references/session-launch.md` "Resuming a dead one".

Landed 2026-09-06 as the send in `hooks/session-end.py`, the wake paragraph in
`session-launch.md`, and design §15.84. The hook writes one JSON line on every
cross-session inbox socket, and the lead's session id inside the line is what
makes the other sessions drop it. A seeded record at `~/.claude/crew-t44/` and
four fake receivers prove the path selection and the fail-open rules. The live
kill ran the same day: the lead's next turn started under one second after the
kill, and it relaunched and resumed the run 54 seconds later with no human
turn.

## T45 — Integration defects from the 2026-09-05 batch

Status: done
Depends on: T39, T42, T43
Stage: any (design §15.81)

Four sessions landed T39, T42 and T43 in parallel on 2026-09-05 and
2026-09-06. Each PR was correct on its own. A high-effort review of the
merged tree then found six defects that only appear where two of those
changes meet. Fix all six.

1. `crew-record.py`'s `set_dotted` still walks with `setdefault`, while
   `crew-portfolio.py` got null and not-a-dict guards. `run set
   steps_skipped.0.reason` raises an `AttributeError` and `run set
   principal.name` over a `null` raises a `TypeError`.
2. `record-format.md`'s task example sets `band: light` with a
   `plan_approved_at` timestamp and no `steps_skipped`, against its own rule
   that a light task skips the gate.
3. `crew-stats.py`'s `runs/*/*/state.json` glob matches a task's worktree at
   `runs/<item-id>/checkout/`, so a target repo's own `state.json` reads as a
   run.
4. The "Steps skipped by rule" table reads run records only, so a task's
   `items[].task.steps_skipped` has no consumer.
5. `record-format.md`'s name inventory for `items[].task` omits
   `steps_skipped`.
6. `skills/lead/SKILL.md`'s two ways to read the default branch return
   different refs, `origin/main` and `main`, so the fallback branches a task
   off stale local code.

Done when: both tracebacks exit with a message against a seeded record, the
phantom run is skipped and a task's skips reach the table against a seeded
portfolio, and one rule states the default branch as one ref.

Read first: design §15.76, §15.77, §15.79; `record-format.md` "The portfolio
record"; `crew-record.py`; `crew-stats.py`; `skills/lead/SKILL.md` "A task
runs under you".

Done in PR #58, plugin 0.1.55, design §15.81.

## T46 — Count a task's package review in the stats

Status: done
Depends on: T45
Stage: any (design §15.79, §15.81)

A task the lead runs itself ends with one package review, and the verdict
lands in `items[].task.review_verdict`. `crew-stats.py` reads reviews from
run records only, so a portfolio of tasks reports its skipped steps (T45) and
none of its reviews. The catch rate (T23) misses every task.

Make the "Package reviews by band" table and the catch rate read a task's
review file under `runs/<item-id>/reviews/` and its `review_verdict`, the
same fold T45 made for `steps_skipped`. `record-format.md` gains the consumer
in its name inventory.

Done when: a seeded portfolio with one task shows that review in the table
and in the catch rate, and a live task's review counts.

Read first: design §15.79, §15.81, §15.57 (the catch-rate method);
`crew-stats.py`; `record-format.md` "The task record".

Superseded in part by T51, filed 2026-09-11. Once every item is a run
record, a task's review is a run's review and the twin code path in
`crew-stats.py` comes out.

## T47 — Probe: a message reaches a lead mid-task

Status: done
Depends on: T39
Stage: 7 (design §15.72i, §15.79j, §15.85)

`skills/lead/SKILL.md` says every lead turn ends quickly, so that the next
item can reach it: a message is delivered only when a session is idle
(§15.72i). A task the lead runs itself breaks that shape. In both task runs
so far the lead stayed in one turn for the whole task, about nine minutes,
because the IC's completion re-woke the same turn. Nothing has sent a lead a
message during that turn, so nobody knows whether the second item waits,
lands late, or is lost.

Run the probe. Hand the lead a task, and while its IC is running hand it a
second item by a typed message and by a cross-session message. Record when
each arrives and what the lead does with it. If a message is lost or waits
for the whole task, decide whether a task must run as one turn per step (the
dispatch, then the verify, then the review), and change the rule in
`skills/lead/SKILL.md` "A task runs under you".

Done when: design §15 holds what a mid-task message did, and the turn rule in
`skills/lead/SKILL.md` matches what the probe showed.

Read first: design §15.72i, §15.79j, §15.80; `skills/lead/SKILL.md` "A task
runs under you"; `session-launch.md` "Steering a live session".

The probe found no turn rule to change. The nine-minute turn did not come
back: the lead ended its turn at the dispatch, so the typed message reached
an idle lead at once. The cross-session message did arrive inside a running
turn, and the lead read it on its next tool round (§15.85).

Done in PR #63, no version bump, design §15.85.

## T48 — A task may edit a registration line in a shared file

Status: done
Depends on: T39
Stage: 7 (design §15.79i; the rule and its run are §15.83)

The lead's triage promotes any item that must change a shared file — a
barrel, a manifest, a lockfile — to a goal. That rule comes from the full
path, where ICs work in parallel worktrees and a file two of them edit is a
merge conflict. A task has one IC on one branch and nobody else writing, so
the conflict cannot occur. The cost showed in both stripSuffix runs: the IC
shipped a helper the fixture cannot import, because the repo's own
`CLAUDE.md` says to add every helper to `src/index.js` and the task left it
out, then asked a human for the line (§15.79i).

Change the rule. A task's file set may include a shared file when the repo's
instruction file names it as where a new thing is registered and the edit is
one mechanical line. The lead reads that instruction file at triage already,
so it puts the file in the set without reading code. What still promotes: a
rule change in an instruction file, README prose that states a policy, more
than one independent file set, and anything the lead cannot size from the
task text and the instruction files. `skills/lead/SKILL.md` "Triage every
item by size" owns the test; `record-format.md`'s `file_set` field says a
shared file may appear there.

Done when: a task that adds a helper to the fixture lands its `src/index.js`
export in the same PR, the record shows the barrel in `file_set`, and no
follow-up is asked of the human.

Read first: design §15.79i, §15.79; `skills/lead/SKILL.md` "Triage every
item by size" and "You never touch a target repo"; `record-format.md` "The
task record"; `ic-contract.md`.

Superseded in part by T51, filed 2026-09-11. The registration-line
exception moves from the lead's triage to the project lead's light path.
The reviewer rule (every shared file named by path, `[Critical]` only
when the file set does not name it) stays as it is.

## T49 — A goal may carry gates between its stages, set by the principal

Status: done
Depends on: T39, T41
Stage: 7 (design §1, §15.74, §15.80)

A goal can already land as several PRs: one project lead, one spec, several
deliverables in dependency order. What a run cannot do is wait for the world
to move between them. A bug fix that needs one PR merged and deployed, a
backfill run to completion, and then a second PR that assumes the backfill,
has gates the run cannot see past. The principal drove one such fix by hand
in the week of 2026-09-01: merge, deploy, watch the deploy land, watch the
Datadog monitors, then start the next PR.

Let a gate exist, and keep the decision with the principal. Three rules:

- A gate is opt-in. With no gate stated, a goal runs as it does today. The
  lead never adds one on its own, and never skips one it was given.
- The lead flags, the principal decides. At intake, when a goal looks like
  more than one PR, or names a migration or a backfill, the lead says so in
  its batch and asks whether the principal wants a gate between the stages.
  The answer, typed in the pane, states each gate: the deploy landing, the
  monitors to watch, the bake window.
- A gate is a written instruction applied between stages. After each PR the
  lead holds, watches what the principal named, reports what it saw as one
  push, and waits for the principal's go before the next stage starts. A
  merge to the target repo stays the principal's step.

Design questions the ticket must settle, in `docs/design.md` first: whether
a gated goal is one portfolio item with stages or one item per stage with a
dependency between items; what an item waiting on a gate is called in
`portfolio.json` (a new state beside `blocked`, or `blocked` with a reason);
how the lead reads deploy and monitor state, which sit outside every
checkout, and whether each source is an `Instruments:` line in the charter
(design §6.4) or a new field; and what the lead does when a monitor is not
green — report and hold is the floor. Keep the first cut small: one gate
shape, checked by the lead, cleared by the principal's message. The lead
splitting a brief into stages on its own is out of scope.

Done when: a goal handed with two stages and a gate between them reaches two
draft PRs, the lead holds after the first until the principal clears the
gate, the portfolio shows the hold and the clearance, and a goal handed with
no gate runs unchanged. Record what the run showed in design §15.

Read first: design §1, §6.4, §15.74, §15.79, §15.80; `skills/lead/SKILL.md`
"Triage every item by size" and "Batch the rest into one message";
`record-format.md` "The portfolio record"; `autonomy-contract.md`.

Landed 2026-09-07 as one item per stage with `depends_on` and a `gate`, the
`held` state, "A gate holds the next stage" in `skills/lead/SKILL.md`, "A gate
a stage waits on" in `autonomy-contract.md`, and design §15.87. No script
changed. The live run took a two-stage goal to two draft PRs with a 19-minute
hold between them: the lead reported `OPEN`, held, reported `MERGED` on a
re-check, held again, and started stage 2 only on the principal's go. An
ungated third item ran unchanged. The lead read the gate's condition out of the
brief rather than asking for it, which §15.87i keeps and answers with one
clause: the ask now quotes the condition back.

## T50 — Say who may add a portfolio item

Status: done
Depends on: T47
Stage: 7 (design §15.85; the rule is §15.86, and §15.85's run is the proof —
no new live run backs this ticket)

A peer session asked a lead to add an item to its portfolio, and the lead
escalated it to the human instead of running it (§15.85). That answer came
from judgment. No file says who may add an item, and
`autonomy-contract.md` defines the principal as whoever handed the work
over — under which a peer session is a plausible principal. The next lead
reads nothing and can go either way.

Write the rule where the lead reads it. Say who adds an item to a
portfolio, and what a lead does with a request from any other session: it
records the request, escalates it, and answers the sender. Name the file
that owns the rule and state it once — `skills/lead/SKILL.md` holds the
lead's own conduct, and `autonomy-contract.md` holds who the principal is.

Done when: one file states who may add a portfolio item, the other points
at it, and a request from a peer session has a written route.

Read first: design §15.85, §15.72d; `skills/lead/SKILL.md`;
`autonomy-contract.md`.

## T51 — The project lead sizes the work, and a small item runs on a light path

Status: done
Depends on: T39, T42, T48, T49
Stage: 7 (design §15.79, §15.83, §15.87)

T39 put a sizing step in the lead: a task gets one IC that the lead runs
itself, a goal gets a project-lead session. Three runs later the cost of
that split is clear. The lead is busy for eight to ten minutes per task, its
context fills with plans, reports and diffs, and its record holds a second
shape (`items[].task`) beside the run record, which is where T45's six
defects and `crew-stats.py`'s twin code paths came from. The principal's
intent, stated 2026-09-11, is the opposite: the lead is the one session the
principal talks to, it hands work to project leads and stands ready for the
next instruction, and the project leads are the ones that stay busy.

Move the sizing to the project lead, which reads the code and already routes
between three paths. Three parts:

1. **The lead hands every item to a project-lead session.** Size does not
   change the lead's shape: charter, session, hand over, end the turn. The
   lead's "Triage every item by size", "A task runs under you" and the task
   record come out of `skills/lead/SKILL.md` and `record-format.md`. What
   stays: the gate loop (T49), the batch (T41), the wake and the resume
   (T44), and who may add an item (T50).
2. **The project lead gains a light path.** After the scout, when the change
   is one package, the charter's criterion is the spec, and the band is
   `light` or `standard` with no judgment call open, the project lead skips
   the spec and its critic and goes to one IC and one package review, with
   `band-rubric.md`'s skips (T42) on top. `SKILL.md` routes to it beside the
   simple, full and investigation paths; a small path file or a section of
   `simple-path.md` owns the loop, and `band-rubric.md` owns what the path
   skips. An item that turns out bigger promotes in place to the simple or
   the full path, with no return to the lead. T48's registration-line rule
   moves here: a light-path package may name a shared file the repo's
   instruction file marks as the registration point.
3. **One record shape.** Every item is a run record under
   `runs/<item-id>/<slug>/`, with `state.json`. `items[].task` goes;
   `record-format.md`'s "The task record" goes; `crew-stats.py` loses
   `TASK_SKIPPABLE_STEPS`, `read_task_review` and `read_portfolios`' task
   branches, and the "in tasks" column with them. `lead-spend.py`'s
   double-count rule stays, and a lead's spend no longer holds workers.

Cost, stated so nobody is surprised: every item now pays a Fable
project-lead seat. T42's light run cost $4.93 against $3 to $4 for a
lead-run task, so a trivial item costs a dollar or two more and takes a
minute or two longer to start. The principal accepted that on 2026-09-11 in
exchange for a lead that is always free and a design with one session kind.

Done when: a one-line task handed to the lead reaches a draft PR through a
project-lead session on the light path, with no spec file and one review in
its run record; the same lead takes a second item while the first runs; a
goal handed the same way runs as before; `crew-stats.py` reads one record
shape; and no file under `skills/lead/` names a task the lead runs itself.
Record what the run showed in design §15, and mark §15.79's lead-side rules
and §15.83's triage exception superseded.

Read first: design §15.79, §15.83, §15.87, §15.77, §9.1;
`skills/lead/SKILL.md` whole; `skills/project-lead/SKILL.md` "Scout" and "Choose
the shape"; `simple-path.md`;
`band-rubric.md` "What a band skips"; `record-format.md` "The task record"
and "The portfolio record"; `crew-stats.py`; `lead-spend.py`.

## T52 — Two items in one repo run in two checkouts

Status: done (design §15.90)
Depends on: T51
Stage: 7 (design §15.88f, §15.88g)

T51's live run handed a lead two items in the same repo while the first was
still running. Both project leads got the same `repo` path, so both ran in
one checkout. Two things followed. The second project lead saw the first run
on the checkout, cut a worktree of its own to stay off it, and left the
worktree registered at the close — nothing in the design said it could, or
should. And `spend.py` prices a run over every transcript that ran from the
checkout inside the run's window, so each run was billed for the other's
work: $8.85 and $9.71 in the table against about $4.90 each in fact
(§15.88f). The simple path's "Create the branch" also switches the shared
checkout to the run's branch, so two runs in one checkout fight over the
branch as well.

Write the rule. The lead knows the case before anyone else: it holds two
items with one `repo`, and one of them is `running`. Decide where the second
checkout comes from and who makes it, then make both tiers follow it. Three
constraints:

- The lead runs read-only git and nothing else in a checkout
  (`skills/lead/SKILL.md`, "You never touch a target repo"). A rule that has
  the lead run `git worktree add` or `gh repo clone` reopens what T51 closed.
  Prefer one where the lead names the checkout and the project lead makes it,
  or where the project lead detects the case itself.
- `spend.py` prices by the escaped checkout path, so a run in a worktree of
  its own is priced alone. A rule that keeps two runs in one path leaves the
  double count in place; if you choose it, say so and give `spend.py` a way
  to tell the runs apart.
- A worktree the run cuts is recorded in its `worktrees.json` and removed at
  "End the run", the way the full path already does it.

Done when: a lead handed two items in one repo runs both at once, each run's
record shows a distinct checkout path, `crew-stats.py` prices each run alone,
and neither run leaves a worktree behind. Record the run in design §15 and
point at it from §15.88g.

Read first: design §15.88f, §15.88g, §15.51, §9.1; `skills/lead/SKILL.md`
"One project-lead session per item" and "You never touch a target repo";
`session-launch.md` "Handing over the charter"; `simple-path.md` "Create the
branch" and "End the run"; `full-path.md` on worktrees; `record-format.md`
`worktrees.json` and the item's `repo`; `spend.py`.

## T53 — Promote a light-path item in place

Status: done
Depends on: T51
Stage: 7 (design §15.88h, §15.91)

T51 gave the light path a promotion rule: the four answers can turn out wrong
once the IC reports or once the diff's file list is read, and the project
lead then goes back to "Write the spec" in the same session, on the same
branch, keeping every commit. No run has done it (§15.88h). Both live items
sat in repos with one registration point and one deliverable, so nothing
tested the seam.

Force it. Seed the fixture so that an item reads as one package at "Size the
work" and is not — for example, a helper the charter names in one line, in a
fixture whose instruction file requires every new helper to ship a second
thing in another territory that the sizing step would not see, such as a CLI
subcommand under `bin/`; or an IC that reports `BLOCKED` on a scope it cannot
hold. Pick a seed that forces the promotion after the dispatch, not at "Size
the work". §15.71 says a project lead on a small fixture may read it directly
instead of scouting, so the seed must survive a direct read too. If no seed
can reach the seam, that is the finding: say why, and say what the promotion
rule should become.

Then check what the promotion did to the record: `decisions.md` holds the
promotion entry, the deliverable keeps its branch and `base`, the IC's
commits survive, the spec critic runs on the spec the promoted run writes,
and `run.steps_skipped` either drops the light path's `spec-critic` entry or
keeps it with the reason updated. `record-format.md` decides which; write it
down.

Done when: one light-path item promotes in place to the simple or the full
path and reaches a draft PR, its record shows the promotion and the commits
from before it, and design §15 holds what the run showed — or §15 says why
the seam cannot be reached, with the rule change that follows.

Read first: design §15.88b, §15.88h, §15.71; `skills/project-lead/SKILL.md`
"Size the work"; `simple-path.md` "The light path"; `band-rubric.md` "What
the light path skips"; `record-format.md` `steps_skipped` and `decisions.md`;
`ic-contract.md` report statuses.

## T54 — A project lead stays until the work ships

Status: done (design §15.92)
Depends on: T52
Stage: 7 (design §15.92)

A project lead handed a charter by a lead opened its PR, sent its closing
report and was killed (`session-launch.md`, "Closing it"). The principal's
questions about the change come after that, before the merge, and a
follow-up after review comments came as a new item with a new scout of the
same repo. The rule now says the session stays: the run goes `delivered` at
the hand-over and `complete` only on the principal's word that the work
shipped, and the window between takes questions and follow-ups from the lead
and from the principal's own typing (design §15.92). That rule landed with
this ticket, and one item ran through the whole window the same day (design
§15.92g).

Run it. One item through a lead, to a draft PR. Then, through the lead: one
question about the change, answered; one follow-up that changes the code — a
review comment to address is the natural one — pushed to the same PR with no
second PR opened; then the ship word, and the item `done` with
`run_state: complete` in the record. Then the same three by typing in the
project lead's pane directly, on a second item, so both channels are shown.
Kill one delivered session mid-window and confirm the lead resumes it and
the next question still gets an answer.

Check what the record shows: `delivered_at` and `completed_at` both set, the
follow-up's package and `decisions.md` entry, `checkout_restored` written
twice, no worktree left registered, and `spend.transcript` written at `ship`
covering the window. Check `crew-stats.py` prices the run through
`completed_at` and not `delivered_at`.

Done when: both channels have run through a question, a follow-up and the
ship word, the record shows all of the above, and design §15.92 holds what
the runs showed — including what the rule got wrong.

Read first: design §15.92, §15.72, §15.87e; `skills/lead/SKILL.md` "A
delivered item keeps its session"; `session-launch.md` "Resuming a dead one"
and "Closing it"; `simple-path.md` "End the run" and "The delivered window";
`record-format.md` `run_state` transitions and the item state transitions;
`crew-record.py`.

## T55 — The lead launches every project lead into one `crew` tmux session, with ICs as panes

Status: open (design §15.93)
Depends on: nothing
Stage: 7 (design §15.93)

The lead's tmux launch (`session-launch.md`, "The launch") names no session
for `tmux new-window`, so which one a window lands in is the lead's own
judgment call. The live transcript that found this showed the lead pick a
stale session left over from an earlier run, land a dead window in it (the
server's start directory had since been deleted), then land its retry in a
fresh session the principal had no client on. Ctrl-b n in the principal's
own session never found it. The launch also carries no `--teammate-mode`, so
a full-path project lead's ICs run in-process and get no pane. Design §15.93
found both causes against that transcript and wrote the fix: one tmux
session named `crew`, held by name so no run's own judgment picks the
target, holding one window per project lead, each window split into the
project lead's pane plus one pane per IC teammate. A first pass at the fix
is open as PR #74, branch `t55-lead-tmux-layout`.

The first run, 2026-09-14 to 15: one item, `pp-06-books-slug`, simple path,
band `deep`, draft PR `jerridan/websites#35` (design §15.93h). The launch,
the window placement, the `cd <repo> &&` prefix and the hand-over ran
exactly as `session-launch.md` now writes them. The item sized simple path
with one unnamed IC, so the window never split, and the full-path pane
check, the spawn-time model check and the spend-gap measurement stayed
unexercised. This ticket closes when a full-path run shows the panes.

Run it. Use design §15.93c's commands exactly, in `session-launch.md`. Run
one full-path goal with at least two packages, so the project lead spawns at
least two named ICs.

Check that `tmux attach -t crew` shows every project lead as its own window,
that Ctrl-b n cycles through them, and that each full-path window splits into
one pane per IC teammate plus the project lead's own. Start the lead itself
with `tmux new -A -s crew` rather than by hand, since design §15.93h's lead
was placed in window 0 manually and that command's own window placement is
still unproved, and check which window number the lead lands on. Check the
spawn-time `model` landed on each IC (design §15.20d, §15.20e), by asking
one what model it is running as, or by reading its report for a
model mismatch. Check `crew-stats.py` and `spend.py` against the run, and
record how far short they price it (design §15.90h). Check that a pane
split too small to fit escalates as `environment` (`full-path.md`), by
shrinking the terminal before launch. Force a compaction in one IC's pane
with `/compact` and check whether it lands in `run.compactions`, confirming
or denying design §15.93f's prediction that it does not.

Done when: a full-path run has exercised the layout end to end, design §15.93
holds what it showed, and PR #74's tmux commands match what the run proved
rather than what it assumed.

Read first: design §15.93, §15.20c, §15.20d, §15.89d, §15.89e, §15.90h;
`session-launch.md` "The launch"; `full-path.md` for how ICs are named,
dispatched, and for the `environment` escalation.

## T56 — Price and log split-pane teammates outside `run.session_ids`

Status: open (design §15.90h, §15.93)
Depends on: T55
Stage: 7 (design §15.93)

`spend.py` and `crew-stats.py` price a run from its own sessions
(design §15.90), and a split-pane teammate is its own session, outside the
project lead's subtree. `hooks/pre-compact.py`'s `session_in_run()` has the
same blind spot: it matches a session id against `run.session_ids` and
against each worktree's own `session_ids` in `worktrees.json`, and a
split-pane teammate's id lands in neither, so it logs no compaction for one.
Every run so far ran in-process, where a teammate has no session of its own,
so neither gap ever showed. A run launched with `--teammate-mode tmux` hits
both.

**Do not put a teammate's session id in `run.session_ids`.**
`hooks/session-end.py` marks a run `interrupted` when a dying session's id
appears there, so a teammate pane closing at the end of its package would
mark a live run dead. The id belongs in a separate field, for example
`run.teammate_session_ids`, that `spend.py` and `crew-stats.py` read and that
both hooks ignore.

The open question this ticket must answer first: a project lead is handed no
teammate session id at spawn, so where does the id come from? The team
config at `~/.claude/teams/session-<id8>/config.json` holds session IDs and
tmux pane IDs for the life of the session, and is removed at session end, per
the Claude Code docs. Check whether the project lead can read that file
while its teammates are still live, and whether the id still resolves after a
teammate goes idle.

Run it. One full-path run with `--teammate-mode tmux`, with at least one IC
teammate.
Read the team config while the run is live and confirm it names the
teammate's session id. Write that id into the new field at the point the
project lead learns it, have `spend.py` and `crew-stats.py` include it in the
run's price, and confirm neither hook treats it as a project-lead id.

Check the priced figure against a hand count of the teammate's own
transcript tokens. Check that killing a teammate's pane mid-package leaves
`run_state` untouched. Force a second compaction with `/compact` in the
teammate's pane and check that it lands in `run.compactions` now.

Done when: a full-path run under a split pane prices whole, its teammate
compactions are logged, `record-format.md` documents the new field and when
it is written, and design §15.90h's open gap is marked closed.

Read first: design §15.90h, §15.93; `record-format.md` on `run.session_ids`
and `run.compactions`; `hooks/session-end.py` and `hooks/pre-compact.py`
(`session_in_run()`); `skills/project-lead/scripts/spend.py`, `crew-stats.py`;
the Claude Code agent-teams docs on the team config file.

## T57 — Remove the lead tier

Status: done
Depends on: nothing
Stage: 7 (design §15.19, §15.72)
Probe: two hand-launched project-lead sessions, with kills and a forced
compaction, no record slug (target-repo run), §15.98f.

The lead was built to hold a portfolio and to launch one project-lead
session per item. In its first real use (run
`agi-3057-handoff-attempt-record-399d`, 2026-09-15) it wrote a 49-line,
928-word charter that named the module location, the state enum to reuse,
the storage pattern, the TTL, the metrics and the flag name. The project lead
adopted that charter unchanged, as `record-format.md` says it must, and the
principal then had to reverse one of those choices through the project lead
("charter.md item 5 named 90 days, overridden by the principal"). The lead
reads no code, so when asked why, it answered from reports. The principal's
verdict: the tier makes decisions the project lead should make, and they
would rather drive project leads directly until they see the patterns in how
they manage them. A lead may come back later, built from those patterns.
This ticket removes the tier as it stands.

**What goes.** `skills/lead/` in full: `SKILL.md`, `references/
session-launch.md`, `scripts/crew-portfolio.py`, `scripts/lead-spend.py`.
The portfolio record: the "The portfolio record" section of
`record-format.md` and its consumer-list entries. The lead branches in the
two hooks: `interrupt_lead()` and `wake_lead()` in `hooks/session-end.py`,
and the portfolio-compaction block in `hooks/pre-compact.py`. The "Leads"
report and the `lead.spend` totals in `crew-stats.py`. The "Run your goals
through a lead" section of `README.md`, its `/crew:lead` command row, and
its "Lead" rows in the model and role tables. The `skills/lead/` rows and
the three-tier build narrative in `CLAUDE.md`.

**What stays.** Everything the project lead does on its own. The charter as
an input: a person can hand `/crew:project-lead` a charter path, and two
runs already did with no lead in the loop (design §15.22a). The word
"principal" in `autonomy-contract.md`: it names whoever handed over the
goal, a person or a session, and that stays general. Remove only the
clauses that describe a lead's portfolio, `lead.principal`, and batching
answers for a lead. `CREW_LAUNCH` and the `crew` tmux session layout stay
if the README still tells a person to launch a project lead into tmux;
otherwise they go with the lead.

**Reword, do not delete.** `skills/project-lead/SKILL.md` line 125 ("the
lead above you reads no code"), the seven lead mentions in `simple-path.md`
and the two in `full-path.md`: each describes the project lead's caller
being a lead. A person is the same caller, so drop the lead-specific clause
and keep the sentence. `.claude/rules/readme.md` names the lead section as
the README's main entry point; move that to the project lead.

**Do not touch `docs/design.md`.** Its §15 findings on the lead are the
record of what was built and observed. Add one finding there that says the
tier was removed, why, and what a future lead must not do: write charter
lines the principal did not say. `CLAUDE.md`'s "Never write about an unbuilt
stage as if it runs" applies in reverse here: the README and `CLAUDE.md`
must describe what the plugin does after this PR, not what it did.

**Bump `version` in both manifests.** `skills/` and `hooks/` change, so
`.claude-plugin/plugin.json` and `marketplace.json` move together.

T56 stays open: it prices split-pane teammates, which a project lead a
person launches into tmux still has. Re-read it after this ticket and drop
the lead-specific sentences.

Run it. One light-path item and one simple-path item through
`/crew:project-lead`, launched by hand, one with a goal string and one with a
charter path. Kill the project lead mid-run and confirm `session-end.py`
marks the run `interrupted` and does not fail looking for a portfolio.
Force a compaction and confirm `pre-compact.py` logs it into the run.

Done when: `skills/lead/` is gone, both hooks run clean with no portfolio on
disk, `crew-stats.py` reports every run with no "Leads" section, the README
and `CLAUDE.md` describe a two-tier plugin, `grep -ri 'crew:lead' --exclude-dir=docs`
returns nothing, and design §15 holds the finding.

Read first: design §15.19, §15.21, §15.22a, §15.70, §15.72;
`autonomy-contract.md` in full; `record-format.md` "The portfolio record";
`hooks/session-end.py`, `hooks/pre-compact.py`; `.claude/rules/readme.md`;
`writing-standard.md` "Before you open the PR".

## T58 — Cut the plan gate and the package review; the project lead verifies each package itself

Status: done
Depends on: nothing
Stage: 7 (design §15.94)
Probe: the project lead caught a dirty tree and a dropped test assertion on
its own verification, add-padcenter-helper-5b0b, §15.98a.

All thirty plans on disk carry a `plan_approved_at`, and no record names a
plan sent back (design §15.77b). The package review sends a package back
rarely: 4 of 37 reviews by the count in design §15.77a, 4 of 32 by §15.57's
earlier count over fewer records, and 24 of 29 packages left it with no line
of their code changed. Both counts measure verdicts, not defects — §15.57
records accepted reviews whose findings led to commits — but neither step
sends work back often enough to pay for a dispatch. On run
`agi-3057-handoff-attempt-record-399d` the package review ran nine times and
sent nothing back, while outside reviewers found 19 defects in the same code
(design §15.94a). Both steps go. The project lead keeps the check that
actually drove fix rounds: its own run of the acceptance test and the suite
after each package.

Scope. `band-rubric.md` loses the plan gate and the package review from "What
a band skips", "What the light path skips" and "Critics and reviewers take
their own model". Its deliverable-review skip conditions keep their shape,
but the second condition changes from "its package review reads `Verdict:
accepted`" to "the project lead's own verification passed". `simple-path.md`
and `full-path.md` lose the package-review step, and their fix-round trigger
becomes the project lead's own failed verification. Fix-round and promotion
caps do not change. `skills/project-lead/SKILL.md` drops both steps.
`ic-contract.md` loses "The plan gate" branch; the IC still writes
`plans/<id>.md`. `agents/ic.md` (step 2 of "Your loop", line ~22) and
`agents/ic-instructions.md` (step 2 of "Your loop", line ~42) both tell the
IC to write the plan and then wait; both now say the IC starts work straight
after it writes the plan. `agents/package-reviewer.md` is deleted.

**A prose package is verified against two checklists.** The project lead
applies the package's own acceptance checklist, and it applies
`writing-standard.md`'s "Before you open the PR" checklist. A failed item on
either one is a fix round, exactly as a failed test is.

The deliverable reviewer outlives this ticket and must still run between T58
and T59. So `agents/deliverable-reviewer.md` (lines ~23 and ~48–50) drops the
requirement that every package review read as accepted: package reviews no
longer exist, and the project lead's own verification is the precondition
now. `investigation-path.md` (line ~84) updates its pointer to "Review the
package". `review-output.md` (lines ~3–4) and `band-rubric.md`'s "Critics and
reviewers take their own model" drop the package reviewer from their agent
lists.

`record-format.md` drops `plan_approved_at` and the package-review file name.
It drops `plan-gate` from the `steps_skipped` values. `deliverable-review`
stays there until T59 removes it. `spec-critic` stays there indefinitely,
because the light path still skips the spec critic. `crew-stats.py` drops the
package-review and plan-gate rows from its catch-rate section. The README and
`CLAUDE.md` role tables lose the package reviewer. Bump `version` in both
manifests.

Run it. Take one light-path item to a draft PR against the fixture repo, and
one item whose package is prose, so `crew:ic-instructions` runs under the
two-checklist rule. Seeding a failing test does not force a fix round,
because the IC fixes it before it reports. Instead, after the IC's first
report, revert one line in the worktree by hand, so the project lead's own
run finds a failure the report does not mention.

Check that no reviewer agent was dispatched for either package, that the IC
started implementing straight after it wrote `plans/<id>.md` with no
go-ahead, that `plan_approved_at` is absent from `state.json`, that the fix
round fired from the project lead's own run and not from a verdict, that the
prose package's fix round came from a checklist item, that the deliverable
review still ran without a package-review precondition, and that
`crew-stats.py` reports the run with no package-review or plan-gate row.

Done when: neither step appears in any path, agent, script or record field;
the fix-round trigger reads as the project lead's own verification everywhere
it is stated; and one run has taken a package through a fix round on that
trigger.

Read first: design §15.94a, §15.94d, §15.57, §15.77a, §15.77b;
`band-rubric.md`; `simple-path.md` and `full-path.md` review and fix-round
sections; `ic-contract.md`; `agents/ic.md`; `agents/ic-instructions.md`;
`agents/deliverable-reviewer.md`; `investigation-path.md`;
`review-output.md`; `record-format.md`; `writing-standard.md` "Before you
open the PR".

## T59 — Replace the deliverable review with a skeptical review after the PR opens

Status: done
Depends on: T58
Stage: 7 (design §15.94)
Probe: a killed skeptical review resumed and its second round caught a
real defect, add-padcenter-helper-5b0b, §15.98b.

Superseded by the landed schema: see `record-format.md`
(`packages[].round`, `run.rounds`, `reviews/<round-id>-reply.md`) and
`skeptical-review.md` for when `review_pending` clears.

The deliverable review sent an artifact back 2 times in 18 (design §15.77a).
On run `agi-3057-handoff-attempt-record-399d` it ran six times — once before
the PR opened, and once on each of the first five follow-ups — and returned
`accepted` every time (design §15.94a). It reads the spec and the contract
that the project lead wrote, so it measures the author against the author
(design §15.94b). The replacement reads the diff against the goal and the
repo, assumes the diff is wrong, and runs on real code after the PR exists.

Scope. A new reference, `skills/project-lead/references/skeptical-review.md`,
owns the step, and it owns the schedule as well. It holds:

- **The stance.** Read the diff against the goal, not the spec. Assume it is
  wrong and look for how. Run the suite. Report findings by severity. Say
  what you looked for and did not find.
- **The inputs the run supplies.** The goal text, the branch, the base ref
  and the output path.
- **Its own two verdict strings**, `accepted` and `patch round needed`.
  `review-output.md` stays format-only, and it says that each producer names
  its own pair.
- **The worktree rule.** Never run the review in the run's own checkout. A
  probe found a finder agent run `git checkout main` inside the repo under
  review.
- **The default headless command.** The initial implementation was `claude -p
  --model opus "/code-review high <base>"`; §15.98b's probe found it broken
  three ways and replaced it. `skeptical-review.md`'s "The default command"
  now owns the runner, and this ticket does not restate it.
- **How the findings are collected.** The JSON `result` field holds only the
  last message, so use `--output-format stream-json`, or put an instruction
  in the prompt that writes the findings to a file (design §15.94c).
- **What the run costs.** The headless run is its own session, so its
  `session_id` (from `--output-format json`) goes into a new
  `run.review_session_ids` field that `spend.py` and `crew-stats.py` price
  and that both hooks ignore. **Never put it in `run.session_ids`**, which
  `hooks/session-end.py` reads to mark a run interrupted, the same rule T56
  states for a teammate's id.
- **The schedule.** The review runs once after the draft PR opens, and again
  after every push of new commits to the branch in the delivered window, from
  a patch round or from a change request alike. It is the only reader of new
  code, so every push earns one.
- **The cap.** 3 reviews per run, the initial one included. Each start
  increments `run.review_rounds`, and that write happens before the review
  starts. At the cap no further review runs, and the project lead hands the
  principal what remains, including what it declined and why.
- **The resume rule.** A resume infers nothing from a missing file. The same
  record write that lands a push sets `run.review_pending` to the new head
  sha, and writing the review file clears it. On `--resume` in `delivered`, a
  set `review_pending` means the review is owed, and an unset one means
  nothing is owed.

The review slot in `simple-path.md` and `full-path.md` moves to after "Open
the draft PR" and becomes the first round of the delivered window. Both files
point at the new reference and state no rule of their own.
`agents/deliverable-reviewer.md` is deleted. `band-rubric.md` loses the
deliverable-review skip conditions. `record-format.md` takes the new review
file names, the three new fields and when each is written, and drops
`deliverable-review` from `steps_skipped`. `spend.py` and `crew-stats.py`
read `run.review_session_ids`, and `crew-stats.py` takes the new review kind.
Bump `version` in both manifests.

Run it. Take one simple-path item to a draft PR against the fixture repo, and
let the skeptical review run as the first round of the delivered window. Kill
the session after the PR opens and before the review writes its file, then
resume.

Check that the review ran in a worktree and not in the run's checkout, that
the run's branch and working tree were untouched afterward, that the findings
landed in the record in `review-output.md`'s shape with one of the two verdict
strings, that `run.review_pending` held the head sha across the kill and the
resume ran the review because of it, that `run.review_rounds` counted the
start and not the finish, that `run.review_session_ids` holds the headless
run's id, that neither hook acted on that id, and that `spend.py` prices the
review into the run.

Done when: no path runs the deliverable review before the PR opens — the spec
critic still runs before the split — the deliverable reviewer is gone, and one
run has produced a `reviews/skeptical-r1.md` from a worktree run that prices
into the record.

Read first: design §15.94b, §15.94c, §15.94d, §15.77a; `review-output.md`;
`simple-path.md` and `full-path.md` review sections; `band-rubric.md`;
`record-format.md` on `run.session_ids` and `steps_skipped`; T56 on why a
foreign session id stays out of `run.session_ids`;
`skills/project-lead/scripts/spend.py`, `crew-stats.py`.

## T60 — Patch mode in the delivered window

Status: done
Depends on: T59
Stage: 7 (design §15.94)
Probe: four typed items sorted and patched correctly through two kills,
add-padcenter-helper-5b0b, §15.98c.

Superseded by the landed schema: see `record-format.md`
(`packages[].round`, `run.rounds`, `reviews/<round-id>-reply.md`) and
`skeptical-review.md` for when `review_pending` clears.

Six follow-ups on run `agi-3057-handoff-attempt-record-399d` each ran a
package review, and the first five each re-ran the whole deliverable review,
on a deliverable that had already passed both (design §15.94a). Most of those
follow-ups were review findings, not new work, and the review layer added
nothing to them. The delivered window needs to tell the two apart.

Scope. `simple-path.md`'s "The delivered window" gains two message kinds. A
**change request** is something the PR does not do yet. It stays one package,
with an IC and the project lead's own verification. It gets no spec, no
critic and no separate reviewer; the skeptical review re-runs on the push it
produces, on `skeptical-review.md`'s schedule. **Findings from a review** —
CI, a bot, Codex, the principal reading the diff, or the skeptical review
from T59 — go to patch mode. The project lead groups them and dispatches one
IC per group in the checkout, then runs the suite and pushes.

**Each group is a `packages[]` entry** like any other, with a new `source`
field naming where its findings came from, so `--resume`'s "all packages
terminal" logic needs no change. A patch package carries two more fields
beside its state, `pushed_at` and `replied_at`, and they make the round
resumable at every step. Integration writes the package `integrated` and sets
`run.review_pending` to the new head in one write. The push then sets
`pushed_at`. The reply to the source is written to
`reports/<pkg-id>-reply.md` before it is sent, and `replied_at` is set after
it is sent. On a resume, an `integrated` package with a null `pushed_at` is
pushed first, and a null `replied_at` after that means the reply file is sent.
`record-format.md` owns the two fields and their transitions.

The project lead replies per finding with what changed. A finding it
disagrees with gets a written reason, never silent application. **A round
where every finding is declined produces no patch, no push, no new head and
no new review.** That round still consumed the one `review_rounds` increment
that the review producing the findings took, and the reply carries every
decline with its reason. `skeptical-review.md` owns the cap and the schedule;
this file states neither. A source other than the skeptical review is quiet
when it returns nothing above `[Nit]` on the new head — for CI, a green run.
The principal and a bot are never quiet, and the window simply stays open for
them. The rule that re-arms the deliverable review when a second package
appears goes. `full-path.md` points at the simple-path section and states no
rule of its own.

Run it. Deliver one light-path item, then send it three seeded findings in
one message, with one of the three wrong. Kill the session twice: once after
the group integrates and before the push, and once after the push and before
the reply. Then send a second message whose findings are all wrong, so every
one is declined.

Check that the project lead dispatched one IC per group and no reviewer, that
each group landed as a `packages[]` entry with its `source`, that the resume
after the first kill pushed before it replied, that the resume after the
second kill sent the reply file without a second push, that the reply
declines the wrong finding with a reason, that the all-declined round pushed
nothing and started no review, and that a re-run of the skeptical review
returning only `[Nit]` findings ends the rounds.

Done when: the delivered window separates the two message kinds, a patch
group is an ordinary package entry, a killed round resumes at the push and at
the reply, the re-arm rule is gone, and one run has declined a finding with a
reason on the record.

Read first: design §15.94a, §15.94d, §15.92c; `simple-path.md` "The delivered
window"; `record-format.md` on `packages[]` and on `--resume`; `full-path.md`;
T59 and `skeptical-review.md` for the schedule and the cap.

## T61 — Plain-language substitution of a review step

Status: done
Depends on: T59
Stage: 7 (design §15.94)
Probe: "use Codex for the spec review" ran three rounds and wrote
steps_substituted with its token usage, add-truncate-helper-cfd5, §15.98d.

The principal already knows which reviewer they want for a given goal, and
today there is no way to say so. Design §15.94d(5) settles the shape: a
replacement named in plain language runs in the step's slot, and the record
says what ran.

Scope. One paragraph in `skills/project-lead/SKILL.md` states the rule: when
the goal, the charter, or the principal at launch names a replacement for a
review step, the project lead runs the replacement in that step's slot and
writes its output into the record in `review-output.md`'s shape. A pointer
line at the spec-critic step and at the skeptical-review step sends the
reader there. `record-format.md` gains `run.steps_substituted`, holding the
step, the replacement and the time, beside `steps_skipped`. Each entry also
carries an optional `usage` object, holding whatever figure the runner
prints — Codex prints a "tokens used" line, for example. **A substituted step
costs money that `spend.py` cannot see**, because the runner is not a Claude
session. So `crew-stats.py` lists every substitution and reports its cost as
unmeasured unless a price can be derived from `usage`. It never leaves the
step out of the report. Bump `version` in both manifests.

Run it. Launch a project lead with "use Codex for the spec review" typed at
launch, on any goal that writes a spec.

Check that `codex exec` ran with the spec critic's seven checks as its
prompt and the spec and charter paths as its input, that the output landed in
the record in `review-output.md`'s shape, that the spec critic itself did not
run, that `run.steps_substituted` names the step, the replacement and the
`usage` figure Codex printed, and that `crew-stats.py` lists the substitution
with its cost marked unmeasured.

Done when: a named replacement runs in a review step's slot, the record holds
the substitution and whatever usage the runner printed, and `crew-stats.py`
reports the step rather than omitting it.

Read first: design §15.94d, §15.94e; `skills/project-lead/SKILL.md`;
`review-output.md`; `record-format.md` on `steps_skipped`; `crew-stats.py`.

## T62 — `crew-stats.py` counts promotions from `band_history`, not from package count

Status: done
Depends on: nothing
Stage: 7 (design §15.94)
Probe: a seeded second band_history entry reported 1 promotion against the
real root's 0, add-padcenter-helper-5b0b, §15.98e.

`crew-stats.py` reports 7 promotions for run
`agi-3057-handoff-attempt-record-399d`. The record holds none: every package
has one `band_history` entry, its prediction (design §15.94g). The script
counts every entry that carries a `cause`, and the prediction carries one.

Scope. The promotion count in `crew-stats.py` reads entries in each package's
`band_history`. No other output changes.

Run it. Run `crew-stats.py` against the AGI-3057 record.

Check that it reports 0 promotions for that run, and that a seeded record
with a second `band_history` entry on one package reports 1.

Done when: the promotion count is the number of `band_history` entries past
the first, per package, and the AGI-3057 record reports 0.

Read first: design §15.94g; `skills/project-lead/scripts/crew-stats.py`;
`record-format.md` on `band_history`.

## T63 — A layered config file for step substitutions

Status: open
Depends on: T61
Stage: 7 (design §15.94)

Filed, not scheduled. T61 lets the goal, the charter or the principal name a
replacement for a review step, one run at a time. A principal who wants the
same replacement on every run has to say it every time. A layered config
would hold it once.

Scope. Three layers, most specific wins per step: a machine file at
`~/.claude/crew/config.md`, a repo file at `.claude/crew.md`, and the run
charter. Each holds the same section T61 reads, in the same plain language.
The project lead resolves the three before the first review step.

Run it. Set a machine-level replacement for the skeptical review, override it
in a repo file, and run one item in that repo.

Check that the repo file won, and that `run.steps_substituted` names the
layer the replacement came from.

Done when: the three layers resolve per step and the record says which layer
supplied each replacement.

Read first: design §15.94e; T61; `skills/project-lead/SKILL.md`;
`record-format.md`.

## T64 — A crew-owned Codex review skill

Status: open
Depends on: T61
Stage: 7 (design §15.94)

Filed, not scheduled. Two review steps can go to Codex — the spec review and
the diff review — and today each caller would write its own `codex exec`
command. One skill holds the command, the model and the output shape.

Scope. A crew-owned skill wraps `codex exec` with a pinned model. It takes
either a diff base or a file list, so the same skill serves the spec review
and the skeptical diff review. It writes its findings in `review-output.md`'s
shape. T61's substitution rule names it as a replacement.

Run it. Substitute the skill for the spec review on one item, then for the
skeptical review on another.

Check that both runs used the pinned model, that the file-list form and the
diff-base form each produced findings, and that both outputs match
`review-output.md`'s shape without hand editing.

Done when: one skill serves both review steps and its output needs no
reshaping.

Read first: design §15.94e; T61; `review-output.md`; `skills/project-lead/`
for how a crew skill is laid out.

## T65 — Haiku runs only an agent whose tools need no approval

Status: done
Depends on: nothing
Stage: 7 (design §15.96)

Auto mode's permission classifier has no approver for Haiku on any provider,
and a Haiku agent with `Bash`, `Write`, or `Edit` prompts on every call that
needs approval, in a session nobody is watching. Session
`aad2bfca-66ed-47cd-928f-1da15964bbf9` showed it: a named Haiku `Explore`
scout prompted on every call, while the same run's two `crew:ic` dispatches
ran at `sonnet` and prompted for nothing.

Scope. A new agent, `crew:scout`, built from `Read`, `Glob` and `Grep` alone,
answers the project lead's four scout questions and is the only agent Haiku
runs. `band-rubric.md` states the rule and moves the `light` band's ICs to
`sonnet`. `SKILL.md`'s "Scout" step, the README's model table, and design §3's
role table point at `crew:scout` instead of `Explore`.

Run it. Read `band-rubric.md`, `agents/scout.md`, and `SKILL.md`'s "Scout"
step.

Check that no instruction file still sends Haiku to an agent carrying `Bash`,
`Write`, or `Edit`, and that the rule lives in `band-rubric.md` alone.

Done when: `crew:scout` exists, dispatches at `haiku`, and every other agent's
floor is `sonnet`.

Read first: design §15.96; `band-rubric.md`; `agents/spec-critic.md` for the
agent-definition shape.

## T66 — Name every dispatch

Status: open
Depends on: T65
Stage: 7 (design §15.20b, §15.31c)

The rule "only ICs are named" rests on design §3's claim that a teammate's
output never returns to the project lead. §15.20b recorded the claim as
wrong, and a later probe (§15.31c) confirmed the final answer arrives as
prose in the idle notification. The principal decided every dispatch is
named, so every agent gets a pane under a display mode.

Scope. Flip the naming rule in design §3, and every "unnamed" in `SKILL.md`,
`simple-path.md`, `full-path.md`, `investigation-path.md`, the agent
descriptions, `CLAUDE.md`, and `README.md`. State that with the teams flag
off, a name changes nothing. A teammate cannot spawn a teammate, so the
researcher's own lookups run one at a time. Each dispatch's report is read
from its idle notification, and the record file stays the durable copy where
one exists.

Run it. Read design §3, §15.20, §15.21, §15.89, and CLAUDE.md's "Constraints
that are easy to get wrong".

Check that no instruction file leaves an agent the project lead dispatches
unnamed, that the naming rule is stated once, and that a probe with the flag
on shows the spec critic's one-line verdict and a council batch read
correctly from idle notifications. An agent's own subagents — a researcher's
lookups, an IC's — stay unnamed; `SKILL.md`'s "Every dispatch is named" says
why.

Done when: no instruction file leaves an agent the project lead dispatches
unnamed, the naming rule is stated in one place, and a flag-on probe reads
both cases back correctly.

Read first: design §3, §15.20, §15.21, §15.89; CLAUDE.md "Constraints that
are easy to get wrong".

## T67 — The project lead session dominates run cost

Status: open
Depends on: nothing
Stage: 7 (design §15.98g)

Filed, not scheduled. On run 1 of `add-padcenter-helper-5b0b`, the Opus total
was $31.74 of the run's $32.87 — 277 messages, 35.8M cache-read tokens — but
$3.86 of that is the four headless skeptical-review sessions, so the project
lead session on its own is about $27.9, roughly 85% of the run; the ICs added
$1.13 more. The project lead session, not its dispatches, is where a run's
money goes.

Scope. Measure where the Opus tokens go: reference reads per step, repeated
file reads, or spinner-time thinking between tool calls. Propose the cut —
fewer or cached reference reads, or a lower band for a light- or simple-path
project lead.

Run it. Read a project lead's own transcript against `spend.py`'s per-message
breakdown for one delivered run.

Check that the measurement names which step or pattern the cache-read tokens
concentrate in.

Done when: the measurement exists and names a specific cut to try.

Read first: design §15.98g; `skills/project-lead/scripts/spend.py`.

## T68 — Move the skeptical review launch into scripts/

Status: open
Depends on: nothing
Stage: 7 (design §15.98b)

Filed, not scheduled. Five different launch shapes were typed across two
probe runs before the working one in `skeptical-review.md` was found. A
script removes the retyping and the chance of another broken shape.

Scope. A `crew-review.py` (or an equivalent shell script) under
`skills/project-lead/scripts/` takes the record directory, the round number,
the review worktree and the suite command, and writes `-result.json`,
`-result.stderr` and `-result.exit`, and records the session id, the way
`skeptical-review.md`'s "The default command" and "Record the review's
session id" say to. Depends on T59's fixed command, which this ticket wraps
rather than replaces.

Run it. Substitute the script for a hand-typed launch on one skeptical review
round.

Check that the script produces the same files, `-result.exit` included, in
the same shape, that a hand-typed launch does.

Done when: `skeptical-review.md` points at the script instead of stating the
command inline.

Read first: design §15.98b; `skeptical-review.md`.

## T69 — Open the PR ready for review

Status: open
Depends on: nothing
Stage: 7 (design §15.99)

A run opens a draft PR, and the principal marks it ready by hand. The
principal asked for a PR ready for review by default.

Scope. `simple-path.md`'s "End the run" drops `--draft` from `gh pr create`,
and passes it only when the charter or the principal asks for a draft. Every
"draft PR" that describes crew's output — the skill description, the
manifests, `CLAUDE.md`, `README.md`, the design — says a PR ready for review.
The deliverable state keeps the name `draft-pr-opened`.

Run it. Hand one goal to a project lead on the fixture repo, and one goal
that asks for a draft.

Check that the first PR opens ready for review and the second opens as a
draft, and that both deliverables record `draft-pr-opened`.

Done when: a run opens its PR ready for review unless the goal asks for a
draft.

Read first: design §15.99; `simple-path.md` "End the run".

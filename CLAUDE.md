# crew

`crew` is a Claude Code plugin: an autonomous project lead that takes one goal
to a reviewable draft PR and picks the cheapest model for each piece of work.
The repo root is the plugin root.

Almost every file here is markdown. Verifying a change is reading, not
running — there is no build, no test suite and no CI. The exceptions are the
two hooks and the three scripts under `skills/project-lead/scripts/`: they are
code, run against a seeded record (design §15.38, §15.50).

## Layout

| Path | What it is | What loads it |
|---|---|---|
| `.claude-plugin/plugin.json` | plugin manifest | the plugin loader |
| `.claude-plugin/marketplace.json` | marketplace entry | `/plugin marketplace add` |
| `agents/*.md` | definitions for dispatched agents | the dispatcher, at spawn time |
| `skills/project-lead/SKILL.md` | the `/crew:project-lead` entry point — the goal, the scouting, the size, the spec and the shape, a review step the principal replaced, then a route to one path file | its skill trigger |
| `skills/project-lead/references/*.md` | shared references, read with `Read` | whoever is pointed at one |
| `skills/project-lead/scripts/*.py` | `crew-record.py` writes one `state.json` field; `spend.py` prices a run from its transcripts; `crew-stats.py` reports cost, bands, fix rounds, councils, reviews, the review catch rate, the skipped steps and the steps the principal replaced over every record | the project lead, from Bash; a person runs `crew-stats.py` |
| `hooks/hooks.json`, `hooks/session-end.py`, `hooks/pre-compact.py` | `SessionEnd` marks a dead run interrupted; `PreCompact` logs a compaction into the run | the plugin loader, in every session |
| `docs/design.md` | the living spec | a person |
| `docs/tickets.md` | the build backlog, one ticket per hand-off | a session taking a ticket |
| `docs/implementation-plan.md`, `docs/stage-2-run/`, `docs/pr-body.md` | frozen build record | a person |
| `.github/pull_request_template.md` | the PR body skeleton | GitHub, when you open a PR |

A run's own output — charter, spec, plan, state, reports, reviews — never
lands in this repo. It goes to `<record-root>/<goal-slug>/`, where the root
is `$CREW_RECORD_ROOT` or, by default, `~/.claude/crew/`.

## Build state

Stages 0 through 7 are built: seven agents — the six workers and the
read-only `crew:scout` — ten references, both hooks and all four of
`/crew:project-lead`'s paths. The **simple path** runs one package on
one branch under one named subagent; the **full path** runs several packages
in worktrees under named IC teammates, with a merge per package and
`--resume` recovery. Both have run end to end against a real repo.
The **investigation path** takes a symptom to a diagnosis, then to a fix or to
a report ending; both endings have run, and it is `crew:researcher`'s only
caller, which no run has dispatched yet. The **light path** is the simple path
with no spec and no spec critic. Four light-path items have run to a draft PR,
and none promoted in place (§15.88, §15.91). A project lead stays in its
session after the hand-over: the run goes `delivered`, and `complete` only on
the ship word. One item has run the whole window (§15.92), which an
unexercised **skeptical review** opens. That window separates a **change
request**, one more package, from **findings**, which go to **patch mode**: a
package per group, one push, a reply per finding (§15.94d). Neither has run.

**Every run named above predates T58, T59 and T60**, which cut two review
steps, moved the last to after the hand-over and gave the window a patch mode.
Each is evidence for one step, not for the loop.

Two items in one repo take a checkout each: the project lead cuts its own when
another run holds the shared one, and `spend.py` prices every run from its own
sessions rather than from the checkout (§15.90).

T57 removed the tier above the project lead: the principal hands each goal
over itself (§15.95). Nothing in this checkout has run since.

`docs/design.md` §13 holds the build order and `docs/tickets.md` the backlog.
Never write about an unbuilt stage as if it runs, or about a built one as if
a run has exercised it.

## Authority

`docs/design.md` is the spec. Read the section you are changing before you
change behavior. §15 holds the open questions and the findings from the
stage-2 run; add a new finding there.

Each reference owns one subject and is canonical for it:

- `autonomy-contract.md` — how a question is routed, when a project lead
  escalates and to whom, and how a run's spend is counted.
- `simple-path.md` — the loop for one package: one named IC subagent, one
  branch in this checkout, no merge. It also owns the **light path**, the
  same loop with no spec, and the **delivered window** on every path.
- `full-path.md` — the loop for more than one package: worktrees, IC
  teammates, merges, promotion and recovery.
- `investigation-path.md` — the loop from a symptom to a diagnosis: the
  debugging checklist, the evidence files, and the two endings.
- `record-format.md` — the goal record: its `state.json`, `worktrees.json`
  and `decisions.md`. Every field, and every state transition.
- `band-rubric.md` — the model a package gets, and when to promote.
- `ic-contract.md` — what an IC may and may not do, and its report statuses.
- `review-output.md` — the shape every review reports its findings in.
- `skeptical-review.md` — the review of the finished diff, and when it runs.
- `writing-standard.md` — how an instruction file and a README are written.

A rule lives in exactly one file. Point at that file from anywhere else. A
second copy is worse than no copy, because nothing decides which copy wins.

## Writing rules

Read `skills/project-lead/references/writing-standard.md` before you draft or
edit any Claude instruction — a `CLAUDE.md`, a `.claude/rules/` file, a
`SKILL.md`, an agent definition, or a file under `references/`, this one
included. Check the draft against its `## Before you open the PR` checklist
before you commit. That checklist defines done.

Read its `## Writing for a person` section before you touch `README.md`, a PR
body or an issue. State the action; leave the reasoning in `docs/design.md`.
Design voice in the README is the drift that keeps coming back.
`.claude/rules/readme.md` owns the README's shape and says which change
updates which section, in the same PR.

Those prose rules are ASD-STE100 — Simplified Technical English. Apply them to
every file here, and to each commit message and PR body. Only the
container-choice check is limited to the standard's four container types.

## Constraints that are easy to get wrong

- A change to what the plugin loads — `agents/`, `skills/`, `hooks/`, or the
  manifests — bumps `version` in both `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`. Keep the two values equal. Nothing else
  bumps it: `docs/`, `README.md`, `CLAUDE.md` and `LICENSE` never reach a
  plugin user, so a bump for them says a release happened when none did.
- The hierarchy is project lead → ICs. Write **project lead** in full every
  time; the bare word `lead` names no tier here (design §15.19, §15.95).
- Every dispatch is named. `skills/project-lead/SKILL.md`'s "Every dispatch
  is named" owns the rule: the name shape, where the result is read, and
  what naming costs (design §3, §15.20b).
- Teammates are experimental and gated on
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. With the flag off, a named agent
  launches as a plain subagent, and the name changes nothing (design
  §15.20a).
- A teammate cannot spawn a teammate, and an in-process teammate's subagents
  are forced to the foreground. Any tier that must dispatch in parallel cannot
  itself be a teammate (design §15.21).
- A teammate built from an agent definition **appends** the body to its default
  system prompt, in both display modes, and neither applies `skills:`. The
  split-pane mode replaced the prompt when §15.20d was written and appends it on
  2.1.268, so write an agent body that survives both (design §15.20d, §15.89e).
- A dispatch's permission prompts surface in the project lead's session for a
  human to approve — `SKILL.md`'s "Every dispatch is named" owns the rule.
  Pre-approve what a run needs, or a no-prompt run stops on the first one
  (design §15.20, §15.12).
- Frontmatter `hooks` is ignored for teammates and banned for plugin agents.
  Crew's hooks ship in `hooks/hooks.json` (design §12, §13.1).
- A spawn-time `model` overrides an agent's frontmatter, and
  `reasoning_effort` cannot travel that way. `band-rubric.md` owns what
  follows from that (design §8, §12).
- No crew agent invokes a superpowers skill. Every superpowers process skill
  stops for a human, and removing that stop is the point of this plugin. Copy
  a checklist word for word instead, so it stays easy to re-sync (design §2,
  §14).
- Draw a diagram as text inside a fenced block, never as mermaid. Mermaid
  renders inconsistently across the places these files get read, and it
  degrades to nothing when it fails.
- `docs/implementation-plan.md` and `docs/stage-2-run/` are evidence from the
  first hand-driven run. Do not edit them, and do not repair their paths —
  they are relative to the larger plugin repo crew was built inside. Record
  what you learned from them in `docs/design.md` §15 instead.

## Communication

Report progress as you work. Name each decision as you make it. Say plainly
when something failed, or when you got it wrong. Never finish work silently —
a completed task with no reply reads as a stall.

Ask when a choice is genuinely the user's. Name the option you recommend.

## Workflow

- Branch, commit with a one-line message, open a draft PR. A human merges.
- Fill in `.github/pull_request_template.md` for every PR: a plain-language
  summary, the ticket link and the change type, then the agent context.
- Never hard wrap text you send to GitHub — `writing-standard.md` says why.
- Exercise a change against this checkout, never the installed copy:
  `claude --plugin-dir <path to this repo>`.
- Spawning a teammate needs no display mode: in-process is the default. Split
  panes are the opt-in: `--teammate-mode tmux` or `iterm2` (design §15.20c,
  §15.89d). Pass tmux to give each full-path IC a pane (design §15.93).
- Set `CLAUDE_CODE_ENABLE_PROMPT_SUGGESTION=false` for an experiment you drive
  in tmux. A suggestion lands in the input box unsent, and a session reading
  the pane cannot tell it from a person's typing (design §15.47).
- The `Skill` tool is auto-rejected in headless `claude -p`, so a probe that
  relies on invoking one passes vacuously (design §12).

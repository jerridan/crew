# crew

`crew` is a Claude Code plugin: an autonomous project lead that takes one goal
to a reviewable draft PR and picks the cheapest model for each piece of work.
The repo root is the plugin root.

Every file here is markdown. There is no source code, no build, no test suite,
and no CI. Correctness means an instruction a model follows, so verifying a
change is reading, not running.

## Layout

| Path | What it is | What loads it |
|---|---|---|
| `.claude-plugin/plugin.json` | plugin manifest | the plugin loader |
| `.claude-plugin/marketplace.json` | marketplace entry | `/plugin marketplace add` |
| `agents/*.md` | definitions for dispatched agents | the dispatcher, at spawn time |
| `skills/project-lead/SKILL.md` | the `/crew:project-lead` entry point — the simple-path loop | its skill trigger |
| `skills/project-lead/references/*.md` | shared references, read with `Read` | whoever is pointed at one |
| `docs/design.md` | the living spec | a person |
| `docs/tickets.md` | the build backlog, one ticket per hand-off | a session taking a ticket |
| `docs/implementation-plan.md`, `docs/stage-2-run/`, `docs/pr-body.md` | frozen build record | a person |
| `.github/pull_request_template.md` | the PR body skeleton | GitHub, when you open a PR |

A run's own output — charter, spec, plan, state, reports, reviews — never
lands in this repo. It goes to `~/.claude/crew/<goal-slug>/`.

## Build state

Stages 0 through 4 are built: six agents, five references, and
`/crew:project-lead`'s **simple path** — one goal, one deliverable, one
package, one unnamed subagent, from a goal string or a charter file to a
draft PR. That loop dispatches `crew:spec-critic`, `crew:ic` or
`crew:ic-instructions`, `crew:package-reviewer`, and
`crew:deliverable-reviewer`.

Nothing dispatches `crew:split-critic` yet — the simple path has one
package, so it is skipped. The full path (worktrees, territories,
teammates), the council, and the hooks are stages 5 and 6, and none of them
exist. `docs/design.md` §13 holds the build order, and
`docs/tickets.md` holds the backlog. Never write about an unbuilt stage as if
it runs.

## Authority

`docs/design.md` is the spec. Read the section you are changing before you
change behavior. §15 holds the open questions and the findings from the
stage-2 run; add a new finding there.

Each reference owns one subject and is canonical for it:

- `autonomy-contract.md` — how a question is routed, when the project lead
  escalates and to whom, and how a run's spend is counted.
- `record-format.md` — the record directory, every `state.json`,
  `worktrees.json` and `decisions.md` field, and every state transition.
- `band-rubric.md` — which model a package or a council gets, and when to
  promote.
- `ic-contract.md` — what an IC may and may not do, and its report statuses.
- `writing-standard.md` — how every instruction file here is written.

A rule lives in exactly one file. Point at that file from anywhere else. A
second copy is worse than no copy, because nothing decides which copy wins.

## Writing rules

Read `skills/project-lead/references/writing-standard.md` before you draft any
Claude instruction — a `CLAUDE.md`, a `.claude/rules/` file, a `SKILL.md`, or
an agent definition, this file included. Check the draft against its checklist
under `## Before you open the PR` before you commit. That checklist defines
done.

Those prose rules are ASD-STE100 — Simplified Technical English. Apply them to
every file in this repo, and to each commit message and PR body. Only the
container-choice check is limited to the four container types the standard
names.

## Constraints that are easy to get wrong

- A change to what the plugin loads — `agents/`, `skills/`, `hooks/`, or the
  manifests — bumps `version` in both `.claude-plugin/plugin.json` and
  `.claude-plugin/marketplace.json`. Keep the two values equal. Nothing else
  bumps it: `docs/`, `README.md`, `CLAUDE.md` and `LICENSE` never reach a
  plugin user, so a bump for them says a release happened when none did.
- The hierarchy is lead → project leads → ICs. `lead` names the tier above
  this plugin, which does not exist yet, so what crew builds is a **project
  lead** — write it in full, and leave the bare word `lead` for that future
  tier (design §15.19).
- Only ICs are named agents. A named agent becomes a teammate, and a teammate
  returns no parseable tool result — just a final answer in its idle
  notification. Anything whose result the dispatcher must read and act on
  stays unnamed (design §3, §15.20b).
- Teammates are experimental and gated on
  `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1`. With the flag off, a named agent
  launches as a plain subagent, so the naming rule above holds only when it is
  on (design §15.20a).
- A teammate cannot spawn a teammate, and an in-process teammate's subagents
  are forced to the foreground. Any tier that must dispatch in parallel cannot
  itself be a teammate (design §15.21).
- A teammate built from an agent definition reads that definition differently
  by display mode: in-process **appends** the body to its default system
  prompt, split-pane **replaces** it, and neither applies `skills:`. Write an
  agent body that survives both (design §15.20d).
- A teammate's permission prompts surface in the project lead's session for a
  human to approve. Pre-approve what a run needs, or a no-prompt run stops on
  the first one (design §15.20, §15.12).
- Frontmatter `hooks` is ignored for teammates and banned for plugin agents.
  Crew's hooks ship in `hooks/hooks.json`, in stage 5 (design §12, §13.1).
- A spawn-time `model` overrides an agent's frontmatter `model`.
  `reasoning_effort` is frontmatter only, and a teammate inherits the project
  lead's effort. That is why a band sets model and never effort (design §8,
  §12).
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
  summary, the ticket link and the change type for a person, then the agent
  context an AI reviewer needs.
- Do not hard wrap a PR body, an issue body, or a comment on GitHub. Each
  paragraph and list item goes on one long line. GitHub renders a single
  newline as a line break, so a wrapped body renders as a narrow column. The
  files in this repo stay hard wrapped; only the text you send to GitHub does
  not.
- Exercise a change against this checkout, never the installed copy:
  `claude --plugin-dir <path to this repo>`.
- Spawning a teammate needs a working display mode: iTerm2 with its Python API
  enabled, a session inside tmux, or `teammateMode: "in-process"`.
- The `Skill` tool is auto-rejected in headless `claude -p`. A `-p` run can
  confirm a skill is listed, but it cannot invoke one, so a probe that relies
  on invocation passes vacuously (design §12).

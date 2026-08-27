# Plan: crew-readme

## Standard route

The shared instructions-writer skill invocation returned an error with no
standard text (`Execute skill: instructions-writer`, no body). Per
contract, I fell back to reading
the external plugin's `instructions-writer/SKILL.md` directly from the
lead-given path. I can quote the checklist under `## Before you open the
PR`:

- The instruction sits in the cheapest container that still reaches its
  reader.
- Nothing repeats or contradicts the standard or a sibling file.
- Reference depth and per-link annotations match `references/standard.md`.
- Sizes and table-of-contents thresholds match `references/standard.md`.
- The prose passes ASD-STE100: short sentences, active voice, one
  instruction per sentence.

I did not read `references/standard.md` or `references/evidence.md`
separately — the SKILL.md body itself states the container-choice table,
the "write for what the reader already has" section, and the checklist
above, which is what a README package needs. A README is not one of the
four containers this skill governs (CLAUDE.md, rule, SKILL.md, agent
definition), so the container-choice table does not select a container for
it — the brief already fixed the container (`plugins/crew/README.md`).
What applies is the general craft standard: ASD-STE100, conciseness,
revise-down, and the final checklist.

## Content plan

Single file: `plugins/crew/README.md`. Sections, each mapped to the brief's
five required items:

1. **Title + one-paragraph "what crew does"** — autonomous project lead,
   one goal to a reviewable draft PR, no human in the loop per stage,
   cheapest model per unit of work. Cite nothing beyond this; do not restate
   scope boundaries beyond a short "does not merge for you" pointer, since
   the brief warns against overselling scope during active build-out.
2. **Roles table** — 9 rows (lead, scout, advocate, spec critic,
   decomposition critic, IC, instruction IC, package reviewer, deliverable
   reviewer), each with a one-line "what it does" restated for a README
   reader (not copied verbatim from design §3's table, which has
   mechanism/model/lifetime columns aimed at a build audience).
3. **Getting started** — the launch command `/crew:lead <goal>` as its own
   short subsection.
4. **Prerequisite** — a clearly labeled "Before you run this" callout: one
   of iTerm2 (with Python API enabled), tmux, or `teammateMode:
   "in-process"` is required, because ICs run as named teammates and
   teammate spawning needs a working display mode. State the failure mode
   (dispatching an IC fails) so it reads as actionable, not trivia.
5. **Credit** — short paragraph: process spine adapted from `superpowers`
   (spec, plan, critique, TDD, review, integrate), several checklists
   copied verbatim to stay easy to re-sync, and crew never invokes a
   superpowers skill directly because every superpowers process skill
   stops for a human, which crew removes.

Also note build status briefly (still under active build-out, stage 2 of a
staged plan) so a reader does not assume full autonomy already ships, per
brief's scope-oversell warning — one sentence, not a restatement of design
§13.

## Steps

1. Draft `plugins/crew/README.md` covering the five items above.
2. Revise down — read cold, expect to cut roughly a third, tighten to
   ASD-STE100.
3. Self-check against the acceptance criterion's 6 items and the
   instructions-writer checklist (5 items above).
4. Commit with a one-liner message.
5. Self-review per contract, write report.

Single commit expected (one file, one logical step) — I will still commit
once the draft passes review rather than mid-draft, since there's no
intermediate "green" state for a single new file the way there is for a
multi-step checklist. If the checklist review triggers real revisions, I
will treat "draft passes checklist" as the one green step and commit then.

## Assumption

No live SendMessage channel back to a lead is confirmed yet in this
environment; I will send the plan-gate message and, if there is no live
lead process to receive it, proceed after a reasonable wait is not
possible — I will state this explicitly in my report rather than stalling
indefinitely.

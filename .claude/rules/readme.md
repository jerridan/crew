---
paths:
  - README.md
  - skills/**
  - hooks/**
  - .claude-plugin/**
---

# The README

`README.md` is for a person who wants to know what crew is and how to use it.
It is not the design doc. `writing-standard.md`'s "Writing for a person" owns
its prose rules; this file owns its shape, and when a change must touch it.

## The section order is fixed

Description, then Install, then Run your goals through a lead, then Run one
goal in your session, then What a run needs. Everything about the design
comes after those five. A reader who only wants to run crew never scrolls
past them.

`/crew:lead` is the main entry point, and it comes first everywhere: the
entry-point table, the usage sections, the Status table and the Roles table.
`/crew:project-lead` is what the lead runs for each goal, and the README says
so.

Keep the rest in this order: How it works, Models, The record, Status, Roles,
Help and contributing, Credit, Reading the docs, License. Add a section only
when no existing one can hold the content.

## A change that a user can see updates the README in the same PR

| The change | The section it lands in |
|---|---|
| A new or renamed command, or a new argument to one | Run your goals through a lead, or Run one goal in your session |
| A new flag, environment variable or launch requirement | What a run needs, and the command it belongs to |
| A new agent or role | Roles, and Models |
| A new path, or a change to which path a goal takes | The path table under Run one goal in your session |
| A new file in the record | The record |
| A stage lands, or a run first exercises a built piece | Status |
| The reason for any of the above | `docs/design.md`, cited by section. Never the README. |

The command in the README is the command in the file that owns it:
`session-launch.md` for launch flags, each `SKILL.md` for its arguments. When
the owner changes, the README changes.

## Every example is one a person can paste

Show the command, the argument or the message a person types, in a code
block, and say what happens. Show no internal command: `crew-record.py` and
`crew-portfolio.py` belong to the skills, and `crew-stats.py` is the one
script a person runs.

## Before the PR

Run `writing-standard.md`'s "Keep the status true" grep, and read every hit
in the Status table.

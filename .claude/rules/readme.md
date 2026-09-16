---
paths:
  - README.md
  - skills/**
  - hooks/**
  - .claude-plugin/**
---

# The README

`README.md` is for a person who wants to know what crew is and how to use it.
It is not the design doc and not the build record. `writing-standard.md`'s
"Writing for a person" owns its prose rules; this file owns its shape, and
when a change must touch it.

## The section order is fixed

Description, then Install, then Run one goal in your session, then What a run
needs. Everything about the design comes after those four. A reader who only
wants to run crew never scrolls past them.

`/crew:project-lead` is the entry point, and it comes first everywhere: the
entry-point table, the usage section and the Roles table.

Keep the rest in this order: How it works, Models, The record, Roles, Help
and contributing, Credit, License. Add a section only when no existing one
can hold the content.

## The README cites nothing

No `design §N` and no `§15` anywhere in it. "Writing for a person" allows a
citation or nothing; the README picks nothing, because a person reading it
does not have the design doc open. The one pointer to `docs/design.md` is the
"to learn more" sentence under Help and contributing.

The README carries no build record either: no table of what is built, and no
account of which run exercised what. One sentence under the entry-point table
says crew is experimental. `docs/design.md` §13 and §15 hold the rest.

## A change that a user can see updates the README in the same PR

| The change | The section it lands in |
|---|---|
| A new or renamed command, or a new argument to one | Run one goal in your session |
| A new flag, environment variable or launch requirement | What a run needs, and the command it belongs to |
| A new agent or role | Roles, and Models |
| A new path, or a change to which path a goal takes | The path table under Run one goal in your session |
| A new file in the record | The record |
| The reason for any of the above | `docs/design.md`. Never the README. |

The command in the README is the command in the file that owns it:
`SKILL.md` for its arguments, and `simple-path.md` or `full-path.md` for a
launch requirement. When the owner changes, the README changes.

## Every example is one a person can paste

Show the command, the argument or the message a person types, in a code
block, and say what happens. Show no internal command: `crew-record.py`
belongs to the skill, and `crew-stats.py` is the one script a person runs.

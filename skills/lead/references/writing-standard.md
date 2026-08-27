# Writing standard

Read this before drafting or editing a `CLAUDE.md`, a `.claude/rules/`
file, a `SKILL.md`, or an agent definition. No test can run against
prose. This standard, and its final checklist, is what "done" means for
a package like that.

## Pick the container

Route content to the cheapest container that still reaches its reader.
Each container has a different cost to the reader:

- **A project `CLAUDE.md`** loads into every session in the project. It
  is the most expensive place to put anything — pay for it only with
  content every session needs.
- **A `.claude/rules/` file** loads only when its path scope matches the
  current work. Use it for a rule that applies to one area of a repo,
  not the whole project.
- **A `SKILL.md`** loads on demand, when its `description` matches what
  the user or the model is doing. Use it for a workflow invoked
  occasionally, not read on every turn.
- **An agent definition** is the system prompt for one dispatched agent.
  It never reaches the calling session — only the dispatched agent sees
  it. Put in it only what that one job needs.

A README, and reader-facing prose in general, is none of these four. A
person opens it directly; nothing loads it automatically. Recommended
routing: hold it to this standard's prose rules — write for the reader,
revise down, ASD-STE100 — but skip the container-choice check below,
since no cheaper container exists to route it to. This routing is not
settled. Flag it as open when you hit it.

## Write for what the reader already has

The reader is a capable model, not a novice. Do not explain git, npm, or
any tool a capable model already knows. Give it only what it cannot
infer for itself: this project's own commands, this project's own
conventions, and the reason behind a rule that would look arbitrary
without one.

Test every line against one question: would deleting it cause a
mistake? If the answer is no, delete it.

## Frontmatter

Frontmatter keys are not documentation. They decide whether the file
loads, how it gets found, and what it is allowed to do.

- **`description`** on a skill is a trigger, not a summary. State what
  the skill does and when to reach for it, in words a person would
  actually type. A description that only summarizes content never
  fires at the right moment.
- **`description`** on an agent is selection text a dispatcher reads
  before it sees the agent's body. Write it so the dispatcher picks this
  agent over a similar one without reading further.
- **`tools`** (or `allowed-tools`) is a capability boundary, not a
  formality. List only what the job needs.
- **`model`** and **`reasoning_effort`** are cost knobs. Pick the
  cheapest pair that still does the job.

Keep every key concrete — a name, a trigger phrase, or a file type beats
an adjective.

## Revise down

Expect to cut about a third of a first draft. Cut, in this order:

1. Restated context the reader already gets from its own brief or tools.
2. Hedging — "generally", "in most cases", "you may want to". State the
   rule, or drop it.
3. Anything the reader already knows (see the section above).
4. A rule stated twice. Keep it in the one file that owns it.

## Before you open the PR

Each item is a pass/fail check. A "no" on any one means the package is
not done.

1. **Container.** Every new instruction sits in the cheapest container
   that still reaches its reader — nothing landed in a `CLAUDE.md` that
   a rule file or a skill would have reached just as well.
2. **No duplication.** No rule in this change repeats or contradicts a
   rule already stated in a sibling file. Grep the change's key terms
   against the package's other files before you finish.
3. **Reference depth.** A reference file sits at most one link away from
   the file that points to it. No reference file points to a second
   reference file.
4. **Size.** A `CLAUDE.md` or a `.claude/rules/` file is at most 150
   lines. A `SKILL.md` body, not counting `references/`, is at most 200
   lines. Over either limit, move the excess into a reference file.
5. **ASD-STE100 prose.** Every sentence is short, uses active voice, and
   carries exactly one instruction. A sentence you must reread to parse
   is too long — split it.

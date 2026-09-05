# Writing standard

Read this before drafting or editing a `CLAUDE.md`, a `.claude/rules/` file, a
`SKILL.md`, an agent definition, or a reference beside this one under
`skills/project-lead/references/` — and its `## Writing for a person` section
before a `README.md`, a PR body, an issue or a comment. No test can run against
prose. This standard, and its final checklist, is what "done" means for a
package like that.

A reference is an instruction file like any other. It carries every rule here
except the container choice, which is already settled by the time content
lands in one.

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
person opens it directly; nothing loads it automatically. Hold it to this
standard's prose rules, skip the container-choice check — no cheaper
container exists to route it to — and add the section below. It is a fifth
container type, owned by `crew:ic-instructions` alongside the four above
(design §15.17, §3.1).

## Writing for a person

A README is read by a human who is scanning, not by a model that will act
on it. That changes what belongs in it.

- **State the action, not the mechanism.** Say what to set, install or run.
  The reason it works that way belongs in `docs/design.md`.
- **Never explain a design decision.** "Crew cannot detect this, because a
  session cannot read its own permission mode" is a design fact. Cite the
  design section instead, or say nothing.
- **Prefer a table** for anything with a repeating shape: requirements,
  state, roles, options. A reader finds a row faster than a paragraph.
- **No bolded lead-in followed by its own explanation.** Two or three of
  those in a row is design voice, and it is the drift to watch for.
- **Keep the status true.** A README that calls a built thing a stub is
  worse than one that says nothing. `## Keep the status true` owns this rule.

The same rules hold for a PR body, an issue and a comment.

**Never hard wrap text you send to GitHub.** Each paragraph and list item
goes on one long line. GitHub renders a single newline as a line break, so a
wrapped body renders as a narrow column. Files in this repo stay hard
wrapped; only the text you send to GitHub does not.

## Keep the status true

Every sentence that says what is built goes stale when a stage lands. The
session that lands the stage is the one least likely to notice it (design
§15.48, §15.49, §15.52). Reading does not catch this. A grep does.

The `pattern` line below is the vocabulary that dates. It is the canonical
list. An instruction file that needs the vocabulary points here; it never
copies the terms. Run this block before the change lands, with `<repo>` the
absolute path to the checkout and `<base>` the branch's base ref:

```
pattern='not built|unbuilt|no run has|no session has|nothing dispatches|unexercised|not yet|stub|does not exist yet|deferred'

# every change: the lines this change adds
git -C <repo> diff <base>...HEAD | grep -inE "^\+.*($pattern)"

# a change that lands a stage: the whole repo as well
git -C <repo> grep -inE "$pattern"
```

The second grep exists because a file the change never touched can still
claim that stage is unbuilt. Run it only when the change lands a stage.

Read every hit. Fix a hit that this change makes false. Leave a hit that is
still true.

`simple-path.md`'s "Integrate" says who runs this sweep, and when.

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
3. **Reference depth.** No step may require reading a third file to
   finish it. A reference **naming** the file that owns a rule is not a
   hop — that is how a rule keeps one owner — but a reference that sends
   you to a second file to learn what to do next is.
4. **Size.** A `CLAUDE.md` or a `.claude/rules/` file is at most 150
   lines. A `SKILL.md` body targets 200 lines and never passes the 500
   the skill guidance sets. A file under `references/` has no cap,
   because a reference loads only when a step sends the reader to it.
   Count every line the file holds — blank lines included — from the
   line after the closing `---` of the frontmatter to the end. Over a
   limit, move the excess into a reference file.
5. **ASD-STE100 prose.** Every sentence is short, uses active voice, and
   carries exactly one instruction. A sentence you must reread to parse
   is too long — split it.

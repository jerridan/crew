<!-- Write every paragraph and list item on ONE long line. CLAUDE.md, under Workflow, owns this rule and says why. -->

## Summary

<!-- Two to five sentences of plain language, for a person who has not read the ticket or the design. Say what now exists that did not before, and what problem made it necessary. No file paths, no section numbers, no agent names the reader would have to look up. -->

<!-- Ticket: link the exact ticket by its heading anchor, with a full URL — `[T1 — Split critic](https://github.com/jerridan/crew/blob/main/docs/tickets.md#t1--split-critic-and-the-planmd-format)`. A relative link does not resolve in a PR body; GitHub rewrites those only inside repository files. For the anchor, lowercase the heading, drop the punctuation, and turn each space into a hyphen. Write N/A if this PR answers no ticket. -->
<!-- Type: one of Bug fix, New feature, or Refactor. -->

**Ticket:**
**Type:**

---

## Agent context

<!-- Everything below is written for an AI session pointed at this PR with nothing else loaded — a reviewer, or a later session that picks the work up. Be literal. Name paths, not descriptions of paths. -->

### Authority

<!-- The docs/design.md sections that govern this change. The reference file under skills/project-lead/references/ that owns each rule the change touches. -->

### What changed, by file

<!-- One line per file: the path, then what it now does that it did not do before. Include renames and deletions. -->

### Constraints that applied

<!-- The CLAUDE.md and design constraints this change had to satisfy, and how each one is satisfied. Name any constraint you deliberately did not satisfy, and why. -->

### How this was verified

<!-- This repo has no tests. Correctness means an instruction a model follows, so verifying a change is reading it, or hand-dispatching the agent the change defines. State what you read or ran, and what came back. A claim with no evidence is not verification. -->

### Known gaps

<!-- What is unproven, unfinished, or deferred to a later ticket. Write "None" if there are none. -->

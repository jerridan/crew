# IC contract

The project lead injects this file into every IC spawn prompt, along with your
record root — an absolute path outside your worktree — and your package id.
You inherit no conversation history. This file, your brief, and those two
values are everything you know about how to behave.

## What you may not do

### Files and git

- Never run `git reset --hard`, `git checkout --`, `git clean`, or `git
  stash`. Uncommitted work exists in exactly one place, and each of these
  destroys it.
- Never weaken, skip, or delete a test to reach green, and never commit with
  `--no-verify`. If the acceptance test looks wrong, report it and stop — do
  not edit it.
- Do not write `state.json`, `plan.md`, `worktrees.json`, `decisions.md`, or
  any other package's file under `reports/` or `plans/`.
- Edit only the files in your file set, plus two exceptions: your plan and
  your report (see below). Touch no other file, in your worktree or in the
  record.
- Commit only to your own branch, only in your own worktree. Do not merge,
  rebase, switch branches, run a worktree command, push, pull, or open a
  pull request.
- Do not edit a shared file — a version manifest, lockfile, barrel or
  `index` file, or shared config — even when your work seems to need it.
  Report it to the project lead instead.
- Read and write nothing outside your own worktree, except your plan and
  your report in the record.

### Scope

- Do not renegotiate your scope. If your scope looks wrong, ask the project lead
  (see Questions, below). Do not act on your own judgment instead.
- Implement your interface contract's `produces` signatures exactly as
  given. If one looks wrong, ask the project lead — do not change it yourself.

### Subagents

- Do not spawn another implementer, and do not spawn a reviewer.
- You may spawn `Explore` for a read-only lookup, and no other agent type.
  It runs in the foreground, so it blocks you and costs wall-clock time. Use
  it only when you need an answer you cannot find yourself.

## The worktree rule

```
The shell working directory resets after EVERY Bash call. `cd` holds only
within one invocation. Every command you run must carry its own
`cd <your-worktree> &&` prefix. A command without it runs against the wrong
checkout and reports no error.
```

## The plan gate

Before you write any code, write your implementation plan to
`<record-root>/plans/<id>.md` — this is your `plan_path`. `<id>` is your
package's id; `<record-root>` is the path the project lead gave you at spawn
time, not your worktree. This path is absolute. Use it as given — never `cd`
into it and never resolve it against your worktree. Then stop and wait for the
project lead's go-ahead by message — this is an expected pause, not an idle to
fix. Do not start implementing before the project lead responds.

## Commit discipline

Commit after every green step — a passing test for a code package, or the
next completed step of your checklist for an instruction package. This
bounds crash loss to one increment.

## When you are done

The project lead gives you an acceptance criterion at spawn time. Run it. It must
pass — that is your only definition of done. Do not report `DONE`, and do
not stop, before it passes.

## Questions

You will sometimes hit a question this contract and your brief do not
answer. When you do:

1. `SendMessage` the project lead. Never message the human — you have no
   channel to the human, and the project lead is the one who decides whether
   to escalate.
2. Do not wait for the reply. A message to a busy project lead sits until it
   is between actions, so waiting turns one question into a stalled worktree.
3. Prefer to proceed under a stated assumption. Name the assumption in your
   report.
4. If you cannot proceed under any assumption, and your territory has
   another package that does not depend on the answer, work that package
   next instead of stopping.
5. Stop only when the question blocks your whole current package and you
   cannot write any code without an answer. Never go idle with no report on
   disk — before you stop, write your report with status `NEEDS_CONTEXT` or
   `BLOCKED`.

## Report status

Your report carries exactly one of these four statuses. Each has a defined
meaning and a defined project lead response — pick the one that matches your
actual state, not the one that sounds best.

| Status | Meaning | What the project lead does |
|---|---|---|
| `DONE` | You finished the package with no reservations. | Verifies your work against git, then sends it to package review. |
| `DONE_WITH_CONCERNS` | You finished, but you have doubts worth flagging. | Reads your concerns first. Resolves any correctness or scope concern before review continues. Notes a plain observation and proceeds to review. |
| `NEEDS_CONTEXT` | You are missing information and the work is not complete. | Supplies the missing information and re-dispatches you. This differs from the Questions protocol above, which is for a question you can work around — use `NEEDS_CONTEXT` only when you cannot continue at all. |
| `BLOCKED` | You cannot complete the package as assigned. | Promotes the package one band up (`band-rubric.md`), or stops the run at the spend or fix-round breaker. |

## Report contract

Write your report to `<record-root>/reports/<id>.md`, the same
`<record-root>` and `<id>` as your plan — this is your `report_path`. This
path is absolute. Use it as given — never `cd` into it and never resolve it
against your worktree. Include:

- Your status, one of the four above.
- The commits you made.
- Every assumption you took, from the Questions protocol.
- Every question you raised, and how you resolved it or why it is still
  open.

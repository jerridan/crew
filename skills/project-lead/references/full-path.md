# Full path

This file owns the loop for a deliverable with more than one package
(design §9.2). `SKILL.md` runs steps 1 to 5 first, then sends you here in
place of its steps 6 to 14.

The simple path stays in `SKILL.md`. Nothing here applies to it.

This file runs **one** deliverable. Deliverables run sequentially and
`split.md` carries `Depends on` to order them, but no loop reads it yet, so a
goal needing two deliverables is escalation trigger 8, not a bigger split.

## What changes

| | Simple path | Full path |
|---|---|---|
| The IC | one unnamed subagent | one **named** teammate per territory |
| Where it works | this checkout | its own worktree and branch |
| The plan gate | two dispatches | one dispatch, then a message |
| Its report | a tool result you read | a file in the record, plus an idle notification |
| Integration | nothing merges | one squash merge per package |
| The split critic | skipped | runs before any IC is dispatched |

An IC is named here because a teammate is a named agent. Every other agent
in a run stays unnamed, because you must read its result (design §3,
§15.20b).

## 0. Check the launch conditions

Three you can check yourself. Check them before you write the split, and
escalate on any that fails — none can be fixed mid-run.

1. `CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS=1` is set. With the flag off, a
   named agent launches as a plain subagent and every rule here is wrong.
2. This session is **not** worktree-isolated. An isolated session cannot run
   `git -C` against any other worktree, which is the whole verification step
   (design §15.10, §15.23f).
3. A display mode works: iTerm2 with its Python API, a session inside tmux,
   or `teammateMode: "in-process"`.

State which condition failed. Do not start the run and discover it later.

The fourth condition is **not yours to check**: nothing in the run may stop
for a human. A teammate's permission prompts surface in your session (design
§15.12, §15.20), so one un-granted command stalls the whole run. A session
cannot read its own permission mode, so you cannot verify this in advance —
the README names it as a launch requirement and the principal owns it. You
may not widen it yourself either, because settings are configuration.

What you do instead is fail fast on it. If your first dispatch stalls waiting
for an approval, stop there and escalate as an `environment` block. Do not
spawn the rest of the territories first; one stalled dispatch is a cheap
lesson, and four is a wasted run.

## 1. Write the split

Write `split.md` in `record-format.md`'s format: one deliverable, its
packages grouped into territories. One IC owns one territory and works its
packages in the listed order. Mirror every field into `state.json`'s
`packages[]`.

## 2. Have the split reviewed

Dispatch `crew:split-critic`, unnamed, with `split.md`, `spec.md`, the repo
path, and `review-output.md` whole. Write its findings to
`reviews/<deliverable-id>-split-critic-r<n>.md`, `<n>` being one more than
the highest already on disk under that name.

Adjudicate as `SKILL.md` step 4 does. A failed invariant is not a style
note — fix the split and dispatch again. Three re-splits is the cap;
escalate at it.

## 3. Create the branch and the worktrees

Branch from the current head:
`git -C <repo> switch -c crew/<goal-slug>/<deliverable-id>`. Write the
`deliverables[]` entry now — `id`, branch, the head sha as `base`,
`state: pending`, `pr_url: null`.

Then one worktree per territory, all branching from that same head, so
integration is a merge and never a rebase (design §9.3):

```
git -C <repo> worktree add <worktree-root>/<territory-slug> -b crew/<goal-slug>/<territory-slug>
```

`<worktree-root>` is `<record-root>/worktrees` — **outside the target repo**.
A repo-local root looks tidy and breaks the suite: a test runner that globs,
which is the common case, collects every worktree's tests as well as the
repo's own, and the run then measures the wrong tree (design §15.35b). Put
the root inside the repo only when you have a reason, and record it.

Write `worktrees.json` now: the IC's name, the absolute worktree path, its
branch, this session's id, and `orphaned: false`. Set every package's
`ic_name` to the name of the IC that owns its territory. Nothing else maps a
package back to the worktree that must verify it.

Name an IC `ic-<territory-slug>`.

## 4. Spawn the ICs

Spawn one **named** teammate per territory, at the band of the package it
starts on: `crew:ic` for code, `crew:ic-instructions` for a `CLAUDE.md`, a
`.claude/rules/` file, a `SKILL.md` or an agent definition.

Pass the band's model at spawn time. A spawn-time `model` overrides the
agent's frontmatter, and effort is inherited and cannot be set per teammate
(design §12), which is why a band is model only.

A teammate inherits no conversation history, so the spawn prompt carries all
of: `ic-contract.md`'s full text, the brief, the file set, **the absolute
worktree path**, the interface contract, the acceptance criterion, the
global constraints section, and the package id.

It also carries the record root, as an absolute path. An interactive
teammate can write there (design §15.31b), so a full-path IC writes
`plans/<id>.md` and `reports/<id>.md` itself. If a write is denied anyway,
`ic-contract.md` makes the IC's final message its plan or its report, and
that message reaches you in its idle notification. Transcribe it, and say in
the file that you transcribed it.

Write the agent body to survive both display modes: in-process **appends**
an agent definition to the default system prompt and split-pane
**replaces** it, and neither applies `skills:` (design §15.20d). That is why
the contract is injected into the prompt and not linked.

Set the package and its deliverable `in-flight` at the first spawn, and write
that package's `base`: the worktree's head sha right now. For a territory's
first package that equals the deliverable's `base`.

## 5. The plan gate

A teammate has a message channel, so the gate is one dispatch and a reply —
not the simple path's two dispatches.

The IC writes `plans/<id>.md` and waits. Read it, then approve it or send it
back with what to change. `SendMessage` the IC its go-ahead, and set
`plan_approved_at`.

While `plans/<id>.md` exists and `plan_approved_at` is `null`, that IC's
idle is an expected pause and not a fault (design §15.8).

## 6. Verify before you believe

Read `reports/<id>.md`, then treat it as a claim and never as evidence. The
evidence is `git -C <worktree> log <package-base>..HEAD` and
`git -C <worktree> diff <package-base>..HEAD`.

`<package-base>` is that package's own `base`, not the deliverable's. A
territory works its packages in sequence in one worktree, so a range from the
deliverable base carries the previous packages' files too, and every package
after the first would be failed for scope drift it did not cause.

Always `git -C <worktree>`. Never `cd <worktree> && git ...` — the harness
denies any command that changes directory before it runs git, allow rule or
not (design §15.23b).

Check three things, every time:

- The diff's file list matches the declared file set. A file outside it is
  scope drift.
- The commits are on the IC's own branch, in the IC's own worktree. A commit
  anywhere else means the IC wandered, and nothing else detects that.
- The acceptance criterion passes on a fresh run you performed yourself.

A `BLOCKED` report names its cause, and `band-rubric.md`'s promotion rules
say what each cause earns. Committing on a blocked IC's behalf is a normal
outcome here, not a failure (design §15.12).

## 7. Review the package

Write the diff to `diffs/<id>-r<n>.patch` so it never enters your context:

```
git -C <worktree> diff <package-base>..HEAD > <record-root>/diffs/<id>-r<n>.patch
```

An instruction package gets its acceptance checklist file instead.

Dispatch `crew:package-reviewer`, unnamed, with all five inputs it requires:
the package's record entry (`file_set`, `interface_contract`,
`acceptance_criterion`), the worktree path, the IC's report, the diff or
checklist path, and the brief. Inject `review-output.md` whole.

Write its findings to `reviews/<id>-package-review-r<n>.md`, `<n>` being
`fix_rounds_used`.

## 8. Fix rounds

Run a round only on `Verdict: fix round needed`. Five is the cap.

- **Rounds 1 to 3** message the same IC. It keeps its context, which is the
  point of a teammate.
- **Rounds 4 and 5** stand the IC down, then spawn a fresh one **one band
  up**. A fresh IC holds no context, so its prompt describes what is already
  committed — `git -C <worktree> log --oneline` plus `git -C <worktree> diff
  --stat` — and which findings it must fix. A `deep` package cannot promote,
  so a `deep` package reaching round 4 escalates instead: respawn it at
  `deep` only if the principal says to (`band-rubric.md`).
- **At the cap**, fix the package yourself, or park it as `abandoned` with
  your reasoning recorded. At the top band, escalate instead.

**Increment `fix_rounds_used` and write `state.json` first**, before the round
runs. Steps 6 and 7 name `diffs/<id>-r<n>.patch` and
`reviews/<id>-package-review-r<n>.md` from that counter, so incrementing
afterwards makes round 1 overwrite round 0's diff and review — the two files
that are a reviewer's only audit trail.

Then the round goes back through steps 6 and 7. A fix nobody re-reviewed is a
claim. Leave this step only on `Verdict: accepted`. Log every promotion into
`band_history` with its predicted band, actual band, and cause.

Then send the IC its next package in the same territory, and return to step
5. An IC works its packages in the order `split.md` lists them. Write the new
package's `base` as you send it — the worktree head as it stands now, which
is the accepted package's last commit. That is what keeps the next review
diff to the next package's own work.

## 9. Integrate

Merge one package at a time, into the deliverable branch, as each package is
accepted rather than once per territory:

```
git -C <repo> cherry-pick -n <package-base>..<package-head>
git -C <repo> commit -m "<package one-liner>"
<run the suite>
```

Apply the package's own commit range, never `merge --squash` of the territory
branch. That branch holds every package the territory has finished, so a
branch-level squash collapses them into one commit and one suite run, which
loses the per-package attribution the next two paragraphs promise (design
§15.37b).

**Run the suite after each merge, not after all of them.** A failure is then
attributable to one package with no bisect. Read the output yourself. A
green run only proves the tree it ran on.

One squashed commit per package gives a reviewer a narrative to read, and
the IC's per-green-step commits stay on its own branch, which is what makes
a resume safe.

Mark each package `integrated` as its merge lands and its suite run passes.

Textual conflicts should be impossible — disjoint file sets leave git
nothing to conflict on, and you own every shared file. What remains is the
semantic conflict, and the per-merge suite run is what catches it.

Then edit the shared files yourself. Read the target repo's own instructions
for which files must change together, and keep the values they require equal.
Crew's own two-manifest version rule is crew's, not every repo's — a repo that
bumps at release wants no bump here at all. Commit them.

## 10. Review the deliverable

**Write the diff again now**, to `diffs/<deliverable-id>-final.patch`. Step
7's diffs predate the fix rounds and
every shared-file edit you just made, and those edits are exactly what the
next reviewer's shared-file check exists to read (design §15.24).

Dispatch `crew:deliverable-reviewer`, unnamed, with `spec.md`, `split.md`,
the repo path and base ref, the fresh diff path, every accepted package
review, and `review-output.md` whole. Four of its seven checks read the
record rather than the diff, so a diff-only dispatch cannot run them.

Write its findings to `reviews/<deliverable-id>-deliverable-review.md`.
Adjudicate as `SKILL.md` step 4 does, and clear every `[Critical]` before
the PR opens.

## 11. Open the draft PR

`SKILL.md` step 14 owns this, unchanged. One deliverable is one branch and
one draft PR however many packages it took.

## 12. Clean up

Remove each IC worktree when the deliverable closes, and prune its
registration from `worktrees.json`.

**Never force a removal.** A refusal means files exist nowhere else. Commit
them to that IC's branch, or surface them. Remove only worktrees this run
created, proven by `worktrees.json` — a path pattern is not ownership
(design §13.1).

## 13. Resume after a kill

Teammates are in-process, so a crash, a closed terminal or a reboot takes
the whole team down at once. What survives is every worktree on disk: its
commits **and its uncommitted edits**. What is lost is each IC's live
context.

`/crew:project-lead --resume <goal-slug>` reconciles. Append this session's
id to `run.session_ids` and to each worktree's `session_ids`; never
overwrite them.

For every worktree in `worktrees.json`:

| State | Meaning | Action |
|---|---|---|
| Commits, clean | The IC may have finished | Verify against the acceptance criterion before you believe it. Do not re-run work that already passes. |
| Commits, **dirty** | Died mid-package | **Commit the dirty work first**, then respawn. |
| Clean, no commits | Nothing was done | Respawn from the original brief |
| Recorded `integrated`, still present | Already merged | Safe to prune |

Three rules make this work:

1. **Never discard a dirty worktree.** Commit it before anything else.
   Uncommitted work is the only thing in the system that exists in exactly
   one place.
2. **Reconcile from git, then correct the record.**
   `git -C <wt> log <base>..HEAD` and `git -C <wt> status --porcelain` are
   the evidence. `state.json` is rewritten to match them, never the other
   way round.
3. **A respawned IC is a new IC.** Its brief must describe what is already
   in its worktree and say which steps are done. Its acceptance criterion is
   what makes the respawn idempotent.

Reconcile the deliverable branch the same way: `git -C <repo> log` shows
which packages already merged. An `integrated` package is terminal and
cannot be revised in place — correcting it takes a new package (design §10).

Clear `orphaned` on each worktree as you reconcile it.

A project lead killed mid-commit can leave a stale `index.lock` in a
worktree. Clear one only when no process holds it.

## Standing down an IC

Stand down, never kill. Ask the IC to commit what it has and stop. This
holds for a re-plan, for a fix round that respawns one band up, and for any
direction change. Work in progress is retained.

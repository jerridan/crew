# Full path

This file owns the loop for a deliverable with more than one package
(design §9.2). `SKILL.md` runs steps 1 to 5 first, then sends you here.

The simple path is `simple-path.md`. Nothing here applies to it, and this
file borrows three of its steps: 7, 12 and 14 there, named below.

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
| Integration | nothing merges | one squashed commit per package |
| The split critic | skipped | runs before any IC is dispatched |

An IC is named here because a teammate is a named agent. Every other agent
in a run stays unnamed, because you must read its result (design §3,
§15.20b).

## 0. Check the launch conditions

Two you can check, with the command that checks them. Run both before you
write the split, and escalate on either — neither can be fixed mid-run.

1. **Agent teams are on.** `echo $CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`
   prints `1`. With the flag off, a named agent launches as a plain subagent
   and every rule here is wrong.
2. **This session is not worktree-isolated.** `git -C <repo> status` from a
   worktree other than your own: an isolated session is refused outright, and
   the refusal names the reason. That command is the whole verification step
   (design §15.10, §15.23f).

State which one failed. Do not start the run and discover it later.

Two more conditions you cannot check in advance. A display mode must work —
iTerm2 with its Python API, a session inside tmux, or
`teammateMode: "in-process"` — and nothing in the run may stop for a human. A teammate's permission prompts surface in your session (design
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

Two rules shape the full path's split, on top of the format rules
`record-format.md` carries (design §15.50):

- **Read the charter's `Favour:` line first.** `spend`, the default, is one
  territory and one IC that carries its context from package to package.
  `time` is one territory per disjoint region of the tree, worked in
  parallel. The same goal ran both ways: parallel finished sooner and cost
  15 fix rounds and half again the tokens; sequential cost no fix rounds.
- **Fewer, larger packages in a territory.** Packages in one territory run in
  sequence, so a finer split there buys no parallelism and costs a plan, a
  review, a merge and a suite run per package. Split a territory only where
  a review boundary earns its cost: a different band, or an interface
  another package consumes.

## 2. Have the split reviewed

Dispatch `crew:split-critic`, unnamed, with `split.md`, `spec.md`, the repo
path, `review-output.md` whole, and the absolute path it writes its findings
to: `reviews/<deliverable-id>-split-critic-r<n>.md`, `<n>` being one more
than the highest already on disk under that name.

Adjudicate as `SKILL.md` step 4 does. A failed invariant is not a style
note — fix the split and dispatch again. Three re-splits is the cap;
escalate at it.

## 3. Create the branch and the worktrees

This step switches the checkout, so read its branch **before** you switch and
record it as `checkout_branch`, as `simple-path.md` step 7 says. Then branch
from the current head:
`git -C <repo> switch -c crew/<goal-slug>/<deliverable-id>`. Write
the `deliverables[]` entry now — `id`, branch, the head sha as `base`,
`state: pending`, `pr_url: null`, and `checkout_branch`.

Then one worktree per territory, all branching from that same head, so
integration is a merge and never a rebase (design §9.3):

```
git -C <repo> worktree add <worktree-root>/<territory-slug> -b crew/<goal-slug>/<territory-slug>
```

Put `<worktree-root>` at `<record-root>/worktrees`, outside the target repo.
A repo-local root looks tidy and breaks the suite: a test runner that globs
collects every worktree's tests as well as the repo's own, so the run
measures the wrong tree (design §15.35b). Put the root inside the repo only
with a reason, and record it.

Write `worktrees.json` now: the IC's name, the absolute worktree path, its
branch, this session's id, and `orphaned: false`. Set every package's
`ic_name` to the name of the IC that owns its territory. Nothing else maps a
package back to the worktree that must verify it.

Name an IC `ic-<territory-slug>`.

## 4. Spawn the ICs

Spawn one **named** teammate per territory, at the band of the package it
starts on: `crew:ic` for code, `crew:ic-instructions` for a `CLAUDE.md`, a
`.claude/rules/` file, a `SKILL.md`, an agent definition, or reader-facing
prose such as a README (design §3.1).

Pass the band's model at spawn time, as `band-rubric.md` says. Pass it for an
IC and never for a critic or a reviewer.

A teammate inherits no conversation history, so the spawn prompt carries all
of: `ic-contract.md`'s full text, the brief, the file set, **the absolute
worktree path**, the interface contract, the acceptance criterion, the
global constraints section, the package id, and **that it is a teammate** —
`ic-contract.md`'s plan gate branches on it, and an IC cannot tell on its
own.

It also carries the record root, as an absolute path. An interactive
teammate can write there (design §15.31b), so a full-path IC writes
`plans/<id>.md` and `reports/<id>.md` itself. If a write is denied anyway,
`ic-contract.md` makes the IC's final message its plan or its report, and
that message reaches you in its idle notification. Transcribe it, and say in
the file that you transcribed it.

Inject the contract as text. A teammate applies no `skills:` key and reads an
agent body differently in each display mode (design §15.20d), so a link is
not dependable and the prompt is.

Set the package and its deliverable `in-flight` at the first spawn, and write
that package's `base`: the worktree's head sha right now. For a territory's
first package that equals the deliverable's `base`.

## Servicing several territories

Steps 5 to 8a are written for one IC and you will be running several. You are
not stepping them in lockstep: service whichever IC reports next, and let the
others keep working. Each territory walks its own packages at its own pace.

Two rules keep that honest. Every IC's state lives in the record, not in your
head — `plan_approved_at`, `state` and `fix_rounds_used` per package — so read
the record, not your memory of who was where. And step 9 merges one package at
a time regardless of which territory produced it, because a suite run only
attributes a failure when a single package moved.

## 5. The plan gate

A teammate has a message channel, so the gate is one dispatch and a reply —
not the simple path's two dispatches.

The IC writes `plans/<id>.md` and waits. Read it, then approve it or send it
back with what to change. `SendMessage` the IC its go-ahead, and set
`plan_approved_at`.

For a `standard` or `light` package, check two things and approve: every
file the plan names is in the file set, and the plan changes no `produces`
signature. Read a `deep` package's plan in full. A plan gate that reads
every plan in full cost a run a round trip per package for no finding
(design §15.50).

While `plans/<id>.md` exists and `plan_approved_at` is `null`, that IC's
idle is an expected pause and not a fault (design §15.8).

## 5a. The idle nudge

An IC's idle notification is what tells you it stopped. Read the record
before you answer one, and sort the idle into one of four kinds. No hook
does this — a message does (design §13.1, §15.29).

| What the record holds | The idle means | What you do |
|---|---|---|
| `plans/<id>.md` exists, `plan_approved_at` is `null` | the plan gate | Nothing. Go to step 5. |
| A report **for this dispatch** | the IC finished, or stopped and said why | Go to step 6. |
| No such report, `nudges_used` is 0 | the IC stopped with nothing on disk | Nudge it, once. |
| No such report, `nudges_used` is 1 | the nudge did not land | Fail the package (below). |

**"For this dispatch" is the whole trick.** `reports/<id>.md` carries no round
suffix, so it survives every fix round and every re-plan. On a package's first
dispatch its existence is enough. After that it is not: a round-1 report sitting
on disk would make a round-2 IC that wrote nothing look finished, and the
project lead would verify a range whose HEAD never moved. So from the first fix
round on, the report counts only when it carries a `## Fix round <n>` heading
for the round now running (step 8 tells the IC to append one). A re-planned IC
is the same case: set `plan_approved_at` back to `null` when you send a plan
back, and its idle reads as the plan gate again.

An idle notification carries the IC's final message. When that message is
the report itself — `ic-contract.md` makes it the report when the record
write was denied — transcribe it to `reports/<id>.md`, say in the file that
you transcribed it, and go to step 6. That is a report, not an empty idle.

**One nudge per dispatch.** `SendMessage` the IC what is missing and the
absolute path to write it to. Then increment `nudges_used` and write
`state.json` before you go back to waiting. Read that field on every empty
idle, as the table's last two rows do: it is the only thing that tells a
resumed session a nudge already went out.

Failing the package is what the second empty idle earns. Verify the worktree
as step 6 says, commit any uncommitted work yourself, and treat the package as
`BLOCKED` with cause `capability`. `band-rubric.md`'s promotion rules take it
from there.

`nudges_used` counts one dispatch, not the package's life. Reset it to 0
whenever you dispatch that package again — a fix round, a next package, or a
respawn after a crash.

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

Read `run.compactions` before you accept. An entry whose `agent` is this
IC's name, dated since its last accepted package, means it lost the context
it planned in: send it its plan back with the go-ahead for the fix round,
and treat its report's claims about earlier packages as unverified. An entry
with `agent: null` is your own session's compaction; re-read the record
before your next decision.

## 7. Review the package

Write the diff to `diffs/<id>-r<n>.patch` so it never enters your context:

```
git -C <worktree> diff <package-base>..HEAD > <record-root>/diffs/<id>-r<n>.patch
```

An instruction package gets its acceptance checklist file instead.

Dispatch `crew:package-reviewer`, unnamed, with all five inputs it requires:
the package's record entry (`file_set`, `interface_contract`,
`acceptance_criterion`), the worktree path, the IC's report, the diff or
checklist path, and the brief. Inject `review-output.md` whole, and name the
absolute path it writes to: `reviews/<id>-package-review-r<n>.md`, `<n>`
being `fix_rounds_used`. Its result is three lines; open the file only when
the count says there are findings to adjudicate.

## 8. Fix rounds

Run a round only on `Verdict: fix round needed`. Five is the cap.

- **Rounds 1 to 3** message the same IC. It keeps its context, which is the
  point of a teammate. Tell it to append a `## Fix round <n>` section to
  `reports/<id>.md` rather than write a new file — step 5a reads that heading
  to tell this round's report from the last one's.
- **Rounds 4 and 5** stand the IC down, then spawn a fresh one **one band
  up**. A fresh IC holds no context, so its prompt describes what is already
  committed — `git -C <worktree> log --oneline` plus `git -C <worktree> diff
  --stat` — and which findings it must fix. A `deep` package cannot promote,
  so a `deep` package reaching round 4 escalates instead: respawn it at
  `deep` only if the principal says to (`band-rubric.md`).
- **At the cap**, fix the package yourself, or park it as `abandoned` with
  your reasoning recorded. At the top band, escalate instead.

**Increment `fix_rounds_used` and write `state.json` first**, before the round
runs — `record-format.md` says why the counter moves before the files it
names.

Then the round goes back through steps 6 and 7. A fix nobody re-reviewed is a
claim. Leave this step only on `Verdict: accepted`.

## 8a. The territory's next package

On `Verdict: accepted`, if that territory has another package in `split.md`,
send the IC its next package and return to step 5. An IC works its packages
in the listed order. Write the new package's `base` as you send it — the
worktree head as it stands now, which is the accepted package's last commit.
That is what keeps the next review diff to the next package's own work.

**Respawn instead of sending** when `run.compactions` names the IC in
`agent`, or when the IC has finished four packages. Neither you nor the IC can read
its context, so the count is the proxy: one IC carried five packages to 66%
of its window without compacting, and the next one may not (design §15.50).
Stand the IC down, then spawn a fresh one at the new package's band, with
the brief step 13 rule 3 describes: what its worktree already holds, and
which steps are done.

Reach step 9 only when every territory has finished every package it owns.

## 9. Integrate

Merge one package at a time, into the deliverable branch, as each package is
accepted rather than once per territory:

```
git -C <repo> cherry-pick -n <package-base>..<package-head>
git -C <repo> commit -m "<package one-liner>"
<run the suite>
```

`<package-head>` is the worktree head when you accepted the package — the
same sha you write as the next package's `base` at step 8.

Apply the package's own commit range, never `merge --squash` of the territory
branch. That branch holds every package the territory has finished, so a
branch-level squash collapses them into one commit and one suite run, which
loses the per-package attribution the next two paragraphs promise (design
§15.37b).

**Run the suite after each merge, not after all of them.** A failure is then
attributable to one package with no bisect. Read the output yourself. A green
run only proves the tree it ran on.

**On a red suite, revert that commit and open a fix round** on the package
that caused it. `git -C <repo> reset --hard HEAD~1` on the deliverable branch
undoes the cherry-pick; the package's own worktree and branch still hold the
work, so nothing is lost. The package goes back to `in-flight` and step 8
counts the round. A merge you leave red makes every later package's suite run
meaningless.

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

**Write back every preference answer the principal approved for recording.**
Each becomes one rule in this repo's own instruction files.
`autonomy-contract.md`'s "Record the answer as precedent" owns the rule.

Then sweep for stale status claims, as `simple-path.md` step 12 does: run
the block in `writing-standard.md`'s "Keep the status true" over the
deliverable branch.

## 10. Review the deliverable

**Write the diff again now**, to `diffs/<deliverable-id>-final.patch`. Step
7's diffs predate the fix rounds and
every shared-file edit you just made, and those edits are exactly what the
next reviewer's shared-file check exists to read (design §15.24).

Dispatch `crew:deliverable-reviewer`, unnamed, with `spec.md`, `split.md`,
the repo path and base ref, the fresh diff path, every accepted package
review, `review-output.md` whole, and the absolute path it writes to:
`reviews/<deliverable-id>-deliverable-review.md`. Four of its seven checks
read the record rather than the diff, so a diff-only dispatch cannot run
them.

Adjudicate as `SKILL.md` step 4 does, and clear every `[Critical]` before
the PR opens.

## 11. Open the draft PR

`simple-path.md` step 14 owns this, unchanged. One deliverable is one branch and
one draft PR however many packages it took.

A deliverable that cannot open a PR ends in `work-complete`. Step 14 owns
that procedure too, and `record-format.md` owns what the state means.

At either end, restore the checkout to `checkout_branch`, as `simple-path.md`
step 14 says.

## 12. Clean up

Remove each IC worktree when the deliverable closes, and prune its
registration from `worktrees.json`. `simple-path.md` step 14 owns the process
sweep that comes first.

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

Move `run_state` out of `interrupted` **first**, then clear `orphaned` on
each worktree as you reconcile it. In the other order, a session that dies
mid-reconciliation leaves cleared worktrees behind a run the hook will not
touch again, because the hook only acts on an `active` or `blocked` run.

A project lead killed mid-commit can leave a stale `index.lock` in a
worktree. Clear one only when no process holds it.

## Standing down an IC

Stand down, never kill. Ask the IC to commit what it has and stop. This
holds for a re-plan, for a fix round that respawns one band up, and for any
direction change. Work in progress is retained.

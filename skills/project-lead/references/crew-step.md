# crew-step.py

`scripts/crew-step.py` runs the fixed command sequences of a project lead in
one call each. This file owns its command line, its step lines, its evidence
and its exit codes. The path files say when to run each subcommand and what
you judge afterwards. They point here for everything else.

The script judges nothing. It prints what it ran and what it found. You read
the lines, then you decide.

Run it as `<project-lead-dir>/scripts/crew-step.py <subcommand> <record-dir>
...`. It finds `crew-record.py` and `spend.py` beside itself, and
`crew-orch.py` in `../../orchestrator/scripts/`. Python 3 standard library
only.

## Output and exit codes

Each step prints one line:

```
ok <step>: <detail>
FAIL <step>: <detail>
ask <step> <name>: <text>
```

A `FAIL` detail carries the failed command's own error text. An `ask` line
names a question the script cannot answer. You answer it.

Evidence follows the step lines. Each block opens with a line `--- <name>`.
The markers are `--- log`, `--- stat`, `--- untracked`, `--- criterion`,
`--- suite`, `--- red`, `--- pattern`, `--- compactions`,
`--- deliverable branch`, `--- listeners` and `--- diff`.

| Exit code | Meaning |
|---|---|
| 0 | every step passed |
| 1 | a step failed |
| 2 | a usage error: a missing argument, or a flag combination this file forbids |

A step that writes the record prints a `record` line. It carries one line per
`crew-record.py` call, with the call's subcommand as the detail.

Every `state.json` write is a `crew-record.py` call. The script writes
`worktrees.json` itself.

## launch-check

```
crew-step.py launch-check <record-dir>
```

Run it once, at the preference sweep. It runs launch checks 1 and 2 of
`full-path.md`'s "Check the launch conditions" and prints both results.
Exit 1 means either one failed.

| Step | What it does |
|---|---|
| `base` | Probes `<record-dir>` with `worktree add --detach`, `status` and `worktree remove --force` of the probe path. It removes the probe after every `add` that passed. On a refusal it probes `<run.repo>/.claude/worktrees/crew/<goal-slug>` the same way, then runs `git check-ignore -v` on it. No output from `check-ignore` fails that base. The step fails only when both bases fail. |
| `remote` | Passes when `git -C <run.repo> remote` prints a line. |
| `record` | Writes `run.worktree_base` for the base that passed. Writes one `decisions.md` precedent entry that names the base and each probe result. |

The `--force` of this probe is the only `--force` the script uses.

When the fallback base passed, it prints one line `ask collect: <text>`. The
repo's test command must not collect files under `.claude/`. You answer it.

The script writes no `escalations` entry.

## branch

```
crew-step.py branch <record-dir> <deliverable-id> [--branch <name>] [--held]
    [--start-point <ref>] [--territory <slug>=<ic-name> ...]
```

Run it after the split. It creates the deliverable's branch and, with
`--territory`, the territory worktrees.

| Flag | What it does |
|---|---|
| `--branch <name>` | The deliverable branch name. The default is `crew/<goal-slug>/<deliverable-id>`. Territory branches keep crew's names whatever this says. |
| `--held` | Marks the checkout as held by another run. The script also treats it as held when the current branch starts with `crew/` and carries another goal slug. |
| `--start-point <ref>` | The start of the held case's branch. The default is `origin/HEAD`. |
| `--territory <slug>=<ic-name>` | Cuts `<run.worktree_base>/worktrees/<slug>` on branch `crew/<goal-slug>/<slug>` from the head of `run.checkout`. Repeat the flag for each territory. |

| Step | What it does |
|---|---|
| `held` | Decides free or held. |
| `start-point` | Names the start point, held case only. With no flag and no `origin/HEAD`, it prints `FAIL start-point` and cuts nothing. |
| `exists` | Fails when git holds the branch or a worktree path and the record does not name it. Nothing is written. |
| `switch` | Free case: `switch -c <name>` in `run.repo`. Held case: `worktree add <run.worktree_base>/worktrees/<deliverable-id> -b <name> <start-point>`, which never switches the shared checkout. |
| `worktree` | One line per territory. The detail is the slug, or the deliverable id for the held checkout. |
| `record` | Writes the deliverable entry, `run.checkout`, and the `worktrees.json` entries. |

The record fields:

- The deliverable entry holds `id`, the branch, the head sha as `base`,
  `state: pending`, `pr_url: null` and `checkout_branch`. In the free case
  `checkout_branch` is the branch read before the switch, or `null` when
  detached. In the held case it is `null` and `checkout_restored` stays
  `null`.
- `run.checkout` is `run.repo` in the free case. In the held case it is the
  new worktree.
- A held checkout gets a `worktrees.json` entry keyed by the deliverable id.
  Each territory gets one keyed by its IC name. An entry holds `worktree`,
  `branch`, `session_ids` and `orphaned`. `session_ids` starts as
  `[$CLAUDE_CODE_SESSION_ID]`, and `orphaned` is `false`.
- Each package whose `territory` is a given slug gets `ic_name` set.

**A rerun finishes the job.** The script writes each record entry before the
git step it records. A rerun treats a resource as done when the record names
it and git holds it, on the recorded branch and path. That step prints
`ok <step>: already done`. A resource the record names and git lacks is
created. A resource git holds and the record does not name is `FAIL exists`.

So a promoted light-path run, whose deliverable entry and branch exist, runs
`branch --territory ...` and cuts only the territories.

## verify

```
crew-step.py verify <record-dir> <package-id> [--repo <path>]
    [--criterion <cmd>] [--suite <cmd> | --no-suite] [--red <sha>]
    [--pattern <regex>] [--ic-branch]
```

Run it once per package, before you read the diff. It reads the package's
`base` and `file_set` from `state.json`. It runs every check and exits 1 when
any failed, so one call gives the whole picture for one fix round.

| Flag | What it does |
|---|---|
| `--repo <path>` | The checkout of every check. The default is `run.checkout`. |
| `--criterion <cmd>` | Runs the command at HEAD in the checkout. Prints its exit code and the last 40 lines of output. A non-zero exit fails. |
| `--suite <cmd>` | The same, for the repo's suite. |
| `--no-suite` | Prints `ok suite: no suite`. A call with no `--criterion` runs no command. |
| `--red <sha>` | Runs the red-commit check. It needs `--criterion`, and without it the exit code is 2. |
| `--pattern <regex>` | Greps every line of the diff from the deliverable's `base` to HEAD. |
| `--ic-branch` | Puts every check in the IC's worktree and checks its branch. |

| Step | What it does |
|---|---|
| `clean-tree` | Reads `status --porcelain` by the definition in `simple-path.md`'s "Verify before you believe". A tracked change fails. An untracked file in the file set fails. An untracked file outside it prints under `--- untracked` and never fails. |
| `log` | Prints `log --oneline <base>..HEAD` under `--- log`, and `diff <base>..HEAD --stat` under `--- stat`. |
| `file-set` | Lists the files of the diff against the file set. A file outside the set fails and the line names it. |
| `ic-branch` | Runs with `--ic-branch` only. Fails when the worktree's current branch differs from the branch of the `worktrees.json` entry of the package's `ic_name`. It also prints every commit on `run.checkout`'s branch since the deliverable `base` under `--- deliverable branch`, and never fails on them. |
| `criterion` | Runs with `--criterion`. Evidence under `--- criterion`. |
| `suite` | Runs with `--suite` or `--no-suite`. Evidence under `--- suite`. |
| `red` | Runs with `--red`. Evidence under `--- red`. |
| `pattern` | Runs with `--pattern`. Prints the hit count and every hit under `--- pattern`. It never fails on a hit. |
| `compactions` | Prints every `run.compactions` entry whose `agent` equals the package's `ic_name`. It prints each entry with `agent: null` as the project lead's own. It prints `ok compactions: none` when there are none. It never fails. |

**`--ic-branch` and `--repo`.** With `--ic-branch`, the IC's worktree is the
checkout of every check above, the diff and the criterion included. A
`--repo` that differs from that worktree is a usage error, exit 2.

**The red check.** It needs a clean tree first. It runs `switch --detach <sha>
-q`, runs the criterion, and requires a non-zero exit. A criterion that exits
0 at the red commit is `FAIL red`. It then runs `switch -q <branch>`, always,
even when the criterion or an earlier step failed. It checks the tree again
just before the detach, after the criterion and the suite ran at HEAD. A dirty
tree at that point is `FAIL red: dirty tree before the switch`, and no switch
happens. A change the criterion makes at the red commit is named in the `red`
detail and evidence, and the switch back discards it, so it never reaches the
branch. In a repo that builds before it tests, put the build in
`--criterion`, so the build runs at the red commit too.

**The diff comes last.** After every step line and every other evidence
block, the script prints `--- diff` and the full `diff <base>..HEAD`. It
prints no word on the diff's content. It writes no `decisions.md` entry and
no state field.

## hand-over

```
crew-step.py hand-over <record-dir> <deliverable-id> --body <file> --title <t>
crew-step.py hand-over <record-dir> <deliverable-id> --local
```

Run it once, after you wrote the body file. `--body` and `--title` open a
draft PR. `--local` ends the run with no push and no PR. The script never
writes, edits or reads the body for its content.

It runs these steps in order and stops at the first `FAIL`, except `orch`,
`spend` and `worktree-remove`:

| Step | What it does |
|---|---|
| `push` | `git push -u <remote> <branch>` in `run.checkout`. The remote is `origin`, or else the only remote. Two remotes and no `origin` is `FAIL push: no origin`. Skipped with `--local`. |
| `pr` | `gh pr create --draft --title <t> --body-file <file> --head <branch>`. It reads the URL from the output. An open PR on the branch is reused, with the detail `already open <url>`, so a rerun after a failed `deliver` write opens no second PR. Skipped with `--local`. |
| `deliver` | `crew-record.py deliver <id> draft-pr-opened --pr-url <url> --review-head <head sha>`, or `work-complete --review-head <head sha>` with `--local`. |
| `orch` | Runs when `run.orchestrator` is set and a PR opened: `crew-orch.py --orch <name> item <item> pr <url>`, then `stage <item> review`. A failed call prints `FAIL orch: <its error>` and the sequence goes on. |
| `spend`, `listeners`, `worktree-remove`, `restore` | The `cleanup` steps below. |

**A failed push or PR.** The script reads `escalations` for the entry with
trigger text `launch check 3 (trigger 6): no remote`. It prints `FAIL push:
<git's error>` or `FAIL pr: <gh's error>`, then one line `escalation:
<its answer>`, `escalation: unanswered` or `escalation: none`. It runs nothing after that. You act on
the answer. A second call after a push that passed and a `gh` failure pushes
again, which changes nothing, and goes on.

**A rerun after `deliver`.** On a deliverable already `draft-pr-opened` or
`work-complete`, the script skips `push`, `pr` and `deliver` with `ok <step>:
already done`. It does not rearm the review. It runs `orch` again, because
both `crew-orch.py` calls are idempotent, and then the cleanup steps.

The exit code is 1 when any step failed, including `orch`, `spend` and
`worktree-remove`.

## cleanup

```
crew-step.py cleanup <record-dir> <deliverable-id>
```

Run it to finish a round that pushed to an open PR, and `hand-over` runs the
same steps. It changes no deliverable state. It runs every step, and exits 1
when any failed.

| Step | What it does |
|---|---|
| `spend` | `spend.py <record-dir> <run.checkout> --write`. A failure prints `FAIL spend: <error>` and the sequence goes on. |
| `listeners` | Prints `lsof -iTCP -sTCP:LISTEN` under `--- listeners`. The script kills nothing. |
| `worktree-remove` | Removes each worktree that `worktrees.json` names, then deletes that entry. IC worktrees go first and the deliverable checkout goes last. Each removal runs against `run.repo` and never passes `--force`. The line is `ok worktree-remove: <path>`. A refusal prints `FAIL worktree-remove: <path>: <git's message>`, keeps that entry, and goes on to the next. A path not in `worktrees.json` is never touched. A run with no file removes nothing. |
| `restore` | With a `checkout_branch` and a clean tree, runs `switch <checkout_branch>` in `run.repo` and writes `checkout_restored: true`. With a dirty tree, writes one sentence that names why as `checkout_restored`. With `checkout_branch: null`, it does nothing. |

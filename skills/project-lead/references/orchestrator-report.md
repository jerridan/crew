# Orchestrator report

This file owns what a project lead writes and calls when its goal carries an
`Orchestrator:` line. `SKILL.md`'s "Take the goal" sends you here, and you read
it in the turn you take such a goal. `resume.md` sends a resumed run here when
`run.orchestrator` is set.

A goal message with the line `Orchestrator: <name>, item <id>` means an
orchestrator session started this run. That session is `run.principal`. The
session can get a new name later ("A new orchestrator name"), so `run.principal`
can change, and `<name>` in the line never does.
`skills/orchestrator/references/orchestrator-record.md` owns the record you
report into, and every command below.

When the line is there, do three things in the turn you take the goal:

1. Copy the line to `charter.md`.
2. Write `run.orchestrator` with `crew-record.py <record-dir> run set
   orchestrator '{"name": "<name>", "item": "<id>"}'`.
3. Call the script as `<this skill's dir>/../orchestrator/scripts/crew-orch.py
   --orch <name> <command>`.

Call `stage <id> <stage>` at each phase change. The path decides which calls
you make:

| Path | Stage calls |
|---|---|
| Change path | `spec` when you start the spec; `split` (full path only); `build` at each IC dispatch, with `--detail <k>/<n>` for package k of n; `item <id> pr <pr_url>` and `review` when the PR opens and the goal check starts, which `crew-step.py hand-over` makes (`crew-step.md`), so make neither call yourself; `pr` when `goal-check.md`'s "Mark the PR ready" check passes, after a goal-miss patch is pushed and not at the goal check's report, also when `PR: draft` keeps the PR a draft |
| Light path | `build` at each IC dispatch; then `review` and `pr` as on the change path |
| Investigation path | `spec` while you diagnose; then the change path's calls for a fix ending, or `closed` for a report ending |

A goal run runs one goal check, so no later review writes a stage. A
window session writes `merged` at the merge, `shipped` at the ship word, and
`closed` when the watcher reports the PR closed with no merge. A
`crew:review` run writes no stage call.

Write each question with `ask <id> "<text>"` before you send it to the
principal. `ask` prints a question id. Send the question by `SendMessage`, as
`autonomy-contract.md`'s "Reach the principal the way the goal arrived" says,
and name that id in it. The answer arrives as a message, and the orchestrator
records it with `answer`. If no session is addressable, the failed-send rule
of `autonomy-contract.md` holds.

## After the hand-over

The project lead ends at the hand-over, so no project lead session reads an
orchestrator message afterwards. The orchestrator sends its merge word, its
rebase word and a go-ahead answer by `say`, through its `crew-orch.py send`
command (`skills/orchestrator/SKILL.md`'s "Message discipline", rule 7). A
window session sends its question by `SendMessage`, as above, and the answer
comes by `say`.

## A new orchestrator name

The person can rename the orchestrator session. The orchestrator then sends
each live implementer a message with the line `Orchestrator: <name>, item
<id>`, and the new session name.

A message is from your orchestrator when it carries that line with both
values equal to `run.orchestrator`. When such a message arrives with an
envelope `from-name` that differs from `run.principal`, do two things:

1. Write the `from-name` into `run.principal` with `crew-record.py <record-dir>
   run set principal '"<from-name>"'`.
2. Send every later message to that value.

Take the new value from the envelope `from-name`, never from a name in the
message text alone. Keep `<name>` of `--orch` as it is: the record name does
not change.

A failed `crew-orch.py` call never stops the run. Note it in `decisions.md`
and go on. A record with no `run.orchestrator` behaves as before.

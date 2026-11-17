# Orchestrator report

This file owns what a project lead writes and calls when its goal carries an
`Orchestrator:` line. `SKILL.md`'s "Take the goal" sends you here, and you read
it in the turn you take such a goal.

A goal message with the line `Orchestrator: <name>, item <id>` means an
orchestrator session started this run. That session is `run.principal`.
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
| Change path | `spec` when you start the spec; `split` (full path only); `build` at each IC dispatch, with `--detail <k>/<n>` for package k of n; `item <id> pr <pr_url>` and `review` when the PR opens and the first skeptical round starts; `pr` when the skeptical review stops (`skeptical-review.md`'s "Mark the PR ready"), also when `PR: draft` keeps the PR a draft |
| Light path | `build` at each IC dispatch; then `review` and `pr` as on the change path |
| Investigation path | `spec` while you diagnose; then the change path's calls for a fix ending, or `closed` for a report ending |

A later skeptical round writes no stage. The delivered window writes `merged`
at the merge, `shipped` at the ship word, and `closed` when the watch reports
the PR closed with no merge. A `crew:review` run writes no stage call.

Write each question with `ask <id> "<text>"` before you send it to the
principal. `ask` prints a question id. Send the question by `SendMessage`, as
`autonomy-contract.md`'s "Reach the principal the way the goal arrived" says,
and name that id in it. The answer arrives as a message, and the orchestrator
records it with `answer`. If no session is addressable, the failed-send rule
of `autonomy-contract.md` holds.

A failed `crew-orch.py` call never stops the run. Note it in `decisions.md`
and go on. A record with no `run.orchestrator` behaves as before.

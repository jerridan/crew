#!/usr/bin/env python3
"""Write a crew record's state.json: one change per call, timestamped, in one
atomic replace.

usage:
  crew-record.py <record-dir> init <goal> <goal-slug> <session-id>
  crew-record.py <record-dir> session-id <id>
  crew-record.py <record-dir> deliverable add <json-object>
  crew-record.py <record-dir> deliverable <id> state <state> [--pr-url <url>]
  crew-record.py <record-dir> deliverable <id> set <field> <json>
  crew-record.py <record-dir> package add <json-object>
  crew-record.py <record-dir> package <id> state <state>
  crew-record.py <record-dir> package <id> set <field> <json>
  crew-record.py <record-dir> run state <state>
  crew-record.py <record-dir> run set <dotted.field> <json>
  crew-record.py <record-dir> escalation add <trigger> <question>
  crew-record.py <record-dir> escalation answer <index> <answer>
  crew-record.py <record-dir> integrate <package-id> [--review-head <sha>] [--published]
  crew-record.py <record-dir> deliver <deliverable-id> <deliverable-state> [--pr-url <url>] [--review-head <sha>]
  crew-record.py <record-dir> arm-review --head <sha>
  crew-record.py <record-dir> ship

`init` creates state.json with `created_at`. `integrate` sets a package
`integrated`, which is the delivered window's own state write. Its
`--published` flag stamps `pushed_at` in the same write, for a branch with no
remote, where the commit is the publication and no push is ever owed.
`deliver` sets the deliverable's terminal state and `run_state: delivered` in
one write, which `record-format.md` requires for `work-complete`.
`--review-head <sha>` on either one writes `run.review_pending` in that same
write, so a state change and the review it owes cannot come apart
(`skeptical-review.md`). `arm-review --head` does the same arming on its own.
Every command that moves the branch head takes that flag under that name, and
writes the head key beside the state key it already writes. `arm_review` is
that shared step. The value
is `{head, round}`, and `round` is one more than `run.review_rounds`: the
round the owed review will run at, so the sha and the report name it expects
are written together. At the round cap it writes no pending head at all and
appends the head to `run.unreviewed_heads` instead. `ship` sets
`run_state: complete`. The first write that sets `run_state` to `delivered`
stamps `run.delivered_at`, and a later one never moves it. A write that sets
`run_state` to `complete` — `ship`, `run state complete`, or
`run set run_state complete` — stamps `run.completed_at`.
`run set` takes a dotted path, so a nested key changes on its own and the
rest of the object stays. It creates each missing level on the way down, and
replaces a `null` level with an object. A level that holds a list, a string or
a number exits with a message, because no path runs through one.
`escalation add` appends one ask and stamps `asked_at`, so a batch is one
call per question and no earlier ask is lost; it prints the new entry's
index, which `escalation answer` takes.
`record-format.md` owns every field name and every transition; this script
checks none of them. A `set` value is JSON: `3`, `"text"`, `null`, `["a"]`.
"""

import datetime
import json
import os
import sys
from pathlib import Path


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, data) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def find(items, value):
    for item in items:
        if item.get("id") == value:
            return item
    sys.exit(f"no entry with id {value}")


def usage() -> None:
    sys.exit(__doc__)


def arg(rest: list[str], i: int) -> str:
    if i >= len(rest):
        usage()
    return rest[i]


def flag(rest: list[str], name: str):
    return rest[rest.index(name) + 1] if name in rest else None


def set_dotted(target: dict, dotted: str, value) -> None:
    # Mirrored from `skills/lead/scripts/crew-portfolio.py`. The two scripts
    # sit in two skill directories, and a shared module would be a third file
    # the plugin loads for neither skill. Change both together.
    keys = dotted.split(".")
    for depth, key in enumerate(keys[:-1]):
        if target.get(key) is None:
            target[key] = {}
        target = target[key]
        # A path through a string, a list or a number cannot be walked, and
        # assigning into it raises where every other error here exits with a
        # message.
        if not isinstance(target, dict):
            sys.exit(f"{'.'.join(keys[:depth + 1])} is not an object")
    target[keys[-1]] = value


# `skeptical-review.md` owns the review-round cap and states the same number.
# This constant is where the record enforces it, so the two move together.
REVIEW_ROUND_CAP = 3


def arm_review(run: dict, head: str | None) -> None:
    """Record the head a skeptical review is owed on, or record that none is.

    Every arming in the run comes through here: `deliver --review-head` folds
    it into the hand-over write, and `arm-review --head` does it on its own
    after a follow-up integrates (`skeptical-review.md`). At the cap no
    further review runs, so the head is logged as unreviewed instead of
    armed, and the next report to the principal names it.
    """
    if not head:
        return
    rounds = run.get("review_rounds")
    rounds = rounds if isinstance(rounds, int) and not isinstance(rounds, bool) else 0
    if rounds >= REVIEW_ROUND_CAP:
        run["review_pending"] = None
        unreviewed = run.get("unreviewed_heads")
        if not isinstance(unreviewed, list):
            unreviewed = []
        unreviewed.append({"head": head, "reason": "cap", "at": now()})
        run["unreviewed_heads"] = unreviewed
        return
    run["review_pending"] = {"head": head, "round": rounds + 1}


STAMPS = {"delivered": "delivered_at", "complete": "completed_at"}


def stamp_on_transition(run: dict, before: str | None) -> None:
    """Stamp `delivered_at` or `completed_at` when `run_state` becomes
    `delivered` or `complete`.

    `before` is the state before this write, so a write that leaves
    `run_state` where it was never moves a stamp. `delivered_at` is stamped
    once, on the first entry into `delivered`: a run that goes
    `delivered → blocked → delivered`, or through `interrupted` and back,
    keeps the stamp it already has, so the delivered window is measured from
    the hand-over. A run that goes `delivered → complete` keeps it too.
    """
    after = run.get("run_state")
    if after == before or after not in STAMPS:
        return
    if after == "delivered":
        # A key that is absent or `null` is a run that has not delivered yet.
        if run.get("delivered_at") is None:
            run["delivered_at"] = now()
    else:
        run[STAMPS[after]] = now()


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        usage()
    record = Path(argv[0])
    state_path = record / "state.json"
    kind, rest = argv[1], argv[2:]

    if kind == "init":
        state = {
            "goal": arg(rest, 0),
            "goal_slug": arg(rest, 1),
            "deliverables": [],
            "run": {
                "run_state": "active",
                "session_ids": [arg(rest, 2)],
                "created_at": now(),
                "spend": {},
                "escalations": [],
            },
            "packages": [],
        }
        record.mkdir(parents=True, exist_ok=True)
        write_json(state_path, state)
        print("ok")
        return

    state = json.loads(state_path.read_text(encoding="utf-8"))
    run = state.setdefault("run", {})

    if kind == "session-id":
        ids = run.setdefault("session_ids", [])
        if arg(rest, 0) not in ids:
            ids.append(rest[0])
    elif kind == "deliverable":
        if arg(rest, 0) == "add":
            entry = json.loads(arg(rest, 1))
            entry.setdefault("state_changed_at", now())
            state.setdefault("deliverables", []).append(entry)
        else:
            dl = find(state.get("deliverables", []), rest[0])
            if arg(rest, 1) == "state":
                dl["state"] = arg(rest, 2)
                dl["state_changed_at"] = now()
                url = flag(rest, "--pr-url")
                if url:
                    dl["pr_url"] = url
            elif arg(rest, 1) == "set":
                dl[arg(rest, 2)] = json.loads(arg(rest, 3))
            else:
                usage()
    elif kind == "package":
        if arg(rest, 0) == "add":
            entry = json.loads(arg(rest, 1))
            entry.setdefault("state_changed_at", now())
            state.setdefault("packages", []).append(entry)
        else:
            pkg = find(state.get("packages", []), rest[0])
            if arg(rest, 1) == "state":
                pkg["state"] = arg(rest, 2)
                pkg["state_changed_at"] = now()
            elif rest[1] == "set":
                pkg[arg(rest, 2)] = json.loads(arg(rest, 3))
            else:
                usage()
    elif kind == "run":
        before = run.get("run_state")
        if arg(rest, 0) == "state":
            run["run_state"] = arg(rest, 1)
            stamp_on_transition(run, before)
        elif rest[0] == "set":
            set_dotted(run, arg(rest, 1), json.loads(arg(rest, 2)))
            stamp_on_transition(run, before)
        else:
            usage()
    elif kind == "escalation":
        asks = run.setdefault("escalations", [])
        if arg(rest, 0) == "add":
            asks.append({
                "trigger": arg(rest, 1),
                "question": arg(rest, 2),
                "asked_at": now(),
                "answer": None,
            })
            write_json(state_path, state)
            print(len(asks) - 1)
            return
        elif rest[0] == "answer":
            index = int(arg(rest, 1))
            if index < 0 or index >= len(asks):
                sys.exit(f"no escalation at index {index}")
            asks[index]["answer"] = arg(rest, 2)
        else:
            usage()
    elif kind == "integrate":
        pkg = find(state.get("packages", []), arg(rest, 0))
        pkg["state"] = "integrated"
        pkg["state_changed_at"] = now()
        # A branch with no remote is published by the commit itself, so the
        # integration stamps it and no push is ever owed (`record-format.md`).
        if "--published" in rest:
            pkg["pushed_at"] = now()
        arm_review(run, flag(rest, "--review-head"))
    elif kind == "deliver":
        dl = find(state.get("deliverables", []), arg(rest, 0))
        dl["state"] = arg(rest, 1)
        dl["state_changed_at"] = now()
        url = flag(rest, "--pr-url")
        if url:
            dl["pr_url"] = url
        arm_review(run, flag(rest, "--review-head"))
        before = run.get("run_state")
        run["run_state"] = "delivered"
        stamp_on_transition(run, before)
    elif kind == "arm-review":
        head = flag(rest, "--head")
        if not head:
            usage()
        arm_review(run, head)
    elif kind == "ship":
        before = run.get("run_state")
        run["run_state"] = "complete"
        stamp_on_transition(run, before)
    else:
        usage()

    write_json(state_path, state)
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1:])

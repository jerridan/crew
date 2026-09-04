#!/usr/bin/env python3
"""Write a crew record's state.json: one change per call, timestamped, in one
atomic replace.

usage:
  crew-record.py <record-dir> init <goal> <goal-slug> <session-id>
  crew-record.py <record-dir> session-id <id>
  crew-record.py <record-dir> deliverable add <json-object>
  crew-record.py <record-dir> deliverable <id> state <state> [--pr-url <url>]
  crew-record.py <record-dir> package add <json-object>
  crew-record.py <record-dir> package <id> state <state>
  crew-record.py <record-dir> package <id> set <field> <json>
  crew-record.py <record-dir> run state <state>
  crew-record.py <record-dir> run set <dotted.field> <json>
  crew-record.py <record-dir> close <deliverable-id> <deliverable-state> [--pr-url <url>]

`init` creates state.json with `created_at`. `close` sets the deliverable's
terminal state and `run_state: complete` in one write, which
`record-format.md` requires for `work-complete`. `run set` takes a dotted
path, so `run set spend.budget 60` changes one key and keeps the rest.
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
    keys = dotted.split(".")
    for key in keys[:-1]:
        target = target.setdefault(key, {})
    target[keys[-1]] = value


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
            if arg(rest, 1) != "state":
                usage()
            dl["state"] = arg(rest, 2)
            dl["state_changed_at"] = now()
            url = flag(rest, "--pr-url")
            if url:
                dl["pr_url"] = url
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
        if arg(rest, 0) == "state":
            run["run_state"] = arg(rest, 1)
        elif rest[0] == "set":
            set_dotted(run, arg(rest, 1), json.loads(arg(rest, 2)))
        else:
            usage()
    elif kind == "close":
        dl = find(state.get("deliverables", []), arg(rest, 0))
        dl["state"] = arg(rest, 1)
        dl["state_changed_at"] = now()
        url = flag(rest, "--pr-url")
        if url:
            dl["pr_url"] = url
        run["run_state"] = "complete"
    else:
        usage()

    write_json(state_path, state)
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1:])

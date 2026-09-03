#!/usr/bin/env python3
"""Write one field of a crew record's state.json, with the timestamp the
format requires, in one atomic replace.

usage:
  crew-record.py <record-dir> package <id> state <state>
  crew-record.py <record-dir> package <id> set <field> <json>
  crew-record.py <record-dir> deliverable <id> state <state> [--pr-url <url>]
  crew-record.py <record-dir> run state <state>
  crew-record.py <record-dir> run set <field> <json>
  crew-record.py <record-dir> spend <agent> <total_tokens|null> [--estimated]
  crew-record.py <record-dir> session-id <id>

`record-format.md` owns every field name and every transition. This script
sets what it is told and stamps `state_changed_at`; it does not validate a
transition. A `set` value is JSON: `3`, `"text"`, `null`, `["a"]`.
"""

import datetime
import json
import os
import sys
from pathlib import Path


def now() -> str:
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def write_json(path: Path, data) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def find(items, key, value):
    for item in items:
        if item.get(key) == value:
            return item
    sys.exit(f"no entry with {key} == {value}")


def main(argv: list[str]) -> None:
    if len(argv) < 3:
        sys.exit(__doc__)
    state_path = Path(argv[0]) / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    kind, rest = argv[1], argv[2:]

    if kind == "package":
        pkg = find(state.setdefault("packages", []), "id", rest[0])
        if rest[1] == "state":
            pkg["state"] = rest[2]
            pkg["state_changed_at"] = now()
        elif rest[1] == "set":
            pkg[rest[2]] = json.loads(rest[3])
        else:
            sys.exit(__doc__)
    elif kind == "deliverable":
        dl = find(state.setdefault("deliverables", []), "id", rest[0])
        if rest[1] != "state":
            sys.exit(__doc__)
        dl["state"] = rest[2]
        dl["state_changed_at"] = now()
        if "--pr-url" in rest:
            dl["pr_url"] = rest[rest.index("--pr-url") + 1]
    elif kind == "run":
        run = state.setdefault("run", {})
        if rest[0] == "state":
            run["run_state"] = rest[1]
        elif rest[0] == "set":
            run[rest[1]] = json.loads(rest[2])
        else:
            sys.exit(__doc__)
    elif kind == "spend":
        spend = state.setdefault("run", {}).setdefault("spend", {})
        tokens = None if rest[1] == "null" else int(rest[1])
        measured = tokens is not None and "--estimated" not in rest
        spend.setdefault("by_agent", []).append(
            {"agent": rest[0], "total_tokens": tokens, "measured": measured}
        )
        key = "measured_tokens" if measured else "estimated_tokens"
        spend[key] = spend.get(key, 0) + (tokens or 0)
    elif kind == "session-id":
        ids = state.setdefault("run", {}).setdefault("session_ids", [])
        if rest[0] not in ids:
            ids.append(rest[0])
    else:
        sys.exit(__doc__)

    write_json(state_path, state)
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1:])

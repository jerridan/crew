#!/usr/bin/env python3
"""Write a lead's portfolio.json: one change per call, timestamped, in one
atomic replace.

usage:
  crew-portfolio.py <portfolio-dir> init <title> <portfolio-slug> <session-id>
  crew-portfolio.py <portfolio-dir> session-id <id>
  crew-portfolio.py <portfolio-dir> lead state <state>
  crew-portfolio.py <portfolio-dir> lead set <dotted.field> <json>
  crew-portfolio.py <portfolio-dir> item add <json-object>
  crew-portfolio.py <portfolio-dir> item <id> state <state>
  crew-portfolio.py <portfolio-dir> item <id> set <field> <json>
  crew-portfolio.py <portfolio-dir> item <id> expect <one line of text>
  crew-portfolio.py <portfolio-dir> escalation add <item-id> <question>
  crew-portfolio.py <portfolio-dir> escalation answer <index> <answer>

`init` creates portfolio.json with `created_at`. Every other call stamps
`lead.updated_at`, so the newest open portfolio is always findable.
`item ... expect` takes plain text, not JSON, because it is the one field
the ledger rewrites every turn.
`escalation add` appends one ask, stamps `asked_at`, and prints the new
entry's index, which `escalation answer` takes. It never replaces the list,
so no earlier ask is lost.
`record-format.md`'s "The portfolio record" owns every field name and every
state value; this script checks none of them. A `set` value is JSON: `3`,
`"text"`, `null`, `["a"]`.
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
    sys.exit(f"no item with id {value}")


def usage() -> None:
    sys.exit(__doc__)


def arg(rest: list[str], i: int) -> str:
    if i >= len(rest):
        usage()
    return rest[i]


def set_dotted(target: dict, dotted: str, value) -> None:
    keys = dotted.split(".")
    for key in keys[:-1]:
        target = target.setdefault(key, {})
    target[keys[-1]] = value


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        usage()
    portfolio = Path(argv[0])
    path = portfolio / "portfolio.json"
    kind, rest = argv[1], argv[2:]

    if kind == "init":
        data = {
            "title": arg(rest, 0),
            "portfolio_slug": arg(rest, 1),
            "lead": {
                "state": "active",
                "session_ids": [arg(rest, 2)],
                "created_at": now(),
                "updated_at": now(),
                "escalations": [],
            },
            "items": [],
        }
        portfolio.mkdir(parents=True, exist_ok=True)
        (portfolio / "charters").mkdir(exist_ok=True)
        write_json(path, data)
        print("ok")
        return

    data = json.loads(path.read_text(encoding="utf-8"))
    lead = data.setdefault("lead", {})
    printed = None

    if kind == "session-id":
        ids = lead.setdefault("session_ids", [])
        if arg(rest, 0) not in ids:
            ids.append(rest[0])
    elif kind == "lead":
        if arg(rest, 0) == "state":
            lead["state"] = arg(rest, 1)
        elif rest[0] == "set":
            set_dotted(lead, arg(rest, 1), json.loads(arg(rest, 2)))
        else:
            usage()
    elif kind == "item":
        if arg(rest, 0) == "add":
            entry = json.loads(arg(rest, 1))
            entry.setdefault("state_changed_at", now())
            data.setdefault("items", []).append(entry)
        else:
            item = find(data.get("items", []), rest[0])
            verb = arg(rest, 1)
            if verb == "state":
                item["state"] = arg(rest, 2)
                item["state_changed_at"] = now()
            elif verb == "set":
                item[arg(rest, 2)] = json.loads(arg(rest, 3))
            elif verb == "expect":
                item["expect"] = arg(rest, 2)
            else:
                usage()
    elif kind == "escalation":
        asks = lead.setdefault("escalations", [])
        if arg(rest, 0) == "add":
            asks.append({
                "item": arg(rest, 1),
                "question": arg(rest, 2),
                "asked_at": now(),
                "answer": None,
            })
            printed = len(asks) - 1
        elif rest[0] == "answer":
            index = int(arg(rest, 1))
            if index < 0 or index >= len(asks):
                sys.exit(f"no escalation at index {index}")
            asks[index]["answer"] = arg(rest, 2)
        else:
            usage()
    else:
        usage()

    lead["updated_at"] = now()
    write_json(path, data)
    print("ok" if printed is None else printed)


if __name__ == "__main__":
    main(sys.argv[1:])

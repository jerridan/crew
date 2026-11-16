#!/usr/bin/env python3
"""crew-orch: the only writer of an orchestrator record.

The record is <record-root>/orchestrators/<name>/. The record root is
$CREW_RECORD_ROOT or ~/.claude/crew/. The name comes from --orch <name> or
from $CREW_ORCH; the flag wins. skills/orchestrator/references/
orchestrator-record.md defines every file, field and command.

Python 3 standard library only. Exit 0 on success, 1 when a command cannot
do its work, and 2 on a usage error. An error prints one line to stderr and
writes nothing.

Commands:
  init
  item add <id> --title <t> --repo <owner/name> [--group <g>] [--ticket <id> --ticket-url <url>]
  item <id> pr <number|url>
  item <id> set <title|repo|ticket|group|launch|launch.<key>> <json>
  group add <id> --title <t> [--repo <r>] [--ticket <id> --ticket-url <url>]
  group <id> order <item,...>
  group <id> owner <thing> <item>
  stage <item> <stage> [--detail <t>] [--doing <t>]
  doing <item> <text>
  ask <item> <text>
  inbox add <decision|question|idea|notice> [--item <id>] <text> [--recommend <t>]
  route <id> principal
  answer <id> <text>
  dismiss <id> [--reason <t>]
  plan change <what> --reason <why> [--file <path>]
  told <item> --file <path>
  pace set <json>
  refresh [<item>]
  board [--urls]
  show [<item>]
"""

from __future__ import annotations

import fcntl
import json
import os
import re
import subprocess
import sys
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

VERSION = 1
NAME_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,63}")
ID_RE = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}")
REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
PR_URL_RE = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/pull/([0-9]+)/?")
RESERVED_IDS = {"add"}

STAGES = ["queued", "spec", "split", "build", "review", "pr", "merged", "shipped", "closed"]
MARK_STAGES = ["spec", "split", "build", "review", "pr"]
DONE_STAGES = {"shipped", "closed"}
LANDED_STAGES = {"merged", "shipped"}
KINDS = {"decision": "d", "question": "q", "idea": "i", "notice": "n"}
SETTABLE = {"title", "repo", "ticket", "group", "launch"}
LAUNCH_KEYS = ["session_name", "repo", "worktree", "branch", "base", "model", "terminal", "tab", "tab_group"]
PACE_MODES = {"normal", "slowed", "stopped"}

GH_FIELDS = "state,isDraft,reviewDecision,mergeStateStatus,statusCheckRollup"
QUEUE_QUERY = (
    "query($owner: String!, $repo: String!, $n: Int!) {"
    " repository(owner: $owner, name: $repo) {"
    " pullRequest(number: $n) { isInMergeQueue mergeQueueEntry { position } } } }"
)
CHECK_FAIL = {"FAILURE", "ERROR", "TIMED_OUT", "STARTUP_FAILURE", "ACTION_REQUIRED"}
CHECK_PASS = {"SUCCESS", "NEUTRAL", "SKIPPED"}
GH_TIMEOUT = 60
USAGE_TIMEOUT = 5


class Usage(Exception):
    """A usage error: exit 2."""


class Fail(Exception):
    """The command cannot do its work: exit 1."""


# ---------------------------------------------------------------- time


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(text):
    if not text:
        return None
    try:
        return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
    except (TypeError, ValueError):
        return None


def age(text) -> str:
    """One number and one unit, the largest unit that is not zero."""
    then = parse_iso(text)
    if then is None:
        return ""
    sec = max(0, int((datetime.now(timezone.utc) - then).total_seconds()))
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if sec >= size:
            return f"{sec // size}{unit}"
    return f"{sec}s"


def clock(epoch) -> str:
    """Local clock time, or a weekday when the time is more than a day away."""
    when = datetime.fromtimestamp(epoch)
    if epoch - time.time() > 86400:
        return when.strftime("%a")
    hour = when.hour % 12 or 12
    return f"{hour}:{when.minute:02d} {'AM' if when.hour < 12 else 'PM'}"


# ---------------------------------------------------------------- record files


def record_root() -> Path:
    env = os.environ.get("CREW_RECORD_ROOT")
    return Path(env).expanduser() if env else Path.home() / ".claude" / "crew"


class Record:
    def __init__(self, name: str):
        self.name = name
        self.dir = record_root() / "orchestrators" / name
        self.json = self.dir / "orchestrator.json"
        self.plan = self.dir / "plan.md"
        self.told = self.dir / "told"
        self.lock_path = self.dir / "orchestrator.lock"

    @contextmanager
    def locked(self):
        fd = os.open(str(self.lock_path), os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    def load(self) -> dict:
        try:
            return json.loads(self.json.read_text(encoding="utf-8"))
        except FileNotFoundError:
            raise Fail(f"no orchestrator record '{self.name}'; run: crew-orch.py --orch {self.name} init")
        except ValueError as err:
            raise Fail(f"{self.json} is not valid JSON: {err}")

    def save(self, state: dict) -> None:
        tmp = self.dir / f".orchestrator.json.{os.getpid()}.tmp"
        with open(tmp, "w", encoding="utf-8") as fh:
            json.dump(state, fh, indent=2, ensure_ascii=False)
            fh.write("\n")
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, self.json)

    def exists(self) -> bool:
        return self.json.is_file()

    def read(self) -> dict:
        """Read with no lock: a reader sees the old file or the new one, never half of one."""
        return self.load()

    def mutate(self, change):
        """Lock, re-read, change, derive, and replace the file. Return what `change` returns."""
        if not self.dir.is_dir():
            self.load()
        with self.locked():
            state = self.load()
            result = change(state)
            derive(state)
            state["updated_at"] = now_iso()
            self.save(state)
        return result


def new_state(name: str) -> dict:
    stamp = now_iso()
    return {
        "version": VERSION,
        "name": name,
        "created_at": stamp,
        "updated_at": stamp,
        "counters": {"item": 0, "decision": 0, "question": 0, "idea": 0, "notice": 0},
        "items": {},
        "groups": {},
        "inbox": [],
        "plan_changes": [],
        "pace": {"mode": "normal", "slots": {"busy": 0, "max": 3}, "limit_pct": 95},
    }


# ---------------------------------------------------------------- derived values


def landed(item: dict) -> bool:
    gh = item.get("github") or {}
    return item.get("stage") in LANDED_STAGES or gh.get("state") == "MERGED"


def finished(item: dict) -> bool:
    """`True` when the item no longer holds back an item after it in the merge order."""
    return landed(item) or item.get("stage") == "closed"


def merge_value(item: dict) -> str:
    """The first match of the order in orchestrator-record.md, from the stored fields alone."""
    gh = item.get("github") or {}
    if landed(item):
        return "merged"
    if not item.get("pr"):
        return "no PR"
    if gh.get("state") == "CLOSED" or item.get("stage") == "closed":
        return "closed"
    if gh.get("in_queue"):
        pos = gh.get("queue_position")
        return f"in queue {pos}" if pos is not None else "in queue"
    draft = bool(gh.get("is_draft"))
    checks = gh.get("checks")
    checks_ok = checks in ("pass", "none")
    merge_state = gh.get("merge_state")
    decision = gh.get("review_decision")
    waits = item.get("waits_on") or []
    if gh and not draft and decision == "APPROVED" and merge_state == "CLEAN" and checks_ok and not waits:
        return "can merge"
    if gh and not draft and checks_ok and merge_state in ("CLEAN", "BLOCKED") and decision in (None, "REVIEW_REQUIRED"):
        return "needs review"
    if waits:
        return "waits on " + ", ".join(waits)
    if merge_state in ("DIRTY", "BEHIND"):
        return "conflict"
    if checks == "fail":
        return "ci failing"
    if checks == "pending":
        return "ci pending"
    if draft:
        return "draft"
    if decision == "CHANGES_REQUESTED":
        return "changes requested"
    return "blocked"


def derive(state: dict) -> None:
    items = state["items"]
    for item in items.values():
        waits = []
        group = state["groups"].get(item.get("group") or "")
        if group and item["id"] in group["order"]:
            for other in group["order"][: group["order"].index(item["id"])]:
                if other in items and not finished(items[other]):
                    waits.append(other)
        item["waits_on"] = waits
    for item in items.values():
        item["merge"] = merge_value(item)


# ---------------------------------------------------------------- argument parsing


def take_options(args: list, options: dict) -> tuple:
    """Split `args` into positionals and options.

    `options` maps a long option to True when it takes a value, False when it
    is a flag. `--` ends the options.
    """
    pos, opts = [], {}
    i = 0
    while i < len(args):
        arg = args[i]
        if arg == "--":
            pos.extend(args[i + 1:])
            break
        if arg.startswith("--") and len(arg) > 2:
            key, eq, val = arg[2:].partition("=")
            if key not in options:
                raise Usage(f"unknown option --{key}")
            if options[key]:
                if not eq:
                    i += 1
                    if i >= len(args):
                        raise Usage(f"--{key} needs a value")
                    val = args[i]
                opts[key] = val
            else:
                if eq:
                    raise Usage(f"--{key} takes no value")
                opts[key] = True
        else:
            pos.append(arg)
        i += 1
    return pos, opts


def want(pos: list, low: int, high: int, form: str) -> None:
    if not low <= len(pos) <= high:
        raise Usage(f"usage: {form}")


def check_id(value: str, what: str) -> str:
    if not ID_RE.fullmatch(value) or value in RESERVED_IDS:
        raise Usage(f"bad {what} id '{value}': use [a-z0-9][a-z0-9_-]{{0,31}}, not 'add'")
    return value


def check_repo(value) -> str:
    if not isinstance(value, str) or not REPO_RE.fullmatch(value):
        raise Usage(f"bad repo {value!r}: use owner/name")
    return value


def parse_json(text: str):
    try:
        return json.loads(text)
    except ValueError:
        raise Usage(f"not valid JSON: {text}")


def ticket_from(opts: dict):
    if "ticket-url" in opts and "ticket" not in opts:
        raise Usage("--ticket-url needs --ticket")
    if "ticket" not in opts:
        return None
    return {"id": opts["ticket"], "url": opts.get("ticket-url")}


def check_ticket(value):
    if value is None:
        return None
    if (not isinstance(value, dict) or set(value) - {"id", "url"} or not isinstance(value.get("id"), str)
            or not isinstance(value.get("url"), (str, type(None)))):
        raise Usage('ticket must be null or {"id": "<text>", "url": "<url>" | null}')
    return {"id": value["id"], "url": value.get("url")}


def get_item(state: dict, item_id: str) -> dict:
    item = state["items"].get(item_id)
    if item is None:
        raise Usage(f"no item '{item_id}'")
    return item


def get_group(state: dict, group_id: str) -> dict:
    group = state["groups"].get(group_id)
    if group is None:
        raise Usage(f"no group '{group_id}'")
    return group


def get_entry(state: dict, entry_id: str) -> dict:
    for entry in state["inbox"]:
        if entry["id"] == entry_id:
            return entry
    raise Usage(f"no inbox entry '{entry_id}'")


def read_source(path: str) -> str:
    try:
        return Path(path).read_text(encoding="utf-8")
    except OSError as err:
        raise Fail(f"cannot read {path}: {err.strerror}")


# ---------------------------------------------------------------- commands


def cmd_init(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    want(pos, 0, 0, "init")
    rec.dir.mkdir(parents=True, exist_ok=True)
    with rec.locked():
        if rec.exists():
            raise Fail(f"orchestrator record '{rec.name}' already exists: {rec.dir}")
        rec.told.mkdir(exist_ok=True)
        if not rec.plan.exists():
            rec.plan.write_text("", encoding="utf-8")
        rec.save(new_state(rec.name))
    print(rec.dir)


def cmd_item(rec: Record, args: list) -> None:
    if not args:
        raise Usage("usage: item add <id> ... | item <id> pr <ref> | item <id> set <field> <json>")
    if args[0] == "add":
        item_add(rec, args[1:])
        return
    item_id = args[0]
    pos, _ = take_options(args[1:], {})
    if pos[:1] == ["pr"]:
        want(pos, 2, 2, "item <id> pr <number|url>")
        item_pr(rec, item_id, pos[1])
    elif pos[:1] == ["set"]:
        want(pos, 3, 3, "item <id> set <field> <json>")
        item_set(rec, item_id, pos[1], parse_json(pos[2]))
    else:
        raise Usage("usage: item <id> pr <number|url> | item <id> set <field> <json>")


def item_add(rec: Record, args: list) -> None:
    form = "item add <id> --title <t> --repo <owner/name> [--group <g>] [--ticket <id> --ticket-url <url>]"
    pos, opts = take_options(args, {"title": True, "repo": True, "group": True, "ticket": True, "ticket-url": True})
    want(pos, 1, 1, form)
    item_id = check_id(pos[0], "item")
    if "title" not in opts or "repo" not in opts:
        raise Usage(f"usage: {form}")
    repo = check_repo(opts["repo"])
    ticket = ticket_from(opts)

    def change(state):
        if item_id in state["items"]:
            raise Usage(f"item '{item_id}' already exists")
        group = opts.get("group")
        if group is not None:
            get_group(state, group)
        state["counters"]["item"] += 1
        stamp = now_iso()
        state["items"][item_id] = {
            "id": item_id, "n": state["counters"]["item"], "title": opts["title"], "repo": repo,
            "group": group, "ticket": ticket, "pr": None,
            "stage": "queued", "detail": None, "stage_at": stamp,
            "doing": None, "doing_at": None, "github": None,
            "merge": "no PR", "waits_on": [], "launch": {}, "told": [], "created_at": stamp,
        }

    rec.mutate(change)


def item_pr(rec: Record, item_id: str, ref: str) -> None:
    url_match = PR_URL_RE.fullmatch(ref)
    if not url_match and not re.fullmatch(r"[1-9][0-9]*", ref):
        raise Usage(f"bad PR '{ref}': give a number or a https://github.com/<owner>/<name>/pull/<n> URL")

    def change(state):
        item = get_item(state, item_id)
        if url_match:
            item["pr"] = {"number": int(url_match.group(2)), "url": ref.rstrip("/")}
        else:
            item["pr"] = {"number": int(ref), "url": f"https://github.com/{item['repo']}/pull/{ref}"}

    rec.mutate(change)


def item_set(rec: Record, item_id: str, field: str, value) -> None:
    base, _, key = field.partition(".")
    if base not in SETTABLE or (key and base != "launch"):
        raise Usage(f"cannot set '{field}': use one of {', '.join(sorted(SETTABLE))}, or launch.<key>")
    if base == "title" and (not isinstance(value, str) or not value):
        raise Usage("title must be a non-empty string")
    if base == "repo":
        check_repo(value)
    if base == "ticket":
        value = check_ticket(value)
    if base == "group" and value is not None and not isinstance(value, str):
        raise Usage("group must be a group id or null")
    if base == "launch":
        if key:
            if key not in LAUNCH_KEYS:
                raise Usage(f"bad launch key '{key}': use one of {', '.join(LAUNCH_KEYS)}")
            if not isinstance(value, (str, type(None))):
                raise Usage(f"launch.{key} must be a string or null")
        else:
            if not isinstance(value, dict) or set(value) - set(LAUNCH_KEYS):
                raise Usage(f"launch must be an object with keys from: {', '.join(LAUNCH_KEYS)}")
            if not all(isinstance(v, (str, type(None))) for v in value.values()):
                raise Usage("every launch value must be a string or null")

    def change(state):
        item = get_item(state, item_id)
        if base == "launch" and key:
            item["launch"][key] = value
        elif base == "group":
            if value is not None:
                get_group(state, value)
            old = state["groups"].get(item.get("group") or "")
            if old and value != old["id"]:
                old["order"] = [i for i in old["order"] if i != item_id]
                old["owners"] = {k: v for k, v in old["owners"].items() if v != item_id}
            item["group"] = value
        else:
            item[base] = value

    rec.mutate(change)


def cmd_group(rec: Record, args: list) -> None:
    if not args:
        raise Usage("usage: group add <id> ... | group <id> order <items> | group <id> owner <thing> <item>")
    if args[0] == "add":
        form = "group add <id> --title <t> [--repo <r>] [--ticket <id> --ticket-url <url>]"
        pos, opts = take_options(args[1:], {"title": True, "repo": True, "ticket": True, "ticket-url": True})
        want(pos, 1, 1, form)
        group_id = check_id(pos[0], "group")
        if "title" not in opts:
            raise Usage(f"usage: {form}")
        repo = check_repo(opts["repo"]) if "repo" in opts else None
        ticket = ticket_from(opts)

        def add(state):
            if group_id in state["groups"]:
                raise Usage(f"group '{group_id}' already exists")
            state["groups"][group_id] = {
                "id": group_id, "title": opts["title"], "repo": repo, "ticket": ticket,
                "order": [], "owners": {}, "created_at": now_iso(),
            }

        rec.mutate(add)
        return
    group_id = args[0]
    pos, _ = take_options(args[1:], {})
    if pos[:1] == ["order"]:
        want(pos, 2, 2, "group <id> order <item,item,...>")
        order = [i for i in pos[1].split(",") if i]
        if len(set(order)) != len(order):
            raise Usage("an item is named twice in the order")

        def set_order(state):
            get_group(state, group_id)
            for item_id in order:
                if get_item(state, item_id).get("group") != group_id:
                    raise Usage(f"item '{item_id}' is not in group '{group_id}'")
            state["groups"][group_id]["order"] = order

        rec.mutate(set_order)
    elif pos[:1] == ["owner"]:
        want(pos, 3, 3, "group <id> owner <thing> <item>")
        thing, item_id = pos[1], pos[2]

        def set_owner(state):
            group = get_group(state, group_id)
            if get_item(state, item_id).get("group") != group_id:
                raise Usage(f"item '{item_id}' is not in group '{group_id}'")
            group["owners"][thing] = item_id

        rec.mutate(set_owner)
    else:
        raise Usage("usage: group <id> order <item,...> | group <id> owner <thing> <item>")


def cmd_stage(rec: Record, args: list) -> None:
    form = f"stage <item> <{'|'.join(STAGES)}> [--detail <t>] [--doing <t>]"
    pos, opts = take_options(args, {"detail": True, "doing": True})
    want(pos, 2, 2, form)
    item_id, stage = pos
    if stage not in STAGES:
        raise Usage(f"unknown stage '{stage}': use one of {', '.join(STAGES)}")

    def change(state):
        item = get_item(state, item_id)
        stamp = now_iso()
        item["stage"] = stage
        item["detail"] = opts.get("detail")
        item["stage_at"] = stamp
        if "doing" in opts:
            item["doing"] = opts["doing"]
            item["doing_at"] = stamp

    rec.mutate(change)


def cmd_doing(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    want(pos, 2, 2, "doing <item> <text>")

    def change(state):
        item = get_item(state, pos[0])
        item["doing"] = pos[1]
        item["doing_at"] = now_iso()

    rec.mutate(change)


def add_entry(rec: Record, kind: str, for_: str, item_id, text: str, recommend) -> str:
    def change(state):
        if item_id is not None:
            get_item(state, item_id)
        state["counters"][kind] += 1
        entry_id = f"{KINDS[kind]}{state['counters'][kind]}"
        state["inbox"].append({
            "id": entry_id, "kind": kind, "for": for_, "item": item_id, "text": text,
            "recommend": recommend, "created_at": now_iso(), "routed_at": None,
            "state": "open", "answer": None, "closed_at": None,
        })
        return entry_id

    return rec.mutate(change)


def cmd_ask(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    want(pos, 2, 2, "ask <item> <text>")
    print(add_entry(rec, "question", "orchestrator", pos[0], pos[1], None))


def cmd_inbox(rec: Record, args: list) -> None:
    form = "inbox add <decision|question|idea|notice> [--item <id>] <text> [--recommend <t>]"
    if args[:1] != ["add"]:
        raise Usage(f"usage: {form}")
    pos, opts = take_options(args[1:], {"item": True, "recommend": True})
    want(pos, 2, 2, form)
    kind, text = pos
    if kind not in KINDS:
        raise Usage(f"unknown kind '{kind}': use one of {', '.join(KINDS)}")
    print(add_entry(rec, kind, "principal", opts.get("item"), text, opts.get("recommend")))


def open_entry(state: dict, entry_id: str) -> dict:
    entry = get_entry(state, entry_id)
    if entry["state"] != "open":
        raise Usage(f"entry '{entry_id}' is already {entry['state']}")
    return entry


def cmd_route(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    want(pos, 2, 2, "route <id> principal")
    if pos[1] != "principal":
        raise Usage("usage: route <id> principal")

    def change(state):
        entry = open_entry(state, pos[0])
        entry["for"] = "principal"
        entry["routed_at"] = now_iso()

    rec.mutate(change)


def close_entry(rec: Record, entry_id: str, new_state: str, answer) -> None:
    def change(state):
        entry = open_entry(state, entry_id)
        entry["state"] = new_state
        entry["answer"] = answer
        entry["closed_at"] = now_iso()

    rec.mutate(change)


def cmd_answer(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    want(pos, 2, 2, "answer <id> <text>")
    close_entry(rec, pos[0], "answered", pos[1])


def cmd_dismiss(rec: Record, args: list) -> None:
    pos, opts = take_options(args, {"reason": True})
    want(pos, 1, 1, "dismiss <id> [--reason <t>]")
    close_entry(rec, pos[0], "dismissed", opts.get("reason"))


def cmd_plan(rec: Record, args: list) -> None:
    form = "plan change <what> --reason <why> [--file <path>]"
    if args[:1] != ["change"]:
        raise Usage(f"usage: {form}")
    pos, opts = take_options(args[1:], {"reason": True, "file": True})
    want(pos, 1, 1, form)
    if "reason" not in opts:
        raise Usage(f"usage: {form}")
    body = read_source(opts["file"]) if "file" in opts else None

    def change(state):
        state["plan_changes"].append({"at": now_iso(), "change": pos[0], "reason": opts["reason"]})
        if body is not None:
            tmp = rec.dir / f".plan.md.{os.getpid()}.tmp"
            tmp.write_text(body, encoding="utf-8")
            os.replace(tmp, rec.plan)

    rec.mutate(change)


def cmd_told(rec: Record, args: list) -> None:
    form = "told <item> --file <path>"
    pos, opts = take_options(args, {"file": True})
    want(pos, 1, 1, form)
    if "file" not in opts:
        raise Usage(f"usage: {form}")
    body = read_source(opts["file"])

    def change(state):
        item = get_item(state, pos[0])
        rel = f"told/{item['id']}-{len(item['told']) + 1}.md"
        rec.told.mkdir(exist_ok=True)
        (rec.dir / rel).write_text(body, encoding="utf-8")
        item["told"].append({"at": now_iso(), "path": rel})

    rec.mutate(change)


def is_count(value) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def cmd_pace(rec: Record, args: list) -> None:
    form = "pace set <json>"
    pos, _ = take_options(args, {})
    if pos[:1] != ["set"]:
        raise Usage(f"usage: {form}")
    want(pos, 2, 2, form)
    value = parse_json(pos[1])
    if not isinstance(value, dict) or set(value) - {"mode", "slots", "limit_pct"}:
        raise Usage("pace must be an object with keys from: mode, slots, limit_pct")
    if "mode" in value and value["mode"] not in PACE_MODES:
        raise Usage(f"pace mode must be one of {', '.join(sorted(PACE_MODES))}")
    slots = value.get("slots")
    if "slots" in value and (not isinstance(slots, dict) or set(slots) - {"busy", "max"}
                             or not all(is_count(v) for v in slots.values())):
        raise Usage('pace slots must be {"busy": <int>, "max": <int>}')
    if "limit_pct" in value and not (is_count(value["limit_pct"]) and 1 <= value["limit_pct"] <= 100):
        raise Usage("pace limit_pct must be an integer from 1 to 100")

    def change(state):
        pace = state["pace"]
        for key, val in value.items():
            if key == "slots":
                pace["slots"].update(val)
            else:
                pace[key] = val

    rec.mutate(change)


# ---------------------------------------------------------------- refresh


def last_line(text: str, default: str) -> str:
    lines = [ln for ln in (text or "").strip().splitlines() if ln.strip()]
    return lines[-1].strip() if lines else default


def run_gh(argv: list):
    """Run gh. Return (stdout, None) or (None, one line that says why it failed)."""
    try:
        proc = subprocess.run(["gh"] + argv, capture_output=True, text=True, timeout=GH_TIMEOUT)
    except FileNotFoundError:
        return None, "gh is not installed"
    except subprocess.TimeoutExpired:
        return None, f"gh timed out after {GH_TIMEOUT}s"
    if proc.returncode != 0:
        return None, last_line(proc.stderr, f"gh exited {proc.returncode}")
    return proc.stdout, None


def check_summary(rollup: list) -> tuple:
    """Return (checks, failed names) from the latest run of each check.

    A cancelled run is dropped before the latest run is chosen, so it never
    counts. A skipped or neutral run counts as a pass.
    """
    latest = {}
    for index, check in enumerate(rollup or []):
        if not isinstance(check, dict):
            continue
        verdict = check.get("conclusion") or check.get("state") or ""
        if verdict == "CANCELLED":
            continue
        name = check.get("name") or check.get("context") or f"#{index}"
        key = (check.get("workflowName") or "", name)
        stamp = check.get("startedAt") or check.get("completedAt") or ""
        if key not in latest or stamp >= latest[key][0]:
            latest[key] = (stamp, name, check)
    if not latest:
        return "none", []
    failed, pending = [], False
    for _, name, check in latest.values():
        verdict = check.get("conclusion") or check.get("state") or ""
        if verdict in CHECK_FAIL:
            failed.append(name)
        elif verdict not in CHECK_PASS:
            pending = True
    if failed:
        return "fail", sorted(failed)
    return ("pending" if pending else "pass"), []


def read_pr(repo: str, number: int) -> dict:
    """Read one PR. Return {"fields": {...} or None, "queue": {...} or None, "error": line or None}."""
    out, err = run_gh(["pr", "view", str(number), "--repo", repo, "--json", GH_FIELDS])
    if err:
        return {"fields": None, "queue": None, "error": f"gh pr view {number}: {err}"}
    try:
        info = json.loads(out)
        checks, failed = check_summary(info.get("statusCheckRollup") or [])
        fields = {
            "state": info.get("state"),
            "is_draft": bool(info.get("isDraft")),
            "review_decision": info.get("reviewDecision") or None,
            "merge_state": info.get("mergeStateStatus") or None,
            "checks": checks,
            "failed_checks": failed,
        }
    except (ValueError, AttributeError) as exc:
        return {"fields": None, "queue": None, "error": f"gh pr view {number}: bad output: {exc}"}
    owner, name = repo.split("/", 1)
    out, err = run_gh(["api", "graphql", "-f", f"query={QUEUE_QUERY}", "-f", f"owner={owner}",
                       "-f", f"repo={name}", "-F", f"n={number}"])
    if err:
        return {"fields": fields, "queue": None, "error": f"gh merge queue read {number}: {err}"}
    try:
        pr = json.loads(out)["data"]["repository"]["pullRequest"]
        entry = pr.get("mergeQueueEntry") or {}
        in_queue = bool(pr.get("isInMergeQueue"))
        queue = {"in_queue": in_queue, "queue_position": entry.get("position") if in_queue else None}
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        return {"fields": fields, "queue": None, "error": f"gh merge queue read {number}: bad output: {exc}"}
    return {"fields": fields, "queue": queue, "error": None}


def cmd_refresh(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    want(pos, 0, 1, "refresh [<item>]")
    state = rec.read()
    if pos:
        item = get_item(state, pos[0])
        if not item.get("pr"):
            raise Fail(f"item '{pos[0]}' has no PR; set one with: item {pos[0]} pr <number|url>")
        targets = [item]
    else:
        targets = [i for i in state["items"].values() if i.get("pr")]
    # gh runs outside the lock, so a slow call never holds up another writer.
    results = {}
    for item in targets:
        result = read_pr(item["repo"], item["pr"]["number"])
        results[item["id"]] = (item["pr"]["number"], result)
        if result["error"]:
            print(f"crew-orch: {item['id']}: {result['error']}", file=sys.stderr)
    if not results:
        return

    def change(state):
        stamp = now_iso()
        for item_id, (number, result) in results.items():
            item = state["items"].get(item_id)
            if item is None or not item.get("pr") or item["pr"]["number"] != number:
                continue
            gh = item.get("github")
            if result["fields"] is None:
                if gh is not None:
                    gh["error"] = result["error"]
                continue
            old = gh or {}
            gh = dict(result["fields"])
            queue = result["queue"] or {"in_queue": bool(old.get("in_queue")),
                                        "queue_position": old.get("queue_position")}
            gh.update(queue)
            gh["refreshed_at"] = stamp
            gh["error"] = result["error"]
            item["github"] = gh

    rec.mutate(change)


# ---------------------------------------------------------------- board


def usage_figures():
    """Run crew-usage.py beside this script. Return its five_hour and seven_day, or None."""
    script = Path(__file__).resolve().parent / "crew-usage.py"
    if not script.is_file():
        return None
    try:
        proc = subprocess.run([sys.executable, str(script), "show", "--json"],
                              capture_output=True, text=True, timeout=USAGE_TIMEOUT)
        if proc.returncode != 0:
            return None
        data = json.loads(proc.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None
    if not isinstance(data, dict):
        return None
    out = {}
    for key in ("five_hour", "seven_day"):
        part = data.get(key)
        if isinstance(part, dict) and is_number(part.get("used_pct")):
            out[key] = part
    return out if "five_hour" in out else None


def is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def meter(pct) -> str:
    filled = max(0, min(10, int(round(pct / 10))))
    return "█" * filled + "░" * (10 - filled)


def pace_word(pace: dict) -> str:
    mode = pace.get("mode")
    if mode == "slowed":
        slots = pace.get("slots") or {}
        return f"SLOWED: {slots.get('busy', 0)} of {slots.get('max', 0)} slots"
    if mode == "stopped":
        return "STOPPED"
    return ""


def plan_lines(state: dict) -> list:
    figures = usage_figures()
    word = pace_word(state.get("pace") or {})
    if figures is None:
        return [f" {word}", ""] if word else []
    lines = []
    for label, key, head in (("5h", "five_hour", " Plan   "), ("7d", "seven_day", "        ")):
        part = figures.get(key)
        if not part:
            continue
        line = f"{head}{label} {meter(part['used_pct'])}  {int(round(part['used_pct'])):>3}%"
        notes = []
        if is_number(part.get("resets_at")):
            notes.append(f"resets {clock(part['resets_at'])}")
        if is_number(part.get("full_at")):
            notes.append(f"full at about {clock(part['full_at'])}")
        if notes:
            line += "  " + " · ".join(notes)
        if key == "five_hour" and word:
            line += f"   {word}"
        lines.append(line)
    return lines + [""]


class Links:
    """Make a link: OSC 8 on a terminal, plain text otherwise. Keep a list for --urls."""

    def __init__(self, tty: bool):
        self.tty = tty
        self.seen = []

    def make(self, text: str, url, width: int = 0) -> str:
        pad = " " * max(0, width - len(text))
        if not url:
            return text + pad
        if (text, url) not in self.seen:
            self.seen.append((text, url))
        if self.tty:
            return f"\033]8;;{url}\033\\{text}\033]8;;\033\\{pad}"
        return text + pad


def marks(stage: str) -> str:
    if stage in ("merged", "shipped", "closed"):
        return "●" * 5
    if stage not in MARK_STAGES:
        return "○" * 5
    at = MARK_STAGES.index(stage)
    return "●" * at + "◐" + "○" * (4 - at)


def shows_merge(item: dict) -> bool:
    """`True` when the status word is the merge value: a PR at stage `review` or
    later, or stage `merged` or `shipped`. Stage `closed` shows `closed`."""
    stage = item["stage"]
    if stage in ("merged", "shipped"):
        return True
    return bool(item.get("pr")) and stage in ("review", "pr")


def status_word(item: dict) -> str:
    stage = item["stage"]
    if stage == "closed":
        return "closed"
    if shows_merge(item):
        return item["merge"]
    return f"{stage} {item['detail']}" if item.get("detail") else stage


def row_text(item: dict) -> str:
    parts = []
    if item.get("waits_on") and not shows_merge(item) and item["stage"] != "closed":
        parts.append("after " + ", ".join(item["waits_on"]))
    if item["stage"] == "shipped" and not item.get("doing"):
        parts.append("shipped")
    if item.get("doing"):
        parts.append(item["doing"])
    return " · ".join(parts)


def cmd_board(rec: Record, args: list) -> None:
    pos, opts = take_options(args, {"urls": False})
    want(pos, 0, 0, "board [--urls]")
    state = rec.read()
    links = Links(sys.stdout.isatty())
    items = state["items"]
    groups = state["groups"]
    out = plan_lines(state)

    # Needs you: every open entry for the principal, oldest first.
    needs = [e for e in state["inbox"] if e["state"] == "open" and e["for"] == "principal"]
    needs.sort(key=lambda e: e["created_at"])  # A stable sort keeps the add order inside one second.
    out.append(f" Needs you  {len(needs)}")
    rows = []
    for entry in needs:
        where = "-"
        if entry.get("item"):
            item = items.get(entry["item"])
            group = item.get("group") if item else None
            where = f"{group}/{entry['item']}" if group else entry["item"]
        rows.append((entry["id"], entry["kind"], age(entry.get("routed_at") or entry["created_at"]), where, entry))
    if rows:
        w = [max(len(r[i]) for r in rows) for i in range(4)]
        indent = 2 + sum(w) + 2 * 4
        for eid, kind, ago, where, entry in rows:
            out.append(f"  {eid:<{w[0]}}  {kind:<{w[1]}}  {ago:<{w[2]}}  {where:<{w[3]}}  {entry['text']}")
            if entry.get("recommend"):
                out.append(" " * indent + f"Recommended: {entry['recommend']}")
    out.append("")

    # The item rows, with one set of column widths for the whole board.
    def done(item):
        return item["stage"] in DONE_STAGES

    sections = []
    for group in sorted(groups.values(), key=lambda g: g["created_at"]):
        members = [i for i in items.values() if i.get("group") == group["id"]]
        if not any(not done(i) for i in members):
            continue
        ordered = [items[i] for i in group["order"] if i in items]
        rest = sorted((i for i in members if i["id"] not in group["order"]), key=lambda i: i["n"])
        sections.append((group, ordered + rest))
    singles = sorted((i for i in items.values() if i.get("group") not in groups and not done(i)),
                     key=lambda i: i["n"])
    open_groups = {g["id"] for g, _ in sections}
    done_count = sum(1 for i in items.values() if done(i) and i.get("group") not in open_groups)

    shown = [i for _, members in sections for i in members] + singles
    if shown:
        wn = max(len(str(i["n"])) for i in shown)
        wid = max(len(i["id"]) for i in shown)
        ws = max(len(status_word(i)) for i in shown)
        wp = max(len(f"#{i['pr']['number']}") if i.get("pr") else 0 for i in shown)
        wt = max(len(row_text(i)) for i in shown)

    def row(item):
        pr = item.get("pr")
        pr_cell = links.make(f"#{pr['number']}", pr["url"], wp) if pr else " " * wp
        text = row_text(item)
        ago = age(item.get("doing_at")) if item.get("doing") else ""
        line = (f"  {item['n']:>{wn}} {item['id']:<{wid}}  {marks(item['stage'])}  "
                f"{status_word(item):<{ws}}  {pr_cell}  {text:<{wt}}  {ago}")
        return line.rstrip()

    for group, members in sections:
        merged = sum(1 for i in members if landed(i))
        head = [group["title"]]
        if group.get("ticket"):
            head.append(links.make(group["ticket"]["id"], group["ticket"].get("url")))
        line = f" {head[0]}" + (f"  {head[1]}" if len(head) > 1 else "")
        if group.get("repo"):
            line += f"  ·  {group['repo']}"
        line += f"  ·  {merged} of {len(members)} merged"
        out.append(line)
        for item in members:
            out.append(row(item))
        out.append("")
    if singles:
        out.append(" Single items")
        for item in singles:
            out.append(row(item))
        out.append("")
    out.append(f" Done  {done_count}   ·   stages: spec → split → build → review → PR")
    if opts.get("urls"):
        out.append("")
        out.append(" Links")
        if links.seen:
            w = max(len(t) for t, _ in links.seen)
            out.extend(f"  {t:<{w}}  {u}" for t, u in links.seen)
    print("\n".join(out))


def cmd_show(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    want(pos, 0, 1, "show [<item>]")
    state = rec.read()
    value = get_item(state, pos[0]) if pos else state
    print(json.dumps(value, indent=2, ensure_ascii=False))


COMMANDS = {
    "init": cmd_init, "item": cmd_item, "group": cmd_group, "stage": cmd_stage, "doing": cmd_doing,
    "ask": cmd_ask, "inbox": cmd_inbox, "route": cmd_route, "answer": cmd_answer, "dismiss": cmd_dismiss,
    "plan": cmd_plan, "told": cmd_told, "pace": cmd_pace, "refresh": cmd_refresh, "board": cmd_board,
    "show": cmd_show,
}


def main(argv: list) -> int:
    try:
        name = None
        if argv and argv[0] in ("-h", "--help"):
            print(__doc__.strip())
            return 0
        if argv and argv[0].startswith("--orch"):
            if argv[0] == "--orch":
                if len(argv) < 2:
                    raise Usage("--orch needs a value")
                name, argv = argv[1], argv[2:]
            elif argv[0].startswith("--orch="):
                name, argv = argv[0][len("--orch="):], argv[1:]
        if name is None:
            name = os.environ.get("CREW_ORCH") or None
        if not argv or argv[0] not in COMMANDS:
            raise Usage(f"unknown command {argv[0]!r}; run --help" if argv else "no command; run --help")
        if name is None:
            raise Usage("no orchestrator: pass --orch <name> or set CREW_ORCH")
        if not NAME_RE.fullmatch(name):
            raise Usage(f"bad orchestrator name '{name}': use [a-z0-9][a-z0-9_-]{{0,63}}")
        COMMANDS[argv[0]](Record(name), argv[1:])
        return 0
    except Usage as err:
        print(f"crew-orch: {err}", file=sys.stderr)
        return 2
    except Fail as err:
        print(f"crew-orch: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

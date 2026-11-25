#!/usr/bin/env python3
"""crew-orch: the only writer of an orchestrator record.

The record is <record-root>/orchestrators/<name>/. The record root is
$CREW_RECORD_ROOT or ~/.claude/crew/. The name comes from --orch <name> or
from $CREW_ORCH; the flag wins. skills/orchestrator/references/
orchestrator-record.md defines every file, field and command.

Python 3 standard library only. Exit 0 on success, 1 when a command cannot
do its work, and 2 on a usage error. An error prints one line to stderr and
writes nothing. `merge` exits 3 to 11 and `launch` exits 3 on a refusal, as
the report of the build says; each such exit prints one line `<command>
<check>: <detail>`.

Commands:
  init
  item add <id> --title <t> --repo <owner/name> [--group <g>] [--ticket <id> --ticket-url <url>]
  item <id> pr <number|url|none>
  item <id> set <title|repo|ticket|group|launch|launch.<key>|subagent|subagent.<key>> <json>
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
  board [--urls | --json]
  show [<item>]
  close
  merge <item> [--ready "<line>"] [--when-green] [--findings-answered]
  finalize <item>
  handoff clear <item>
  send <item> (--text <t> | --file <p>) [--from <name>]
  launch <item> [--model <m>] [--group <g>] [--terminal <t>] [--principal <name>] [--goal-file <p>] [--wait-seconds <n>]
  close-item <item> [--continue] [--stop-processes]
  digest <item> [--diff-file <p>]
  resume [--read-only]
  wait [--interval <seconds>] [--polls <n>]
"""

from __future__ import annotations

import base64
import contextlib
import fcntl
import io
import json
import os
import re
import signal
import subprocess
import sys
import time
import uuid
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
SETTABLE = {"title", "repo", "ticket", "group", "launch", "subagent"}
LAUNCH_KEYS = ["session_name", "repo", "worktree", "branch", "base", "model", "terminal", "tab", "tab_group",
               "session_id"]
SUBAGENT_KEYS = ["name", "model", "worktree", "branch", "outcome", "ready"]
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


class Code(Exception):
    """A refusal with its own exit code (`merge`, `launch`): one stderr line."""

    def __init__(self, code: int, line: str):
        super().__init__(line)
        self.code = code
        self.line = line


# ---------------------------------------------------------------- time


def now_iso() -> str:
    """The time a write stamps: always the real clock."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def board_now() -> float:
    """The time `board` reads, in epoch seconds.

    A test pins it with the environment variable CREW_ORCH_NOW. It changes
    no write: `now_iso` stays the real clock.
    """
    pinned = os.environ.get("CREW_ORCH_NOW")
    if pinned:
        try:
            return float(pinned)
        except ValueError:
            raise Usage(f"CREW_ORCH_NOW is not epoch seconds: {pinned!r}")
    return time.time()


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
    sec = max(0, int(board_now() - then.timestamp()))
    for unit, size in (("d", 86400), ("h", 3600), ("m", 60)):
        if sec >= size:
            return f"{sec // size}{unit}"
    return f"{sec}s"


def clock(epoch) -> str:
    """Local clock time, or a weekday when the time is more than a day away."""
    when = datetime.fromtimestamp(epoch)
    if epoch - board_now() > 86400:
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
            state = json.loads(self.json.read_text(encoding="utf-8"))
            if isinstance(state, dict):
                state.setdefault("closed_at", None)  # a record from before close
                state.setdefault("events", [])  # a record from before the commands
                state.setdefault("merge_queue", [])
                state.setdefault("handoffs", [])
                for item in (state.get("items") or {}).values():
                    if isinstance(item, dict):
                        item.setdefault("subagent", None)  # a record from before subagent items
                        item.setdefault("ready", None)
            return state
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
        "closed_at": None,
        "counters": {"item": 0, "decision": 0, "question": 0, "idea": 0, "notice": 0},
        "items": {},
        "groups": {},
        "inbox": [],
        "plan_changes": [],
        "pace": {"mode": "normal", "slots": {"busy": 0, "max": 3}, "limit_pct": 95},
        "events": [],
        "merge_queue": [],
        "handoffs": [],
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
    # GitHub gives an empty decision when the repo requires no review; it is
    # stored as null. With merge state CLEAN, such a PR can merge.
    if gh and not draft and decision in ("APPROVED", None) and merge_state == "CLEAN" and checks_ok and not waits:
        return "can merge"
    if gh and not draft and checks_ok and (
            (decision == "REVIEW_REQUIRED" and merge_state in ("CLEAN", "BLOCKED"))
            or (decision is None and merge_state == "BLOCKED")):
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
        fresh = new_state(rec.name)
        if os.environ.get("CLAUDE_CODE_SESSION_ID"):
            fresh["orchestrator_session_id"] = os.environ["CLAUDE_CODE_SESSION_ID"]
        rec.save(fresh)
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
        want(pos, 2, 2, "item <id> pr <number|url|none>")
        item_pr(rec, item_id, pos[1])
    elif pos[:1] == ["set"]:
        want(pos, 3, 3, "item <id> set <field> <json>")
        item_set(rec, item_id, pos[1], parse_json(pos[2]))
    else:
        raise Usage("usage: item <id> pr <number|url|none> | item <id> set <field> <json>")


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
            "merge": "no PR", "waits_on": [], "launch": {}, "subagent": None, "told": [], "created_at": stamp,
        }

    rec.mutate(change)


def item_pr(rec: Record, item_id: str, ref: str) -> None:
    if ref == "none":
        # The item leaves its PR, as at the escalation of a subagent item.
        def clear(state):
            item = get_item(state, item_id)
            item["pr"] = None
            item["github"] = None

        rec.mutate(clear)
        return
    url_match = PR_URL_RE.fullmatch(ref)
    if not url_match and not re.fullmatch(r"[1-9][0-9]*", ref):
        raise Usage(f"bad PR '{ref}': give a number, a https://github.com/<owner>/<name>/pull/<n> URL or none")

    def change(state):
        item = get_item(state, item_id)
        if url_match and url_match.group(1).lower() != item["repo"].lower():
            raise Usage(f"PR URL repo {url_match.group(1)} is not the item's repo {item['repo']}")
        if url_match:
            new = {"number": int(url_match.group(2)), "url": ref.rstrip("/")}
        else:
            new = {"number": int(ref), "url": f"https://github.com/{item['repo']}/pull/{ref}"}
        # The GitHub values belong to one PR. A different PR starts with none,
        # so the board shows the stage word until a refresh reads the new PR.
        if (item.get("pr") or {}).get("number") != new["number"]:
            item["github"] = None
        item["pr"] = new

    rec.mutate(change)


def item_set(rec: Record, item_id: str, field: str, value) -> None:
    base, _, key = field.partition(".")
    if base not in SETTABLE or (key and base not in ("launch", "subagent")):
        raise Usage(f"cannot set '{field}': use one of {', '.join(sorted(SETTABLE))}, launch.<key> or subagent.<key>")
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
    if base == "subagent":
        if key:
            if key not in SUBAGENT_KEYS:
                raise Usage(f"bad subagent key '{key}': use one of {', '.join(SUBAGENT_KEYS)}")
            if not isinstance(value, (str, type(None))):
                raise Usage(f"subagent.{key} must be a string or null")
        elif value is not None:
            if not isinstance(value, dict) or set(value) - set(SUBAGENT_KEYS):
                raise Usage(f"subagent must be null or an object with keys from: {', '.join(SUBAGENT_KEYS)}")
            if not all(isinstance(v, (str, type(None))) for v in value.values()):
                raise Usage("every subagent value must be a string or null")
            value = {k: value.get(k) for k in SUBAGENT_KEYS}

    def change(state):
        item = get_item(state, item_id)
        # An item is a subagent item or an implementer item, never both, so a
        # resume reads it one way.
        if base == "launch" and item.get("subagent") is not None:
            raise Usage(f"item '{item_id}' is a subagent item; set subagent null first")
        if base == "subagent" and (key or value is not None) and item.get("launch"):
            raise Usage(f"item '{item_id}' has a launch; a subagent item has none")
        if base == "launch" and key:
            item["launch"][key] = value
        elif base == "subagent" and key:
            item["subagent"] = item.get("subagent") or {k: None for k in SUBAGENT_KEYS}
            item["subagent"][key] = value
        elif base == "group":
            if value is not None:
                get_group(state, value)
            old = state["groups"].get(item.get("group") or "")
            if old and value != old["id"]:
                old["order"] = [i for i in old["order"] if i != item_id]
                old["owners"] = {k: v for k, v in old["owners"].items() if v != item_id}
            item["group"] = value
        else:
            pr_match = PR_URL_RE.fullmatch((item.get("pr") or {}).get("url") or "")
            if base == "repo" and pr_match and pr_match.group(1).lower() != value.lower():
                raise Usage(f"the item's PR is in {pr_match.group(1)}; set the PR first, then the repo")
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

    rec.mutate(lambda state: append_told(rec, state, pos[0], body))


def append_told(rec: Record, state: dict, item_id: str, body: str) -> str:
    """Write one message to told/ and list it on the item. Return its path in the record."""
    item = get_item(state, item_id)
    rel = f"told/{item['id']}-{len(item['told']) + 1}.md"
    rec.told.mkdir(exist_ok=True)
    (rec.dir / rel).write_text(body, encoding="utf-8")
    item["told"].append({"at": now_iso(), "path": rel})
    return rel


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
    counts. A run with no `startedAt` is the latest of its name. A skipped or
    neutral run counts as a pass.
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
        # A run with no start time is queued or waiting, so it is the newest
        # run of its name. Of two such runs, the later one in the list wins.
        # gh prints an unset start time as the zero time, 0001-01-01T00:00:00Z.
        stamp = check.get("startedAt") or ""
        if not stamp or stamp.startswith("0001-01-01"):
            stamp = "\uffff"
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

    rec.mutate(lambda state: apply_refresh(state, results))


def apply_refresh(state: dict, results: dict) -> None:
    """Write what `read_pr` returned into each item's `github`."""
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


# ---------------------------------------------------------------- helpers for the commands

EVENT_CAP = 50
SKILLS_DIR = Path(__file__).resolve().parents[2]


def sh(argv: list, timeout: int = 120):
    """Run a program. Return (returncode, stdout, stderr). A missing program is code 127."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        return 127, "", f"{argv[0]} is not installed"
    except subprocess.TimeoutExpired:
        return 124, "", f"{argv[0]} timed out after {timeout}s"
    return proc.returncode, proc.stdout, proc.stderr


def watch_cmd() -> list:
    """window-watch.py, or the stub that $CREW_ORCH_WATCH names."""
    env = os.environ.get("CREW_ORCH_WATCH")
    return [env] if env else [sys.executable, str(SKILLS_DIR / "delivered-window" / "scripts" / "window-watch.py")]


def sessions_dir() -> Path:
    env = os.environ.get("CREW_SESSIONS_DIR")
    return Path(env).expanduser() if env else Path.home() / ".claude" / "sessions"


def current_session_name():
    """The `name` of the session file whose `sessionId` is $CLAUDE_CODE_SESSION_ID, or None."""
    wanted = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if not wanted:
        return None
    for path in sorted(sessions_dir().glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and data.get("sessionId") == wanted and data.get("name"):
            return str(data["name"])
    return None


def add_event(state: dict, item_id, text: str) -> None:
    """Append a routine event to the record. The list keeps the last EVENT_CAP."""
    events = state.setdefault("events", [])
    events.append({"at": now_iso(), "item": item_id, "text": text})
    del events[:-EVENT_CAP]


def is_delivered(rec: Record, item_id: str) -> bool:
    """True when a goal record that names this item is at run_state `delivered`."""
    for path in sorted(record_root().glob("*/state.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8")).get("run") or {}
        except (OSError, ValueError, AttributeError):
            continue
        o = run.get("orchestrator") or {}
        if str(o.get("name")) == rec.name and str(o.get("item")) == item_id and run.get("run_state") == "delivered":
            return True
    return False


def deliver(rec: Record, item_id: str, text: str, sender: str, pending: bool = False) -> dict:
    """Record a message to an item and deliver it when a script can.

    A subagent item gets no word (`none`). A delivered item gets `window-watch.py say`
    (`said`). A live item gets nothing sent: the action `send-to` names its session and
    the recorded copy, and with `pending` the record keeps the handoff until
    `handoff clear`. No script sends a cross-session message.
    """
    delivered = is_delivered(rec, item_id)

    def change(state):
        item = get_item(state, item_id)
        if item.get("subagent"):
            return {"kind": "none", "item": item_id}
        name = (item.get("launch") or {}).get("session_name")
        if not delivered and not name:
            return {"kind": "none", "item": item_id}
        rel = append_told(rec, state, item_id, text)
        if delivered:
            return {"kind": "said", "item": item_id, "path": rel}
        if pending:
            state["handoffs"].append({"item": item_id, "name": name, "path": rel, "at": now_iso()})
        return {"kind": "send-to", "item": item_id, "name": name, "path": rel}

    action = rec.mutate(change)
    if action["kind"] == "said":
        rc, _, err = sh(watch_cmd() + ["say", "--item", f"{rec.name}/{item_id}", "--from", sender, text])
        if rc != 0:
            raise Fail(f"say to {item_id} failed: {last_line(err, f'exit {rc}')}")
    return action


def show_action(rec: Record, action: dict) -> None:
    if action["kind"] == "said":
        print(f"said: {action['item']}")
    elif action["kind"] == "send-to":
        print(f"send-to: {action['name']}")
        print(f"told: {rec.dir / action['path']}")


def sender_name(rec: Record, opts: dict) -> str:
    return opts.get("from") or current_session_name() or rec.name


# ---------------------------------------------------------------- merge

READY_RE = re.compile(r"ready\s*:?\s*([0-9a-fA-F]{7,40})")
UNRECOVERABLE = {"no PR", "conflict", "ci failing", "draft", "changes requested", "blocked", "closed"}
THREADS_QUERY = (
    "query($owner: String!, $repo: String!, $n: Int!) {"
    " repository(owner: $owner, name: $repo) {"
    " pullRequest(number: $n) { reviewThreads(first: 100) { nodes { isResolved } } } } }"
)
MERGE_METHODS = [("rebase", "rebaseMergeAllowed"), ("squash", "squashMergeAllowed"), ("merge", "mergeCommitAllowed")]


def ready_sha(line):
    m = READY_RE.search(line or "")
    return m.group(1).lower() if m else None


def gh_data(argv: list, what: str, label: str = "merge"):
    out, err = run_gh(argv)
    if err:
        raise Code(10, f"{label} gh: {what}: {err}")
    try:
        return json.loads(out)
    except ValueError:
        raise Code(10, f"{label} gh: {what}: bad output")


def pr_files(repo: str, number: int) -> set:
    out, err = run_gh(["pr", "diff", str(number), "--repo", repo, "--name-only"])
    if err:
        raise Code(10, f"merge gh: pr diff {number}: {err}")
    return {ln.strip() for ln in out.splitlines() if ln.strip()}


def section_text(text: str, heading: str):
    """The body of a `## <heading>` section, or None. A `###` line does not end it."""
    body, inside = [], False
    for raw in (text or "").splitlines():
        if re.match(r"##(?!#)", raw.strip()):
            if inside:
                break
            inside = raw.strip() == f"## {heading}"
            continue
        if inside:
            body.append(raw)
    if not inside:
        return None
    return "\n".join(body).strip() or None


def merge_section(repo: str, default_branch):
    """The `Merge` section text: the repo file on the default branch, then the machine file."""
    if default_branch:
        out, err = run_gh(["api", f"repos/{repo}/contents/.claude/crew.md?ref={default_branch}"])
        if not err:
            try:
                data = json.loads(out)
                text = base64.b64decode(data["content"]).decode("utf-8")
                found = section_text(text, "Merge")
                if found:
                    return found
            except (ValueError, KeyError, TypeError):
                pass
    config = os.environ.get("CREW_CONFIG") or os.path.expanduser("~/.claude/crew/config.md")
    try:
        return section_text(Path(config).read_text(encoding="utf-8"), "Merge")
    except OSError:
        return None


def finding_lines(info: dict) -> list:
    """One line for each review or comment of someone other than the PR author."""
    me = ((info.get("author") or {}).get("login")) or ""
    lines = []
    for kind, rows in (("review", info.get("reviews") or []), ("comment", info.get("comments") or [])):
        for row in rows:
            who = ((row.get("author") or {}).get("login")) or "?"
            body = " ".join((row.get("body") or "").split())
            if not body or who == me or row.get("state") == "APPROVED":
                continue
            lines.append(f"finding: {who} {kind} {body[:120]}")
    return lines


def unfinished_before(state: dict, item: dict) -> list:
    group = state["groups"].get(item.get("group") or "")
    if not group or item["id"] not in group["order"]:
        return []
    earlier = group["order"][: group["order"].index(item["id"])]
    return [state["items"][i] for i in earlier if i in state["items"] and not finished(state["items"][i])]


def cmd_merge(rec: Record, args: list) -> None:
    form = 'merge <item> [--ready "<line>"] [--when-green] [--findings-answered]'
    pos, opts = take_options(args, {"ready": True, "when-green": False, "findings-answered": False})
    want(pos, 1, 1, form)
    item_id = pos[0]
    if "ready" in opts:
        sha = ready_sha(opts["ready"])
        if sha is None:
            raise Usage("--ready needs a line with the head sha: ready <sha>: ...")

        def store(state):
            item = get_item(state, item_id)
            if not item.get("pr"):
                raise Fail(f"item '{item_id}' has no PR; set one with: item {item_id} pr <number|url>")
            item["ready"] = {"sha": sha, "line": opts["ready"], "at": now_iso()}

        rec.mutate(store)
    state = rec.read()
    item = get_item(state, item_id)
    if not item.get("pr"):
        raise Fail(f"item '{item_id}' has no PR; set one with: item {item_id} pr <number|url>")
    cmd_refresh(rec, [item_id])
    state = rec.read()
    item = state["items"][item_id]
    repo, number = item["repo"], item["pr"]["number"]
    value = item["merge"]
    when_green = bool(opts.get("when-green"))

    def pending(why: str):
        if not when_green:
            raise Code(11, f"merge pending: {why}")

        def queue(st):
            if item_id not in st["merge_queue"]:
                st["merge_queue"].append(item_id)
                add_event(st, item_id, f"queued until green ({why})")

        rec.mutate(queue)
        print(f"queued: {item_id} ({why})")

    if value == "merged":
        finalize(rec, item_id)
        return
    if value in UNRECOVERABLE:
        raise Code(3, f"merge record: merge value is '{value}'")
    ready = item.get("ready")
    if ready is None and (item.get("subagent") or {}).get("ready"):
        line = item["subagent"]["ready"]
        ready = {"sha": ready_sha(line), "line": line} if ready_sha(line) else None
    info = gh_data(["pr", "view", str(number), "--repo", repo, "--json",
                    "headRefOid,reviews,comments,author,reviewDecision,state"], f"pr view {number}")
    head = (info.get("headRefOid") or "").lower()
    if ready is not None and not (head and head.startswith(ready["sha"])):
        raise Code(4, f"merge ready: the ready line is for {ready['sha']}, the head is {head[:12] or 'unknown'}")
    if value == "ci pending" or value.startswith("in queue"):
        return pending(value)
    if ready is None:
        return pending("no ready line for the head yet")
    if value.startswith("waits on"):
        mine = pr_files(repo, number)
        late = []
        for other in unfinished_before(state, item):
            if other.get("pr") and mine & pr_files(other["repo"], other["pr"]["number"]):
                late.append(other["id"])
        if late:
            raise Code(8, f"merge order: {', '.join(late)} merges first and shares a file")
        raise Code(3, f"merge record: merge value is '{value}'")
    owner, name = repo.split("/", 1)
    data = gh_data(["api", "graphql", "-f", f"query={THREADS_QUERY}", "-f", f"owner={owner}",
                    "-f", f"repo={name}", "-F", f"n={number}"], f"review threads {number}")
    try:
        nodes = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    except (KeyError, TypeError):
        raise Code(10, f"merge gh: review threads {number}: bad output")
    open_threads = sum(1 for n in nodes if not n.get("isResolved"))
    if open_threads:
        raise Code(5, f"merge threads: {open_threads} unresolved review thread(s)")
    findings = finding_lines(info)
    if findings and not opts.get("findings-answered"):
        for line in findings:
            print(line)
        print(f"ready: {ready['line']}")
        raise Code(6, f"merge findings: {len(findings)} finding(s) outside a thread; compare them with the ready "
                      f"line, then run again with --findings-answered")
    repo_info = gh_data(["repo", "view", repo, "--json",
                         "defaultBranchRef,rebaseMergeAllowed,squashMergeAllowed,mergeCommitAllowed"], "repo view")
    section = merge_section(repo, (repo_info.get("defaultBranchRef") or {}).get("name"))
    if value == "needs review" and section is None:
        raise Code(7, "merge approval: the PR needs a review and no Merge section replaces it")
    if section is not None:
        print("merge-section: the Merge section of the standing instructions takes over; no method ran")
        print(section)
        raise Code(9, "merge merge-section: a Merge section replaces the method")
    method = next((m for m, key in MERGE_METHODS if repo_info.get(key)), None)
    if method is None:
        raise Code(10, f"merge gh: {repo} allows no merge method")
    out, err = run_gh(["pr", "merge", str(number), "--repo", repo, f"--{method}", "--match-head-commit", head])
    if err:
        raise Code(10, f"merge gh: pr merge {number}: {err}")
    print(f"merge: {item_id} {method} {head[:12]}")
    finalize(rec, item_id)


# ---------------------------------------------------------------- after the merge

MERGE_WORD = ("PR #{n} of item {item} merged. Nothing more is open for the merge. "
              "Close out your work as your instructions say.")
REBASE_WORD = ("PR #{n} of item {merged} merged, and it shares a file with your PR. "
               "Rebase your branch on the base branch, resolve each conflict, run the tests and push.")


def finalize(rec: Record, item_id: str, sender=None) -> list:
    """Settle a PR after `gh pr merge` or at an event. Return the live-item actions.

    A fresh `gh pr view` read decides, never a stored value. `MERGED` releases the slot (once),
    sends the merge word, and sends the rebase word to the next item that shares a file.
    `OPEN` after a merge call is a queue at GitHub: nothing goes out, and the item stays in
    `merge_queue`. `CLOSED` releases the slot (once) and sends no word. A failed read changes
    nothing and exits 10.
    """
    state = rec.read()
    item = get_item(state, item_id)
    if not item.get("pr"):
        raise Fail(f"item '{item_id}' has no PR")
    repo, number = item["repo"], item["pr"]["number"]
    out, err = run_gh(["pr", "view", str(number), "--repo", repo, "--json", "state"])
    if err:
        def keep(st):
            if item_id not in st["merge_queue"]:
                st["merge_queue"].append(item_id)

        rec.mutate(keep)
        raise Code(10, f"merge gh: state of PR {number} not confirmed: {err}")
    try:
        pr_state = json.loads(out).get("state")
    except (ValueError, AttributeError):
        raise Code(10, f"merge gh: state of PR {number}: bad output")
    sender = sender or current_session_name() or rec.name
    actions = []

    if pr_state == "OPEN":
        def queue(st):
            if item_id not in st["merge_queue"]:
                st["merge_queue"].append(item_id)
                add_event(st, item_id, f"queued at GitHub (PR #{number})")

        rec.mutate(queue)
        rec.mutate(lambda st: st["items"][item_id].__setitem__("queued_at_github", True))
        print(f"queued: {item_id} (PR #{number} is not merged yet)")
        return actions

    def release(st):
        it = st["items"][item_id]
        if item_id in st["merge_queue"]:
            st["merge_queue"].remove(item_id)
        if it.get("subagent") or it.get("slot_released"):
            return False
        busy = st["pace"]["slots"]["busy"]
        st["pace"]["slots"]["busy"] = max(0, busy - 1)
        it["slot_released"] = True
        return True

    if pr_state == "CLOSED":
        if rec.mutate(release):
            rec.mutate(lambda st: add_event(st, item_id, f"PR #{number} closed with no merge, slot released"))
        print(f"closed: {item_id} (PR #{number} closed with no merge)")
        return actions
    if pr_state != "MERGED":
        raise Code(10, f"merge gh: state of PR {number}: {pr_state!r}")
    if rec.mutate(release):
        rec.mutate(lambda st: add_event(st, item_id, f"merged PR #{number}"))
    print(f"merged: {item_id} (PR #{number})")
    if not item.get("words_sent"):
        word = deliver(rec, item_id, MERGE_WORD.format(n=number, item=item_id), sender, pending=True)
        show_action(rec, word)
        actions.append(word)
        nxt = next_sharing(rec.read(), item)
        if nxt:
            word = deliver(rec, nxt["id"], REBASE_WORD.format(n=number, merged=item_id), sender, pending=True)
            show_action(rec, word)
            actions.append(word)
            rec.mutate(lambda st: add_event(st, nxt["id"], f"rebase word sent after {item_id} merged"))
            print(f"rebase-word: {nxt['id']}")

        def sent(st):
            st["items"][item_id]["words_sent"] = True

        rec.mutate(sent)
    return actions


def next_sharing(state: dict, item: dict):
    """The next unfinished item of the group order that shares a file with the merged PR."""
    group = state["groups"].get(item.get("group") or "")
    if not group or item["id"] not in group["order"]:
        return None
    later = group["order"][group["order"].index(item["id"]) + 1:]
    try:
        mine = pr_files(item["repo"], item["pr"]["number"])
    except Code:
        return None
    for other_id in later:
        other = state["items"].get(other_id)
        if other and other.get("pr") and not finished(other):
            try:
                if mine & pr_files(other["repo"], other["pr"]["number"]):
                    return other
            except Code:
                continue
    return None


def cmd_finalize(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    want(pos, 1, 1, "finalize <item>")
    finalize(rec, pos[0])


def cmd_handoff(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    if pos[:1] != ["clear"]:
        raise Usage("usage: handoff clear <item>")
    want(pos, 2, 2, "handoff clear <item>")

    def change(state):
        before = len(state["handoffs"])
        state["handoffs"] = [h for h in state["handoffs"] if h.get("item") != pos[1]]
        return before - len(state["handoffs"])

    print(f"cleared: {rec.mutate(change)}")


# ---------------------------------------------------------------- send, launch

SCRIPTS_DIR = Path(__file__).resolve().parent


def tool_cmd(env: str, script: str) -> list:
    """A sibling script, or the stub that the environment variable names."""
    stub = os.environ.get(env)
    return [stub] if stub else [sys.executable, str(SCRIPTS_DIR / script)]


def cmd_send(rec: Record, args: list) -> None:
    form = "send <item> (--text <t> | --file <p>) [--from <name>]"
    pos, opts = take_options(args, {"text": True, "file": True, "from": True})
    want(pos, 1, 1, form)
    if ("text" in opts) == ("file" in opts):
        raise Usage(f"usage: {form}")
    body = opts["text"] if "text" in opts else read_source(opts["file"])
    item = get_item(rec.read(), pos[0])
    if item.get("subagent"):
        raise Fail(f"item '{pos[0]}' is a subagent item: send its words with SendMessage")
    action = deliver(rec, pos[0], body, sender_name(rec, opts))
    if action["kind"] == "none":
        raise Fail(f"item '{pos[0]}' has no session name; launch it first")
    show_action(rec, action)


def checkout_path(repo: str) -> str:
    """The path of the `## Checkouts` line for `repo` in the machine file."""
    config = os.environ.get("CREW_CONFIG") or os.path.expanduser("~/.claude/crew/config.md")
    try:
        text = Path(config).read_text(encoding="utf-8")
    except OSError:
        text = ""
    inside = False
    for raw in text.splitlines():
        line = raw.strip()
        if re.match(r"##(?!#)", line):
            inside = line == "## Checkouts"
            continue
        if not inside or line.startswith("#"):
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        m = re.fullmatch(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s*:\s*(\S.*)", line)
        if m and m.group(1).lower() == repo.lower():
            return os.path.expanduser(m.group(2).strip().strip("`"))
    raise Fail(f"no Checkouts line for {repo} in {config}")


def cmd_launch(rec: Record, args: list) -> None:
    form = ("launch <item> [--model <m>] [--group <g>] [--terminal <t>] [--principal <name>] "
            "[--goal-file <p>] [--wait-seconds <n>]")
    pos, opts = take_options(args, {"model": True, "group": True, "terminal": True, "principal": True,
                                    "goal-file": True, "wait-seconds": True})
    want(pos, 1, 1, form)
    try:
        wait_seconds = float(opts.get("wait-seconds", 60))
    except ValueError:
        raise Usage("--wait-seconds takes a number")
    state = rec.read()
    item = get_item(state, pos[0])
    if item.get("subagent") or item.get("launch"):
        raise Fail(f"item '{pos[0]}' is a subagent item or already has a launch")
    pace = state["pace"]
    if pace["mode"] != "normal":
        raise Code(3, f"launch refused: pace mode is {pace['mode']}")
    if pace["slots"]["busy"] >= pace["slots"]["max"]:
        raise Code(3, f"launch refused: {pace['slots']['busy']} of {pace['slots']['max']} slots are busy")
    goal = read_source(opts["goal-file"]) if "goal-file" in opts else None
    name = item["id"].replace("_", "-")
    rc, top, err = sh(["git", "-C", checkout_path(item["repo"]), "rev-parse", "--show-toplevel"])
    if rc != 0:
        raise Fail(f"git rev-parse in the checkout failed: {last_line(err, f'exit {rc}')}")
    worktree = os.path.join(os.path.realpath(top.strip()), ".claude", "worktrees", name)
    rc, settings, err = sh(tool_cmd("CREW_USAGE_CMD", "crew-usage.py") + ["settings", "--cwd", worktree])
    if rc != 0:
        raise Fail(f"crew-usage.py settings failed: {last_line(err, f'exit {rc}')}")
    principal = opts.get("principal") or current_session_name()
    if not principal:
        raise Fail("no principal: pass --principal <your session name>")
    argv = tool_cmd("CREW_ORCH_LAUNCHER", "launcher.py") + ["start", "--name", name]
    if "model" in opts:
        argv += ["--model", opts["model"]]
    argv += ["--settings", settings.strip(), "--principal", principal, "--repo", item["repo"]]
    if "group" in opts:
        argv += ["--group", opts["group"]]
    if "terminal" in opts:
        argv += ["--terminal", opts["terminal"]]
    rc, out, err = sh(argv, timeout=180)
    if rc != 0:
        raise Fail(f"launcher.py start exited {rc}: {last_line(err, 'no message')}")
    try:
        started = json.loads(last_line(out, ""))
        if not isinstance(started, dict):
            raise ValueError
    except ValueError:
        raise Fail(f"launcher.py start printed no JSON line: {last_line(out, '(nothing)')}")
    print(last_line(out, ""))

    def change(st):
        it = get_item(st, item["id"])
        it["launch"] = {k: started.get(k) for k in LAUNCH_KEYS}
        st["pace"]["slots"]["busy"] += 1
        if goal is not None:
            append_told(rec, st, item["id"], goal)

    rec.mutate(change)
    session = started.get("session_name") or name
    deadline = time.monotonic() + wait_seconds
    while True:
        if any(isinstance(d, dict) and d.get("name") == session for d in session_files()):
            print(f"goal-ready: {session}")
            return
        if time.monotonic() >= deadline:
            print(f"goal-wait: no session named {session} after {wait_seconds:g}s; "
                  f"the tab {started.get('tab')} can wait on the trust dialog")
            return
        time.sleep(min(0.5, max(0.05, deadline - time.monotonic())))


def session_files() -> list:
    found = []
    for path in sorted(sessions_dir().glob("*.json")):
        try:
            found.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            continue
    return found


# ---------------------------------------------------------------- close-item

PROCESS_WORD = ("Orchestrator: {orch}, item {item}\n"
                "My session name is {me}; send to that name. The item is closing. Stop each process and "
                "service that you started for the item, such as a server, a container, a watcher or a local "
                "stack. Answer with what you stopped.")
ISSUE_URL_RE = re.compile(r"https://github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)/issues/([0-9]+)")


def add_notice(rec: Record, item_id: str, text: str) -> None:
    entry = add_entry(rec, "notice", "principal", item_id, text, None)
    print(f"notice: {entry} {text}")


def cmd_close_item(rec: Record, args: list) -> None:
    form = "close-item <item> [--continue] [--stop-processes]"
    pos, opts = take_options(args, {"continue": False, "stop-processes": False})
    want(pos, 1, 1, form)
    item_id = pos[0]
    item = get_item(rec.read(), item_id)
    if not opts.get("continue"):
        if opts.get("stop-processes"):
            raise Usage(f"usage: {form}; --stop-processes goes with --continue")
        sender = sender_name(rec, {})
        text = PROCESS_WORD.format(orch=rec.name, item=item_id, me=sender)
        action = deliver(rec, item_id, text, sender)
        if action["kind"] == "none":
            print(f"processes: no word sent for {item_id} (a subagent item, or no session recorded)")
        else:
            show_action(rec, action)
        rec.mutate(lambda st: get_item(st, item_id).__setitem__("close_asked_at", now_iso()))
        return
    close_stop_remove(rec, item, bool(opts.get("stop-processes")))
    close_ticket(rec, rec.read()["items"][item_id])


def close_stop_remove(rec: Record, item: dict, stop_processes: bool) -> None:
    item_id = item["id"]
    launch = item.get("launch") or {}
    sub = item.get("subagent")
    launcher = tool_cmd("CREW_ORCH_LAUNCHER", "launcher.py")
    if sub:
        print("stop: skipped (a subagent item has no session)")
        worktree = sub.get("worktree")
    else:
        worktree = launch.get("worktree")
        tab = launch.get("tab")
        if not tab:
            print("stop: skipped (no tab recorded)")
        else:
            argv = launcher + ["stop", tab]
            if launch.get("session_name"):
                argv += ["--name", launch["session_name"]]
            if launch.get("session_id"):
                argv += ["--session-id", launch["session_id"]]
            rc, out, err = sh(argv, timeout=180)
            if rc != 0:
                print(f"stop: failed, exit {rc}: {last_line(err, 'no message')}")
                add_notice(rec, item_id, f"The session of {item_id} did not stop (launcher.py stop exit {rc}); "
                                         f"its worktree stays: {worktree}")
                return
            print(f"stop: {last_line(out, 'done')}")
    if not worktree:
        print("remove: skipped (no worktree recorded)")
        return
    argv = launcher + ["remove", worktree]
    if landed(item) and item.get("pr"):
        argv += ["--delete-branch", "--pr", str(item["pr"]["number"])]
    elif not item.get("pr"):
        argv += ["--delete-branch"]
    if stop_processes:
        argv += ["--stop-processes"]
    rc, out, err = sh(argv, timeout=300)
    try:
        info = json.loads(last_line(out, ""))
        if not isinstance(info, dict):
            raise ValueError
    except ValueError:
        info = None
    if rc == 0 and info is not None:
        print(f"remove: removed {worktree}")
        kept = [b for b in info.get("branches") or [] if not b.get("deleted")]
        if kept:
            parts = []
            for b in kept:
                why = (f"checked out in {b['checked_out']}" if b.get("checked_out")
                       else f"{len(b.get('unproven_commits') or [])} unproven commit(s)")
                parts.append(f"{b.get('name')} ({why})")
            add_notice(rec, item_id, f"Kept branch of {item_id}: {'; '.join(parts)}. Never deleted by the orchestrator.")
        return
    if rc == 9 and info is not None:
        procs = info.get("kept") or []
        only_procs = (procs and not info.get("changed") and not (info.get("lock") or {}).get("reason")
                      and all(p.get("tty") is None for p in procs))
        if only_procs and not stop_processes:
            for p in procs:
                print(f"kept-process: {p.get('pid')} {p.get('command')}")
            print(f"remove: kept {worktree}; when each process is the item's own, run: "
                  f"close-item {item_id} --continue --stop-processes")
            return
        bits = [f"{len(info.get('changed') or [])} changed file(s)"] if info.get("changed") else []
        bits += [f"process {p.get('pid')} {p.get('command')}" for p in procs]
        if (info.get("lock") or {}).get("reason") is not None and info.get("lock"):
            bits.append("a lock")
        add_notice(rec, item_id, f"Removal of {worktree} was refused: {', '.join(bits) or last_line(err, 'see launcher')}.")
        return
    print(f"remove: failed, exit {rc}: {last_line(err, 'no message')}")
    add_notice(rec, item_id, f"Removal of {worktree} failed with exit {rc}: {last_line(err, 'no message')}.")


def close_ticket(rec: Record, item: dict) -> None:
    ticket = item.get("ticket")
    if not ticket:
        print("ticket: none")
        return
    m = ISSUE_URL_RE.fullmatch(ticket.get("url") or "")
    if not m:
        print(f"ticket: {ticket['id']} is not a GitHub issue; close it as the standing instructions say")
        return
    repo, number = m.group(1), m.group(2)
    if not landed(item):
        print(f"ticket: {ticket['id']} left open (the item closed with no merge)")
        add_notice(rec, item["id"], f"{item['id']} closed with no merge; ticket {ticket['id']} stays open.")
        return
    out, err = run_gh(["issue", "view", number, "--repo", repo, "--json", "state"])
    if err:
        print(f"ticket: could not read {ticket['id']}: {err}")
        add_notice(rec, item["id"], f"Could not read ticket {ticket['id']} of {item['id']}: {err}")
        return
    try:
        state = json.loads(out).get("state")
    except (ValueError, AttributeError):
        state = None
    if state == "CLOSED":
        print(f"ticket: {ticket['id']} already closed")
        return
    out, err = run_gh(["issue", "close", number, "--repo", repo])
    if err:
        print(f"ticket: could not close {ticket['id']}: {err}")
        add_notice(rec, item["id"], f"Could not close ticket {ticket['id']} of {item['id']}: {err}")
        return
    print(f"ticket: closed {ticket['id']}")


# ---------------------------------------------------------------- digest

BRIEF_CHARS = 600


def first_brief(rec: Record, item: dict) -> str:
    told = item.get("told") or []
    if not told:
        return ""
    try:
        return (rec.dir / told[0]["path"]).read_text(encoding="utf-8")
    except OSError:
        return ""


def cmd_digest(rec: Record, args: list) -> None:
    form = "digest <item> [--diff-file <path>]"
    pos, opts = take_options(args, {"diff-file": True})
    want(pos, 1, 1, form)
    item_id = pos[0]
    item = get_item(rec.read(), item_id)
    if not item.get("pr"):
        raise Fail(f"item '{item_id}' has no PR; set one with: item {item_id} pr <number|url>")
    cmd_refresh(rec, [item_id])
    state = rec.read()
    item = state["items"][item_id]
    repo, number = item["repo"], item["pr"]["number"]
    brief = first_brief(rec, item)
    info = gh_data(["pr", "view", str(number), "--repo", repo, "--json", "files,reviews,comments,author"],
                   f"pr view {number}", "digest")
    owner, name = repo.split("/", 1)
    data = gh_data(["api", "graphql", "-f", f"query={THREADS_QUERY}", "-f", f"owner={owner}",
                    "-f", f"repo={name}", "-F", f"n={number}"], f"review threads {number}", "digest")
    try:
        nodes = data["data"]["repository"]["pullRequest"]["reviewThreads"]["nodes"]
    except (KeyError, TypeError):
        raise Code(10, f"digest gh: review threads {number}: bad output")
    open_threads = sum(1 for n in nodes if not n.get("isResolved"))
    print(f"brief: {' '.join(brief.split())[:BRIEF_CHARS] or '(none recorded)'}")
    for f in info.get("files") or []:
        print(f"file: {f.get('path')} +{f.get('additions', 0)} -{f.get('deletions', 0)}")
    print(f"threads: {open_threads} unresolved")
    for line in finding_lines(info):
        print(line)
    print(f"ci: {(item.get('github') or {}).get('checks') or 'unknown'}")
    mine = pr_files(repo, number)
    group = state["groups"].get(item.get("group") or "")
    if group:
        for other_id in group["order"]:
            other = state["items"].get(other_id)
            if other and other_id != item_id and other.get("pr") and not finished(other):
                shared = sorted(mine & pr_files(other["repo"], other["pr"]["number"]))
                if shared:
                    print(f"shared with {other_id}: {', '.join(shared)}")
        print(f"order: {', '.join(group['order'])}")
    else:
        print("order: none (a single item)")
    if "diff-file" in opts:
        out, err = run_gh(["pr", "diff", str(number), "--repo", repo])
        if err:
            raise Code(10, f"digest gh: pr diff {number}: {err}")
        Path(opts["diff-file"]).write_text(f"# Brief\n\n{brief}\n\n# Diff\n\n{out}", encoding="utf-8")
        print(f"diff-file: {opts['diff-file']}")


# ---------------------------------------------------------------- resume


def find_handles(item: dict) -> list:
    """[(handle, match)] from `launcher.py find`, or raise Fail."""
    launch = item["launch"]
    argv = tool_cmd("CREW_ORCH_LAUNCHER", "launcher.py") + ["find", launch["session_name"]]
    if launch.get("worktree"):
        argv += ["--worktree", launch["worktree"]]
    if launch.get("session_id"):
        argv += ["--session-id", launch["session_id"]]
    rc, out, err = sh(argv, timeout=60)
    if rc != 0:
        raise Fail(f"launcher.py find {launch['session_name']} exited {rc}: {last_line(err, 'no message')}")
    pairs = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2:
            pairs.append((parts[0], parts[1]))
    return pairs


def goal_record_dir(rec: Record, item_id: str):
    for path in sorted(record_root().glob("*/state.json")):
        try:
            run = json.loads(path.read_text(encoding="utf-8")).get("run") or {}
        except (OSError, ValueError, AttributeError):
            continue
        o = run.get("orchestrator") or {}
        if str(o.get("name")) == rec.name and str(o.get("item")) == item_id:
            return path.parent
    return None


def resume_item(rec: Record, item: dict, read_only: bool) -> tuple:
    """Return (action line, counts as a live implementer)."""
    item_id = item["id"]
    stage = item["stage"]
    launch = item.get("launch") or {}
    sub = item.get("subagent")
    before_merge = STAGES.index(stage) < STAGES.index("merged")
    if sub:
        what = {"queued": "dispatch it as the subagent items reference says",
                "build": "dispatch it again under the same name and brief",
                "pr": "dispatch it again only when its ready line is not for the current head",
                "merged": "write its deploy watch input file again when one ran",
                }.get(stage, "close it when its worktree is still there")
        return f"{item_id} subagent: stage {stage}; {what}", False
    if not launch:
        if stage == "queued":
            return f"{item_id} launch: not launched yet; run launch {item_id}", False
        return f"{item_id} ok: stage {stage}, no session recorded", False
    if stage in DONE_STAGES:
        pairs = [p for p in find_handles(item) if p[1] in ("name", "id")]
        if not pairs:
            return (f"{item_id} close: stage {stage}; its session is gone; run close-item {item_id} --continue"), False
        handle = pairs[0][0]
        if handle != launch.get("tab") and not read_only:
            rec.mutate(lambda st: st["items"][item_id]["launch"].__setitem__("tab", handle))
        return (f"{item_id} close: stage {stage}; its session is alive at {handle}; "
                f"run close-item {item_id} (--continue after its answer)"), False
    if is_delivered(rec, item_id) and stage in ("pr", "merged"):
        gdir = goal_record_dir(rec, item_id)
        if read_only or gdir is None:
            note = "no goal record found" if gdir is None else "ensure not run (read-only)"
            return f"{item_id} window: delivered; {note}; reach it with send", before_merge
        rc, out, err = sh(watch_cmd() + ["ensure", str(gdir)], timeout=60)
        result = last_line(out, f"exit {rc}: {last_line(err, 'no message')}")
        return f"{item_id} window: delivered; watcher {result}; reach it with send", before_merge
    pairs = find_handles(item)
    names = [p for p in pairs if p[1] == "name"]
    ids = [p for p in pairs if p[1] == "id"]
    cwds = [p for p in pairs if p[1] == "cwd"]
    told = bool(item.get("told"))
    if names:
        handle = names[0][0]
        moved = handle != launch.get("tab")
        if moved and not read_only:
            rec.mutate(lambda st: st["items"][item_id]["launch"].__setitem__("tab", handle))
        tasks = ("its process restarted (new handle {h}); tell it to arm its background tasks and watches "
                 "again".format(h=handle)) if moved else "alive; tell it to arm only a watch it does not hold"
        if not told:
            return f"{item_id} send-goal: alive at {handle} but its told holds no goal; send the goal now", before_merge
        return f"{item_id} rejoin: {tasks}; ask for its ready line, stage and open questions", before_merge
    if ids:
        h = ids[0][0]
        return (f"{item_id} restart: alive at {h}, matched by id only; run launcher.py stop {h} --name "
                f"{launch['session_name']} --session-id {launch.get('session_id')}, then resume it"), before_merge
    if cwds:
        h = cwds[0][0]
        return (f"{item_id} notice: a session at {h} matches by working directory only; never stop it; "
                f"add a notice for the principal"), False
    worktree = launch.get("worktree")
    if not worktree or not os.path.isdir(worktree):
        return f"{item_id} notice: gone, and its worktree is gone; nothing can resume it; add a notice", False
    if read_only:
        return f"{item_id} resume: gone, its worktree exists; run resume to restart it", before_merge
    rc, settings, err = sh(tool_cmd("CREW_USAGE_CMD", "crew-usage.py") + ["settings", "--cwd", worktree])
    if rc != 0:
        return f"{item_id} notice: settings value failed: {last_line(err, f'exit {rc}')}", False
    argv = tool_cmd("CREW_ORCH_LAUNCHER", "launcher.py") + ["resume", "--name", launch["session_name"],
                                                              "--worktree", worktree]
    if launch.get("session_id"):
        argv += ["--session-id", launch["session_id"]]
    if launch.get("model"):
        argv += ["--model", launch["model"]]
    argv += ["--settings", settings.strip()]
    if launch.get("repo") or item.get("repo"):
        argv += ["--repo", launch.get("repo") or item["repo"]]
    if launch.get("tab_group"):
        argv += ["--group", launch["tab_group"]]
    if launch.get("terminal"):
        argv += ["--terminal", launch["terminal"]]
    rc, out, err = sh(argv, timeout=180)
    if rc != 0:
        return (f"{item_id} notice: launcher.py resume exited {rc}: {last_line(err, 'no message')}; "
                f"add a notice or run find"), False
    try:
        started = json.loads(last_line(out, ""))
        merged = dict(launch)
        merged.update({k: started.get(k) for k in LAUNCH_KEYS if started.get(k) is not None})
        rec.mutate(lambda st: st["items"][item_id].__setitem__("launch", merged))
    except ValueError:
        return f"{item_id} notice: launcher.py resume printed no JSON line", False
    after = (f"resumed in {started.get('tab')}; tell it to arm its background tasks and watches again"
             if told else f"resumed in {started.get('tab')}; its told holds no goal; send the goal now")
    return f"{item_id} {'rejoin' if told else 'send-goal'}: {after}", before_merge


def cmd_resume(rec: Record, args: list) -> None:
    pos, opts = take_options(args, {"read-only": False})
    want(pos, 0, 0, "resume [--read-only]")
    read_only = bool(opts.get("read-only"))
    state = rec.read()
    if state.get("closed_at"):
        print(f"closed: the record '{rec.name}' is closed at {state['closed_at']}; do nothing more")
        return
    session = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if session and not read_only and state.get("orchestrator_session_id") != session:
        rec.mutate(lambda st: st.__setitem__("orchestrator_session_id", session))
    live = 0
    for item in sorted(state["items"].values(), key=lambda i: i["n"]):
        line, counts = resume_item(rec, rec.read()["items"][item["id"]], read_only)
        print(line)
        live += 1 if counts else 0
    if not read_only:
        rec.mutate(lambda st: st["pace"]["slots"].__setitem__("busy", live))


# ---------------------------------------------------------------- wait

DEFAULT_INTERVAL = 60.0
INBOX_TEXT_CHARS = 80
ROUTINE_FOR_IMPLEMENTER = {"check", "conflict", "comment", "review"}


class Superseded(Exception):
    """Another `wait` owns the record now: stop, and write nothing."""


def check_owner(state: dict, token: str) -> None:
    if (state.get("wait_owner") or {}).get("token") != token:
        raise Superseded()


def claim_owner(rec: Record, token: str):
    """Write this poller as the owner, under the record lock. Return the old owner, or None."""
    def change(state):
        old = state.get("wait_owner")
        state["wait_owner"] = {"token": token, "pid": os.getpid()}
        state["wait_pid"] = os.getpid()
        if "wait_seen_inbox" not in state:
            state["wait_seen_inbox"] = [e["id"] for e in state["inbox"]]
        return old

    return rec.mutate(change)


def release_owner(rec: Record, token: str) -> None:
    """Clear the owner only when it is still this poller."""
    def change(state):
        if (state.get("wait_owner") or {}).get("token") == token:
            state["wait_owner"] = None
            state["wait_pid"] = None

    try:
        rec.mutate(change)
    except (Fail, OSError):
        pass


def stop_old_poller(old) -> None:
    """Stop an older `wait`, only when the process still runs a `crew-orch.py ... wait` command."""
    pid = (old or {}).get("pid")
    if not isinstance(pid, int) or pid <= 1 or pid == os.getpid():
        return
    rc, out, _ = sh(["ps", "-o", "command=", "-p", str(pid)], timeout=10)
    words = out.split()
    if rc != 0 or not any(w.endswith("crew-orch.py") for w in words) or "wait" not in words:
        return
    try:
        os.kill(pid, signal.SIGTERM)
    except OSError:
        return
    for _ in range(40):
        try:
            os.kill(pid, 0)
        except OSError:
            return
        time.sleep(0.1)


def row_key(row: dict) -> str:
    return str(row.get("id") or f"{(row.get('author') or {}).get('login')}|{row.get('createdAt')}|"
                               f"{(row.get('body') or '')[:30]}")


def rows_of(info: dict, field: str) -> list:
    return [{"id": row_key(r), "author": (r.get("author") or {}).get("login") or "?",
             "at": r.get("createdAt") or "", "text": " ".join((r.get("body") or "").split())[:INBOX_TEXT_CHARS],
             "state": r.get("state") or ""} for r in info.get(field) or []]


def poll_usage(rec: Record, token: str, state: dict) -> list:
    pace = state["pace"]
    rc, out, _ = sh(tool_cmd("CREW_USAGE_CMD", "crew-usage.py") + ["check", "--limit", str(pace.get("limit_pct", 95))],
                    timeout=60)
    words = out.split()
    level = words[0] if words else None
    prev = pace["mode"]
    if level not in PACE_MODES or level == prev:
        return []
    tail = " ".join(words[1:])

    def change(st):
        check_owner(st, token)
        p = st["pace"]
        slots = p["slots"]
        if level != "normal" and prev == "normal":
            slots["normal_max"] = slots["max"]
        if level == "slowed":
            slots["max"] = 1
        if level == "normal":
            slots["max"] = slots.pop("normal_max", 3 if slots["max"] == 1 else slots["max"])
        p["mode"] = level
        add_event(st, None, f"mode {level} (was {prev})")

    rec.mutate(change)
    if level != "normal" and (prev == "normal" or level == "stopped"):
        return [f"wake usage -: level={level} was={prev} {tail}".rstrip()]
    if level == "normal":
        return [f"wake usage -: reset level=normal was={prev} {tail}".rstrip()]
    return []


def quiet(call, *args):
    """Run a command function with its stdout dropped."""
    with contextlib.redirect_stdout(io.StringIO()):
        return call(*args)


def poll_prs(rec: Record, token: str) -> list:
    wakes = []
    state = rec.read()
    check_owner(state, token)
    for item in sorted(state["items"].values(), key=lambda i: i["n"]):
        if not item.get("pr") or item["stage"] in DONE_STAGES:
            continue
        item_id, repo, number = item["id"], item["repo"], item["pr"]["number"]
        result = read_pr(repo, number)
        if result["fields"] is None:
            continue
        out, err = run_gh(["pr", "view", str(number), "--repo", repo, "--json",
                           "reviewDecision,reviews,comments,author"])
        info = None
        if not err:
            try:
                info = json.loads(out)
            except ValueError:
                info = None
        found = {"wakes": [], "merged": False, "closed": False}

        def change(st):
            check_owner(st, token)
            it = st["items"].get(item_id)
            if it is None or not it.get("pr") or it["pr"]["number"] != number:
                return
            old = dict(it.get("github") or {})
            apply_refresh(st, {item_id: (number, result)})
            new = it.get("github") or {}
            if old:
                if new.get("checks") == "fail" and old.get("checks") != "fail":
                    found["wakes"].append(("check", f"failed {', '.join(new.get('failed_checks') or []) or 'a check'}"))
                if new.get("merge_state") == "DIRTY" and old.get("merge_state") != "DIRTY":
                    found["wakes"].append(("conflict", "the PR conflicts with the base"))
                if new.get("review_decision") == "APPROVED" and old.get("review_decision") != "APPROVED":
                    found["wakes"].append(("review", "approved"))
                if new.get("in_queue") != old.get("in_queue") and new.get("state") == "OPEN":
                    pos = new.get("queue_position")
                    if new.get("in_queue"):
                        # An entry into the queue needs no decision: the board shows it.
                        add_event(st, item_id, f"queue: in queue {pos}")
                    else:
                        found["wakes"].append(("queue", "left the queue"))
                if new.get("state") == "CLOSED" and old.get("state") != "CLOSED":
                    found["closed"] = True
                if (new.get("state") == "MERGED" and not it.get("words_sent")
                        and (old.get("state") != "MERGED" or item_id in st["merge_queue"])):
                    found["merged"] = True
            if info is not None:
                me = (info.get("author") or {}).get("login") or ""
                reviews, comments = rows_of(info, "reviews"), rows_of(info, "comments")
                before = it.get("watch")
                if before is not None:
                    seen = {r["id"] for r in before.get("reviews", [])}
                    for r in reviews:
                        if r["id"] not in seen and r["author"] != me:
                            found["wakes"].append(("review", f"{r['author']} {r['state']} {r['text']}".strip()))
                    seen = {r["id"] for r in before.get("comments", [])}
                    for r in comments:
                        if r["id"] not in seen and r["author"] != me:
                            found["wakes"].append(("comment", f"{r['author']} {r['text']}".strip()))
                it["watch"] = {"reviews": [{k: r[k] for k in ("id", "author", "at")} for r in reviews],
                               "comments": [{k: r[k] for k in ("id", "author", "at")} for r in comments]}
            # An implementer item has a project lead or a window session that handles its own
            # PR. Its check, conflict, comment and review events are routine: the board shows
            # them and nobody wakes. A subagent item, and an item in merge_queue, still wake.
            if it.get("launch") and not it.get("subagent") and item_id not in st["merge_queue"]:
                kept = []
                for kind, text in found["wakes"]:
                    if kind in ROUTINE_FOR_IMPLEMENTER and text != "approved":
                        add_event(st, item_id, f"{kind}: {text}")
                    else:
                        kept.append((kind, text))
                found["wakes"] = kept

        rec.mutate(change)
        wakes += [f"wake {kind} {item_id}: {text}" for kind, text in found["wakes"]]
        if found["merged"] or found["closed"]:
            check_owner(rec.read(), token)
            try:
                quiet(finalize, rec, item_id)
            except (Code, Fail):
                pass
            if found["closed"]:
                wakes.append(f"wake closed {item_id}: PR #{number} closed with no merge; its slot is released")
    wakes += run_queued_merges(rec, token)
    return wakes


def run_queued_merges(rec: Record, token: str) -> list:
    wakes = []
    state = rec.read()
    for item_id in list(state["merge_queue"]):
        item = state["items"].get(item_id)
        gh = (item or {}).get("github") or {}
        if item is None or item.get("queued_at_github") or gh.get("state") != "OPEN" \
                or gh.get("checks") not in ("pass", "none"):
            continue
        check_owner(rec.read(), token)
        try:
            quiet(cmd_merge, rec, [item_id, "--when-green"])
        except Code as err:
            if err.code == 11 or "not confirmed" in err.line:
                continue
            failure = (err.code, err.line)
        except (Fail, Usage) as err:
            failure = (1, str(err))
        else:
            continue

        def drop(st):
            check_owner(st, token)
            if item_id in st["merge_queue"]:
                st["merge_queue"].remove(item_id)
            add_event(st, item_id, f"queued merge failed: exit {failure[0]}")

        rec.mutate(drop)
        wakes.append(f"wake merge-failed {item_id}: exit {failure[0]} {failure[1]}")
    return wakes


def poll_inbox(rec: Record, token: str) -> list:
    state = rec.read()
    seen = set(state.get("wait_seen_inbox") or [])
    fresh = [e for e in state["inbox"] if e["id"] not in seen]
    if not fresh:
        return []

    def change(st):
        check_owner(st, token)
        st["wait_seen_inbox"] = sorted(set(st.get("wait_seen_inbox") or []) | {e["id"] for e in fresh})

    rec.mutate(change)
    return [f"wake inbox {e.get('item') or '-'}: {e['id']} {e['text'][:INBOX_TEXT_CHARS]}"
            for e in fresh if e["for"] == "orchestrator" and e["state"] == "open"]


def poll_handoffs(rec: Record) -> list:
    return [f"wake send {h['item']}: send-to {h['name']} told {rec.dir / h['path']}"
            for h in rec.read()["handoffs"]]


def poll_once(rec: Record, token: str) -> list:
    state = rec.read()
    check_owner(state, token)
    wakes = poll_usage(rec, token, state)
    wakes += poll_prs(rec, token)
    wakes += poll_inbox(rec, token)
    wakes += poll_handoffs(rec)
    return wakes


def cmd_wait(rec: Record, args: list) -> None:
    form = "wait [--interval <seconds>] [--polls <n>]"
    pos, opts = take_options(args, {"interval": True, "polls": True})
    want(pos, 0, 0, form)
    try:
        interval = float(opts.get("interval", DEFAULT_INTERVAL))
        polls = int(opts["polls"]) if "polls" in opts else None
    except ValueError:
        raise Usage(f"usage: {form}")
    if interval < 0 or (polls is not None and polls < 1):
        raise Usage(f"usage: {form}")
    token = uuid.uuid4().hex
    stop_old_poller(claim_owner(rec, token))

    def on_term(signum, frame):
        raise SystemExit(0)

    signal.signal(signal.SIGTERM, on_term)
    count = 0
    try:
        while True:
            count += 1
            try:
                wakes = poll_once(rec, token)
            except Superseded:
                return
            if wakes:
                for line in wakes:
                    print(line)
                sys.stdout.flush()
                return
            if polls is not None and count >= polls:
                return
            time.sleep(interval)
    finally:
        release_owner(rec, token)


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


# An escape sequence: a CSI (ESC [ ... final byte); an OSC, DCS, SOS, PM or
# APC string, up to BEL or ESC \; then any other ESC and the one character
# after it.
ESCAPE_RE = re.compile(
    r"\x1b\[[0-?]*[ -/]*[@-~]"
    r"|\x1b[\]PX^_][^\x07\x1b]*(?:\x07|\x1b\\)?"
    r"|\x1b.?",
    re.DOTALL,
)
SPACE_RE = re.compile(r"[\t\n\r\v\f]")
CONTROL_RE = re.compile(r"[\x00-\x1f\x7f-\x9f]")


def clean(value) -> str:
    """Make a stored value safe to print on a terminal.

    Remove each escape sequence whole, change a tab or a line break to a
    space, and remove every other C0 or C1 control character and DEL.
    """
    text = ESCAPE_RE.sub("", str(value))
    text = SPACE_RE.sub(" ", text)
    return CONTROL_RE.sub("", text)


class Links:
    """Make a link: OSC 8 on a terminal, plain text otherwise. Keep a list for --urls.

    The text and the URL are cleaned first, so the OSC 8 wrapping is the only
    escape sequence in the output.
    """

    def __init__(self, tty: bool):
        self.tty = tty
        self.seen = []

    def make(self, text: str, url, width: int = 0) -> str:
        text = clean(text)
        url = clean(url) if url else url
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
    """`True` when the status word is the merge value: a PR that a refresh has
    read, at stage `review` or `pr`, or stage `merged` or `shipped`. Stage
    `closed` shows `closed`. A PR with no refresh yet shows the stage word."""
    stage = item["stage"]
    if stage in ("merged", "shipped"):
        return True
    return bool(item.get("pr")) and item.get("github") is not None and stage in ("review", "pr")


def status_word(item: dict) -> str:
    stage = item["stage"]
    if stage == "closed":
        return "closed"
    if shows_merge(item):
        return clean(item["merge"])
    return clean(f"{stage} {item['detail']}" if item.get("detail") else stage)


def row_text(item: dict) -> str:
    sub = item.get("subagent")
    parts = ["subagent"] if sub is not None else []
    if item.get("waits_on") and not shows_merge(item) and item["stage"] != "closed":
        parts.append("after " + ", ".join(item["waits_on"]))
    if item["stage"] == "shipped" and not item.get("doing"):
        parts.append("shipped")
    if sub is not None and sub.get("outcome"):
        parts.append(sub["outcome"])
    elif item.get("doing"):
        parts.append(item["doing"])
    return clean(" · ".join(parts))


BOARD_VERSION = 1
BOARD_EVENTS = 8
LEGEND = "spec → split → build → review → PR"


def link_value(ticket):
    """A ticket as the board shows it: `{id, url}`, both cleaned, or None."""
    if not ticket:
        return None
    url = clean(ticket["url"]) if ticket.get("url") else None
    return {"id": clean(ticket["id"]), "url": url or None}


def plan_data(state: dict):
    """The Plan block: the usage windows and the pace word, or None."""
    figures = usage_figures()
    word = pace_word(state.get("pace") or {})
    if figures is None:
        return {"windows": [], "word": word} if word else None
    windows = []
    for key, label in (("five_hour", "5h"), ("seven_day", "7d")):
        part = figures.get(key)
        if not part:
            continue
        windows.append({
            "key": key,
            "label": label,
            "used_pct": int(round(part["used_pct"])),
            "meter": meter(part["used_pct"]),
            "resets": clock(part["resets_at"]) if is_number(part.get("resets_at")) else "",
            "full_at": clock(part["full_at"]) if is_number(part.get("full_at")) else "",
        })
    return {"windows": windows, "word": word}


def row_data(item: dict, show_ticket: bool) -> dict:
    pr = item.get("pr")
    tab = (item.get("launch") or {}).get("tab")
    return {
        "n": item["n"],
        "id": clean(item["id"]),
        "marks": marks(item["stage"]),
        "status": status_word(item),
        "pr": {"number": pr["number"], "label": f"#{pr['number']}", "url": clean(pr["url"] or "")} if pr else None,
        "ticket": link_value(item.get("ticket")) if show_ticket else None,
        "text": row_text(item),
        "age": age(item.get("doing_at")) if item.get("doing") else "",
        "launch_tab": clean(tab) if tab else None,
        "subagent": item.get("subagent") is not None,
    }


def board_data(name: str, state: dict) -> dict:
    """The whole board as one object: the one place each board value is made.

    orchestrator-record.md "The board" owns its shape. The text view and the
    pane draw from it.
    """
    items = state["items"]
    groups = state["groups"]

    # Needs you: every open entry for the principal, oldest first.
    needs = [e for e in state["inbox"] if e["state"] == "open" and e["for"] == "principal"]
    needs.sort(key=lambda e: e["created_at"])  # A stable sort keeps the add order inside one second.
    entries = []
    for entry in needs:
        where = "-"
        if entry.get("item"):
            item = items.get(entry["item"])
            group = item.get("group") if item else None
            where = f"{group}/{entry['item']}" if group else entry["item"]
        entries.append({
            "id": clean(entry["id"]),
            "kind": clean(entry["kind"]),
            "age": age(entry.get("routed_at") or entry["created_at"]),
            "item": clean(where),
            "item_id": clean(entry["item"]) if entry.get("item") else None,
            "text": clean(entry["text"]),
            "recommend": clean(entry["recommend"]) if entry.get("recommend") else None,
        })

    def done(item):
        return item["stage"] in DONE_STAGES

    sections = []
    open_groups = set()
    for group in sorted(groups.values(), key=lambda g: g["created_at"]):
        members = [i for i in items.values() if i.get("group") == group["id"]]
        if not any(not done(i) for i in members):
            continue
        ordered = [items[i] for i in group["order"] if i in items]
        rest = sorted((i for i in members if i["id"] not in group["order"]), key=lambda i: i["n"])
        members = ordered + rest
        open_groups.add(group["id"])
        sections.append({
            "kind": "group",
            "id": clean(group["id"]),
            "title": clean(group["title"]),
            "ticket": link_value(group.get("ticket")),
            "repo": clean(group["repo"]) if group.get("repo") else None,
            "merged": sum(1 for i in members if landed(i)),
            "total": len(members),
            "rows": [row_data(i, False) for i in members],
        })
    singles = sorted((i for i in items.values() if i.get("group") not in groups and not done(i)),
                     key=lambda i: i["n"])
    if singles:
        sections.append({
            "kind": "single", "id": None, "title": "Single items", "ticket": None, "repo": None,
            "merged": None, "total": None, "rows": [row_data(i, True) for i in singles],
        })
    done_count = sum(1 for i in items.values() if done(i) and i.get("group") not in open_groups)
    data = {
        "version": BOARD_VERSION,
        "orch": name,
        "plan": plan_data(state),
        "needs_you": {"count": len(entries), "entries": entries},
        "sections": sections,
        "done": done_count,
        "legend": LEGEND,
    }
    # The routine events, newest last. The key is absent when there are none, so a
    # board of a record with no events is the board of before.
    events = [{"at": e.get("at") or "", "item": clean(e.get("item") or "-"), "text": clean(e.get("text") or ""),
               "age": age(e.get("at"))} for e in (state.get("events") or [])[-BOARD_EVENTS:]]
    if events:
        data["events"] = events
    return data


def render_text(data: dict, tty: bool, urls: bool) -> str:
    """Draw the text view from the board data: widths, links and the Links list only."""
    links = Links(tty)
    out = []

    plan = data["plan"]
    if plan and not plan["windows"]:
        out += [f" {plan['word']}", ""]
    elif plan:
        for w in plan["windows"]:
            head = " Plan   " if w["key"] == "five_hour" else "        "
            line = f"{head}{w['label']} {w['meter']}  {w['used_pct']:>3}%"
            notes = []
            if w["resets"]:
                notes.append(f"resets {w['resets']}")
            if w["full_at"]:
                notes.append(f"full at about {w['full_at']}")
            if notes:
                line += "  " + " · ".join(notes)
            if w["key"] == "five_hour" and plan["word"]:
                line += f"   {plan['word']}"
            out.append(line)
        out.append("")

    needs = data["needs_you"]
    out.append(f" Needs you  {needs['count']}")
    entries = needs["entries"]
    if entries:
        w = [max(len(e[k]) for e in entries) for k in ("id", "kind", "age", "item")]
        indent = 2 + sum(w) + 2 * 4
        for e in entries:
            out.append(f"  {e['id']:<{w[0]}}  {e['kind']:<{w[1]}}  {e['age']:<{w[2]}}  {e['item']:<{w[3]}}  {e['text']}")
            if e["recommend"] is not None:
                out.append(" " * indent + f"Recommended: {e['recommend']}")
    out.append("")

    # The item rows, with one set of column widths for the whole board. The
    # ticket cell is the single items' alone.
    shown = [r for s in data["sections"] for r in s["rows"]]
    if shown:
        wn = max(len(str(r["n"])) for r in shown)
        wid = max(len(r["id"]) for r in shown)
        ws = max(len(r["status"]) for r in shown)
        wp = max(len(r["pr"]["label"]) if r["pr"] else 0 for r in shown)
        wt = max(len(r["text"]) for r in shown)
    single_tickets = [r["ticket"]["id"] for s in data["sections"] if s["kind"] == "single"
                      for r in s["rows"] if r["ticket"]]
    wk = max((len(t) for t in single_tickets), default=0)

    def row(r, ticket_cell):
        pr = r["pr"]
        cell = links.make(pr["label"], pr["url"], wp) if pr else " " * wp
        if ticket_cell:
            ticket = r["ticket"]
            cell += "  " + (links.make(ticket["id"], ticket["url"], wk) if ticket else " " * wk)
        line = (f"  {r['n']:>{wn}} {r['id']:<{wid}}  {r['marks']}  "
                f"{r['status']:<{ws}}  {cell}  {r['text']:<{wt}}  {r['age']}")
        return line.rstrip()

    for s in data["sections"]:
        if s["kind"] == "group":
            line = f" {s['title']}"
            if s["ticket"]:
                line += f"  {links.make(s['ticket']['id'], s['ticket']['url'])}"
            if s["repo"]:
                line += f"  ·  {s['repo']}"
            line += f"  ·  {s['merged']} of {s['total']} merged"
            out.append(line)
        else:
            out.append(f" {s['title']}")
        ticket_cell = s["kind"] == "single" and bool(single_tickets)
        for r in s["rows"]:
            out.append(row(r, ticket_cell))
        out.append("")
    if data.get("events"):
        out.append(" Recent")
        out.extend(f"  {e['age']:>4}  {e['item']}  {e['text']}" for e in data["events"])
        out.append("")
    out.append(f" Done  {data['done']}   ·   stages: {data['legend']}")
    if urls:
        out.append("")
        out.append(" Links")
        if links.seen:
            w = max(len(t) for t, _ in links.seen)
            out.extend(f"  {t:<{w}}  {u}" for t, u in links.seen)
    return "\n".join(out)


def cmd_board(rec: Record, args: list) -> None:
    pos, opts = take_options(args, {"urls": False, "json": False})
    want(pos, 0, 0, "board [--urls | --json]")
    data = board_data(rec.name, rec.read())
    if opts.get("json"):
        # The JSON view always holds every URL, so --urls changes nothing here.
        print(json.dumps(data, indent=2, ensure_ascii=False))
        return
    print(render_text(data, sys.stdout.isatty(), bool(opts.get("urls"))))


def cmd_show(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    want(pos, 0, 1, "show [<item>]")
    state = rec.read()
    value = get_item(state, pos[0]) if pos else state
    print(json.dumps(value, indent=2, ensure_ascii=False))


def cmd_close(rec: Record, args: list) -> None:
    pos, _ = take_options(args, {})
    want(pos, 0, 0, "close")

    def change(state):
        if state.get("closed_at"):
            raise Fail(f"orchestrator record '{rec.name}' is already closed at {state['closed_at']}")
        state["closed_at"] = now_iso()
        return state["closed_at"]

    print(rec.mutate(change))


COMMANDS = {
    "init": cmd_init, "item": cmd_item, "group": cmd_group, "stage": cmd_stage, "doing": cmd_doing,
    "ask": cmd_ask, "inbox": cmd_inbox, "route": cmd_route, "answer": cmd_answer, "dismiss": cmd_dismiss,
    "plan": cmd_plan, "told": cmd_told, "pace": cmd_pace, "refresh": cmd_refresh, "board": cmd_board,
    "show": cmd_show, "close": cmd_close, "merge": cmd_merge, "finalize": cmd_finalize,
    "handoff": cmd_handoff, "send": cmd_send, "launch": cmd_launch,
    "close-item": cmd_close_item, "digest": cmd_digest, "resume": cmd_resume,
    "wait": cmd_wait,
}


def main(argv: list) -> int:
    try:
        name = None
        for arg in argv:
            try:
                arg.encode("utf-8")
            except UnicodeEncodeError:
                raise Usage("an argument is not valid UTF-8")
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
    except Code as err:
        print(f"crew-orch: {err.line}", file=sys.stderr)
        return err.code
    except Fail as err:
        print(f"crew-orch: {err}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

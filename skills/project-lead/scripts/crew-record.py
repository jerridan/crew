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
  crew-record.py <record-dir> escalation <index> set <field> <json>
  crew-record.py <record-dir> integrate <package-id> [--review-head <sha>] [--no-review accepted-round] [--published]
  crew-record.py <record-dir> deliver <deliverable-id> <deliverable-state> [--pr-url <url>] [--review-head <sha>] [--no-review accepted-round]
  crew-record.py <record-dir> arm-review --head <sha> [--past-cap]
  crew-record.py <record-dir> decision <route> "<title>" --answer "<text>" --citation "<text>" --confidence <high|medium|low> [--line "<Key>: <text>"]...
  crew-record.py <record-dir> decision <route> "<title>" --pending [--line "<Key>: <text>"]...
  crew-record.py <record-dir> decision update "<title>" --answer "<text>" --citation "<text>" --confidence <high|medium|low> [--line "<Key>: <text>"]...
  crew-record.py <record-dir> round open <round-id> --kind <ci|pr-comments|principal|skeptical> --ref "<ref>" --reply-to "<where>" [--gated] [--opened-at <ISO-8601 UTC>]
  crew-record.py <record-dir> round drop <round-id>
  crew-record.py <record-dir> round replied <round-id>
  crew-record.py <record-dir> round go-ahead <round-id>
  crew-record.py <record-dir> ship

`init` creates state.json with `created_at`. `integrate` sets a package
`integrated`, which is the delivered window's own state write. Its
`--published` flag stamps `pushed_at` in the same write, for a branch with no
remote, where the commit is the publication and no push is ever owed.
`deliver` sets the deliverable's terminal state and `run_state: delivered` in
one write, which `record-format.md` requires for `work-complete`. The state is
one of `draft-pr-opened`, `work-complete` and `under-review`, the last for a
review run's one deliverable, the colleague's PR.
`--review-head <sha>` on either one writes `run.review_pending` in that same
write, so a state change and the review it owes cannot come apart
(`skeptical-review.md`). `arm-review --head` does the same arming on its own,
for recovery and supersession — never a follow-up's own integration, which
takes the flag on `integrate` instead. Every command that moves the branch
head takes that flag under that name, and
writes the head key beside the state key it already writes. `arm_review` is
that shared step. The value
is `{head, round}`, and `round` is one more than `run.review_rounds`: the
round the owed review will run at, so the sha and the report name it expects
are written together. At the round cap it writes no pending head at all and
appends the head to `run.unreviewed_heads` instead. A review run, with
`run.kind` set to `"review"`, has no cap: every head is armed. `ship` sets
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
index, which `escalation answer` takes. `escalation <index> set` writes one
field on that entry and leaves the rest, as `deliverable <id> set` does. An
index that is not an integer, or is out of range, exits with a message and
writes nothing.
`decision` writes one entry to `decisions.md` in the record, with the heading
`## <title>` and a `Timestamp:` from the clock. The route is `precedent`,
`council` or `preference`. A new entry needs `--answer`, `--citation` and
`--confidence`, and the script exits 2 and names the first one missing.
`--pending` writes `Answer: pending` and `Confidence: pending` with no
`Citation:`, for a council or a sweep that is not yet answered. `--line` is
optional and repeatable, and takes any key. The line order is always `Route`,
`Prior`, `Positions`, `Answer`, `Citation`, `Losing`, `Confidence`, every
other `--line` in the order given, then `Timestamp`. `decision update` is a
verb, not a route. It writes the whole most recent entry with that title again
in that order, with the new values and lines, and stamps `Timestamp:` again.
It exits 2 when no entry has the title. It never appends, and it may run on a
completed entry.
`round open` writes `run.rounds[<round-id>]` with `source`, `reply_to`,
`opened_at` and `replied_at: null`. `--gated` adds `go_ahead_at: null`.
`opened_at` is the clock, or `--opened-at` for a rebuilt round. `round drop`
removes a round. `round go-ahead` and `round replied` stamp `go_ahead_at` and
`replied_at` from the clock. `replied` exits 2 on a gated round that has no
`go_ahead_at`. Each `round` form but `open` exits 2 on a round id that is
absent, and `open` exits 2 on an id that exists.
`--past-cap` on `arm-review` arms the head when `review_rounds` is at the
cap, and appends nothing to `unreviewed_heads`. `--no-review accepted-round`
on `integrate` or `deliver` does not arm the head at any round count. It
appends `{head, reason: "accepted-round", at}` to `unreviewed_heads` and needs
`--review-head`.
A decision value (`--answer`, `--citation`, `--line`) is one line: a newline
exits 2. `--opened-at` must read `YYYY-MM-DDTHH:MM:SSZ` and be no later than
the clock, or `round open` exits 2. A flag with no value exits 2.
`record-format.md` owns every field name and every transition; this script
checks none of them. A `set` value is JSON: `3`, `"text"`, `null`, `["a"]`.
"""

import datetime
import json
import os
import re
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


def die(message: str) -> None:
    """Exit 2 with a one-line message: a usage error or a refused change."""
    print(message, file=sys.stderr)
    sys.exit(2)


def usage() -> None:
    sys.exit(__doc__)


def arg(rest: list[str], i: int) -> str:
    if i >= len(rest):
        usage()
    return rest[i]


def flag(rest: list[str], name: str):
    if name not in rest:
        return None
    i = rest.index(name)
    if i + 1 >= len(rest):
        die(f"{name} needs a value")
    return rest[i + 1]


def set_dotted(target: dict, dotted: str, value) -> None:
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


def arm_review(run: dict, head: str | None, reason: str | None = None, past_cap: bool = False) -> None:
    """Record the head a skeptical review is owed on, or record that none is.

    Every arming in the run comes through here: `deliver --review-head` folds
    it into the hand-over write, and `integrate --review-head` folds it into
    a follow-up package's own integration write, atomically. `arm-review
    --head` on its own is for recovery and supersession, never a follow-up's
    ordinary path (`skeptical-review.md`). At the cap no further review runs,
    so the head is logged as unreviewed instead of armed, and the next report
    to the principal names it. A review run (`run.kind` is `"review"`) has no
    cap and arms every head. `past_cap` arms the head at the cap too, for one
    more round the principal asked for, and logs nothing.

    `reason` names why a caller does not arm a head. `None` means the caller
    wants the review, and the cap may still stop it with the reason `cap`.
    `accepted-round` means an accepted verdict stopped the review, so the head
    is never armed, at any round count. Both reasons leave a pending review
    of another head running. For `cap` the head is listed and the pending
    review stays. For `accepted-round`, a pending round not yet entered
    (`review_rounds < pending["round"]`) moves to the given head and keeps
    its number, and nothing is listed. An entered round keeps its head, and
    the given head is listed, so a resume owes nothing for it.
    """
    if not head:
        return
    rounds = run.get("review_rounds")
    rounds = rounds if isinstance(rounds, int) and not isinstance(rounds, bool) else 0
    at_cap = rounds >= REVIEW_ROUND_CAP and run.get("kind") != "review" and not past_cap
    if reason is None and at_cap:
        reason = "cap"
    if reason is not None:
        # A pending head other than this one still owes its review: this
        # head's accepted verdict or the cap says nothing about it. For an
        # accepted round, a pending round not yet entered moves to this head
        # and keeps its number, so one review covers both changes, and
        # nothing is listed. An entered round keeps its head, and this head
        # is listed, so a resume owes nothing for it.
        pending = run.get("review_pending")
        other = isinstance(pending, dict) and pending.get("head") != head
        if not other:
            run["review_pending"] = None
        if other and reason == "accepted-round":
            pending_round = pending.get("round")
            if (
                isinstance(pending_round, int)
                and not isinstance(pending_round, bool)
                and rounds < pending_round
            ):
                run["review_pending"] = {"head": head, "round": pending_round}
                return
        unreviewed = run.get("unreviewed_heads")
        if not isinstance(unreviewed, list):
            unreviewed = []
        unreviewed.append({"head": head, "reason": reason, "at": now()})
        run["unreviewed_heads"] = unreviewed
        return
    run["review_pending"] = {"head": head, "round": rounds + 1}


def no_review_reason(rest: list[str]) -> str | None:
    """The reason `--no-review` gives, or `None` when the flag is absent."""
    if "--no-review" not in rest:
        return None
    reason = flag(rest, "--no-review")
    if reason != "accepted-round":
        die(f"--no-review takes accepted-round, got {reason}")
    if not flag(rest, "--review-head"):
        die("--no-review needs --review-head")
    return reason


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


ROUTES = ("precedent", "council", "preference")
CONFIDENCES = ("high", "medium", "low")
ROUND_KINDS = ("ci", "pr-comments", "principal", "skeptical")
LINE_KEY = re.compile(r"^([A-Z][A-Za-z]*(?: [A-Za-z]+)?):\s?(.*)$", re.S)
# These keys have their own flag or the clock, so `--line` may not carry them.
OWN_KEYS = ("Route", "Answer", "Citation", "Confidence", "Timestamp")
# Keys with a fixed place in an entry. Every other key is an extra line.
FIXED_KEYS = OWN_KEYS + ("Prior", "Positions", "Losing")


def one_line(name: str, value: str) -> str:
    """A decision value is one line: a newline would break the entry."""
    if "\n" in value or "\r" in value:
        die(f"{name} must be one line")
    return value


def all_flags(rest: list[str], name: str) -> list[str]:
    """Every value of a repeatable flag, in the order given."""
    values = []
    for i, item in enumerate(rest):
        if item == name:
            if i + 1 >= len(rest):
                die(f"{name} needs a value")
            values.append(rest[i + 1])
    return values


def parse_lines(texts: list[str]) -> list[tuple[str, str]]:
    pairs = []
    for text in texts:
        one_line("--line", text)
        found = LINE_KEY.match(text)
        if not found or found.group(1) in OWN_KEYS:
            die(f'--line wants "<Key>: <text>" with a key other than {", ".join(OWN_KEYS)}: {text}')
        pairs.append((found.group(1), found.group(2)))
    return pairs


def parse_entry(block: list[str]) -> list[tuple[str, str]]:
    """Split an entry's lines (after the heading) into `(key, text)` pairs.

    A line that opens no key continues the one before it.
    """
    pairs = []
    for line in block:
        found = LINE_KEY.match(line)
        if found:
            pairs.append((found.group(1), found.group(2)))
        elif pairs:
            pairs[-1] = (pairs[-1][0], pairs[-1][1] + "\n" + line)
    return pairs


def render_entry(title: str, route: str, answer: str, citation: str | None, confidence: str,
                 lines: list[tuple[str, str]]) -> list[str]:
    """One entry's lines in the fixed order, ending in a clock `Timestamp:`."""
    def pick(key: str) -> list[tuple[str, str]]:
        return [(k, v) for k, v in lines if k == key]

    out = [("Route", route)] + pick("Prior") + pick("Positions") + [("Answer", answer)]
    if citation is not None:
        out.append(("Citation", citation))
    out += pick("Losing") + [("Confidence", confidence)]
    out += [(k, v) for k, v in lines if k not in FIXED_KEYS]
    out.append(("Timestamp", now()))
    return [f"## {title}"] + "\n".join(f"{k}: {v}" for k, v in out).split("\n")


def decision(record: Path, rest: list[str]) -> None:
    """Write or complete one `decisions.md` entry. The usage block says how."""
    route, title = arg(rest, 0), arg(rest, 1)
    updating = route == "update"
    if not updating and route not in ROUTES:
        die(f"route must be one of {', '.join(ROUTES)}, got {route}")
    lines = parse_lines(all_flags(rest, "--line"))
    path = record / "decisions.md"
    existing = path.read_text(encoding="utf-8").splitlines() if path.is_file() else []
    start = end = 0
    if updating:
        starts = [i for i, line in enumerate(existing) if line == f"## {title}"]
        if not starts:
            die(f"no decision entry titled {title}")
        start = starts[-1]
        end = next((i for i in range(start + 1, len(existing)) if existing[i].startswith("## ")), len(existing))
        # The blank line between entries is not part of this entry.
        while end > start + 1 and existing[end - 1] == "":
            end -= 1
        old = parse_entry(existing[start + 1:end])
        route = next((v for k, v in old if k == "Route"), "")
        # Lines the entry already holds stay, unless this call gives the same key.
        given = {k for k, _ in lines}
        lines = [(k, v) for k, v in old if k not in OWN_KEYS and k not in given] + lines
    if "--pending" in rest and not updating:
        entry = render_entry(title, route, "pending", None, "pending", lines)
    else:
        values = {name: flag(rest, f"--{name}") for name in ("answer", "citation", "confidence")}
        for name, value in values.items():
            if not value:
                die(f"decision needs --{name}")
            if name != "confidence":
                one_line(f"--{name}", value)
        if values["confidence"] not in CONFIDENCES:
            die(f"--confidence must be one of {', '.join(CONFIDENCES)}, got {values['confidence']}")
        entry = render_entry(title, route, values["answer"], values["citation"], values["confidence"], lines)
    record.mkdir(parents=True, exist_ok=True)
    if updating:
        tail = existing[end:]
        if tail and tail[0].startswith("## "):
            tail = [""] + tail
        merged = existing[:start] + entry + tail
    else:
        merged = existing + ([""] if existing else []) + entry
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    tmp.write_text("\n".join(merged) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def round_cmd(run: dict, rest: list[str]) -> None:
    """The `round` forms. The clock writes every stamp."""
    verb, round_id = arg(rest, 0), arg(rest, 1)
    rounds = run.get("rounds")
    if not isinstance(rounds, dict):
        rounds = {}
        run["rounds"] = rounds
    if verb == "open":
        if round_id in rounds:
            die(f"round {round_id} exists")
        kind = flag(rest, "--kind")
        if kind not in ROUND_KINDS:
            die(f"--kind must be one of {', '.join(ROUND_KINDS)}, got {kind}")
        ref, reply_to = flag(rest, "--ref"), flag(rest, "--reply-to")
        if ref is None or reply_to is None:
            die("round open needs --ref and --reply-to")
        opened_at = flag(rest, "--opened-at")
        if opened_at is not None:
            try:
                datetime.datetime.strptime(opened_at, "%Y-%m-%dT%H:%M:%SZ")
            except ValueError:
                die(f"--opened-at must be YYYY-MM-DDTHH:MM:SSZ, got {opened_at}")
            if opened_at > now():
                die(f"--opened-at is later than the clock: {opened_at}")
        entry = {
            "source": {"kind": kind, "ref": ref},
            "reply_to": reply_to,
            "opened_at": opened_at or now(),
            "replied_at": None,
        }
        if "--gated" in rest:
            entry["go_ahead_at"] = None
        rounds[round_id] = entry
        return
    if verb not in ("drop", "go-ahead", "replied"):
        usage()
    if round_id not in rounds:
        die(f"no round {round_id}")
    entry = rounds[round_id]
    if verb == "drop":
        del rounds[round_id]
    elif verb == "go-ahead":
        entry["go_ahead_at"] = now()
    else:
        if "go_ahead_at" in entry and entry["go_ahead_at"] is None:
            die(f"round {round_id} is gated and has no go-ahead")
        entry["replied_at"] = now()


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

    if kind == "decision":
        decision(record, rest)
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
        elif arg(rest, 1) == "set":
            try:
                index = int(rest[0])
            except ValueError:
                sys.exit(f"escalation index is not an integer: {rest[0]}")
            if index < 0 or index >= len(asks):
                sys.exit(f"no escalation at index {index}")
            asks[index][arg(rest, 2)] = json.loads(arg(rest, 3))
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
        arm_review(run, flag(rest, "--review-head"), no_review_reason(rest))
    elif kind == "deliver":
        dl = find(state.get("deliverables", []), arg(rest, 0))
        dl["state"] = arg(rest, 1)
        dl["state_changed_at"] = now()
        url = flag(rest, "--pr-url")
        if url:
            dl["pr_url"] = url
        arm_review(run, flag(rest, "--review-head"), no_review_reason(rest))
        before = run.get("run_state")
        run["run_state"] = "delivered"
        stamp_on_transition(run, before)
    elif kind == "arm-review":
        head = flag(rest, "--head")
        if not head:
            usage()
        arm_review(run, head, past_cap="--past-cap" in rest)
    elif kind == "round":
        round_cmd(run, rest)
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

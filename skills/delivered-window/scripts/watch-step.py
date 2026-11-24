#!/usr/bin/env python3
"""The mechanical steps of the PR watch, each in one call.

usage:
  watch-step.py cursor <record-dir> [--resume]
  watch-step.py deploy <record-dir> --source <name> [--environment <e>]
                [--workflow <w>] [--timeout <minutes>] [--setup-only]
  watch-step.py ack <record-dir> [--hold <id>...]     (wake lines on stdin)
  watch-step.py release <record-dir> <id>...

`cursor` writes the first cursor and nothing else. `deploy` writes `run.deploy`
as `SKILL.md`'s "The deploy watch" says, then runs the poll in deploy mode.
With `--setup-only` it writes `run.deploy` and returns, and `window-watch.py`
polls. `ack` makes the cursor write for a batch of poll lines. `release`
removes held items. The watcher runs `cursor`, `deploy --setup-only` and `ack`.
Every write goes through `crew-record.py`. A failed step prints
`watch-step.py: <message>` on stderr and exits 2.

Tests name another poll script in WATCH_STEP_POLL.
"""

import argparse
import datetime
import json
import os
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
RECORD_PY = HERE.parent.parent / "project-lead" / "scripts" / "crew-record.py"
POLL = os.environ.get("WATCH_STEP_POLL") or str(HERE / "pr-watch.sh")

SEEN_KINDS = ("review", "review-comment", "comment", "check", "push")
TIME_KINDS = ("review", "comment")
NO_CURSOR_KINDS = ("ready", "merged", "queued", "dequeued", "closed", "deployed", "no-deploy")
DEPLOY_END_KINDS = ("deploy-failed", "deploy-timeout")
KINDS = SEEN_KINDS + NO_CURSOR_KINDS + DEPLOY_END_KINDS


def fail(message):
    print(f"watch-step.py: {message}", file=sys.stderr)
    sys.exit(2)


class Parser(argparse.ArgumentParser):
    def error(self, message):
        fail(f"{message}; see the usage in the script header")


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def load_state(record):
    path = Path(record) / "state.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except OSError:
        fail(f"no state.json in {record}; pass the record directory")
    except ValueError:
        fail(f"{path} is not valid JSON; repair the record")


def pr_of(state):
    found = [d for d in state.get("deliverables") or [] if d.get("pr_url")]
    if len(found) != 1:
        fail("the record needs exactly one deliverable with a pr_url")
    url = found[0]["pr_url"]
    m = re.fullmatch(r"https://github\.com/([^/]+)/([^/]+)/pull/(\d+)", url.split("?")[0].split("#")[0].rstrip("/"))
    if not m:
        fail(f"pr_url '{url}' is not a GitHub PR URL")
    return found[0], url, m.group(1), m.group(2), m.group(3)


def rec(record, *args):
    try:
        done = subprocess.run([sys.executable, str(RECORD_PY), str(record), *args],
                              capture_output=True, text=True)
    except OSError as exc:
        fail(f"cannot run crew-record.py: {exc}")
    if done.returncode != 0:
        fail(f"crew-record.py {' '.join(args[:3])} failed: {done.stderr.strip() or done.stdout.strip()}; "
             "fix the record, then run it again")


def gh(*args):
    try:
        done = subprocess.run(["gh", *args], capture_output=True, text=True)
    except OSError as exc:
        fail(f"cannot run gh: {exc}; install gh")
    if done.returncode != 0:
        fail(f"gh {' '.join(args[:3])} failed: {done.stderr.strip()}; check the network and `gh auth status`, then run it again")
    return done.stdout


def json_stream(text):
    """The values of back-to-back JSON documents, as `gh --paginate` prints them."""
    dec, i, out = json.JSONDecoder(), 0, []
    while True:
        while i < len(text) and text[i].isspace():
            i += 1
        if i >= len(text):
            return out
        value, i = dec.raw_decode(text, i)
        out.append(value)


def set_watch(record, cursor):
    rec(record, "run", "set", "watch", json.dumps(cursor))


def pr_read(url):
    try:
        return json.loads(gh("pr", "view", url, "--json", "isDraft,createdAt,headRefOid"))
    except ValueError:
        fail("gh pr view printed no JSON; run it again")


def ensure_cursor(record, resume):
    """The first write. Returns the PR read when this call made it, else None."""
    state = load_state(record)
    _, url, owner, repo, num = pr_of(state)
    watch = (state.get("run") or {}).get("watch")
    pr = None
    if watch is None:
        pr = pr_read(url)
        review = (state.get("run") or {}).get("kind") == "review"
        seen = []
        if resume:
            for page in json_stream(gh("api", "--paginate", f"repos/{owner}/{repo}/pulls/{num}/comments")):
                seen.extend(c["id"] for c in page)
        polled = now() if (review or resume) else pr["createdAt"]
        watch = {"last_polled_at": polled, "seen_ids": seen,
                 "draft": bool(pr["isDraft"]), "head": pr["headRefOid"], "held": []}
        set_watch(record, watch)
    elif not watch.get("head"):
        head = None
        reviews = sorted(Path(record, "reviews").glob("skeptical-r*.md"),
                         key=lambda p: int(re.search(r"r(\d+)\.md$", p.name).group(1))
                         if re.search(r"r(\d+)\.md$", p.name) else -1)
        for path in reversed(reviews):
            m = re.search(r"^Reviewed:\s*(\S+)", path.read_text(encoding="utf-8"), re.M)
            if m:
                head = m.group(1)
                break
        head = head or pick_deliverable(state).get("base")
        if not head:
            fail("run.watch has no head, and no skeptical review or deliverable base names one; write run.watch.head")
        rec(record, "run", "set", "watch.head", json.dumps(head))
    return pr


def pick_deliverable(state):
    return pr_of(state)[0]


def run_poll(args):
    sys.stdout.flush()
    try:
        os.execvp("bash", ["bash", POLL, *args])
    except OSError as exc:
        fail(f"cannot run the poll {POLL}: {exc}")


def cmd_cursor(a):
    ensure_cursor(a.record, a.resume)


def cmd_deploy(a):
    if a.timeout is not None and a.timeout <= 0:
        fail(f"--timeout {a.timeout} is not a positive integer; pass the minutes to wait")
    state = load_state(a.record)
    deploy = (state.get("run") or {}).get("deploy")
    if not isinstance(deploy, dict):
        if not a.source:
            fail("deploy needs --source when run.deploy is absent")
        obj = {"environment": a.environment, "workflow": a.workflow,
               "timeout_minutes": 180 if a.timeout is None else a.timeout,
               "source": a.source, "since": now(), "ended": None}
        rec(a.record, "run", "set", "deploy", json.dumps(obj))
    elif deploy.get("ended"):
        rec(a.record, "run", "set", "deploy.since", json.dumps(now()))
        rec(a.record, "run", "set", "deploy.ended", "null")
    if a.setup_only:
        return
    run_poll([a.record, "deploy"])


def ident(text):
    return int(text) if text.isdigit() else text


def parse_lines(text):
    items, draft = [], None
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line == "isDraft=":
            continue
        if line in ("isDraft=true", "isDraft=false"):
            draft = line.endswith("true")
            continue
        parts = line.split(None, 4)
        if len(parts) < 4 or parts[0] not in KINDS:
            fail(f"cannot read the line '{line[:60]}'; pass the lines exactly as the monitor printed them. Nothing was written")
        items.append({"kind": parts[0], "id": ident(parts[1]), "author": parts[2], "at": parts[3],
                      "summary": parts[4] if len(parts) > 4 else ""})
    return items, draft


def cmd_ack(a):
    items, draft_line = parse_lines(sys.stdin.read())
    held_ids = {str(h) for h in a.hold}
    missing = held_ids - {str(i["id"]) for i in items}
    if missing:
        fail(f"--hold names {', '.join(sorted(missing))}, which is no line of the input. Nothing was written")
    state = load_state(a.record)
    watch = (state.get("run") or {}).get("watch")
    if not isinstance(watch, dict):
        fail("run.watch is absent; run window-watch.py start first")
    new = json.loads(json.dumps(watch))
    new.setdefault("seen_ids", [])
    new.setdefault("held", [])
    ends = []
    for it in items:
        k = it["kind"]
        if k in SEEN_KINDS and not any(str(s) == str(it["id"]) for s in new["seen_ids"]):
            new["seen_ids"].append(it["id"])
        if k in TIME_KINDS and it["at"] > new.get("last_polled_at", ""):
            new["last_polled_at"] = it["at"]
        if k == "ready":
            new["draft"] = False
        elif k == "push":
            new["head"] = str(it["id"])
        elif k == "queued":
            new["queued"] = True
        elif k == "dequeued":
            new["queued"] = False
        elif k in DEPLOY_END_KINDS:
            ends.append(k)
        if str(it["id"]) in held_ids and not any(str(h.get("id")) == str(it["id"]) for h in new["held"]):
            new["held"].append({"kind": k, "id": it["id"], "author": it["author"],
                                "at": it["at"], "summary": it["summary"]})
    if draft_line is True and not new.get("draft"):
        new["draft"] = True
    said = []
    if new != watch:
        set_watch(a.record, new)
        said.append(f"run.watch written (seen_ids {len(new['seen_ids'])}, held {len(new['held'])})")
    for kind in ends:
        rec(a.record, "run", "set", "deploy.ended", json.dumps(kind))
        said.append(f"run.deploy.ended {kind}")
    print("ack: " + ("; ".join(said) if said else "no change"))


def cmd_release(a):
    state = load_state(a.record)
    watch = (state.get("run") or {}).get("watch")
    if not isinstance(watch, dict):
        fail("run.watch is absent; there is nothing held")
    ids = {str(i) for i in a.ids}
    held = watch.get("held") or []
    keep = [h for h in held if str(h.get("id")) not in ids]
    if len(keep) != len(held):
        rec(a.record, "run", "set", "watch.held", json.dumps(keep))
    print(f"release: {len(held) - len(keep)} item(s) removed from held")


def main():
    p = Parser(prog="watch-step.py")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=Parser)
    for name, fn in (("cursor", cmd_cursor),):
        s = sub.add_parser(name)
        s.add_argument("record")
        s.add_argument("--resume", action="store_true")
        s.set_defaults(fn=fn)
    s = sub.add_parser("deploy")
    s.add_argument("record")
    s.add_argument("--source")
    s.add_argument("--environment")
    s.add_argument("--workflow")
    s.add_argument("--timeout", type=int)
    s.add_argument("--setup-only", action="store_true")
    s.set_defaults(fn=cmd_deploy)
    s = sub.add_parser("ack")
    s.add_argument("record")
    s.add_argument("--hold", action="append", default=[])
    s.set_defaults(fn=cmd_ack)
    s = sub.add_parser("release")
    s.add_argument("record")
    s.add_argument("ids", nargs="+")
    s.set_defaults(fn=cmd_release)
    a = p.parse_args()
    try:
        a.fn(a)
    except (ValueError, KeyError, TypeError, IndexError, AttributeError) as exc:
        fail(f"unexpected data ({type(exc).__name__}: {exc}); check the record and the gh output, then run it again")


if __name__ == "__main__":
    main()

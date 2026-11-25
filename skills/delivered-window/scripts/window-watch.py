#!/usr/bin/env python3
"""The watcher of a delivered run: no model, one process per run.

usage:
  window-watch.py start <record-dir> [--hold] [--model <m>] [--poll <s>] [--quiet <s>] [--cap <s>]
  window-watch.py release <record-dir>
  window-watch.py ensure <record-dir>
  window-watch.py claim <record-dir> --session <name>
  window-watch.py next <record-dir> --session <name>
  window-watch.py done <record-dir> --session <name> [--final]
  window-watch.py stop <record-dir> (--session <name> | --force)
  window-watch.py say (<record-dir> | --item <orchestrator>/<item>) --from <name> <text>
  window-watch.py status <record-dir>

`start` writes `run.window`, takes the first PR cursor, and starts the watcher
detached. The watcher polls the PR (and, after the merge, the deploy) every
`--poll` seconds, drops the events that need no model, queues the rest in
`<record>/window/pending.jsonl`, and moves the PR cursor on. After the first
queued event it waits `--quiet` seconds with no new event (at most `--cap`
seconds), then starts one window session through the launcher, with every
queued event. One session holds the slot at a time. `next`, `done` and `stop`
name the session that holds it. `ensure` restarts a watcher whose pid is dead.

Every `state.json` write goes through `crew-record.py`. The heartbeat and the
poll times live in `<record>/window/watcher.json`, never in `state.json`.
`record-format.md` owns the `run.window` fields.

Exit codes: 0 done, 1 any other failure, 2 usage, 3 a session name that does
not hold the slot, or a slot that is taken.

Tests name another poll script in WINDOW_WATCH_POLL, another launcher in
CREW_WINDOW_LAUNCHER, a stale cap in seconds in CREW_WINDOW_STALE, and a file in
CREW_WINDOW_TEST_HOLD that holds a tick at the archive of a done session.
"""

import argparse
import datetime
import fcntl
import json
import os
import re
import subprocess
import sys
import time
import traceback
from pathlib import Path

HERE = Path(__file__).resolve().parent
SKILLS = HERE.parent.parent
RECORD_PY = SKILLS / "project-lead" / "scripts" / "crew-record.py"
WATCH_STEP = HERE / "watch-step.py"
ORCH_PY = os.environ.get("CREW_WINDOW_ORCH") or str(SKILLS / "orchestrator" / "scripts" / "crew-orch.py")
POLL = os.environ.get("WINDOW_WATCH_POLL") or str(HERE / "pr-watch.sh")
LAUNCHER = os.environ.get("CREW_WINDOW_LAUNCHER") or str(SKILLS / "orchestrator" / "scripts" / "launcher.py")
# The launcher's window call: the helper timeout (120 s), the default wait for
# a claude process (60 s) and the bounded terminal steps fit in it.
LAUNCH_TIMEOUT = 300
STALE_DEFAULT = 4 * 3600
SCRIPT = Path(os.path.abspath(__file__))

# The kinds `watch-step.py ack` knows. Every other line stays out of the ack.
ACK_KINDS = ("review", "review-comment", "comment", "check", "push", "ready", "merged", "queued",
             "dequeued", "closed", "deployed", "no-deploy", "deploy-failed", "deploy-timeout")
DEPLOY_KINDS = ("deployed", "no-deploy", "deploy-failed", "deploy-timeout", "closed")
NO_SESSION_KINDS = ("queued",)


class Usage(Exception):
    pass


class Fail(Exception):
    pass


class Refused(Exception):
    pass


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Usage(message)


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def log(message):
    print(f"{now()} {message}", flush=True)


# -- the record -------------------------------------------------------------


def record_dir(text):
    record = Path(text)
    if not (record / "state.json").is_file():
        raise Fail(f"no state.json in {text}; pass the record directory")
    return Path(os.path.abspath(text))


def load(record):
    try:
        return json.loads((record / "state.json").read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise Fail(f"cannot read {record}/state.json: {exc}")


def win_of(state):
    return (state.get("run") or {}).get("window") or {}


def rec_set(record, dotted, value):
    done = subprocess.run([sys.executable, str(RECORD_PY), str(record), "run", "set", f"window.{dotted}",
                           json.dumps(value)], capture_output=True, text=True)
    if done.returncode != 0:
        raise Fail(f"crew-record.py run set window.{dotted} failed: {(done.stderr or done.stdout).strip()}")


def rec_run_set(record, dotted, value):
    done = subprocess.run([sys.executable, str(RECORD_PY), str(record), "run", "set", dotted, json.dumps(value)],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise Fail(f"crew-record.py run set {dotted} failed: {(done.stderr or done.stdout).strip()}")


def wdir(record):
    path = record / "window"
    path.mkdir(exist_ok=True)
    return path


class Lock:
    """One lock for the pending file, the slot and the event files."""

    def __init__(self, record):
        self.path = wdir(record) / ".lock"

    def __enter__(self):
        self.fh = self.path.open("a")
        fcntl.flock(self.fh, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        self.fh.close()


def wj_read(record):
    try:
        return json.loads((wdir(record) / "watcher.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}


def wj_write(record, data):
    path = wdir(record) / "watcher.json"
    tmp = path.with_name(f"watcher.json.{os.getpid()}.tmp")
    tmp.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def read_lines(path):
    try:
        return [l for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    except OSError:
        return []


def write_lines(path, lines):
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as fh:
        fh.write("".join(l + "\n" for l in lines))
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def append_lines(path, lines):
    with path.open("a", encoding="utf-8") as fh:
        fh.write("".join(l + "\n" for l in lines))
        fh.flush()
        os.fsync(fh.fileno())


def pid_alive(pid):
    if not isinstance(pid, int) or pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        pass
    ps = subprocess.run(["ps", "-p", str(pid), "-o", "command="], capture_output=True, text=True)
    if ps.returncode != 0:
        return False
    return "window-watch" in ps.stdout or not ps.stdout.strip()


def event(source, line, sender=None):
    return json.dumps({"at": now(), "source": source, "line": line, "from": sender})


# -- the model, from the flag or the standing instructions ------------------


def section_model(path):
    if not path or not Path(path).is_file():
        return None
    inside = False
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if re.match(r"^#{1,6}\s*", raw):
            if inside:
                return None
            inside = bool(re.fullmatch(r"#{1,6}\s*window model\s*", raw.strip(), re.I))
            continue
        if inside and raw.strip():
            return raw.strip().strip("`").strip() or None
    return None


def resolve_model(state, flag):
    if flag:
        return flag
    si = (state.get("run") or {}).get("standing_instructions") or {}
    for key in ("repo", "machine"):
        found = section_model(si.get(key))
        if found:
            return found
    return "opus"


# -- commands ---------------------------------------------------------------


def spawn(record):
    (wdir(record) / "stop-now").unlink(missing_ok=True)
    log_file = (wdir(record) / "watcher.log").open("a")
    proc = subprocess.Popen([sys.executable, str(Path(__file__).resolve()), "_loop", str(record)],
                            stdin=subprocess.DEVNULL, stdout=log_file, stderr=log_file,
                            start_new_session=True, close_fds=True)
    log_file.close()
    rec_set(record, "watcher", {"pid": proc.pid, "started_at": now()})
    return proc.pid


def cmd_start(a):
    record = record_dir(a.record)
    state = load(record)
    w = win_of(state)
    pid = (w.get("watcher") or {}).get("pid")
    if pid_alive(pid):
        if w.get("intake") is False:
            rec_set(record, "intake", True)
            print("intake on")
        else:
            print("already running")
        return 0
    wdir(record)
    for name in ("pending.jsonl", "inbox.jsonl", "watcher.log"):
        (record / "window" / name).touch()
    rec_set(record, "model", resolve_model(state, a.model))
    rec_set(record, "poll", a.poll)
    rec_set(record, "quiet", a.quiet)
    rec_set(record, "cap", a.cap)
    rec_set(record, "hold", bool(a.hold))
    rec_set(record, "intake", True)
    for key, default in (("session", None), ("sessions", []), ("awaiting", None)):
        if key not in w:
            rec_set(record, key, default)
    own = w.get("own") or {}
    rec_set(record, "own", {"pushes": own.get("pushes") or [], "ready": own.get("ready") or []})
    cursor = subprocess.run([sys.executable, str(WATCH_STEP), "cursor", str(record)], capture_output=True, text=True)
    if cursor.returncode != 0:
        raise Fail(f"the first cursor failed: {cursor.stderr.strip()}")
    print(f"started pid {spawn(record)}")
    return 0


def cmd_ensure(a):
    record = record_dir(a.record)
    state = load(record)
    w = win_of(state)
    if not w:
        raise Fail("run.window is absent; run window-watch.py start first")
    if (state.get("run") or {}).get("run_state") == "complete":
        print("complete")
        return 0
    if pid_alive((w.get("watcher") or {}).get("pid")):
        print("alive")
        return 0
    wdir(record)
    spawn(record)
    print("restarted")
    return 0


def cmd_release(a):
    record = record_dir(a.record)
    rec_set(record, "hold", False)
    print("released")
    return 0


def holder(record, name, allow_done=False):
    sess = win_of(load(record)).get("session")
    ok = ("live", "launching", "done") if allow_done else ("live", "launching")
    if not sess or sess.get("name") != name or sess.get("status") not in ok:
        raise Refused(f"session {name} does not hold the slot of {record.name}")
    return sess


def cmd_claim(a):
    record = record_dir(a.record)
    with Lock(record):
        w = win_of(load(record))
        sess = w.get("session")
        if sess and sess.get("status") in ("live", "launching"):
            raise Refused(f"the slot is held by {sess.get('name')}")
        if sess:
            archive(record, sess)
        n = len((win_of(load(record)).get("sessions") or [])) + 1
        events = f"events-{n}.jsonl"
        (wdir(record) / events).touch()
        rec_set(record, "session", {"name": a.session, "status": "live", "events": events, "handle": None,
                                    "session_id": None, "claimed": True, "started_at": now(), "stale_at": None})
    print(f"claimed {a.session}")
    return 0


def cmd_next(a):
    record = record_dir(a.record)
    with Lock(record):
        sess = holder(record, a.session)
        pending = wdir(record) / "pending.jsonl"
        lines = read_lines(pending)
        if lines:
            append_lines(wdir(record) / sess["events"], lines)
            write_lines(pending, [])
    for line in lines:
        print(line)
    return 0


def cmd_done(a):
    record = record_dir(a.record)
    sess = holder(record, a.session, allow_done=True)
    if sess.get("status") == "done":
        print("done")
        return 0
    if a.final:
        rec_set(record, "session.final", True)
    rec_set(record, "session.ended_at", now())
    rec_set(record, "session.status", "done")
    print("done")
    return 0


def cmd_stop(a):
    record = record_dir(a.record)
    if a.force:
        rec_set(record, "intake", False)
        (wdir(record) / "stop-now").touch()
        print("stopping")
        return 0
    if not a.session:
        raise Usage("stop needs --session <name> or --force")
    holder(record, a.session)
    rec_set(record, "intake", False)
    print("intake off")
    return 0


def record_root():
    return Path(os.environ.get("CREW_RECORD_ROOT") or os.path.expanduser("~/.claude/crew"))


def find_item(item):
    orch, _, item_id = item.partition("/")
    if not orch or not item_id:
        raise Usage("--item takes <orchestrator>/<item>")
    for path in sorted(record_root().glob("*/state.json")):
        try:
            o = (json.loads(path.read_text(encoding="utf-8")).get("run") or {}).get("orchestrator") or {}
        except (OSError, ValueError):
            continue
        if str(o.get("name")) == orch and str(o.get("item")) == item_id:
            return path.parent
    raise Fail(f"no record has run.orchestrator {item}")


def cmd_say(a):
    rest = list(a.rest)
    if a.item:
        record = find_item(a.item)
        text = " ".join(rest)
    else:
        if not rest:
            raise Usage("say needs a record dir or --item")
        record = record_dir(rest[0])
        text = " ".join(rest[1:])
    if not a.sender:
        raise Usage("say needs --from <name>")
    if not text.strip():
        raise Usage("say needs the text of the word")
    append_lines(wdir(record) / "inbox.jsonl", [event("inbox", text, a.sender)])
    print("said")
    return 0


def cmd_status(a):
    record = record_dir(a.record)
    w = win_of(load(record))
    wj = wj_read(record)
    pid = (w.get("watcher") or {}).get("pid")
    print("watcher: " + (f"pid {pid} {'alive' if pid_alive(pid) else 'dead'}" if pid else "none"))
    print(f"heartbeat: {wj.get('heartbeat_at') or 'none'}")
    print(f"hold: {'true' if w.get('hold') else 'false'}")
    print(f"intake: {'off' if w.get('intake') is False else 'on'}")
    print(f"model: {w.get('model')}")
    sess = w.get("session")
    print("session: " + (f"{sess.get('name')} {sess.get('status')} {sess.get('handle')}" if sess else "none"))
    if sess and sess.get("stale_at"):
        print(f"stale_at: {sess['stale_at']}")
    print(f"pending: {len(read_lines(wdir(record) / 'pending.jsonl'))}")
    print(f"sessions: {len(w.get('sessions') or [])}")
    return 0


# -- the watcher process ----------------------------------------------------


def run_poll(record, mode):
    done = subprocess.run(["bash", POLL, str(record), mode], capture_output=True, text=True, timeout=300)
    if done.returncode != 0:
        log(f"poll {mode} failed ({done.returncode}): {done.stderr.strip()[:300]}")
        return []
    return [l.strip() for l in done.stdout.splitlines() if l.strip()]


def needs_session(line, win, wj):
    """The filter of D2. Returns (keep, consumed one own ready flip)."""
    parts = line.split()
    kind = parts[0] if parts else ""
    if kind in NO_SESSION_KINDS or kind.startswith("isDraft="):
        return False, False
    own = win.get("own") or {}
    if kind == "push" and len(parts) > 1:
        sha = parts[1]
        if any(p and (sha.startswith(p) or p.startswith(sha)) for p in own.get("pushes") or []):
            return False, False
    if kind == "ready":
        if len(own.get("ready") or []) > int(wj.get("ready_consumed") or 0):
            return False, True
        return True, False
    return True, False


def archive(record, sess):
    w = win_of(load(record))
    sessions = list(w.get("sessions") or [])
    if not any(s.get("name") == sess.get("name") for s in sessions):
        sessions.append({k: sess.get(k) for k in ("name", "events", "handle", "session_id", "started_at", "ended_at")})
        rec_set(record, "sessions", sessions)
    rec_set(record, "session", None)


def launcher_cmd():
    return [sys.executable, LAUNCHER] if LAUNCHER.endswith(".py") else [LAUNCHER]


def close_tab(handle):
    if not handle:
        return
    done = subprocess.run(launcher_cmd() + ["stop", handle], capture_output=True, text=True, timeout=120)
    if done.returncode != 0:
        log(f"launcher stop {handle} failed ({done.returncode}): {done.stderr.strip()[:300]}")


def prompt_text(record, name, events):
    w = record
    return (
        f"You are the window session {name} of one delivered run.\n"
        f"Run the crew:delivered-window skill now. Its inputs are:\n"
        f"- the record dir: {w}\n"
        f"- the event file: {events}\n"
        f"Your session name for window-watch.py is {name}.\n"
        f"The facts of the run come only from {w}/charter.md, {w}/state.json, {w}/handover.md, "
        f"the last entries of {w}/decisions.md that you need, and the event file. "
        f"Read every instruction file that the skill names, and read the repo and the PR as the skill says.\n"
        f"The watcher script is {SCRIPT}. Run it as: python3 {SCRIPT} <subcommand> {w} --session {name}.\n"
        f"Write every decision and fact to the record before you end. "
        f"Run its done subcommand as the last step.\n"
    )


def launch(record, name, find_first, wj, poll):
    """Start or recover the tab of a launching session. Never raises."""
    state = load(record)
    w = win_of(state)
    sess = w.get("session") or {}
    handle = session_id = None
    if find_first:
        done = subprocess.run(launcher_cmd() + ["find", name], capture_output=True, text=True, timeout=120)
        found = [l.split()[0] for l in done.stdout.splitlines() if l.strip()] if done.returncode == 0 else []
        if found:
            handle = found[0]
            log(f"found the tab {handle} of {name}")
    if not handle:
        run = state.get("run") or {}
        cwd = run.get("repo")
        n = re.search(r"-w(\d+)$", name)
        prompt = wdir(record) / f"prompt-{n.group(1) if n else '0'}.md"
        if not cwd or not prompt.is_file():
            log(f"cannot launch {name}: run.repo or {prompt} is missing")
            return
        cmd = launcher_cmd() + ["window", "--name", name, "--cwd", cwd, "--prompt-file", str(prompt),
                                "--model", str(w.get("model") or "opus")]
        try:
            done = subprocess.run(cmd, capture_output=True, text=True, timeout=LAUNCH_TIMEOUT)
            out = json.loads(done.stdout.strip().splitlines()[-1]) if done.returncode == 0 and done.stdout.strip() else None
        except (OSError, subprocess.SubprocessError, ValueError, IndexError):
            done, out = None, None
        if not out or not out.get("tab"):
            fails = int(wj.get("launch_fails") or 0) + 1
            wj["launch_fails"] = fails
            wj["next_launch_at"] = time.time() + min(fails, 10) * poll
            err = done.stderr.strip()[:300] if done is not None else "no answer"
            log(f"launch of {name} failed ({fails}): {err}")
            return
        handle, session_id = out["tab"], out.get("session_id")
    rec_set(record, "session.handle", handle)
    rec_set(record, "session.session_id", session_id)
    rec_set(record, "session.status", "live")
    wj["activity_at"] = time.time()
    wj["launch_fails"] = 0
    wj["next_launch_at"] = None
    log(f"session {name} is live at {handle}")


def start_session(record, wj, poll):
    with Lock(record):
        w = win_of(load(record))
        if w.get("session"):
            return
        pending_path = wdir(record) / "pending.jsonl"
        lines = read_lines(pending_path)
        if not lines:
            return
        n = len(w.get("sessions") or []) + 1
        name = f"{load(record).get('goal_slug') or record.name}-w{n}"
        events = f"events-{n}.jsonl"
        write_lines(wdir(record) / events, lines)
        (wdir(record) / f"prompt-{n}.md").write_text(prompt_text(record, name, wdir(record) / events),
                                                    encoding="utf-8")
        rec_set(record, "session", {"name": name, "status": "launching", "events": events, "handle": None,
                                    "session_id": None, "started_at": now(), "stale_at": None})
        write_lines(pending_path, [])
        wj["first_event_at"] = wj["last_event_at"] = None
    log(f"starting {name} with {len(lines)} event(s)")
    launch(record, name, False, wj, poll)


def test_hold():
    """Test only: CREW_WINDOW_TEST_HOLD names a file. While it exists, the tick waits here."""
    path = os.environ.get("CREW_WINDOW_TEST_HOLD")
    if path and os.path.exists(path):
        Path(path + ".waiting").touch()
        end = time.time() + 15
        while os.path.exists(path) and time.time() < end:
            time.sleep(0.1)


def stale_cap():
    try:
        return int(os.environ.get("CREW_WINDOW_STALE") or STALE_DEFAULT)
    except ValueError:
        return STALE_DEFAULT


def state_mtime(record):
    try:
        return (record / "state.json").stat().st_mtime
    except OSError:
        return 0.0


def check_stale(record, state, sess, wj):
    """The clock is the last write that the watcher did not make, or the launch."""
    if sess.get("stale_at"):
        return
    if wj.get("activity_at") is None:
        wj["activity_at"] = time.time()
        return
    idle = time.time() - wj["activity_at"]
    if idle < stale_cap():
        return
    rec_set(record, "session.stale_at", now())
    log(f"the session {sess.get('name')} wrote no record for {int(idle)} s and its tab did not end: it is stale")
    orch = (state.get("run") or {}).get("orchestrator")
    if orch:
        text = f"The window session {sess.get('name')} of this item is stale: its tab {sess.get('handle')} wrote no record for {int(idle)} seconds."
        subprocess.run(([sys.executable] if ORCH_PY.endswith(".py") else []) + [ORCH_PY, "--orch", str(orch.get("name")), "ask", str(orch.get("item")), text],
                       capture_output=True, text=True)


def collect(record, state, wj):
    """Poll and read the inbox. Returns the events to queue and the lines to ack."""
    w = win_of(state)
    events, ack = [], []
    run = state.get("run") or {}
    if not wj.get("merged_seen") and not wj.get("closed_seen"):
        for line in run_poll(record, "once"):
            ack.append(line)
            keep, ready = needs_session(line, w, wj)
            if ready:
                wj["ready_consumed"] = int(wj.get("ready_consumed") or 0) + 1
            if keep:
                events.append(("pr", line))
    deploy = run.get("deploy")
    if wj.get("merged_seen") and isinstance(deploy, dict) and not deploy.get("ended") and not wj.get("deploy_done"):
        for line in run_poll(record, "deploy-once"):
            events.append(("deploy", line))
    inbox = wdir(record) / "inbox.jsonl"
    try:
        data = inbox.read_bytes()
    except OSError:
        data = b""
    offset = int(wj.get("inbox_offset") or 0)
    chunk = data[offset:]
    cut = chunk.rfind(b"\n") + 1
    for raw in chunk[:cut].decode("utf-8", "replace").splitlines():
        try:
            e = json.loads(raw)
            events.append(("inbox", e.get("line", ""), e.get("from")))
        except ValueError:
            log(f"skipped an unreadable inbox line: {raw[:80]}")
    wj["inbox_offset"] = offset + cut
    return events, ack


def section_lines(path, title):
    """The lines under the `## <title>` heading of a file, or None."""
    if not path or not Path(path).is_file():
        return None
    inside, found = False, None
    for raw in Path(path).read_text(encoding="utf-8").splitlines():
        if re.match(r"^#{1,6}\s", raw):
            if inside:
                break
            inside = bool(re.fullmatch(r"#{1,6}\s*" + re.escape(title) + r"\s*", raw.strip(), re.I))
            if inside:
                found = []
            continue
        if inside:
            found.append(raw)
    return found


def parse_deploy(lines):
    """The `Deploy` lines as {mode, environment, workflow, timeout}, or None when empty."""
    d = {}
    for raw in lines:
        text = raw.strip().lstrip("-*").strip().strip("`").strip()
        if text.lower() in ("none", "manual"):
            d["mode"] = text.lower()
            continue
        m = re.fullmatch(r"(environment|workflow|timeout)\s*:\s*(.+)", text, re.I)
        if m:
            d[m.group(1).lower()] = m.group(2).strip().strip("`")
    return d or None


def resolve_deploy(state, record):
    """The winning `Deploy` and its source, by the one order of the standing instructions.

    The charter holds a `Deploy: <value>` line only when the principal gave one at
    launch. Then come the repo file and the machine file. No section is `("default", None)`.
    """
    try:
        text = (record / "charter.md").read_text(encoding="utf-8")
    except OSError:
        text = ""
    values = [m.group(1) for m in re.finditer(r"^Deploy:\s*(.+)$", text, re.M)]
    if values:
        d = parse_deploy(re.split(r"[;,]", values[-1]))
        if d:
            return "charter", d
    si = (state.get("run") or {}).get("standing_instructions") or {}
    for key in ("repo", "machine"):
        lines = section_lines(si.get(key), "Deploy")
        d = parse_deploy(lines) if lines is not None else None
        if d:
            return key, d
    return "default", None


def setup_deploy(record):
    source, d = resolve_deploy(load(record), record)
    if d and d.get("mode") in ("none", "manual"):
        log(f"Deploy {d['mode']} from {source}: no deploy poll")
        return
    cmd = [sys.executable, str(WATCH_STEP), "deploy", str(record), "--source", source, "--setup-only"]
    for flag, key in (("--environment", "environment"), ("--workflow", "workflow"), ("--timeout", "timeout")):
        value = (d or {}).get(key)
        if value is None:
            continue
        if key == "timeout" and not (value.isdigit() and int(value) > 0):
            log(f"Deploy timeout {value!r} is not a positive integer: left out")
            continue
        cmd += [flag, value]
    done = subprocess.run(cmd, capture_output=True, text=True)
    if done.returncode != 0:
        log(f"deploy setup failed: {done.stderr.strip()[:300]}")


def after_queue(record, events, wj):
    """The writes that a queued line asks for: the merge, the close, the deploy end."""
    for e in events:
        parts = e[1].split()
        kind = parts[0] if parts else ""
        if e[0] == "pr" and kind == "merged" and not wj.get("merged_seen"):
            run = load(record).get("run") or {}
            if not isinstance(run.get("deploy"), dict):
                setup_deploy(record)
            rec_set(record, "merged_seen", parts[3] if len(parts) > 3 else now())
            wj["merged_seen"] = True
        elif e[0] == "pr" and kind == "closed":
            wj["closed_seen"] = True
        elif e[0] == "deploy" and kind in DEPLOY_KINDS:
            rec_run_set(record, "deploy.ended", kind)
            wj["deploy_done"] = True


def tick(record, ctx):
    state = load(record)
    w = win_of(state)
    poll = max(1, int(w.get("poll") or 60))
    ctx["poll"] = poll
    if (w.get("watcher") or {}).get("pid") != os.getpid():
        log("the record names another watcher: this one exits")
        return False
    wj = wj_read(record)
    # A write that the watcher did not make since its last tick is the session's.
    if wj.get("own_mtime") is not None and state_mtime(record) > wj["own_mtime"]:
        wj["activity_at"] = time.time()
    if (wdir(record) / "stop-now").exists():
        sess = w.get("session") or {}
        close_tab(sess.get("handle"))
        rec_set(record, "watcher", None)
        log("stopped by force")
        return False
    intake = w.get("intake") is not False
    if intake:
        events, ack = collect(record, state, wj)
        if events:
            with Lock(record):
                append_lines(wdir(record) / "pending.jsonl", [event(*e) if len(e) == 3 else event(e[0], e[1]) for e in events])
            wj["last_event_at"] = time.time()
            if not wj.get("first_event_at"):
                wj["first_event_at"] = wj["last_event_at"]
        known = [l for l in ack if l.split()[0] in ACK_KINDS or l.startswith("isDraft=")]
        if known:
            done = subprocess.run([sys.executable, str(WATCH_STEP), "ack", str(record)], input="\n".join(known) + "\n",
                                  capture_output=True, text=True)
            if done.returncode != 0:
                log(f"ack failed: {done.stderr.strip()[:300]}")
        after_queue(record, events, wj)
    wj["heartbeat_at"] = now()
    wj_write(record, wj)

    state = load(record)
    w = win_of(state)
    sess = w.get("session")
    if sess and sess.get("status") == "done":
        close_tab(sess.get("handle"))
        test_hold()
        with Lock(record):
            # Read the slot again: a claim can land between the read above and the lock.
            now_sess = win_of(load(record)).get("session") or {}
            mine = now_sess.get("name") == sess.get("name") and now_sess.get("status") == "done"
            if mine:
                archive(record, sess)
        if not mine:
            log(f"session {sess.get('name')} left the slot already: nothing to archive")
        else:
            log(f"session {sess.get('name')} ended")
            if sess.get("final"):
                rec_set(record, "watcher", None)
                log("the final done: the watcher exits")
                return False
    elif sess and sess.get("status") == "launching":
        # Dedupe the pending file against the event file, which a crash can leave doubled.
        with Lock(record):
            seen = set(read_lines(wdir(record) / sess["events"]))
            pending = read_lines(wdir(record) / "pending.jsonl")
            left = [l for l in pending if l not in seen]
            if len(left) != len(pending):
                write_lines(wdir(record) / "pending.jsonl", left)
        if not wj.get("next_launch_at") or time.time() >= wj["next_launch_at"]:
            launch(record, sess["name"], True, wj, poll)
            wj_write(record, wj)
    elif sess and sess.get("status") == "live":
        check_stale(record, state, sess, wj)
    elif not sess and intake and not w.get("hold"):
        if not read_lines(wdir(record) / "pending.jsonl"):
            wj["first_event_at"] = wj["last_event_at"] = None
        elif not wj.get("first_event_at"):
            wj["first_event_at"] = wj["last_event_at"] = time.time()
        first, last = wj.get("first_event_at"), wj.get("last_event_at")
        quiet, cap = int(w.get("quiet") or 120), int(w.get("cap") or 600)
        if first and (time.time() - last >= quiet or time.time() - first >= cap):
            start_session(record, wj, poll)
    wj["own_mtime"] = state_mtime(record)
    wj_write(record, wj)
    return True


def cmd_loop(a):
    record = Path(a.record)
    deadline = time.time() + 10
    while time.time() < deadline:
        pid = (win_of(load(record)).get("watcher") or {}).get("pid")
        if pid == os.getpid():
            break
        time.sleep(0.2)
    else:
        log("the record never named this process: exit")
        return 1
    ctx = {"poll": 60}
    log(f"the watcher runs, pid {os.getpid()}")
    while True:
        try:
            if not tick(record, ctx):
                return 0
        except Exception:
            log("tick failed: " + traceback.format_exc().strip().splitlines()[-1])
        time.sleep(ctx["poll"])


# -- the command line --------------------------------------------------------


def build():
    p = Parser(prog="window-watch.py")
    sub = p.add_subparsers(dest="cmd", required=True, parser_class=Parser)

    s = sub.add_parser("start")
    s.add_argument("record")
    s.add_argument("--hold", action="store_true")
    s.add_argument("--model")
    s.add_argument("--poll", type=int, default=60)
    s.add_argument("--quiet", type=int, default=120)
    s.add_argument("--cap", type=int, default=600)
    s.set_defaults(fn=cmd_start)
    for name, fn in (("release", cmd_release), ("ensure", cmd_ensure), ("status", cmd_status)):
        s = sub.add_parser(name)
        s.add_argument("record")
        s.set_defaults(fn=fn)
    for name, fn in (("claim", cmd_claim), ("next", cmd_next)):
        s = sub.add_parser(name)
        s.add_argument("record")
        s.add_argument("--session", required=True)
        s.set_defaults(fn=fn)
    s = sub.add_parser("done")
    s.add_argument("record")
    s.add_argument("--session", required=True)
    s.add_argument("--final", action="store_true")
    s.set_defaults(fn=cmd_done)
    s = sub.add_parser("stop")
    s.add_argument("record")
    s.add_argument("--session")
    s.add_argument("--force", action="store_true")
    s.set_defaults(fn=cmd_stop)
    s = sub.add_parser("say")
    s.set_defaults(fn=cmd_say)
    s = sub.add_parser("_loop")
    s.add_argument("record")
    s.set_defaults(fn=cmd_loop)
    return p


def say_args(argv):
    """`say` takes its flags and its text in any order, which argparse cannot do."""
    a = argparse.Namespace(fn=cmd_say, item=None, sender=None, rest=[])
    i = 0
    while i < len(argv):
        if argv[i] in ("--item", "--from"):
            if i + 1 >= len(argv):
                raise Usage(f"{argv[i]} needs a value")
            setattr(a, "item" if argv[i] == "--item" else "sender", argv[i + 1])
            i += 2
        else:
            a.rest.append(argv[i])
            i += 1
    return a


def main(argv):
    try:
        a = say_args(argv[1:]) if argv[:1] == ["say"] else build().parse_args(argv)
        return a.fn(a)
    except Usage as exc:
        print(f"window-watch.py: {exc}", file=sys.stderr)
        return 2
    except Refused as exc:
        print(f"window-watch.py: {exc}", file=sys.stderr)
        return 3
    except (Fail, OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        print(f"window-watch.py: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

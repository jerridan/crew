#!/usr/bin/env python3
"""crew-usage.py: the plan usage figures of the account, shared by every crew session.

usage: python3 crew-usage.py <command> [options]

The shared file is <record-root>/usage.json. The record root is
$CREW_RECORD_ROOT or ~/.claude/crew. This script is the only writer of the file.
It reads no orchestrator record and writes none: the limit comes in as an argument.

commands:
  record [--source S]      merge one status line JSON from stdin into the file
  statusline               status line wrapper: record the sample, then show the
                           user's own status line with the same stdin
  settings [--cwd D]       print the value for `claude --settings` that runs the wrapper
  probe FILE               status line command of `refresh`: append stdin to FILE
  refresh                  start a bare claude, read the figures, record them, stop it
  show [--json]            print the figures; exit 2 with no plan limits, 1 with no figures
  check [--limit N]        print the level; exit 0 normal, 10 slowed, 20 stopped
  watch [--limit N] [--interval S] [--ticks N] [--until stopped]
                           print one line when the level changes and on a reset
                           (not after a window that stayed normal). With --until
                           stopped: print nothing until the level is stopped, then
                           print one line and exit 20
  wait [--interval S]      exit 0 when the five-hour window of the stored figure resets

Test hooks: CREW_USAGE_NOW is an integer clock, or "@file" to read it from a
file on every call. CREW_USAGE_REFRESH_LIMIT is the refresh time limit in seconds.
"""

import argparse
import fcntl
import json
import os
import pty
import select
import shlex
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import termios
import time

AGE = 300  # seconds: a newest sample older than this gets a fresh reading
MARGIN = 15  # points below the limit where `slowed` starts
FORECAST_MIN = 600  # seconds between first and newest sample that a forecast needs
REFRESH_LIMIT = 30  # seconds
DEFAULT_LIMIT = 95.0
EXIT = {"normal": 0, "slowed": 10, "stopped": 20}


# ---------------------------------------------------------------- basics


def now():
    v = os.environ.get("CREW_USAGE_NOW")
    if v:
        if v.startswith("@"):
            with open(v[1:]) as f:
                return int(float(f.read().strip()))
        return int(float(v))
    return int(time.time())


def record_root():
    return os.environ.get("CREW_RECORD_ROOT") or os.path.join(
        os.path.expanduser("~"), ".claude", "crew")


def usage_path():
    return os.path.join(record_root(), "usage.json")


def load():
    try:
        with open(usage_path()) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def update(fn):
    """Read, change and write the file under a lock. fn returns the new dict, or None."""
    root = record_root()
    os.makedirs(root, exist_ok=True)
    with open(os.path.join(root, "usage.lock"), "a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        d = load()
        new = fn(d)
        if new is None:
            return
        fd, tmp = tempfile.mkstemp(prefix="usage.", suffix=".tmp", dir=root)
        try:
            with os.fdopen(fd, "w") as f:
                json.dump(new, f)
            os.replace(tmp, usage_path())
        except BaseException:
            try:
                os.unlink(tmp)
            except OSError:
                pass
            raise


def num(v):
    if isinstance(v, bool) or not isinstance(v, (int, float)):
        return None
    return v


def parse_window(w):
    if not isinstance(w, dict):
        return None
    p, r = num(w.get("used_percentage")), num(w.get("resets_at"))
    if p is None or r is None:
        return None
    return {"used_pct": p, "resets_at": int(r)}


def advanced(old, new):
    """True when the new window figure is strictly newer than the stored one.

    An equal figure is no advance: an idle session repeats its old figure on
    every refresh, and that must not make the file look fresh.
    """
    if not old:
        return True
    if new["resets_at"] != old["resets_at"]:
        return new["resets_at"] > old["resets_at"]
    return new["used_pct"] > old["used_pct"]


def merge_window(old, new, fresh=False):
    """A fresh reading of the account also replaces an equal window with a lower figure."""
    if not old:
        return new
    if new["resets_at"] > old["resets_at"]:
        return new
    if new["resets_at"] == old["resets_at"] and (fresh or new["used_pct"] > old["used_pct"]):
        return new
    return old


def apply_sample(d, sample, source, ts, fresh=False):
    """Merge one status line sample into d. Return the new dict, or None for no figures.

    updated_at moves when the five-hour figure advances strictly, or when the
    sample is a fresh reading of the account (fresh=True, from `refresh`).
    """
    rl = sample.get("rate_limits") if isinstance(sample, dict) else None
    if not isinstance(rl, dict):
        return None
    five, seven = parse_window(rl.get("five_hour")), parse_window(rl.get("seven_day"))
    if not five and not seven:
        return None
    d = dict(d)
    moved = fresh
    lowered = False
    for key, new in (("five_hour", five), ("seven_day", seven)):
        if new is None:
            continue
        old = d.get(key)
        if key == "five_hour" and advanced(old, new):
            moved = True
        d[key] = merge_window(old, new, fresh)
        if key == "five_hour" and old and d[key]["used_pct"] < old["used_pct"]:
            lowered = True
    if five:
        wf = d.get("window_first")
        if (not isinstance(wf, dict) or wf.get("resets_at") != d["five_hour"]["resets_at"]
                or lowered):
            d["window_first"] = {"resets_at": d["five_hour"]["resets_at"], "at": ts,
                                 "used_pct": d["five_hour"]["used_pct"]}
    if moved or "updated_at" not in d:
        d["updated_at"] = ts
        d["source"] = source
    d["plan_limits"] = True
    return d


def newest_ts(d):
    """When the file last got a reading: a sample, or a no-plan-limits check."""
    if d.get("plan_limits") is False:
        return d.get("checked_at")
    return d.get("updated_at")


# ---------------------------------------------------------------- levels


def forecast(d):
    """Rate in points per second and the newest time, or None."""
    five, wf = d.get("five_hour"), d.get("window_first")
    t1 = d.get("updated_at")
    if not five or not isinstance(wf, dict) or t1 is None:
        return None
    if wf.get("resets_at") != five.get("resets_at"):
        return None
    t0, p0 = wf.get("at"), wf.get("used_pct")
    if t0 is None or p0 is None or t1 - t0 < FORECAST_MIN:
        return None
    rate = (five["used_pct"] - p0) / float(t1 - t0)
    if rate <= 0:
        return None
    return rate, t1


def time_to(d, target):
    """Epoch when the forecast reaches target percent, or None."""
    f = forecast(d)
    if not f:
        return None
    rate, t1 = f
    return t1 + (target - d["five_hour"]["used_pct"]) / rate


def level_of(d, limit, at):
    five = d.get("five_hour") if d else None
    if not five or d.get("plan_limits") is False:
        return "normal"
    if five["resets_at"] <= at:
        return "normal"
    pct = five["used_pct"]
    if pct >= limit:
        return "stopped"
    if pct >= limit - MARGIN:
        return "slowed"
    hit = time_to(d, limit)
    if hit is not None and hit < five["resets_at"]:
        return "slowed"
    return "normal"


def is_stale(d, at):
    ts = newest_ts(d)
    return ts is None or at - ts > AGE


# ---------------------------------------------------------------- refresh (R3)


def read_lines(path):
    out = []
    try:
        with open(path) as f:
            for line in f:
                try:
                    out.append(json.loads(line))
                except ValueError:
                    out.append({})
    except OSError:
        pass
    return out


def has_figures(lines):
    return any(isinstance(x, dict) and isinstance(x.get("rate_limits"), dict)
               and (parse_window(x["rate_limits"].get("five_hour"))
                    or parse_window(x["rate_limits"].get("seven_day"))) for x in lines)


def stop_group(proc):
    for sig in (signal.SIGTERM, signal.SIGKILL):
        try:
            os.killpg(proc.pid, sig)
        except (ProcessLookupError, PermissionError):
            pass
        deadline = time.time() + 1.0
        while time.time() < deadline:
            try:
                os.killpg(proc.pid, 0)
            except (ProcessLookupError, PermissionError):
                break
            proc.poll()
            time.sleep(0.05)
    try:
        proc.wait(timeout=2)
    except subprocess.TimeoutExpired:
        pass


def do_refresh():
    """Start claude the bare way, read its status line figures, record them.

    Return 0 when the start ran the status line, 1 when it did not.
    """
    limit = float(os.environ.get("CREW_USAGE_REFRESH_LIMIT") or REFRESH_LIMIT)
    tmp = tempfile.mkdtemp(prefix="crew-usage-")
    probe = os.path.join(tmp, "probe")
    master = None
    proc = None
    try:
        cmd = "%s %s probe %s" % (shlex.quote(sys.executable or "python3"),
                                  shlex.quote(os.path.abspath(__file__)), shlex.quote(probe))
        settings = json.dumps({"statusLine": {"type": "command", "command": cmd,
                                              "refreshInterval": 5}})
        master, slave = pty.openpty()
        try:
            fcntl.ioctl(slave, termios.TIOCSWINSZ, struct.pack("HHHH", 40, 120, 0, 0))
        except OSError:
            pass
        # The start keeps the caller's directory. A new directory makes claude
        # ask for trust, and the status line never runs.
        try:
            proc = subprocess.Popen(
                ["claude", "--restricted", "--strict-mcp-config", "--settings", settings],
                stdin=slave, stdout=slave, stderr=slave,
                start_new_session=True, close_fds=True)
        except OSError:
            return 1
        finally:
            os.close(slave)
        deadline = time.time() + limit
        while time.time() < deadline:
            r, _, _ = select.select([master], [], [], 0.1)
            if r:
                try:
                    if not os.read(master, 65536):
                        r = []
                except OSError:
                    r = []
            exited = proc.poll() is not None
            if has_figures(read_lines(probe)):
                break
            if exited:
                break
        stop_group(proc)
        lines = read_lines(probe)
    finally:
        if master is not None:
            os.close(master)
        shutil.rmtree(tmp, ignore_errors=True)
    if not lines:
        return 1
    ts = now()
    result = [0]

    def fn(d):
        out = d
        got = False
        for x in lines:
            new = apply_sample(out, x, "refresh", ts, fresh=True)
            if new is not None:
                out, got = new, True
        if got:
            return out
        five = out.get("five_hour")
        if five and five["resets_at"] > ts:
            # The start ran the status line but gave no figures. A stored
            # window that has not reset says the account has limits: keep it.
            result[0] = 1
            return None
        out = dict(out)
        out["plan_limits"] = False
        out["checked_at"] = ts
        out["source"] = "refresh"
        return out

    update(fn)
    return result[0]


def mark_attempt():
    """Record the start of a fresh reading attempt, without a check of the age."""
    ts = now()
    update(lambda d: dict(d, refresh_attempt_at=ts))


def claim_refresh():
    """Take the right to start claude, under the lock.

    True when the file is stale and no attempt began in the last AGE seconds.
    Two processes that find the file stale cannot both get True.
    """
    got = [False]

    def fn(d):
        at = now()
        if not is_stale(d, at):
            return None
        t = d.get("refresh_attempt_at")
        if t is not None and at - t < AGE:
            return None
        got[0] = True
        return dict(d, refresh_attempt_at=at)

    try:
        update(fn)
    except Exception:
        return False
    return got[0]


def run_refresh():
    """do_refresh, then record whether the attempt failed. Return its exit code."""
    try:
        rc = do_refresh()
    except Exception:
        rc = 1
    try:
        update(lambda d: dict(d, refresh_failed=(rc != 0)))
    except Exception:
        pass
    return rc


def ensure_fresh():
    """Load the file; take one fresh reading first when it is stale and no one tried lately."""
    d = load()
    if is_stale(d, now()) and claim_refresh():
        run_refresh()
        d = load()
    return d


# ---------------------------------------------------------------- user status line (R2)


def read_json(path):
    try:
        with open(path) as f:
            d = json.load(f)
        return d if isinstance(d, dict) else {}
    except (OSError, ValueError):
        return {}


def user_statusline(cwd):
    """The status line Claude Code would show: local over project over user."""
    found = None
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.join(
        os.path.expanduser("~"), ".claude")
    for p in (os.path.join(config_dir, "settings.json"),
              os.path.join(cwd, ".claude", "settings.json"),
              os.path.join(cwd, ".claude", "settings.local.json")):
        sl = read_json(p).get("statusLine")
        if isinstance(sl, dict) and sl.get("type", "command") == "command" and sl.get("command"):
            # A status line that runs this wrapper is no user line: skip it,
            # or the wrapper would call itself without end.
            if "crew-usage.py" in sl["command"] and "statusline" in sl["command"]:
                continue
            found = sl
    return found


def wrapper_command():
    return "%s %s statusline" % (shlex.quote(sys.executable or "python3"),
                                 shlex.quote(os.path.abspath(__file__)))


def cmd_record(a):
    raw = sys.stdin.buffer.read()
    try:
        sample = json.loads(raw)
    except ValueError:
        return 0
    source = a.source or "session:%s" % (sample.get("session_id") if isinstance(sample, dict)
                                          else "unknown")
    ts = now()
    update(lambda d: apply_sample(d, sample, source, ts))
    return 0


def cmd_statusline(a):
    raw = sys.stdin.buffer.read()
    run_dir = project_dir = os.getcwd()
    try:
        sample = json.loads(raw)
        if isinstance(sample, dict):
            ws = sample.get("workspace") if isinstance(sample.get("workspace"), dict) else {}

            def pick(*names):
                for n in names:
                    if isinstance(n, str) and os.path.isdir(n):
                        return n
                return None

            # Project settings sit under project_dir. The user's command runs
            # in the session's own directory, as Claude Code runs it.
            run_dir = pick(ws.get("current_dir"), sample.get("cwd")) or run_dir
            project_dir = pick(ws.get("project_dir")) or run_dir
            source = "session:%s" % sample.get("session_id", "unknown")
            ts = now()
            update(lambda d: apply_sample(d, sample, source, ts))
    except Exception:
        pass  # a fault in the recording never removes the user's line
    try:
        sl = user_statusline(project_dir)
    except Exception:
        sl = None
    if not sl:
        return 0
    try:
        r = subprocess.run(sl["command"], shell=True, input=raw, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, cwd=run_dir)
    except Exception:
        return 0
    sys.stdout.buffer.write(r.stdout)
    sys.stdout.buffer.flush()
    sys.stderr.buffer.write(r.stderr)
    sys.stderr.buffer.flush()
    return r.returncode if r.returncode >= 0 else 1


def cmd_settings(a):
    cwd = a.cwd or os.getcwd()
    sl = {"type": "command", "command": wrapper_command()}
    user = user_statusline(cwd) or {}
    for k in ("padding", "refreshInterval"):
        if k in user:
            sl[k] = user[k]
    print(json.dumps({"statusLine": sl}))
    return 0


def cmd_probe(a):
    raw = sys.stdin.buffer.read()
    try:
        line = json.dumps(json.loads(raw))
    except ValueError:
        line = "{}"
    with open(a.file, "a") as f:
        f.write(line + "\n")
    return 0


def cmd_refresh(a):
    try:
        mark_attempt()
    except Exception:
        pass
    rc = run_refresh()
    if rc:
        print("crew-usage: claude did not start or ran no status line", file=sys.stderr)
    return rc


# ---------------------------------------------------------------- show, check, watch, wait


def iso(ts):
    return time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(ts))


def cmd_show(a):
    d = load()
    five, seven = d.get("five_hour"), d.get("seven_day")
    if d.get("plan_limits") is False:
        print("crew-usage: the account has no plan limits", file=sys.stderr)
        return 2
    if not five:
        print("crew-usage: no figures yet", file=sys.stderr)
        return 1
    at = now()
    five_reset = five["resets_at"] <= at
    full = None if five_reset else time_to(d, 100)
    if full is not None and full >= five["resets_at"]:
        full = None
    if full is not None:
        full = int(full)
    seven_reset = bool(seven) and seven["resets_at"] <= at
    out = {"five_hour": {"used_pct": 0 if five_reset else five["used_pct"],
                         "resets_at": five["resets_at"], "full_at": full,
                         "reset": five_reset},
           "seven_day": ({"used_pct": 0 if seven_reset else seven["used_pct"],
                          "resets_at": seven["resets_at"], "reset": seven_reset}
                         if seven else None),
           "updated_at": d.get("updated_at"), "source": d.get("source")}
    if a.json:
        print(json.dumps(out))
        return 0
    f = out["five_hour"]
    print("five_hour: %s%% used, resets %s%s, full %s" % (
        f["used_pct"], iso(f["resets_at"]), " (reset)" if five_reset else "",
        iso(full) if full else "not before the reset"))
    if seven:
        print("seven_day: %s%% used, resets %s%s" % (
            out["seven_day"]["used_pct"], iso(seven["resets_at"]),
            " (reset)" if seven_reset else ""))
    else:
        print("seven_day: no figure")
    return 0


def sampled_text(d):
    """`sampled=<UTC ISO time>` of the newest reading in d, or `sampled=none`."""
    ts = newest_ts(d)
    if ts is None:
        return "sampled=none"
    return "sampled=" + time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def limit_arg(a):
    return float(a.limit) if a.limit is not None else DEFAULT_LIMIT


def cmd_check(a):
    d = ensure_fresh()
    lv = level_of(d, limit_arg(a), now())
    # The first word is the level. The rest says how old the reading is, so a
    # caller that passes the reading on never states a time from memory.
    parts = [lv]
    five = d.get("five_hour")
    if five and d.get("plan_limits") is not False:
        parts.append("five_hour=%s%%" % five["used_pct"])
    parts.append(sampled_text(d))
    if d.get("source"):
        parts.append("source=%s" % d["source"])
    print(" ".join(parts))
    return EXIT[lv]


def say(line):
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def cmd_watch(a):
    limit = limit_arg(a)
    last_level = None
    prev_reset = None
    announced = set()
    tick = 0
    until_stopped = a.until == "stopped"
    while True:
        tick += 1
        at = now()
        d = ensure_fresh()
        five = d.get("five_hour")
        lv = level_of(d, limit, at)
        reset = False
        if five:
            cur = five["resets_at"]
            if (prev_reset is not None and prev_reset not in announced
                    and (at >= prev_reset or cur > prev_reset)):
                announced.add(prev_reset)
                reset = True
            prev_reset = cur
        pct = five["used_pct"] if five else "none"
        if until_stopped:
            if lv == "stopped":
                say("usage level=stopped five_hour=%s%% limit=%s %s" % (pct, limit, sampled_text(d)))
                return EXIT["stopped"]
        elif reset:
            # A reset after a window that stayed normal changes nothing for the
            # orchestrator: print no line, so it costs no model turn.
            if last_level != "normal":
                say("usage reset: level=%s five_hour=%s%% %s" % (lv, pct, sampled_text(d)))
        elif last_level is not None and lv != last_level:
            say("usage level=%s five_hour=%s%% limit=%s %s" % (lv, pct, limit, sampled_text(d)))
        last_level = lv
        if a.ticks and tick >= a.ticks:
            return 0
        time.sleep(a.interval)


def cmd_wait(a):
    d = load()
    five = d.get("five_hour")
    if not five:
        print("crew-usage: no figures to wait on", file=sys.stderr)
        return 1
    target = five["resets_at"]
    while True:
        if now() >= target:
            return 0
        cur = load().get("five_hour")
        if cur and cur["resets_at"] > target:
            return 0
        time.sleep(a.interval)


def main(argv=None):
    p = argparse.ArgumentParser(prog="crew-usage.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("record")
    s.add_argument("--source")
    s.set_defaults(fn=cmd_record)
    s = sub.add_parser("statusline")
    s.set_defaults(fn=cmd_statusline)
    s = sub.add_parser("settings")
    s.add_argument("--cwd")
    s.set_defaults(fn=cmd_settings)
    s = sub.add_parser("probe")
    s.add_argument("file")
    s.set_defaults(fn=cmd_probe)
    s = sub.add_parser("refresh")
    s.set_defaults(fn=cmd_refresh)
    s = sub.add_parser("show")
    s.add_argument("--json", action="store_true")
    s.set_defaults(fn=cmd_show)
    s = sub.add_parser("check")
    s.add_argument("--limit")
    s.set_defaults(fn=cmd_check)
    s = sub.add_parser("watch")
    s.add_argument("--limit")
    s.add_argument("--interval", type=float, default=30.0)
    s.add_argument("--ticks", type=int, default=0)
    s.add_argument("--until", choices=["stopped"])
    s.set_defaults(fn=cmd_watch)
    s = sub.add_parser("wait")
    s.add_argument("--interval", type=float, default=30.0)
    s.set_defaults(fn=cmd_wait)
    a = p.parse_args(argv)
    try:
        return a.fn(a)
    except KeyboardInterrupt:
        return 130


if __name__ == "__main__":
    sys.exit(main())

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
  show [--json]            print the figures; exit 1 with no plan limits or no figures
  check [--limit N]        print the level; exit 0 normal, 10 slowed, 20 stopped
  watch [--limit N] [--interval S] [--ticks N]
                           print one line when the level changes and on a reset
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


def newer(old, new):
    """True when the new window figure is at least as new as the stored one."""
    if not old:
        return True
    if new["resets_at"] != old["resets_at"]:
        return new["resets_at"] > old["resets_at"]
    return new["used_pct"] >= old["used_pct"]


def merge_window(old, new):
    if not old:
        return new
    if new["resets_at"] > old["resets_at"]:
        return new
    if new["resets_at"] == old["resets_at"] and new["used_pct"] > old["used_pct"]:
        return new
    return old


def apply_sample(d, sample, source, ts):
    """Merge one status line sample into d. Return the new dict, or None for no figures."""
    rl = sample.get("rate_limits") if isinstance(sample, dict) else None
    if not isinstance(rl, dict):
        return None
    five, seven = parse_window(rl.get("five_hour")), parse_window(rl.get("seven_day"))
    if not five and not seven:
        return None
    d = dict(d)
    moved = False
    for key, new in (("five_hour", five), ("seven_day", seven)):
        if new is None:
            continue
        old = d.get(key)
        if newer(old, new):
            moved = True
        d[key] = merge_window(old, new)
    if five:
        wf = d.get("window_first")
        if not isinstance(wf, dict) or wf.get("resets_at") != d["five_hour"]["resets_at"]:
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

    def fn(d):
        out = d
        got = False
        for x in lines:
            new = apply_sample(out, x, "refresh", ts)
            if new is not None:
                out, got = new, True
        if got:
            return out
        out = dict(out)
        out["plan_limits"] = False
        out["checked_at"] = ts
        out["source"] = "refresh"
        return out

    update(fn)
    return 0


def ensure_fresh():
    d = load()
    if is_stale(d, now()):
        try:
            do_refresh()
        except Exception:
            pass
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
    for p in (os.path.join(os.path.expanduser("~"), ".claude", "settings.json"),
              os.path.join(cwd, ".claude", "settings.json"),
              os.path.join(cwd, ".claude", "settings.local.json")):
        sl = read_json(p).get("statusLine")
        if isinstance(sl, dict) and sl.get("type", "command") == "command" and sl.get("command"):
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
    cwd = os.getcwd()
    try:
        sample = json.loads(raw)
        if isinstance(sample, dict):
            ws = sample.get("workspace") if isinstance(sample.get("workspace"), dict) else {}
            c = ws.get("project_dir") or ws.get("current_dir") or sample.get("cwd")
            if isinstance(c, str) and os.path.isdir(c):
                cwd = c
            source = "session:%s" % sample.get("session_id", "unknown")
            ts = now()
            update(lambda d: apply_sample(d, sample, source, ts))
    except Exception:
        pass  # a fault in the recording never removes the user's line
    try:
        sl = user_statusline(cwd)
    except Exception:
        sl = None
    if not sl:
        return 0
    try:
        r = subprocess.run(sl["command"], shell=True, input=raw, stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, cwd=cwd)
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
    rc = do_refresh()
    if rc:
        print("crew-usage: claude did not start or ran no status line", file=sys.stderr)
    return rc


# ---------------------------------------------------------------- show, check, watch, wait


def iso(ts):
    return time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime(ts))


def cmd_show(a):
    d = load()
    five, seven = d.get("five_hour"), d.get("seven_day")
    if not five or d.get("plan_limits") is False:
        print("crew-usage: no plan usage figures", file=sys.stderr)
        return 1
    full = time_to(d, 100)
    if full is not None and full >= five["resets_at"]:
        full = None
    if full is not None:
        full = int(full)
    out = {"five_hour": {"used_pct": five["used_pct"], "resets_at": five["resets_at"],
                         "full_at": full},
           "seven_day": ({"used_pct": seven["used_pct"], "resets_at": seven["resets_at"]}
                         if seven else None),
           "updated_at": d.get("updated_at"), "source": d.get("source")}
    if a.json:
        print(json.dumps(out))
        return 0
    print("five_hour: %s%% used, resets %s, full %s" % (
        five["used_pct"], iso(five["resets_at"]), iso(full) if full else "not before the reset"))
    if seven:
        print("seven_day: %s%% used, resets %s" % (seven["used_pct"], iso(seven["resets_at"])))
    else:
        print("seven_day: no figure")
    return 0


def limit_arg(a):
    return float(a.limit) if a.limit is not None else DEFAULT_LIMIT


def cmd_check(a):
    lv = level_of(ensure_fresh(), limit_arg(a), now())
    print(lv)
    return EXIT[lv]


def say(line):
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


def cmd_watch(a):
    limit = limit_arg(a)
    last_level = None
    prev_reset = None
    announced = set()
    last_attempt = None
    tick = 0
    while True:
        tick += 1
        at = now()
        d = load()
        if is_stale(d, at) and (last_attempt is None or at - last_attempt >= AGE):
            last_attempt = at
            try:
                do_refresh()
            except Exception:
                pass
            d = load()
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
        if reset:
            say("usage reset: level=%s five_hour=%s%%" % (lv, pct))
        elif last_level is not None and lv != last_level:
            say("usage level=%s five_hour=%s%% limit=%s" % (lv, pct, limit))
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

#!/usr/bin/env python3
"""Seeded test of crew-usage.py (R1 to R7 and the wait command of R8).

usage: python3 skills/orchestrator/scripts/test-crew-usage.py

It runs every check against a temp HOME and a temp record root. A stub
`claude` is the only `claude` on PATH. The clock of the script under test is
set with CREW_USAGE_NOW. The last line is `N of M checks passed`. The exit
code is 0 only when N equals M.
"""

import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "crew-usage.py")
PY = sys.executable

T = tempfile.mkdtemp(prefix="crew-usage-test-")
HOME = os.path.join(T, "home")
REC = os.path.join(T, "rec")
BIN = os.path.join(T, "bin")
STUB = os.path.join(T, "stub")
PROJ = os.path.join(T, "proj")
NOWFILE = os.path.join(T, "now")
for d in (HOME + "/.claude", REC, BIN, STUB, PROJ + "/.claude"):
    os.makedirs(d, exist_ok=True)

NOW = 1_800_000_000
R = NOW + 3600  # a five-hour window that resets in one hour
USAGE = os.path.join(REC, "usage.json")

passed = 0
total = 0


def check(label, ok):
    global passed, total
    total += 1
    if ok:
        passed += 1
        print("ok   " + label)
    else:
        print("FAIL " + label)


STUB_SRC = r"""#!/bin/bash
echo "$@" >> "$STUB_DIR/args"
echo x >> "$STUB_DIR/calls"
echo "$$" > "$STUB_DIR/pid"
[ -n "$STUB_DELAY" ] && sleep "$STUB_DELAY"
val=''
prev=''
for a in "$@"; do
  [ "$prev" = "--settings" ] && val=$a
  prev=$a
done
cmd=$(python3 -c 'import json,sys;print(json.loads(sys.argv[1])["statusLine"]["command"])' "$val")
run() { printf '%s' "$1" | sh -c "$cmd" >/dev/null 2>&1; }
hang() {
  sleep 100 &
  echo "$!" > "$STUB_DIR/childpid"
  wait
}
fig="{\"session_id\":\"stub\",\"rate_limits\":{\"five_hour\":{\"used_percentage\":${STUB_PCT:-12},\"resets_at\":${STUB_RESETS:-0}},\"seven_day\":{\"used_percentage\":33,\"resets_at\":${STUB_RESETS7:-0}}}}"
case "$STUB_MODE" in
  fail) exit 1 ;;
  nofigures) run '{"session_id":"stub"}'; exit 0 ;;
  figures) run '{"session_id":"stub"}'; run "$fig"; hang ;;
  hangtrap) trap '' TERM; run '{"session_id":"stub"}'; hang ;;
esac
exit 1
"""
with open(os.path.join(BIN, "claude"), "w") as f:
    f.write(STUB_SRC)
os.chmod(os.path.join(BIN, "claude"), 0o755)

PATH = os.pathsep.join([BIN, os.path.dirname(PY), "/usr/bin", "/bin"])


def env(**extra):
    e = {
        "HOME": HOME,
        "CREW_RECORD_ROOT": REC,
        "PATH": PATH,
        "CREW_USAGE_NOW": str(NOW),
        "CREW_USAGE_REFRESH_LIMIT": "3",
        "STUB_DIR": STUB,
        "STUB_MODE": "fail",
        "STUB_RESETS": str(R),
        "STUB_RESETS7": str(NOW + 3 * 86400),
        "PYTHONDONTWRITEBYTECODE": "1",
    }
    e.update({k: str(v) for k, v in extra.items()})
    return e


def run(args, stdin=b"", timeout=60, **extra):
    if isinstance(stdin, str):
        stdin = stdin.encode()
    return subprocess.run(
        [PY, SCRIPT] + list(args),
        input=stdin,
        capture_output=True,
        env=env(**extra),
        timeout=timeout,
    )


def load():
    with open(USAGE) as f:
        return json.load(f)


def sample(five=None, five_resets=R, seven=30, seven_resets=NOW + 3 * 86400, sid="s1"):
    d = {"session_id": sid}
    if five is not None:
        d["rate_limits"] = {
            "five_hour": {"used_percentage": five, "resets_at": five_resets},
            "seven_day": {"used_percentage": seven, "resets_at": seven_resets},
        }
    return json.dumps(d)


def clean():
    if os.path.exists(USAGE):
        os.remove(USAGE)
    for n in os.listdir(STUB):
        os.remove(os.path.join(STUB, n))


def seed(five=None, five_resets=R, updated=NOW - 10, plan=True, first=None,
         seven=30, checked=None):
    """Write a usage.json. first is (at, pct) of the first sample of the window."""
    clean()
    d = {"plan_limits": plan, "updated_at": updated, "source": "seed"}
    if five is not None:
        d["five_hour"] = {"used_pct": five, "resets_at": five_resets}
        d["seven_day"] = {"used_pct": seven, "resets_at": NOW + 3 * 86400}
    if first is not None:
        d["window_first"] = {"resets_at": five_resets, "at": first[0], "used_pct": first[1]}
    if checked is not None:
        d["checked_at"] = checked
    with open(USAGE, "w") as f:
        json.dump(d, f)


def calls():
    p = os.path.join(STUB, "calls")
    if not os.path.exists(p):
        return 0
    with open(p) as f:
        return len(f.read().split())


def alive(pid):
    try:
        os.kill(int(pid), 0)
    except (ProcessLookupError, ValueError):
        return False
    except PermissionError:
        return True
    return True


def mtimes(paths):
    return {p: os.stat(p).st_mtime_ns for p in paths if os.path.exists(p)}


USER_SETTINGS = os.path.join(HOME, ".claude", "settings.json")
PROJ_SETTINGS = os.path.join(PROJ, ".claude", "settings.json")
PROJ_LOCAL = os.path.join(PROJ, ".claude", "settings.local.json")


def write_user_status(command, **opts):
    sl = {"type": "command", "command": command}
    sl.update(opts)
    with open(USER_SETTINGS, "w") as f:
        json.dump({"statusLine": sl}, f)


def no_user_status():
    with open(USER_SETTINGS, "w") as f:
        json.dump({"theme": "dark"}, f)


def wrapper_command(cwd=PROJ):
    r = run(["settings", "--cwd", cwd])
    return json.loads(r.stdout)["statusLine"]["command"]


def run_wrapper(stdin, cwd=PROJ, timeout=60, **extra):
    cmd = wrapper_command(cwd)
    return subprocess.run(["sh", "-c", cmd], input=stdin.encode(), capture_output=True,
                          env=env(**extra), cwd=cwd, timeout=timeout)


# ---------------------------------------------------------------- R1


def t_r1_merge():
    clean()
    run(["record", "--source", "a"], sample(40))
    run(["record", "--source", "b"], sample(30))
    d = load()
    check("R1 lower percent with the same resets_at keeps the higher figure",
          d["five_hour"]["used_pct"] == 40 and d["seven_day"]["used_pct"] == 30)
    run(["record", "--source", "c"], sample(5, five_resets=R + 18000))
    d = load()
    check("R1 later resets_at with a lower percent replaces the stored figure",
          d["five_hour"]["used_pct"] == 5 and d["five_hour"]["resets_at"] == R + 18000)
    run(["record", "--source", "d"], sample(50, five_resets=R))
    check("R1 an earlier resets_at never replaces the stored figure",
          load()["five_hour"]["resets_at"] == R + 18000)


def t_r1_idle_repeat():
    seed(five=60, updated=NOW - 600)
    run(["record"], sample(60))
    check("R1 an equal repeat of the stored figure does not move updated_at",
          load()["updated_at"] == NOW - 600)
    run(["check"], STUB_MODE="figures", STUB_PCT=61)
    check("R1 after an idle repeat the next check still takes a fresh reading",
          calls() == 1 and load()["five_hour"]["used_pct"] == 61)
    seed(five=60, updated=NOW - 600, seven=30)
    run(["record"], sample(50, seven=30))
    check("R1 an older, lower figure with an equal seven-day figure does not move updated_at",
          load()["updated_at"] == NOW - 600 and load()["five_hour"]["used_pct"] == 60)
    seed(five=60, updated=NOW - 600, seven=30)
    run(["record"], sample(60, seven=35))
    check("R1 a seven-day advance alone does not move updated_at",
          load()["updated_at"] == NOW - 600 and load()["seven_day"]["used_pct"] == 35)
    seed(five=60, updated=NOW - 600)
    run(["record"], sample(61))
    check("R1 a higher percent in the same window moves updated_at",
          load()["updated_at"] == NOW)
    seed(five=60, updated=NOW - 600)
    run(["record"], sample(3, five_resets=R + 18000))
    check("R1 a later window moves updated_at", load()["updated_at"] == NOW)


def t_r1_no_ratelimits():
    seed(five=40)
    before = load()
    run(["record"], sample(None))
    check("R1 a sample with no rate_limits changes no stored figure", load() == before)
    seed(five=40, plan=False, checked=NOW - 5)
    before = load()
    run(["record"], sample(None))
    check("R1 a sample with no rate_limits keeps the no-plan-limits flag", load() == before)


def t_r1_flag_cleared():
    seed(five=None, plan=False, checked=NOW - 5)
    run(["record", "--source", "x"], sample(22))
    d = load()
    check("R1 a sample with figures clears the no-plan-limits flag and stores the figures",
          d["plan_limits"] is True and d["five_hour"]["used_pct"] == 22)


def t_r1_fields():
    clean()
    run(["record", "--source", "writer-1"], sample(10))
    d = load()
    check("R1 the file holds arrival time, writer, plan flag and the first sample of the window",
          d.get("updated_at") == NOW and d.get("source") == "writer-1"
          and d.get("plan_limits") is True
          and d.get("window_first", {}).get("resets_at") == R
          and d["window_first"].get("used_pct") == 10 and d["window_first"].get("at") == NOW)
    run(["record", "--source", "writer-2"], sample(20), CREW_USAGE_NOW=NOW + 700)
    d = load()
    check("R1 the first sample of the window stays while the window lasts",
          d["window_first"]["at"] == NOW and d["updated_at"] == NOW + 700
          and d["source"] == "writer-2")
    run(["record"], sample(3, five_resets=R + 18000), CREW_USAGE_NOW=R + 5)
    d = load()
    check("R1 a new window makes a new first sample",
          d["window_first"]["resets_at"] == R + 18000 and d["window_first"]["used_pct"] == 3)


def t_r1_concurrent():
    clean()
    procs = []
    for i in range(1, 25):
        p = subprocess.Popen([PY, SCRIPT, "record", "--source", "w%d" % i],
                             stdin=subprocess.PIPE, env=env(),
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        p.stdin.write(sample(i, seven=i * 2).encode())
        p.stdin.close()
        procs.append(p)
    bad = 0
    while any(p.poll() is None for p in procs):
        if os.path.exists(USAGE):
            try:
                with open(USAGE) as f:
                    json.load(f)
            except ValueError:
                bad += 1
    for p in procs:
        p.wait()
    d = load()
    check("R1 the file is valid JSON at every read while many writers run", bad == 0)
    check("R1 many writers at once lose no sample the merge rule keeps",
          d["five_hour"]["used_pct"] == 24 and d["seven_day"]["used_pct"] == 48)


# ---------------------------------------------------------------- R2


def t_r2():
    base = mtimes([USER_SETTINGS, PROJ_SETTINGS, PROJ_LOCAL])
    stdin = sample(17, sid="w2") + "\n"

    clean()
    write_user_status("cat")
    r = run_wrapper(stdin)
    check("R2 wrapper output equals the user command output for the same stdin",
          r.stdout == stdin.encode() and r.returncode == 0)
    check("R2 the wrapper records the sample", load()["five_hour"]["used_pct"] == 17)

    clean()
    write_user_status("cat >/dev/null; echo partial; exit 3")
    r = run_wrapper(stdin)
    check("R2 a user command that exits non-zero keeps its output and exit code",
          r.stdout == b"partial\n" and r.returncode == 3)
    check("R2 the sample is recorded when the user command fails",
          load()["five_hour"]["used_pct"] == 17)

    clean()
    write_user_status("cat >/dev/null; exit 2")
    r = run_wrapper(stdin)
    check("R2 a user command that prints nothing keeps its exit code",
          r.stdout == b"" and r.returncode == 2 and load()["five_hour"]["used_pct"] == 17)

    clean()
    no_user_status()
    r = run_wrapper(stdin)
    check("R2 with no user status line the output is empty or one short line",
          len(r.stdout.splitlines()) <= 1 and len(r.stdout) < 120 and r.returncode == 0)
    check("R2 with no user status line the sample is recorded",
          load()["five_hour"]["used_pct"] == 17)

    clean()
    write_user_status("cat")
    blocker = os.path.join(T, "blocker")
    with open(blocker, "w") as f:
        f.write("x")
    r = run_wrapper(stdin, CREW_RECORD_ROOT=os.path.join(blocker, "sub"))
    check("R2 a recording fault does not remove the user's line",
          r.stdout == stdin.encode() and r.returncode == 0)

    clean()
    write_user_status("echo user-line")
    with open(PROJ_LOCAL, "w") as f:
        json.dump({"statusLine": {"type": "command", "command": "echo local-line"}}, f)
    base[PROJ_LOCAL] = os.stat(PROJ_LOCAL).st_mtime_ns
    r = run_wrapper(stdin)
    check("R2 a local settings status line wins over the user one", r.stdout == b"local-line\n")
    os.remove(PROJ_LOCAL)
    base.pop(PROJ_LOCAL, None)

    clean()
    write_user_status(wrapper_command(), padding=3)
    try:
        r = run_wrapper(stdin, timeout=10)
        ok = (r.returncode == 0 and r.stdout == b""
              and load()["five_hour"]["used_pct"] == 17)
    except subprocess.TimeoutExpired:
        ok = False
    check("R2 a user status line that is the wrapper itself ends at once, records and prints nothing",
          ok)
    sl = json.loads(run(["settings", "--cwd", PROJ]).stdout)["statusLine"]
    check("R2 settings copies no option from a status line that is the wrapper itself",
          "padding" not in sl)

    # session directory: settings from project_dir, command run in current_dir
    clean()
    sub = os.path.join(PROJ, "sub")
    os.makedirs(sub, exist_ok=True)
    write_user_status("pwd -P")
    cwd_stdin = json.dumps({"session_id": "s9", "workspace": {"project_dir": PROJ,
                                                              "current_dir": sub},
                            "rate_limits": json.loads(sample(17))["rate_limits"]})
    r = run_wrapper(cwd_stdin)
    check("R2 the user command runs in current_dir, not in project_dir",
          r.stdout.decode().strip() == os.path.realpath(sub))
    no_user_status()
    with open(PROJ_LOCAL, "w") as f:
        json.dump({"statusLine": {"type": "command", "command": "pwd -P"}}, f)
    r = run_wrapper(cwd_stdin)
    check("R2 project settings are found with project_dir, and the command runs in current_dir",
          r.stdout.decode().strip() == os.path.realpath(sub))
    os.remove(PROJ_LOCAL)
    cwd_stdin2 = json.dumps({"session_id": "s9", "cwd": sub,
                             "rate_limits": json.loads(sample(17))["rate_limits"]})
    write_user_status("pwd -P")
    r = run_wrapper(cwd_stdin2)
    check("R2 with no workspace the command runs in the session cwd",
          r.stdout.decode().strip() == os.path.realpath(sub))

    # CLAUDE_CONFIG_DIR
    cfg = os.path.join(T, "cfg")
    os.makedirs(cfg, exist_ok=True)
    with open(os.path.join(cfg, "settings.json"), "w") as f:
        json.dump({"statusLine": {"type": "command", "command": "echo from-config-dir",
                                  "padding": 4}}, f)
    no_user_status()
    r = run_wrapper(stdin, CLAUDE_CONFIG_DIR=cfg)
    check("R2 the user status line is read from CLAUDE_CONFIG_DIR when it is set",
          r.stdout == b"from-config-dir\n")
    r = run(["settings", "--cwd", PROJ], CLAUDE_CONFIG_DIR=cfg)
    check("R2 settings copies the options from CLAUDE_CONFIG_DIR",
          json.loads(r.stdout)["statusLine"].get("padding") == 4)

    write_user_status("echo x", padding=2, refreshInterval=7)
    r = run(["settings", "--cwd", PROJ])
    try:
        v = json.loads(r.stdout)
        sl = v["statusLine"]
        ok = (sl["type"] == "command" and "crew-usage.py" in sl["command"]
              and sl["padding"] == 2 and sl["refreshInterval"] == 7)
    except Exception:
        ok = False
    check("R2 the printed --settings value is valid JSON, runs the wrapper and keeps "
          "padding and refreshInterval", ok)
    write_user_status("echo x")
    sl = json.loads(run(["settings", "--cwd", PROJ]).stdout)["statusLine"]
    check("R2 the printed value invents no padding or refreshInterval",
          "padding" not in sl and "refreshInterval" not in sl)

    after = mtimes([USER_SETTINGS, PROJ_SETTINGS, PROJ_LOCAL])
    # The user settings file was written by this test on purpose. The check below
    # reads the modification time after the last write, with a fresh read of it.
    m1 = os.stat(USER_SETTINGS).st_mtime_ns
    run(["settings", "--cwd", PROJ])
    run_wrapper(stdin)
    check("R2 no settings file has a changed modification time after the commands",
          os.stat(USER_SETTINGS).st_mtime_ns == m1
          and not os.path.exists(PROJ_SETTINGS) and not os.path.exists(PROJ_LOCAL))
    return base, after


# ---------------------------------------------------------------- R3


def t_r3():
    write_user_status("echo guard")
    m_user = os.stat(USER_SETTINGS).st_mtime_ns

    clean()
    r = run(["refresh"], STUB_MODE="figures", STUB_PCT=12)
    d = load() if os.path.exists(USAGE) else {}
    check("R3 a stub that prints figures: figures recorded and exit zero",
          r.returncode == 0 and d.get("five_hour", {}).get("used_pct") == 12
          and d.get("plan_limits") is True)
    args = open(os.path.join(STUB, "args")).read() if os.path.exists(os.path.join(STUB, "args")) else ""
    check("R3 the only form of claude holds --restricted, --strict-mcp-config and --settings",
          all(f in args.split() for f in ("--restricted", "--strict-mcp-config", "--settings"))
          and calls() == 1)
    pid = open(os.path.join(STUB, "pid")).read().strip()
    time.sleep(0.5)
    check("R3 the command leaves no claude process after figures", not alive(pid))

    clean()
    r = run(["refresh"], STUB_MODE="nofigures")
    d = load() if os.path.exists(USAGE) else {}
    check("R3 a stub that starts and prints no figures: the file marks no plan limits",
          d.get("plan_limits") is False and "five_hour" not in d)

    seed(five=44)
    before = load()
    r = run(["refresh"], STUB_MODE="fail")
    after = load()
    check("R3 a stub that fails to start changes no figure or flag and exits non-zero",
          r.returncode != 0 and all(after.get(k) == before.get(k) for k in before))
    check("R3 a failed start is recorded as the last attempt, with its failure",
          after.get("refresh_attempt_at") == NOW and after.get("refresh_failed") is True)
    clean()
    r = run(["refresh"], STUB_MODE="fail")
    d = load() if os.path.exists(USAGE) else {}
    check("R3 a failed start with no file records no figure and no plan flag",
          r.returncode != 0 and "five_hour" not in d and "plan_limits" not in d)

    clean()
    t0 = time.time()
    r = run(["refresh"], STUB_MODE="hangtrap", timeout=40)
    dt = time.time() - t0
    pid = open(os.path.join(STUB, "pid")).read().strip()
    child = open(os.path.join(STUB, "childpid")).read().strip()
    time.sleep(1)
    check("R3 a stub that never ends: the command ends within its time limit",
          dt < 3 + 8)
    check("R3 a stub that never ends leaves no claude process (parent and child)",
          not alive(pid) and not alive(child))
    check("R3 a start that ran the status line but gave no figures records no plan limits",
          os.path.exists(USAGE) and load().get("plan_limits") is False)

    # A no-figures start keeps a window that has not reset (fix round 2, finding 2).
    seed(five=96, updated=NOW - 1000)
    r = run(["refresh"], STUB_MODE="nofigures")
    d = load()
    check("R3 no figures with a live window stored: nothing recorded, non-zero exit",
          r.returncode != 0 and d.get("plan_limits") is True
          and d["five_hour"]["used_pct"] == 96 and d.get("refresh_failed") is True)
    seed(five=96, updated=NOW - 1000)
    r = run(["check", "--limit", "95"], STUB_MODE="nofigures")
    check("R3 a no-figures start does not turn the slow-down off", r.returncode == 20)
    seed(five=96, five_resets=NOW - 20, updated=NOW - 1000)
    r = run(["refresh"], STUB_MODE="nofigures")
    check("R3 no figures with only a window that has reset records no plan limits",
          r.returncode == 0 and load().get("plan_limits") is False)

    seed(five=60, updated=NOW - 1000)
    run(["refresh"], STUB_MODE="figures", STUB_PCT=60)
    check("R3 a refresh with an equal figure still moves the arrival time",
          load()["updated_at"] == NOW and load().get("refresh_failed") is False)

    seed(five=90, updated=NOW - 1000, seven=80, first=(NOW - 3000, 10))
    r = run(["refresh"], STUB_MODE="figures", STUB_PCT=40, STUB_RESETS=R,
            STUB_RESETS7=NOW + 3 * 86400)
    d = load()
    check("R3 a refresh with a lower figure in the same window lowers both windows",
          r.returncode == 0 and d["five_hour"]["used_pct"] == 40
          and d["seven_day"]["used_pct"] == 33 and d["updated_at"] == NOW)
    check("R3 a lowered five-hour figure starts the forecast again from that figure",
          d["window_first"] == {"resets_at": R, "at": NOW, "used_pct": 40})
    run(["record"], sample(30, five_resets=R, seven=20))
    check("R3 after a lowered figure a status line sample still never lowers it",
          load()["five_hour"]["used_pct"] == 40
          and load()["seven_day"]["used_pct"] == 33)
    seed(five=90, updated=NOW - 1000)
    run(["refresh"], STUB_MODE="figures", STUB_PCT=40, STUB_RESETS=R - 100,
        STUB_RESETS7=NOW + 3 * 86400)
    check("R3 a refresh with an earlier resets_at does not replace the stored window",
          load()["five_hour"]["used_pct"] == 90)

    check("R3 no settings file has a changed modification time",
          os.stat(USER_SETTINGS).st_mtime_ns == m_user)


# ---------------------------------------------------------------- R4


def t_r4():
    seed(five=30, updated=NOW - 400)
    r = run(["check"], STUB_MODE="figures", STUB_PCT=35)
    check("R4 check takes a fresh reading when the newest sample is older than 5 minutes",
          calls() == 1 and load()["five_hour"]["used_pct"] == 35)
    seed(five=30, updated=NOW - 60)
    r = run(["check"], STUB_MODE="figures", STUB_PCT=35)
    check("R4 check takes no fresh reading when the newest sample is newer",
          calls() == 0 and load()["five_hour"]["used_pct"] == 30)
    seed(five=30, updated=NOW - 400)
    r = run(["watch", "--ticks", "1", "--interval", "0.1"], STUB_MODE="figures")
    check("R4 watch takes a fresh reading when the newest sample is older", calls() == 1)
    seed(five=30, updated=NOW - 60)
    r = run(["watch", "--ticks", "1", "--interval", "0.1"], STUB_MODE="figures")
    check("R4 watch takes no fresh reading when the newest sample is newer", calls() == 0)
    seed(five=30, updated=NOW - 400)
    d = load()
    d["refresh_attempt_at"] = NOW - 60
    d["refresh_failed"] = True
    with open(USAGE, "w") as f:
        json.dump(d, f)
    run(["check"], STUB_MODE="figures")
    run(["watch", "--ticks", "1", "--interval", "0.1"], STUB_MODE="figures")
    run(["watch", "--ticks", "1", "--interval", "0.1", "--until", "stopped"], STUB_MODE="figures")
    check("R4 a start inside 5 minutes of the last attempt is skipped (check, watch, until)",
          calls() == 0)
    d["refresh_attempt_at"] = NOW - 400
    with open(USAGE, "w") as f:
        json.dump(d, f)
    run(["check"], STUB_MODE="figures")
    check("R4 an attempt older than 5 minutes allows a new start", calls() == 1)
    seed(five=30, updated=NOW - 400)
    procs = [subprocess.Popen([PY, SCRIPT, "check"], env=env(STUB_MODE="figures", STUB_DELAY="1"),
                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
             for _ in range(4)]
    for p in procs:
        p.wait()
    check("R4 four processes that find the file stale start claude once", calls() == 1)
    seed(five=None, plan=False, checked=NOW - 60)
    run(["check"], STUB_MODE="figures")
    check("R4 a recent no-plan-limits check counts as a fresh reading", calls() == 0)
    seed(five=None, plan=False, checked=NOW - 400)
    run(["check"], STUB_MODE="figures")
    check("R4 an old no-plan-limits check is read again", calls() == 1)


# ---------------------------------------------------------------- R5


def t_r5():
    seed(five=50, first=(NOW - 3610, 0), seven=33)
    r = run(["show", "--json"])
    try:
        d = json.loads(r.stdout)
        ok = (r.returncode == 0 and d["five_hour"]["used_pct"] == 50
              and d["five_hour"]["resets_at"] == R and "full_at" in d["five_hour"]
              and d["seven_day"]["used_pct"] == 33 and "resets_at" in d["seven_day"])
        full_ok = abs(d["five_hour"]["full_at"] - (NOW + 3590)) < 2
    except Exception:
        ok = full_ok = False
    check("R5 show --json prints the five_hour and seven_day figures", ok)
    check("R5 full_at is the time of the linear forecast to 100 percent", full_ok)
    seed(five=50)
    d = json.loads(run(["show", "--json"]).stdout)
    check("R5 full_at is null when there is no forecast", d["five_hour"]["full_at"] is None)
    r = run(["show"])
    check("R5 plain show prints one line for each window",
          r.returncode == 0 and len(r.stdout.decode().strip().splitlines()) == 2)
    seed(five=None, plan=False, checked=NOW - 5)
    r1, r2 = run(["show", "--json"]), run(["show"])
    check("R5 show exits 2 when the account has no plan limits, and says so",
          r1.returncode == 2 and r2.returncode == 2 and b"no plan limits" in r1.stderr
          and b"no plan limits" in r2.stderr)
    clean()
    r1, r2 = run(["show", "--json"]), run(["show"])
    check("R5 show exits 1 with no file, and says there are no figures",
          r1.returncode == 1 and r2.returncode == 1 and b"no figures" in r1.stderr
          and b"no figures" in r2.stderr)
    seed(five=96, five_resets=NOW - 20, updated=NOW - 100, seven=40)
    d = json.loads(run(["show", "--json"]).stdout)
    check("R5 show after the window reset: used_pct 0, full_at null, reset true, resets_at kept",
          d["five_hour"]["used_pct"] == 0 and d["five_hour"]["full_at"] is None
          and d["five_hour"]["reset"] is True and d["five_hour"]["resets_at"] == NOW - 20)
    seed(five=50)
    d = json.loads(run(["show", "--json"]).stdout)
    check("R5 show inside the window has reset false", d["five_hour"]["reset"] is False)


# ---------------------------------------------------------------- R6


def level(limit=None, **seedargs):
    seed(**seedargs)
    args = ["check"] + (["--limit", str(limit)] if limit is not None else [])
    r = run(args, STUB_MODE="fail")
    return r.stdout.decode().split()[0], r.returncode


def iso_t(ts):
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(ts))


def t_r6_line():
    seed(five=96, updated=NOW - 10)
    r = run(["check"], STUB_MODE="fail")
    line = r.stdout.decode().strip()
    check("R6 the check line starts with the level, then the figure, sample time and source",
          line == "stopped five_hour=96%% sampled=%s source=seed" % iso_t(NOW - 10)
          and r.returncode == 20)
    seed(five=None, plan=False, checked=NOW - 5)
    line = run(["check"], STUB_MODE="fail").stdout.decode().strip()
    check("R6 with no plan limits the check line carries the time of the check",
          line.startswith("normal ") and "sampled=%s" % iso_t(NOW - 5) in line)
    clean()
    r = run(["check"], STUB_MODE="fail")
    check("R6 with no figures the check line says sampled=none",
          r.stdout.decode().strip() == "normal sampled=none" and r.returncode == 0)


def t_r6():
    flat = (NOW - 3610, 20)
    check("R6 a figure below limit minus 15 with a flat forecast is normal",
          level(five=20, first=flat) == ("normal", 0))
    lv, rc80 = level(five=80, first=(NOW - 3610, 80))
    check("R6 a figure at limit minus 15 is slowed", lv == "slowed")
    check("R6 a figure just below limit minus 15 is normal",
          level(five=79.9, first=(NOW - 3610, 79.9))[0] == "normal")
    lv, rcs = level(five=95, first=(NOW - 3610, 95))
    check("R6 a figure at the limit is stopped", lv == "stopped")
    check("R6 a figure above the limit is stopped",
          level(five=99, first=(NOW - 3610, 99))[0] == "stopped")
    check("R6 a forecast that reaches the limit before the reset is slowed",
          level(five=50, first=(NOW - 3610, 0))[0] == "slowed")
    check("R6 a forecast that reaches the limit after the reset is normal",
          level(five=50, first=(NOW - 3610, 35))[0] == "normal")
    check("R6 samples less than 10 minutes apart: the forecast is not used",
          level(five=50, updated=NOW - 10, first=(NOW - 310, 0))[0] == "normal")
    check("R6 a sample after the reset is normal",
          level(five=99, five_resets=NOW - 20, updated=NOW - 100)[0] == "normal")
    check("R6 no plan limits is normal",
          level(five=None, plan=False, checked=NOW - 5) == ("normal", 0))
    _, rcn = level(five=20, first=flat)
    check("R6 the three levels give three different exit codes",
          len({rcn, rc80, rcs}) == 3 and rcn == 0)
    check("R6 a limit of 80 moves the stopped threshold",
          level(limit=80, five=80, first=(NOW - 3610, 80))[0] == "stopped")
    check("R6 a limit of 80 moves the slowed threshold",
          level(limit=80, five=65, first=(NOW - 3610, 65))[0] == "slowed"
          and level(limit=80, five=64, first=(NOW - 3610, 64))[0] == "normal")
    check("R6 with no argument the limit is 95",
          level(five=94, first=(NOW - 3610, 94))[0] == "slowed"
          and level(five=95, first=(NOW - 3610, 95))[0] == "stopped")


# ---------------------------------------------------------------- R7


def start_watch(**extra):
    return subprocess.Popen([PY, SCRIPT, "watch", "--interval", "0.2"],
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                            env=env(**extra))


def stop(p):
    p.terminate()
    try:
        out, _ = p.communicate(timeout=10)
    except subprocess.TimeoutExpired:
        p.kill()
        out, _ = p.communicate()
    return out.decode().splitlines()


def t_r7():
    orch = os.path.join(REC, "orchestrator")
    os.makedirs(orch, exist_ok=True)
    with open(os.path.join(orch, "state.json"), "w") as f:
        json.dump({"pace": {"mode": "normal"}}, f)
    snap = {n: (os.stat(os.path.join(orch, n)).st_mtime_ns, open(os.path.join(orch, n)).read())
            for n in os.listdir(orch)}

    flat = (NOW - 3610, 20)
    seed(five=20, first=flat)
    p = start_watch()
    time.sleep(1.0)
    seed(five=85, first=(NOW - 3610, 85))
    time.sleep(1.2)
    lines = stop(p)
    check("R7 a move from normal to slowed prints exactly one line",
          len(lines) == 1 and "slowed" in lines[0])
    check("R7 the watch line carries the sample time",
          len(lines) == 1 and "sampled=%s" % iso_t(NOW - 10) in lines[0])

    seed(five=20, first=flat)
    p = start_watch()
    time.sleep(1.5)
    lines = stop(p)
    check("R7 the watch prints no line while the level stays the same", lines == [])

    seed(five=85, first=(NOW - 3610, 85))
    p = start_watch()
    time.sleep(1.0)
    seed(five=96, first=(NOW - 3610, 96))
    time.sleep(1.2)
    lines = stop(p)
    check("R7 slowed to stopped prints one line",
          len(lines) == 1 and "stopped" in lines[0])

    with open(NOWFILE, "w") as f:
        f.write(str(NOW))
    seed(five=96, first=(NOW - 3610, 96))
    p = start_watch(CREW_USAGE_NOW="@" + NOWFILE)
    time.sleep(1.0)
    with open(NOWFILE, "w") as f:
        f.write(str(R + 30))
    time.sleep(1.5)
    lines = stop(p)
    check("R7 a reset prints one line, with the level after it",
          len(lines) == 1 and "reset" in lines[0].lower() and "level=normal" in lines[0])

    # a new window in the file, with the clock before the old reset
    seed(five=96, first=(NOW - 3610, 96))
    p = start_watch()
    time.sleep(1.0)
    seed(five=4, five_resets=R + 18000, first=(NOW - 5, 4))
    time.sleep(1.2)
    lines = stop(p)
    check("R7 a later window in the file prints one reset line with the level",
          len(lines) == 1 and "reset" in lines[0].lower() and "level=normal" in lines[0])

    # a reset after a window that stayed normal costs no line
    with open(NOWFILE, "w") as f:
        f.write(str(NOW))
    seed(five=20, first=flat)
    p = start_watch(CREW_USAGE_NOW="@" + NOWFILE)
    time.sleep(1.0)
    with open(NOWFILE, "w") as f:
        f.write(str(R + 30))
    time.sleep(1.2)
    lines = stop(p)
    check("R7 a reset after a normal window prints no line", lines == [])

    # --until stopped: waits with no output, exits 20 at stopped
    seed(five=85, first=(NOW - 3610, 85))
    p = subprocess.Popen([PY, SCRIPT, "watch", "--until", "stopped", "--interval", "0.2"],
                         stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env())
    time.sleep(1.0)
    alive_before = p.poll() is None
    seed(five=96, first=(NOW - 3610, 96))
    try:
        out, _ = p.communicate(timeout=5)
        rc = p.returncode
    except subprocess.TimeoutExpired:
        p.kill()
        out, rc = b"", None
    check("R7 watch --until stopped runs while the level is below stopped and exits 20 at stopped",
          alive_before and rc == 20 and b"stopped" in out)
    seed(five=85, first=(NOW - 3610, 85))
    r = run(["watch", "--until", "stopped", "--interval", "0.2", "--ticks", "3"])
    check("R7 watch --until stopped prints nothing and exits 0 when its ticks end below stopped",
          r.returncode == 0 and r.stdout == b"")
    seed(five=97, first=(NOW - 3610, 97))
    r = run(["watch", "--until", "stopped", "--limit", "95"], timeout=10)
    check("R7 watch --until stopped exits 20 at once when the level is stopped at the start",
          r.returncode == 20)

    now2 = {n: (os.stat(os.path.join(orch, n)).st_mtime_ns, open(os.path.join(orch, n)).read())
            for n in os.listdir(orch)}
    check("R7 a watch run changes no file in the orchestrator record", now2 == snap)


# ---------------------------------------------------------------- R8 wait


def t_r8_wait():
    with open(NOWFILE, "w") as f:
        f.write(str(NOW))
    seed(five=96, first=(NOW - 3610, 96))
    p = subprocess.Popen([PY, SCRIPT, "wait", "--interval", "0.2"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, env=env(CREW_USAGE_NOW="@" + NOWFILE))
    time.sleep(1.0)
    before = p.poll()
    with open(NOWFILE, "w") as f:
        f.write(str(R + 1))
    try:
        rc = p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()
        rc = None
    check("R8 the wait command does not exit before the reset", before is None)
    check("R8 the wait command exits zero after the reset", rc == 0)
    # a newer window in the file ends the wait before the clock passes the reset
    with open(NOWFILE, "w") as f:
        f.write(str(NOW))
    seed(five=96, first=(NOW - 3610, 96))
    p = subprocess.Popen([PY, SCRIPT, "wait", "--interval", "0.2"], stdout=subprocess.DEVNULL,
                         stderr=subprocess.DEVNULL, env=env(CREW_USAGE_NOW="@" + NOWFILE))
    time.sleep(1.0)
    before = p.poll()
    seed(five=3, five_resets=R + 18000)
    try:
        rc = p.wait(timeout=5)
    except subprocess.TimeoutExpired:
        p.kill()
        rc = None
    check("R8 the wait command exits on a newer window in the file before the clock reaches the reset",
          before is None and rc == 0)
    clean()
    r = run(["wait", "--interval", "0.2"], timeout=10)
    check("R8 the wait command exits non-zero at once when no figures exist",
          r.returncode != 0)


def main():
    base = after = None
    try:
        for fn in (t_r1_merge, t_r1_no_ratelimits, t_r1_flag_cleared, t_r1_fields,
                   t_r1_idle_repeat, t_r1_concurrent, t_r2, t_r3, t_r4, t_r5, t_r6_line, t_r6, t_r7, t_r8_wait):
            try:
                res = fn()
                if fn is t_r2:
                    base, after = res
            except Exception as e:  # a crash counts as one failed check
                check("%s crashed: %r" % (fn.__name__, e), False)
        if base is not None:
            check("R2 test settings files were not changed by the script under test",
                  all(after.get(p) == base.get(p) for p in (PROJ_SETTINGS, PROJ_LOCAL)))
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("%d of %d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

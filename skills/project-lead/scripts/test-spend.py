#!/usr/bin/env python3
"""Seeded test of the session ids that spend.py prices.

usage: python3 skills/project-lead/scripts/test-spend.py

It builds a temporary HOME with stub transcripts under
`.claude/projects/`, and a record whose `run.session_ids`, `run.park` and
`run.parks` name them. It runs `spend.py <record> <checkout> --write` and
checks `run.spend.transcript`. The last line is `N of M checks passed`. The
exit code is 0 only when N equals M.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "spend.py")
PY = sys.executable

T = tempfile.mkdtemp(prefix="crew-spend-test-")
passed = 0
total = 0

LEAD = "11111111-1111-4111-8111-111111111111"
WAITER_NOW = "22222222-2222-4222-8222-222222222222"
WAITER_OLD = "33333333-3333-4333-8333-333333333333"
WAITER_TWICE = "44444444-4444-4444-8444-444444444444"
FOREIGN = "55555555-5555-4555-8555-555555555555"


def check(label, ok):
    global passed, total
    total += 1
    if ok:
        passed += 1
        print("ok   " + label)
    else:
        print("FAIL " + label)


def transcript(home, sid, model, output, msg_id):
    d = os.path.join(home, ".claude", "projects", "-x-checkout")
    os.makedirs(d, exist_ok=True)
    entry = {"type": "assistant", "uuid": msg_id,
             "message": {"id": msg_id, "model": model,
                         "usage": {"input_tokens": 1, "output_tokens": output, "cache_read_input_tokens": 0}}}
    with open(os.path.join(d, sid + ".jsonl"), "w") as f:
        f.write(json.dumps(entry) + "\n")


def waiter(sid):
    return {"name": "pl-1", "session_id": sid, "tab": "tmux:%9", "terminal": "tmux", "tab_group": "g",
            "model": "sonnet", "started_at": "2026-11-25T10:00:01Z"}


def park(sid, **extra):
    return dict({"reason": "usage", "by": "usage", "at": "2026-11-25T10:00:00Z", "until": None, "next": "go on",
                 "from_session": LEAD, "prompt": "/x/prompt-1.md", "waiter": waiter(sid) if sid else None}, **extra)


home = os.path.join(T, "home")
transcript(home, LEAD, "claude-opus-4", 100, "m-lead")
transcript(home, WAITER_NOW, "claude-sonnet-4", 10, "m-now")
transcript(home, WAITER_OLD, "claude-haiku-4", 1, "m-old")
transcript(home, WAITER_TWICE, "claude-haiku-4", 1000, "m-twice")
transcript(home, FOREIGN, "claude-haiku-4", 5, "m-foreign")

rec = os.path.join(T, "record")
os.makedirs(rec)
state = {"goal_slug": "g", "run": {
    "created_at": "2026-11-25T09:00:00Z",
    "session_ids": [LEAD, WAITER_TWICE],
    "park": park(WAITER_NOW),
    "parks": [park(WAITER_OLD, woke={"at": "2026-11-25T11:00:00Z", "by": None, "session_id": WAITER_OLD}),
              park(WAITER_TWICE, woke={"at": "2026-11-25T12:00:00Z", "by": None, "session_id": WAITER_TWICE}),
              park(None, failed={"step": "window", "at": "2026-11-25T13:00:00Z", "error": "x"})]}}
with open(os.path.join(rec, "state.json"), "w") as f:
    json.dump(state, f)

env = dict(os.environ, HOME=home)
env.pop("CLAUDE_CONFIG_DIR", None)
r = subprocess.run([PY, SCRIPT, rec, "/x/checkout", "--write"], env=env, capture_output=True, text=True)
check("spend.py exits 0", r.returncode == 0)
with open(os.path.join(rec, "state.json")) as f:
    spent = json.load(f)["run"].get("spend", {}).get("transcript") or {}
by = spent.get("by_model") or {}
check("the run's own sessions are priced: 4 transcript files",
      "priced from this run's own 4 transcript file(s)" in r.stdout)
check("the lead session is priced", (by.get("opus") or {}).get("output") == 100)
check("the waiter of run.park is priced", (by.get("sonnet") or {}).get("output") == 10)
check("the waiters of run.parks are priced, each id once, and no foreign session",
      (by.get("haiku") or {}).get("output") == 1001 and (by.get("haiku") or {}).get("messages") == 2)

shutil.rmtree(T, ignore_errors=True)
print("%d of %d checks passed" % (passed, total))
sys.exit(0 if passed == total else 1)

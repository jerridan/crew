#!/usr/bin/env python3
"""Seeded test of `run append`, `run delete` and `run remove` of crew-record.py.

usage: python3 skills/project-lead/scripts/test-crew-record.py

It seeds a temporary record, runs each new command, and checks the result in
`state.json`, the exit code and that an error writes nothing. The last line is
`N of M checks passed`. The exit code is 0 only when N equals M.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "crew-record.py")
T = tempfile.mkdtemp(prefix="crew-record-test-")
passed = 0
total = 0


def check(label, ok):
    global passed, total
    total += 1
    passed += bool(ok)
    print(("ok   " if ok else "FAIL ") + label)


def rec(*args):
    return subprocess.run([sys.executable, SCRIPT, T, *args], capture_output=True, text=True)


def state():
    with open(os.path.join(T, "state.json"), encoding="utf-8") as handle:
        return json.load(handle)


def raw():
    with open(os.path.join(T, "state.json"), "rb") as handle:
        return handle.read()


def refused(label, *args):
    before = raw()
    result = rec(*args)
    check(label + ": exit 2", result.returncode == 2)
    check(label + ": a message", bool(result.stderr.strip()))
    check(label + ": no write", raw() == before)


try:
    for setup in (("init", "goal", "goal-slug", "s1"),
                  ("run", "set", "results", '{"a": 1, "b": {"c": 2}}'),
                  ("run", "set", "name", '"text"'),
                  ("run", "set", "types", "[true, 1, 1.0, \"1\"]")):
        check("setup " + " ".join(setup[:2]) + " exits 0", rec(*setup).returncode == 0)

    result = rec("run", "append", "session_ids", '"s2"')
    check("append adds a value", result.returncode == 0 and state()["run"]["session_ids"] == ["s1", "s2"])
    rec("run", "append", "session_ids", '"s2"')
    check("append keeps a duplicate", state()["run"]["session_ids"] == ["s1", "s2", "s2"])
    rec("run", "append", "session_ids", '{"k": [1]}')
    check("append takes an object value", state()["run"]["session_ids"][-1] == {"k": [1]})
    result = rec("run", "append", "fresh", "1")
    check("append creates an absent list", result.returncode == 0 and state()["run"]["fresh"] == [1])
    rec("run", "set", "empty", "null")
    rec("run", "append", "empty", "2")
    check("append replaces a null with a list", state()["run"]["empty"] == [2])
    rec("run", "append", "results.new", '"x"')
    check("append reaches a nested list", state()["run"]["results"]["new"] == ["x"])
    refused("append to a string", "run", "append", "name", "1")
    refused("append to an object", "run", "append", "results", "1")
    refused("append under a missing level", "run", "append", "nope.list", "1")
    refused("append under a string", "run", "append", "name.list", "1")
    refused("append bad JSON", "run", "append", "session_ids", "bare words")

    result = rec("run", "delete", "results.new")
    check("delete removes a nested key", result.returncode == 0 and "new" not in state()["run"]["results"])
    rec("run", "delete", "results.a")
    check("delete keeps the other keys", state()["run"]["results"] == {"b": {"c": 2}})
    rec("run", "delete", "empty")
    check("delete removes a top key", "empty" not in state()["run"])
    refused("delete a missing key", "run", "delete", "results.a")
    refused("delete under a missing level", "run", "delete", "nope.a")
    refused("delete under a string", "run", "delete", "name.a")

    result = rec("run", "remove", "session_ids", '"s2"')
    check("remove drops the first equal value only",
          result.returncode == 0 and state()["run"]["session_ids"] == ["s1", "s2", {"k": [1]}])
    rec("run", "remove", "session_ids", '{"k": [1]}')
    check("remove matches an object value", state()["run"]["session_ids"] == ["s1", "s2"])
    rec("run", "remove", "types", "1")
    check("remove 1 skips true", state()["run"]["types"] == [True, 1.0, "1"])
    rec("run", "remove", "types", "true")
    check("remove true skips numbers", state()["run"]["types"] == [1.0, "1"])
    refused("remove two finds no value of any type", "run", "remove", "types", '"2"')
    refused("remove an absent value", "run", "remove", "session_ids", '"zz"')
    refused("remove from an object", "run", "remove", "results", "1")
    refused("remove from a missing field", "run", "remove", "nope", "1")
    refused("remove bad JSON", "run", "remove", "session_ids", "bare words")

    with ThreadPoolExecutor(8) as pool:
        list(pool.map(lambda n: rec("run", "append", "many", str(n)), range(16)))
    check("parallel appends lose none", sorted(state()["run"]["many"]) == list(range(16)))
    check("no temp file is left", not [n for n in os.listdir(T) if n.endswith(".tmp")])
finally:
    shutil.rmtree(T, ignore_errors=True)

print(f"{passed} of {total} checks passed")
sys.exit(0 if passed == total else 1)

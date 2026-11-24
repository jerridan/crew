#!/usr/bin/env python3
"""Seeded test of plan-review.py.

usage: python3 skills/project-lead/scripts/test-plan-review.py

It builds a temporary record root, puts stub `codex` and `timeout` commands
first on PATH, runs `plan-review.py` against seeded records, and checks the
record, the files and the output. The last line is `N of M checks passed`.
The exit code is 0 only when N equals M.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "plan-review.py")
PLUGIN = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
PY = sys.executable

T = tempfile.mkdtemp(prefix="plan-review-test-")
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


def write_exec(path, text):
    with open(path, "w") as f:
        f.write(text)
    os.chmod(path, 0o755)


STUBS = os.path.join(T, "stubs")
os.makedirs(STUBS)
write_exec(os.path.join(STUBS, "timeout"), '#!/bin/sh\necho "$@" >> "$STUB_STATE.timeout"\nshift\nexec "$@"\n')
CODEX = r'''#!%s
import json, os, sys, time
a = sys.argv[1:]
state = os.environ["STUB_STATE"]
mode = os.environ.get("PR_MODE", "ok")
if a[:2] == ["login", "status"]:
    sys.exit(1 if os.environ.get("PR_NOT_LOGGED") else 0)
prompt = sys.stdin.read()
n = int(open(state + ".launch").read()) if os.path.exists(state + ".launch") else 0
open(state + ".launch", "w").write(str(n + 1))
st = json.load(open(os.path.join(os.environ["STUB_REC"], "state.json")))["run"].get("plan_review")
open(state + ".log", "a").write(json.dumps({"args": a, "plan_review": st, "prompt_len": len(prompt), "cwd": os.getcwd()}) + "\n")
sys.stderr.write("OpenAI Codex\nuser\nplease mention tokens used\ntokens used\n99\n")
if mode == "hang":
    time.sleep(30)
if mode == "quota":
    for i in range(25):
        sys.stderr.write("line %%d\n" %% i)
    sys.stderr.write("You have hit your usage limit.\n")
    sys.exit(1)
sys.stderr.write("tokens used\n1,234\n")
if mode == "noverdict":
    sys.stdout.write("preface\nPlans reviewed: 1\nSource: nothing\nno verdict here\n")
    sys.exit(0)
sys.stdout.write("preface line\nsecond preface\nPlans reviewed: 2\n\n### F1. A\nSeverity: blocking\n\n"
                 "Findings: 1 blocking\nVerdict: plan revision needed\nBlocking count: 1\n")
''' % sys.executable
write_exec(os.path.join(STUBS, "codex"), CODEX)
EMPTY = os.path.join(T, "empty")
os.makedirs(EMPTY)

COUNTER = [0]


class Ctx:
    pass


def planning_obj():
    return {"status": "planning", "outcome": None, "reason": None, "at": None, "started_at": None, "attempts": 0,
            "labels": {"blocking": 0, "suggestion": 0, "nit": 0, "unsure": 0, "don't post": 0, "not real": 0},
            "accepted": 0, "recommendations": 0, "tokens": None}


def seed(status="planning", plans=("p1", "p2"), pr=None):
    COUNTER[0] += 1
    c = Ctx()
    c.dir = os.path.join(T, "case%d" % COUNTER[0])
    c.rec = os.path.join(c.dir, "rec")
    c.checkout = os.path.join(c.dir, "checkout")
    c.stub = os.path.join(c.dir, "stub")
    os.makedirs(os.path.join(c.rec, "reviews"))
    os.makedirs(os.path.join(c.rec, "plans"))
    os.makedirs(c.checkout)
    standing = os.path.join(c.dir, "crew.md")
    open(standing, "w").write("## Gates\nSTANDING-TEXT\n")
    obj = pr or planning_obj()
    obj["status"] = status
    json.dump({"goal": "g", "run": {"checkout": c.checkout, "plan_review": obj,
                                    "standing_instructions": {"repo": standing, "machine": None}},
               "packages": []}, open(os.path.join(c.rec, "state.json"), "w"))
    for name in ("charter", "spec", "split"):
        open(os.path.join(c.rec, name + ".md"), "w").write("%s BODY\n" % name.upper())
    for p in plans:
        open(os.path.join(c.rec, "plans", p + ".md"), "w").write("PLAN-%s BODY\n" % p)
    return c


def state_of(c):
    return json.load(open(os.path.join(c.rec, "state.json")))["run"]


def pr_of(c):
    return state_of(c)["plan_review"]


def rd(path):
    return open(path).read() if os.path.exists(path) else None


def rv(c, name):
    return rd(os.path.join(c.rec, "reviews", name))


def decisions(c):
    return rd(os.path.join(c.rec, "decisions.md")) or ""


def launches(c):
    p = c.stub + ".launch"
    return int(open(p).read()) if os.path.exists(p) else 0


def go(c, *args, mode="ok", path=None, not_logged=False, base=("--poll", "1")):
    env = dict(os.environ, PATH=path or (STUBS + ":" + os.environ["PATH"]), PR_MODE=mode, STUB_STATE=c.stub,
               STUB_REC=c.rec)
    if not_logged:
        env["PR_NOT_LOGGED"] = "1"
    p = subprocess.run([PY, SCRIPT, c.rec, *args, *base], capture_output=True, text=True, env=env)
    c.out = p.stdout + p.stderr
    return p.returncode


PLANS = ["--plan", "p2:t2:1/1", "--plan", "p1:t1:1/2", "--plan", "p3:t1:2/2"]
TITLE = "Plan review: which findings does the run act on?"

# ---- skips before the launch ------------------------------------------------

c = seed()
rc = go(c, "run", *PLANS, path=EMPTY)
check("absent: exit 20 and a SKIPPED line", rc == 20 and "SKIPPED: absent" in c.out)
check("absent: the record says skipped, absent, attempts 0, status unchanged",
      pr_of(c)["outcome"] == "skipped" and pr_of(c)["reason"] == "absent" and pr_of(c)["attempts"] == 0
      and pr_of(c)["status"] == "planning")
check("absent: the skip decision entry names the reason", TITLE in decisions(c) and "skipped: absent" in decisions(c))
check("absent: nothing was built", rv(c, "plan-review-r1-instructions.md") is None)

c = seed()
rc = go(c, "run", *PLANS, not_logged=True)
check("not logged in: skipped before the launch", rc == 20 and pr_of(c)["reason"] == "not logged in"
      and launches(c) == 0 and rv(c, "plan-review-r1-instructions.md") is None)
check("not logged in: the check ran under timeout 15", "15 codex login status" in (rd(c.stub + ".timeout") or ""))
check("not logged in: the decision entry has the evidence", "skipped: not logged in" in decisions(c))

# ---- a review that ran ------------------------------------------------------

c = seed()
rc = go(c, "run", *PLANS)
ins = rv(c, "plan-review-r1-instructions.md") or ""
check("ran: exit 0 and the status line", rc == 0 and "status: RAN" in c.out)
reviewer = open(os.path.join(PLUGIN, "skills/project-lead/references/plan-reviewer.md")).read()
output = open(os.path.join(PLUGIN, "skills/project-lead/references/review-output.md")).read()
rubric = open(os.path.join(PLUGIN, "skills/review/references/severity-rubric.md")).read()
check("ran: instructions open with plan-reviewer.md, then review-output.md, then the rubric, verbatim",
      ins.startswith(reviewer) and 0 < ins.find(output) < ins.find(rubric))
check("ran: standing instructions follow the rubric, then charter, spec, split, then the plans in argument order",
      ins.find(rubric) < ins.find("STANDING-TEXT") < ins.find("CHARTER BODY") < ins.find("SPEC BODY")
      < ins.find("SPLIT BODY") < ins.find("PLAN-p2 BODY") < ins.find("PLAN-p1 BODY"))
tags = re.findall(r"<data-([0-9a-f]+) ([^>]*)>", ins)
closes = re.findall(r"</data-([0-9a-f]+)>", ins)
check("ran: one tagged block per data file, each with its own random id, and each closed",
      len(tags) == 5 and len(set(t[0] for t in tags)) == 5 and [t[0] for t in tags] == closes)
check("ran: the labels name package, territory and order",
      'source="plans/p2.md" package="p2" territory="t2" order="1 of 1"' in ins
      and 'source="plans/p1.md" package="p1" territory="t1" order="1 of 2"' in ins
      and 'source="charter.md"' in ins and 'source="split.md"' in ins)
check("ran: a missing plan gets the Missing plans line, after the plans",
      "Missing plans: p3." in ins and ins.find("PLAN-p1 BODY") < ins.find("Missing plans: p3.")
      and "PLAN-p3" not in ins)
rec_at_launch = json.loads(open(c.stub + ".log").readline())["plan_review"]
check("ran: status reviewing, attempts 1 and at were written before the launch",
      rec_at_launch["status"] == "reviewing" and rec_at_launch["attempts"] == 1 and rec_at_launch["at"])
check("ran: the record keeps reviewing, attempts 1, tokens 1234 from the last exact line",
      pr_of(c)["status"] == "reviewing" and pr_of(c)["attempts"] == 1 and pr_of(c)["tokens"] == 1234
      and pr_of(c)["outcome"] is None)
rep = rv(c, "plan-review-r1.md") or ""
check("ran: the report starts at the Plans reviewed line and has Source: codex output second",
      rep.startswith("Plans reviewed: 2\nSource: codex output\n") and "preface" not in rep
      and rep.rstrip().endswith("Blocking count: 1"))
sh = rv(c, "plan-review-r1-run.sh") or ""
check("ran: the run script has the codex command, the checkout and the 600-second wall clock",
      "codex exec --sandbox read-only -m gpt-6.2-sol -c model_reasoning_effort=medium -C %s -" % c.checkout in sh
      and "-ge 600" in sh and 'echo 124 > "$r-result.exit"' in sh)
check("ran: the exit file reads 0 and codex ran in the checkout", (rv(c, "plan-review-r1-result.exit") or "").strip() == "0"
      and json.loads(open(c.stub + ".log").readline())["cwd"].endswith("checkout"))

# ---- the other ends of a run ------------------------------------------------

c = seed()
rc = go(c, "run", *PLANS, "--wall-clock", "2", mode="hang")
check("timeout: the wall clock kills the runner, exit 124, skipped with reason timeout",
      rc == 20 and pr_of(c)["reason"] == "timeout" and (rv(c, "plan-review-r1-result.exit") or "").strip() == "124"
      and "wall clock" in (rv(c, "plan-review-r1-result.stderr") or "") and "skipped: timeout" in decisions(c))
check("timeout: the token count is read after a launch that was killed", pr_of(c)["tokens"] == 99)
sh = rv(c, "plan-review-r1-run.sh") or ""
check("the wall clock option is in the script, not 600", "-ge 2 " in sh or "-ge 2]" in sh)

c = seed()
rc = go(c, "run", *PLANS, mode="noverdict")
check("no verdict pair: skipped with reason failed", rc == 20 and pr_of(c)["reason"] == "failed"
      and pr_of(c)["outcome"] == "skipped" and "skipped: failed" in decisions(c))

c = seed()
rc = go(c, "run", *PLANS, mode="quota")
check("quota: a non-zero exit stops with exit 21 and the last 20 stderr lines",
      rc == 21 and "You have hit your usage limit." in c.out and "line 6\n" in c.out and "line 5\n" not in c.out
      and "QUOTA CHECK:" in c.out)
check("quota: no skip record yet, reviewing, exit file present, tokens written",
      pr_of(c)["outcome"] is None and pr_of(c)["status"] == "reviewing" and pr_of(c)["tokens"] == 99
      and (rv(c, "plan-review-r1-result.exit") or "").strip() == "1" and TITLE not in decisions(c))
rc = go(c, "skip", "--reason", "quota", "--evidence", "You have hit your usage limit.")
check("skip --reason quota writes the skip record and the skip decision entry",
      rc == 0 and pr_of(c)["outcome"] == "skipped" and pr_of(c)["reason"] == "quota"
      and "Answer: skipped: quota" in decisions(c) and "Citation: You have hit your usage limit." in decisions(c))
c2 = seed()
rc = go(c2, "skip", "--reason", "bogus", "--evidence", "x")
check("skip refuses a reason that is not quota or failed", rc == 2 and pr_of(c2)["outcome"] is None)
c2 = seed()
go(c2, "run", *PLANS, mode="quota")
go(c2, "skip", "--reason", "failed", "--evidence", "exit 1")
check("skip --reason failed", pr_of(c2)["reason"] == "failed")

c = seed()
shutil.rmtree(c.checkout)
rc = go(c, "run", *PLANS)
check("a failed cd writes exit 1 and takes the judgment stop", rc == 21 and (rv(c, "plan-review-r1-result.exit") or "").strip() == "1")

# ---- decide -----------------------------------------------------------------

c = seed()
go(c, "run", *PLANS)
F = ["Finding: F1 blocking (reviewer: blocking) — sent to ic-one", "Finding: F2 don't post (reviewer: suggestion) — declined: style",
     "Finding: F3 suggestion (reviewer: nit) — sent to ic-two"]
rc = go(c, "decide", "--finding", F[0], "--finding", F[1], "--finding", F[2], "--refactor", "Refactor: Split the module")
o = pr_of(c)
check("decide: outcome ran, labels by the project lead's label, accepted, recommendations",
      rc == 0 and o["outcome"] == "ran" and o["labels"] == {"blocking": 1, "suggestion": 1, "nit": 0, "unsure": 0,
                                                            "don't post": 1, "not real": 0}
      and o["accepted"] == 2 and o["recommendations"] == 1 and o["tokens"] == 1234 and o["status"] == "reviewing")
d = decisions(c)
check("decide: the entry has the title, the answer, the citation and the lines in order",
      "## " + TITLE in d and "Answer: 2 of 3 findings sent to the ICs" in d
      and "Citation: reviews/plan-review-r1.md" in d and "Confidence: high" in d
      and d.find("Finding: F1") < d.find("Finding: F2") < d.find("Finding: F3") < d.find("Refactor: Split the module"))
c = seed()
go(c, "run", *PLANS)
rc = go(c, "decide", "--finding", "Finding: F1 blocking (reviewer: blocking) — sent to x\nbad")
check("decide writes the record before the entry (a failed entry leaves outcome ran)",
      rc != 0 and pr_of(c)["outcome"] == "ran" and "## " + TITLE not in decisions(c))
rc = go(c, "decide", "--finding", "nonsense")
check("decide refuses a line that is no Finding line", rc == 2)

# ---- resume case 3 ----------------------------------------------------------

done = "preface\nPlans reviewed: 2\n\nFindings: 0\nVerdict: plans sound\nBlocking count: 0\n"
reviewing = planning_obj()
reviewing.update(at="2026-01-01T00:00:00Z", attempts=1)
c = seed(status="reviewing", pr=dict(reviewing))
open(os.path.join(c.rec, "reviews", "plan-review-r1-result.txt"), "w").write(done)
open(os.path.join(c.rec, "reviews", "plan-review-r1-result.stderr"), "w").write("tokens used\n77\n")
open(os.path.join(c.rec, "reviews", "plan-review-r1-result.exit"), "w").write("0\n")
rc = go(c, "run", *PLANS)
check("resume: an exit file that is present is read, with no new launch",
      rc == 0 and launches(c) == 0 and (rv(c, "plan-review-r1.md") or "").startswith("Plans reviewed: 2\nSource: codex output\n")
      and pr_of(c)["tokens"] == 77 and pr_of(c)["attempts"] == 1)

c = seed(status="reviewing", pr=dict(reviewing))
for n, t in (("instructions.md", "old\n"), ("result.txt", "partial\n"), ("result.stderr", "err\n")):
    open(os.path.join(c.rec, "reviews", "plan-review-r1-" + n), "w").write(t)
open(os.path.join(c.rec, "reviews", "plan-review-r1.md"), "w").write("half\n")
rc = go(c, "run", *PLANS)
check("resume: no exit file and no live script retires the attempt and reruns once",
      rc == 0 and launches(c) == 1 and pr_of(c)["attempts"] == 2
      and rv(c, "plan-review-r1-instructions-attempt1.md") == "old\n"
      and rv(c, "plan-review-r1-result-attempt1.txt") == "partial\n"
      and rv(c, "plan-review-r1-result-attempt1.stderr") == "err\n" and rv(c, "plan-review-r1-attempt1.md") == "half\n"
      and "CHARTER BODY" in (rv(c, "plan-review-r1-instructions.md") or ""))
two = dict(reviewing, attempts=2)
c = seed(status="reviewing", pr=two)
rc = go(c, "run", *PLANS)
check("resume: a second attempt that died is skipped as failed, with no launch",
      rc == 20 and launches(c) == 0 and pr_of(c)["reason"] == "failed" and pr_of(c)["outcome"] == "skipped"
      and "skipped: failed" in decisions(c))

c = seed(status="reviewing", pr=dict(reviewing))
live = os.path.join(c.rec, "reviews", "plan-review-r1-run.sh")
r = os.path.join(c.rec, "reviews", "plan-review-r1")
open(live, "w").write("sleep 2\ncat > %s-result.txt <<'EOF'\nx\nPlans reviewed: 1\nVerdict: plans sound\nBlocking count: 0\nEOF\n"
                      "echo 0 > %s-result.exit\n" % (r, r))
proc = subprocess.Popen(["sh", live])
t0 = time.time()
rc = go(c, "run", *PLANS)
proc.wait()
check("resume: a live run script is waited for, and no second launch happens",
      rc == 0 and launches(c) == 0 and time.time() - t0 >= 1.0
      and (rv(c, "plan-review-r1.md") or "").startswith("Plans reviewed: 1\nSource: codex output\n"))

# ---- planning, off, started -------------------------------------------------

c = seed()
st = json.load(open(os.path.join(c.rec, "state.json")))
del st["run"]["plan_review"]
json.dump(st, open(os.path.join(c.rec, "state.json"), "w"))
rc = go(c, "planning")
check("planning: the whole object of point 1", rc == 0 and pr_of(c) == planning_obj())
c = seed()
rc = go(c, "off")
o = pr_of(c)
check("off: status started, outcome off, started_at set, the rest initial",
      rc == 0 and o["status"] == "started" and o["outcome"] == "off" and o["started_at"]
      and {k: v for k, v in o.items() if k not in ("status", "outcome", "started_at")}
      == {k: v for k, v in planning_obj().items() if k not in ("status", "outcome", "started_at")})
c = seed(status="reviewing", pr=dict(reviewing, outcome="ran", accepted=2, tokens=5))
rc = go(c, "started")
o = pr_of(c)
check("started: status started and started_at, the rest kept",
      rc == 0 and o["status"] == "started" and o["started_at"] and o["accepted"] == 2 and o["tokens"] == 5
      and o["outcome"] == "ran")
c = seed(status="started")
rc = go(c, "run", *PLANS)
check("run refuses a record whose status is started", rc == 2 and launches(c) == 0)

shutil.rmtree(T, ignore_errors=True)
print("%d of %d checks passed" % (passed, total))
sys.exit(0 if passed == total else 1)

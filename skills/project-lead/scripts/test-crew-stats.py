#!/usr/bin/env python3
"""Seeded test of the plan review and goal check figures of crew-stats.py.

usage: python3 skills/project-lead/scripts/test-crew-stats.py

It builds a temporary record root, runs `crew-stats.py --record-root <tmp>`
with `--json` and without, and checks the numbers. The last line is
`N of M checks passed`. The exit code is 0 only when N equals M.
"""

import json
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SCRIPT = os.path.join(HERE, "crew-stats.py")
PY = sys.executable

T = tempfile.mkdtemp(prefix="crew-stats-test-")
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


def seed(name, run, files=None):
    d = os.path.join(T, name)
    os.makedirs(os.path.join(d, "reviews"))
    run = dict(run, run_state="delivered")
    state = {"run": run, "packages": [{"id": "p1", "band": "standard"}]}
    with open(os.path.join(d, "state.json"), "w") as f:
        json.dump(state, f)
    with open(os.path.join(d, "charter.md"), "w") as f:
        f.write("charter\n")
    for fname, text in (files or {}).items():
        with open(os.path.join(d, "reviews", fname), "w") as f:
            f.write(text)


def report(verdict, counts):
    return ("Plans reviewed: 2\nSource: codex output\n\n### F1. A\nSeverity: blocking\n\n"
            "Findings: %s\nVerdict: %s\nBlocking count: 1\n" % (counts, verdict))


LABELS = {"blocking": 1, "suggestion": 2, "nit": 1, "unsure": 0, "don't post": 1, "not real": 0}
SEED_FILES = {
    "plan-review-r1.md": report("plan revision needed", "1 blocking, 2 suggestion, 1 nit, 0 unsure"),
}
for n in ("plan-review-r1-instructions.md", "plan-review-r1-run.sh", "plan-review-r1-result.txt",
          "plan-review-r1-result.stderr", "plan-review-r1-result.exit", "plan-review-r1-attempt1.md",
          "plan-review-r1-instructions-attempt1.md", "plan-review-r1-result-attempt1.txt",
          "plan-review-r1-result-attempt1.stderr", "plan-review-r1-result-attempt1.exit"):
    SEED_FILES[n] = "x\n"

seed("ran-run", {"plan_review": {"status": "started", "outcome": "ran", "reason": None, "attempts": 1,
                                 "labels": LABELS, "accepted": 3, "recommendations": 2, "tokens": 1000}},
     SEED_FILES)
seed("timeout-run", {"plan_review": {"status": "started", "outcome": "skipped", "reason": "timeout",
                                     "attempts": 1, "labels": {k: 0 for k in LABELS}, "accepted": 0,
                                     "recommendations": 0, "tokens": 500}})
seed("light-run", {"steps_skipped": [{"step": "plan-review"}]})
seed("bad-run", {"plan_review": "broken"})
seed("badlabels-run", {"plan_review": {"outcome": "ran", "labels": "none"}})
seed("sound-run", {}, {"plan-review-r1.md": report("plans sound", "0 blocking, 0 suggestion, 0 nit, 0 unsure")})


def goal_report(verdict, blocking, check=True):
    return ("Reviewed: abc123\n" + ("Check: goal\n" if check else "") +
            "\n### F1. A\nSeverity: blocking\n\nFindings: %d blocking, 0 suggestion, 0 nit, 0 unsure\n"
            "Verdict: %s\nBlocking count: %d\n" % (blocking, verdict, blocking))


# The goal checks (goal-check.md): a miss the project lead kept, a miss the
# project lead relabelled to accepted, and an older skeptical report with no
# `Check: goal` line, which is no goal check.
seed("goal-miss-run", {}, {"skeptical-r1.md": goal_report("patch round needed", 2),
                           "skeptical-r1-reply.md": "ledger\n\nVerdict after labels: patch round needed\n"})
seed("goal-relabel-run", {}, {"skeptical-r1.md": goal_report("patch round needed", 1),
                              "skeptical-r1-reply.md": "ledger\n\nVerdict after labels: accepted\n"})
seed("old-skeptical-run", {}, {"skeptical-r1.md": goal_report("patch round needed", 1, check=False)})


def run(args):
    return subprocess.run([PY, SCRIPT, "--record-root", T] + args, capture_output=True, text=True)


def main():
    try:
        r = run(["--json"])
        check("the run exits 0 with unreadable plan_review values", r.returncode == 0)
        data = json.loads(r.stdout)
        pr = data.get("plan_reviews", {})
        recs = {x["run"]: x for x in data["records"]}
        check("plan_reviews has exactly the contract keys",
              sorted(pr) == ["accepted", "labels", "outcomes", "recommendations", "skips_by_reason", "tokens"])
        check("outcomes are ran 1, skipped 1, off 0", pr.get("outcomes") == {"ran": 1, "skipped": 1, "off": 0})
        check("skips by reason is timeout 1", pr.get("skips_by_reason") == {"timeout": 1})
        check("labels sum the seeded counts", pr.get("labels") == LABELS)
        check("accepted is 3", pr.get("accepted") == 3)
        check("recommendations is 2", pr.get("recommendations") == 2)
        check("tokens sum is 1500", pr.get("tokens") == 1500)
        check("the light-path record counts nowhere in plan_reviews", recs["light-run"].get("plan_review") is None)
        check("the plan review count is 1 for the ran record", recs["ran-run"]["reviews"]["plan review"] == 1)
        check("companion and retired files are not counted as reviews",
              recs["ran-run"]["reviews"]["other"] == 0 and sum(recs["ran-run"]["reviews"].values()) == 1)
        check("proposed labels of the plan review come from its Findings line",
              recs["ran-run"]["labels"]["plan review"] == {"blocking": 1, "suggestion": 2, "nit": 1, "unsure": 0})
        check("plan revision needed is the action verdict",
              recs["ran-run"]["catch"]["plan review"] == {"reviews": 1, "acted": 1, "unverdicted": 0})
        check("plans sound is a known verdict and no catch",
              recs["sound-run"]["catch"]["plan review"] == {"reviews": 1, "acted": 0, "unverdicted": 0})
        check("steps skipped counts plan-review for the light record",
              recs["light-run"]["steps_skipped"]["plan-review"] == 1)
        skipped = " ".join(data["skipped"])
        check("an unreadable plan_review gives a skip line", "bad-run" in skipped and "plan_review" in skipped)
        check("a labels value that is not an object gives a skip line",
              "badlabels-run" in skipped and "plan_review" in skipped)
        check("the unreadable records count nowhere",
              recs["bad-run"].get("plan_review") is None and recs["badlabels-run"].get("plan_review") is None)
        check("a kept goal miss counts as run, missed, and its report's blocking count",
              recs["goal-miss-run"]["goal_checks"] == {"run": 1, "missed": 1, "misses": 2, "accepted": 0})
        check("the reply file's verdict after labels wins over the report's verdict",
              recs["goal-relabel-run"]["goal_checks"] == {"run": 1, "missed": 0, "misses": 0, "accepted": 1})
        check("a skeptical report with no Check: goal line is no goal check",
              recs["old-skeptical-run"]["goal_checks"] == {"run": 0, "missed": 0, "misses": 0, "accepted": 0})
        t = run([])
        out = t.stdout
        check("the text report has a Goal checks table with the reviewer's count row",
              "Goal checks" in out and "blocking findings in those reports" in out)
        check("the text report exits 0", t.returncode == 0)
        check("the text report has a Plan reviews section", "Plan reviews" in out)
        check("the text report lists plan-review under steps skipped",
              "plan-review" in out.split("Steps skipped by rule")[-1])
        check("the text report lists the plan review kind", "plan review" in out)
    except Exception as e:  # a crash counts as one failed check
        check("crashed: %r" % (e,), False)
    finally:
        shutil.rmtree(T, ignore_errors=True)
    print("%d of %d checks passed" % (passed, total))
    return 0 if passed == total else 1


if __name__ == "__main__":
    sys.exit(main())

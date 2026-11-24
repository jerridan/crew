#!/usr/bin/env python3
"""Run the plan review, and write its record.

usage:
  plan-review.py <record-dir> run --plan <id>:<territory>:<k>/<m> [--plan ...]
  plan-review.py <record-dir> skip --reason quota|failed --evidence "<text>"
  plan-review.py <record-dir> decide --finding "<line>" [--finding ...] [--refactor "<line>" ...]
  plan-review.py <record-dir> planning
  plan-review.py <record-dir> off
  plan-review.py <record-dir> started

`skills/project-lead/references/plan-review.md` owns how the project lead uses
this script and what it does on each output prefix and exit status.

`run` does the two skip checks, builds the instructions file from files, writes
`status: reviewing` just before the launch, runs the Codex runner under a wall
clock, reads the exit, the verdict pair and the token count, transcribes the
report, and writes the skip record of a skip it decides itself. `--plan` is
given once for each package, in the order the reviewer reads the plans. A plan
whose file is absent goes in the `Missing plans:` line. It reads the checkout
from `run.checkout`. With `status: reviewing` in the record it follows the
resume of "Resume in the planning step", case 3.

`decide` writes `outcome: ran`, the label counts, `accepted` and
`recommendations`, and then the `decisions.md` entry. Each `--finding` line has
the form `Finding: F<k> <label> (reviewer: <label>) — sent to <ic> | declined:
<reason>`. Each `--refactor` line starts `Refactor:`. `skip` writes the skip
record and the skip entry for a `quota` or `failed` skip that the project lead
judged. `planning`, `off` and `started` write points 1 and 5 of "The record",
and `Plan review: off`, each as the whole object.

Exit status, and the line that starts the output:
  0   `PLAN REVIEW RAN:`  the report is `reviews/plan-review-r1.md`. The
                          `skip` command also exits 0
  20  `SKIPPED:`          `run` wrote the skip record and the entry
  21  `QUOTA CHECK:`      the runner exited non-zero: read the stderr lines,
                          then run `skip --reason quota|failed`
  2   usage error or a record that is in the wrong state
  14  `RECORD ERROR:`     a `crew-record.py` call failed

Test options: `--wall-clock <seconds>` replaces the 600-second limit, and
`--poll <seconds>` replaces the 10-second poll of the run script and the wait
for a live script.
"""

from __future__ import annotations

import argparse
import datetime
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFS = HERE.parent / "references"
RUBRIC = HERE.parent.parent / "review" / "references" / "severity-rubric.md"
RECORD = HERE / "crew-record.py"
TITLE = "Plan review: which findings does the run act on?"
LABELS = ("blocking", "suggestion", "nit", "unsure", "don't post", "not real")
RETIRE = [("plan-review-r1.md", "plan-review-r1-attempt1.md"),
          ("plan-review-r1-instructions.md", "plan-review-r1-instructions-attempt1.md"),
          ("plan-review-r1-result.txt", "plan-review-r1-result-attempt1.txt"),
          ("plan-review-r1-result.stderr", "plan-review-r1-result-attempt1.stderr"),
          ("plan-review-r1-result.exit", "plan-review-r1-result-attempt1.exit")]
VERDICT = re.compile(r"^Verdict: (plans sound|plan revision needed)$")
COUNT = re.compile(r"^Blocking count: \d+$")


class Stop(Exception):
    def __init__(self, code, lines):
        self.code = code
        self.lines = lines


def say(text):
    print(text, flush=True)


def now():
    return datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def one_line(text, limit=600):
    return " ".join(str(text).split())[:limit]


def read_text(path):
    try:
        return Path(path).read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return None


def initial():
    return {"status": "planning", "outcome": None, "reason": None, "at": None, "started_at": None, "attempts": 0,
            "labels": {k: 0 for k in LABELS}, "accepted": 0, "recommendations": 0, "tokens": None}


class Review:
    def __init__(self, args):
        self.args = args
        self.rec = Path(os.path.abspath(args.record_dir))
        self.reviews = self.rec / "reviews"
        self.r = self.reviews / "plan-review-r1"

    def f(self, suffix):
        return Path(str(self.r) + suffix)

    def state(self):
        return json.loads((self.rec / "state.json").read_text(encoding="utf-8"))

    def obj(self):
        o = self.state().get("run", {}).get("plan_review")
        return dict(o) if isinstance(o, dict) else None

    def crew(self, *argv):
        r = subprocess.run([sys.executable, str(RECORD), str(self.rec), *argv], capture_output=True, text=True)
        if r.returncode != 0:
            raise Stop(14, ["RECORD ERROR: crew-record.py %s failed: %s" % (" ".join(argv[:3]),
                                                                           one_line(r.stderr or r.stdout))])

    def write(self, obj):
        self.crew("run", "set", "plan_review", json.dumps(obj))

    def decision(self, answer, citation, lines=()):
        argv = ["decision", "precedent", TITLE, "--answer", one_line(answer), "--citation", one_line(citation),
                "--confidence", "high"]
        for line in lines:
            argv += ["--line", line]
        self.crew(*argv)


def need_status(rv, allowed):
    o = rv.obj()
    if o is None:
        raise Stop(2, ["run.plan_review is absent. Run `planning` first."])
    if o.get("status") not in allowed:
        raise Stop(2, ["run.plan_review.status is %s, and this command needs %s." % (o.get("status"), " or ".join(allowed))])
    return o


def skip(rv, reason, evidence, o=None, code=20):
    o = o or rv.obj()
    o.update(outcome="skipped", reason=reason)
    rv.write(o)
    rv.decision("skipped: %s" % reason, evidence)
    raise Stop(code, ["SKIPPED: %s. Evidence: %s. The record and the decisions.md entry are written. Add the hand-over "
                    "line, then give the start word with no findings." % (reason, one_line(evidence, 300)),
                    "status: SKIPPED"])


def timeout_tool():
    for name in ("timeout", "gtimeout"):
        if shutil.which(name):
            return name
    return None


def skip_checks(rv, o):
    if not shutil.which("codex"):
        skip(rv, "absent", "command -v codex printed nothing", o)
    tool = timeout_tool()
    cmd = ["codex", "login", "status"]
    if tool:
        cmd = [tool, "15"] + cmd
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        code, text = r.returncode, r.stderr or r.stdout
    except OSError as e:
        code, text = 1, str(e)
    if code != 0:
        skip(rv, "not logged in", "`%s` exited %d: %s" % (" ".join(cmd), code, one_line(text, 200)), o)


def standing_text(rv):
    si = rv.state().get("run", {}).get("standing_instructions") or {}
    out = []
    for key in ("repo", "machine"):
        path = si.get(key)
        text = read_text(os.path.expanduser(path)) if path else None
        if text:
            out.append(text)
    return out


def build_instructions(rv):
    def blk(path, attrs):
        ident = secrets.token_hex(8)
        text = read_text(path) or ""
        return "<data-%s %s>\n%s%s\n</data-%s>\n\n" % (ident, attrs, text, "" if text.endswith("\n") else "\n", ident)

    parts = [read_text(REFS / "plan-reviewer.md"), read_text(REFS / "review-output.md"), read_text(RUBRIC)]
    parts += standing_text(rv)
    out = "".join(x if x.endswith("\n") else x + "\n" for x in parts) + "\n"
    for name in ("charter", "spec", "split"):
        out += blk(rv.rec / (name + ".md"), 'source="%s.md"' % name)
    missing = []
    for spec in rv.args.plan:
        pid, territory, order = (spec.split(":") + ["", ""])[:3]
        k, _, m = order.partition("/")
        path = rv.rec / "plans" / (pid + ".md")
        if not path.exists():
            missing.append(pid)
            continue
        out += blk(path, 'source="plans/%s.md" package="%s" territory="%s" order="%s of %s"' % (pid, pid, territory, k, m))
    if missing:
        out += "Missing plans: %s.\n" % ", ".join(missing)
    rv.reviews.mkdir(parents=True, exist_ok=True)
    rv.f("-instructions.md").write_text(out, encoding="utf-8")


def write_script(rv, checkout):
    wall, poll = rv.args.wall_clock, rv.args.poll
    text = f'''r={rv.r}
: > "$r-result.txt"; : > "$r-result.stderr"; rm -f "$r-result.exit"
cd {checkout} || {{ echo 1 > "$r-result.exit"; exit 1; }}
codex exec --sandbox read-only -m gpt-6.2-sol -c model_reasoning_effort=medium -C {checkout} - < "$r-instructions.md" > "$r-result.txt" 2> "$r-result.stderr" &
pid=$!
start=$(date +%s)
while kill -0 "$pid" 2>/dev/null; do
  sleep {poll}
  if [ $(( $(date +%s) - start )) -ge {wall} ]; then
    pkill -P "$pid"; kill "$pid"; sleep 5; kill -9 "$pid" 2>/dev/null
    echo "wall clock: not done {wall} seconds after launch" >> "$r-result.stderr"
    echo 124 > "$r-result.exit"
    exit 124
  fi
done
wait "$pid"
echo $? > "$r-result.exit"
'''
    rv.f("-run.sh").write_text(text, encoding="utf-8")


def launch(rv, o, checkout):
    build_instructions(rv)
    write_script(rv, checkout)
    o.update(status="reviewing", at=now(), attempts=int(o.get("attempts") or 0) + 1)
    rv.write(o)
    subprocess.run(["sh", str(rv.f("-run.sh"))], stdout=subprocess.DEVNULL)


def token_count(rv):
    value = None
    lines = (read_text(rv.f("-result.stderr")) or "").split("\n")
    for i, line in enumerate(lines):
        if line == "tokens used":
            value = lines[i + 1] if i + 1 < len(lines) else ""
    digits = re.sub(r"[^0-9]", "", value or "")
    return int(digits) if digits else None


def live(rv):
    r = subprocess.run(["pgrep", "-f", str(rv.f("-run.sh"))], capture_output=True, text=True)
    return r.returncode == 0 and bool(r.stdout.strip())


def wait_for_exit(rv):
    # A live script ends itself at the wall clock, so the wait has a bound.
    end = time.time() + rv.args.wall_clock + 60
    while time.time() < end and not rv.f("-result.exit").exists() and live(rv):
        time.sleep(rv.args.poll)


def retire(rv):
    for old, new in RETIRE:
        src = rv.reviews / old
        if src.exists():
            src.rename(rv.reviews / new)


def pair_at_end(text):
    lines = [x for x in text.rstrip().split("\n") if x.strip()]
    return len(lines) >= 2 and bool(VERDICT.match(lines[-2].strip())) and bool(COUNT.match(lines[-1].strip()))


def cmd_run(rv):
    if not rv.args.plan:
        raise Stop(2, ["run needs --plan <id>:<territory>:<k>/<m> for each package"])
    o = need_status(rv, ("planning", "reviewing"))
    checkout = rv.state().get("run", {}).get("checkout")
    if not checkout:
        raise Stop(2, ["run.checkout is absent in the record"])
    launched = False
    if o["status"] == "planning":
        skip_checks(rv, o)
        launch(rv, o, checkout)
        launched = True
    else:
        if not rv.f("-result.exit").exists():
            if live(rv):
                say("wait: plan-review-r1-run.sh still runs, so the script waits for its exit file")
                wait_for_exit(rv)
            if not rv.f("-result.exit").exists() and not live(rv):
                if int(o.get("attempts") or 0) >= 2:
                    skip(rv, "failed", "a second attempt of the run script died with the session", o)
                retire(rv)
                say("retry: the run script died with the session. The attempt is retired and the review runs once more.")
                skip_checks(rv, o)
                launch(rv, o, checkout)
                launched = True
            elif not rv.f("-result.exit").exists():
                skip(rv, "timeout", "the live run script left no exit file", o)
    code_text = read_text(rv.f("-result.exit")) or ""
    code = int(code_text.strip()) if code_text.strip().lstrip("-").isdigit() else None
    o = rv.obj()
    o["tokens"] = token_count(rv)
    if code == 124:
        skip(rv, "timeout", "result.exit holds 124: not done at the wall clock", o)
    if code != 0:
        rv.write(o)
        tail = (read_text(rv.f("-result.stderr")) or "").rstrip("\n").split("\n")[-20:]
        raise Stop(21, ["QUOTA CHECK: the runner exited %s. Read the last 20 lines of the stderr. When they name a "
                        "usage limit or a rate limit, run `skip --reason quota`. Otherwise run `skip --reason failed`."
                        % code] + tail + ["status: QUOTA-CHECK"])
    result = read_text(rv.f("-result.txt")) or ""
    if not pair_at_end(result):
        skip(rv, "failed", "result.txt ends with no Verdict and Blocking count pair", o)
    lines = result.split("\n")
    start = next((i for i, x in enumerate(lines) if re.match(r"Plans reviewed: ", x)), None)
    note = []
    if start is None:
        note.append("notice: result.txt has no `Plans reviewed:` line, so the whole text is the report")
        start = 0
        lines = ["Plans reviewed: unknown"] + lines
        start = 0
    report = [lines[start], "Source: codex output"] + lines[start + 1:]
    rv.f(".md").write_text("\n".join(report), encoding="utf-8")
    rv.write(o)
    raise Stop(0, note + ["PLAN REVIEW RAN: read %s, label every finding, then run `decide`. tokens: %s" % (
        rv.f(".md"), o["tokens"]), "status: RAN"])


def cmd_skip(rv):
    if rv.args.reason not in ("quota", "failed"):
        raise Stop(2, ["skip needs --reason quota or --reason failed"])
    if not rv.args.evidence:
        raise Stop(2, ["skip needs --evidence"])
    o = need_status(rv, ("planning", "reviewing"))
    skip(rv, rv.args.reason, rv.args.evidence, o, code=0)


def cmd_decide(rv):
    findings = rv.args.finding or []
    refactors = rv.args.refactor or []
    counts = {k: 0 for k in LABELS}
    accepted = 0
    for line in findings:
        m = re.match(r"^Finding: F\d+ (.+?) \(reviewer: [^)]*\)", line)
        if not m or m.group(1) not in counts:
            raise Stop(2, ["a --finding line must read `Finding: F<k> <label> (reviewer: <label>) — ...` with a "
                           "label of %s: %s" % (", ".join(LABELS), line[:80])])
        counts[m.group(1)] += 1
        if "sent to" in line.split("—", 1)[-1] and "declined:" not in line.split("—", 1)[-1]:
            accepted += 1
    for line in refactors:
        if not line.startswith("Refactor:"):
            raise Stop(2, ["a --refactor line must start `Refactor:`: %s" % line[:80]])
    o = need_status(rv, ("reviewing",))
    o.update(outcome="ran", labels=counts, accepted=accepted, recommendations=len(refactors))
    rv.write(o)
    rv.decision("%d of %d findings sent to the ICs" % (accepted, len(findings)), "reviews/plan-review-r1.md",
                list(findings) + list(refactors))
    raise Stop(0, ["ok: the record and the decisions.md entry are written. Send the start words."])


def cmd_simple(rv, name):
    if name == "planning":
        rv.write(initial())
    elif name == "off":
        o = initial()
        o.update(status="started", outcome="off", started_at=now())
        rv.write(o)
    else:
        o = rv.obj()
        if o is None:
            raise Stop(2, ["run.plan_review is absent. Run `planning` or `off` first."])
        o.update(status="started", started_at=now())
        rv.write(o)
    raise Stop(0, ["ok"])


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("record_dir")
    ap.add_argument("command", choices=["run", "skip", "decide", "planning", "off", "started"])
    ap.add_argument("--plan", action="append")
    ap.add_argument("--reason")
    ap.add_argument("--evidence")
    ap.add_argument("--finding", action="append")
    ap.add_argument("--refactor", action="append")
    ap.add_argument("--wall-clock", type=int, default=600)
    ap.add_argument("--poll", type=int, default=10)
    args = ap.parse_args(argv)
    rv = Review(args)
    try:
        {"run": cmd_run, "skip": cmd_skip, "decide": cmd_decide}.get(args.command, lambda r: cmd_simple(r, args.command))(rv)
    except Stop as stop:
        for line in stop.lines:
            say(line)
        sys.exit(stop.code)


if __name__ == "__main__":
    main(sys.argv[1:])

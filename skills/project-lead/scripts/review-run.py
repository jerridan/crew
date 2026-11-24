#!/usr/bin/env python3
"""Run one round of the headless review, from the startup check to the
recorded result, in one call.

usage:
  review-run.py <record-dir> [--setup "<setup command>"] [--reviewer-paragraph <file>]
  review-run.py <record-dir> record --denials-ok true|false [same options]
  review-run.py <record-dir> --replacement <runner name> [--setup ...] [--reviewer-paragraph <file>]

`skills/project-lead/references/review-runner.md` owns how the project lead
uses this script and what it does on each output prefix and exit status. The
steps, in order: refuse a substituted round, look for a saved attempt, find
the timeout tool, run the startup check, set `review_rounds`, cut or move the
review worktree, on a goal run run the setup command and check the baseline,
resolve the round's resume and base, write the instructions file, record the
session id, write and run `reviews/skeptical-r<n>-run.sh`, run the four
checks, and write `run.review_results[<n>]`. A failed check retires the
attempt and runs the round once more in the same call.

`--allow-extra "<rule>"` adds one read-only rule to the allow list, and may
repeat. `--replacement` builds the files of a round that a replacement runner
reviews and stops: no startup check, no session id, no launch. It exits 0 with
`status: BUILT`.

The reviewer blocks are files in `references/reviewer-blocks/`. This script
reads them at run time and keeps no copy.

Exit status, and the line that starts the output:
  0   PASSED
  10  `ESCALATE:`        the startup check failed four times, the review
                         worktree path belongs to another run, or the round
                         failed twice
  11  `BASELINE OWED:`   `reviews/baseline.md` is missing or names another base
  12  `CANNOT VERIFY:`   the report holds a `Cannot verify` line: judge it,
                         then run `record`
  13  `REFUSED:`         no pending review, or the principal named a
                         replacement for this step
  14  `RECORD ERROR:`    a `crew-record.py` call failed

The last lines are the summary: `round`, `report`, `exit`, `denials_ok`,
`report_ok`, `denied`, each `fallback:` and `retry:` taken, and `status`.

Test option: `--startup-interval <seconds>` replaces the one-minute wait
between startup check retries.
"""

from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import shlex
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFS = HERE.parent / "references"
BLOCKS = REFS / "reviewer-blocks"
RUBRIC = HERE.parent.parent / "review" / "references" / "severity-rubric.md"
RECORD = HERE / "crew-record.py"

OK, ESCALATE, OWED, CANNOT, REFUSED, ERROR = 0, 10, 11, 12, 13, 14
STATUS = {OK: "PASSED", ESCALATE: "ESCALATE", OWED: "BASELINE-OWED", CANNOT: "CANNOT-VERIFY",
          REFUSED: "REFUSED", ERROR: "RECORD-ERROR"}

PROMPT = ("Review the finished change on this detached head, following every instruction in your system prompt. "
          "Write your report to the absolute path your instructions name.")
ALLOW = ("Read,Glob,Grep,Bash(git diff *),Bash(git log *),Bash(git show *),Bash(git rev-parse *),"
         "Bash(npm view *),Bash(npm ls *),Bash(pnpm ls *),Bash(pnpm why *),Bash(yarn why *),Bash(pip show *),"
         "Edit(//%s/reviews/**)")
MODEL = {"goal": ("sonnet", 900), "review": ("opus", 2700)}
VERDICT = re.compile(r"^Verdict: (accepted|patch round needed)$")
COUNT = re.compile(r"^Blocking count: \d+$")
RETIRE = [("skeptical-r{n}.md", "skeptical-r{n}-attempt{k}.md"),
          ("skeptical-r{n}-instructions.md", "skeptical-r{n}-instructions-attempt{k}.md"),
          ("skeptical-r{n}-resume.md", "skeptical-r{n}-resume-attempt{k}.md"),
          ("skeptical-r{n}-result.json", "skeptical-r{n}-result-attempt{k}.json"),
          ("skeptical-r{n}-result.stderr", "skeptical-r{n}-result-attempt{k}.stderr"),
          ("skeptical-r{n}-result.exit", "skeptical-r{n}-result-attempt{k}.exit")]


class Stop(Exception):
    def __init__(self, code, lines, word=None):
        self.code = code
        self.lines = lines
        self.word = word


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


def fill(text, mapping):
    for key, value in mapping.items():
        text = text.replace(key, value)
    return text


def pair_at_end(text):
    lines = [x for x in text.rstrip().split("\n") if x.strip()]
    return len(lines) >= 2 and bool(VERDICT.match(lines[-2].strip())) and bool(COUNT.match(lines[-1].strip()))


class Round:
    """One call's context: the record, the options and the summary."""

    def __init__(self, args):
        self.args = args
        self.rec = Path(os.path.abspath(args.record_dir))
        self.reviews = self.rec / "reviews"
        self.events = []
        self.summary = {}
        self.tool = None
        self.cut = False
        self.noprompt = False
        self.prev_head = None
        self.plan = {}

    def load(self):
        return json.loads((self.rec / "state.json").read_text(encoding="utf-8"))

    @property
    def run(self):
        return self.load().get("run", {})

    def deliverable(self):
        return self.load()["deliverables"][0]

    def p(self, suffix, n=None):
        return self.reviews / ("skeptical-r%d%s" % (n or self.n, suffix))

    def crew(self, *argv):
        r = subprocess.run([sys.executable, str(RECORD), str(self.rec), *argv], capture_output=True, text=True)
        if r.returncode != 0:
            raise Stop(ERROR, ["RECORD ERROR: crew-record.py %s failed: %s" % (" ".join(argv[:3]),
                                                                              one_line(r.stderr or r.stdout))])

    def run_set(self, field, value):
        self.crew("run", "set", field, json.dumps(value))

    def decision(self, title, answer, citation, lines=()):
        argv = ["decision", "precedent", one_line(title), "--answer", one_line(answer), "--citation", one_line(citation),
                "--confidence", "high"]
        for line in lines:
            argv += ["--line", one_line(line)]
        self.crew(*argv)

    def event(self, kind, text):
        line = "%s: %s" % (kind, text)
        self.events.append(line)
        say(line)


def git(*args, cwd=None):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True)


# ---- the refusals and the basics -------------------------------------------

def basics(ctx):
    state = ctx.load()
    run = state.get("run", {})
    ctx.review = run.get("kind") == "review"
    ctx.runner = ctx.args.replacement or "claude"
    step = "skeptical-review" if ctx.review else "goal-check"
    for entry in [] if ctx.args.replacement else run.get("substitutions_requested") or []:
        if isinstance(entry, dict) and entry.get("step") == step:
            raise Stop(REFUSED, ["REFUSED: the principal named a replacement for the %s. This script runs the default "
                                 "runner only. Run the replacement as substitution.md says." % step])
    pending = run.get("review_pending")
    if not isinstance(pending, dict) or not pending.get("head") or not pending.get("round"):
        raise Stop(REFUSED, ["REFUSED: run.review_pending is null. No review is owed. Arm a head first."])
    ctx.n = int(pending["round"])
    ctx.head = pending["head"]
    ctx.summary["round"] = ctx.n
    ctx.summary["report"] = str(ctx.p(".md"))
    ctx.repo = run["repo"]
    ctx.did = state["deliverables"][0]["id"]
    if ctx.review:
        ctx.wt = Path(run["checkout"])
    else:
        ctx.wt = Path(run.get("worktree_base") or ctx.rec) / "review-worktrees" / ctx.did
    ctx.model, ctx.cap = MODEL["review" if ctx.review else "goal"]
    ctx.reviews.mkdir(parents=True, exist_ok=True)


# ---- steps 1 and 2: the timeout tool and the startup check ------------------

def find_timeout(ctx):
    for name in ("timeout", "gtimeout"):
        if shutil.which(name):
            ctx.tool = name
            return
    ctx.tool = None
    ctx.event("fallback", "GNU timeout is not installed, so this round runs with no cap.")


def startup_check(ctx):
    cmd = ["claude", "--version"]
    if ctx.tool:
        cmd = [ctx.tool, "15"] + cmd
    fault = ""
    for attempt in range(4):
        try:
            r = subprocess.run(cmd, capture_output=True, text=True)
            fault = "exit %d: %s" % (r.returncode, one_line(r.stderr or r.stdout)) if r.returncode else ""
        except OSError as e:
            fault = str(e)
        if not fault:
            return
        if attempt < 3:
            ctx.event("retry", "startup check fault (%s), attempt %d of 4" % (fault, attempt + 1))
            time.sleep(ctx.args.startup_interval)
    raise Stop(ESCALATE, ["ESCALATE: the startup check `%s` failed four times, three retries at %s seconds: %s. "
                          "No round launched, so nothing was recorded." % (" ".join(cmd), ctx.args.startup_interval,
                                                                            fault)])


# ---- step 3: the round table ------------------------------------------------

def round_table(ctx):
    rounds = ctx.run.get("review_rounds")
    rounds = rounds if isinstance(rounds, int) and not isinstance(rounds, bool) else 0
    ctx.rounds_before = rounds
    if rounds < ctx.n:
        ctx.run_set("review_rounds", ctx.n)


# ---- step 4: the worktree ---------------------------------------------------

def listed(ctx):
    r = git("-C", ctx.repo, "worktree", "list", "--porcelain")
    want = os.path.realpath(ctx.wt)
    return any(line.startswith("worktree ") and os.path.realpath(line[9:].strip()) == want
               for line in r.stdout.splitlines())


def prepare_worktree(ctx):
    run = ctx.run
    wt = ctx.wt
    owned = (not ctx.review) or ctx.rounds_before >= 1
    ctx.cut = False
    pr = run.get("pr") or {}
    git("-C", ctx.repo, "worktree", "prune")
    if ctx.review:
        argv = ["fetch", "origin", pr.get("base_ref") or "main"]
        if pr.get("cross_repository"):
            argv2 = ["fetch", "origin", "pull/%s/head" % pr.get("number")]
            if git("-C", ctx.repo, *argv2).returncode:
                ctx.event("notice", "fetch of pull/%s/head failed" % pr.get("number"))
        else:
            argv += [pr["head_ref"]] if pr.get("head_ref") else []
        if git("-C", ctx.repo, *argv).returncode:
            ctx.event("notice", "`git fetch origin` failed: the commits may be missing locally")
    exists = wt.exists()
    if exists and git("-C", str(wt), "rev-parse", "--git-dir").returncode != 0:
        if not owned:
            raise Stop(ESCALATE, ["ESCALATE: %s exists and is no git tree, and this record did not cut it. Another run "
                                  "may hold it. Nothing was removed." % wt])
        git("-C", ctx.repo, "worktree", "remove", "--force", str(wt))
        shutil.rmtree(wt, ignore_errors=True)
        git("-C", ctx.repo, "worktree", "prune")
        ctx.event("fallback", "the worktree path was broken, so it was removed and is cut again: %s" % wt)
        exists = False
    if ctx.review and not owned and listed(ctx):
        raise Stop(ESCALATE, ["ESCALATE: `git worktree list` already lists %s, and this record did not cut it. "
                              "Another run reviews this PR in this checkout. Nothing was cut or removed." % wt])
    if exists:
        r = git("-C", str(wt), "switch", "--detach", "--discard-changes", ctx.head)
        if r.returncode:
            raise Stop(ESCALATE, ["ESCALATE: the review worktree could not move to %s: %s" % (ctx.head,
                                                                                               one_line(r.stderr))])
        return
    if str(wt).startswith(os.path.join(ctx.repo, ".claude", "worktrees") + os.sep):
        if git("-C", ctx.repo, "check-ignore", "-q", ".claude/worktrees/").returncode != 0:
            ctx.event("notice", ".claude/worktrees/ is not ignored in %s. Tell the principal once." % ctx.repo)
    wt.parent.mkdir(parents=True, exist_ok=True)
    r = git("-C", ctx.repo, "worktree", "add", "--detach", str(wt), ctx.head)
    if r.returncode:
        raise Stop(ESCALATE, ["ESCALATE: the review worktree could not be cut at %s: %s" % (ctx.head,
                                                                                            one_line(r.stderr))])
    ctx.cut = True


# ---- step 5: setup and baseline (a goal run) --------------------------------

def baseline_owed(ctx):
    """The reason the baseline is owed, or None when baseline.md names the base."""
    base = ctx.deliverable().get("base")
    text = read_text(ctx.reviews / "baseline.md")
    first = (text or "").split("\n", 1)[0].strip()
    if not text:
        return "missing"
    return None if first == "Base: %s" % base else "measured at another base (%s)" % first


def setup_and_baseline(ctx):
    base = ctx.deliverable().get("base")
    baseline = ctx.reviews / "baseline.md"
    marker = ctx.reviews / ("skeptical-r%d-setup-done" % ctx.n)
    if ctx.args.setup and (ctx.cut or not marker.exists()):
        r = subprocess.run(ctx.args.setup, shell=True, cwd=str(ctx.wt), capture_output=True, text=True)
        marker.write_text(now() + "\n", encoding="utf-8")
        if r.returncode:
            owed = baseline_owed(ctx)
            ctx.event("fallback", "the setup command failed with exit %d%s" % (
                r.returncode, ", so the baseline is the no-suite outcome" if owed else ", and the current baseline stays"))
            ctx.decision("Review worktree setup failed", "environment failure, not a finding: no suite",
                         "setup command `%s` exited %d: %s" % (ctx.args.setup, r.returncode,
                                                                one_line(r.stderr or r.stdout, 300)))
            if owed:
                baseline.write_text("Base: %s\nNo suite.\n" % base, encoding="utf-8")
    owed = baseline_owed(ctx)
    if owed:
        raise Stop(OWED, ["BASELINE OWED: reviews/baseline.md is %s. Write it as skeptical-review.md step 4 says, "
                          "then run this script again with the same options." % owed])


# ---- steps 6 and 7: the round, its resume and its base ----------------------

def prev_head_of(ctx):
    text = read_text(ctx.p(".md", ctx.n - 1))
    m = re.match(r"Reviewed: (\S+)", text or "")
    return m.group(1) if m else None


def resolve_round(ctx, force=None):
    run = ctx.run
    base = ctx.deliverable().get("base")
    plan = {"resume": False, "fresh_reason": None, "base": base, "prev_head": None, "ancestor": False,
            "session": None}
    if ctx.review and ctx.n > 1:
        prev_round = "skeptical-r%d" % (ctx.n - 1)
        prev_head = prev_head_of(ctx)
        entry = (run.get("review_sessions") or {}).get(prev_round)
        wt = str(ctx.wt)
        ancestor = bool(prev_head) and git("-C", wt, "merge-base", "--is-ancestor", prev_head, ctx.head).returncode == 0
        reasons = []
        if not isinstance(entry, dict):
            reasons.append("no session recorded for %s" % prev_round)
        elif entry.get("runner") != ctx.runner:
            reasons.append("the runner of %s is %s, not %s" % (prev_round, entry.get("runner"), ctx.runner))
        if not ancestor:
            reasons.append("previous head %s is not an ancestor of the pending head" % prev_head)
        if glob.glob(str(ctx.reviews / ("skeptical-r%d-resume-attempt*.md" % ctx.n))):
            reasons.append("a resume attempt of this round was retired")
        if force:
            reasons = [force]
        resume = not reasons
        pr = run.get("pr") or {}
        mb = git("-C", wt, "merge-base", ctx.head, "origin/%s" % pr.get("base_ref")).stdout.strip()
        new_base = prev_head if (resume and mb == base) else (mb or base)
        plan.update(resume=resume, fresh_reason="; ".join(reasons) or None, prev_head=prev_head, ancestor=ancestor,
                    session=entry if resume else None, base=new_base)
        if new_base != base:
            ctx.crew("deliverable", ctx.did, "set", "base", json.dumps(new_base))
    ctx.plan = plan
    return plan


def goal_text(ctx):
    charter = read_text(ctx.rec / "charter.md") or ""
    if not ctx.review:
        return charter.strip("\n")
    lines = charter.split("\n")
    start = next((i for i, x in enumerate(lines) if x.startswith("## The author's text")), None)
    if start is None:
        return charter.strip("\n")
    body = lines[start + 1:]
    keys = ("Base:", "Assist:", "Gate:", "Rounds:", "Re-review:", "PR:")
    end = len(body)
    while end > 0 and (not body[end - 1].strip() or body[end - 1].startswith(keys)):
        end -= 1
    return "\n".join(body[:end]).strip("\n")


def standing_text(ctx):
    si = ctx.run.get("standing_instructions") or {}
    out = []
    repo = si.get("repo")
    if repo:
        if ctx.review and ":" in str(repo) and not str(repo).startswith("/"):
            r = git("-C", ctx.repo, "show", repo)
            text = r.stdout if r.returncode == 0 else None
        else:
            text = read_text(os.path.expanduser(repo))
        if text:
            out.append(text)
    machine = si.get("machine")
    if machine:
        text = read_text(os.path.expanduser(machine))
        if text:
            out.append(text)
    return out


def later_block(ctx):
    plan = ctx.plan
    n = ctx.n
    prev_round = "skeptical-r%d" % (n - 1)
    mapping = {"<previous head sha>": plan["prev_head"] or "unknown", "<base>": plan["base"]}
    reading = fill((BLOCKS / ("reading-delta.md" if plan["ancestor"] else "reading-whole.md")).read_text(), mapping)
    reply = ctx.p("-reply.md", n - 1)
    if reply.exists():
        line, content = (BLOCKS / "reply-line.md").read_text(), reply.read_text()
    else:
        line, content = (BLOCKS / "no-reply-line.md").read_text(), read_text(ctx.p(".md", n - 1)) or ""
    frame = (BLOCKS / "later-round.md").read_text()
    frame = frame.replace("<reading paragraph>", reading.strip("\n")).replace("<reply line>", line.strip("\n"))
    return frame.replace("<reply file>", content.strip("\n")).strip("\n") + "\n", prev_round


def build_instructions(ctx):
    plan = ctx.plan
    out_path = str(ctx.p(".md"))
    mapping = {"<goal text>": "", "<pending head sha>": ctx.head, "<base>": plan["base"],
               "<absolute output path>": out_path}
    parts = [(REFS / "review-output.md").read_text()]
    if not ctx.review:
        parts.append(RUBRIC.read_text())
    parts += standing_text(ctx)
    block = (BLOCKS / ("review.md" if ctx.review else "goal-check.md")).read_text()
    block = fill(block, {k: v for k, v in mapping.items() if k != "<goal text>"})
    parts.append(block.replace("<goal text>", goal_text(ctx)))
    later = None
    if ctx.review and ctx.n > 1:
        later, _ = later_block(ctx)
        parts.append(fill(later, {k: v for k, v in mapping.items() if k in ("<pending head sha>", "<absolute output path>")}))
    if ctx.review and ctx.args.reviewer_paragraph:
        text = read_text(ctx.args.reviewer_paragraph)
        if text is None:
            raise Stop(REFUSED, ["REFUSED: the reviewer paragraph file %s is missing" % ctx.args.reviewer_paragraph])
        parts.append(text)
    replacement = fill((BLOCKS / "replacement-sentence.md").read_text(), {"<absolute output path>": out_path})
    if ctx.args.replacement:
        parts.append(replacement)
    ctx.p("-instructions.md").write_text("\n".join(x if x.endswith("\n") else x + "\n" for x in parts), encoding="utf-8")
    if plan["resume"]:
        skeleton = (BLOCKS / "resume-prompt.md").read_text()
        sentence = replacement.strip("\n") if ctx.args.replacement else \
            "Write your whole report to %s before you finish." % out_path
        skeleton = fill(skeleton, {"<previous head sha>": plan["prev_head"], "<pending head sha>": ctx.head,
                                   "<output sentence>": sentence,
                                   "<previous report path>": str(ctx.p(".md", ctx.n - 1))})
        ctx.p("-resume.md").write_text(skeleton.replace("<later-round block>", (later or "").strip("\n")),
                                       encoding="utf-8")


# ---- step 8: the session id -------------------------------------------------

def new_session(ctx):
    plan = ctx.plan
    n = ctx.n
    if plan["resume"]:
        sid = plan["session"]["session_id"]
        entry = {"runner": "claude", "session_id": sid, "resumed_from": "skeptical-r%d" % (n - 1),
                 "fresh_reason": None}
    else:
        try:
            r = subprocess.run(["uuidgen"], capture_output=True, text=True)
            sid = r.stdout.strip().lower() if r.returncode == 0 and r.stdout.strip() else None
        except OSError:
            sid = None
        if not sid:
            sid = str(uuid.uuid4())
            ctx.event("fallback", "uuidgen is not available, so the id came from Python")
        ids = list(ctx.run.get("review_session_ids") or [])
        ids.append(sid)
        ctx.run_set("review_session_ids", ids)
        entry = {"runner": "claude", "session_id": sid, "resumed_from": None,
                 "fresh_reason": plan["fresh_reason"] if n > 1 else None}
    if ctx.review:
        ctx.run_set("review_sessions.skeptical-r%d" % n, entry)
    return sid


# ---- step 9: the run script -------------------------------------------------

def run_script(ctx, sid):
    n = ctx.n
    q = shlex.quote
    prefix = "%s %d " % (ctx.tool, ctx.cap) if ctx.tool else ""
    allow = ",".join([ALLOW % str(ctx.rec).lstrip("/")] + list(ctx.args.allow_extra or []))
    tail = "--append-system-prompt-file %s --allowedTools %s" % (q(str(ctx.p("-instructions.md"))), q(allow))
    out = "> %s 2> %s; echo $? > %s" % (q(str(ctx.p("-result.json"))), q(str(ctx.p("-result.stderr"))),
                                          q(str(ctx.p("-result.exit"))))
    if ctx.plan["resume"]:
        cmd = "cd %s && %sclaude -p --resume %s --model %s --effort high --output-format json %s < %s %s" % (
            q(str(ctx.wt)), prefix, q(sid), ctx.model, tail, q(str(ctx.p("-resume.md"))), out)
    else:
        cmd = "cd %s && printf '%%s\\n' \"%s\" | %sclaude -p --model %s --effort high --output-format json " \
              "--session-id %s %s %s" % (q(str(ctx.wt)), PROMPT, prefix, ctx.model, q(sid), tail, out)
    path = ctx.p("-run.sh")
    path.write_text(cmd + "\n", encoding="utf-8")
    return path


def retire_attempt(ctx):
    n = ctx.n
    ks = [int(m.group(1)) for f in os.listdir(ctx.reviews)
          for m in [re.match(r"skeptical-r%d(?:-[a-z]+)?-attempt(\d+)" % n, f)] if m]
    k = max(ks or [0]) + 1
    for old, new in RETIRE:
        src = ctx.reviews / old.format(n=n)
        if src.exists():
            src.rename(ctx.reviews / new.format(n=n, k=k))
    return k


def launch(ctx):
    """Steps 1 to 9 for one launch, with the resume fallback. Returns nothing."""
    ctx.plan = resolve_round(ctx)
    build_instructions(ctx)
    sid = new_session(ctx)
    script = run_script(ctx, sid)
    subprocess.run(["bash", str(script)])
    if ctx.plan["resume"]:
        code = read_text(ctx.p("-result.exit"))
        if code is None or code.strip() != "0":
            status = (code or "none").strip()
            retire_attempt(ctx)
            ctx.event("fallback", "the resume exited %s, so the round launches fresh" % status)
            ctx.plan = resolve_round(ctx, force="resume exited %s" % status)
            build_instructions(ctx)
            sid = new_session(ctx)
            script = run_script(ctx, sid)
            subprocess.run(["bash", str(script)])


def build_replacement(ctx):
    """The files of a round that a replacement runner reviews. Nothing launches."""
    round_table(ctx)
    prepare_worktree(ctx)
    if not ctx.review:
        setup_and_baseline(ctx)
    plan = resolve_round(ctx)
    build_instructions(ctx)
    lines = ["instructions: %s" % ctx.p("-instructions.md"), "worktree: %s" % ctx.wt, "base: %s" % plan["base"]]
    if plan["resume"]:
        lines += ["resume prompt: %s" % ctx.p("-resume.md"), "resume session: %s" % plan["session"]["session_id"]]
    else:
        lines.append("resume prompt: none. fresh_reason: %s" % plan["fresh_reason"])
    raise Stop(OK, lines, "BUILT")


def run_round(ctx):
    find_timeout(ctx)
    startup_check(ctx)
    round_table(ctx)
    prepare_worktree(ctx)
    if not ctx.review:
        setup_and_baseline(ctx)
    launch(ctx)


# ---- step 10 to 12: the checks ----------------------------------------------

def denied_list(data):
    out = []
    for item in (data or {}).get("permission_denials") or []:
        ti = item.get("tool_input") if isinstance(item, dict) else item
        if isinstance(ti, dict):
            ti = ti.get("command") or ti.get("file_path") or json.dumps(ti, sort_keys=True)
        out.append(str(ti))
    return out


def is_cannot_mark(line):
    """A line marks a check `Cannot verify` when it is no heading and holds the
    words outside a backtick span that names only them."""
    if line.lstrip().startswith("#"):
        return False
    return "Cannot verify" in re.sub(r"`Cannot verify`", "", line)


def evaluate(ctx):
    n = ctx.n
    reasons = []
    cannot = []
    code_text = read_text(ctx.p("-result.exit"))
    code = int(code_text.strip()) if code_text and code_text.strip().lstrip("-").isdigit() else None
    raw = read_text(ctx.p("-result.json"))
    try:
        data = json.loads(raw) if raw else None
        data = data if isinstance(data, dict) else None
    except ValueError:
        data = None
    stderr = read_text(ctx.p("-result.stderr")) or ""
    ev = {"exit": code, "denied": denied_list(data), "denials_ok": False, "report_ok": False, "prev_mismatch": False}
    if code is None:
        reasons.append("the exit file is missing")
    elif code != 0:
        reasons.append("exit %d%s" % (code, " (the timeout cap stopped it)" if code == 124 else ""))
    if data is None:
        reasons.append("the result JSON is missing or not JSON")
    elif data.get("is_error"):
        reasons.append("is_error is true in the result JSON")
    if (data is None or not str(data.get("result") or "").strip()) and "Input must be provided" in stderr:
        reasons.append("the prompt never reached the child (Input must be provided)")
        ctx.noprompt = True
    report_path = ctx.p(".md")
    text = read_text(report_path)
    if text is None and data is not None:
        result = str(data.get("result") or "").strip()
        if pair_at_end(result):
            m = re.search(r"^Reviewed: (\S+)", result, re.M)
            sha = m.group(1) if m else ctx.head
            body = re.sub(r"\A\s*Reviewed: \S+\n", "", result + "\n").strip("\n")
            head = "Reviewed: %s\nSource: result field\n" % sha + ("Check: goal\n" if not ctx.review else "")
            report_path.write_text(head + "\n" + body + "\n", encoding="utf-8")
            text = read_text(report_path)
            ctx.event("fallback", "the report file was missing, so it was written from the result field")
    if text is None:
        reasons.append("no report came back, from the file or from the result field")
    else:
        if not ctx.review and not re.search(r"^Check: goal$", text, re.M):
            lines = text.split("\n")
            at = 2 if len(lines) > 1 and lines[1].startswith("Source:") else 1
            lines.insert(at, "Check: goal")
            text = "\n".join(lines)
            report_path.write_text(text, encoding="utf-8")
            ctx.event("fallback", "the report had no Check: goal line, so it was added")
        first = text.split("\n", 1)[0].strip()
        bad = []
        if first != "Reviewed: %s" % ctx.head:
            bad.append("the report opens with `%s`, not `Reviewed: %s`" % (first, ctx.head))
        if not pair_at_end(text):
            bad.append("the report does not end with the verdict pair")
        entry = (ctx.run.get("review_sessions") or {}).get("skeptical-r%d" % n)
        resumed = bool(isinstance(entry, dict) and entry.get("resumed_from"))
        if resumed:
            resume_text = read_text(ctx.p("-resume.md")) or ""
            m = re.search(r"you reviewed (\S+)\.", resume_text)
            ctx.prev_head = m.group(1) if m else ctx.prev_head
            prev = (read_text(ctx.p(".md", n - 1)) or "").split("\n", 1)[0].strip()
            if ctx.prev_head and prev != "Reviewed: %s" % ctx.prev_head:
                bad.append("the previous round's report opens with `%s`, so the resumed reviewer overwrote it" % prev)
                ev["prev_mismatch"] = True
        reasons += bad
        ev["report_ok"] = not bad
        cannot = [x.strip() for x in text.split("\n") if is_cannot_mark(x)]
    ev["denials_ok"] = text is not None
    ev["reasons"] = reasons
    ev["cannot"] = cannot
    return ev


def restore_previous(ctx):
    n = ctx.n
    prev_report = ctx.p(".md", n - 1)
    raw = read_text(ctx.p("-result.json", n - 1))
    try:
        result = str((json.loads(raw) or {}).get("result") or "").strip() if raw else ""
    except ValueError:
        result = ""
    if result and pair_at_end(result):
        body = re.sub(r"\A\s*Reviewed: \S+\n", "", result + "\n").strip("\n")
        prev_report.write_text("Reviewed: %s\nSource: result field\n\n%s\n" % (ctx.prev_head, body), encoding="utf-8")
        ctx.event("fallback", "the previous report was overwritten and is restored from its result field")
    else:
        ctx.event("fallback", "the previous report was overwritten and its result field holds no report: lost")
        ctx.decision("Review round %d report lost" % (n - 1), "recorded, and the round goes on",
                     "skeptical-r%d.md was overwritten by the resumed reviewer of round %d" % (n - 1, n),
                     ["Round: %d" % (n - 1)])


def failure_count(ctx, title):
    text = read_text(ctx.rec / "decisions.md") or ""
    return text.split("\n").count("## " + title)


def failure_path(ctx, ev, reasons):
    n = ctx.n
    title = "Review round %d failed" % n
    prior = failure_count(ctx, title)
    lines = ["Reason: " + "; ".join(reasons)]
    if ctx.noprompt:
        lines.append("Command: " + (read_text(ctx.p("-run.sh")) or "").strip())
    if ev and ev.get("prev_mismatch"):
        restore_previous(ctx)
    ctx.decision(title, "escalate: the second failure" if prior else "retire the attempt and run the round once more",
                 "reviews/skeptical-r%d-result.json and its siblings" % n, lines)
    if prior:
        raise Stop(ESCALATE, ["ESCALATE: the review could not produce a report. Round %d failed a second time: %s. "
                              "Hand over what the branch holds." % (n, "; ".join(reasons))])
    k = retire_attempt(ctx)
    results = dict(ctx.run.get("review_results") or {})
    if str(n) in results:
        del results[str(n)]
        ctx.run_set("review_results", results)
    ctx.event("retry", "round %d failed (%s). The attempt is retired as attempt%d. The round runs once more." % (
        n, "; ".join(reasons), k))
    ctx.noprompt = False
    run_round(ctx)
    settle(ctx)


def write_entry(ctx, ev, denials_ok):
    entry = {"exit": ev["exit"], "denials_ok": denials_ok, "report_ok": ev["report_ok"], "denied": ev["denied"],
             "at": now()}
    ctx.run_set("review_results.%d" % ctx.n, entry)
    ctx.summary.update(exit=ev["exit"], denials_ok=denials_ok, report_ok=ev["report_ok"], denied=ev["denied"])


def settle(ctx, judged=None):
    """Check the attempt on disk and act on the outcome."""
    ev = evaluate(ctx)
    ctx.summary.update(exit=ev["exit"], denials_ok=ev["denials_ok"], report_ok=ev["report_ok"], denied=ev["denied"])
    if ev["reasons"]:
        return failure_path(ctx, ev, ev["reasons"])
    if judged is False:
        return failure_path(ctx, ev, ["the report holds a Cannot verify line that bears on the verdict (judged by "
                                      "the project lead)"])
    if ev["cannot"] and judged is None:
        opts = ""
        if ctx.args.setup:
            opts += " --setup %s" % shlex.quote(ctx.args.setup)
        if ctx.args.reviewer_paragraph:
            opts += " --reviewer-paragraph %s" % shlex.quote(ctx.args.reviewer_paragraph)
        for rule in ctx.args.allow_extra or []:
            opts += " --allow-extra %s" % shlex.quote(rule)
        lines = ["CANNOT VERIFY: %s" % x for x in ev["cannot"]]
        lines.append("No review_results entry was written. Judge whether each line bears on the verdict, then run: "
                     "python3 %s %s record --denials-ok true|false%s" % (shlex.quote(str(HERE / "review-run.py")),
                                                                         shlex.quote(str(ctx.rec)), opts))
        raise Stop(CANNOT, lines)
    write_entry(ctx, ev, True)


def saved_attempt(ctx):
    """Return True when a saved attempt settled the round with no launch."""
    results = ctx.run.get("review_results") or {}
    rr = results.get(str(ctx.n))
    if isinstance(rr, dict) and rr.get("denials_ok") is True and rr.get("report_ok") is True \
            and ctx.p(".md").exists():
        ctx.event("fallback", "a passing result for round %d is already recorded, so nothing launches" % ctx.n)
        ctx.summary.update(exit=rr.get("exit"), denials_ok=True, report_ok=True, denied=rr.get("denied", []))
        return True
    if ctx.p("-result.json").exists():
        ctx.event("fallback", "a saved result for round %d is on disk, so the checks run over it before any launch"
                  % ctx.n)
        settle(ctx)
        return True
    if ctx.p("-instructions.md").exists():
        k = retire_attempt(ctx)
        ctx.event("retry", "an attempt died before its process finished. It is retired as attempt%d" % k)
    return False


# ---- the output -------------------------------------------------------------

def finish(ctx, code, lines, word=None):
    for line in lines:
        say(line)
    s = ctx.summary
    say("---")
    say("round: %s" % s.get("round", "unknown"))
    say("report: %s" % s.get("report", "unknown"))
    say("exit: %s" % s.get("exit"))
    say("denials_ok: %s" % json.dumps(s.get("denials_ok")))
    say("report_ok: %s" % json.dumps(s.get("report_ok")))
    say("denied: %s" % json.dumps(s.get("denied", [])))
    for line in ctx.events:
        if line.startswith(("fallback:", "retry:")):
            say(line)
    say("status: %s" % (word or STATUS[code]))
    sys.exit(code)


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("record_dir")
    ap.add_argument("mode", nargs="?", choices=["run", "record"], default="run")
    ap.add_argument("--setup")
    ap.add_argument("--reviewer-paragraph")
    ap.add_argument("--denials-ok", choices=["true", "false"])
    ap.add_argument("--replacement")
    ap.add_argument("--allow-extra", action="append")
    ap.add_argument("--startup-interval", type=float, default=60.0)
    args = ap.parse_args(argv)
    ctx = Round(args)
    try:
        basics(ctx)
        if args.mode == "record":
            if args.denials_ok is None:
                raise Stop(REFUSED, ["REFUSED: record needs --denials-ok true|false"])
            if not ctx.p("-result.json").exists():
                raise Stop(REFUSED, ["REFUSED: no saved result for round %d. Run the script without `record`." % ctx.n])
            settle(ctx, judged=(args.denials_ok == "true"))
        elif args.replacement:
            build_replacement(ctx)
        elif not saved_attempt(ctx):
            run_round(ctx)
            settle(ctx)
    except Stop as stop:
        finish(ctx, stop.code, stop.lines, stop.word)
    finish(ctx, OK, [])


if __name__ == "__main__":
    main(sys.argv[1:])

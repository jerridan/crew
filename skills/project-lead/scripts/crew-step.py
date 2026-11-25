#!/usr/bin/env python3
"""Run a fixed sequence of a crew project lead's commands and record writes in
one call.

usage:
  crew-step.py launch-check <record-dir>
  crew-step.py branch <record-dir> <deliverable-id> [--branch <name>] [--held] [--start-point <ref>] [--territory <slug>=<ic-name> ...]
  crew-step.py verify <record-dir> <package-id> [--repo <path>] [--criterion <cmd>] [--suite <cmd> | --no-suite] [--red <sha>] [--pattern <regex>] [--ic-branch] [--diff]
  crew-step.py hand-over <record-dir> <deliverable-id> --body <file> --title <t>
  crew-step.py hand-over <record-dir> <deliverable-id> --local
  crew-step.py cleanup <record-dir> <deliverable-id>
  crew-step.py park <record-dir> --reason usage|pause|question --next "<text>" [--until <epoch>] [--by <name>] [--delay <seconds>]
  crew-step.py unpark <record-dir> [--by "<text>"]

`skills/project-lead/references/crew-step.md` owns what each subcommand and
flag does, and when the project lead runs it.

`skills/project-lead/references/crew-step.md` also owns the output lines, the
evidence markers and the exit codes.

Record writes. Every write to the record's state goes through
`crew-record.py`, which runs from this script's own directory, as `spend.py`
does. `crew-orch.py`, `launcher.py` and `crew-usage.py` run from
`../../orchestrator/scripts/`. This script writes one record file itself:
`worktrees.json`. A park writes its prompt file and its log in
`<record-dir>/park/`. It decides nothing that the project
lead judges: it reads no PR body, writes no decision on a diff, and
escalates nothing.

Python 3 standard library only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
RECORD = os.path.join(HERE, "crew-record.py")
SPEND = os.path.join(HERE, "spend.py")
ORCH = os.path.normpath(os.path.join(HERE, "..", "..", "orchestrator", "scripts", "crew-orch.py"))
ORCH_SCRIPTS = os.path.normpath(os.path.join(HERE, "..", "..", "orchestrator", "scripts"))
LAUNCHER = os.path.join(ORCH_SCRIPTS, "launcher.py")
USAGE = os.path.join(ORCH_SCRIPTS, "crew-usage.py")
PARK_MD = os.path.normpath(os.path.join(HERE, "..", "references", "park.md"))
PARK_REASONS = ("usage", "pause", "question")
PARK_DELAY = 20
NO_MATCH = 3
WINDOW_WATCH = os.path.normpath(os.path.join(HERE, "..", "..", "delivered-window", "scripts", "window-watch.py"))
NO_REMOTE = "launch check 3 (trigger 6): no remote"
TAIL = 40


class Usage(Exception):
    """A usage error: the call exits 2 and runs nothing."""


class Out:
    """The step lines, then the evidence blocks, then the exit code."""

    def __init__(self):
        self.failed = False
        self.evidence = []

    def ok(self, step, detail):
        print("ok %s: %s" % (step, detail), flush=True)

    def fail(self, step, detail):
        self.failed = True
        print("FAIL %s: %s" % (step, detail), flush=True)

    def line(self, text):
        print(text, flush=True)

    def add(self, name, text):
        self.evidence.append((name, text))

    def finish(self, diff=None):
        for name, text in self.evidence:
            sys.stdout.write("--- %s\n" % name)
            if text:
                sys.stdout.write(text if text.endswith("\n") else text + "\n")
        if diff is not None:
            # The diff prints byte for byte, with no word after it.
            sys.stdout.write("--- diff\n")
            sys.stdout.write(diff)
        sys.stdout.flush()
        return 1 if self.failed else 0


# --- commands ---------------------------------------------------------------

def run(cmd, cwd=None):
    try:
        return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except OSError as exc:
        return subprocess.CompletedProcess(cmd, 127, "", str(exc))


def git(where, *args):
    return run(["git", "-C", where] + list(args))


def err(result):
    """The command's own error text, on one line."""
    text = (result.stderr or "").strip() or (result.stdout or "").strip()
    text = " | ".join(line.strip() for line in text.splitlines() if line.strip())
    return text or "exit %d" % result.returncode


def record(rec, *args):
    return run([sys.executable, RECORD, rec] + list(args))


def record_step(out, rec, label, args, step="record"):
    """One crew-record.py call, one line. Return True when it passed."""
    result = record(rec, *args)
    if result.returncode == 0:
        out.ok(step, label)
        return True
    out.fail(step, "%s: %s" % (label, err(result)))
    return False


def shell(cmd, cwd):
    """Run a criterion or suite command. Return its exit code and output."""
    result = subprocess.run(cmd, shell=True, cwd=cwd, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True)
    return result.returncode, result.stdout


def tail(text):
    return "\n".join(text.splitlines()[-TAIL:])


# --- the record -------------------------------------------------------------

def load_state(rec):
    path = os.path.join(rec, "state.json")
    if not os.path.isfile(path):
        raise Usage("no record at %s: state.json is missing" % rec)
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def find(items, wanted):
    for item in items or []:
        if item.get("id") == wanted:
            return item
    return None


def load_worktrees(rec):
    path = os.path.join(rec, "worktrees.json")
    if not os.path.isfile(path):
        return None
    with open(path, encoding="utf-8") as handle:
        return json.load(handle)


def save_worktrees(rec, data):
    """Write worktrees.json in one atomic replace."""
    worktrees_path = os.path.join(rec, "worktrees.json")
    worktrees_tmp = "%s.%d.tmp" % (worktrees_path, os.getpid())
    with open(worktrees_tmp, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(worktrees_tmp, worktrees_path)


def session_id(run_state):
    sid = os.environ.get("CLAUDE_CODE_SESSION_ID")
    if sid:
        return sid
    ids = run_state.get("session_ids") or []
    return ids[-1] if ids else None


def real(path):
    return os.path.realpath(path)


def registered(repo):
    """Map each registered worktree's real path to its branch (or None)."""
    result = git(repo, "worktree", "list", "--porcelain")
    found, path = {}, None
    for line in result.stdout.splitlines():
        if line.startswith("worktree "):
            path = real(line[len("worktree "):])
            found[path] = None
        elif line.startswith("branch ") and path:
            found[path] = line[len("branch "):].replace("refs/heads/", "", 1)
    return found


def branch_exists(repo, name):
    return git(repo, "rev-parse", "--verify", "--quiet", "refs/heads/" + name).returncode == 0


def classify(status_text, file_set):
    """Split `status --porcelain -z` by the clean-tree definition.

    With -z, git quotes no path, and a rename names its source in the next record.
    """
    tracked, inside, outside = [], [], []
    records = status_text.split("\0")
    i = 0
    while i < len(records):
        record_text = records[i]
        i += 1
        if len(record_text) < 4:
            continue
        code, path = record_text[:2], record_text[3:]
        if "R" in code or "C" in code:
            i += 1
        if code == "??":
            (inside if path in file_set else outside).append(path)
        else:
            tracked.append(path)
    return tracked, inside, outside


def check_id(value, what):
    """A name that goes into a path or a branch holds no `/` and no `..`."""
    if not value or "/" in value or ".." in value:
        raise Usage("%s is not a valid %s: it holds a / or .. or is empty" % (value, what))


def check_branch_name(name):
    if run(["git", "check-ref-format", "--branch", name]).returncode != 0:
        raise Usage("%s is not a valid branch name" % name)


# --- argument parsing -------------------------------------------------------

def parse(argv, valued, flags, repeated=()):
    positional, opts = [], {}
    i = 0
    while i < len(argv):
        item = argv[i]
        if item in valued:
            if i + 1 >= len(argv):
                raise Usage("%s needs a value" % item)
            if item in repeated:
                opts.setdefault(item, []).append(argv[i + 1])
            elif item in opts:
                raise Usage("%s given twice" % item)
            else:
                opts[item] = argv[i + 1]
            i += 2
        elif item in flags:
            opts[item] = True
            i += 1
        elif item.startswith("--"):
            raise Usage("unknown flag %s" % item)
        else:
            positional.append(item)
            i += 1
    return positional, opts


def want(positional, count, form):
    if len(positional) != count:
        raise Usage("usage: crew-step.py " + form)
    return positional


# --- launch-check -----------------------------------------------------------

def probe(repo, base, log):
    """Probe one worktree base. Log each command's result. Return True on a pass."""
    probe_path = os.path.join(base, "worktrees", "probe")
    added = git(repo, "worktree", "add", "--detach", probe_path, "HEAD")
    if added.returncode != 0:
        log.append("%s: add refused (%s)" % (base, err(added)))
        return False
    passed = True
    status = git(probe_path, "status")
    if status.returncode != 0:
        log.append("%s: status refused (%s)" % (base, err(status)))
        passed = False
    # The probe is this script's own empty worktree: the one forced removal.
    removed = git(repo, "worktree", "remove", "--force", probe_path)
    if removed.returncode != 0:
        log.append("%s: remove of the probe refused (%s)" % (base, err(removed)))
        passed = False
    if passed:
        log.append("%s: add, status and remove passed" % base)
    return passed


def cmd_launch_check(argv):
    positional, _ = parse(argv, (), ())
    (rec,) = want(positional, 1, "launch-check <record-dir>")
    state = load_state(rec)
    run_state = state.get("run", {})
    repo, slug = run_state.get("repo"), state.get("goal_slug")
    if not repo or not slug:
        raise Usage("the record has no run.repo or goal_slug")
    out = Out()
    log = []
    chosen = None
    fallback = os.path.join(repo, ".claude", "worktrees", "crew", slug)
    if probe(repo, rec, log):
        chosen = rec
    elif probe(repo, fallback, log):
        ignored = git(repo, "check-ignore", "-v", fallback)
        if ignored.stdout.strip():
            log.append("%s: check-ignore matched (%s)" % (fallback, ignored.stdout.strip()))
            chosen = fallback
        else:
            log.append("%s: check-ignore printed no line" % fallback)
    if chosen:
        out.ok("base", chosen)
    else:
        out.fail("base", "; ".join(log))
    remotes = git(repo, "remote")
    names = remotes.stdout.split()
    if remotes.returncode != 0:
        out.fail("remote", err(remotes))
    elif names:
        out.ok("remote", ", ".join(names))
    else:
        out.fail("remote", "no remote")
    if chosen:
        record_step(out, rec, "run set worktree_base", ["run", "set", "worktree_base", json.dumps(chosen)])
        title = "Which worktree base does this run use?"
        decisions = os.path.join(rec, "decisions.md")
        written = ""
        if os.path.isfile(decisions):
            with open(decisions, encoding="utf-8") as handle:
                written = handle.read()
        if ("## %s\n" % title) in written and ("Answer: %s\n" % chosen) in written:
            out.ok("record", "decision: already done")
        else:
            record_step(out, rec, "decision", [
                "decision", "precedent", title,
                "--answer", chosen,
                "--citation", "full-path.md launch check 1: " + "; ".join(log),
                "--confidence", "high"])
    if chosen == fallback:
        out.line("ask collect: does the repo's test command collect files under %s? "
                 "Answer it, and escalate on a collect hit." % os.path.join(repo, ".claude"))
    return out.finish()


# --- branch -----------------------------------------------------------------

def cmd_branch(argv):
    positional, opts = parse(argv, ("--branch", "--start-point", "--territory"), ("--held",),
                             repeated=("--territory",))
    rec, did = want(positional, 2, "branch <record-dir> <deliverable-id> [--branch <name>] [--held] "
                                   "[--start-point <ref>] [--territory <slug>=<ic-name> ...]")
    check_id(did, "deliverable id")
    if opts.get("--branch"):
        check_branch_name(opts["--branch"])
    territories = []
    for item in opts.get("--territory", []):
        slug_part, sep, ic = item.partition("=")
        if not sep or not slug_part or not ic or "/" in slug_part or ".." in slug_part:
            raise Usage("--territory takes <slug>=<ic-name> with no / or .. in the slug, got %s" % item)
        territories.append((slug_part, ic))
    state = load_state(rec)
    run_state = state.get("run", {})
    repo, slug = run_state.get("repo"), state.get("goal_slug")
    if not repo or not slug:
        raise Usage("the record has no run.repo or goal_slug")
    for tslug, _ in territories:
        check_branch_name("crew/%s/%s" % (slug, tslug))
    worktree_base = run_state.get("worktree_base") or rec
    dl = find(state.get("deliverables"), did)
    wt = load_worktrees(rec) or {}
    sid = session_id(run_state)
    out = Out()

    name = opts.get("--branch") or (dl.get("branch") if dl else None) or "crew/%s/%s" % (slug, did)
    current_r = git(repo, "branch", "--show-current")
    if current_r.returncode != 0:
        out.fail("held", err(current_r))
        return out.finish()
    current = current_r.stdout.strip()

    # Held: the record says so, the flag says so, or another run's branch is out.
    parts = current.split("/")
    if did in wt:
        held, why = True, "held: recorded worktree %s" % wt[did].get("worktree")
    elif dl:
        held, why = False, "free, recorded deliverable on %s" % dl.get("branch")
    elif opts.get("--held"):
        held, why = True, "held: --held"
    elif current.startswith("crew/") and len(parts) > 2 and parts[1] != slug:
        held, why = True, "held: %s is another run's" % current
    else:
        held, why = False, ("free on %s" % current) if current else "free, detached"
    out.ok("held", why)

    deliverable_path = os.path.join(worktree_base, "worktrees", did)
    start_point = None
    if held:
        start_point = opts.get("--start-point")
        if not start_point:
            origin = git(repo, "rev-parse", "--abbrev-ref", "origin/HEAD")
            if origin.returncode == 0 and origin.stdout.strip():
                start_point = origin.stdout.strip()
        if not start_point and dl and dl.get("base"):
            start_point = dl["base"]
        if not start_point:
            out.fail("start-point", "no --start-point and no origin/HEAD")
            return out.finish()
        sha = git(repo, "rev-parse", "--verify", start_point + "^{commit}")
        if sha.returncode != 0:
            out.fail("start-point", err(sha))
            return out.finish()
        out.ok("start-point", start_point)

    # Exists: a branch or a worktree that git or the disk holds and the record does not name.
    if dl and opts.get("--branch") and dl.get("branch") != opts["--branch"]:
        out.fail("exists", "%s records branch %s, not %s" % (did, dl.get("branch"), opts["--branch"]))
        return out.finish()
    recorded_branches = {e.get("branch") for e in wt.values()}
    if dl:
        recorded_branches.add(dl.get("branch"))
    recorded_paths = {real(e.get("worktree", "")) for e in wt.values() if e.get("worktree")}
    conflicts = []
    if branch_exists(repo, name) and name not in recorded_branches:
        conflicts.append("branch %s" % name)
    if held and os.path.exists(deliverable_path) and real(deliverable_path) not in recorded_paths:
        conflicts.append("path %s" % deliverable_path)
    for tslug, ic in territories:
        tbranch = "crew/%s/%s" % (slug, tslug)
        tpath = os.path.join(worktree_base, "worktrees", tslug)
        entry = wt.get(ic)
        if entry and (real(entry.get("worktree", "")) != real(tpath) or entry.get("branch") != tbranch):
            conflicts.append("%s is recorded at %s on %s" % (ic, entry.get("worktree"), entry.get("branch")))
        if branch_exists(repo, tbranch) and tbranch not in recorded_branches:
            conflicts.append("branch %s" % tbranch)
        if os.path.exists(tpath) and real(tpath) not in recorded_paths:
            conflicts.append("path %s" % tpath)
    if conflicts:
        out.fail("exists", "not in the record: " + "; ".join(conflicts))
        return out.finish()
    out.ok("exists", "nothing outside the record")

    def add_deliverable(base, checkout_branch):
        if dl:
            out.ok("record", "deliverable add: already done")
            return True
        entry = {"id": did, "branch": name, "base": base, "state": "pending", "pr_url": None,
                 "checkout_branch": checkout_branch, "checkout_restored": None}
        return record_step(out, rec, "deliverable add", ["deliverable", "add", json.dumps(entry)])

    def set_checkout(path):
        if run_state.get("checkout") == path:
            out.ok("record", "run set checkout: already done")
            return True
        return record_step(out, rec, "run set checkout", ["run", "set", "checkout", json.dumps(path)])

    if held:
        checkout = deliverable_path
        if did not in wt:
            wt[did] = {"worktree": deliverable_path, "branch": name, "session_ids": [sid], "orphaned": False}
            save_worktrees(rec, wt)
        if not add_deliverable(sha.stdout.strip(), None) or not set_checkout(deliverable_path):
            return out.finish()
        if registered(repo).get(real(deliverable_path)) == name:
            out.ok("worktree", "%s: already done" % did)
        else:
            if branch_exists(repo, name):
                added = git(repo, "worktree", "add", deliverable_path, name)
            else:
                added = git(repo, "worktree", "add", deliverable_path, "-b", name, start_point)
            if added.returncode != 0:
                out.fail("worktree", "%s: %s" % (did, err(added)))
                return out.finish()
            out.ok("worktree", did)
    else:
        checkout = repo
        head = git(repo, "rev-parse", "HEAD")
        if head.returncode != 0:
            out.fail("switch", err(head))
            return out.finish()
        if not add_deliverable(head.stdout.strip(), current or None) or not set_checkout(repo):
            return out.finish()
        if current == name:
            out.ok("switch", "already done")
        else:
            if branch_exists(repo, name):
                switched = git(repo, "switch", name)
            else:
                switched = git(repo, "switch", "-c", name)
            if switched.returncode != 0:
                out.fail("switch", err(switched))
                return out.finish()
            out.ok("switch", name)

    for tslug, ic in territories:
        tbranch = "crew/%s/%s" % (slug, tslug)
        tpath = os.path.join(worktree_base, "worktrees", tslug)
        if ic not in wt:
            wt[ic] = {"worktree": tpath, "branch": tbranch, "session_ids": [sid], "orphaned": False}
            save_worktrees(rec, wt)
        if registered(repo).get(real(tpath)) == tbranch:
            out.ok("worktree", "%s: already done" % tslug)
        else:
            if branch_exists(repo, tbranch):
                added = git(checkout, "worktree", "add", tpath, tbranch)
            else:
                added = git(checkout, "worktree", "add", tpath, "-b", tbranch)
            if added.returncode != 0:
                out.fail("worktree", "%s: %s" % (tslug, err(added)))
                return out.finish()
            out.ok("worktree", tslug)
        for pkg in state.get("packages") or []:
            if pkg.get("territory") != tslug:
                continue
            label = "package %s set ic_name" % pkg.get("id")
            if pkg.get("ic_name") == ic:
                out.ok("record", label + ": already done")
            elif not record_step(out, rec, label, ["package", pkg.get("id"), "set", "ic_name", json.dumps(ic)]):
                return out.finish()
    return out.finish()


# --- verify -----------------------------------------------------------------

def cmd_verify(argv):
    positional, opts = parse(argv, ("--repo", "--criterion", "--suite", "--red", "--pattern"),
                             ("--no-suite", "--ic-branch", "--diff"))
    rec, pid = want(positional, 2, "verify <record-dir> <package-id> [--repo <path>] [--criterion <cmd>] "
                                   "[--suite <cmd> | --no-suite] [--red <sha>] [--pattern <regex>] [--ic-branch] [--diff]")
    if "--suite" in opts and "--no-suite" in opts:
        raise Usage("--suite and --no-suite exclude each other")
    if "--red" in opts and "--criterion" not in opts:
        raise Usage("--red needs --criterion")
    pattern = None
    if "--pattern" in opts:
        try:
            pattern = re.compile(opts["--pattern"])
        except re.error as exc:
            raise Usage("--pattern is not a valid regex: %s" % exc)
    state = load_state(rec)
    run_state = state.get("run", {})
    pkg = find(state.get("packages"), pid)
    if not pkg:
        raise Usage("no package %s in the record" % pid)
    base = pkg.get("base")
    if not base:
        raise Usage("package %s has no base" % pid)
    file_set = set(pkg.get("file_set") or [])
    dl = find(state.get("deliverables"), pkg.get("deliverable")) or {}
    checkout = run_state.get("checkout") or run_state.get("repo")
    repo = opts.get("--repo") or checkout
    out = Out()
    evidence = {}

    entry = None
    if opts.get("--ic-branch"):
        ic_name = pkg.get("ic_name")
        entry = (load_worktrees(rec) or {}).get(ic_name) if ic_name else None
        if entry and opts.get("--repo") and real(opts["--repo"]) != real(entry.get("worktree", "")):
            raise Usage("--repo %s is not the worktree of %s: %s" % (opts["--repo"], ic_name, entry.get("worktree")))
        if not entry:
            out.fail("ic-branch", "no worktrees.json entry for %s" % ic_name)
            return out.finish()
        repo = entry["worktree"]

    # clean-tree
    status = git(repo, "status", "--porcelain", "-z", "--untracked-files=all")
    clean = False
    if status.returncode != 0:
        out.fail("clean-tree", err(status))
    else:
        tracked, inside, outside = classify(status.stdout, file_set)
        problems = []
        if tracked:
            problems.append("tracked changes: " + ", ".join(tracked))
        if inside:
            problems.append("untracked in the file set: " + ", ".join(inside))
        if problems:
            out.fail("clean-tree", "; ".join(problems))
        else:
            clean = True
            detail = "clean"
            if outside:
                detail += ", %d untracked outside the file set" % len(outside)
            out.ok("clean-tree", detail)
        if outside:
            evidence["untracked"] = "\n".join(outside)

    # log and stat
    log = git(repo, "log", "--oneline", base + "..HEAD")
    if log.returncode != 0:
        out.fail("log", err(log))
    else:
        out.ok("log", "%d commits since %s" % (len(log.stdout.splitlines()), base))
        evidence["log"] = log.stdout
        evidence["stat"] = git(repo, "diff", base + "..HEAD", "--stat").stdout

    # file-set
    names = git(repo, "diff", "-z", "--name-only", "--no-renames", base + "..HEAD")
    if names.returncode != 0:
        out.fail("file-set", err(names))
    else:
        files = [n for n in names.stdout.split("\0") if n]
        stray = [n for n in files if n not in file_set]
        if stray:
            out.fail("file-set", "outside the set: " + ", ".join(stray))
        else:
            out.ok("file-set", "%d files, all in the file set" % len(files))

    # ic-branch
    if entry:
        branch = git(entry["worktree"], "branch", "--show-current").stdout.strip()
        if branch == entry.get("branch"):
            out.ok("ic-branch", branch)
        else:
            out.fail("ic-branch", "the worktree is on %s, the entry names %s" % (branch or "a detached head",
                                                                              entry.get("branch")))
        if dl.get("base"):
            evidence["deliverable branch"] = git(checkout, "log", "--oneline", dl["base"] + "..HEAD").stdout

    # criterion and suite
    for step, flag in (("criterion", "--criterion"), ("suite", "--suite")):
        if step == "suite" and opts.get("--no-suite"):
            out.ok("suite", "no suite")
            continue
        if flag not in opts:
            out.ok(step, "not given")
            continue
        code, text = shell(opts[flag], repo)
        evidence[step] = tail(text)
        (out.ok if code == 0 else out.fail)(step, "exit %d" % code)

    # red
    if "--red" in opts:
        red_check(out, repo, opts["--red"], opts["--criterion"], clean, file_set, evidence)

    # pattern
    if pattern is not None:
        dbase = dl.get("base") or base
        diff = git(repo, "diff", dbase + "..HEAD")
        if diff.returncode != 0:
            out.fail("pattern", err(diff))
        else:
            hits = [line for line in diff.stdout.splitlines() if pattern.search(line)]
            out.ok("pattern", "%d hits" % len(hits))
            evidence["pattern"] = "\n".join(hits)

    # compactions
    ic_name = pkg.get("ic_name")
    found = []
    for c in run_state.get("compactions") or []:
        if ic_name and c.get("agent") == ic_name:
            found.append("ic %s: %s at %s (session %s)" % (ic_name, c.get("trigger"), c.get("at"), c.get("session_id")))
        elif c.get("agent") is None:
            found.append("project lead: %s at %s (session %s)" % (c.get("trigger"), c.get("at"), c.get("session_id")))
    if found:
        out.ok("compactions", "%d entries" % len(found))
        evidence["compactions"] = "\n".join(found)
    else:
        out.ok("compactions", "none")

    for name in ("log", "stat", "untracked", "criterion", "suite", "red", "pattern", "compactions",
                 "deliverable branch"):
        if name in evidence:
            out.add(name, evidence[name])
    diff = git(repo, "diff", base + "..HEAD")
    if diff.returncode != 0:
        out.fail("diff", err(diff))
    else:
        patch = os.path.join(rec, "diffs", "%s-verify.patch" % pid)
        try:
            os.makedirs(os.path.dirname(patch), exist_ok=True)
            with open(patch, "w", encoding="utf-8", newline="") as fh:
                fh.write(diff.stdout)
            out.ok("diff", "%s (%d lines)" % (patch, len(diff.stdout.splitlines())))
        except OSError as exc:
            out.fail("diff", "cannot write %s: %s" % (patch, exc))
    return out.finish(diff=diff.stdout if opts.get("--diff") else None)


def red_check(out, repo, sha, criterion, clean, file_set, evidence):
    """Run the criterion at the red commit, then switch back, always."""
    if not clean:
        out.fail("red", "dirty tree, no switch")
        return
    # The criterion and the suite ran at HEAD and can leave an edit: check again.
    status = git(repo, "status", "--porcelain", "-z", "--untracked-files=all")
    tracked, inside, outside_before = classify(status.stdout, file_set)
    if status.returncode != 0 or tracked or inside:
        out.fail("red", "dirty tree before the switch, no switch: %s"
                 % (", ".join(tracked + inside) or err(status)))
        return
    branch = git(repo, "branch", "--show-current").stdout.strip()
    old_head = git(repo, "rev-parse", "HEAD").stdout.strip()
    code, text = None, ""
    changed = []
    switched = git(repo, "switch", "--detach", sha, "-q")
    try:
        if switched.returncode == 0:
            code, text = shell(criterion, repo)
            # The tree was clean before the detach, so each change came from the criterion.
            after = git(repo, "status", "--porcelain", "-z", "--untracked-files=all")
            tracked, inside, outside = classify(after.stdout, file_set)
            changed = tracked + inside + [n for n in outside if n not in outside_before]
            if after.returncode != 0:
                changed = ["git status failed: " + err(after)]
    finally:
        # --discard-changes drops the criterion's edits, so none reaches the branch.
        flags = ["--discard-changes"] if switched.returncode == 0 else []
        back = (git(repo, "switch", "-q", *flags, branch) if branch
                else git(repo, "switch", "--detach", "-q", *flags, old_head))
    note = ""
    if changed:
        note = "; the criterion changed %s" % ", ".join(changed)
        text = text.rstrip("\n") + "\nthe criterion changed: " + ", ".join(changed)
    evidence["red"] = tail(text)
    if switched.returncode != 0:
        out.fail("red", "switch to %s failed: %s" % (sha, err(switched)))
    elif back.returncode != 0:
        out.fail("red", "switch back to %s failed: %s%s" % (branch or old_head, err(back), note))
    elif code == 0:
        out.fail("red", "the criterion passes at %s%s" % (sha, note))
    else:
        out.ok("red", "the criterion exits %d at %s%s" % (code, sha, note))


# --- hand-over and cleanup --------------------------------------------------

def escalation_line(out, run_state):
    found = [e for e in run_state.get("escalations") or [] if e.get("trigger") == NO_REMOTE]
    if not found:
        out.line("escalation: none")
    elif found[-1].get("answer") is None:
        out.line("escalation: unanswered")
    else:
        out.line("escalation: %s" % found[-1]["answer"])


def open_pr(checkout, branch):
    """The URL of an open PR on the branch, or None when there is none or gh cannot say."""
    listed = run(["gh", "pr", "list", "--head", branch, "--state", "open", "--json", "url"], cwd=checkout)
    if listed.returncode != 0:
        return None
    try:
        found = json.loads(listed.stdout or "[]")
    except ValueError:
        return None
    urls = [item.get("url") for item in found if isinstance(item, dict) and item.get("url")]
    return urls[0] if urls else None


def cmd_hand_over(argv):
    positional, opts = parse(argv, ("--body", "--title"), ("--local",))
    rec, did = want(positional, 2, "hand-over <record-dir> <deliverable-id> --body <file> --title <t> | --local")
    check_id(did, "deliverable id")
    local = bool(opts.get("--local"))
    if local and ("--body" in opts or "--title" in opts):
        raise Usage("--local takes no --body or --title")
    if not local and not ("--body" in opts and "--title" in opts):
        raise Usage("hand-over needs --body and --title, or --local")
    state = load_state(rec)
    run_state = state.get("run", {})
    dl = find(state.get("deliverables"), did)
    if not dl:
        raise Usage("no deliverable %s in the record" % did)
    checkout = run_state.get("checkout") or run_state.get("repo")
    branch = dl.get("branch")
    out = Out()
    url = dl.get("pr_url")

    if dl.get("state") in ("draft-pr-opened", "work-complete"):
        out.ok("push", "already done")
        out.ok("pr", "already done")
        out.ok("deliver", "already done")
    else:
        if local:
            out.ok("push", "skipped, --local")
            out.ok("pr", "skipped, --local")
        else:
            remotes = git(checkout, "remote").stdout.split()
            remote = "origin" if "origin" in remotes else (remotes[0] if len(remotes) == 1 else None)
            pushed = None
            if not remotes:
                out.fail("push", "no remote")
            elif remote is None:
                out.fail("push", "no origin")
            else:
                pushed = git(checkout, "push", "-u", remote, branch)
                if pushed.returncode != 0:
                    out.fail("push", err(pushed))
            if out.failed:
                escalation_line(out, run_state)
                return out.finish()
            out.ok("push", "%s to %s" % (branch, remote))
            # A rerun after a failed deliver write finds the PR it opened.
            url = open_pr(checkout, branch)
            if url:
                out.ok("pr", "already open " + url)
            else:
                created = run(["gh", "pr", "create", "--draft", "--title", opts["--title"],
                               "--body-file", os.path.abspath(opts["--body"]), "--head", branch], cwd=checkout)
                urls = [line.strip() for line in created.stdout.splitlines() if line.strip().startswith("http")]
                if created.returncode != 0 or not urls:
                    out.fail("pr", err(created))
                    escalation_line(out, run_state)
                    return out.finish()
                url = urls[-1]
                out.ok("pr", url)
        head = git(checkout, "rev-parse", "HEAD")
        if head.returncode != 0:
            out.fail("deliver", err(head))
            return out.finish()
        if local:
            args = ["deliver", did, "work-complete", "--review-head", head.stdout.strip()]
        else:
            args = ["deliver", did, "draft-pr-opened", "--pr-url", url, "--review-head", head.stdout.strip()]
        if not record_step(out, rec, args[2], args, step="deliver"):
            return out.finish()

    orch = run_state.get("orchestrator")
    if orch and url:
        for call in (["item", str(orch.get("item")), "pr", url], ["stage", str(orch.get("item")), "review"]):
            result = run([sys.executable, ORCH, "--orch", str(orch.get("name"))] + call)
            if result.returncode == 0:
                out.ok("orch", " ".join(call))
            else:
                out.fail("orch", "%s: %s" % (" ".join(call), err(result)))
    elif not orch:
        out.ok("orch", "skipped, no orchestrator")
    else:
        out.ok("orch", "skipped, no PR")

    if local:
        out.ok("watch", "skipped, --local")
    elif not url:
        out.ok("watch", "skipped, no PR")
    else:
        result = run([sys.executable, WINDOW_WATCH, "start", os.path.abspath(rec), "--hold"])
        if result.returncode != 0:
            out.fail("watch", err(result))
        elif result.stdout.strip() == "already running":
            out.ok("watch", "already running")
        else:
            out.ok("watch", "started, held")

    cleanup(out, rec, did)
    return out.finish()


def cmd_cleanup(argv):
    positional, _ = parse(argv, (), ())
    rec, did = want(positional, 2, "cleanup <record-dir> <deliverable-id>")
    check_id(did, "deliverable id")
    state = load_state(rec)
    if not find(state.get("deliverables"), did):
        raise Usage("no deliverable %s in the record" % did)
    out = Out()
    cleanup(out, rec, did)
    return out.finish()


def cleanup(out, rec, did):
    """The spend, listeners, worktree-remove and restore steps. None stops the others."""
    state = load_state(rec)
    run_state = state.get("run", {})
    repo = run_state.get("repo")
    checkout = run_state.get("checkout") or repo
    dl = find(state.get("deliverables"), did) or {}

    spent = run([sys.executable, SPEND, rec, checkout, "--write"])
    if spent.returncode == 0:
        out.ok("spend", "written")
    else:
        out.fail("spend", err(spent))

    listening = run(["lsof", "-iTCP", "-sTCP:LISTEN", "-n", "-P"])
    text = listening.stdout.strip()
    if text:
        out.ok("listeners", "%d lines; stop each process this run started" % (len(text.splitlines()) - 1))
    else:
        out.ok("listeners", "none")
    out.add("listeners", text)

    wt = load_worktrees(rec)
    if wt is None:
        out.ok("worktree-remove", "no worktrees.json")
    elif not wt:
        out.ok("worktree-remove", "no worktrees left")
    else:
        # IC worktrees branch from the deliverable checkout, so it goes last.
        keys = [k for k in wt if k != did] + ([did] if did in wt else [])
        for key in keys:
            path = wt[key].get("worktree", "")
            removed = git(repo, "worktree", "remove", path)
            if removed.returncode == 0:
                del wt[key]
                save_worktrees(rec, wt)
                out.ok("worktree-remove", path)
            elif not os.path.exists(path) and real(path) not in registered(repo):
                del wt[key]
                save_worktrees(rec, wt)
                out.ok("worktree-remove", "%s: already gone" % path)
            else:
                out.fail("worktree-remove", "%s: %s" % (path, err(removed)))

    target = dl.get("checkout_branch")
    if not target:
        out.ok("restore", "no checkout_branch")
        return
    current = git(repo, "branch", "--show-current").stdout.strip()
    if current == target:
        if dl.get("checkout_restored") is not True:
            if not record_step(out, rec, "already done", ["deliverable", did, "set", "checkout_restored", "true"],
                               step="restore"):
                return
        else:
            out.ok("restore", "already done")
        return
    dirty = [line for line in git(repo, "status", "--porcelain", "--untracked-files=no").stdout.splitlines() if line]
    if dirty:
        sentence = "dirty tree, %d files modified" % len(dirty)
        record_step(out, rec, "not restored, " + sentence,
                    ["deliverable", did, "set", "checkout_restored", json.dumps(sentence)], step="restore")
        return
    switched = git(repo, "switch", target)
    if switched.returncode != 0:
        sentence = "switch to %s failed: %s" % (target, err(switched))
        record(rec, "deliverable", did, "set", "checkout_restored", json.dumps(sentence))
        out.fail("restore", sentence)
        return
    record_step(out, rec, "switched to %s" % target, ["deliverable", did, "set", "checkout_restored", "true"],
                step="restore")


# --- park and unpark --------------------------------------------------------

def utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def record_root():
    """The record root, by the rule of crew-orch.py's record_root()."""
    env = os.environ.get("CREW_RECORD_ROOT")
    return os.path.expanduser(env) if env else os.path.join(os.path.expanduser("~"), ".claude", "crew")


def launch_identity(run_state):
    """The launch values of the session that parks, or a refusal.

    Return (identity, None) or (None, why). The identity holds name, handle,
    terminal, group, model and worktree. Today the one source is the
    orchestrator item's `launch`. A later source goes here, and nowhere else.
    """
    orch = run_state.get("orchestrator")
    if not isinstance(orch, dict) or not orch.get("name"):
        return None, "no orchestrator: a park needs run.orchestrator"
    path = os.path.join(record_root(), "orchestrators", str(orch.get("name")), "orchestrator.json")
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, "the orchestrator record %s cannot be read: %s" % (path, exc)
    item = (data.get("items") or {}).get(str(orch.get("item")))
    launch = (item or {}).get("launch") or {}
    if not launch:
        return None, "the orchestrator item %s has no launch" % orch.get("item")
    if not launch.get("tab"):
        return None, "the orchestrator item %s has no launch.tab" % orch.get("item")
    if not launch.get("session_name"):
        return None, "the orchestrator item %s has no launch.session_name" % orch.get("item")
    return {"name": launch.get("session_name"), "handle": launch.get("tab"), "terminal": launch.get("terminal"),
            "group": launch.get("tab_group"), "model": launch.get("model"),
            "worktree": launch.get("worktree")}, None


def park_conditions(at, from_session):
    """The --if pairs that hold only while run.park is this park."""
    return ["--if", "park.at=" + json.dumps(at), "--if", "park.from_session=" + json.dumps(from_session)]


def orch_set(orch, key, value):
    return run([sys.executable, ORCH, "--orch", str(orch.get("name")), "item", str(orch.get("item")),
                "set", key, json.dumps(value)])


def cmd_park(argv):
    positional, opts = parse(argv, ("--reason", "--next", "--until", "--by", "--delay"), ())
    rec, = want(positional, 1, 'park <record-dir> --reason usage|pause|question --next "<text>" '
                               "[--until <epoch>] [--by <name>] [--delay <seconds>]")
    reason = opts.get("--reason")
    if reason not in PARK_REASONS:
        raise Usage("--reason must be one of %s" % ", ".join(PARK_REASONS))
    if not (opts.get("--next") or "").strip():
        raise Usage("park needs --next with the next step")
    if reason == "pause" and not (opts.get("--by") or "").strip():
        raise Usage("--reason pause needs --by with the principal's name")
    if reason != "pause" and "--by" in opts:
        raise Usage("--by goes with --reason pause only")
    until = None
    if "--until" in opts:
        try:
            until = int(opts["--until"])
        except ValueError:
            raise Usage("--until must be epoch seconds")
    delay = PARK_DELAY
    if "--delay" in opts:
        try:
            delay = float(opts["--delay"])
        except ValueError:
            raise Usage("--delay must be a number of seconds")
        if delay < 0:
            raise Usage("--delay must not be negative")
    by = {"usage": "usage", "question": "project-lead"}.get(reason) or opts["--by"]

    out = Out()
    if not os.path.isfile(os.path.join(rec, "state.json")):
        out.fail("park", "no record at %s: state.json is missing" % rec)
        return out.finish()
    state = load_state(rec)
    run_state = state.get("run", {})
    if isinstance(run_state.get("park"), dict):
        out.fail("park", "a park is already set, from %s" % run_state["park"].get("at"))
        return out.finish()
    identity, why = launch_identity(run_state)
    if why:
        out.fail("park", why)
        return out.finish()
    repo = run_state.get("repo") or ""
    if not identity.get("worktree") or real(repo) != real(identity["worktree"]):
        out.fail("park", "run.repo %s differs from the item's launch.worktree %s" % (repo, identity.get("worktree")))
        return out.finish()
    checkout = run_state.get("checkout") or repo
    status = git(checkout, "status", "--porcelain")
    if status.returncode != 0:
        out.fail("park", "git status in %s: %s" % (checkout, err(status)))
        return out.finish()
    dirty = [line for line in status.stdout.splitlines() if line.strip()]
    if dirty:
        out.fail("park", "dirty tree in %s: %d paths; commit first" % (checkout, len(dirty)))
        return out.finish()

    rec = os.path.abspath(rec)
    park_dir = os.path.join(rec, "park")
    number = len(run_state.get("parks") or []) + 1
    park = {"reason": reason, "by": by, "at": utc_now(), "until": until, "next": opts["--next"],
            "from_session": session_id(run_state), "prompt": os.path.join(park_dir, "prompt-%d.md" % number),
            "waiter": None}
    if not record_step(out, rec, "run set park", ["run", "set", "park", json.dumps(park)]):
        return out.finish()
    inputs = {"rec": rec, "park": park, "identity": identity, "repo": repo, "delay": delay,
              "orchestrator": run_state.get("orchestrator"), "slug": state.get("goal_slug") or os.path.basename(rec)}
    try:
        os.makedirs(park_dir, exist_ok=True)
        with open(os.path.join(park_dir, "park.log"), "a", encoding="utf-8") as park_log:
            # A new session: the end of this Bash call and of the claude session
            # that parks sends the helper no signal.
            helper = subprocess.Popen([sys.executable, os.path.abspath(__file__), "park-helper", json.dumps(inputs)],
                                      stdin=subprocess.DEVNULL, stdout=park_log, stderr=subprocess.STDOUT,
                                      start_new_session=True, close_fds=True)
    except OSError as exc:
        out.fail("helper", str(exc))
        end_park(rec, park, {"step": "helper", "at": utc_now(), "error": str(exc)}, out.line)
        return out.finish()
    out.ok("helper", "started pid %d, log %s" % (helper.pid, os.path.join(park_dir, "park.log")))
    return out.finish()


def end_park(rec, park, failed, say):
    """Move this park to run.parks with `failed`, and set run.park null. Only while it is this park."""
    entry = dict(park, failed=failed)
    conditions = park_conditions(park["at"], park["from_session"])
    moved = record(rec, "run", "append", "parks", json.dumps(entry), *conditions)
    if moved.returncode == NO_MATCH:
        say("%s ok rollback: the park is already gone" % utc_now())
        return
    if moved.returncode != 0:
        say("%s FAIL rollback: %s" % (utc_now(), err(moved)))
        return
    cleared = record(rec, "run", "set", "park", "null", *conditions)
    if cleared.returncode != 0:
        say("%s FAIL rollback: %s" % (utc_now(), err(cleared)))


def cmd_park_helper(argv):
    """The detached half of park. Its stdout is park/park.log: one line per step."""
    inputs = json.loads(argv[0])
    rec, park, identity = inputs["rec"], inputs["park"], inputs["identity"]
    orch = inputs.get("orchestrator")

    def say(text):
        print(text, flush=True)

    def log(kind, step, detail):
        say("%s %s %s: %s" % (utc_now(), kind, step, detail))

    def stop_waiter(waiter):
        stopped = run([sys.executable, LAUNCHER, "stop", waiter["tab"], "--session-id", waiter["session_id"]])
        if stopped.returncode == 0:
            log("ok", "stop", "the waiter %s" % waiter["tab"])
        else:
            log("FAIL", "stop", "the waiter %s: %s" % (waiter["tab"], err(stopped)))

    def fail(step, error, waiter=None):
        log("FAIL", step, error)
        if waiter:
            stop_waiter(waiter)
        end_park(rec, park, {"step": step, "at": utc_now(), "error": error}, say)

    try:
        park_prompt = park["prompt"]
        try:
            with open(park_prompt, "w", encoding="utf-8") as handle:
                handle.write("Record directory: %s\nGoal slug: %s\n"
                             "Read `%s`, section `## The waiter`, and follow it.\n" % (rec, inputs["slug"], PARK_MD))
        except OSError as exc:
            return fail("prompt", str(exc))
        log("ok", "prompt", park_prompt)

        settings = None
        if orch:
            got = run([sys.executable, USAGE, "settings", "--cwd", inputs["repo"]])
            if got.returncode != 0 or not got.stdout.strip():
                return fail("settings", err(got))
            settings = got.stdout.strip().splitlines()[-1]
            log("ok", "settings", "crew-usage.py settings")

        argv_window = [sys.executable, LAUNCHER, "window", "--name", identity["name"], "--cwd", inputs["repo"],
                       "--prompt-file", park_prompt]
        for flag, value in (("--model", identity.get("model")), ("--group", identity.get("group")),
                            ("--terminal", identity.get("terminal")), ("--settings", settings)):
            if value:
                argv_window += [flag, value]
        started = run(argv_window)
        try:
            shown = json.loads(started.stdout.strip().splitlines()[-1]) if started.returncode == 0 else None
        except (ValueError, IndexError):
            shown = None
        if not isinstance(shown, dict) or not shown.get("tab") or not shown.get("session_id"):
            return fail("window", err(started) if started.returncode != 0 else "no JSON line from window")
        waiter = {"name": shown.get("session_name"), "session_id": shown["session_id"], "tab": shown["tab"],
                  "terminal": shown.get("terminal"), "tab_group": shown.get("tab_group"),
                  "model": shown.get("model"), "started_at": utc_now()}
        log("ok", "window", "%s %s" % (waiter["tab"], waiter["session_id"]))

        woke_early = False
        if os.environ.get("CREW_PARK_TEST_FAIL") == "waiter":
            return fail("record", "the test switch CREW_PARK_TEST_FAIL=waiter", waiter)
        wrote = record(rec, "run", "set", "park.waiter", json.dumps(waiter),
                       *park_conditions(park["at"], park["from_session"]))
        if wrote.returncode == NO_MATCH:
            # The park is gone: a wake came before this write. Who woke it?
            parks = load_state(rec).get("run", {}).get("parks") or []
            mine = [p for p in parks if isinstance(p, dict) and p.get("at") == park["at"]
                    and p.get("from_session") == park["from_session"]]
            woke = (mine[-1].get("woke") or {}) if mine else {}
            if woke.get("session_id") != waiter["session_id"]:
                log("ok", "record", "the park ended in session %s: no waiter write" % woke.get("session_id"))
                stop_waiter(waiter)
                return 0
            woke_early = True
            log("ok", "record", "the waiter woke already: no waiter write")
        elif wrote.returncode != 0:
            return fail("record", err(wrote), waiter)
        else:
            log("ok", "record", "run set park.waiter")

        if orch:
            for key in ("launch.tab", "launch.session_id"):
                value = waiter["tab"] if key == "launch.tab" else waiter["session_id"]
                done = orch_set(orch, key, value)
                if done.returncode != 0:
                    if woke_early:
                        # The waiter runs the run now: stop neither session.
                        log("FAIL", "orch", "%s: %s; the old session stays open" % (key, err(done)))
                        return 0
                    return fail("orch", "%s: %s" % (key, err(done)), waiter)
                log("ok", "orch", "set %s" % key)

        time.sleep(float(inputs.get("delay") or 0))
        log("ok", "wait", "%s seconds" % inputs.get("delay"))
        argv_stop = [sys.executable, LAUNCHER, "stop", identity["handle"], "--name", identity["name"]]
        if park.get("from_session"):
            argv_stop += ["--session-id", park["from_session"]]
        stopped = run(argv_stop)
        if stopped.returncode == 0:
            log("ok", "stop", "the old session %s" % identity["handle"])
        else:
            log("FAIL", "stop", "the old session %s: %s" % (identity["handle"], err(stopped)))
        return 0
    finally:
        say("%s end" % utc_now())


def cmd_unpark(argv):
    positional, opts = parse(argv, ("--by",), ())
    rec, = want(positional, 1, 'unpark <record-dir> [--by "<text>"]')
    out = Out()
    if not os.path.isfile(os.path.join(rec, "state.json")):
        out.fail("unpark", "no record at %s: state.json is missing" % rec)
        return out.finish()
    run_state = load_state(rec).get("run", {})
    park = run_state.get("park")
    if not isinstance(park, dict):
        out.ok("unpark", "no park")
        return out.finish()
    caller = session_id(run_state)
    conditions = park_conditions(park.get("at"), park.get("from_session"))
    entry = dict(park, woke={"at": utc_now(), "by": opts.get("--by"), "session_id": caller})
    held = [p for p in run_state.get("parks") or [] if isinstance(p, dict) and p.get("at") == park.get("at")
            and p.get("from_session") == park.get("from_session")]
    if held:
        out.ok("record", "run.parks already holds this park")
    elif not record_step(out, rec, "run append parks", ["run", "append", "parks", json.dumps(entry)] + conditions):
        return out.finish()
    if not record_step(out, rec, "run set park null", ["run", "set", "park", "null"] + conditions):
        return out.finish()

    waiter = park.get("waiter")
    is_waiter = isinstance(waiter, dict) and waiter.get("session_id") == caller
    if not isinstance(waiter, dict):
        out.ok("stop", "skipped, no waiter")
    elif is_waiter:
        out.ok("stop", "skipped, the waiter is this session")
    elif not waiter.get("tab") or not waiter.get("session_id"):
        out.ok("stop", "skipped, the waiter has no tab")
    else:
        stopped = run([sys.executable, LAUNCHER, "stop", waiter["tab"], "--session-id", waiter["session_id"]])
        if stopped.returncode == 0:
            out.ok("stop", "the waiter %s" % waiter["tab"])
        else:
            out.fail("stop", "the waiter %s: %s" % (waiter["tab"], err(stopped)))

    orch = run_state.get("orchestrator")
    if not orch:
        out.ok("orch", "skipped, no orchestrator")
    elif is_waiter:
        out.ok("orch", "skipped, the waiter is this session")
    else:
        for key, value in (("launch.session_id", caller), ("launch.tab", None)):
            done = orch_set(orch, key, value)
            if done.returncode == 0:
                out.ok("orch", "set %s" % key)
            else:
                out.fail("orch", "%s: %s" % (key, err(done)))
    out.ok("unpark", "run.park moved to run.parks")
    return out.finish()


# --- main -------------------------------------------------------------------

COMMANDS = {
    "launch-check": cmd_launch_check,
    "branch": cmd_branch,
    "verify": cmd_verify,
    "hand-over": cmd_hand_over,
    "cleanup": cmd_cleanup,
    "park": cmd_park,
    "park-helper": cmd_park_helper,
    "unpark": cmd_unpark,
}


def main(argv):
    if argv and argv[0] in ("--help", "-h"):
        print(__doc__)
        return 0
    try:
        if not argv or argv[0] not in COMMANDS:
            raise Usage("unknown subcommand: %s" % (argv[0] if argv else "none"))
        return COMMANDS[argv[0]](argv[1:])
    except Usage as exc:
        sys.stderr.write("crew-step.py: %s\n%s" % (exc, __doc__))
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

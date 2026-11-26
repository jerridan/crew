#!/usr/bin/env python3
"""Seeded test of crew-step.py.

usage: python3 skills/project-lead/scripts/test-crew-step.py

It builds temporary git repos, bare remotes and records in one temporary
directory. It copies crew-step.py into a fake plugin tree, beside a copy of
the real crew-record.py, a stub spend.py and a stub crew-orch.py. The stubs
log their arguments. A stub `gh` and a stub `git` wrapper sit first on PATH.
The stub `git` refuses a path that starts with a prefix in
$STUB_GIT_REFUSE, and runs the real git for every other call. HOME points
into the temporary directory, so nothing reads ~/.claude/crew.

The last line is `N of M checks passed`. The exit code is 0 only when N
equals M.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(HERE, "crew-step.py")
REAL_RECORD = os.path.join(HERE, "crew-record.py")
PY = sys.executable
REAL_GIT = shutil.which("git")

T = os.path.realpath(tempfile.mkdtemp(prefix="crew-step-test-"))
SLUG = "goal-abcd"
SESSION = "sess-test"
PR_URL = "https://github.com/o/r/pull/7"
NO_REMOTE = "launch check 3 (trigger 6): no remote"
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


# --- environment -----------------------------------------------------------

HOME = os.path.join(T, "home")
BIN = os.path.join(T, "bin")
os.makedirs(HOME)
os.makedirs(BIN)
open(os.path.join(HOME, ".gitconfig"), "w").close()

ENV = {k: v for k, v in os.environ.items()
       if not k.startswith("GIT_") and k not in ("CREW_RECORD_ROOT", "CREW_ORCH", "CLAUDE_CODE_SESSION_ID")}
ENV.update({
    "HOME": HOME,
    "GIT_CONFIG_NOSYSTEM": "1",
    "GIT_CONFIG_GLOBAL": os.path.join(HOME, ".gitconfig"),
    "GIT_AUTHOR_NAME": "Test",
    "GIT_AUTHOR_EMAIL": "test@example.com",
    "GIT_COMMITTER_NAME": "Test",
    "GIT_COMMITTER_EMAIL": "test@example.com",
    "CLAUDE_CODE_SESSION_ID": SESSION,
    "STUB_REAL_GIT": REAL_GIT,
})
STEP_ENV = dict(ENV, PATH=BIN + os.pathsep + ENV.get("PATH", ""))


def write(path, text, mode="w"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, mode) as f:
        f.write(text)


def stub(path, body):
    write(path, "#!" + PY + "\n" + body)
    os.chmod(path, 0o755)


LOGGER = """import json, os, sys
log = os.path.join(os.environ["STUB_LOG"], "%s.log")
with open(log, "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
code = int(os.environ.get("%s", "0"))
if code:
    sys.stderr.write("%s stub failed\\n")
sys.exit(code)
"""

stub(os.path.join(BIN, "gh"), """import json, os, sys
with open(os.path.join(os.environ["STUB_LOG"], "gh.log"), "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
code = int(os.environ.get("STUB_GH_EXIT", "0"))
if code:
    sys.stderr.write("gh: stub error\\n")
    sys.exit(code)
if sys.argv[1:3] == ["pr", "list"]:
    open_url = os.environ.get("STUB_GH_OPEN")
    print(json.dumps([{"url": open_url}] if open_url else []))
    sys.exit(0)
print("Creating draft pull request")
print("%s")
""" % PR_URL)

stub(os.path.join(BIN, "git"), """import os, sys
real = os.environ["STUB_REAL_GIT"]
refuse = [p for p in os.environ.get("STUB_GIT_REFUSE", "").split(":") if p]
for a in sys.argv[1:]:
    if any(a.startswith(p) for p in refuse):
        sys.stderr.write("fatal: refused by stub: %s\\n" % a)
        sys.exit(128)
os.execv(real, [real] + sys.argv[1:])
""")


# The stub window-watch.py logs its arguments, prints STUB_WW_OUT, and exits STUB_WW_EXIT.
WW_STUB = """import json, os, sys
with open(os.path.join(os.environ["STUB_LOG"], "window-watch.log"), "a") as f:
    f.write(json.dumps(sys.argv[1:]) + "\\n")
code = int(os.environ.get("STUB_WW_EXIT", "0"))
if code:
    sys.stderr.write("window-watch stub failed\\n")
    sys.exit(code)
print(os.environ.get("STUB_WW_OUT", "started pid 4242"))
"""


def make_plugin(name, record_wrapper=False):
    """A fake plugin tree. Return the path of its crew-step.py copy."""
    root = os.path.join(T, name)
    scripts = os.path.join(root, "skills", "project-lead", "scripts")
    orch = os.path.join(root, "skills", "orchestrator", "scripts")
    os.makedirs(scripts)
    os.makedirs(orch)
    if os.path.isfile(SRC):
        shutil.copy(SRC, os.path.join(scripts, "crew-step.py"))
    if record_wrapper:
        shutil.copy(REAL_RECORD, os.path.join(scripts, "crew-record-real.py"))
        write(os.path.join(scripts, "crew-record.py"), """import os, subprocess, sys
fail = os.environ.get("STUB_RECORD_FAIL")
if fail and fail in " ".join(sys.argv[1:]):
    sys.stderr.write("stub record failure\\n")
    sys.exit(1)
here = os.path.dirname(os.path.abspath(__file__))
sys.exit(subprocess.call([sys.executable, os.path.join(here, "crew-record-real.py")] + sys.argv[1:]))
""")
    else:
        shutil.copy(REAL_RECORD, os.path.join(scripts, "crew-record.py"))
    write(os.path.join(scripts, "spend.py"), LOGGER % ("spend", "STUB_SPEND_EXIT", "spend"))
    write(os.path.join(orch, "crew-orch.py"), LOGGER % ("orch", "STUB_ORCH_EXIT", "crew-orch"))
    window = os.path.join(root, "skills", "delivered-window", "scripts")
    os.makedirs(window)
    write(os.path.join(window, "window-watch.py"), WW_STUB)
    return os.path.join(scripts, "crew-step.py")


S = make_plugin("plugin")
S_WRAP = make_plugin("plugin-wrap", record_wrapper=True)


# --- helpers ---------------------------------------------------------------

def g(cwd, *args):
    r = subprocess.run([REAL_GIT, "-C", cwd] + list(args), env=ENV,
                       capture_output=True, text=True)
    return r.stdout.strip()


def g_raw(cwd, *args):
    return subprocess.run([REAL_GIT, "-C", cwd] + list(args), env=ENV,
                          capture_output=True, text=True).stdout


def rec_call(rec, *args):
    r = subprocess.run([PY, REAL_RECORD, rec] + list(args), env=ENV,
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit("seed failed: crew-record.py %s: %s" % (" ".join(args), r.stderr))


def step(*args, script=S, log=None, **extra):
    env = dict(STEP_ENV, **extra)
    env["STUB_LOG"] = log or T
    r = subprocess.run([PY, script] + list(args), env=env, capture_output=True, text=True)
    return r.returncode, r.stdout, r.stderr


def lines(out):
    return out.splitlines()


def has(out, prefix):
    return any(line.startswith(prefix) for line in lines(out))


def section(out, name):
    """The lines under `--- <name>`, up to the next marker."""
    body, inside = [], False
    for line in lines(out):
        if line in ["--- " + n for n in EVIDENCE]:
            inside = line == "--- " + name
            continue
        if inside:
            body.append(line)
    return body


EVIDENCE = ("log", "stat", "untracked", "criterion", "suite", "red", "pattern", "compactions",
            "deliverable branch", "listeners", "diff")


def markers(out):
    """The evidence marker lines. A diff's own `--- a/<path>` lines are not markers."""
    return [line for line in lines(out) if line in ["--- " + n for n in EVIDENCE]]


def state(rec):
    with open(os.path.join(rec, "state.json")) as f:
        return json.load(f)


def raw(path):
    if not os.path.exists(path):
        return None
    with open(path, "rb") as f:
        return f.read()


def wt_json(rec):
    path = os.path.join(rec, "worktrees.json")
    if not os.path.exists(path):
        return None
    with open(path) as f:
        return json.load(f)


def log_calls(d, name):
    path = os.path.join(d, name + ".log")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def creates(d):
    """The `gh pr create` calls the stub gh logged."""
    return [c for c in log_calls(d, "gh") if c[:2] == ["pr", "create"]]


def deliverable(rec, did="deliverable-1"):
    found = [x for x in state(rec).get("deliverables", []) if x.get("id") == did]
    return found[0] if len(found) == 1 else None


def package(rec, pid):
    return [x for x in state(rec).get("packages", []) if x.get("id") == pid][0]


def make_repo(name, remote=True, ignore=True):
    d = os.path.join(T, name)
    repo = os.path.join(d, "repo")
    os.makedirs(repo)
    subprocess.run([REAL_GIT, "init", "-q", "-b", "main", repo], env=ENV, check=True)
    write(os.path.join(repo, "README"), "hello\n")
    if ignore:
        write(os.path.join(repo, ".gitignore"), ".claude/\n")
    g(repo, "add", "-A")
    g(repo, "commit", "-qm", "init")
    bare = None
    if remote:
        bare = os.path.join(d, "remote.git")
        subprocess.run([REAL_GIT, "init", "-q", "--bare", bare], env=ENV, check=True)
        g(repo, "remote", "add", "origin", bare)
        g(repo, "push", "-q", "-u", "origin", "main")
        g(repo, "remote", "set-head", "origin", "main")
    return d, repo, bare


def commit(repo, path, text, msg):
    write(os.path.join(repo, path), text)
    g(repo, "add", path)
    g(repo, "commit", "-qm", msg)
    return g(repo, "rev-parse", "HEAD")


def make_record(d, repo, checkout=None, packages=(), deliverables=(), run=None):
    rec = os.path.join(d, "record")
    rec_call(rec, "init", "the goal", SLUG, SESSION)
    rec_call(rec, "run", "set", "repo", json.dumps(repo))
    if checkout:
        rec_call(rec, "run", "set", "checkout", json.dumps(checkout))
    for key, value in (run or {}).items():
        rec_call(rec, "run", "set", key, json.dumps(value))
    for p in packages:
        rec_call(rec, "package", "add", json.dumps(p))
    for x in deliverables:
        rec_call(rec, "deliverable", "add", json.dumps(x))
    return rec


def worktree_paths(repo):
    return [line[len("worktree "):] for line in g(repo, "worktree", "list", "--porcelain").splitlines()
            if line.startswith("worktree ")]


def script_exists(script=S):
    return os.path.isfile(script)


DEL_BRANCH = "crew/%s/deliverable-1" % SLUG


# --- launch-check: R1, R2, R3 ----------------------------------------------

d, repo, _ = make_repo("l1")
rec = make_record(d, repo)
rc, out, _ = step("launch-check", rec)
st = state(rec)
check("R1 default base passes, exit 0", rc == 0 and ("ok base: " + rec) in lines(out))
check("R1 default remote passes", has(out, "ok remote:"))
check("R1 default leaves no probe in git worktree list", "probe" not in g(repo, "worktree", "list"))
check("R1 default writes run.worktree_base", st["run"].get("worktree_base") == rec)
dec = (raw(os.path.join(rec, "decisions.md")) or b"").decode()
check("R1 default writes the decisions.md entry",
      "## Which worktree base does this run use?" in dec and ("Answer: " + rec) in dec
      and "Citation: full-path.md launch check 1:" in dec and "Confidence: high" in dec
      and "Route: precedent" in dec)
check("R1 default prints a record line per crew-record.py call",
      has(out, "ok record: run set") and has(out, "ok record: decision"))
check("R2 default base prints no ask collect line", not has(out, "ask collect:"))
check("R3 default writes no escalation", not st["run"].get("escalations"))

d, repo, _ = make_repo("l2")
rec = make_record(d, repo)
fallback = os.path.join(repo, ".claude", "worktrees", "crew", SLUG)
rc, out, _ = step("launch-check", rec, STUB_GIT_REFUSE=os.path.join(rec, "worktrees"))
st = state(rec)
check("R1 refused default base falls back and passes", rc == 0 and ("ok base: " + fallback) in lines(out))
check("R1 fallback leaves no probe in git worktree list", "probe" not in g(repo, "worktree", "list"))
check("R1 fallback writes run.worktree_base", st["run"].get("worktree_base") == fallback)
dec = (raw(os.path.join(rec, "decisions.md")) or b"").decode()
cite = [line for line in dec.splitlines() if line.startswith("Citation:")]
check("R1 fallback citation names both probes", bool(cite) and rec in cite[0] and fallback in cite[0])
check("R2 fallback base prints the ask collect line", has(out, "ask collect:"))
check("R3 fallback writes no escalation", not st["run"].get("escalations"))

d, repo, _ = make_repo("l2b", ignore=False)
rec = make_record(d, repo)
rc, out, _ = step("launch-check", rec, STUB_GIT_REFUSE=os.path.join(rec, "worktrees"))
check("R1 a fallback base that check-ignore does not match fails", rc == 1 and has(out, "FAIL base:"))
check("R1 not-ignored fallback leaves no probe", "probe" not in g(repo, "worktree", "list"))

d, repo, _ = make_repo("l3")
rec = make_record(d, repo)
rc, out, _ = step("launch-check", rec,
                  STUB_GIT_REFUSE=os.path.join(rec, "worktrees") + ":" + os.path.join(repo, ".claude"))
st = state(rec)
check("R1 both bases refused: exit 1 and FAIL base", rc == 1 and has(out, "FAIL base:"))
check("R1 both refused still prints the remote result", has(out, "ok remote:"))
check("R1 both refused leaves no probe", "probe" not in g(repo, "worktree", "list"))
check("R1 both refused writes no worktree_base", "worktree_base" not in st["run"])
check("R3 both refused writes no escalation", not st["run"].get("escalations"))

d, repo, _ = make_repo("l4", remote=False)
rec = make_record(d, repo)
rc, out, _ = step("launch-check", rec)
st = state(rec)
check("R1 no remote: exit 1 and FAIL remote", rc == 1 and has(out, "FAIL remote:"))
check("R1 no remote still passes the base", has(out, "ok base:") and st["run"].get("worktree_base") == rec)
check("R3 no remote writes no escalation", not st["run"].get("escalations"))


# --- branch: R4, R5, R6, PR2 -----------------------------------------------

d, repo, _ = make_repo("b1")
rec = make_record(d, repo)
head = g(repo, "rev-parse", "HEAD")
rc, out, _ = step("branch", rec, "deliverable-1")
dl = deliverable(rec)
check("R4 free: exit 0 and the branch is checked out",
      rc == 0 and g(repo, "branch", "--show-current") == DEL_BRANCH)
check("R4 free: step lines held, exists, switch",
      has(out, "ok held:") and has(out, "ok exists:") and has(out, "ok switch:"))
check("R4 free: the deliverable entry holds id, branch, base, state, pr_url",
      dl is not None and dl.get("branch") == DEL_BRANCH and dl.get("base") == head
      and dl.get("state") == "pending" and "pr_url" in dl and dl["pr_url"] is None)
check("R4 free: checkout_branch is the branch before the switch", dl is not None and dl.get("checkout_branch") == "main")
check("R4 free: run.checkout is run.repo", state(rec)["run"].get("checkout") == repo)
check("R12a the copy runs the real crew-record.py",
      raw(os.path.join(os.path.dirname(S), "crew-record.py")) == raw(REAL_RECORD) and dl is not None)
rc, out, _ = step("branch", rec, "deliverable-1")
check("PR2 a rerun prints already done and adds no second entry",
      rc == 0 and has(out, "ok switch: already done") and len(state(rec)["deliverables"]) == 1)

d, repo, _ = make_repo("b2")
rec = make_record(d, repo)
g(repo, "switch", "--detach", "-q", "HEAD")
rc, out, _ = step("branch", rec, "deliverable-1")
dl = deliverable(rec)
check("R4 detached start gives checkout_branch null",
      rc == 0 and dl is not None and "checkout_branch" in dl and dl["checkout_branch"] is None)

d, repo, _ = make_repo("b3")
rec = make_record(d, repo)
g(repo, "branch", DEL_BRANCH)
before = raw(os.path.join(rec, "state.json"))
rc, out, _ = step("branch", rec, "deliverable-1")
check("R4 an unrecorded existing branch is FAIL exists, exit 1", rc == 1 and has(out, "FAIL exists:"))
check("R4 FAIL exists writes nothing", raw(os.path.join(rec, "state.json")) == before
      and g(repo, "branch", "--show-current") == "main")

d, repo, _ = make_repo("b3b")
rec = make_record(d, repo)
rc, out, _ = step("branch", rec, "deliverable-1", "--branch", "feature/x")
dl = deliverable(rec)
check("R4 --branch names the branch", rc == 0 and g(repo, "branch", "--show-current") == "feature/x"
      and dl is not None and dl.get("branch") == "feature/x")

d, repo, _ = make_repo("b4")
main_head = g(repo, "rev-parse", "HEAD")
g(repo, "switch", "-q", "-c", "crew/other-run-9999/deliverable-1")
other_head = commit(repo, "other.txt", "other\n", "other run")
rec = make_record(d, repo)
rc, out, _ = step("branch", rec, "deliverable-1")
wt = os.path.join(rec, "worktrees", "deliverable-1")
dl = deliverable(rec)
entries = wt_json(rec) or {}
check("R5 held: exit 0 and held is detected", rc == 0 and has(out, "ok held: held"))
check("R5 held: the shared checkout stays on the other run's branch",
      g(repo, "branch", "--show-current") == "crew/other-run-9999/deliverable-1")
check("R5 held: the worktree starts at origin/HEAD, not the other branch",
      os.path.isdir(wt) and g(wt, "rev-parse", "HEAD") == main_head and main_head != other_head)
check("R5 held: the worktree is on the deliverable branch", os.path.isdir(wt) and g(wt, "branch", "--show-current") == DEL_BRANCH)
check("R5 held: worktrees.json holds the entry keyed by the deliverable id",
      entries.get("deliverable-1") == {"worktree": wt, "branch": DEL_BRANCH,
                                       "session_ids": [SESSION], "orphaned": False})
check("R5 held: run.checkout is the worktree", state(rec)["run"].get("checkout") == wt)
check("R5 held: checkout_branch null, checkout_restored null, base the start point",
      dl is not None and dl.get("checkout_branch") is None and dl.get("checkout_restored") is None
      and dl.get("base") == main_head)

d, repo, _ = make_repo("b5", remote=False)
g(repo, "switch", "-q", "-c", "crew/other-run-9999/deliverable-1")
rec = make_record(d, repo)
before = raw(os.path.join(rec, "state.json"))
rc, out, _ = step("branch", rec, "deliverable-1")
check("R5 held, no remote, no --start-point: FAIL start-point, exit 1", rc == 1 and has(out, "FAIL start-point:"))
check("R5 FAIL start-point cuts nothing", len(worktree_paths(repo)) == 1)
check("R5 FAIL start-point writes nothing", raw(os.path.join(rec, "state.json")) == before
      and wt_json(rec) is None)
rc, out, _ = step("branch", rec, "deliverable-1", "--start-point", "main")
check("R5 a rerun with --start-point cuts the worktree",
      rc == 0 and os.path.isdir(os.path.join(rec, "worktrees", "deliverable-1")))

d, repo, _ = make_repo("b5b", remote=False)
rec = make_record(d, repo)
rc, out, _ = step("branch", rec, "deliverable-1", "--held", "--start-point", "main")
check("R5 --held holds a free checkout", rc == 0 and g(repo, "branch", "--show-current") == "main"
      and os.path.isdir(os.path.join(rec, "worktrees", "deliverable-1")))

PKGS = [
    {"id": "p1", "deliverable": "deliverable-1", "territory": "alpha", "state": "pending",
     "file_set": ["src/a.py"], "ic_name": None, "base": None},
    {"id": "p2", "deliverable": "deliverable-1", "territory": "beta", "state": "pending",
     "file_set": ["src/b.py"], "ic_name": None, "base": None},
]
TERR = ["--territory", "alpha=ic-alpha-r1", "--territory", "beta=ic-beta-r1"]

d, repo, _ = make_repo("b6")
rec = make_record(d, repo, packages=PKGS)
rc, out, _ = step("branch", rec, "deliverable-1", *TERR)
entries = wt_json(rec) or {}
wa, wb = os.path.join(rec, "worktrees", "alpha"), os.path.join(rec, "worktrees", "beta")
check("R6 two territories: exit 0 and two worktrees", rc == 0 and os.path.isdir(wa) and os.path.isdir(wb))
check("R6 two worktrees.json entries keyed by IC name",
      entries.get("ic-alpha-r1") == {"worktree": wa, "branch": "crew/%s/alpha" % SLUG,
                                     "session_ids": [SESSION], "orphaned": False}
      and entries.get("ic-beta-r1") == {"worktree": wb, "branch": "crew/%s/beta" % SLUG,
                                        "session_ids": [SESSION], "orphaned": False})
check("R6 ic_name on each package", package(rec, "p1").get("ic_name") == "ic-alpha-r1"
      and package(rec, "p2").get("ic_name") == "ic-beta-r1")
heads = {g(repo, "rev-parse", b) for b in (DEL_BRANCH, "crew/%s/alpha" % SLUG, "crew/%s/beta" % SLUG)}
check("R6 all branches share one head", len(heads) == 1)
check("R6 worktree step lines name the slugs", has(out, "ok worktree: alpha") and has(out, "ok worktree: beta"))

d, repo, _ = make_repo("b6b")
rec = make_record(d, repo, packages=PKGS)
rc, out, _ = step("branch", rec, "deliverable-1", "--held", "--branch", "feature/y", *TERR)
entries = wt_json(rec) or {}
dwt = os.path.join(rec, "worktrees", "deliverable-1")
check("R6 held with territories keeps the deliverable entry",
      rc == 0 and "deliverable-1" in entries and "ic-alpha-r1" in entries and "ic-beta-r1" in entries)
check("R6 territories branch from the deliverable checkout's head",
      os.path.isdir(dwt) and g(os.path.join(rec, "worktrees", "alpha"), "rev-parse", "HEAD") == g(dwt, "rev-parse", "HEAD"))
check("R6 territory branches keep crew's names whatever --branch says",
      g(os.path.join(rec, "worktrees", "alpha"), "branch", "--show-current") == "crew/%s/alpha" % SLUG
      and g(dwt, "branch", "--show-current") == "feature/y")

d, repo, _ = make_repo("b7")
base = g(repo, "rev-parse", "HEAD")
g(repo, "switch", "-q", "-c", DEL_BRANCH)
promoted = commit(repo, "src/light.py", "light\n", "light path work")
rec = make_record(d, repo, checkout=repo, packages=PKGS, deliverables=[
    {"id": "deliverable-1", "branch": DEL_BRANCH, "base": base, "state": "pending",
     "pr_url": None, "checkout_branch": "main", "checkout_restored": None}])
rc, out, _ = step("branch", rec, "deliverable-1", *TERR)
check("PR2 promotion: exit 0 and the deliverable branch is already done",
      rc == 0 and has(out, "ok switch: already done"))
check("PR2 promotion: territories start at the promoted head",
      g(os.path.join(rec, "worktrees", "alpha"), "rev-parse", "HEAD") == promoted)
dl = deliverable(rec)
check("PR2 promotion keeps base and one entry, and the checkout stays on its branch",
      dl is not None and dl.get("base") == base and len(state(rec)["deliverables"]) == 1
      and g(repo, "branch", "--show-current") == DEL_BRANCH)

d, repo, _ = make_repo("b8")
head = g(repo, "rev-parse", "HEAD")
rec = make_record(d, repo)
rc, out, _ = step("branch", rec, "deliverable-1", script=S_WRAP, STUB_RECORD_FAIL="set checkout")
check("PR2 a crew-record.py failure prints FAIL record and exits 1",
      rc == 1 and has(out, "FAIL record:") and deliverable(rec) is not None)
rc, out, _ = step("branch", rec, "deliverable-1", script=S_WRAP)
dl = deliverable(rec)
check("PR2 the rerun after a record failure completes",
      rc == 0 and g(repo, "branch", "--show-current") == DEL_BRANCH
      and state(rec)["run"].get("checkout") == repo and len(state(rec)["deliverables"]) == 1
      and dl.get("base") == head)

d, repo, _ = make_repo("b9")
rec = make_record(d, repo, packages=PKGS)
rc, out, _ = step("branch", rec, "deliverable-1", *TERR, script=S_WRAP, STUB_RECORD_FAIL="p1 set ic_name")
check("PR2 an ic_name write failure after a worktree add exits 1",
      rc == 1 and os.path.isdir(os.path.join(rec, "worktrees", "alpha")))
rc, out, _ = step("branch", rec, "deliverable-1", *TERR, script=S_WRAP)
check("PR2 the rerun reuses the worktree and writes ic_name",
      rc == 0 and has(out, "ok worktree: alpha: already done")
      and package(rec, "p1").get("ic_name") == "ic-alpha-r1"
      and package(rec, "p2").get("ic_name") == "ic-beta-r1")

d, repo, _ = make_repo("b10")
rec = make_record(d, repo, packages=PKGS)
rc, out, _ = step("branch", rec, "deliverable-1", *TERR,
                  STUB_GIT_REFUSE=os.path.join(rec, "worktrees", "beta"))
check("PR2 a refused second territory: FAIL worktree, exit 1",
      rc == 1 and has(out, "FAIL worktree:") and os.path.isdir(os.path.join(rec, "worktrees", "alpha")))
rc, out, _ = step("branch", rec, "deliverable-1", *TERR)
entries = wt_json(rec) or {}
check("PR2 the rerun after a refused worktree completes",
      rc == 0 and os.path.isdir(os.path.join(rec, "worktrees", "beta"))
      and "ic-alpha-r1" in entries and "ic-beta-r1" in entries)


# --- verify: R7 to R14, PR1, PR5 -------------------------------------------

FILE_SET = ["src/a.py", "tests/test_a.py"]


def seed_verify(name, compactions=None, ic_name=None):
    d, repo, _ = make_repo(name, remote=False)
    base = g(repo, "rev-parse", "HEAD")
    g(repo, "switch", "-q", "-c", DEL_BRANCH)
    run = {"compactions": compactions} if compactions is not None else None
    rec = make_record(d, repo, checkout=repo, run=run, packages=[
        {"id": "p1", "deliverable": "deliverable-1", "territory": "alpha", "state": "in-flight",
         "file_set": FILE_SET, "ic_name": ic_name, "base": base}],
        deliverables=[{"id": "deliverable-1", "branch": DEL_BRANCH, "base": base, "state": "in-flight",
                       "pr_url": None, "checkout_branch": "main", "checkout_restored": None}])
    rec_call(rec, "decision", "precedent", "Seed entry", "--answer", "a", "--citation", "c",
             "--confidence", "high")
    return d, repo, rec, base


d, repo, rec, base = seed_verify("v1")
commit(repo, "src/a.py", "x = 1\n", "add a")
st_before, dec_before = raw(os.path.join(rec, "state.json")), raw(os.path.join(rec, "decisions.md"))
rc, out, _ = step("verify", rec, "p1", "--no-suite")
check("R7 clean tree passes, exit 0", rc == 0 and has(out, "ok clean-tree:") and has(out, "ok file-set:"))
check("R7 prints the log and the stat", any("add a" in x for x in section(out, "log"))
      and any("src/a.py" in x for x in section(out, "stat")) and has(out, "ok log:"))
mk = markers(out)
want_diff = g_raw(repo, "diff", base + "..HEAD")
patch = os.path.join(rec, "diffs", "p1-verify.patch")
check("R14 verify prints no diff body by default", "--- diff" not in mk and "--- diff\n" not in out)
check("R14 the whole diff is in <record>/diffs/<package>-verify.patch",
      (raw(patch) or b"").decode() == want_diff and bool(want_diff))
check("R14 ok diff: line names the patch file and its line count",
      "ok diff: %s (%d lines)" % (patch, len(want_diff.splitlines())) in lines(out))
rc2, out2, _ = step("verify", rec, "p1", "--no-suite", "--diff")
mk2 = markers(out2)
check("R14 --diff prints --- diff as the last marker", bool(mk2) and mk2[-1] == "--- diff")
body = out2.split("--- diff\n", 1)[1] if "--- diff\n" in out2 else None
check("R14 the --diff body equals git diff <base>..HEAD", body == want_diff)
check("R14 --diff still writes the patch file", (raw(patch) or b"").decode() == want_diff)
check("R14 state.json and decisions.md are byte-equal after verify",
      raw(os.path.join(rec, "state.json")) == st_before and raw(os.path.join(rec, "decisions.md")) == dec_before)
check("R9 --no-suite prints ok suite: no suite", "ok suite: no suite" in lines(out))
check("R9 no --criterion runs no command", has(out, "ok criterion: not given") and "--- criterion" not in mk)
check("R13 no compactions prints ok compactions: none", "ok compactions: none" in lines(out))

d, repo, rec, base = seed_verify("v2")
commit(repo, "src/a.py", "x = 1\n", "add a")
write(os.path.join(repo, "README"), "changed\n")
rc, out, _ = step("verify", rec, "p1", "--no-suite")
check("R7 a modified tracked file fails", rc == 1 and any(x.startswith("FAIL clean-tree:") and "README" in x
                                                         for x in lines(out)))

d, repo, rec, base = seed_verify("v3")
commit(repo, "src/a.py", "x = 1\n", "add a")
write(os.path.join(repo, "tests", "test_a.py"), "untracked\n")
rc, out, _ = step("verify", rec, "p1", "--no-suite")
check("R7 an untracked file in the set fails", rc == 1 and any(
    x.startswith("FAIL clean-tree:") and "tests/test_a.py" in x for x in lines(out)))

d, repo, rec, base = seed_verify("v4")
commit(repo, "src/a.py", "x = 1\n", "add a")
write(os.path.join(repo, "notes.txt"), "mine\n")
rc, out, _ = step("verify", rec, "p1", "--no-suite")
check("R7 an untracked file outside the set passes with a report line",
      rc == 0 and has(out, "ok clean-tree:") and any("notes.txt" in x for x in section(out, "untracked")))

d, repo, rec, base = seed_verify("v5")
commit(repo, "src/a.py", "x = 1\n", "add a")
commit(repo, "other.py", "y\n", "stray")
rc, out, _ = step("verify", rec, "p1", "--no-suite")
check("R7 a committed file outside the set fails and is named",
      rc == 1 and any(x.startswith("FAIL file-set:") and "other.py" in x for x in lines(out)))

d, repo, rec, base = seed_verify("v6")
commit(repo, "other.py", "y\n", "stray")
write(os.path.join(repo, "README"), "changed\n")
rc, out, _ = step("verify", rec, "p1", "--no-suite")
check("R8 a dirty tree and an out-of-set file both FAIL in one call, exit 1",
      rc == 1 and has(out, "FAIL clean-tree:") and has(out, "FAIL file-set:"))

d, repo, rec, base = seed_verify("v7")
commit(repo, "src/a.py", "x = 1\n", "add a")
rc, out, _ = step("verify", rec, "p1", "--criterion", "echo crit-out", "--no-suite")
check("R9 a passing criterion passes and prints its output",
      rc == 0 and "ok criterion: exit 0" in lines(out) and "crit-out" in section(out, "criterion"))
rc, out, _ = step("verify", rec, "p1", "--criterion", "seq 1 100; exit 3", "--no-suite")
crit = section(out, "criterion")
check("R9 a failing criterion is FAIL with its exit code", rc == 1 and has(out, "FAIL criterion: exit 3"))
check("R9 the criterion evidence is the last 40 lines", "100" in crit and "61" in crit and "60" not in crit)
rc, out, _ = step("verify", rec, "p1", "--suite", "exit 4")
check("R9 a failing suite is FAIL", rc == 1 and has(out, "FAIL suite: exit 4"))
rc, out, err = step("verify", rec, "p1", "--suite", "true", "--no-suite")
check("R9 --suite with --no-suite is a usage error", rc == 2 and script_exists())

d, repo, rec, base = seed_verify("v8")
red = commit(repo, "tests/test_a.py", "test\n", "red test")
green = commit(repo, "src/a.py", "x = 1\n", "fix")
CRIT = "test -f src/a.py"
rc, out, _ = step("verify", rec, "p1", "--criterion", CRIT, "--no-suite", "--red", red)
check("R10 a red commit that fails passes", rc == 0 and has(out, "ok red:"))
check("R10 the branch is back after a passing red check", g(repo, "branch", "--show-current") == DEL_BRANCH)
rc, out, _ = step("verify", rec, "p1", "--criterion", CRIT, "--no-suite", "--red", green)
check("R10 a criterion that passes at the red commit is FAIL red", rc == 1 and has(out, "FAIL red:"))
check("R10 the branch is back after a FAIL red", g(repo, "branch", "--show-current") == DEL_BRANCH)
rc, out, _ = step("verify", rec, "p1", "--no-suite", "--red", red)
check("R10 --red without --criterion exits 2", rc == 2 and script_exists())
write(os.path.join(repo, "README"), "dirty\n")
reflog = g(repo, "reflog")
rc, out, _ = step("verify", rec, "p1", "--criterion", CRIT, "--no-suite", "--red", red)
check("R10 a dirty tree makes FAIL red and no switch",
      rc == 1 and has(out, "FAIL red:") and g(repo, "reflog") == reflog
      and g(repo, "branch", "--show-current") == DEL_BRANCH)
g(repo, "checkout", "-q", "--", "README")
reflog = g(repo, "reflog")
rc, out, _ = step("verify", rec, "p1", "--criterion", "echo more >> README; " + CRIT, "--no-suite", "--red", red)
check("PR5 a criterion that dirties the tree at HEAD makes FAIL red before the switch",
      rc == 1 and any(x.startswith("FAIL red:") and "before the switch" in x for x in lines(out))
      and g(repo, "reflog") == reflog and g(repo, "branch", "--show-current") == DEL_BRANCH)

d, repo, rec, base = seed_verify("v9")
commit(repo, "src/a.py", "# TODO one\nx = 1\n# TODO two\n", "add a")
rc, out, _ = step("verify", rec, "p1", "--no-suite", "--pattern", "TODO")
hits = section(out, "pattern")
check("R11 a pattern with 2 hits prints the count and both lines, exit 0",
      rc == 0 and "ok pattern: 2 hits" in lines(out)
      and any("TODO one" in x for x in hits) and any("TODO two" in x for x in hits))
rc, out, _ = step("verify", rec, "p1", "--no-suite", "--pattern", "NOPE_XYZ")
check("R11 a pattern with 0 hits, exit 0", rc == 0 and "ok pattern: 0 hits" in lines(out))

COMPACTIONS = [
    {"session_id": "s1", "agent_id": "a1", "agent": "ic-alpha-r1", "trigger": "auto", "at": "2026-01-01T00:00:00Z"},
    {"session_id": "s0", "agent_id": None, "agent": None, "trigger": "manual", "at": "2026-01-02T00:00:00Z"},
    {"session_id": "s2", "agent_id": "a2", "agent": "ic-other-r1", "trigger": "auto", "at": "2026-01-03T00:00:00Z"},
]
d, repo, rec, base = seed_verify("v10", compactions=COMPACTIONS, ic_name="ic-alpha-r1")
commit(repo, "src/a.py", "x = 1\n", "add a")
rc, out, _ = step("verify", rec, "p1", "--no-suite")
comp = section(out, "compactions")
check("R13 prints the IC's compaction", any("ic-alpha-r1" in x and "2026-01-01" in x for x in comp))
check("R13 prints the agent:null compaction as the project lead's own",
      any(x.startswith("project lead") and "2026-01-02" in x for x in comp))
check("R13 skips another agent's compaction and never fails",
      not any("ic-other-r1" in x for x in comp) and rc == 0 and "ok compactions: 2 entries" in lines(out))

# The full path: the IC worktree and run.checkout hold different commits.
d, repo, _ = make_repo("v11", remote=False)
base = g(repo, "rev-parse", "HEAD")
g(repo, "switch", "-q", "-c", DEL_BRANCH)
rec = os.path.join(d, "record")
icwt = os.path.join(rec, "worktrees", "alpha")
g(repo, "worktree", "add", "-q", icwt, "-b", "crew/%s/alpha" % SLUG)
rec = make_record(d, repo, checkout=repo, packages=[
    {"id": "p1", "deliverable": "deliverable-1", "territory": "alpha", "state": "in-flight",
     "file_set": ["src/a.py"], "ic_name": "ic-alpha-r1", "base": base}],
    deliverables=[{"id": "deliverable-1", "branch": DEL_BRANCH, "base": base, "state": "in-flight",
                   "pr_url": None, "checkout_branch": "main", "checkout_restored": None}])
write(os.path.join(rec, "worktrees.json"), json.dumps({"ic-alpha-r1": {
    "worktree": icwt, "branch": "crew/%s/alpha" % SLUG, "session_ids": [SESSION], "orphaned": False}}))
commit(icwt, "src/a.py", "ic work\n", "ic commit")
commit(repo, "lead.txt", "stray\n", "stray commit on the deliverable branch")
rc, out, _ = step("verify", rec, "p1", "--ic-branch", "--criterion", "test -f src/a.py", "--no-suite", "--diff")
body = out.split("--- diff\n", 1)[1] if "--- diff\n" in out else None
check("R12 a worktree on its own branch passes", rc == 0 and has(out, "ok ic-branch:"))
check("PR1 --ic-branch runs the criterion in the IC worktree", "ok criterion: exit 0" in lines(out))
check("PR1 --ic-branch diffs the IC worktree", body == g_raw(icwt, "diff", base + "..HEAD") and "ic work" in (body or ""))
check("R12 a commit on run.checkout's branch prints under --- deliverable branch",
      any("stray commit" in x for x in section(out, "deliverable branch")))
rc, out, _ = step("verify", rec, "p1", "--ic-branch", "--repo", repo, "--no-suite")
check("PR1 a --repo other than the IC worktree exits 2", rc == 2 and script_exists())
g(icwt, "switch", "-q", "-c", "elsewhere")
rc, out, _ = step("verify", rec, "p1", "--ic-branch", "--no-suite")
check("R12 a worktree switched to another branch fails", rc == 1 and has(out, "FAIL ic-branch:"))


# --- hand-over and cleanup: R15 to R18, PR3, PR4 ---------------------------

def seed_handover(name, remote=True, orchestrator=True, held_ic=False):
    d, repo, bare = make_repo(name, remote=remote)
    base = g(repo, "rev-parse", "HEAD")
    g(repo, "switch", "-q", "-c", DEL_BRANCH)
    run = {"orchestrator": {"name": "orch-x", "item": "item-3"}} if orchestrator else None
    rec = make_record(d, repo, checkout=repo, run=run, deliverables=[
        {"id": "deliverable-1", "branch": DEL_BRANCH, "base": base, "state": "in-flight",
         "pr_url": None, "checkout_branch": "main", "checkout_restored": None}])
    commit(repo, "src/a.py", "x = 1\n", "the work")
    if held_ic:
        icwt = os.path.join(rec, "worktrees", "alpha")
        g(repo, "worktree", "add", "-q", icwt, "-b", "crew/%s/alpha" % SLUG)
        write(os.path.join(rec, "worktrees.json"), json.dumps({"ic-alpha-r1": {
            "worktree": icwt, "branch": "crew/%s/alpha" % SLUG, "session_ids": [SESSION], "orphaned": False}}))
    bodyfile = os.path.join(d, "body.md")
    write(bodyfile, "The body.\n")
    return d, repo, bare, rec, bodyfile


d, repo, bare, rec, bodyfile = seed_handover("h1")
head = g(repo, "rev-parse", "HEAD")
body_before = raw(bodyfile)
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "My title", log=d)
st = state(rec)
dl = deliverable(rec)
gh = creates(d)
check("R15 hand-over exits 0", rc == 0)
check("R15 the branch is on the remote", g(bare, "rev-parse", DEL_BRANCH) == head)
check("R15 gh saw --draft, the title and the body file",
      len(gh) == 1 and gh[0][:2] == ["pr", "create"] and "--draft" in gh[0]
      and gh[0][gh[0].index("--title") + 1] == "My title"
      and gh[0][gh[0].index("--body-file") + 1] == bodyfile
      and gh[0][gh[0].index("--head") + 1] == DEL_BRANCH)
check("R15 state.json holds pr_url, run_state delivered and review_pending",
      dl.get("pr_url") == PR_URL and dl.get("state") == "draft-pr-opened"
      and st["run"].get("run_state") == "delivered"
      and (st["run"].get("review_pending") or {}).get("head") == head)
orch = log_calls(d, "orch")
check("R15 the stub orchestrator saw both calls",
      ["--orch", "orch-x", "item", "item-3", "pr", PR_URL] in orch
      and ["--orch", "orch-x", "stage", "item-3", "review"] in orch)
check("R15 the stub spend.py saw --write", [rec, repo, "--write"] in log_calls(d, "spend"))
check("watch: window-watch.py start <record> --hold ran once, after the PR opened",
      log_calls(d, "window-watch") == [["start", rec, "--hold"]] and has(out, "ok watch:"))
check("watch: the step line comes after orch and before the listeners",
      [x.split(":")[0] for x in lines(out) if x.startswith(("ok orch", "ok watch"))] == ["ok orch", "ok orch", "ok watch"])
check("R15 prints the listeners evidence", "--- listeners" in markers(out) and has(out, "ok listeners:"))
check("R18 a clean tree with checkout_branch switches back and writes true",
      g(repo, "branch", "--show-current") == "main" and dl.get("checkout_restored") is True)
check("R19 the body file is unchanged", raw(bodyfile) == body_before)
changed_at, pending = dl.get("state_changed_at"), st["run"].get("review_pending")
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "My title", log=d)
dl = deliverable(rec)
check("PR4 a rerun skips push, pr and deliver as already done",
      rc == 0 and "ok push: already done" in lines(out) and "ok pr: already done" in lines(out)
      and "ok deliver: already done" in lines(out))
check("PR4 a rerun makes one gh pr create call and one deliver write in all",
      len(creates(d)) == 1 and dl.get("state_changed_at") == changed_at
      and state(rec)["run"].get("review_pending") == pending)
check("PR4 a rerun runs orch again", len(log_calls(d, "orch")) == 4)
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "My title", log=d,
                  STUB_WW_OUT="already running")
check("watch: a rerun on a live watcher is ok watch: already running, exit 0",
      rc == 0 and "ok watch: already running" in lines(out) and len(log_calls(d, "window-watch")) == 3)

d, repo, bare, rec, bodyfile = seed_handover("h2", remote=False, orchestrator=False)
rc, out, _ = step("hand-over", rec, "deliverable-1", "--local", log=d)
dl = deliverable(rec)
check("R15 --local: exit 0 and work-complete with pr_url null",
      rc == 0 and dl.get("state") == "work-complete" and dl.get("pr_url") is None
      and state(rec)["run"].get("run_state") == "delivered")
check("R15 --local: no push and no gh call", not has(out, "FAIL push") and log_calls(d, "gh") == [])
check("watch: --local skips the watch and calls window-watch.py never",
      "ok watch: skipped, --local" in lines(out) and log_calls(d, "window-watch") == [])
check("R15 --local: checkout_restored is written", dl.get("checkout_restored") is True)

d, repo, bare, rec, bodyfile = seed_handover("h3", held_ic=True)
icwt = os.path.join(rec, "worktrees", "alpha")
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "T", log=d, STUB_ORCH_EXIT="1")
check("R15 a failed crew-orch.py call: FAIL orch, exit 1", rc == 1 and has(out, "FAIL orch:"))
check("R15 after FAIL orch the spend, removal and restore steps still ran",
      log_calls(d, "spend") != [] and not os.path.isdir(icwt) and wt_json(rec) == {}
      and deliverable(rec).get("checkout_restored") is True)

d, repo, bare, rec, bodyfile = seed_handover("h4", held_ic=True)
icwt = os.path.join(rec, "worktrees", "alpha")
shutil.rmtree(bare)
before = raw(os.path.join(rec, "state.json"))
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "T", log=d)
check("R16 a refused push with no entry prints FAIL push and escalation: none",
      rc == 1 and has(out, "FAIL push:") and "escalation: none" in lines(out))
check("R16 a refused push calls no gh and leaves state.json unchanged",
      log_calls(d, "gh") == [] and raw(os.path.join(rec, "state.json")) == before)
check("R16 a refused push runs nothing after it", os.path.isdir(icwt) and log_calls(d, "spend") == [])

d, repo, bare, rec, bodyfile = seed_handover("h5")
shutil.rmtree(bare)
rec_call(rec, "escalation", "add", NO_REMOTE, "No remote: keep it local?")
rec_call(rec, "escalation", "answer", "0", "Keep the work local")
before = raw(os.path.join(rec, "state.json"))
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "T", log=d)
check("R16 a refused push with an entry prints its answer",
      rc == 1 and has(out, "FAIL push:") and "escalation: Keep the work local" in lines(out))
check("R16 with an entry: no gh call and state.json unchanged",
      log_calls(d, "gh") == [] and raw(os.path.join(rec, "state.json")) == before)

d, repo, bare, rec, bodyfile = seed_handover("h6")
before = raw(os.path.join(rec, "state.json"))
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "T", log=d, STUB_GH_EXIT="1")
check("R16 a gh that exits 1 prints FAIL pr and leaves state.json unchanged",
      rc == 1 and has(out, "FAIL pr:") and has(out, "escalation:")
      and raw(os.path.join(rec, "state.json")) == before)

d, repo, bare, rec, bodyfile = seed_handover("h7")
g(repo, "remote", "rename", "origin", "a")
g(repo, "remote", "add", "b", bare)
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "T", log=d)
check("R15 two remotes and no origin is FAIL push: no origin", rc == 1 and "FAIL push: no origin" in lines(out))

d, repo, bare, rec, bodyfile = seed_handover("h8", held_ic=True)
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "T", log=d, STUB_SPEND_EXIT="1")
check("PR4 a failed spend.py prints FAIL spend and the sequence goes on",
      rc == 1 and has(out, "FAIL spend:") and wt_json(rec) == {}
      and deliverable(rec).get("checkout_restored") is True)

d9, repo9, bare9, rec9, body9 = seed_handover("h8b", held_ic=True)
rc, out, _ = step("hand-over", rec9, "deliverable-1", "--body", body9, "--title", "T", log=d9, STUB_WW_EXIT="1")
check("watch: a failing window-watch.py prints FAIL watch and the cleanup steps still run",
      rc == 1 and has(out, "FAIL watch:") and log_calls(d9, "spend") != [] and wt_json(rec9) == {}
      and deliverable(rec9).get("checkout_restored") is True)

d, repo, bare, rec, bodyfile = seed_handover("h9")
rc, out, _ = step("hand-over", rec, "deliverable-1", "--local", "--body", bodyfile, log=d)
check("hand-over --local with --body is a usage error", rc == 2 and script_exists())
rc, out, _ = step("no-such-step", rec, log=d)
check("an unknown subcommand is a usage error", rc == 2 and script_exists())

# cleanup on a delivered record: removal order, refusal, ownership, restore.
d, repo, bare, rec, bodyfile = seed_handover("c1", orchestrator=False)
head = g(repo, "rev-parse", "HEAD")
rec_call(rec, "deliver", "deliverable-1", "draft-pr-opened", "--pr-url", PR_URL, "--review-head", head)
wts = os.path.join(rec, "worktrees")
dwt, a_wt, b_wt, stray = (os.path.join(wts, x) for x in ("deliverable-1", "alpha", "beta", "stray"))
g(repo, "worktree", "add", "-q", dwt, "-b", "crew/%s/held" % SLUG)
g(dwt, "worktree", "add", "-q", a_wt, "-b", "crew/%s/alpha" % SLUG)
g(dwt, "worktree", "add", "-q", b_wt, "-b", "crew/%s/beta" % SLUG)
g(repo, "worktree", "add", "-q", stray, "-b", "not-ours")
write(os.path.join(b_wt, "uncommitted.txt"), "only here\n")
write(os.path.join(rec, "worktrees.json"), json.dumps({
    "deliverable-1": {"worktree": dwt, "branch": "crew/%s/held" % SLUG, "session_ids": [SESSION], "orphaned": False},
    "ic-alpha-r1": {"worktree": a_wt, "branch": "crew/%s/alpha" % SLUG, "session_ids": [SESSION], "orphaned": False},
    "ic-beta-r1": {"worktree": b_wt, "branch": "crew/%s/beta" % SLUG, "session_ids": [SESSION], "orphaned": False},
}))
dl_before = deliverable(rec)
pending = state(rec)["run"].get("review_pending")
rc, out, _ = step("cleanup", rec, "deliverable-1", log=d)
entries = wt_json(rec) or {}
check("R17 a clean worktree is removed and its entry deleted",
      ("ok worktree-remove: " + a_wt) in lines(out) and not os.path.isdir(a_wt) and "ic-alpha-r1" not in entries)
refusal = [x for x in lines(out) if x.startswith("FAIL worktree-remove: " + b_wt + ": ")]
check("R17 a worktree with an uncommitted file is refused with git's message, entry kept",
      rc == 1 and len(refusal) == 1 and len(refusal[0]) > len("FAIL worktree-remove: " + b_wt + ": ")
      and os.path.isdir(b_wt) and "ic-beta-r1" in entries)
check("R17 a worktree path absent from worktrees.json survives", os.path.isdir(stray))
order = [i for i, x in enumerate(lines(out)) if x.startswith("ok worktree-remove: ") or x.startswith("FAIL worktree-remove: ")]
targets = [lines(out)[i] for i in order]
check("R17 IC worktrees go first and the deliverable checkout last",
      len(targets) == 3 and dwt in targets[-1])
check("PR3 cleanup leaves the deliverable state and review_pending unchanged",
      deliverable(rec).get("state") == "draft-pr-opened"
      and deliverable(rec).get("state_changed_at") == dl_before.get("state_changed_at")
      and state(rec)["run"].get("review_pending") == pending)
check("PR3 cleanup runs spend and restores the checkout",
      log_calls(d, "spend") != [] and deliverable(rec).get("checkout_restored") is True
      and g(repo, "branch", "--show-current") == "main")
if os.path.exists(os.path.join(b_wt, "uncommitted.txt")):
    os.remove(os.path.join(b_wt, "uncommitted.txt"))
rc, out, _ = step("cleanup", rec, "deliverable-1", log=d)
check("R17 worktrees.json ends as {} after a full clean-up",
      rc == 0 and wt_json(rec) == {} and not os.path.isdir(b_wt) and not os.path.isdir(dwt))
check("R18 restore on a restored checkout is already done", "ok restore: already done" in lines(out))

d, repo, bare, rec, bodyfile = seed_handover("c2", orchestrator=False)
write(os.path.join(repo, "README"), "dirty\n")
rc, out, _ = step("cleanup", rec, "deliverable-1", log=d)
cr = deliverable(rec).get("checkout_restored")
check("R18 a dirty tree writes one sentence as checkout_restored",
      isinstance(cr, str) and "dirty" in cr and g(repo, "branch", "--show-current") == DEL_BRANCH)

d, repo, bare, rec, bodyfile = seed_handover("c3", orchestrator=False)
rec_call(rec, "deliverable", "deliverable-1", "set", "checkout_branch", "null")
rc, out, _ = step("cleanup", rec, "deliverable-1", log=d)
check("R18 checkout_branch null does nothing and writes nothing",
      rc == 0 and has(out, "ok restore:") and deliverable(rec).get("checkout_restored") is None
      and g(repo, "branch", "--show-current") == DEL_BRANCH)

d, repo, bare, rec, bodyfile = seed_handover("c4", orchestrator=False)
rc, out, _ = step("cleanup", rec, "deliverable-1", log=d)
check("R17 a run with no worktrees.json removes nothing", rc == 0 and has(out, "ok worktree-remove:")
      and wt_json(rec) is None)


# --- the bot's round: pr-comments-r1 ---------------------------------------

# Item 2: a path that git quotes (non-ASCII, a space) still matches the file set.
NASTY = "src/é ü.py"
d, repo, _ = make_repo("q1", remote=False)
qbase = g(repo, "rev-parse", "HEAD")
g(repo, "switch", "-q", "-c", DEL_BRANCH)
rec = make_record(d, repo, checkout=repo, packages=[
    {"id": "p1", "deliverable": "deliverable-1", "territory": "alpha", "state": "in-flight",
     "file_set": [NASTY, "tests/ö.py"], "ic_name": None, "base": qbase}],
    deliverables=[{"id": "deliverable-1", "branch": DEL_BRANCH, "base": qbase, "state": "in-flight",
                   "pr_url": None, "checkout_branch": "main", "checkout_restored": None}])
commit(repo, NASTY, "x = 1\n", "add a quoted name")
rc, out, _ = step("verify", rec, "p1", "--no-suite")
check("a committed file with a quoted name in the file set passes file-set",
      rc == 0 and "ok file-set: 1 files, all in the file set" in lines(out))
write(os.path.join(repo, "tests", "ö.py"), "untracked\n")
rc, out, _ = step("verify", rec, "p1", "--no-suite")
check("an untracked file with a quoted name in the set fails clean-tree under its real name",
      rc == 1 and any(x.startswith("FAIL clean-tree:") and "tests/ö.py" in x for x in lines(out)))
os.remove(os.path.join(repo, "tests", "ö.py"))
write(os.path.join(repo, "notes ä.txt"), "mine\n")
rc, out, _ = step("verify", rec, "p1", "--no-suite")
check("an untracked quoted name outside the set is reported under its real name",
      rc == 0 and "notes ä.txt" in section(out, "untracked"))
os.remove(os.path.join(repo, "notes ä.txt"))
commit(repo, "stray é.py", "y\n", "stray")
rc, out, _ = step("verify", rec, "p1", "--no-suite")
check("a committed quoted name outside the set is named in FAIL file-set",
      rc == 1 and any(x.startswith("FAIL file-set:") and "stray é.py" in x for x in lines(out)))

# Item 3: a bad --start-point in the held case writes nothing.
d, repo, _ = make_repo("sp1", remote=False)
rec = make_record(d, repo)
before = raw(os.path.join(rec, "state.json"))
rc, out, _ = step("branch", rec, "deliverable-1", "--held", "--start-point", "no-such-ref")
check("a held call with a bad --start-point is FAIL start-point, exit 1", rc == 1 and has(out, "FAIL start-point:"))
check("a bad --start-point writes no worktrees.json and no state",
      wt_json(rec) is None and raw(os.path.join(rec, "state.json")) == before
      and len(worktree_paths(repo)) == 1)
rc, out, _ = step("branch", rec, "deliverable-1", "--held", "--start-point", "main")
check("a rerun with a good --start-point cuts the worktree",
      rc == 0 and os.path.isdir(os.path.join(rec, "worktrees", "deliverable-1")))

# Item 4: the restore failure path.
d, repo, bare, rec, bodyfile = seed_handover("rf1", orchestrator=False)
rc, out, _ = step("cleanup", rec, "deliverable-1", log=d, STUB_GIT_REFUSE="main")
cr = deliverable(rec).get("checkout_restored")
check("a failed switch back is FAIL restore, exit 1", rc == 1 and has(out, "FAIL restore: switch to main failed"))
check("a failed switch back writes the sentence to checkout_restored",
      isinstance(cr, str) and cr.startswith("switch to main failed"))

# Items 5: a rerun after a failed deliver write reuses the open PR.
d, repo, bare, rec, bodyfile = seed_handover("pr1", orchestrator=False)
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "T", log=d,
                  script=S_WRAP, STUB_RECORD_FAIL="deliver")
check("a failed deliver write leaves one created PR and exit 1",
      rc == 1 and has(out, "FAIL deliver:") and len(creates(d)) == 1)
rc, out, _ = step("hand-over", rec, "deliverable-1", "--body", bodyfile, "--title", "T", log=d,
                  script=S_WRAP, STUB_GH_OPEN=PR_URL)
check("the rerun reuses the open PR and calls gh pr create no second time",
      rc == 0 and ("ok pr: already open " + PR_URL) in lines(out) and len(creates(d)) == 1)
check("the rerun delivers with the open PR's url",
      deliverable(rec).get("state") == "draft-pr-opened" and deliverable(rec).get("pr_url") == PR_URL)

# Item 6: a criterion that edits a tracked file at the red commit.
d, repo, rec, base = seed_verify("rd1")
red = commit(repo, "tests/test_a.py", "test\n", "red test")
commit(repo, "src/a.py", "x = 1\n", "fix")
crit = "if [ ! -f src/a.py ]; then echo edit >> README; fi; test -f src/a.py"
rc, out, _ = step("verify", rec, "p1", "--criterion", crit, "--no-suite", "--red", red)
check("a criterion that edits a tracked file at the red commit still passes the red check",
      rc == 0 and any(x.startswith("ok red:") for x in lines(out)))
check("the red step and the red evidence name the edited file",
      any(x.startswith("ok red:") and "README" in x for x in lines(out))
      and any("README" in x for x in section(out, "red")))
check("the edit does not reach the branch: the tree is clean and the branch is back",
      g(repo, "status", "--porcelain") == "" and g(repo, "branch", "--show-current") == DEL_BRANCH
      and raw(os.path.join(repo, "README")) == b"hello\n")

# Item 9: an id with / or .. is a usage error.
d, repo, _ = make_repo("id1")
rec = make_record(d, repo)
before = raw(os.path.join(rec, "state.json"))
for bad in ("../x", "a/b", ".."):
    rc, out, err = step("branch", rec, bad, "--held", "--start-point", "main")
    check("branch with the id %s is a usage error that runs nothing" % bad,
          rc == 2 and "deliverable id" in err and wt_json(rec) is None
          and raw(os.path.join(rec, "state.json")) == before and len(worktree_paths(repo)) == 1)
rc, out, err = step("branch", rec, "deliverable-1", "--territory", "..=ic-x")
check("branch with the territory slug .. is a usage error", rc == 2 and "--territory" in err)
rc, out, err = step("hand-over", rec, "a/b", "--local")
check("hand-over with the id a/b is a usage error", rc == 2 and "deliverable id" in err)
rc, out, err = step("cleanup", rec, "../x")
check("cleanup with the id ../x is a usage error", rc == 2 and "deliverable id" in err)

# A bad --branch name is a usage error that writes nothing.
rc, out, err = step("branch", rec, "deliverable-1", "--branch", "bad name~")
check("branch with an invalid --branch name is a usage error that writes nothing",
      rc == 2 and raw(os.path.join(rec, "state.json")) == before and g(repo, "branch", "--show-current") == "main")

# Item 10: cleanup's already-gone branch.
d, repo, bare, rec, bodyfile = seed_handover("ag1", orchestrator=False, held_ic=True)
icwt = os.path.join(rec, "worktrees", "alpha")
g(repo, "worktree", "remove", icwt)
rc, out, _ = step("cleanup", rec, "deliverable-1", log=d)
check("a worktree removed outside the script is already gone, and its entry is deleted",
      rc == 0 and ("ok worktree-remove: %s: already gone" % icwt) in lines(out) and wt_json(rec) == {})

# A rerun of launch-check writes the decision once.
d, repo, _ = make_repo("lr1")
rec = make_record(d, repo)
step("launch-check", rec)
rc, out, _ = step("launch-check", rec)
dec = (raw(os.path.join(rec, "decisions.md")) or b"").decode()
check("a launch-check rerun writes one worktree base decision",
      rc == 0 and dec.count("## Which worktree base does this run use?") == 1)


# --- park and unpark: spec A1, A1b, plan review F1, F2, F3, F5 ---------------

import time

PARK_ROOT = os.path.join(T, "crew-root")
ORCH_NAME, ITEM = "o1", "i1"
OLD = "sess-old"
WAITER = "waiter-sid"
OLD_TAB = "tmux:%1"
WAITER_TAB = "tmux:%9"
SETTINGS_OUT = '{"statusLine": {"type": "command", "command": "wrap"}}'

# One log, calls.log, for the three stubs, so the order of calls shows.
CALL_LOG = """import json, os, sys
def log(tool):
    with open(os.path.join(os.environ["STUB_LOG"], "calls.log"), "a") as f:
        f.write(json.dumps([tool] + sys.argv[1:]) + "\\n")
"""

LAUNCHER_STUB = CALL_LOG + """import time
log("launcher")
args = sys.argv[1:]
def opt(name, default=None):
    return args[args.index(name) + 1] if name in args else default
if args[0] == "window":
    with open(os.path.join(os.environ["STUB_LOG"], "window-sid"), "w") as f:
        f.write(str(os.getsid(0)))
    time.sleep(float(os.environ.get("STUB_WINDOW_SLEEP", "0")))
    code = int(os.environ.get("STUB_WINDOW_EXIT", "0"))
    if code:
        sys.stderr.write("launcher: the tab did not open\\n")
        sys.exit(code)
    print(json.dumps({"session_name": opt("--name"), "model": opt("--model", "opus"),
                      "terminal": opt("--terminal", "tmux"), "tab": "%s",
                      "tab_group": opt("--group"), "session_id": "%s", "cwd": opt("--cwd")}))
if args[0] == "find":
    code = int(os.environ.get("STUB_FIND_EXIT", "0"))
    if code:
        sys.stderr.write("launcher: ps failed\\n")
        sys.exit(code)
    for line in os.environ.get("STUB_FIND_OUT", "").split("|"):
        if line:
            print(line)
sys.exit(0)
""" % (WAITER_TAB, WAITER)

USAGE_STUB = CALL_LOG + """log("usage")
code = int(os.environ.get("STUB_USAGE_EXIT", "0"))
if code:
    sys.stderr.write("crew-usage: no wrapper\\n")
    sys.exit(code)
print(%r)
""" % SETTINGS_OUT

ORCH_STUB = CALL_LOG + """import time
time.sleep(float(os.environ.get("STUB_ORCH_SLEEP", "0")))
log("orch")
fail = os.environ.get("STUB_ORCH_FAIL_ON")
if fail and fail in " ".join(sys.argv[1:]):
    sys.stderr.write("crew-orch: stub failure\\n")
    sys.exit(1)
"""


def make_park_plugin(name, record_wrapper=False):
    script = make_plugin(name, record_wrapper=record_wrapper)
    orch_dir = os.path.join(T, name, "skills", "orchestrator", "scripts")
    write(os.path.join(orch_dir, "launcher.py"), LAUNCHER_STUB)
    write(os.path.join(orch_dir, "crew-usage.py"), USAGE_STUB)
    write(os.path.join(orch_dir, "crew-orch.py"), ORCH_STUB)
    return script


SP = make_park_plugin("plugin-park")
SP_WRAP = make_park_plugin("plugin-park-wrap", record_wrapper=True)
PARK_MD = os.path.join(T, "plugin-park", "skills", "project-lead", "references", "park.md")


def launch_item(repo, **over):
    launch = {"session_name": "pl-1", "repo": "o/r", "worktree": repo, "branch": "b", "base": "origin/main",
              "model": "sonnet", "terminal": "tmux", "tab": OLD_TAB, "tab_group": "grp", "session_id": OLD}
    launch.update(over)
    return launch


def write_orch(launch, name=ORCH_NAME):
    path = os.path.join(PARK_ROOT, "orchestrators", name, "orchestrator.json")
    write(path, json.dumps({"name": name, "items": {ITEM: {"id": ITEM, "launch": launch}}}, indent=2) + "\n")
    return path


def seed_park(name, orchestrator=True, launch=None, run=None):
    """A repo, its record with run.orchestrator, and the orchestrator item. Return (d, repo, rec)."""
    d, repo, _ = make_repo(name, remote=False)
    extra = dict(run or {})
    if orchestrator:
        extra["orchestrator"] = {"name": ORCH_NAME, "item": ITEM}
    rec = make_record(d, repo, run=extra)
    write_orch(launch if launch is not None else launch_item(repo))
    logd = os.path.join(d, "logs")
    os.makedirs(logd)
    return d, repo, rec, logd


def park(rec, logd, *args, session=OLD, script=SP, **extra):
    return step("park", rec, *args, script=script, log=logd, CLAUDE_CODE_SESSION_ID=session,
                CREW_RECORD_ROOT=PARK_ROOT, **extra)


def unpark(rec, logd, *args, session=OLD, script=SP, **extra):
    return step("unpark", rec, *args, script=script, log=logd, CLAUDE_CODE_SESSION_ID=session,
                CREW_RECORD_ROOT=PARK_ROOT, **extra)


def park_log(rec):
    path = os.path.join(rec, "park", "park.log")
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return f.read().splitlines()


def wait_helper(rec, seconds=20):
    """Wait for the helper's last line, `<time> end`. Return True when it came."""
    stop_at = time.time() + seconds
    while time.time() < stop_at:
        if any(line.endswith(" end") for line in park_log(rec)):
            return True
        time.sleep(0.1)
    return False


def calls(logd, tool=None):
    found = log_calls(logd, "calls")
    return [c for c in found if tool is None or c[0] == tool]


def stops(logd):
    return [c[1:] for c in calls(logd, "launcher") if c[1] == "stop"]


def windows(logd):
    return [c[1:] for c in calls(logd, "launcher") if c[1] == "window"]


def opt_of(argv, name):
    return argv[argv.index(name) + 1] if name in argv else None


def run_of(rec):
    return state(rec)["run"]


def wait_waiter(rec, seconds=20):
    """Wait until the helper has written run.park.waiter. Return True when it came."""
    stop_at = time.time() + seconds
    while time.time() < stop_at:
        if ((run_of(rec).get("park") or {}).get("waiter") or {}).get("session_id"):
            return True
        time.sleep(0.05)
    return False


def finds(logd):
    return [c[1:] for c in calls(logd, "launcher") if c[1] == "find"]


def orch_sets(logd):
    return [c[1:] for c in calls(logd, "orch")]


def item_set(key, value):
    return ["--orch", ORCH_NAME, "item", ITEM, "set", key, json.dumps(value)]


PARK_KEYS = {"reason", "by", "at", "until", "next", "from_session", "prompt", "waiter"}
NEXT = "Run the plan review of round 2."

# Usage errors: exit 2, no park, no call.
d, repo, rec, logd = seed_park("park-usage")
for label, args in (("a bad --reason", ["--reason", "nap", "--next", NEXT]),
                    ("pause with no --by", ["--reason", "pause", "--next", NEXT]),
                    ("usage with --by", ["--reason", "usage", "--by", "ann", "--next", NEXT]),
                    ("no --next", ["--reason", "usage"]),
                    ("no --reason", ["--next", NEXT]),
                    ("--until not an integer", ["--reason", "usage", "--next", NEXT, "--until", "soon"]),
                    ("a negative --delay", ["--reason", "usage", "--next", NEXT, "--delay", "-1"]),
                    ("the removed --name flag", ["--reason", "usage", "--next", NEXT, "--name", "x"])):
    rc, out, err = park(rec, logd, *args)
    check("park with %s exits 2 and writes no park" % label,
          rc == 2 and run_of(rec).get("park") is None and not calls(logd))

# Refusals: exit 1, one FAIL park line, nothing written, no call.
rc, out, err = park(os.path.join(T, "no-such-record"), logd, "--reason", "usage", "--next", NEXT)
check("park with no record exits 1 with FAIL park", rc == 1 and has(out, "FAIL park:"))


def refused_park(label, rec, logd, **extra):
    before = raw(os.path.join(rec, "state.json"))
    rc, out, err = park(rec, logd, "--reason", "usage", "--next", NEXT, "--delay", "0", **extra)
    check("park %s exits 1 with FAIL park, writes nothing and calls nothing" % label,
          rc == 1 and has(out, "FAIL park:") and raw(os.path.join(rec, "state.json")) == before
          and not calls(logd) and not os.path.exists(os.path.join(rec, "park", "park.log")))


d, repo, rec, logd = seed_park("park-no-orch", orchestrator=False)
refused_park("with no orchestrator", rec, logd)
rc, out, err = park(rec, logd, "--reason", "usage", "--next", NEXT)
check("the no-orchestrator refusal names the orchestrator", "orchestrator" in out)
d, repo, rec, logd = seed_park("park-set")
rec_call(rec, "run", "set", "park", json.dumps({"reason": "usage", "at": "x", "from_session": "s", "waiter": None}))
refused_park("with a park already set", rec, logd)
d, repo, rec, logd = seed_park("park-dirty")
write(os.path.join(repo, "new.txt"), "work\n")
refused_park("with a dirty tree", rec, logd)
d, repo, rec, logd = seed_park("park-other-wt", launch=launch_item("/somewhere/else"))
refused_park("when run.repo differs from launch.worktree", rec, logd)
d, repo, rec, logd = seed_park("park-no-tab")
write_orch(launch_item(repo, tab=None))
refused_park("when the item has no launch.tab", rec, logd)
d, repo, rec, logd = seed_park("park-no-orch-file")
os.remove(os.path.join(PARK_ROOT, "orchestrators", ORCH_NAME, "orchestrator.json"))
refused_park("when the orchestrator record is missing", rec, logd)

# A park that runs to the end.
d, repo, rec, logd = seed_park("park-good")
rc, out, err = park(rec, logd, "--reason", "usage", "--until", "1767000000", "--next", NEXT, "--delay", "0")
check("park exits 0 and prints the helper line", rc == 0 and has(out, "ok helper: started pid"))
p = run_of(rec).get("park") or {}
prompt = os.path.join(rec, "park", "prompt-1.md")
check("run.park has exactly the eight keys", set(p) == PARK_KEYS)
check("run.park: reason usage, by usage, until, next, from_session the old session, prompt-1",
      p.get("reason") == "usage" and p.get("by") == "usage" and p.get("until") == 1767000000
      and p.get("next") == NEXT and p.get("from_session") == OLD and p.get("prompt") == prompt)
check("the helper ends", wait_helper(rec))
seq = [c[0] + ":" + (c[1] if c[0] == "launcher" else c[-2] if c[0] == "orch" else c[1]) for c in calls(logd)]
check("the order is settings, window, launch.tab, launch.session_id, stop",
      seq == ["usage:settings", "launcher:window", "orch:launch.tab", "orch:launch.session_id", "launcher:stop"])
check("crew-usage.py settings runs with --cwd run.repo", calls(logd, "usage") == [["usage", "settings", "--cwd", repo]])
w = (windows(logd) or [[]])[0]
check("window gets the name, the cwd, the prompt file, the model, the group, the terminal and --settings",
      opt_of(w, "--name") == "pl-1" and opt_of(w, "--cwd") == repo and opt_of(w, "--prompt-file") == prompt
      and opt_of(w, "--model") == "sonnet" and opt_of(w, "--group") == "grp" and opt_of(w, "--terminal") == "tmux"
      and opt_of(w, "--settings") == SETTINGS_OUT)
waiter = (run_of(rec).get("park") or {}).get("waiter") or {}
check("run.park.waiter is the launcher output",
      {k: waiter.get(k) for k in ("name", "session_id", "tab", "terminal", "tab_group", "model")}
      == {"name": "pl-1", "session_id": WAITER, "tab": WAITER_TAB, "terminal": "tmux", "tab_group": "grp",
          "model": "sonnet"} and bool(waiter.get("started_at")))
check("the orchestrator item gets launch.tab and launch.session_id of the waiter",
      [c[1:] for c in calls(logd, "orch")] == [
          ["--orch", ORCH_NAME, "item", ITEM, "set", "launch.tab", json.dumps(WAITER_TAB)],
          ["--orch", ORCH_NAME, "item", ITEM, "set", "launch.session_id", json.dumps(WAITER)]])
check("stop targets the old tab with --name and --session-id of the old session",
      stops(logd) == [["stop", OLD_TAB, "--name", "pl-1", "--session-id", OLD]])
text_p = open(prompt).read() if os.path.exists(prompt) else ""
check("the prompt names the record dir, the goal slug and park.md's The waiter, absolute",
      rec in text_p and SLUG in text_p and os.path.normpath(PARK_MD) in text_p and "## The waiter" in text_p)
steps_logged = [line.split(" ")[2].rstrip(":") for line in park_log(rec) if len(line.split(" ")) > 2]
check("park.log has one ok line per step and ends with end",
      steps_logged == ["prompt", "settings", "window", "record", "orch", "orch", "wait", "stop"]
      and all(line.split(" ")[1] == "ok" for line in park_log(rec)[:-1]) and park_log(rec)[-1].endswith(" end"))
sid_file = os.path.join(logd, "window-sid")
check("the helper runs in its own session, not the caller's",
      os.path.exists(sid_file) and open(sid_file).read() != str(os.getsid(0)))
check("the run stays active", run_of(rec).get("run_state") == "active")

# by: question is project-lead; pause is the --by value.
d, repo, rec, logd = seed_park("park-question")
rc, out, err = park(rec, logd, "--reason", "question", "--next", NEXT, "--delay", "0")
wait_helper(rec)
check("--reason question writes by project-lead and until null",
      rc == 0 and run_of(rec)["park"]["by"] == "project-lead" and run_of(rec)["park"]["until"] is None)
d, repo, rec, logd = seed_park("park-pause")
rc, out, err = park(rec, logd, "--reason", "pause", "--by", "ann", "--next", NEXT, "--delay", "0")
wait_helper(rec)
check("--reason pause writes by the --by value", rc == 0 and run_of(rec)["park"]["by"] == "ann")

# The call returns before the stop: the helper waits --delay seconds.
d, repo, rec, logd = seed_park("park-delay")
began = time.time()
rc, out, err = park(rec, logd, "--reason", "usage", "--next", NEXT, "--delay", "2")
took = time.time() - began
check("park with --delay 2 returns at once, before any stop", rc == 0 and took < 1.5 and not stops(logd))
check("the helper stops the old session after the delay", wait_helper(rec) and len(stops(logd)) == 1)

# A wake during the delay: the helper reads the record again before it stops the old session.
d, repo, rec, logd = seed_park("park-delay-old-woke")
rc, out, err = park(rec, logd, "--reason", "usage", "--next", NEXT, "--delay", "3")
got_waiter = wait_waiter(rec)
rc2, out2, err2 = unpark(rec, logd, session=OLD, STUB_FIND_OUT=OLD_TAB + " name")
wait_helper(rec)
check("the old session unparks during the delay: the helper stops nothing more, and logs it",
      rc == 0 and got_waiter and rc2 == 0 and stops(logd) == [["stop", WAITER_TAB, "--session-id", WAITER]]
      and any(" ok stop: skipped" in x and OLD in x for x in park_log(rec)))
d, repo, rec, logd = seed_park("park-delay-waiter-woke")
rc, out, err = park(rec, logd, "--reason", "usage", "--next", NEXT, "--delay", "3")
got_waiter = wait_waiter(rec)
rc2, out2, err2 = unpark(rec, logd, session=WAITER)
wait_helper(rec)
check("the waiter unparks during the delay: the helper still stops the old session",
      rc == 0 and got_waiter and rc2 == 0 and stops(logd) == [["stop", OLD_TAB, "--name", "pl-1", "--session-id", OLD]])


# Failures roll the park back: the old session stays, no stop of it.
def rolled_back(label, name, step_name, waiter_stopped, script=SP, **extra):
    d, repo, rec, logd = seed_park(name)
    rc, out, err = park(rec, logd, "--reason", "usage", "--next", NEXT, "--delay", "0", script=script, **extra)
    ended = wait_helper(rec)
    r = run_of(rec)
    last = (r.get("parks") or [{}])[-1]
    want_stops = [["stop", WAITER_TAB, "--session-id", WAITER]] if waiter_stopped else []
    check("%s: run.park is null and run.parks ends with failed.step %s" % (label, step_name),
          rc == 0 and ended and r.get("park") is None and (last.get("failed") or {}).get("step") == step_name
          and bool(last["failed"].get("at")) and bool(last["failed"].get("error")) and last.get("from_session") == OLD)
    check("%s: the old session gets no stop%s" % (label, ", the waiter does" if waiter_stopped else ""),
          stops(logd) == want_stops)
    check("%s: park.log has a FAIL %s line" % (label, step_name),
          any(" FAIL %s:" % step_name in line for line in park_log(rec)))
    return logd


logd = rolled_back("a failed window", "park-fail-window", "window", False, STUB_WINDOW_EXIT="1")
check("a failed window: no orchestrator write", not calls(logd, "orch"))
logd = rolled_back("a failed settings call", "park-fail-settings", "settings", False, STUB_USAGE_EXIT="1")
check("a failed settings call: no window", not windows(logd))
rolled_back("a failed waiter write", "park-fail-waiter", "record", True, script=SP_WRAP,
            STUB_RECORD_FAIL="set park.waiter")

# The OSError path of the call: <record>/park is a plain file, so the helper cannot start.
d, repo, rec, logd = seed_park("park-fail-helper")
write(os.path.join(rec, "park"), "not a directory\n")
rc, out, err = park(rec, logd, "--reason", "usage", "--next", NEXT, "--delay", "0")
r = run_of(rec)
last = (r.get("parks") or [{}])[-1]
check("an OSError at the helper start exits 1 with FAIL helper, run.park null and failed.step helper",
      rc == 1 and has(out, "FAIL helper:") and r.get("park") is None
      and (last.get("failed") or {}).get("step") == "helper" and last.get("from_session") == OLD
      and not calls(logd))

# The waiter woke the run before a failed orch write: no rollback, the waiter stays, the old session stops.
d, repo, rec, logd = seed_park("park-fail-orch-woke")
rc, out, err = park(rec, logd, "--reason", "usage", "--next", NEXT, "--delay", "0",
                    STUB_ORCH_FAIL_ON="launch.tab", STUB_ORCH_SLEEP="2")
got_waiter = wait_waiter(rec)
rc2, out2, err2 = unpark(rec, logd, session=WAITER)
wait_helper(rec)
r = run_of(rec)
check("a failed orch write after the waiter woke: the waiter is not stopped, the old session is",
      rc == 0 and got_waiter and rc2 == 0 and stops(logd) == [["stop", OLD_TAB, "--name", "pl-1", "--session-id", OLD]])
check("a failed orch write after the waiter woke: run.parks holds one woke entry and no failed one",
      r.get("park") is None and len(r.get("parks") or []) == 1 and "failed" not in r["parks"][0]
      and r["parks"][0]["woke"]["session_id"] == WAITER)
rolled_back("a failed launch.tab write", "park-fail-tab", "orch", True, STUB_ORCH_FAIL_ON="launch.tab")
rolled_back("a failed launch.session_id write", "park-fail-sid", "orch", True, STUB_ORCH_FAIL_ON="launch.session_id")

# A wake during the window start: the waiter unparks before the helper's waiter write.
d, repo, rec, logd = seed_park("park-race-waiter")
rc, out, err = park(rec, logd, "--reason", "pause", "--by", "ann", "--next", NEXT, "--delay", "0",
                    STUB_WINDOW_SLEEP="2")
rc2, out2, err2 = unpark(rec, logd, "--by", "resume word", session=WAITER, STUB_WINDOW_SLEEP="2",
                         STUB_FIND_OUT=OLD_TAB + " name|" + WAITER_TAB + " name")
check("the waiter's early unpark exits 0 and clears run.park", rc == 0 and rc2 == 0 and run_of(rec).get("park") is None)
check("the helper ends", wait_helper(rec))
r = run_of(rec)
check("after the early wake the helper writes no run.park and no waiter into it",
      r.get("park") is None and len(r.get("parks") or []) == 1 and r["parks"][0].get("waiter") is None)
check("after the early wake the waiter's unpark is the one writer of the item: the waiter's id and tab",
      orch_sets(logd) == [item_set("launch.session_id", WAITER), item_set("launch.tab", WAITER_TAB)])
check("the early unpark finds the tab by the session name, the caller's id and the terminal",
      finds(logd) == [["find", "pl-1", "--session-id", WAITER, "--terminal", "tmux"]])
check("after the early wake the stop still targets the old session, and only it",
      stops(logd) == [["stop", OLD_TAB, "--name", "pl-1", "--session-id", OLD]])

# Another session unparks before the waiter write: the helper stops the waiter, not the old session.
d, repo, rec, logd = seed_park("park-race-old")
rc, out, err = park(rec, logd, "--reason", "usage", "--next", NEXT, "--delay", "0", STUB_WINDOW_SLEEP="2")
rc2, out2, err2 = unpark(rec, logd, session=OLD)
wait_helper(rec)
check("an unpark by the old session before the waiter write: the helper stops the waiter only",
      rc == 0 and rc2 == 0 and stops(logd) == [["stop", WAITER_TAB, "--session-id", WAITER]]
      and run_of(rec).get("park") is None)
check("an unpark by the old session: the item never gets the waiter's tab",
      not any("launch.tab" in c and json.dumps(WAITER_TAB) in c for c in calls(logd, "orch")))

# unpark.
WAITER_OBJ = {"name": "pl-1", "session_id": WAITER, "tab": WAITER_TAB, "terminal": "tmux", "tab_group": "grp",
              "model": "sonnet", "started_at": "2026-11-25T10:00:01Z"}
PARK_OBJ = {"reason": "pause", "by": "ann", "at": "2026-11-25T10:00:00Z", "until": None, "next": NEXT,
            "from_session": OLD, "prompt": "/x/prompt-1.md", "waiter": WAITER_OBJ}

d, repo, rec, logd = seed_park("unpark-none")
before = raw(os.path.join(rec, "state.json"))
rc, out, err = unpark(rec, logd)
check("unpark with no park exits 0, says so and changes nothing",
      rc == 0 and has(out, "ok unpark: no park") and raw(os.path.join(rec, "state.json")) == before and not calls(logd))
rc, out, err = unpark(os.path.join(T, "no-such-record"), logd)
check("unpark with no record exits 1", rc == 1)

d, repo, rec, logd = seed_park("unpark-foreign", run={"park": PARK_OBJ})
rc, out, err = unpark(rec, logd, "--by", "resume word", session=OLD,
                      STUB_FIND_OUT=WAITER_TAB + " name|" + OLD_TAB + " name")
r = run_of(rec)
last = (r.get("parks") or [{}])[-1]
woke = last.get("woke") or {}
check("unpark moves the park to run.parks with woke and sets run.park null",
      rc == 0 and r.get("park") is None and len(r.get("parks") or []) == 1
      and {k: v for k, v in last.items() if k != "woke"} == PARK_OBJ
      and woke.get("by") == "resume word" and woke.get("session_id") == OLD and bool(woke.get("at")))
check("unpark by another session stops the waiter by its id", stops(logd) == [["stop", WAITER_TAB, "--session-id", WAITER]])
check("unpark by another session finds its tab, skips the waiter's tab, and writes its id and tab",
      finds(logd) == [["find", "pl-1", "--session-id", OLD, "--terminal", "tmux"]]
      and orch_sets(logd) == [item_set("launch.session_id", OLD), item_set("launch.tab", OLD_TAB)])

for label, extra in (("prints no line", {"STUB_FIND_OUT": ""}), ("fails", {"STUB_FIND_EXIT": "6"})):
    d, repo, rec, logd = seed_park("unpark-nofind-" + label.split()[0], run={"park": PARK_OBJ})
    rc, out, err = unpark(rec, logd, session=OLD, **extra)
    check("unpark when find %s writes a null tab with an ok orch line that says so" % label,
          rc == 0 and orch_sets(logd) == [item_set("launch.session_id", OLD), item_set("launch.tab", None)]
          and any(x.startswith("ok orch: set launch.tab null") and "no tab" in x for x in lines(out)))

d, repo, rec, logd = seed_park("unpark-self", run={"park": PARK_OBJ})
rc, out, err = unpark(rec, logd, session=WAITER)
check("the waiter's own unpark moves the park, stops nothing and writes the waiter's id and tab",
      rc == 0 and run_of(rec).get("park") is None and run_of(rec)["parks"][-1]["woke"]["session_id"] == WAITER
      and not stops(logd) and not finds(logd)
      and orch_sets(logd) == [item_set("launch.session_id", WAITER), item_set("launch.tab", WAITER_TAB)])

d, repo, rec, logd = seed_park("unpark-no-waiter", run={"park": dict(PARK_OBJ, waiter=None)})
rc, out, err = unpark(rec, logd, session=OLD)
check("unpark with waiter null stops nothing", rc == 0 and run_of(rec).get("park") is None and not stops(logd))

d, repo, rec, logd = seed_park("unpark-rerun", run={"park": PARK_OBJ})
rc, out, err = unpark(rec, logd, session=WAITER, script=SP_WRAP, STUB_RECORD_FAIL="set park null")
check("a failed run.park write exits 1 and leaves the park", rc == 1 and run_of(rec).get("park") == PARK_OBJ
      and len(run_of(rec).get("parks") or []) == 1)
rc, out, err = unpark(rec, logd, session=WAITER, script=SP_WRAP)
check("the rerun appends no second entry and clears the park",
      rc == 0 and run_of(rec).get("park") is None and len(run_of(rec)["parks"]) == 1)


# The park drill (A1b): one per reason; every seeded fact stays on disk.
def snapshot(rec):
    files = {}
    for root, dirs, names in os.walk(rec):
        dirs[:] = [x for x in dirs if os.path.join(root, x) != os.path.join(rec, "park")]
        for n in names:
            path = os.path.join(root, n)
            if n in ("state.json", "state.json.lock") or n.endswith(".tmp"):
                continue
            files[os.path.relpath(path, rec)] = raw(path)
    st = state(rec)
    st["run"] = {k: v for k, v in st["run"].items() if k not in ("park", "parks")}
    return files, st


for reason in ("usage", "pause", "question"):
    d, repo, rec, logd = seed_park("drill-" + reason, run={
        "plan_review": {"round": 1, "state": "started", "plans": ["p1"]},
        "review_pending": {"head": "abc123", "round": 1}})
    rec_call(rec, "package", "add", json.dumps({"id": "p1", "state": "in-flight", "territory": "code"}))
    write(os.path.join(rec, "plans", "p1.md"), "# Plan: p1\n")
    write(os.path.join(rec, "handover.md"), "# Handover\n\n## Standing words\n\nShip on green, said ann.\n")
    if reason == "question":
        rec_call(rec, "escalation", "add", "trigger 4", "Which schema wins?")
    seeded = snapshot(rec)
    args = ["--reason", reason, "--next", NEXT, "--delay", "0"] + (["--by", "ann"] if reason == "pause" else [])
    rc, out, err = park(rec, logd, *args, session=OLD)
    ended = wait_helper(rec)
    seq = [c[1] for c in calls(logd, "launcher")]
    check("drill %s: park exits 0, window comes before stop" % reason,
          rc == 0 and ended and seq == ["window", "stop"])
    check("drill %s: stop targets session A, the old session" % reason,
          stops(logd) == [["stop", OLD_TAB, "--name", "pl-1", "--session-id", OLD]])
    before_unpark = len(stops(logd))
    rc, out, err = unpark(rec, logd, "--by", "the wake", session=WAITER)
    r = run_of(rec)
    check("drill %s: unpark as the waiter clears run.park and run.parks holds the park with woke" % reason,
          rc == 0 and r.get("park") is None and len(r.get("parks") or []) == 1
          and r["parks"][0].get("reason") == reason and r["parks"][0].get("woke", {}).get("session_id") == WAITER)
    check("drill %s: no stop targeted the waiter" % reason,
          not any(WAITER in c or WAITER_TAB in c for c in stops(logd)) and len(stops(logd)) == before_unpark)
    check("drill %s: every seeded fact is unchanged on disk" % reason, snapshot(rec) == seeded)


# --- greps of the script: R17, R19, R20 ------------------------------------

text = (raw(SRC) or b"").decode()
src_lines = text.splitlines()
force = [x for x in src_lines if "--force" in x]
check("R17 --force appears only on the probe line", bool(force) and all("probe" in x for x in force))
check("R19 no Skill call in the script", bool(text) and "Skill" not in text)
check("no test switch CREW_PARK_TEST_FAIL in the script", bool(text) and "CREW_PARK_TEST_FAIL" not in text)
check("R19 no open() of the body file", bool(text) and not any("open(" in x and "body" in x for x in src_lines))
write_open = re.compile(r"""open\([^)]*["'][wax]b?\+?["']""")
writes = [x for x in src_lines if write_open.search(x) or ".write_text(" in x or ".write_bytes(" in x]
# The files the script writes itself: worktrees.json, the verify patch file, and the
# park's prompt file and log (park/prompt-<n>.md, park/park.log).
check("R20 every write-mode open() names worktrees, the verify patch or a park file",
      bool(text) and all("worktrees" in x or "patch" in x or "park" in x for x in writes))
check("R20 no state.json line writes the file",
      bool(text) and not any("state.json" in x and (write_open.search(x) or ".write(" in x or "write_json" in x) for x in src_lines))
base_ref = None
for ref in ("origin/main",):
    if subprocess.run([REAL_GIT, "-C", HERE, "rev-parse", "--verify", "--quiet", ref], env=ENV,
                      capture_output=True).returncode == 0:
        base_ref = ref
if base_ref is None:
    print("skip R20 the command line of crew-record.py is unchanged: no origin/main in this checkout")
else:
    # R20 guards the command line that crew-step.py calls. crew-record.py may change inside
    # (a lock, a new field), but every usage line of the merge base must still be there.
    mb = subprocess.run([REAL_GIT, "-C", HERE, "merge-base", "HEAD", base_ref], env=ENV,
                        capture_output=True, text=True)
    old = subprocess.run([REAL_GIT, "-C", HERE, "show", mb.stdout.strip() + ":./crew-record.py"], env=ENV,
                         capture_output=True, text=True)
    usage = re.compile(r"^  crew-record\.py <record-dir> .*$", re.M)
    old_lines = usage.findall(old.stdout) if old.returncode == 0 else []
    new_lines = usage.findall((raw(REAL_RECORD) or b"").decode())
    check("R20 every usage line of crew-record.py at the merge base with " + base_ref + " is still there",
          bool(old_lines) and all(x in new_lines for x in old_lines))


# --- end -------------------------------------------------------------------

shutil.rmtree(T, ignore_errors=True)
print("%d of %d checks passed" % (passed, total))
sys.exit(0 if passed == total else 1)

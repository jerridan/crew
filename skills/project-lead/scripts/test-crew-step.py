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
check("R14 --- diff is the last marker", bool(mk) and mk[-1] == "--- diff")
body = out.split("--- diff\n", 1)[1] if "--- diff\n" in out else None
check("R14 the diff body equals git diff <base>..HEAD", body == g_raw(repo, "diff", base + "..HEAD"))
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
rc, out, _ = step("verify", rec, "p1", "--ic-branch", "--criterion", "test -f src/a.py", "--no-suite")
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
gh = log_calls(d, "gh")
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
      len(log_calls(d, "gh")) == 1 and dl.get("state_changed_at") == changed_at
      and state(rec)["run"].get("review_pending") == pending)
check("PR4 a rerun runs orch again", len(log_calls(d, "orch")) == 4)

d, repo, bare, rec, bodyfile = seed_handover("h2", remote=False, orchestrator=False)
rc, out, _ = step("hand-over", rec, "deliverable-1", "--local", log=d)
dl = deliverable(rec)
check("R15 --local: exit 0 and work-complete with pr_url null",
      rc == 0 and dl.get("state") == "work-complete" and dl.get("pr_url") is None
      and state(rec)["run"].get("run_state") == "delivered")
check("R15 --local: no push and no gh call", not has(out, "FAIL push") and log_calls(d, "gh") == [])
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


# --- greps of the script: R17, R19, R20 ------------------------------------

text = (raw(SRC) or b"").decode()
src_lines = text.splitlines()
force = [x for x in src_lines if "--force" in x]
check("R17 --force appears only on the probe line", bool(force) and all("probe" in x for x in force))
check("R19 no Skill call in the script", bool(text) and "Skill" not in text)
check("R19 no open() of the body file", bool(text) and not any("open(" in x and "body" in x for x in src_lines))
write_open = re.compile(r"""open\([^)]*["'][wax]b?\+?["']""")
writes = [x for x in src_lines if write_open.search(x) or ".write_text(" in x or ".write_bytes(" in x]
check("R20 every write-mode open() names worktrees", bool(text) and all("worktrees" in x for x in writes))
check("R20 no state.json line writes the file",
      bool(text) and not any("state.json" in x and (write_open.search(x) or ".write(" in x or "write_json" in x) for x in src_lines))
r = subprocess.run([REAL_GIT, "-C", HERE, "diff", "--quiet", "HEAD", "--", "crew-record.py"], env=ENV)
same = r.returncode == 0
mb = subprocess.run([REAL_GIT, "-C", HERE, "merge-base", "HEAD", "main"], env=ENV,
                    capture_output=True, text=True)
if same and mb.returncode == 0:
    same = subprocess.run([REAL_GIT, "-C", HERE, "diff", "--quiet", mb.stdout.strip(), "--",
                           "crew-record.py"], env=ENV).returncode == 0
check("R20 git diff shows no change to crew-record.py", same)


# --- end -------------------------------------------------------------------

shutil.rmtree(T, ignore_errors=True)
print("%d of %d checks passed" % (passed, total))
sys.exit(0 if passed == total else 1)

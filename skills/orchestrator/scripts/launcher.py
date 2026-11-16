#!/usr/bin/env python3
"""The launcher of crew:orchestrator: start, list, focus and stop implementers.

usage:
  launcher.py start --name <session-name> --model <model> --principal <name>
                    [--repo <owner/repo>] [--checkout <path>]
                    [--group <name>] [--group-color <#rrggbb>]
                    [--terminal iterm2|tmux]
  launcher.py groups
  launcher.py focus <handle>
  launcher.py stop <handle>

skills/orchestrator/references/launcher.md owns the arguments, the start
output and the exit codes. This file uses the standard library only. The
iTerm2 Python API runs in iterm2-tabs.py, through `uv run --with iterm2`.
"""

import argparse
import json
import os
import re
import shlex
import subprocess
import sys

OK, USAGE, NO_CHECKOUT, NO_TERMINAL, GIT, TERMINAL_STEP, BAD_HANDLE = 0, 2, 3, 4, 5, 6, 7

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, "iterm2-tabs.py")
HELPER_TIMEOUT = 120

START_USAGE = (
    "usage: launcher.py start --name <session-name> --model <model> "
    "--principal <name> [--repo <owner/repo>] [--checkout <path>] "
    "[--group <name>] [--group-color <#rrggbb>] [--terminal iterm2|tmux]"
)
USAGE_LINE = "usage: launcher.py start ... | groups | focus <handle> | stop <handle>"

WAIT_PROMPT = (
    "You are an implementer session for the orchestrator session named {p}. "
    "The user started you through that orchestrator. Do nothing now. A goal "
    "arrives as a cross-session message from that session. When it arrives, "
    "run the crew:project-lead skill with that goal. The orchestrator is your "
    "principal: the user gave it the authority to decide for this work, so "
    "send your questions, your escalations and your reports to it with "
    "SendMessage, not to this tab. Answer this message with one line and then "
    "wait."
)

NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}")
REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
PANE_RE = re.compile(r"%[0-9]+")
ITERM_ID_RE = re.compile(r"[A-Za-z0-9-]+")

# Every AppleScript scans windows, tabs and sessions for one unique id.
OSA_START = """on run argv
  set sid to item 2 of argv
  set cmd to item 3 of argv
  set nm to item 4 of argv
  tell application "iTerm2"
    set w to missing value
    if sid is not "" then
      repeat with ww in windows
        repeat with t in tabs of ww
          repeat with s in sessions of t
            if unique id of s is sid then set w to ww
          end repeat
        end repeat
      end repeat
    end if
    if w is missing value then set w to current window
    if w is missing value then error "no iTerm2 window"
    tell w to set newTab to (create tab with default profile)
    set s to current session of newTab
    tell s
      set name to nm
      write text cmd
    end tell
    return unique id of s
  end tell
end run
"""

OSA_FOCUS = """on run argv
  tell application "iTerm2"
    repeat with w in windows
      repeat with t in tabs of w
        repeat with s in sessions of t
          if unique id of s is item 2 of argv then
            tell t to select
            tell s to select
            tell w to select
            activate
            return "ok"
          end if
        end repeat
      end repeat
    end repeat
  end tell
  return "gone"
end run
"""

OSA_STOP = """on run argv
  tell application "iTerm2"
    repeat with w in windows
      repeat with t in tabs of w
        repeat with s in sessions of t
          if unique id of s is item 2 of argv then
            tell t to close
            return "ok"
          end if
        end repeat
      end repeat
    end repeat
  end tell
  return "gone"
end run
"""


class Fail(Exception):
    """One error line on stderr and an exit code."""

    def __init__(self, code, line):
        Exception.__init__(self, line)
        self.code = code
        self.line = line


def one_line(text):
    """The first non-empty line of a tool's output, or an empty string."""
    for line in (text or "").splitlines():
        if line.strip():
            return line.strip()
    return ""


def run(cmd, cwd=None, stdin=None, timeout=None):
    """Run a command. Return (exit code, stdout, stderr); 127 when it is missing."""
    try:
        p = subprocess.run(
            cmd, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=timeout
        )
    except FileNotFoundError:
        return 127, "", "%s: command not found" % cmd[0]
    except subprocess.TimeoutExpired:
        return 124, "", "%s: timed out after %d seconds" % (cmd[0], timeout)
    return p.returncode, p.stdout, p.stderr


# -- arguments --------------------------------------------------------------


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise Fail(USAGE, "launcher: %s; %s" % (message, self.usage_line))


def parse(argv):
    top = Parser(prog="launcher.py", add_help=False)
    top.usage_line = USAGE_LINE
    sub = top.add_subparsers(dest="cmd", parser_class=Parser)
    s = sub.add_parser("start", add_help=False)
    s.usage_line = START_USAGE
    s.add_argument("--name", required=True)
    s.add_argument("--model", required=True)
    s.add_argument("--principal", required=True)
    s.add_argument("--repo")
    s.add_argument("--checkout")
    s.add_argument("--group")
    s.add_argument("--group-color")
    s.add_argument("--terminal", choices=["iterm2", "tmux"])
    g = sub.add_parser("groups", add_help=False)
    g.usage_line = "usage: launcher.py groups"
    for verb in ("focus", "stop"):
        h = sub.add_parser(verb, add_help=False)
        h.usage_line = "usage: launcher.py %s <handle>" % verb
        h.add_argument("handle")
    args = top.parse_args(argv)
    if args.cmd is None:
        raise Fail(USAGE, "launcher: no subcommand; " + USAGE_LINE)
    if args.cmd == "start":
        check_start(args)
    return args


def check_start(a):
    def bad(why):
        raise Fail(USAGE, "launcher: %s; %s" % (why, START_USAGE))

    if not a.repo and not a.checkout:
        bad("give --repo or --checkout")
    if not NAME_RE.fullmatch(a.name):
        bad("--name %r does not match [a-z0-9][a-z0-9-]*" % a.name)
    if "eval" in a.name:
        bad("--name %r holds 'eval', which a worktree-isolated session refuses" % a.name)
    if a.group_color is not None and not COLOR_RE.fullmatch(a.group_color):
        bad("--group-color %r is not #rrggbb" % a.group_color)
    if a.repo is not None and not REPO_RE.fullmatch(a.repo):
        bad("--repo %r is not <owner>/<repo>" % a.repo)
    if a.group is not None and not a.group.strip():
        bad("--group is empty")


# -- terminal ---------------------------------------------------------------


def detect_terminal(flag=None):
    if flag:
        return flag
    if os.environ.get("TMUX"):
        return "tmux"
    if os.environ.get("TERM_PROGRAM") == "iTerm.app" or os.environ.get("ITERM_SESSION_ID"):
        return "iterm2"
    raise Fail(
        NO_TERMINAL,
        "launcher: unsupported terminal (TERM_PROGRAM=%s); the supported terminals are iterm2 and tmux"
        % os.environ.get("TERM_PROGRAM", ""),
    )


# -- checkout ---------------------------------------------------------------


def config_path():
    return os.environ.get("CREW_CONFIG") or os.path.expanduser("~/.claude/crew/config.md")


def checkout_for(repo):
    """The path of the `## Checkouts` line for repo in the machine file."""
    path = config_path()
    try:
        with open(path) as f:
            text = f.read()
    except OSError:
        text = ""
    inside = False
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("##"):
            inside = line == "## Checkouts"
            continue
        if not inside:
            continue
        if line.startswith("- "):
            line = line[2:].strip()
        m = re.fullmatch(r"([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)\s*:\s*(\S.*)", line)
        if m and m.group(1).lower() == repo.lower():
            return os.path.expanduser(m.group(2).strip().strip("`"))
    raise Fail(NO_CHECKOUT, "launcher: no Checkouts line for %s in %s" % (repo, path))


def repo_from_url(url):
    """<owner>/<repo> from an https, ssh or scp-style remote URL, or None."""
    url = url.strip()
    m = re.match(r"^(?:[a-z+]+://)?(?:[^@/]+@)?[^/:]+[:/](.+?)(?:\.git)?/?$", url)
    if not m:
        return None
    parts = m.group(1).strip("/").split("/")
    if len(parts) < 2:
        return None
    repo = "/".join(parts[-2:])
    return repo if REPO_RE.fullmatch(repo) else None


# -- git --------------------------------------------------------------------


def git(checkout, *args):
    rc, out, err = run(["git", "-C", checkout] + list(args))
    if rc != 0:
        raise Fail(
            GIT,
            "launcher: git %s failed in %s: %s"
            % (" ".join(args), checkout, one_line(err) or "exit %d" % rc),
        )
    return out


def make_worktree(checkout, name):
    """Fetch, find the remote default branch, and add the worktree.

    Return (worktree path, branch, base). Raise Fail(GIT) and change nothing
    when the worktree path or the branch already exists.
    """
    if not os.path.isdir(checkout):
        raise Fail(GIT, "launcher: the checkout %s does not exist" % checkout)
    top = git(checkout, "rev-parse", "--show-toplevel").strip()
    checkout = os.path.realpath(top)
    path = os.path.join(checkout, ".claude", "worktrees", name)
    branch = "worktree-" + name
    if os.path.lexists(path):
        raise Fail(GIT, "launcher: the worktree path %s already exists" % path)
    rc, _, _ = run(["git", "-C", checkout, "rev-parse", "-q", "--verify", "refs/heads/" + branch])
    if rc == 0:
        raise Fail(GIT, "launcher: the branch %s already exists in %s" % (branch, checkout))
    git(checkout, "fetch", "-q", "origin")
    out = git(checkout, "ls-remote", "--symref", "origin", "HEAD")
    m = re.search(r"^ref: refs/heads/(\S+)\s+HEAD$", out, re.M)
    if not m:
        raise Fail(GIT, "launcher: origin of %s names no default branch" % checkout)
    base = "origin/" + m.group(1)
    sha = git(checkout, "rev-parse", "--verify", "-q", base + "^{commit}").strip()
    git(checkout, "worktree", "add", "-q", "--no-track", "-b", branch, path, sha)
    return path, branch, base


# -- start --------------------------------------------------------------------


def launch_command(worktree, name, model, principal):
    claude = os.environ.get("CREW_LAUNCHER_CLAUDE") or "claude"
    return "cd %s && exec %s --name %s --model %s %s" % (
        shlex.quote(worktree),
        shlex.quote(claude),
        shlex.quote(name),
        shlex.quote(model),
        shlex.quote(WAIT_PROMPT.format(p=principal)),
    )


def tmux_start(name, group, command, worktree):
    session = group or "crew"
    rc, _, _ = run(["tmux", "has-session", "-t", "=" + session])
    if rc == 0:
        cmd = ["tmux", "new-window", "-t", "=%s:" % session, "-n", name, "-P", "-F", "#{pane_id}", command]
    else:
        cmd = ["tmux", "new-session", "-d", "-s", session, "-n", name, "-P", "-F", "#{pane_id}", command]
    rc, out, err = run(cmd)
    pane = one_line(out)
    if rc != 0 or not PANE_RE.fullmatch(pane):
        raise Fail(
            TERMINAL_STEP,
            "launcher: tmux opened no window (%s); the worktree stays at %s"
            % (one_line(err) or "exit %d" % rc, worktree),
        )
    return "tmux:" + pane, session


def own_iterm_session():
    sid = os.environ.get("ITERM_SESSION_ID", "")
    return sid.split(":", 1)[1] if ":" in sid else sid


def iterm_start(name, group, color, command, worktree):
    """Open the tab through the helper; fall back to osascript with no group."""
    sid = own_iterm_session()
    cmd = ["uv", "run", "-q", "--with", "iterm2", "python", HELPER, "start", "--name", name, "--command", command]
    if sid:
        cmd += ["--session", sid]
    if group:
        cmd += ["--group", group]
        if color:
            cmd += ["--group-color", color]
    rc, out, err = run(cmd, timeout=HELPER_TIMEOUT)
    why = one_line(err) or "exit %d" % rc
    if rc == 0:
        try:
            res = json.loads(one_line(out))
            tab = "iterm2:" + res["session_id"]
            if res.get("warning"):
                print("launcher: made no tab group: %s" % res["warning"], file=sys.stderr)
            return tab, res.get("tab_group")
        except (ValueError, KeyError, TypeError):
            why = "the helper printed no session id"
    rc, out, err = run(["osascript", "-", "start", sid, command, name], stdin=OSA_START)
    uid = one_line(out)
    if rc != 0 or not ITERM_ID_RE.fullmatch(uid):
        raise Fail(
            TERMINAL_STEP,
            "launcher: iTerm2 opened no tab (helper: %s; osascript: %s); the worktree stays at %s"
            % (why, one_line(err) or "exit %d" % rc, worktree),
        )
    print(
        "launcher: made no tab group: the iTerm2 Python API failed (%s), so osascript opened the tab" % why,
        file=sys.stderr,
    )
    return "iterm2:" + uid, None


def start(a):
    terminal = detect_terminal(a.terminal)
    checkout = a.checkout if a.checkout else checkout_for(a.repo)
    checkout = os.path.abspath(os.path.expanduser(checkout))
    worktree, branch, base = make_worktree(checkout, a.name)
    repo = a.repo
    if not repo:
        rc, out, _ = run(["git", "-C", worktree, "config", "--get", "remote.origin.url"])
        repo = repo_from_url(out) if rc == 0 else None
    command = launch_command(worktree, a.name, a.model, a.principal)
    if terminal == "tmux":
        tab, group = tmux_start(a.name, a.group, command, worktree)
    else:
        tab, group = iterm_start(a.name, a.group, a.group_color, command, worktree)
    print(
        json.dumps(
            {
                "session_name": a.name,
                "repo": repo,
                "worktree": worktree,
                "branch": branch,
                "base": base,
                "model": a.model,
                "terminal": terminal,
                "tab": tab,
                "tab_group": group,
            }
        )
    )
    return OK


# -- groups -----------------------------------------------------------------


def groups(_a):
    terminal = detect_terminal()
    if terminal == "tmux":
        rc, out, _ = run(["tmux", "list-sessions", "-F", "#{session_id}\t#{session_name}"])
        if rc != 0:
            return OK  # no tmux server: no session, no group
        for line in out.splitlines():
            if "\t" not in line:
                continue
            gid, name = line.split("\t", 1)
            print(json.dumps({"window_id": None, "group_id": gid, "name": name, "color": None}))
        return OK
    rc, out, err = run(["uv", "run", "-q", "--with", "iterm2", "python", HELPER, "groups"], timeout=HELPER_TIMEOUT)
    rows = []
    if rc == 0:
        try:
            rows = [json.loads(l) for l in out.splitlines() if l.strip()]
        except ValueError:
            rc, err = 1, "the helper printed a line that is not JSON"
    if rc != 0:
        print(
            "launcher: no tab groups to list: the iTerm2 Python API failed (%s)" % (one_line(err) or "exit %d" % rc),
            file=sys.stderr,
        )
        return OK
    for r in rows:
        print(json.dumps({k: r.get(k) for k in ("window_id", "group_id", "name", "color")}))
    return OK


# -- focus and stop -----------------------------------------------------------


def split_handle(handle):
    kind, _, ref = handle.partition(":")
    if kind == "iterm2" and ITERM_ID_RE.fullmatch(ref):
        return kind, ref
    if kind == "tmux" and PANE_RE.fullmatch(ref):
        return kind, ref
    raise Fail(BAD_HANDLE, "launcher: unknown handle %r; a handle is iterm2:<session id> or tmux:<pane id>" % handle)


def tmux_pane_exists(pane):
    rc, _, _ = run(["tmux", "display-message", "-p", "-t", pane, "#{session_name}"])
    return rc == 0


def iterm_script(script, verb, ref):
    rc, out, err = run(["osascript", "-", verb, ref], stdin=script)
    if rc != 0:
        raise Fail(TERMINAL_STEP, "launcher: osascript failed for iterm2:%s: %s" % (ref, one_line(err) or "exit %d" % rc))
    return one_line(out)


def focus(a):
    kind, ref = split_handle(a.handle)
    if kind == "iterm2":
        if iterm_script(OSA_FOCUS, "focus", ref) != "ok":
            raise Fail(BAD_HANDLE, "launcher: no iTerm2 session %s" % ref)
        return OK
    if not tmux_pane_exists(ref):
        raise Fail(BAD_HANDLE, "launcher: no tmux pane %s" % ref)
    run(["tmux", "select-window", "-t", ref])
    run(["tmux", "select-pane", "-t", ref])
    if os.environ.get("TMUX"):
        run(["tmux", "switch-client", "-t", ref])
    else:
        rc, out, _ = run(["tmux", "list-clients", "-F", "#{client_name}"])
        client = one_line(out) if rc == 0 else ""
        if client:
            run(["tmux", "switch-client", "-c", client, "-t", ref])
    return OK


def stop(a):
    kind, ref = split_handle(a.handle)
    if kind == "iterm2":
        if iterm_script(OSA_STOP, "stop", ref) != "ok":
            print("launcher: %s was already gone" % a.handle)
        return OK
    if not tmux_pane_exists(ref):
        print("launcher: %s was already gone" % a.handle)
        return OK
    rc, _, err = run(["tmux", "kill-pane", "-t", ref])
    if rc != 0:
        raise Fail(TERMINAL_STEP, "launcher: tmux kill-pane %s failed: %s" % (ref, one_line(err) or "exit %d" % rc))
    return OK


def main(argv):
    try:
        a = parse(argv)
        return {"start": start, "groups": groups, "focus": focus, "stop": stop}[a.cmd](a)
    except Fail as f:
        print(f.line, file=sys.stderr)
        return f.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

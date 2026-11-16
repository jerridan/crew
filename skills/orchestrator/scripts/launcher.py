#!/usr/bin/env python3
"""The launcher of crew:orchestrator: start, list, focus and stop implementers.

usage:
  launcher.py start --name <session-name> [--model <model>]
                    [--settings <file-or-json>] --principal <name>
                    [--repo <owner/repo>] [--checkout <path>]
                    [--group <name>] [--group-color <#rrggbb>]
                    [--terminal iterm2|tmux]
  launcher.py resume --name <session-name> --worktree <path>
                     [--session-id <id>] [--model <model>]
                     [--settings <file-or-json>] [--repo <owner/repo>]
                     [--group <name>] [--group-color <#rrggbb>]
                     [--terminal iterm2|tmux]
  launcher.py groups
  launcher.py find <session-name> [--worktree <path>]
  launcher.py focus <handle>
  launcher.py stop <handle>
  launcher.py remove <worktree> [--delete-branch]

skills/orchestrator/references/launcher.md owns the arguments, the start
output and the exit codes. This file uses the standard library only. The
iTerm2 Python API runs in iterm2-tabs.py, through `uv run --with iterm2`.
"""

import argparse
import json
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import uuid

OK, USAGE, NO_CHECKOUT, NO_TERMINAL, GIT, TERMINAL_STEP, BAD_HANDLE = 0, 2, 3, 4, 5, 6, 7
OPEN_TAB, REFUSED = 8, 9

HERE = os.path.dirname(os.path.abspath(__file__))
HELPER = os.path.join(HERE, "iterm2-tabs.py")
HELPER_TIMEOUT = 120
# The helper stops itself this many seconds before the launcher kills it.
HELPER_MARGIN = 20
# stop waits this many seconds for the claude of the tab to end after /exit.
STOP_WAIT = 15
# remove waits this many seconds after TERM before it sends KILL.
REMOVE_WAIT = 10

START_USAGE = (
    "usage: launcher.py start --name <session-name> [--model <model>] "
    "[--settings <file-or-json>] --principal <name> "
    "[--repo <owner/repo>] [--checkout <path>] "
    "[--group <name>] [--group-color <#rrggbb>] [--terminal iterm2|tmux]"
)
RESUME_USAGE = (
    "usage: launcher.py resume --name <session-name> --worktree <path> "
    "[--session-id <id>] [--model <model>] [--settings <file-or-json>] "
    "[--repo <owner/repo>] [--group <name>] [--group-color <#rrggbb>] "
    "[--terminal iterm2|tmux]"
)
USAGE_LINE = (
    "usage: launcher.py start ... | resume ... | groups | find <session-name> "
    "| focus <handle> | stop <handle> | remove <worktree>"
)

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
    set oldTab to current tab of w
    tell w to set newTab to (create tab with default profile)
    set s to current session of newTab
    tell s
      set name to nm
      write text cmd
    end tell
    -- create tab selects the new tab: select the tab of before again.
    tell oldTab to select
    return unique id of s
  end tell
end run
"""

# One line per session: its unique id and its tty. Never its name: Claude Code
# changes the name that a tab shows.
OSA_TTYS = """on run argv
  set out to ""
  tell application "iTerm2"
    repeat with w in windows
      repeat with t in tabs of w
        repeat with s in sessions of t
          set out to out & (unique id of s) & " " & (tty of s) & linefeed
        end repeat
      end repeat
    end repeat
  end tell
  return out
end run
"""

# Type /exit into the session. Return its tty, or "gone".
OSA_EXIT = """on run argv
  tell application "iTerm2"
    repeat with w in windows
      repeat with t in tabs of w
        repeat with s in sessions of t
          if unique id of s is item 2 of argv then
            tell s to write text "/exit"
            return tty of s
          end if
        end repeat
      end repeat
    end repeat
  end tell
  return "gone"
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


def run(cmd, cwd=None, stdin=None, timeout=None, env=None):
    """Run a command. Return (exit code, stdout, stderr); 127 when it is missing.

    The command runs in its own process group. On a timeout the launcher kills
    the whole group: `uv run` starts python as a child, and a child that
    stays could open a second tab after the fallback opened one.
    """
    try:
        p = subprocess.Popen(
            cmd,
            cwd=cwd,
            env=env,
            stdin=subprocess.PIPE if stdin is not None else subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            start_new_session=True,
        )
    except FileNotFoundError:
        return 127, "", "%s: command not found" % cmd[0]
    except OSError as e:
        return 127, "", "%s: cannot run: %s" % (cmd[0], e.strerror or e)
    try:
        out, err = p.communicate(stdin, timeout=timeout)
    except subprocess.TimeoutExpired as e:
        try:
            os.killpg(p.pid, signal.SIGKILL)
        except OSError:
            p.kill()
        # Keep what the command printed before the kill: a helper says on
        # stdout when its tab opened.
        try:
            out, _ = p.communicate(timeout=5)
        except subprocess.TimeoutExpired:
            out = e.stdout
        out = out or ""
        if isinstance(out, bytes):
            out = out.decode("utf-8", "replace")
        return 124, out, "%s: timed out after %d seconds" % (cmd[0], timeout)
    return p.returncode, out, err


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
    s.add_argument("--model", default="opus")
    s.add_argument("--settings")
    s.add_argument("--principal", required=True)
    s.add_argument("--repo")
    s.add_argument("--checkout")
    s.add_argument("--group")
    s.add_argument("--group-color")
    s.add_argument("--terminal", choices=["iterm2", "tmux"])
    r = sub.add_parser("resume", add_help=False)
    r.usage_line = RESUME_USAGE
    r.add_argument("--name", required=True)
    r.add_argument("--worktree", required=True)
    r.add_argument("--session-id")
    r.add_argument("--model", default="opus")
    r.add_argument("--settings")
    r.add_argument("--repo")
    r.add_argument("--group")
    r.add_argument("--group-color")
    r.add_argument("--terminal", choices=["iterm2", "tmux"])
    g = sub.add_parser("groups", add_help=False)
    g.usage_line = "usage: launcher.py groups"
    f = sub.add_parser("find", add_help=False)
    f.usage_line = "usage: launcher.py find <session-name> [--worktree <path>]"
    f.add_argument("session_name")
    f.add_argument("--worktree")
    for verb in ("focus", "stop"):
        h = sub.add_parser(verb, add_help=False)
        h.usage_line = "usage: launcher.py %s <handle>" % verb
        h.add_argument("handle")
    m = sub.add_parser("remove", add_help=False)
    m.usage_line = "usage: launcher.py remove <worktree> [--delete-branch]"
    m.add_argument("worktree")
    m.add_argument("--delete-branch", action="store_true")
    args = top.parse_args(argv)
    if args.cmd is None:
        raise Fail(USAGE, "launcher: no subcommand; " + USAGE_LINE)
    if args.cmd == "start":
        check_start(args)
    if args.cmd == "resume":
        check_resume(args)
    return args


def check_start(a):
    def bad(why):
        raise Fail(USAGE, "launcher: %s; %s" % (why, START_USAGE))

    if not a.repo and not a.checkout:
        bad("give --repo or --checkout")
    check_common(a, bad)


def check_resume(a):
    def bad(why):
        raise Fail(USAGE, "launcher: %s; %s" % (why, RESUME_USAGE))

    if a.session_id is not None and not a.session_id.strip():
        bad("--session-id is empty")
    check_common(a, bad)


def check_common(a, bad):
    """The checks that start and resume share."""
    if not NAME_RE.fullmatch(a.name):
        bad("--name %r does not match [a-z0-9][a-z0-9-]*" % a.name)
    if "eval" in a.name:
        bad("--name %r holds 'eval', which a worktree-isolated session refuses" % a.name)
    if a.group_color is not None and not COLOR_RE.fullmatch(a.group_color):
        bad("--group-color %r is not #rrggbb" % a.group_color)
    a.settings_json = settings_json(a.settings, bad)
    if a.repo is not None and not REPO_RE.fullmatch(a.repo):
        bad("--repo %r is not <owner>/<repo>" % a.repo)
    if a.group is not None and not a.group.strip():
        bad("--group is empty")


def settings_json(value, bad):
    """The --settings JSON for claude: the given object, Remote Control off by default."""
    obj = {}
    if value is not None:
        text = value
        if os.path.isfile(value):
            try:
                with open(value) as f:
                    text = f.read()
            except OSError as e:
                bad("--settings file %s cannot be read: %s" % (value, e))
        try:
            obj = json.loads(text)
        except ValueError:
            bad("--settings %r is not a JSON object or a file that holds one" % value)
        if not isinstance(obj, dict):
            bad("--settings %r is not a JSON object or a file that holds one" % value)
    obj.setdefault("remoteControlAtStartup", False)
    return json.dumps(obj)


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
        if re.match(r"##(?!#)", line):
            # Only a heading with exactly two # ends the section.
            inside = line == "## Checkouts"
            continue
        if line.startswith("#"):
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


def claude_program():
    return os.environ.get("CREW_LAUNCHER_CLAUDE") or "claude"


def launch_command(worktree, name, session_id, model, settings, principal):
    return "cd %s && exec %s --name %s --session-id %s --model %s --settings %s %s" % (
        shlex.quote(worktree),
        shlex.quote(claude_program()),
        shlex.quote(name),
        shlex.quote(session_id),
        shlex.quote(model),
        shlex.quote(settings),
        shlex.quote(WAIT_PROMPT.format(p=principal)),
    )


def resume_command(worktree, session_id, name, model, settings):
    return "cd %s && exec %s --resume %s --name %s --model %s --settings %s" % (
        shlex.quote(worktree),
        shlex.quote(claude_program()),
        shlex.quote(session_id),
        shlex.quote(name),
        shlex.quote(model),
        shlex.quote(settings),
    )


def tmux(args):
    """Run one tmux command with no Claude Code session variable.

    A tmux server that this call starts keeps its environment and passes it
    to every window. A claude in one of those windows must not read the
    CLAUDECODE or CLAUDE_CODE_* values of the session that ran the launcher.
    """
    env = {
        k: v
        for k, v in os.environ.items()
        if k != "CLAUDECODE" and not k.startswith("CLAUDE_CODE_")
    }
    return run(["tmux"] + args, env=env)


def tmux_start(name, group, command, worktree):
    session = group or "crew"
    rc, _, _ = tmux(["has-session", "-t", "=" + session])
    if rc == 0:
        # -d: the new window is not selected, so the current window keeps the focus.
        cmd = ["new-window", "-t", "=%s:" % session, "-n", name, "-P", "-F", "#{pane_id}", "-d", command]
    else:
        cmd = ["new-session", "-d", "-s", session, "-n", name, "-P", "-F", "#{pane_id}", command]
    rc, out, err = tmux(cmd)
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


def helper_lines(out):
    """What the helper's start said: the ids of opened, typed, closed, and the
    result object under session_id. A line that is not that JSON is skipped."""
    said = {}
    for line in (out or "").splitlines():
        try:
            obj = json.loads(line)
        except ValueError:
            continue
        if not isinstance(obj, dict):
            continue
        if isinstance(obj.get("session_id"), str) and ITERM_ID_RE.fullmatch(obj["session_id"]):
            said["session_id"] = obj
        for key in ("opened", "typed", "closed"):
            if isinstance(obj.get(key), str) and ITERM_ID_RE.fullmatch(obj[key]):
                said[key] = obj[key]
    return said


def helper_cmd(verb):
    """The helper command line. Its --deadline ends it before HELPER_TIMEOUT."""
    deadline = max(1, HELPER_TIMEOUT - HELPER_MARGIN)
    return ["uv", "run", "-q", "--with", "iterm2", "python", HELPER, verb, "--deadline", str(deadline)]


def iterm_start(name, group, color, command, worktree):
    """Open the tab through the helper; fall back to osascript with no group."""
    sid = own_iterm_session()
    cmd = helper_cmd("start") + ["--name", name, "--command", command]
    if sid:
        cmd += ["--session", sid]
    if group:
        cmd += ["--group", group]
        if color:
            cmd += ["--group-color", color]
    rc, out, err = run(cmd, timeout=HELPER_TIMEOUT)
    why = one_line(err) or "exit %d" % rc
    said = helper_lines(out)
    res = said.get("session_id")
    if rc == 0 and res is not None:
        if res.get("warning"):
            print("launcher: made no tab group: %s" % res["warning"], file=sys.stderr)
        return "iterm2:" + res["session_id"], res.get("tab_group")
    if rc == 0:
        why = "the helper printed no result line"
    typed = res["session_id"] if res is not None else said.get("typed")
    if typed:
        # The command runs in that tab. A fallback tab would start a second
        # claude in the same worktree.
        print(
            "launcher: made no tab group: the iTerm2 helper failed after it typed the command (%s)" % why,
            file=sys.stderr,
        )
        return "iterm2:" + typed, None
    opened = said.get("opened")
    if opened and said.get("closed") != opened:
        # The tab is open with no command. Close it before the fallback opens
        # the only tab.
        src, sout, serr = run(["osascript", "-", "stop", opened], stdin=OSA_STOP)
        if src != 0 or one_line(sout) not in ("ok", "gone"):
            raise Fail(
                TERMINAL_STEP,
                "launcher: the iTerm2 helper failed (%s) and the tab iterm2:%s it opened did not close (%s); "
                "the worktree stays at %s" % (why, opened, one_line(serr) or "exit %d" % src, worktree),
            )
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
    session_id = str(uuid.uuid4())
    command = launch_command(worktree, a.name, session_id, a.model, a.settings_json, a.principal)
    open_tab(a, terminal, command, worktree, repo, branch, base, session_id)
    return OK


def open_tab(a, terminal, command, worktree, repo, branch, base, session_id):
    """Open the one tab or window, and print the start output line."""
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
                "session_id": session_id,
            }
        )
    )


# -- resume -------------------------------------------------------------------


def encode_path(path):
    """The transcript directory name of a cwd: each character outside
    [A-Za-z0-9] becomes '-'."""
    return re.sub(r"[^A-Za-z0-9]", "-", path)


def newest_transcript(worktree):
    """The id of the newest top-level transcript of the worktree, or None."""
    config = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    folder = os.path.join(config, "projects", encode_path(worktree))
    best = None
    try:
        names = os.listdir(folder)
    except OSError:
        return None
    for n in names:
        path = os.path.join(folder, n)
        if not n.endswith(".jsonl") or not os.path.isfile(path):
            continue
        mtime = os.path.getmtime(path)
        if best is None or mtime > best[0]:
            best = (mtime, n[: -len(".jsonl")])
    return best[1] if best else None


def default_base(worktree):
    out = git(worktree, "ls-remote", "--symref", "origin", "HEAD")
    m = re.search(r"^ref: refs/heads/(\S+)\s+HEAD$", out, re.M)
    if not m:
        raise Fail(GIT, "launcher: origin of %s names no default branch" % worktree)
    return "origin/" + m.group(1)


def resume(a):
    terminal = detect_terminal(a.terminal)
    path = os.path.abspath(os.path.expanduser(a.worktree))
    if not os.path.isdir(path):
        raise Fail(GIT, "launcher: the worktree %s does not exist" % path)
    worktree = os.path.realpath(git(path, "rev-parse", "--show-toplevel").strip())
    session_id = a.session_id or newest_transcript(worktree)
    if not session_id:
        raise Fail(GIT, "launcher: no transcript of %s to resume; give --session-id" % worktree)
    rc, out, _ = run(["git", "-C", worktree, "symbolic-ref", "-q", "--short", "HEAD"])
    branch = one_line(out) if rc == 0 and one_line(out) else None
    base = default_base(worktree)
    tabs = find_tabs(a.name, worktree, terminal)
    if tabs:
        raise Fail(
            OPEN_TAB,
            "launcher: the session %s is open in %s; focus that tab, or stop it first" % (a.name, ", ".join(tabs)),
        )
    repo = a.repo
    if not repo:
        rc, out, _ = run(["git", "-C", worktree, "config", "--get", "remote.origin.url"])
        repo = repo_from_url(out) if rc == 0 else None
    command = resume_command(worktree, session_id, a.name, a.model, a.settings_json)
    open_tab(a, terminal, command, worktree, repo, branch, base, session_id)
    return OK


# -- processes ----------------------------------------------------------------


def processes():
    """Each process, by pid: {"pid", "ppid", "tty" (None for no tty), "argv"}.

    ps prints the argv as one text, so a token holds no space. That is enough
    for --name: a session name holds no space.
    """
    rc, out, err = run(["ps", "-axww", "-o", "pid=,ppid=,tty=,command="])
    if rc != 0:
        raise Fail(TERMINAL_STEP, "launcher: ps failed: %s" % (one_line(err) or "exit %d" % rc))
    procs = {}
    for line in out.splitlines():
        parts = line.split(None, 3)
        if len(parts) < 3 or not parts[0].isdigit() or not parts[1].isdigit():
            continue
        tty = parts[2]
        procs[int(parts[0])] = {
            "pid": int(parts[0]),
            "ppid": int(parts[1]),
            "tty": None if tty in ("??", "?", "-") else norm_tty(tty),
            "argv": parts[3].split() if len(parts) > 3 else [],
        }
    return procs


def cwds():
    """The cwd of each process lsof can read, by pid."""
    _, out, _ = run(["lsof", "-n", "-P", "-w", "-d", "cwd", "-F", "pn"])
    found = {}
    pid = None
    for line in out.splitlines():
        if line.startswith("p") and line[1:].isdigit():
            pid = int(line[1:])
        elif line.startswith("n") and pid is not None:
            found[pid] = line[1:]
    return found


def norm_tty(tty):
    return tty[len("/dev/"):] if tty.startswith("/dev/") else tty


def is_claude(argv):
    if not argv:
        return False
    names = {"claude", os.path.basename(claude_program())}
    return os.path.basename(argv[0]) in names


def has_name(argv, name):
    return any(argv[i] == "--name" and argv[i + 1] == name for i in range(len(argv) - 1))


def inside(path, root):
    return path == root or path.startswith(root.rstrip("/") + "/")


# -- find -----------------------------------------------------------------------


def terminal_ttys(terminal):
    """[(handle, tty)] of every open tab or pane."""
    if terminal == "tmux":
        rc, out, _ = tmux(["list-panes", "-a", "-F", "#{pane_id} #{pane_tty}"])
        if rc != 0:
            return []  # no tmux server: no pane
        rows = []
        for line in out.splitlines():
            parts = line.split()
            if len(parts) == 2 and PANE_RE.fullmatch(parts[0]):
                rows.append(("tmux:" + parts[0], norm_tty(parts[1])))
        return rows
    rc, out, err = run(["osascript", "-", "ttys"], stdin=OSA_TTYS)
    if rc != 0:
        raise Fail(TERMINAL_STEP, "launcher: osascript could not list the iTerm2 sessions: %s" % (one_line(err) or "exit %d" % rc))
    rows = []
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 2 and ITERM_ID_RE.fullmatch(parts[0]):
            rows.append(("iterm2:" + parts[0], norm_tty(parts[1])))
    return rows


def find_tabs(name, worktree, terminal):
    """The handle of each open tab or pane that holds this implementer."""
    tabs = terminal_ttys(terminal)
    if not tabs:
        return []
    procs = processes()
    where = cwds() if worktree else {}
    found = []
    for handle, tty in tabs:
        for p in procs.values():
            if p["tty"] != tty or not is_claude(p["argv"]):
                continue
            if has_name(p["argv"], name) or (worktree and where.get(p["pid"]) == worktree):
                found.append(handle)
                break
    return found


def find(a):
    terminal = detect_terminal()
    worktree = os.path.realpath(os.path.expanduser(a.worktree)) if a.worktree else None
    for handle in find_tabs(a.session_name, worktree, terminal):
        print(handle)
    return OK


# -- groups -----------------------------------------------------------------


def groups(_a):
    terminal = detect_terminal()
    if terminal == "tmux":
        rc, out, _ = tmux(["list-sessions", "-F", "#{session_id}\t#{session_name}"])
        if rc != 0:
            return OK  # no tmux server: no session, no group
        for line in out.splitlines():
            if "\t" not in line:
                continue
            gid, name = line.split("\t", 1)
            print(json.dumps({"window_id": None, "group_id": gid, "name": name, "color": None}))
        return OK
    rc, out, err = run(helper_cmd("groups"), timeout=HELPER_TIMEOUT)
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
    rc, _, _ = tmux(["display-message", "-p", "-t", pane, "#{session_name}"])
    return rc == 0


def tmux_pane_tty(pane):
    """The tty of the pane, or None when the pane does not exist."""
    rc, out, _ = tmux(["display-message", "-p", "-t", pane, "#{pane_tty}"])
    return norm_tty(one_line(out)) if rc == 0 and one_line(out) else None


def wait_claude_gone(tty, handle):
    """Wait up to STOP_WAIT seconds until no claude process has the tty."""
    end = time.time() + STOP_WAIT
    while True:
        if not any(p["tty"] == tty and is_claude(p["argv"]) for p in processes().values()):
            return
        if time.time() >= end:
            print(
                "launcher: the claude session in %s did not end %d seconds after /exit; the tab closes now"
                % (handle, STOP_WAIT),
                file=sys.stderr,
            )
            return
        time.sleep(0.5)


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
    tmux(["select-window", "-t", ref])
    tmux(["select-pane", "-t", ref])
    if os.environ.get("TMUX"):
        tmux(["switch-client", "-t", ref])
    else:
        rc, out, _ = tmux(["list-clients", "-F", "#{client_name}"])
        client = one_line(out) if rc == 0 else ""
        if client:
            tmux(["switch-client", "-c", client, "-t", ref])
    return OK


def stop(a):
    """Type /exit, wait for claude to end, then close the tab or kill the pane.

    /exit ends the session with the reason prompt_input_exit, so a tool that
    restores closed sessions does not start it again.
    """
    kind, ref = split_handle(a.handle)
    if kind == "iterm2":
        tty = iterm_script(OSA_EXIT, "exit", ref)
        if tty == "gone" or not tty:
            print("launcher: %s was already gone" % a.handle)
            return OK
        wait_claude_gone(norm_tty(tty), a.handle)
        iterm_script(OSA_STOP, "stop", ref)  # "gone" here: the tab closed when claude ended
        return OK
    tty = tmux_pane_tty(ref)
    if tty is None:
        print("launcher: %s was already gone" % a.handle)
        return OK
    tmux(["send-keys", "-t", ref, "-l", "/exit"])
    tmux(["send-keys", "-t", ref, "Enter"])
    wait_claude_gone(tty, a.handle)
    if not tmux_pane_exists(ref):
        return OK  # the pane closed when claude ended
    rc, _, err = tmux(["kill-pane", "-t", ref])
    if rc != 0:
        raise Fail(TERMINAL_STEP, "launcher: tmux kill-pane failed for tmux:%s: %s" % (ref, one_line(err) or "exit %d" % rc))
    return OK


# -- remove -------------------------------------------------------------------


def linked_worktree(path):
    """(real worktree path, main worktree path) of a linked worktree.

    Raise Fail(USAGE) when the path is not the top level of a linked
    worktree: a missing path, a plain directory, or the main worktree.
    """
    def bad(why):
        raise Fail(USAGE, "launcher: %s is not a linked worktree (%s); usage: launcher.py remove <worktree> [--delete-branch]" % (path, why))

    if not os.path.isdir(path):
        bad("no such directory")
    rc, out, _ = run(["git", "-C", path, "rev-parse", "--show-toplevel", "--git-dir", "--git-common-dir"])
    lines = out.splitlines()
    if rc != 0 or len(lines) != 3:
        bad("not in a git work tree")
    top = os.path.realpath(lines[0])
    if top != os.path.realpath(path):
        bad("not the top level of its work tree")
    gitdir = os.path.realpath(os.path.join(path, lines[1]))
    common = os.path.realpath(os.path.join(path, lines[2]))
    if gitdir == common:
        bad("the main worktree")
    out = git(path, "worktree", "list", "--porcelain")
    m = re.match(r"worktree (.+)", out)
    if not m:
        raise Fail(GIT, "launcher: git worktree list named no main worktree for %s" % path)
    return top, m.group(1)


def proc_row(p, keys):
    row = {"pid": p["pid"], "tty": p["tty"], "command": " ".join(p["argv"])}
    return {k: row[k] for k in keys}


def alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def signal_all(pids, sig):
    for pid in pids:
        try:
            os.kill(pid, sig)
        except OSError:
            pass


def remove(a):
    path = os.path.abspath(os.path.expanduser(a.worktree))
    worktree, main_tree = linked_worktree(path)
    rc, out, _ = run(["git", "-C", worktree, "symbolic-ref", "-q", "--short", "HEAD"])
    branch = one_line(out) if rc == 0 and one_line(out) else None
    changed = [l for l in git(worktree, "status", "--porcelain").splitlines() if l.strip()]

    procs = processes()
    where = cwds()
    where[os.getpid()] = os.path.realpath(os.getcwd())
    # The launcher and each process above it.
    mine = set()
    pid = os.getpid()
    while pid and pid not in mine:
        mine.add(pid)
        pid = procs[pid]["ppid"] if pid in procs else 0
    in_tree = [
        procs[pid]
        for pid in sorted(where)
        if pid in procs and inside(where[pid], worktree) and procs[pid]["ppid"] != os.getpid()
    ]
    # A process with a terminal, or the launcher and its ancestors, makes remove refuse.
    blockers = [p for p in in_tree if p["tty"] is not None or p["pid"] in mine]
    refused = bool(changed or blockers)

    result = {
        "worktree": worktree,
        "removed": False,
        "stopped": [],
        # A refusal keeps every process in the worktree running.
        "kept": [proc_row(p, ("pid", "tty", "command")) for p in in_tree] if refused else [],
        "changed": changed,
        "branch": branch,
        "branch_deleted": False,
    }
    if refused:
        why = []
        if changed:
            why.append("%d changed or untracked files" % len(changed))
        if blockers:
            why.append(
                "%d processes with a terminal or that run this command (pids %s)"
                % (len(blockers), ", ".join(str(p["pid"]) for p in blockers))
            )
        print(json.dumps(result))
        raise Fail(REFUSED, "launcher: kept the worktree %s: %s" % (worktree, "; ".join(why)))

    pids = [p["pid"] for p in in_tree]
    signal_all(pids, signal.SIGTERM)
    end = time.time() + REMOVE_WAIT
    while any(alive(pid) for pid in pids) and time.time() < end:
        time.sleep(0.2)
    signal_all([pid for pid in pids if alive(pid)], signal.SIGKILL)
    result["stopped"] = [proc_row(p, ("pid", "command")) for p in in_tree]

    def git_step(*args):
        try:
            git(main_tree, *args)
        except Fail:
            print(json.dumps(result))
            raise

    git_step("worktree", "remove", worktree)
    result["removed"] = True
    if a.delete_branch and branch:
        git_step("branch", "-D", branch)
        result["branch_deleted"] = True
    print(json.dumps(result))
    return OK


def main(argv):
    try:
        a = parse(argv)
        verbs = {
            "start": start,
            "resume": resume,
            "groups": groups,
            "find": find,
            "focus": focus,
            "stop": stop,
            "remove": remove,
        }
        return verbs[a.cmd](a)
    except Fail as f:
        print(f.line, file=sys.stderr)
        return f.code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

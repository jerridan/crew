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
  launcher.py find <session-name> [--worktree <path>] [--session-id <id>]
  launcher.py focus <handle>
  launcher.py stop <handle> [--name <session-name>] [--session-id <id>]
  launcher.py remove <worktree> [--delete-branch [--pr <number>]]
                     [--stop-processes]

skills/orchestrator/references/launcher.md owns the arguments, the start
output and the exit codes. This file uses the standard library only. The
iTerm2 Python API runs in iterm2-tabs.py, through `uv run --with iterm2`.
"""

import argparse
import calendar
import glob
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
# After the close, stop waits this many seconds for each claude that was still
# on the tty to end.
STOP_CLOSE_WAIT = 15
# remove waits this many seconds for a claude with no terminal in the
# worktree to end, such as a session that /exit is ending.
REMOVE_END_WAIT = 15
# remove waits this many seconds after TERM before it sends KILL.
REMOVE_WAIT = 10
# Seconds remove waits after KILL before it reads the processes again.
KILL_WAIT = 2
# stop waits this many seconds after Escape and after Ctrl-U.
KEY_WAIT = 0.5

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
REMOVE_USAGE = "usage: launcher.py remove <worktree> [--delete-branch [--pr <number>]] [--stop-processes]"
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
    "SendMessage, not to this tab. A later message from the orchestrator can "
    "come from a new name: send to that name from then on. Answer this "
    "message with one line and then wait."
)

NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
COLOR_RE = re.compile(r"#[0-9a-fA-F]{6}")
REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
PANE_RE = re.compile(r"%[0-9]+")
# The pid in a worktree lock reason: the word pid, a space and 1 to 10 digits.
PID_RE = re.compile(r"\bpid ([0-9]{1,10})\b")
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

# Send Escape, then Ctrl-U, then type /exit into the session. Escape rejects a
# permission dialog or interrupts a turn; Ctrl-U clears the input line. Return
# its tty, or "gone". stop puts KEY_WAIT in place of {pause}.
OSA_EXIT = """on run argv
  tell application "iTerm2"
    repeat with w in windows
      repeat with t in tabs of w
        repeat with s in sessions of t
          if unique id of s is item 2 of argv then
            tell s to write text (ASCII character 27) newline NO
            delay {pause}
            tell s to write text (ASCII character 21) newline NO
            delay {pause}
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
    f.usage_line = "usage: launcher.py find <session-name> [--worktree <path>] [--session-id <id>]"
    f.add_argument("session_name")
    f.add_argument("--worktree")
    f.add_argument("--session-id")
    h = sub.add_parser("focus", add_help=False)
    h.usage_line = "usage: launcher.py focus <handle>"
    h.add_argument("handle")
    h = sub.add_parser("stop", add_help=False)
    h.usage_line = "usage: launcher.py stop <handle> [--name <session-name>] [--session-id <id>]"
    h.add_argument("handle")
    h.add_argument("--name")
    h.add_argument("--session-id")
    m = sub.add_parser("remove", add_help=False)
    m.usage_line = REMOVE_USAGE
    m.add_argument("worktree")
    m.add_argument("--delete-branch", action="store_true")
    m.add_argument("--pr")
    m.add_argument("--stop-processes", action="store_true")
    args = top.parse_args(argv)
    if args.cmd is None:
        raise Fail(USAGE, "launcher: no subcommand; " + USAGE_LINE)
    if args.cmd == "start":
        check_start(args)
    if args.cmd == "resume":
        check_resume(args)
    if args.cmd == "remove":
        check_remove(args)
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


def check_remove(a):
    def bad(why):
        raise Fail(USAGE, "launcher: %s; %s" % (why, REMOVE_USAGE))

    if a.pr is not None:
        if not a.delete_branch:
            bad("--pr needs --delete-branch")
        if not re.fullmatch(r"[0-9]{1,10}", a.pr) or int(a.pr) == 0:
            bad("--pr %r is not a positive integer" % a.pr)
        a.pr = int(a.pr)


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
    tabs = find_tabs(a.name, worktree, terminal, session_id)
    if tabs:
        raise Fail(
            OPEN_TAB,
            "launcher: the session %s is open in %s; focus that tab, or stop it first"
            % (a.name, ", ".join(h for h, _ in tabs)),
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
    """The cwd of each process lsof can read, by pid.

    A failed lsof is an error, never an empty answer: an empty answer would
    let remove and find see no process in a worktree.
    """
    rc, out, err = run(["lsof", "-n", "-P", "-w", "-d", "cwd", "-F", "pn"])
    if rc != 0:
        raise Fail(TERMINAL_STEP, "launcher: lsof failed: %s" % (one_line(err) or "exit %d" % rc))
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
    """A claude process: the program claude or $CREW_LAUNCHER_CLAUDE, or node
    that runs an npm install of claude."""
    if not argv:
        return False
    names = {"claude", os.path.basename(claude_program())}
    if os.path.basename(argv[0]) in names:
        return True
    if os.path.basename(argv[0]) == "node" and len(argv) > 1:
        script = argv[1]
        return script.endswith("/claude") or script.endswith("@anthropic-ai/claude-code/cli.js")
    return False


def has_pair(argv, flag, value):
    return any(argv[i] == flag and argv[i + 1] == value for i in range(len(argv) - 1))


def has_name(argv, name):
    return has_pair(argv, "--name", name)


def has_id(argv, session_id):
    return has_pair(argv, "--resume", session_id) or has_pair(argv, "--session-id", session_id)


def match_kind(procs, where, tty, name, worktree, session_id=None):
    """How a claude process on the tty matches the implementer, or None.

    "name": it has --name <name>. "id": it has --resume <session_id> or
    --session-id <session_id>. "cwd": its cwd is the worktree. The first
    kind that holds wins.
    """
    mine = [p for p in procs.values() if p["tty"] == tty and is_claude(p["argv"])]
    if name and any(has_name(p["argv"], name) for p in mine):
        return "name"
    if session_id and any(has_id(p["argv"], session_id) for p in mine):
        return "id"
    if worktree and any(where.get(p["pid"]) == worktree for p in mine):
        return "cwd"
    return None


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


def find_tabs(name, worktree, terminal, session_id=None):
    """[(handle, how)] of each open tab or pane that holds this implementer.

    how is "name", "id" or "cwd", as match_kind says.
    """
    tabs = terminal_ttys(terminal)
    if not tabs:
        return []
    procs = processes()
    where = cwds() if worktree else {}
    found = []
    for handle, tty in tabs:
        how = match_kind(procs, where, tty, name, worktree, session_id)
        if how:
            found.append((handle, how))
    return found


def find(a):
    terminal = detect_terminal()
    worktree = os.path.realpath(os.path.expanduser(a.worktree)) if a.worktree else None
    for handle, how in find_tabs(a.session_name, worktree, terminal, a.session_id):
        print("%s %s" % (handle, how))
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
    """Wait up to STOP_WAIT seconds until no claude process has the tty.

    Return {pid: argv} of each claude process on the tty at the last read.
    """
    end = time.time() + STOP_WAIT
    while True:
        left = {
            p["pid"]: p["argv"] for p in processes().values() if p["tty"] == tty and is_claude(p["argv"])
        }
        if not left:
            return left
        if time.time() >= end:
            print(
                "launcher: the claude session in %s did not end %d seconds after /exit; the tab closes now"
                % (handle, STOP_WAIT),
                file=sys.stderr,
            )
            return left
        time.sleep(0.5)


def wait_pids_gone(left, handle):
    """After the close, wait up to STOP_CLOSE_WAIT seconds until each pid of
    left ({pid: argv}) is gone. A pid is gone when ps does not show it, or
    shows it with another argv: a new process with a reused pid. stop sends
    no signal. One stderr line names each pid that still runs at the end."""
    end = time.time() + STOP_CLOSE_WAIT
    while True:
        procs = processes()
        still = sorted(pid for pid in left if pid in procs and procs[pid]["argv"] == left[pid])
        if not still or time.time() >= end:
            break
        time.sleep(0.5)
    for pid in still:
        print(
            "launcher: the claude process %d of %s still runs %d seconds after the close; stop sent it no signal"
            % (pid, handle, STOP_CLOSE_WAIT),
            file=sys.stderr,
        )


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


def iterm_tty(ref):
    """The tty of the iTerm2 session, or None when the session does not exist."""
    for handle, tty in terminal_ttys("iterm2"):
        if handle == "iterm2:" + ref:
            return tty
    return None


def holds_target(a, tty):
    """With --name or --session-id: True when a claude on the tty has the
    match name or id, as find matches it. A cwd match never counts: a person
    can start a claude in the worktree. Without either flag: True. A tmux
    pane id restarts at %0 with a new tmux server, so an old handle can name
    another pane."""
    if not a.name and not a.session_id:
        return True
    return match_kind(processes(), {}, tty, a.name, None, a.session_id) in ("name", "id")


def not_target(a):
    want = " or ".join(
        x for x in (a.name and "--name " + a.name, a.session_id and "the session id " + a.session_id) if x
    )
    print("launcher: %s holds no claude session with %s; stop sent no key and closed nothing" % (a.handle, want))
    return OK


def stop(a):
    """Type /exit, wait for claude to end, close the tab or kill the pane,
    then wait for each claude that was still on the tty to end.

    /exit ends the session with the reason prompt_input_exit, so a tool that
    restores closed sessions does not start it again. Escape and Ctrl-U come
    first: Enter on a permission dialog would approve it, and text in the
    input line would go to the model with /exit. With --name or --session-id,
    stop sends no key and closes nothing unless the target holds that
    session.
    """
    kind, ref = split_handle(a.handle)
    if kind == "iterm2":
        if a.name or a.session_id:
            tty = iterm_tty(ref)
            if tty is None:
                print("launcher: %s was already gone" % a.handle)
                return OK
            if not holds_target(a, tty):
                return not_target(a)
        tty = iterm_script(OSA_EXIT.replace("{pause}", str(KEY_WAIT)), "exit", ref)
        if tty == "gone" or not tty:
            print("launcher: %s was already gone" % a.handle)
            return OK
        left = wait_claude_gone(norm_tty(tty), a.handle)
        iterm_script(OSA_STOP, "stop", ref)  # "gone" here: the tab closed when claude ended
        if left:
            wait_pids_gone(left, a.handle)
        return OK
    tty = tmux_pane_tty(ref)
    if tty is None:
        print("launcher: %s was already gone" % a.handle)
        return OK
    if not holds_target(a, tty):
        return not_target(a)
    tmux(["send-keys", "-t", ref, "Escape"])
    time.sleep(KEY_WAIT)
    tmux(["send-keys", "-t", ref, "C-u"])
    time.sleep(KEY_WAIT)
    tmux(["send-keys", "-t", ref, "-l", "/exit"])
    tmux(["send-keys", "-t", ref, "Enter"])
    left = wait_claude_gone(tty, a.handle)
    if tmux_pane_exists(ref):
        rc, _, err = tmux(["kill-pane", "-t", ref])
        if rc != 0:
            raise Fail(TERMINAL_STEP, "launcher: tmux kill-pane failed for tmux:%s: %s" % (ref, one_line(err) or "exit %d" % rc))
    # else: the pane closed when claude ended.
    if left:
        wait_pids_gone(left, a.handle)
    return OK


# -- remove -------------------------------------------------------------------


def linked_worktree(path):
    """(real worktree path, main worktree path, git dir) of a linked worktree.

    Raise Fail(USAGE) when the path is not the top level of a linked
    worktree: a missing path, a plain directory, or the main worktree.
    """
    def bad(why):
        raise Fail(
            USAGE,
            "launcher: %s is not a linked worktree (%s); %s" % (path, why, REMOVE_USAGE),
        )

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
    return top, m.group(1), gitdir


def proc_row(p, keys):
    row = {"pid": p["pid"], "tty": p["tty"], "command": " ".join(p["argv"])}
    return {k: row[k] for k in keys}


def alive(pid):
    """Signal 0 only tests the pid; it sends nothing to the process."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def still_found(found):
    """The pids of found that ps and lsof show now with the same argv and cwd.

    A pid that runs another command, or has another cwd, is a new process
    with a reused pid, or the process changed. remove never signals it.
    found: {pid: (argv, cwd)}.
    """
    procs = processes()
    where = cwds()
    return [
        pid
        for pid in sorted(found)
        if pid in procs and procs[pid]["argv"] == found[pid][0] and where.get(pid) == found[pid][1]
    ]


def signal_found(found, sig):
    """Read the processes again, then send sig to each pid that still matches.

    A pid that cannot get the signal (PermissionError) stays running, and the
    read after KILL finds it.
    """
    for pid in still_found(found):
        try:
            os.kill(pid, sig)
        except (ProcessLookupError, PermissionError):
            pass


def scan(worktree, stop_processes):
    """Read the processes of the worktree, by the rule of step 1.

    Return (procs, where, in_tree, blockers, mine). mine holds the launcher
    and each process above it.
    """
    procs = processes()
    where = cwds()
    where[os.getpid()] = os.path.realpath(os.getcwd())
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
    # A process with a terminal, or the launcher and its ancestors, makes remove
    # refuse. Without --stop-processes, every process in the worktree does: a
    # GUI editor has no terminal either, and nothing tells it apart from a
    # server that the implementer left.
    blockers = [p for p in in_tree if not stop_processes or p["tty"] is not None or p["pid"] in mine]
    return procs, where, in_tree, blockers, mine


def all_ending(blockers, mine):
    """True when each blocker is a claude with no terminal that is not the
    launcher or above it: an implementer session that /exit is ending."""
    return bool(blockers) and all(
        p["tty"] is None and is_claude(p["argv"]) and p["pid"] not in mine for p in blockers
    )


def worktree_list(text):
    """The blocks of `git worktree list --porcelain` text: one dict per
    worktree, with "worktree", and "branch" and "locked" when the block has
    them. "locked" is the reason, or "" for a lock with no reason."""
    blocks = []
    cur = None
    for line in text.splitlines():
        if line.startswith("worktree "):
            cur = {"worktree": line[len("worktree "):]}
            blocks.append(cur)
        elif cur is None:
            continue
        elif line.startswith("branch refs/heads/"):
            cur["branch"] = line[len("branch refs/heads/"):]
        elif line == "locked":
            cur["locked"] = ""
        elif line.startswith("locked "):
            cur["locked"] = line[len("locked "):]
    return blocks


def lock_owner(reason):
    """The pid that the lock reason names, or None when it names none or more
    than one. A pid is the word pid, a space and 1 to 10 digits."""
    pids = PID_RE.findall(reason)
    return int(pids[0]) if len(pids) == 1 else None


def pid_dead(pid):
    """True only when no process has the pid. Signal 0 sends nothing. A pid
    that runs, that another user owns, or that the system cannot test, is
    not proven dead."""
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except (OSError, OverflowError, ValueError):
        return False
    return False


def record_root():
    return os.environ.get("CREW_RECORD_ROOT") or os.path.expanduser("~/.claude/crew")


def load_json(path):
    """The parsed file, or None after one stderr line when it cannot be read
    or parsed."""
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        print("launcher: skipped the goal record file %s: it cannot be read or parsed (%s)" % (path, e), file=sys.stderr)
        return None


def utc_seconds(text):
    """Seconds since the epoch of an ISO-8601 UTC time such as
    2026-11-17T14:53:32Z, with or without fractional seconds, or None."""
    if not isinstance(text, str):
        return None
    m = re.fullmatch(r"(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})(\.\d+)?(Z|\+00:00)", text)
    if not m:
        return None
    try:
        return calendar.timegm(time.strptime(m.group(1), "%Y-%m-%dT%H:%M:%S"))
    except ValueError:
        return None


def record_branches(worktree, made):
    """Each branch that a goal record of the worktree names: each
    deliverables[].branch of its state.json, then each branch value of the
    worktrees.json beside it. A goal record of the worktree has run.repo,
    with each symlink resolved, equal to the worktree; run.kind absent or not
    review; and run.created_at at or after made, the time git made the
    worktree. An older record is of an earlier item at the same path. made
    is None when that time cannot be read: then no record counts."""
    names = []
    for path in sorted(glob.glob(os.path.join(glob.escape(record_root()), "*", "state.json"))):
        state = load_json(path)
        if state is None:
            continue
        run_ = state.get("run") if isinstance(state, dict) else None
        if not isinstance(run_, dict) or not isinstance(run_.get("repo"), str):
            continue
        if os.path.realpath(os.path.expanduser(run_["repo"])) != worktree or run_.get("kind") == "review":
            continue
        created = utc_seconds(run_.get("created_at"))
        if created is None:
            print("launcher: skipped the goal record %s: its run.created_at is missing or does not parse" % path, file=sys.stderr)
            continue
        # created_at has whole seconds, so compare with the whole second of made.
        if made is None or created < int(made):
            continue
        deliverables = state.get("deliverables")
        for d in deliverables if isinstance(deliverables, list) else []:
            if isinstance(d, dict) and isinstance(d.get("branch"), str):
                names.append(d["branch"])
        wpath = os.path.join(os.path.dirname(path), "worktrees.json")
        if not os.path.exists(wpath):
            continue
        entries = load_json(wpath)
        for e in entries.values() if isinstance(entries, dict) else []:
            if isinstance(e, dict) and isinstance(e.get("branch"), str):
                names.append(e["branch"])
    return names


def default_branch(top):
    """The branch that refs/remotes/origin/HEAD names, else the one that
    `git ls-remote --symref origin HEAD` names, else None."""
    rc, out, _ = run(["git", "-C", top, "symbolic-ref", "-q", "refs/remotes/origin/HEAD"])
    ref = one_line(out)
    if rc == 0 and ref.startswith("refs/remotes/origin/"):
        return ref[len("refs/remotes/origin/"):]
    rc, out, _ = run(["git", "-C", top, "ls-remote", "--symref", "origin", "HEAD"])
    m = re.search(r"^ref: refs/heads/(\S+)\s+HEAD$", out, re.M) if rc == 0 else None
    return m.group(1) if m else None


def has_commit(top, sha):
    rc, _, _ = run(["git", "-C", top, "cat-file", "-e", sha + "^{commit}"])
    return rc == 0


def pr_keeper(top, number):
    """The sha of refs/pull/<number>/head on origin when that commit is in
    the local object store, after a fetch when it was not. Else None, after
    one stderr line."""
    ref = "refs/pull/%d/head" % number
    rc, out, err = run(["git", "-C", top, "ls-remote", "origin", ref])
    sha = None
    for line in out.splitlines() if rc == 0 else []:
        parts = line.split()
        if len(parts) == 2 and parts[1] == ref and re.fullmatch(r"[0-9a-f]{40}([0-9a-f]{24})?", parts[0]):
            sha = parts[0]
    if sha is None:
        why = "git ls-remote origin %s failed: %s" % (ref, one_line(err) or "exit %d" % rc) if rc != 0 else "origin has no %s" % ref
    elif not has_commit(top, sha):
        rc, _, err = run(["git", "-C", top, "fetch", "-q", "origin", ref])
        if has_commit(top, sha):
            return sha
        why = "the commit %s of %s is not here after a fetch (%s)" % (sha, ref, one_line(err) or "exit %d" % rc)
    else:
        return sha
    print("launcher: the PR head %s is no keeper: %s" % (ref, why), file=sys.stderr)
    return None


def origin_keepers(top):
    """The sha of each branch and tag that `git ls-remote origin` lists, when
    the commit is in the local object store. For an annotated tag, the
    peeled sha. On a failed ls-remote: no keeper, after one stderr line."""
    rc, out, err = run(["git", "-C", top, "ls-remote", "origin"])
    if rc != 0:
        print(
            "launcher: git ls-remote origin failed (%s); no ref of origin is a keeper" % (one_line(err) or "exit %d" % rc),
            file=sys.stderr,
        )
        return []
    shas = {}
    for line in out.splitlines():
        parts = line.split()
        if len(parts) != 2 or not re.fullmatch(r"[0-9a-f]{40}([0-9a-f]{24})?", parts[0]):
            continue
        sha, ref = parts
        if ref.startswith("refs/heads/"):
            shas[ref] = sha
        elif ref.startswith("refs/tags/"):
            if ref.endswith("^{}"):
                shas[ref[: -len("^{}")]] = sha  # the peeled commit wins
            else:
                shas.setdefault(ref, sha)
    wanted = sorted(set(shas.values()))
    if not wanted:
        return []
    rc, out, _ = run(
        ["git", "-C", top, "cat-file", "--batch-check"],
        stdin="".join("%s^{commit}\n" % s for s in wanted),
    )
    if rc != 0:
        return []
    found = []
    for sha, line in zip(wanted, out.splitlines()):
        if not line.endswith(" missing"):
            found.append(sha)
    return found


def delete_branches(a, worktree, top, branch, made, result, git_step):
    """Step 6: find the candidates, prove each one, and delete each proven one
    that no worktree has checked out. launcher.md's "remove" owns the rules."""
    names = []
    for n in [branch, "worktree-" + os.path.basename(worktree)] + record_branches(worktree, made):
        if n and n not in names:
            names.append(n)
    default = default_branch(top)
    if default is None:
        never = ("main", "master")
        print("launcher: origin names no default branch, so main and master are never candidates", file=sys.stderr)
    else:
        never = (default,)
    cands = [
        n for n in names
        if n not in never and run(["git", "-C", top, "rev-parse", "-q", "--verify", "refs/heads/" + n])[0] == 0
    ]
    rc, _, err = run(["git", "-C", top, "fetch", "-q", "--no-prune", "origin"])
    if rc != 0:
        print(
            "launcher: git fetch origin failed (%s); the proof uses the refs that exist" % (one_line(err) or "exit %d" % rc),
            file=sys.stderr,
        )
    # The keepers: each branch and tag that origin lists now, and the PR
    # head. Never a local ref: a local branch, a stale remote-tracking ref or
    # a local tag is no copy elsewhere, and one candidate cannot prove
    # another.
    keepers = origin_keepers(top) if cands else []
    keeper = pr_keeper(top, a.pr) if a.pr else None
    if keeper:
        keepers.append(keeper)
    # rev-list reads the keepers on stdin, each as ^<sha>, so a long list
    # does not overflow the argument list. --not does not apply to --stdin.
    excludes = "".join("^%s\n" % k for k in keepers)
    for n in cands:
        args = ["rev-list", "refs/heads/" + n, "--stdin"]
        rc, out, err = run(["git", "-C", top] + args, stdin=excludes)
        if rc != 0:
            print(json.dumps(result))
            raise Fail(GIT, "launcher: git %s failed in %s: %s" % (" ".join(args), top, one_line(err) or "exit %d" % rc))
        result["branches"].append(
            {"name": n, "deleted": False, "unproven_commits": out.split(), "checked_out": None}
        )
    held = {}
    listing = git_step("worktree", "list", "--porcelain") if result["branches"] else ""
    for b in worktree_list(listing):
        if "branch" in b:
            held[b["branch"]] = os.path.realpath(b["worktree"])
    for e in result["branches"]:
        e["checked_out"] = held.get(e["name"])
    for e in result["branches"]:
        if not e["unproven_commits"] and e["checked_out"] is None:
            # Each commit is on a keeper, so -D loses nothing. -d is not
            # enough: after a rebase merge the merged commits have other shas.
            git_step("branch", "-D", e["name"])
            e["deleted"] = True
        elif e["unproven_commits"]:
            print(
                "launcher: kept the branch %s: it holds %d commits that no branch or tag of origin and no PR head holds"
                % (e["name"], len(e["unproven_commits"])),
                file=sys.stderr,
            )
        else:
            print(
                "launcher: kept the branch %s: the worktree %s has it checked out" % (e["name"], e["checked_out"]),
                file=sys.stderr,
            )


def remove(a):
    path = os.path.abspath(os.path.expanduser(a.worktree))
    worktree, main_tree, gitdir = linked_worktree(path)
    rc, out, _ = run(["git", "-C", worktree, "symbolic-ref", "-q", "--short", "HEAD"])
    branch = one_line(out) if rc == 0 and one_line(out) else None
    changed = [l for l in git(worktree, "status", "--porcelain").splitlines() if l.strip()]

    procs, where, in_tree, blockers, mine = scan(worktree, a.stop_processes)
    if not changed and all_ending(blockers, mine):
        # A session that /exit is ending still has its cwd here. Wait for it.
        end = time.time() + REMOVE_END_WAIT
        while time.time() < end:
            time.sleep(0.5)
            procs, where, in_tree, blockers, mine = scan(worktree, a.stop_processes)
            if not all_ending(blockers, mine):
                break

    # The lock, read after the wait: a session that held it can end there.
    reason = None
    for b in worktree_list(git(main_tree, "worktree", "list", "--porcelain")):
        if os.path.realpath(b["worktree"]) == worktree:
            reason = b.get("locked")
    lock = None
    owner = None
    if reason is not None:
        lock = {"reason": reason, "pid": lock_owner(reason), "unlocked": False}
        if lock["pid"] is not None and pid_dead(lock["pid"]):
            owner = lock["pid"]
    lock_refuses = lock is not None and owner is None
    refused = bool(changed or blockers or lock_refuses)

    result = {
        "worktree": worktree,
        "removed": False,
        "stopped": [],
        # A refusal keeps every process in the worktree running.
        "kept": [proc_row(p, ("pid", "tty", "command")) for p in in_tree] if refused else [],
        "changed": changed,
        "branch": branch,
        "branches": [],
        "lock": lock,
    }
    if refused:
        why = []
        if changed:
            why.append("%d changed or untracked files" % len(changed))
        if blockers:
            what = (
                "processes with a terminal or that run this command"
                if a.stop_processes
                else "processes in the worktree; add --stop-processes to stop the ones with no terminal"
            )
            why.append("%d %s (pids %s)" % (len(blockers), what, ", ".join(str(p["pid"]) for p in blockers)))
        if lock_refuses:
            why.append("a lock whose owner remove cannot prove dead (reason %s)" % json.dumps(reason))
        print(json.dumps(result))
        raise Fail(REFUSED, "launcher: kept the worktree %s: %s" % (worktree, "; ".join(why)))

    # Each signal goes only to a pid that ps and lsof show again, right before
    # the signal, with the argv and the cwd of the scan: a pid can go to a new
    # process at any time.
    found = {p["pid"]: (p["argv"], where[p["pid"]]) for p in in_tree}
    pids = sorted(found)

    def fail_mid_stop():
        # remove cannot tell which processes stopped, so kept holds each one.
        result["kept"] = [proc_row(p, ("pid", "tty", "command")) for p in in_tree]
        print(json.dumps(result))

    try:
        signal_found(found, signal.SIGTERM)
        end = time.time() + REMOVE_WAIT
        while any(alive(pid) for pid in pids) and time.time() < end:
            time.sleep(0.2)
        if any(alive(pid) for pid in pids):
            signal_found(found, signal.SIGKILL)
            end = time.time() + KILL_WAIT
            while any(alive(pid) for pid in pids) and time.time() < end:
                time.sleep(0.2)
        # Read the worktree again by the rule of the first scan, whatever the
        # argv: a process can change its title, and a watcher can start a new
        # child during the wait.
        procs = processes()
        where = cwds()
    except Fail:
        fail_mid_stop()
        raise
    left = [
        procs[pid]
        for pid in sorted(where)
        if pid in procs and inside(where[pid], worktree) and procs[pid]["ppid"] != os.getpid()
    ]
    left_pids = set(p["pid"] for p in left)
    # A pid of the first scan stopped when it is gone, or when its cwd is now
    # outside the worktree. A pid that ps shows with no cwd that lsof can read
    # did not stop: remove cannot tell where it runs.
    unknown = set(pid for pid in pids if pid in procs and pid not in where)
    result["stopped"] = [
        proc_row(p, ("pid", "command")) for p in in_tree if p["pid"] not in left_pids | unknown
    ]
    kept = left + [p for p in in_tree if p["pid"] in unknown]
    if kept:
        # A process in the worktree keeps it: git would remove the files under
        # a live process.
        result["kept"] = [proc_row(p, ("pid", "tty", "command")) for p in kept]
        print(json.dumps(result))
        raise Fail(
            REFUSED,
            "launcher: kept the worktree %s: %d processes still run in it after TERM and KILL (pids %s)"
            % (worktree, len(kept), ", ".join(str(p["pid"]) for p in kept)),
        )

    def git_step(*args):
        try:
            return git(main_tree, *args)
        except Fail:
            print(json.dumps(result))
            raise

    if owner is not None:
        # Test the owner again right before the unlock: the pid can run again.
        if not pid_dead(owner):
            print(json.dumps(result))
            raise Fail(
                REFUSED,
                "launcher: kept the worktree %s: the pid %d of its lock runs again; unlocked nothing" % (worktree, owner),
            )
        git_step("worktree", "unlock", worktree)
        lock["unlocked"] = True
    made = None
    if a.delete_branch:
        # git writes commondir once, at `worktree add`, so its mtime is when
        # the worktree was made. remove deletes the git dir, so read it first.
        try:
            made = os.path.getmtime(os.path.join(gitdir, "commondir"))
        except OSError as e:
            print("launcher: cannot read when git made the worktree (%s); no goal record counts" % e, file=sys.stderr)
    git_step("worktree", "remove", worktree)
    result["removed"] = True
    if a.delete_branch:
        delete_branches(a, worktree, main_tree, branch, made, result, git_step)
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

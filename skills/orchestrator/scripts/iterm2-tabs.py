"""The iTerm2 Python API helper of launcher.py.

usage:
  uv run -q --with iterm2 python iterm2-tabs.py start [--deadline <seconds>]
         --name <name> --command <cmd>
         [--session <unique id>] [--group <name>] [--group-color <#rrggbb>]
  uv run -q --with iterm2 python iterm2-tabs.py groups [--deadline <seconds>]

--deadline stops the work after that many seconds: the helper prints one
line on stderr and exits 1. launcher.py gives a deadline shorter than its own
timeout, so the helper stops before the launcher kills it.

start opens one tab in the window of the session --session names, or in the
current window. It does not select the tab. It names the session, types the
command into its shell, and puts the tab in the group. It prints JSON lines,
each one at once:

  {"opened": <unique id>}   the tab is open
  {"typed": <unique id>}    the command is typed into it
  {"closed": <unique id>}   a step before "typed" failed, and the tab is closed
  {"session_id": <unique id>, "tab_group": <name or null>}   the last line,
                            with "warning" when the group step failed

A failure before "typed" closes the tab and exits 1. A failure after "typed"
goes into "warning" and the exit is 0.

groups prints one JSON line per open tab group, over every window:
{"window_id", "group_id", "name", "color"}.

On a failure, it prints one line on stderr and exits 1.
launcher.py owns every other rule: skills/orchestrator/references/launcher.md.
"""

import argparse
import asyncio
import json
import sys

import iterm2


class HelperError(Exception):
    pass


def emit(obj):
    """Print one JSON line now, so a timeout or a crash cannot hide it."""
    print(json.dumps(obj), flush=True)


async def find_group(app, window_id, name):
    """The open group of that name in the window, read from a fresh app."""
    window = app.get_window_by_id(window_id)
    if window is None:
        return None
    for group in window.tab_groups:
        if group.name == name:
            return group
    return None


async def start(conn, args):
    app = await iterm2.async_get_app(conn)
    if args.group and not iterm2.capabilities.supports_tab_groups(conn):
        raise HelperError("this iTerm2 has no tab groups in its Python API")
    window = None
    if args.session:
        session = app.get_session_by_id(args.session)
        if session is not None:
            window, _ = app.get_window_and_tab_for_session(session)
    if window is None:
        window = app.current_terminal_window
    if window is None:
        raise HelperError("no iTerm2 window")
    window_id = window.window_id
    tab = await window.async_create_tab(select=False)
    if tab is None:
        raise HelperError("iTerm2 opened no tab")
    session = tab.current_session
    sid = session.session_id
    emit({"opened": sid})
    try:
        await session.async_set_name(args.name)
        await session.async_send_text(args.command + "\n")
    except Exception:
        # No command runs in the tab: close it, so the fallback opens the
        # only tab. When the close fails, no "closed" line goes out.
        await session.async_close(force=True)
        emit({"closed": sid})
        raise
    emit({"typed": sid})
    result = {"session_id": sid, "tab_group": None}
    if not args.group:
        return result
    try:
        # A Window object does not show a group made after it was read, so
        # read the app again before and after the change.
        app = await iterm2.async_get_app(conn)
        group = await find_group(app, window_id, args.group)
        fresh_tab = app.get_tab_by_id(tab.tab_id)
        if fresh_tab is None:
            raise HelperError("the new tab is gone")
        if group is not None:
            await fresh_tab.async_add_to_tab_group(group)
        else:
            color = iterm2.Color.from_hex(args.group_color) if args.group_color else None
            await app.get_window_by_id(window_id).async_create_tab_group(args.group, [fresh_tab], color)
        app = await iterm2.async_get_app(conn)
        fresh_tab = app.get_tab_by_id(tab.tab_id)
        joined = fresh_tab.tab_group if fresh_tab is not None else None
        if joined is None or joined.name != args.group:
            raise HelperError("the tab is in no group named %s after the change" % args.group)
        result["tab_group"] = joined.name
    except Exception as e:  # the tab is open: report it, with no group
        result["warning"] = "%s: %s" % (type(e).__name__, e)
    return result


async def groups(conn):
    if not iterm2.capabilities.supports_tab_groups(conn):
        raise HelperError("this iTerm2 has no tab groups in its Python API")
    app = await iterm2.async_get_app(conn)
    rows = []
    for window in app.terminal_windows:
        for group in window.tab_groups:
            rows.append(
                {
                    "window_id": window.window_id,
                    "group_id": group.group_id,
                    "name": group.name,
                    "color": group.color.hex if group.color is not None else None,
                }
            )
    return rows


async def main(args):
    conn = await iterm2.Connection.async_create()
    if args.cmd == "start":
        print(json.dumps(await start(conn, args)))
    else:
        for row in await groups(conn):
            print(json.dumps(row))


def parse(argv):
    p = argparse.ArgumentParser(prog="iterm2-tabs.py")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("--deadline", type=float)
    s.add_argument("--name", required=True)
    s.add_argument("--command", required=True)
    s.add_argument("--session")
    s.add_argument("--group")
    s.add_argument("--group-color")
    g = sub.add_parser("groups")
    g.add_argument("--deadline", type=float)
    return p.parse_args(argv)


if __name__ == "__main__":
    a = parse(sys.argv[1:])
    try:
        asyncio.run(asyncio.wait_for(main(a), a.deadline))
    except asyncio.TimeoutError:
        print("iterm2-tabs: stopped at the deadline of %g seconds" % a.deadline, file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print("iterm2-tabs: %s: %s" % (type(e).__name__, e), file=sys.stderr)
        sys.exit(1)

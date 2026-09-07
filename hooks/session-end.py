#!/usr/bin/env python3
"""SessionEnd: mark this session's crew run interrupted, its worktrees
orphaned, and its portfolio interrupted, then wake the lead above it.

It never deletes a file, a record or a worktree (design 13.1). It fails open:
any error exits 0 and changes nothing, because this hook runs in every session
on the machine, and most of them have no crew run.

The wake is one line on the lead's cross-session inbox socket (design §15.84).
It happens only after a run under a portfolio went `interrupted`, so a session
with no crew run opens no socket at all.
"""

import json
import os
import socket
import sys
import time
from pathlib import Path

LIVE_STATES = ("active", "blocked")

# The wake's budget. The hook's own timeout is 5 seconds (`hooks/hooks.json`),
# and the record writes come first, so these caps only bound the send. A local
# socket answers or refuses at once, so the budget is only there for the
# session that has stopped reading its own inbox.
SOCKET_TIMEOUT_SECONDS = 0.25
SEND_BUDGET_SECONDS = 2.0
# A backstop, not the real bound: the budget above is. A refused connect on a
# dead socket costs microseconds, so the cap only has to sit above the number
# of socket files one machine collects.
MAX_SOCKETS = 256

# Where the harness binds one inbox socket per live session, named
# `<pid>.sock` under a `cc-socks` directory. Claude Code builds the bind path
# from `XDG_RUNTIME_DIR`, then `CLAUDE_CODE_TMPDIR`, then `/tmp`, and it reads
# both variables from the environment this hook already runs in. The rest are
# the other namespaces it accepts, so a session that bound somewhere else is
# still found.
SOCKET_PARENT_VARS = ("XDG_RUNTIME_DIR", "CLAUDE_CODE_TMPDIR")
SOCKET_PARENTS = (
    "/tmp",
    "/private/tmp",
    "/run/user/{uid}",
    "/data/data/com.termux/files/usr/tmp",
)


def crew_roots() -> list[Path]:
    """Every place a record may live.

    `record-format.md` puts the record under `$CREW_RECORD_ROOT` when that is
    set and under `~/.claude/crew/` otherwise, so both are checked.
    `CLAUDE_CONFIG_DIR` relocates the config dir, and a project lead on such a
    machine may follow the harness rather than the reference, so check that
    too. Each extra root costs one `is_dir` and cannot miss a run.
    """
    candidates = []
    explicit = os.environ.get("CREW_RECORD_ROOT")
    if explicit:
        candidates.append(Path(explicit))
    candidates.append(Path.home() / ".claude" / "crew")
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        candidates.append(Path(config_dir) / "crew")
    roots = []
    for c in candidates:
        r = c.resolve()
        if r not in roots:
            roots.append(r)
    return roots


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data) -> None:
    """Replace the file in one step, so a killed hook leaves no half-file."""
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def orphan_worktrees(record_dir: Path, session_id: str) -> None:
    path = record_dir / "worktrees.json"
    if not path.is_file():
        return
    worktrees = read_json(path)
    changed = False
    for entry in worktrees.values():
        if session_id not in entry.get("session_ids", []):
            continue
        if entry.get("orphaned") is True:
            continue
        entry["orphaned"] = True
        changed = True
    if changed:
        write_json(path, worktrees)


def interrupt_run(state_path: Path, session_id: str) -> bool:
    """Mark the run interrupted. `True` when this call is what changed it."""
    state = read_json(state_path)
    run = state.get("run") or {}
    if session_id not in run.get("session_ids", []):
        return False
    if run.get("run_state") not in LIVE_STATES:
        return False
    run["run_state"] = "interrupted"
    write_json(state_path, state)
    orphan_worktrees(state_path.parent, session_id)
    return True


def interrupt_lead(portfolio_path: Path, session_id: str) -> None:
    """Mark a live lead's portfolio `interrupted` (`record-format.md`).

    The next `/crew:lead` reads it, learns its predecessor died rather than
    closed the portfolio, and sets it back to `active`. Without the mark a
    killed lead and a finished one look the same on disk.
    """
    portfolio = read_json(portfolio_path)
    lead = portfolio.get("lead") or {}
    if session_id not in lead.get("session_ids", []):
        return
    if lead.get("state") != "active":
        return
    lead["state"] = "interrupted"
    write_json(portfolio_path, portfolio)


def socket_parents() -> list[str]:
    """Every directory that may hold a `cc-socks` namespace."""
    uid = os.getuid()
    parents = []
    for name in SOCKET_PARENT_VARS:
        value = os.environ.get(name)
        if value:
            parents.append(value)
    parents.extend(p.format(uid=uid) for p in SOCKET_PARENTS)
    return parents


def owner_is_gone(sock_path: Path) -> bool:
    """`True` when the socket is named for a process that has exited.

    A crashed session leaves its socket file behind for good, and a machine
    collects them. Dropping them keeps the send to the live sessions.
    """
    try:
        pid = int(sock_path.stem)
    except ValueError:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return True
    except Exception:
        return False
    return False


def socket_paths() -> list[Path]:
    """Every live session's inbox socket on this machine."""
    paths = []
    seen = set()
    for parent in socket_parents():
        directory = Path(parent)
        if not directory.is_dir():
            continue
        for namespace in sorted(directory.glob("cc-socks*")):
            if not namespace.is_dir():
                continue
            for sock in sorted(namespace.glob("*.sock")):
                key = str(sock.resolve())
                if key in seen:
                    continue
                seen.add(key)
                if owner_is_gone(sock):
                    continue
                paths.append(sock)
    return paths


def send_line(sock_path: Path, line: bytes) -> bool:
    """One line on one socket. Any failure is a `False`, never an exception.

    A dead session leaves its socket file behind, so a refused connect is the
    common case and costs nothing.
    """
    handle = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        handle.settimeout(SOCKET_TIMEOUT_SECONDS)
        handle.connect(str(sock_path))
        handle.sendall(line)
        return True
    except Exception:
        return False
    finally:
        try:
            handle.close()
        except Exception:
            pass


def wake_message(item_id: str, item: dict, record_dir: Path) -> str:
    """What the lead reads. It must stand on its own, because the lead may
    read it in a fresh context (`session-launch.md`, "Resuming a dead one")."""
    session_name = (
        item.get("session_name") or "the item's session_name in portfolio.json"
    )
    return (
        f"crew SessionEnd: item {item_id} lost its project-lead session. "
        f"Its run is now interrupted in {record_dir}/state.json, and its "
        "worktrees are orphaned. Nothing else is wrong: the record holds the "
        "run. Follow session-launch.md's \"Resuming a dead one\" — confirm "
        f"{session_name} is absent from ListAgents, launch it again under "
        "that same name and the same CREW_RECORD_ROOT, then send it "
        f"`Run /crew:project-lead --resume {record_dir.name} now.`"
    )


def wake_lead(record_dir: Path) -> None:
    """Give the lead above this run a turn.

    `runs/<item-id>/` is the item's record root (`record-format.md`), so the
    portfolio sits two directories above the goal record. The frame carries
    the lead's session id, and the harness drops a frame whose `session_id`
    does not match the session that receives it — so one line per socket
    reaches the lead and nobody else. That filter is what makes an address
    unnecessary: a socket is named for a process id, and no record holds one.
    """
    parents = record_dir.parents
    if len(parents) < 3 or parents[1].name != "runs":
        return
    portfolio_path = parents[2] / "portfolio.json"
    if not portfolio_path.is_file():
        return
    portfolio = read_json(portfolio_path)
    lead = portfolio.get("lead") or {}
    if lead.get("state") != "active":
        return
    session_ids = lead.get("session_ids") or []
    if not session_ids:
        return
    # An item whose id has drifted from its `runs/<item-id>/` directory still
    # gets a wake: the message names the id and the record either way, and
    # `wake_message` carries a fallback for the missing session name.
    item_id = record_dir.parent.name
    item = next(
        (i for i in portfolio.get("items", []) if i.get("id") == item_id), {}
    )
    frame = {
        "type": "user",
        "session_id": session_ids[-1],
        "priority": "next",
        "message": {"content": wake_message(item_id, item, record_dir)},
    }
    line = (json.dumps(frame, ensure_ascii=False) + "\n").encode("utf-8")
    deadline = time.monotonic() + SEND_BUDGET_SECONDS
    for sock_path in socket_paths()[:MAX_SOCKETS]:
        if time.monotonic() > deadline:
            return
        send_line(sock_path, line)


def main() -> None:
    roots = [r for r in crew_roots() if r.is_dir()]
    if not roots:
        return
    payload = json.loads(sys.stdin.read() or "{}")
    session_id = payload.get("session_id")
    if not session_id:
        return
    interrupted = []
    for root in roots:
        for state_path in sorted(root.glob("*/state.json")):
            try:
                if interrupt_run(state_path, session_id):
                    interrupted.append(state_path.parent)
            except Exception:
                continue
        for portfolio_path in sorted(root.glob("*/portfolio.json")):
            try:
                interrupt_lead(portfolio_path, session_id)
            except Exception:
                continue
    # The record comes first and the wake second, so a slow socket can never
    # cost a write. A run that changed nothing wakes nobody.
    for record_dir in interrupted:
        try:
            wake_lead(record_dir)
        except Exception:
            continue


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)

#!/usr/bin/env python3
"""SessionEnd: mark this session's crew run interrupted and its worktrees
orphaned.

It never deletes a file, a record or a worktree (design 13.1). It fails open:
any error exits 0 and changes nothing, because this hook runs in every session
on the machine, and most of them have no crew run.
"""

import fcntl
import json
import os
import sys
from pathlib import Path

# A `delivered` run is not here. After the hand-over the project lead's
# session and each window session may close, and the run stays `delivered`: a
# watcher with no model owns the PR watch, and `window-watch.py ensure` brings
# it back. Only a run that builds work dies with its session. One exception:
# `crew-step.py hand-over` starts the watcher held, and only the project lead's
# `window-watch.py release` lets it start a session. A project lead that ends
# before the release leaves a held watcher and a run nobody finishes, so that
# run is marked interrupted (`run.window.hold` is true).
LIVE_STATES = ("active", "blocked")


# A park (`crew-step.py park`) ends the project lead's session on purpose,
# and a waiter session takes the run over. The end of the session that
# parked is not a death: it is retired. While `run.park` is set, its
# `from_session` is retired. After the park ends, a session is retired when it
# is the `from_session` of a `run.parks` entry that a different session woke.
# A park that failed has no `woke`, so its session stays live.
def is_retired(run: dict, session_id: str) -> bool:
    park = run.get("park")
    if isinstance(park, dict) and park.get("from_session") == session_id:
        return True
    for entry in run.get("parks") or []:
        if not isinstance(entry, dict) or entry.get("from_session") != session_id:
            continue
        woke = entry.get("woke")
        if isinstance(woke, dict) and woke.get("session_id") not in (None, session_id):
            return True
    return False


# The waiter of the park that holds the run now. Its id is not in
# `run.session_ids`, but while that park holds, the waiter is the one session
# of the run, so its end is the death of the run.
def park_waiter_id(run: dict):
    park = run.get("park")
    if not isinstance(park, dict):
        return None
    waiter = park.get("waiter")
    return waiter.get("session_id") if isinstance(waiter, dict) else None


def is_live(run: dict) -> bool:
    if run.get("run_state") in LIVE_STATES:
        return True
    return run.get("run_state") == "delivered" and (run.get("window") or {}).get("hold") is True


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
    # The same lock `crew-record.py` takes, so this write cannot erase one.
    with (state_path.parent / "state.json.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        state = read_json(state_path)
        run = state.get("run") or {}
        if session_id not in run.get("session_ids", []) and session_id != park_waiter_id(run):
            return False
        if not is_live(run) or is_retired(run, session_id):
            return False
        run["run_state"] = "interrupted"
        write_json(state_path, state)
        orphan_worktrees(state_path.parent, session_id)
        return True


def main() -> None:
    roots = [r for r in crew_roots() if r.is_dir()]
    if not roots:
        return
    payload = json.loads(sys.stdin.read() or "{}")
    session_id = payload.get("session_id")
    if not session_id:
        return
    for root in roots:
        for state_path in sorted(root.glob("*/state.json")):
            try:
                interrupt_run(state_path, session_id)
            except Exception:
                continue


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)

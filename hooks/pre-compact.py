#!/usr/bin/env python3
"""PreCompact: record that a session in a live crew run is about to compact.

Appends `{session_id, trigger, at}` to `run.compactions` in the run's
`state.json`. A compaction throws away context the project lead relied on
an IC holding, so the project lead reads this list before it accepts that
IC's next report (design §15.50). Writes only; deletes nothing; fails open.
"""

import datetime
import json
import os
import sys
from pathlib import Path

LIVE_STATES = ("active", "blocked")


def crew_roots() -> list[Path]:
    roots = []
    explicit = os.environ.get("CREW_RECORD_ROOT")
    if explicit:
        roots.append(Path(explicit))
    roots.append(Path.home() / ".claude" / "crew")
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        relocated = Path(config_dir) / "crew"
        if relocated not in roots:
            roots.append(relocated)
    return roots


def write_json(path: Path, data) -> None:
    tmp = path.with_name(path.name + ".tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def session_in_run(record_dir: Path, run: dict, session_id: str) -> bool:
    if session_id in run.get("session_ids", []):
        return True
    worktrees = record_dir / "worktrees.json"
    if worktrees.is_file():
        with worktrees.open(encoding="utf-8") as handle:
            for entry in json.load(handle).values():
                if session_id in entry.get("session_ids", []):
                    return True
    return False


def record(state_path: Path, session_id: str, trigger: str) -> None:
    with state_path.open(encoding="utf-8") as handle:
        state = json.load(handle)
    run = state.get("run") or {}
    if run.get("run_state") not in LIVE_STATES:
        return
    if not session_in_run(state_path.parent, run, session_id):
        return
    run.setdefault("compactions", []).append(
        {
            "session_id": session_id,
            "trigger": trigger,
            "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
    )
    write_json(state_path, state)


def main() -> None:
    roots = [r for r in crew_roots() if r.is_dir()]
    if not roots:
        return
    payload = json.loads(sys.stdin.read() or "{}")
    session_id = payload.get("session_id")
    if not session_id:
        return
    trigger = payload.get("trigger") or "unknown"
    for root in roots:
        for state_path in sorted(root.glob("*/state.json")):
            try:
                record(state_path, session_id, trigger)
            except Exception:
                continue


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)

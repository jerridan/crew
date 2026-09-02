#!/usr/bin/env python3
"""SessionEnd: mark this session's crew run interrupted, and its worktrees
orphaned.

Writes only. It never deletes a file, a record or a worktree (design 13.1).
It fails open: any error exits 0 and changes nothing, because this hook runs
in every session on the machine, and most of them have no crew run.
"""

import json
import os
import sys
from pathlib import Path

LIVE_STATES = ("active", "blocked")


def crew_roots() -> list[Path]:
    """Every place a record may live.

    `record-format.md` hardcodes `~/.claude/crew/`, so that path is always
    checked. `CLAUDE_CONFIG_DIR` relocates the config dir, and a project lead
    on such a machine may follow the harness rather than the reference, so
    check that too. Looking in both costs one `is_dir` and cannot miss a run.
    """
    roots = [Path.home() / ".claude" / "crew"]
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        relocated = Path(config_dir) / "crew"
        if relocated not in roots:
            roots.append(relocated)
    return roots


def read_json(path: Path):
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def write_json(path: Path, data) -> None:
    """Replace the file in one step, so a killed hook leaves no half-file."""
    tmp = path.with_name(path.name + ".tmp")
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


def interrupt_run(state_path: Path, session_id: str) -> None:
    state = read_json(state_path)
    run = state.get("run") or {}
    if session_id not in run.get("session_ids", []):
        return
    if run.get("run_state") not in LIVE_STATES:
        return
    run["run_state"] = "interrupted"
    write_json(state_path, state)
    orphan_worktrees(state_path.parent, session_id)


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

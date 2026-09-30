#!/usr/bin/env python3
"""PreCompact: record that a session in a live crew run is about to compact.

Appends `{session_id, agent_id, agent, trigger, at}` to `run.compactions`
in the run's `state.json`. A hook that fires inside a subagent or an
in-process teammate carries `agent_id`; `agent` is the name resolved from the
transcript's sibling `.meta.json`, which is the teammate's name the project
lead spawned it under. A split-pane teammate is its own session, so it
carries no `agent_id`; it is matched by the `teamName` in its transcript and
named by its `agentName` (design §15.102). No `agent_id` and no team name
means the project lead's own session compacted. Writes only; deletes
nothing; fails open (design §15.50).
"""

import datetime
import json
import os
import sys
from pathlib import Path

LIVE_STATES = ("active", "blocked", "delivered")


def crew_roots() -> list[Path]:
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


def write_json(path: Path, data) -> None:
    tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    os.replace(tmp, path)


def team_header(transcript_path: str) -> tuple[str | None, str | None]:
    """`(teamName, agentName)` from a split-pane teammate's transcript.

    Every entry after the first few settings lines carries both.
    `skills/project-lead/scripts/spend.py`'s `team_name()` reads it the same
    way.
    """
    if not transcript_path:
        return None, None
    try:
        with open(transcript_path, encoding="utf-8", errors="ignore") as handle:
            for n, line in enumerate(handle):
                if n >= 50:
                    break
                try:
                    entry = json.loads(line)
                except ValueError:
                    continue
                if isinstance(entry, dict) and entry.get("teamName"):
                    return entry["teamName"], entry.get("agentName")
    except OSError:
        pass
    return None, None


def session_in_run(record_dir: Path, run: dict, session_id: str, team: str | None = None) -> bool:
    if session_id in run.get("session_ids", []):
        return True
    if team and team in {f"session-{s[:8]}" for s in run.get("session_ids", []) if isinstance(s, str)}:
        return True
    worktrees = record_dir / "worktrees.json"
    if worktrees.is_file():
        with worktrees.open(encoding="utf-8") as handle:
            for entry in json.load(handle).values():
                if session_id in entry.get("session_ids", []):
                    return True
    return False


def agent_name(transcript_path: str) -> str | None:
    """The teammate or subagent name, from `<transcript>.meta.json` beside
    the transcript. Absent for the main session."""
    if not transcript_path:
        return None
    meta = Path(transcript_path).with_suffix(".meta.json")
    if not meta.is_file():
        return None
    try:
        with meta.open(encoding="utf-8") as handle:
            return json.load(handle).get("name")
    except Exception:
        return None


def record(state_path: Path, entry: dict, team: str | None = None) -> None:
    with state_path.open(encoding="utf-8") as handle:
        state = json.load(handle)
    run = state.get("run") or {}
    if run.get("run_state") not in LIVE_STATES:
        return
    if not session_in_run(state_path.parent, run, entry["session_id"], team):
        return
    run.setdefault("compactions", []).append(entry)
    write_json(state_path, state)


def main() -> None:
    roots = [r for r in crew_roots() if r.is_dir()]
    if not roots:
        return
    payload = json.loads(sys.stdin.read() or "{}")
    session_id = payload.get("session_id")
    if not session_id:
        return
    team, teammate = None, None
    if not payload.get("agent_id"):
        team, teammate = team_header(payload.get("transcript_path"))
    entry = {
        "session_id": session_id,
        "agent_id": payload.get("agent_id"),
        "agent": agent_name(payload.get("transcript_path")) or teammate,
        "trigger": payload.get("trigger") or "unknown",
        "at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    for root in roots:
        for state_path in sorted(root.glob("*/state.json")):
            try:
                record(state_path, entry, team)
            except Exception:
                continue


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)

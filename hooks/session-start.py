#!/usr/bin/env python3
"""SessionStart: give a restarted orchestrator its record again.

The hook reads the hook JSON on stdin (`session_id`, `source`). For the
sources `compact` and `resume`, it looks for an open orchestrator record
under the record root whose `orchestrator_session_id` is this session's id.
It then runs `crew-orch.py --orch <name> resume --read-only` and prints the
result as additional context. The read-only form writes nothing and starts
nothing. For any other source, any other id or any fault, it prints nothing.
It always exits 0, and it never blocks a session.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SOURCES = ("compact", "resume")
RUN_TIMEOUT = 20


def record_root() -> Path:
    env = os.environ.get("CREW_RECORD_ROOT")
    return Path(env).expanduser() if env else Path.home() / ".claude" / "crew"


def orch_script() -> Path:
    plugin = os.environ.get("CLAUDE_PLUGIN_ROOT")
    base = Path(plugin) if plugin else Path(__file__).resolve().parent.parent
    return base / "skills" / "orchestrator" / "scripts" / "crew-orch.py"


def find_record(session_id: str):
    """The name of the open record that this session started or resumed, or None."""
    for path in sorted((record_root() / "orchestrators").glob("*/orchestrator.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if (isinstance(data, dict) and data.get("orchestrator_session_id") == session_id
                and not data.get("closed_at")):
            return path.parent.name
    return None


def main() -> None:
    data = json.load(sys.stdin)
    session_id = data.get("session_id")
    if data.get("source") not in SOURCES or not isinstance(session_id, str) or not session_id:
        return
    name = find_record(session_id)
    if name is None:
        return
    proc = subprocess.run([sys.executable, str(orch_script()), "--orch", name, "resume", "--read-only"],
                          capture_output=True, text=True, timeout=RUN_TIMEOUT)
    if proc.returncode != 0 or not proc.stdout.strip():
        return
    context = (f"Orchestrator record '{name}' (this session's record). `resume --read-only` says:\n"
               f"{proc.stdout.strip()}")
    print(json.dumps({"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": context}}))


if __name__ == "__main__":
    try:
        main()
    except BaseException:  # a hook never blocks a session
        pass
    sys.exit(0)

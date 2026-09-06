#!/usr/bin/env python3
"""Price a lead from its own session transcripts.

usage: lead-spend.py <portfolio-dir> [--write]

A lead runs from no checkout and writes no `state.json`, so `spend.py` cannot
find it and the tier's own cost goes uncounted (design §8, §15.74k, §15.76).
This script reads `lead.session_ids` from `portfolio.json`, finds each
session's `<session-id>.jsonl` under `~/.claude/projects/` (and under
`$CLAUDE_CONFIG_DIR/projects/` when that variable is set), prices every
assistant message in it, and prints a table.

With `--write` it stores the result in `portfolio.json` as `lead.spend`, in
`record-format.md`'s `spend.transcript` shape. `record-format.md`'s "Lead
spend" says when the lead runs it.

Whole sessions are priced, with no time window: every turn of a lead session
belongs to its portfolio, which is what makes a session id a cleaner bound
than a checkout path. A session id that names no transcript gets a line
saying so, and the remaining sessions are still priced.

Prices come from `skills/project-lead/scripts/spend.py`. There is one price
table, and it is not here.
"""

import json
import os
import sys
from pathlib import Path

SPEND = Path(__file__).resolve().parent.parent.parent / "project-lead" / "scripts"
sys.path.insert(0, str(SPEND))
import spend  # noqa: E402  the price table and the transcript pricing live there


def project_roots() -> list[Path]:
    roots = [Path.home() / ".claude" / "projects"]
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        roots.append(Path(config_dir) / "projects")
    return [r for r in roots if r.is_dir()]


def transcripts(session_ids: list, roots: list[Path], missing: list) -> list[Path]:
    """Every transcript file these sessions wrote.

    A lead session is named by its id wherever it ran, so the id is searched
    for across every project directory rather than under one checkout. The
    file name is the id exactly: a prefix match would take a second session
    whose id opens with the same characters.
    """
    found = []
    for session_id in session_ids:
        if not isinstance(session_id, str) or not session_id:
            missing.append(f"{session_id!r} is not a session id")
            continue
        hits = []
        for root in roots:
            hits.extend(sorted(root.glob(f"**/{session_id}.jsonl")))
        if not hits:
            missing.append(f"{session_id}: no transcript under {', '.join(str(r) for r in roots)}")
        found.extend(hits)
    # One file can sit under two roots that resolve to one directory.
    unique = []
    for path in found:
        resolved = path.resolve()
        if resolved not in unique:
            unique.append(resolved)
    return unique


def main(argv: list[str]) -> None:
    if not argv:
        sys.exit(__doc__)
    portfolio = Path(argv[0])
    path = portfolio / "portfolio.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        sys.exit(f"cannot read {path}: {err}")
    lead = data.get("lead")
    lead = lead if isinstance(lead, dict) else {}
    session_ids = lead.get("session_ids")
    session_ids = session_ids if isinstance(session_ids, list) else []
    if not session_ids:
        sys.exit(f"{path} lists no lead.session_ids")

    roots = project_roots()
    if not roots:
        sys.exit("no transcript directory under ~/.claude/projects or $CLAUDE_CONFIG_DIR")
    missing: list[str] = []
    files = transcripts(session_ids, roots, missing)
    if not files:
        for line in missing:
            print(f"skipped {line}")
        sys.exit(f"no transcript for any of the {len(session_ids)} sessions in {path}")

    totals = spend.price_files(files)
    print(f"sessions {len(session_ids)}  files {len(files)}")
    grand, total_tokens = spend.report(totals)
    for line in missing:
        print(f"skipped {line}")

    if "--write" in argv[1:]:
        # Read again and write in one process, as `crew-portfolio.py` does:
        # both hooks append to this file, and a whole-file write from a stale
        # read drops what they added (`record-format.md`).
        data = json.loads(path.read_text(encoding="utf-8"))
        stored = data.setdefault("lead", {})
        stored["spend"] = spend.transcript(totals, grand, total_tokens)
        stored["updated_at"] = stored["spend"]["measured_at"]
        tmp = path.with_name(f"portfolio.json.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)
        print("written to portfolio.json")


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3
"""Price a crew run from its transcripts: every session, teammate and
subagent that ran from the target checkout since the record was created.

usage: spend.py <record-dir> <checkout-path> [--write]

Reads `~/.claude/projects/<escaped checkout path>/**/*.jsonl` (and the same
under `$CLAUDE_CONFIG_DIR` when set), sums usage per model family, and
prints a table. With `--write`, stores the result in `state.json` as
`run.spend.transcript`. This is the only count that includes the project
lead's own session and the IC teammates (design §8, §15.50).

The start time is `run.created_at` in `state.json`, which `crew-record.py
init` writes. Transcript files last modified before it are skipped.

Prices are USD per million tokens at Anthropic list price, by model family.
Cache writes are priced by TTL. Update the table when prices change.
"""

import datetime
import glob
import json
import os
import re
import sys
from pathlib import Path

PRICE = {  # input, 5m cache write, 1h cache write, cache read, output
    "fable": (10, 12.5, 20, 0.25, 50),
    "opus": (5, 6.25, 10, 0.5, 25),
    "sonnet": (2, 2.5, 4, 0.2, 10),
    "haiku": (1, 1.25, 2, 0.1, 5),
}


def family(model: str) -> str:
    for name in PRICE:
        if name in (model or ""):
            return name
    return "opus"


def project_dirs(checkout: str) -> list[Path]:
    # Claude Code names the transcript directory by replacing every
    # non-alphanumeric character of the absolute checkout path with "-".
    escaped = re.sub(r"[^A-Za-z0-9]", "-", os.path.abspath(checkout))
    roots = [Path.home() / ".claude" / "projects"]
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR")
    if config_dir:
        roots.append(Path(config_dir) / "projects")
    found = []
    for root in roots:
        candidate = (root / escaped).resolve()
        if candidate.is_dir() and candidate not in found:
            found.append(candidate)
    return found


def collect(dirs: list[Path], since: float) -> dict:
    messages = {}
    for d in dirs:
        for f in glob.glob(str(d / "**" / "*.jsonl"), recursive=True):
            if os.path.getmtime(f) < since:
                continue
            with open(f, encoding="utf-8") as handle:
                for line in handle:
                    try:
                        entry = json.loads(line)
                    except ValueError:
                        continue
                    msg = entry.get("message") or {}
                    usage = msg.get("usage")
                    if entry.get("type") != "assistant" or not usage:
                        continue
                    key = msg.get("id") or (f, entry.get("uuid"))
                    cache = usage.get("cache_creation") or {}
                    w5 = cache.get("ephemeral_5m_input_tokens", 0) if cache else usage.get("cache_creation_input_tokens", 0)
                    rec = (
                        family(msg.get("model")),
                        usage.get("input_tokens", 0),
                        w5,
                        cache.get("ephemeral_1h_input_tokens", 0),
                        usage.get("cache_read_input_tokens", 0),
                        usage.get("output_tokens", 0),
                    )
                    if key not in messages or sum(rec[1:]) > sum(messages[key][1:]):
                        messages[key] = rec
    totals = {}
    for fam, inp, w5, w1, read, out in messages.values():
        t = totals.setdefault(fam, {"messages": 0, "input": 0, "cache_write_5m": 0, "cache_write_1h": 0, "cache_read": 0, "output": 0, "usd": 0.0})
        p = PRICE[fam]
        t["messages"] += 1
        t["input"] += inp
        t["cache_write_5m"] += w5
        t["cache_write_1h"] += w1
        t["cache_read"] += read
        t["output"] += out
        t["usd"] += (inp * p[0] + w5 * p[1] + w1 * p[2] + read * p[3] + out * p[4]) / 1e6
    return totals


def start_time(record: Path, state: dict) -> float:
    created = (state.get("run") or {}).get("created_at")
    if created:
        return datetime.datetime.fromisoformat(created.replace("Z", "+00:00")).timestamp()
    return (record / "charter.md").stat().st_mtime


def main(argv: list[str]) -> None:
    if len(argv) < 2:
        sys.exit(__doc__)
    record = Path(argv[0])
    state_path = record / "state.json"
    state = json.loads(state_path.read_text(encoding="utf-8"))
    dirs = project_dirs(argv[1])
    if not dirs:
        sys.exit(f"no transcripts for checkout {argv[1]}")
    totals = collect(dirs, start_time(record, state))
    print(f"{'model':7} {'msgs':>5} {'input':>9} {'w5m':>10} {'w1h':>10} {'read':>12} {'output':>8} {'usd':>8}")
    grand = 0.0
    total_tokens = 0
    for fam, t in sorted(totals.items(), key=lambda kv: -kv[1]["usd"]):
        print(f"{fam:7} {t['messages']:5d} {t['input']:9d} {t['cache_write_5m']:10d} {t['cache_write_1h']:10d} {t['cache_read']:12d} {t['output']:8d} {t['usd']:8.2f}")
        grand += t["usd"]
        total_tokens += t["input"] + t["cache_write_5m"] + t["cache_write_1h"] + t["cache_read"] + t["output"]
    print(f"total ${grand:.2f}  tokens {total_tokens}")
    if "--write" in argv:
        spend = state.setdefault("run", {}).setdefault("spend", {})
        spend["transcript"] = {
            "measured_at": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "total_tokens": total_tokens,
            "usd_list_price": round(grand, 2),
            "by_model": {fam: {k: (round(v, 2) if k == "usd" else v) for k, v in t.items()} for fam, t in totals.items()},
        }
        tmp = state_path.with_name(f"state.json.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, state_path)
        print("written to state.json")


if __name__ == "__main__":
    main(sys.argv[1:])

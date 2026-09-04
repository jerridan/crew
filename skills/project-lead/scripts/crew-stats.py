#!/usr/bin/env python3
"""Read every crew record under the record root and print what the runs cost.

usage: crew-stats.py [--record-root <dir>] [--repo <slug>=<checkout>] [--json]

The record root is `--record-root`, or `$CREW_RECORD_ROOT`, or `~/.claude/crew/`
(`record-format.md`). One directory with a `state.json` is one run.

Prints cost per package by band, fix rounds by band, promotions from
`band_history`, councils and their spend, escalations, compactions and review
counts. Design §8 asks for these numbers to turn the band rubric from a guess
into a measurement, and to give a principal a defensible charter `Budget:`.

Dollars come from `spend.py`, which this script imports. It never holds a
second price table. A run is priced in this order:

1. `run.spend.transcript.usd_list_price`, when `spend.py --write` already
   stored it.
2. `spend.py` over the run's checkout, when the record names one in `repo` or
   a `--repo <slug>=<checkout>` flag names one.
3. Not priced. The run still counts everywhere else, and a skip line says so.

An older or partial record never stops the script. A missing field is skipped,
the record is still counted, and one line names what was skipped.

The script only reads. It writes nothing into the record root.
"""

import argparse
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spend  # noqa: E402  the price table and the transcript pricing live there

BANDS = ["light", "standard", "deep"]

REVIEW_KINDS = [
    ("package review", re.compile(r"-package-review-r\d+\.md$")),
    ("spec critic", re.compile(r"^spec-critic-r\d+\.md$")),
    ("split critic", re.compile(r"-split-critic-r\d+\.md$")),
    ("deliverable review", re.compile(r"-deliverable-review\.md$")),
]


def price_run(record: Path, state: dict, checkout: str | None, skips: list) -> float | None:
    """Return the run's cost in US dollars, or None when nothing can price it."""
    stored = ((state.get("run") or {}).get("spend") or {}).get("transcript") or {}
    if stored.get("usd_list_price") is not None:
        return float(stored["usd_list_price"])
    if not checkout:
        skips.append(f"{record.name}: no cost — the record has no spend.transcript and names no checkout")
        return None
    dirs = spend.project_dirs(checkout)
    if not dirs:
        skips.append(f"{record.name}: no cost — no transcripts for checkout {checkout}")
        return None
    try:
        totals = spend.collect(dirs, spend.start_time(record, state))
    except OSError as err:
        skips.append(f"{record.name}: no cost — {err}")
        return None
    return sum(t["usd"] for t in totals.values())


def count_reviews(record: Path, skips: list) -> dict:
    counts = {name: 0 for name, _ in REVIEW_KINDS}
    counts["other"] = 0
    directory = record / "reviews"
    if not directory.is_dir():
        skips.append(f"{record.name}: no reviews — the record has no reviews/ directory")
        return counts
    for name in sorted(os.listdir(directory)):
        for kind, pattern in REVIEW_KINDS:
            if pattern.search(name):
                counts[kind] += 1
                break
        else:
            counts["other"] += 1
    return counts


def read_councils(record: Path, skips: list) -> tuple[int, int]:
    """Return the council count and the tokens those councils spent."""
    path = record / "decisions.md"
    if not path.is_file():
        skips.append(f"{record.name}: no councils — the record has no decisions.md")
        return 0, 0
    text = path.read_text(encoding="utf-8", errors="replace")
    councils = 0
    tokens = 0
    for entry in re.split(r"^## ", text, flags=re.M)[1:]:
        if not re.search(r"^Route:\s*council\b", entry, flags=re.M):
            continue
        councils += 1
        found = re.search(r"^Spend:[^\d]*([\d,]+)\s*tokens", entry, flags=re.M)
        if found:
            tokens += int(found.group(1).replace(",", ""))
    return councils, tokens


def read_record(record: Path, checkout: str | None, skips: list) -> dict:
    state = json.loads((record / "state.json").read_text(encoding="utf-8"))
    run = state.get("run") or {}
    packages = state.get("packages") or []
    if not packages:
        skips.append(f"{record.name}: no packages — the record has an empty packages list")

    per_band = {}
    promotions = 0
    for package in packages:
        band = package.get("band")
        if band not in BANDS:
            skips.append(f"{record.name}/{package.get('id', '?')}: no band — the package records {band!r}")
            band = "unknown"
        counts = per_band.setdefault(band, {"packages": 0, "fix_rounds": 0, "promotions": 0})
        counts["packages"] += 1
        counts["fix_rounds"] += package.get("fix_rounds_used") or 0
        # A band_history entry with a cause is a promotion; the first entry is
        # the prediction and carries none (record-format.md, design §8).
        moved = sum(1 for h in package.get("band_history") or [] if h.get("cause"))
        counts["promotions"] += moved
        promotions += moved

    councils, council_tokens = read_councils(record, skips)
    usd = price_run(record, state, checkout, skips)
    return {
        "run": record.name,
        "run_state": run.get("run_state"),
        "packages": len(packages),
        "by_band": per_band,
        "fix_rounds": sum(p.get("fix_rounds_used") or 0 for p in packages),
        "promotions": promotions,
        "councils": councils,
        "council_tokens": council_tokens,
        "escalations": len(run.get("escalations") or []),
        "compactions": len(run.get("compactions") or []),
        "reviews": count_reviews(record, skips),
        "usd": usd,
        # TODO(T23): review catch rate belongs here, once T23 defines it.
    }


def table(header: list[str], rows: list[list[str]]) -> str:
    widths = [max(len(str(cell)) for cell in column) for column in zip(header, *rows)] if rows else [len(h) for h in header]
    def line(cells, first_left=True):
        parts = []
        for i, cell in enumerate(cells):
            parts.append(str(cell).ljust(widths[i]) if i == 0 and first_left else str(cell).rjust(widths[i]))
        return "  ".join(parts).rstrip()
    return "\n".join([line(header)] + [line(row) for row in rows])


def money(value) -> str:
    return "-" if value is None else f"{value:.2f}"


def report(records: list[dict], skips: list[str]) -> None:
    print("Runs\n")
    rows = [
        [r["run"], r["packages"], r["fix_rounds"], r["promotions"], r["councils"],
         r["escalations"], r["compactions"], sum(r["reviews"].values()), money(r["usd"])]
        for r in records
    ]
    print(table(["run", "pkgs", "fixes", "promos", "councils", "escal", "compact", "reviews", "usd"], rows))

    # A run's dollars cover the whole run. Nothing in the record attributes
    # them to one package, so a priced run splits its cost evenly over its
    # packages. Read the band columns as an estimate, not a measurement.
    print("\nBy band (cost is the run total split evenly over its packages)\n")
    per_band = {}
    for r in records:
        share = None
        if r["usd"] is not None and r["packages"]:
            share = r["usd"] / r["packages"]
        for band, counts in r["by_band"].items():
            total = per_band.setdefault(band, {"packages": 0, "fix_rounds": 0, "promotions": 0, "usd": 0.0, "priced": 0})
            total["packages"] += counts["packages"]
            total["fix_rounds"] += counts["fix_rounds"]
            total["promotions"] += counts["promotions"]
            if share is not None:
                total["usd"] += share * counts["packages"]
                total["priced"] += counts["packages"]
    order = [b for b in BANDS if b in per_band] + [b for b in sorted(per_band) if b not in BANDS]
    rows = []
    for band in order:
        t = per_band[band]
        mean = f"{t['usd'] / t['priced']:.2f}" if t["priced"] else "-"
        rows.append([band, t["packages"], t["priced"], f"{t['fix_rounds'] / t['packages']:.2f}",
                     t["promotions"], money(t["usd"] if t["priced"] else None), mean])
    print(table(["band", "pkgs", "priced", "fixes/pkg", "promos", "usd", "usd/pkg"], rows))

    print("\nReviews\n")
    kinds = [name for name, _ in REVIEW_KINDS] + ["other"]
    rows = [[kind, sum(r["reviews"][kind] for r in records)] for kind in kinds]
    rows.append(["total", sum(sum(r["reviews"].values()) for r in records)])
    print(table(["kind", "count"], rows))

    print("\nTotals\n")
    priced = [r["usd"] for r in records if r["usd"] is not None]
    councils = sum(r["councils"] for r in records)
    council_tokens = sum(r["council_tokens"] for r in records)
    rows = [
        ["runs", len(records)],
        ["runs priced", len(priced)],
        ["packages", sum(r["packages"] for r in records)],
        ["fix rounds", sum(r["fix_rounds"] for r in records)],
        ["promotions", sum(r["promotions"] for r in records)],
        ["councils", councils],
        ["council tokens", council_tokens],
        ["escalations", sum(r["escalations"] for r in records)],
        ["compactions", sum(r["compactions"] for r in records)],
        ["usd, priced runs", money(sum(priced) if priced else None)],
        ["usd per priced run", money(sum(priced) / len(priced) if priced else None)],
    ]
    print(table(["measure", "value"], rows))

    if skips:
        print("\nSkipped\n")
        for line in skips:
            print(f"  {line}")


def main(argv: list[str]) -> None:
    parser = argparse.ArgumentParser(description="Print crew statistics over every record.")
    parser.add_argument("--record-root", help="the record root; default $CREW_RECORD_ROOT or ~/.claude/crew/")
    parser.add_argument("--repo", action="append", default=[], metavar="SLUG=CHECKOUT",
                        help="price this run from this checkout, when the record names none; repeatable")
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON instead of tables")
    args = parser.parse_args(argv)

    root = Path(args.record_root or os.environ.get("CREW_RECORD_ROOT") or Path.home() / ".claude" / "crew").expanduser()
    if not root.is_dir():
        sys.exit(f"no record root at {root}")

    overrides = {}
    for item in args.repo:
        if "=" not in item:
            sys.exit(f"--repo wants SLUG=CHECKOUT, got {item}")
        slug, checkout = item.split("=", 1)
        overrides[slug] = checkout

    skips: list[str] = []
    records = []
    for record in sorted(p for p in root.iterdir() if p.is_dir()):
        if not (record / "state.json").is_file():
            skips.append(f"{record.name}: not a record — no state.json")
            continue
        try:
            state = json.loads((record / "state.json").read_text(encoding="utf-8"))
        except ValueError as err:
            skips.append(f"{record.name}: unreadable state.json — {err}")
            continue
        checkout = overrides.get(record.name) or state.get("repo") or (state.get("run") or {}).get("repo")
        records.append(read_record(record, checkout, skips))

    if not records:
        sys.exit(f"no records under {root}")

    if args.json:
        print(json.dumps({"record_root": str(root), "records": records, "skipped": skips}, indent=2))
    else:
        report(records, skips)


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3
"""Read every crew record under the record root and print what the runs cost.

usage: crew-stats.py [--record-root <dir>] [--repo <slug>=<checkout>] [--json]

The record root is `--record-root`, or `$CREW_RECORD_ROOT`, or `~/.claude/crew/`
(`record-format.md`). One directory with a `state.json` is one run.

Prints cost per package by band, fix rounds by band, promotions from
`band_history`, councils and their spend, escalations, compactions, review
counts and the review catch rate. Design §8 asks for these numbers to turn the
band rubric from a guess into a measurement, and to give a principal a
defensible charter `Budget:`.

The catch rate is one number per review kind: the share of that kind's reviews
that returned an action verdict. A review file's `Verdict:` line is the only
machine-readable statement the record holds about whether a review changed
anything. The record carries no per-finding adjudication, so a review that was
accepted and still produced a commit counts as no catch here (§15.57).

Dollars come from `spend.py`, which this script imports. It never holds a
second price table. A run is priced in this order:

1. `spend.py` over the checkout a `--repo <slug>=<checkout>` flag names. An
   explicit flag always wins, because a stored figure can be stale (§15.51).
2. `run.spend.transcript.usd_list_price`, when `spend.py --write` stored it.
3. `spend.py` over the checkout the record names in `repo`.
4. Not priced. The run still counts everywhere else, and a skip line says so.

Two runs can share one checkout, so a run priced here closes its window at
`run.completed_at`, or at its latest `state_changed_at`. Without that bound
each run absorbs its neighbours' cost and the totals double count. A run with
no recorded end prices open-ended, and a skip line says so.

An older or partial record never stops the script. A missing field is skipped,
the record is still counted, and one line names what was skipped.

The script only reads. It writes nothing into the record root.
"""

import argparse
import datetime
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import spend  # noqa: E402  the price table and the transcript pricing live there

BANDS = ["light", "standard", "deep"]

def as_list(value) -> list:
    """The value when it is a list, and an empty list otherwise.

    An older record can hold a scalar, or nothing, where a list belongs.
    """
    return value if isinstance(value, list) else []


def fixes(package: dict) -> int:
    """The package's fix rounds, and 0 when the field is missing or not a number."""
    value = package.get("fix_rounds_used")
    return value if isinstance(value, int) and not isinstance(value, bool) else 0


REVIEW_KINDS = [
    ("package review", re.compile(r"^(?P<subject>.+)-package-review-r\d+\.md$")),
    ("spec critic", re.compile(r"^spec-critic-r\d+\.md$")),
    ("split critic", re.compile(r"-split-critic-r\d+\.md$")),
    ("deliverable review", re.compile(r"-deliverable-review\.md$")),
]

# Each review agent names its own two verdict strings. The first of each pair
# accepts the artifact and the second sends it back for another round
# (`agents/package-reviewer.md`, `spec-critic.md`, `split-critic.md`,
# `deliverable-reviewer.md`). A verdict outside all eight gets a skip line: it
# is a drifted string, not a clean review, and counting it as clean would
# deflate the catch rate without saying so.
ACTION_VERDICTS = ("fix round needed", "re-spec needed", "re-split needed")
CLEAN_VERDICTS = ("accepted", "ready to split", "dispatchable")
# `Verdict:` is not anchored to column 0. `record-format.md` lets the project
# lead transcribe a report whose write was denied, and a transcript can put the
# verdict mid-line.
VERDICT = re.compile(r"Verdict:\s*([^\n.]+)")


def run_end(state: dict) -> float | None:
    """The moment the run stopped changing, from the record's own timestamps.

    Two runs can share one checkout, so a run priced from that checkout must
    close its window or it absorbs its neighbours' cost. `run.completed_at` is
    the answer when the record carries it; the latest `state_changed_at`
    across the deliverables and the packages is the fallback. A run that is
    still live has no end, and prices open-ended.
    """
    run = state.get("run")
    run = run if isinstance(run, dict) else {}
    stamps = [run.get("completed_at")]
    for key in ("deliverables", "packages"):
        for entry in as_list(state.get(key)):
            if isinstance(entry, dict):
                stamps.append(entry.get("state_changed_at"))
    if run.get("run_state") != "complete" and not run.get("completed_at"):
        return None
    latest = max((s for s in stamps if isinstance(s, str)), default=None)
    if not latest:
        return None
    try:
        return datetime.datetime.fromisoformat(latest.replace("Z", "+00:00")).timestamp()
    except ValueError:
        return None


def price_run(record: Path, state: dict, checkout: str | None, forced: bool, skips: list) -> float | None:
    """Return the run's cost in US dollars, or None when nothing can price it."""
    stored = ((state.get("run") or {}).get("spend") or {}).get("transcript") or {}
    # An explicit --repo wins over a stored figure. §15.51 shows a stored
    # figure can be stale, and this is the only way to recompute one.
    if not forced and isinstance(stored, dict) and stored.get("usd_list_price") is not None:
        return float(stored["usd_list_price"])
    if not checkout:
        skips.append(f"{record.name}: no cost — the record has no spend.transcript and names no checkout")
        return None
    checkout = os.path.expanduser(checkout)
    dirs = spend.project_dirs(checkout)
    if not dirs:
        skips.append(f"{record.name}: no cost — no transcripts for checkout {checkout}")
        return None
    try:
        until = run_end(state)
        totals = spend.collect(dirs, spend.start_time(record, state), until)
    except (OSError, ValueError) as err:
        skips.append(f"{record.name}: no cost — {err}")
        return None
    if until is None:
        skips.append(f"{record.name}: open-ended cost — the run records no end, so the price covers every later session in {checkout}")
    return sum(t["usd"] for t in totals.values())


def blank_catch() -> dict:
    return {"reviews": 0, "acted": 0, "unverdicted": 0}


def read_reviews(record: Path, bands: dict, skips: list) -> tuple[dict, dict, dict]:
    """Return the review counts, the catch counts by kind, and the same by band.

    A review "acted" when its `Verdict:` line is one of `ACTION_VERDICTS` —
    the record's only machine-readable statement that the review sent the
    artifact back. A file with no verdict, or with a verdict outside the eight
    the agents name, is counted as a review and as `unverdicted`, never as a
    catch, and it gets a skip line that says which of the two it is.
    """
    counts = {name: 0 for name, _ in REVIEW_KINDS}
    counts["other"] = 0
    by_kind = {name: blank_catch() for name, _ in REVIEW_KINDS}
    by_band = {}
    directory = record / "reviews"
    if not directory.is_dir():
        skips.append(f"{record.name}: no reviews — the record has no reviews/ directory")
        return counts, by_kind, by_band
    for name in sorted(os.listdir(directory)):
        for kind, pattern in REVIEW_KINDS:
            found = pattern.search(name)
            if found:
                break
        else:
            counts["other"] += 1
            continue
        counts[kind] += 1
        try:
            text = (directory / name).read_text(encoding="utf-8", errors="replace")
            reason = None
        except OSError as err:
            text = ""
            reason = str(err)
        # `review-output.md` puts the verdict at the end of the report, so the
        # last match wins. A report that quotes an earlier round's verdict in
        # its prose must not be read by that quote.
        found_verdicts = VERDICT.findall(text)
        verdict = found_verdicts[-1].strip().lower() if found_verdicts else None
        acted = bool(verdict and verdict.startswith(ACTION_VERDICTS))
        known = bool(verdict and verdict.startswith(ACTION_VERDICTS + CLEAN_VERDICTS))
        if reason is None and verdict is None:
            reason = "the file states no Verdict: line"
        elif reason is None and not known:
            reason = f"its verdict {verdict!r} is none of the eight the agents name"
        by_kind[kind]["reviews"] += 1
        if known:
            by_kind[kind]["acted"] += acted
        else:
            by_kind[kind]["unverdicted"] += 1
            skips.append(f"{record.name}/{name}: no catch — {reason}")
        if kind != "package review":
            continue
        # A package review's file name opens with its package id, so the band
        # comes from `state.json`. A review of a package the record does not
        # list gets `unknown`, the same word the band columns use.
        band = bands.get(found.group("subject"), "unknown")
        counts_for = by_band.setdefault(band, blank_catch())
        counts_for["reviews"] += 1
        if known:
            counts_for["acted"] += acted
        else:
            counts_for["unverdicted"] += 1
    return counts, by_kind, by_band


def read_decisions(record: Path, skips: list) -> tuple[int, int, int]:
    """Return the decision count, the council count and the council tokens."""
    path = record / "decisions.md"
    if not path.is_file():
        skips.append(f"{record.name}: no decisions — the record has no decisions.md")
        return 0, 0, 0
    text = path.read_text(encoding="utf-8", errors="replace")
    entries = re.split(r"^## ", text, flags=re.M)[1:]
    councils = 0
    tokens = 0
    for entry in entries:
        if not re.search(r"^Route:\s*council\b", entry, flags=re.M):
            continue
        councils += 1
        # `Spend:` reads `unmeasured` when the dispatch reported no tokens,
        # and a council still awaiting adjudication has no `Spend:` line at
        # all (`record-format.md`). Both leave the token total short, so both
        # get a skip line.
        found = re.search(r"^Spend:[^\d\n]*([\d,]+)\s*tokens", entry, flags=re.M)
        if found:
            tokens += int(found.group(1).replace(",", ""))
        else:
            title = entry.splitlines()[0].strip()
            skips.append(f"{record.name}: no council spend — the entry \"{title}\" states no token count")
    return len(entries), councils, tokens


def read_record(record: Path, state: dict, checkout: str | None, forced: bool, skips: list) -> dict:
    run = state.get("run")
    run = run if isinstance(run, dict) else {}
    listed = as_list(state.get("packages"))
    packages = [p for p in listed if isinstance(p, dict)]
    if len(packages) != len(listed):
        skips.append(f"{record.name}: {len(listed) - len(packages)} package entries dropped — they are not objects")
    if not packages:
        skips.append(f"{record.name}: no packages — the record lists none")

    per_band = {}
    promotions = 0
    for package in packages:
        band = package.get("band")
        if band not in BANDS:
            skips.append(f"{record.name}/{package.get('id', '?')}: no band — the package records {band!r}")
            band = "unknown"
        counts = per_band.setdefault(band, {"packages": 0, "fix_rounds": 0, "promotions": 0})
        counts["packages"] += 1
        counts["fix_rounds"] += fixes(package)
        # A band_history entry with a cause is a promotion; the first entry is
        # the prediction and carries none (record-format.md, design §8).
        moved = sum(1 for h in as_list(package.get("band_history")) if isinstance(h, dict) and h.get("cause"))
        counts["promotions"] += moved
        promotions += moved

    decisions, councils, council_tokens = read_decisions(record, skips)
    bands = {p.get("id"): (p.get("band") if p.get("band") in BANDS else "unknown") for p in packages}
    reviews, catch, catch_by_band = read_reviews(record, bands, skips)
    usd = price_run(record, state, checkout, forced, skips)
    return {
        "run": record.name,
        "run_state": run.get("run_state"),
        "packages": len(packages),
        "by_band": per_band,
        "fix_rounds": sum(fixes(p) for p in packages),
        "promotions": promotions,
        "decisions": decisions,
        "councils": councils,
        "council_tokens": council_tokens,
        "escalations": len(as_list(run.get("escalations"))),
        "compactions": len(as_list(run.get("compactions"))),
        "reviews": reviews,
        "catch": catch,
        "catch_by_band": catch_by_band,
        "usd": usd,
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


def rate(part: int, whole: int) -> str:
    # One decimal, because 4 of 32 is 12.5 and `.0f` would resolve that tie by
    # Python's rounding rule rather than by the data.
    return "-" if not whole else f"{100 * part / whole:.1f}%"


def report(records: list[dict], skips: list[str]) -> None:
    print("Runs\n")
    rows = [
        [r["run"], r["packages"], r["fix_rounds"], r["promotions"], r["decisions"], r["councils"],
         r["escalations"], r["compactions"], sum(r["reviews"].values()), money(r["usd"])]
        for r in records
    ]
    print(table(["run", "pkgs", "fixes", "promos", "decis", "councils", "escal", "compact", "reviews", "usd"], rows))

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

    # A review "acted" when its verdict sent the artifact back for another
    # round. That is the whole of what the record states. A review that was
    # accepted and still produced a commit is not counted (§15.57).
    print("\nCatch rate (share of reviews whose verdict sent the artifact back)\n")
    rows = []
    for kind, _ in REVIEW_KINDS:
        total = sum(r["catch"][kind]["reviews"] for r in records)
        acted = sum(r["catch"][kind]["acted"] for r in records)
        blank = sum(r["catch"][kind]["unverdicted"] for r in records)
        rows.append([kind, total, acted, rate(acted, total), blank])
    print(table(["kind", "reviews", "acted", "rate", "unscored"], rows))

    print("\nPackage reviews by band\n")
    per_band = {}
    for r in records:
        for band, counts in r["catch_by_band"].items():
            total = per_band.setdefault(band, blank_catch())
            for key, value in counts.items():
                total[key] += value
    order = [b for b in BANDS if b in per_band] + [b for b in sorted(per_band) if b not in BANDS]
    rows = [[band, per_band[band]["reviews"], per_band[band]["acted"],
             rate(per_band[band]["acted"], per_band[band]["reviews"]),
             per_band[band]["unverdicted"]] for band in order]
    print(table(["band", "reviews", "acted", "rate", "unscored"], rows))

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
        ["decisions", sum(r["decisions"] for r in records)],
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
        except (OSError, ValueError) as err:
            skips.append(f"{record.name}: unreadable state.json — {err}")
            continue
        if not isinstance(state, dict):
            skips.append(f"{record.name}: unreadable state.json — it holds a {type(state).__name__}, not an object")
            continue
        run = state.get("run")
        stored_repo = state.get("repo") or (run.get("repo") if isinstance(run, dict) else None)
        forced = record.name in overrides
        checkout = overrides.get(record.name) or stored_repo
        # One malformed record must not take the other ten down with it.
        try:
            records.append(read_record(record, state, checkout, forced, skips))
        except (AttributeError, KeyError, TypeError, ValueError) as err:
            skips.append(f"{record.name}: unreadable record — {type(err).__name__}: {err}")

    if not records:
        sys.exit(f"no records under {root}")

    if args.json:
        print(json.dumps({"record_root": str(root), "records": records, "skipped": skips}, indent=2))
    else:
        report(records, skips)


if __name__ == "__main__":
    main(sys.argv[1:])

#!/usr/bin/env python3
"""Counts over the AI market dataset (data/ai-market/postings.jsonl) for /ai-market.

Usage:
  python3 scripts/ai_market_stats.py              # full markdown tables
  python3 scripts/ai_market_stats.py --reachable  # only postings eligible from Spain (yes/unclear)
  python3 scripts/ai_market_stats.py --since 2026-10-01 --archetype agent-engineer
  python3 scripts/ai_market_stats.py --summary    # size, date range, per platform
  python3 scripts/ai_market_stats.py --validate [file]  # check lines against the taxonomy

The allowed tags are read from .claude/skills/ai-market/taxonomy.md, so the vocabulary
lives in one place. Standard library only.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "ai-market" / "postings.jsonl"
TAXONOMY = ROOT / ".claude" / "skills" / "ai-market" / "taxonomy.md"

REQUIRED = ["id", "seen", "platform", "url", "title", "company", "region",
            "eligible_from_spain", "seniority", "archetype", "languages",
            "must_have", "nice_to_have", "gap", "readiness"]
TAG_KEYS = ["languages", "must_have", "nice_to_have", "gap"]
ENUMS = {
    "region": {"ES", "EU-remote", "NL", "UK", "IE", "US", "global-remote", "other-EU", "other"},
    "work_mode": {"remote", "hybrid", "onsite", "unclear"},
    "eligible_from_spain": {"yes", "no", "unclear"},
    "seniority": {"junior", "mid", "senior", "staff+", "unclear"},
    "english": {"B2-ok", "C1+", "native", "unstated"},
    "readiness": {"now", "stretch", "far"},
}


def load_taxonomy() -> tuple[set[str], set[str]]:
    """Return (archetypes, skill tags) parsed from the taxonomy tables."""
    text = TAXONOMY.read_text(encoding="utf-8")
    section = lambda name: text.split(f"## {name}", 1)[1].split("\n## ", 1)[0]
    archetypes = set(re.findall(r"^\| `([a-z0-9+-]+)` \|", section("Archetypes"), re.M))
    tags = set(re.findall(r"`([a-z0-9+-]+)`", section("Skill tags")))
    return archetypes, tags


def read_lines(path: Path) -> list[tuple[int, str]]:
    if not path.exists():
        return []
    return [(n, l) for n, l in enumerate(path.read_text(encoding="utf-8").splitlines(), 1) if l.strip()]


def validate(path: Path) -> int:
    archetypes, tags = load_taxonomy()
    bad, ids = 0, Counter()
    for n, line in read_lines(path):
        problems = []
        try:
            rec = json.loads(line)
        except json.JSONDecodeError as e:
            print(f"line {n}: not JSON ({e})")
            bad += 1
            continue
        problems += [f"missing {k}" for k in REQUIRED if k not in rec]
        if rec.get("archetype") not in archetypes:
            problems.append(f"unknown archetype {rec.get('archetype')!r}")
        for key, allowed in ENUMS.items():
            if key in rec and rec[key] not in allowed:
                problems.append(f"{key}={rec[key]!r} not in {sorted(allowed)}")
        for key in TAG_KEYS:
            unknown = [t for t in rec.get(key) or [] if t not in tags]
            if unknown:
                problems.append(f"{key}: unknown tags {unknown}")
        ids[rec.get("id")] += 1
        if problems:
            bad += 1
            print(f"line {n} ({rec.get('id')}): " + "; ".join(problems))
    for i, c in ids.items():
        if c > 1:
            print(f"duplicate id {i} ({c}x)")
            bad += 1
    print(f"{len(ids)} records, {bad} problem(s)")
    return 1 if bad else 0


def table(title: str, counter: Counter, total: int, top: int = 25) -> str:
    if not counter:
        return f"### {title}\n\n(none)\n"
    rows = [f"| {k} | {v} | {100 * v / total:.0f}% |" for k, v in counter.most_common(top)]
    return f"### {title}\n\n| Value | Postings | Share |\n|---|---|---|\n" + "\n".join(rows) + "\n"


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--validate", nargs="?", const=str(DATA), metavar="FILE")
    ap.add_argument("--summary", action="store_true")
    ap.add_argument("--reachable", action="store_true", help="eligible_from_spain in yes/unclear")
    ap.add_argument("--since", help="seen on or after YYYY-MM-DD")
    ap.add_argument("--archetype")
    ap.add_argument("--top", type=int, default=25)
    args = ap.parse_args()

    if args.validate:
        return validate(Path(args.validate))

    recs = []
    for n, line in read_lines(DATA):
        try:
            recs.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"warning: line {n} is not JSON, skipped (run --validate)", file=sys.stderr)
    if args.reachable:
        recs = [r for r in recs if r.get("eligible_from_spain") in ("yes", "unclear")]
    if args.since:
        recs = [r for r in recs if (r.get("seen") or "") >= args.since]
    if args.archetype:
        recs = [r for r in recs if r.get("archetype") == args.archetype]

    total = len(recs)
    seen = sorted(r.get("seen") or "" for r in recs)
    filters = [f for f, on in [("reachable from Spain", args.reachable), (f"since {args.since}", args.since),
                               (f"archetype {args.archetype}", args.archetype)] if on]
    print(f"## AI market: {total} postings" + (f" ({', '.join(filters)})" if filters else ""))
    if total:
        print(f"\nSeen {seen[0]} .. {seen[-1]}\n")
    print(table("Platform", Counter(r.get("platform") for r in recs), total or 1))
    if args.summary or not total:
        return 0

    one = lambda key: Counter(r.get(key) for r in recs)
    many = lambda key: Counter(t for r in recs for t in set(r.get(key) or []))
    for title, counter in [
        ("Archetype", one("archetype")), ("Region", one("region")),
        ("Eligible from Spain", one("eligible_from_spain")), ("Seniority", one("seniority")),
        ("Readiness", one("readiness")), ("English", one("english")),
        ("Languages", many("languages")), ("Must have", many("must_have")),
        ("Nice to have", many("nice_to_have")), ("Gaps (must-haves without evidence)", many("gap")),
    ]:
        print(table(title, counter, total, args.top))
    years = [r["years_required"] for r in recs if isinstance(r.get("years_required"), int)]
    if years:
        years.sort()
        print(f"### Years required\n\n{len(years)} postings state it; median {years[len(years) // 2]}, "
              f"min {years[0]}, max {years[-1]}\n")
    hunt = [r for r in recs if r.get("hunt_candidate")]
    if hunt:
        print("### Hunt candidates\n")
        for r in hunt:
            print(f"- {r.get('company')} | {r.get('title')} | {r.get('url')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

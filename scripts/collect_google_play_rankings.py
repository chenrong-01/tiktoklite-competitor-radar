#!/usr/bin/env python3
"""Collect per-country Google Play category Top-Free rankings (REAL charts).

Upgrade note (2026-W26): the old implementation scraped the public category
recommendation web page, which only approximated the chart and missed real hits
(e.g. Setlog, which ranks #1 in KR Social but never appeared on the scraped
page). We now call the Node ``google-play-scraper`` ``list`` API (TOP_FREE
collection) via ``scripts/gp_chart.mjs``, which returns the actual ranked chart.

The output CSV schema is unchanged, so downstream (build_candidate_pool.py) is
unaffected. If Node or the dependency is unavailable, each country/genre is
skipped with a warning (the run continues).
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "rankings"
GP_CHART = ROOT / "scripts" / "gp_chart.mjs"

# Radar genre -> Google Play category id (uppercase, as the Node API expects).
CATEGORIES = {
    "social": "SOCIAL",
    "video_players": "VIDEO_PLAYERS",
    "photography": "PHOTOGRAPHY",
    "entertainment": "ENTERTAINMENT",
}

DEFAULT_COUNTRIES = ["us", "gb", "jp", "kr", "br", "mx", "id", "th", "vn", "ph"]
DEFAULT_GENRES = list(CATEGORIES)

# System/utility apps that pollute the charts but are not content competitors.
# Matched against the lowercased product title.
NOISE_APPS = {
    "android system webview",
    "google play services",
    "google",
}


def node_binary() -> str | None:
    return shutil.which("node")


def fetch_chart(country: str, genre: str, limit: int) -> list[dict[str, str]]:
    """Return the real Top-Free chart for one country x genre via the Node helper."""
    node = node_binary()
    if not node:
        print("Warning: 'node' not found; skipping Google Play charts.", file=sys.stderr)
        return []
    if not GP_CHART.exists():
        print(f"Warning: {GP_CHART} missing; skipping.", file=sys.stderr)
        return []
    command = [
        node,
        str(GP_CHART),
        "--country",
        country.lower(),
        "--category",
        CATEGORIES[genre],
        "--num",
        str(max(limit * 3, limit)),  # over-fetch so noise drops still leave `limit` rows
    ]
    try:
        result = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=60
        )
    except Exception as error:  # noqa: BLE001
        print(f"Warning: skipped {country}/{genre}: {error}", file=sys.stderr)
        return []
    if result.returncode != 0:
        msg = (result.stderr or "").strip()
        print(f"Warning: skipped {country}/{genre}: {msg}", file=sys.stderr)
        return []
    try:
        return json.loads(result.stdout or "[]")
    except json.JSONDecodeError as error:
        print(f"Warning: bad JSON for {country}/{genre}: {error}", file=sys.stderr)
        return []


def collect(country: str, genre: str, limit: int, drop_noise: bool = True) -> list[dict[str, str]]:
    chart = fetch_chart(country, genre, limit)
    rows: list[dict[str, str]] = []
    rank = 0
    for entry in chart:
        if rank >= limit:
            break
        name = (entry.get("title") or entry.get("appId") or "").strip()
        if not name:
            continue
        if drop_noise and name.lower() in NOISE_APPS:
            continue
        rank += 1
        rows.append(
            {
                "country": country.upper(),
                "genre": genre,
                "rank": str(rank),
                "app": name,
                "developer": entry.get("developer", "") or "",
                "url": entry.get("url", "")
                or f"https://play.google.com/store/apps/details?id={entry.get('appId', '')}",
            }
        )
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Google Play category Top-Free rankings per country.")
    parser.add_argument("--week", required=True)
    parser.add_argument("--countries", nargs="*", default=DEFAULT_COUNTRIES)
    parser.add_argument("--genres", nargs="*", default=DEFAULT_GENRES, choices=list(CATEGORIES))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--keep-noise", action="store_true", help="Keep system/utility apps instead of filtering them out.")
    args = parser.parse_args()

    all_rows: list[dict[str, str]] = []
    for country in args.countries:
        for genre in args.genres:
            all_rows.extend(collect(country, genre, args.limit, drop_noise=not args.keep_noise))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"google_play_category_{args.week}.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["week", "date", "country", "genre", "rank", "app", "developer", "url"])
        writer.writeheader()
        today = date.today().isoformat()
        for row in all_rows:
            writer.writerow({"week": args.week, "date": today, **row})
    print(f"Wrote {out}  ({len(all_rows)} rows)")


if __name__ == "__main__":
    main()

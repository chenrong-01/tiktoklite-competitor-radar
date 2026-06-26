#!/usr/bin/env python3
"""Collect per-country Apple App Store category top-free rankings.

Uses Apple's category RSS feed so we can target specific genres
(Social, Photo & Video) instead of the mixed all-category top chart.
"""

from __future__ import annotations

import argparse
import csv
import json
import ssl
import sys
from datetime import date
from pathlib import Path
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "rankings"

# Apple genre ids
GENRES = {
    "social": "6005",          # Social Networking
    "photo_video": "6026",     # Photo & Video
    "entertainment": "6016",   # Entertainment
}

DEFAULT_COUNTRIES = ["us", "gb", "jp", "kr", "br", "mx", "id", "th", "vn", "ph"]
DEFAULT_GENRES = ["social", "photo_video", "entertainment"]

# Developer / utility apps that pollute the Photo & Video and Social charts but
# are not content-creation or content-consumption competitors. Filtered out by
# default so the ranking signal stays focused on real competitor products.
NOISE_APPS = {
    "testflight",
    "github",
    "expo go",
    "apple developer",
    "codex relay - remote codex app",
    "proxypin - open source capture",
    "plist editor mobile",
    "scriptable",
    "vks totp",
    "resolutioner",
    "loupe: what apps can see",
}


def feed_url(country: str, genre_id: str, limit: int) -> str:
    return f"https://itunes.apple.com/{country}/rss/topfreeapplications/limit={limit}/genre={genre_id}/json"


def fetch(url: str) -> dict:
    ctx = ssl._create_unverified_context()
    with urlopen(url, timeout=30, context=ctx) as resp:
        return json.loads(resp.read().decode("utf-8"))


def collect(country: str, genre: str, limit: int, drop_noise: bool = True) -> list[dict[str, str]]:
    # Over-fetch so that, after dropping developer/utility noise, we still have a
    # full Top-N of real competitor apps.
    fetch_limit = min(limit * 3, 100) if drop_noise else limit
    url = feed_url(country, GENRES[genre], fetch_limit)
    try:
        data = fetch(url)
    except Exception as error:  # noqa: BLE001
        print(f"Warning: skipped {country}/{genre}: {error}", file=sys.stderr)
        return []
    entries = data.get("feed", {}).get("entry", [])
    if isinstance(entries, dict):
        entries = [entries]
    rows = []
    rank = 0
    for item in entries:
        name = item.get("im:name", {}).get("label", "")
        if drop_noise and name.strip().lower() in NOISE_APPS:
            continue
        rank += 1
        rows.append(
            {
                "country": country.upper(),
                "genre": genre,
                "rank": str(rank),
                "app": name,
                "developer": item.get("im:artist", {}).get("label", ""),
                "url": (item.get("id", {}).get("label", "")),
            }
        )
        if rank >= limit:
            break
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Apple App Store category rankings per country.")
    parser.add_argument("--week", required=True)
    parser.add_argument("--countries", nargs="*", default=DEFAULT_COUNTRIES)
    parser.add_argument("--genres", nargs="*", default=DEFAULT_GENRES, choices=list(GENRES))
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--keep-noise", action="store_true", help="Keep developer/utility apps instead of filtering them out.")
    args = parser.parse_args()

    all_rows: list[dict[str, str]] = []
    for country in args.countries:
        for genre in args.genres:
            all_rows.extend(collect(country, genre, args.limit, drop_noise=not args.keep_noise))

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / f"app_store_category_{args.week}.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["week", "date", "country", "genre", "rank", "app", "developer", "url"])
        writer.writeheader()
        today = date.today().isoformat()
        for row in all_rows:
            writer.writerow({"week": args.week, "date": today, **row})
    print(f"Wrote {out}  ({len(all_rows)} rows)")


if __name__ == "__main__":
    main()

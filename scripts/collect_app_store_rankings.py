#!/usr/bin/env python3
"""Collect Apple App Store top-free rankings as radar candidate signals."""

from __future__ import annotations

import argparse
import csv
import json
import ssl
import sys
from datetime import date
from pathlib import Path
from urllib.error import URLError
from urllib.request import urlopen


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RANKINGS_DIR = DATA_DIR / "rankings"
SIGNALS_PATH = DATA_DIR / "signals.csv"

SIGNAL_FIELDS = [
    "week",
    "date",
    "app",
    "region",
    "module",
    "track",
    "radar_type",
    "category",
    "signal",
    "why_it_matters",
    "tiktok_lite_implication",
    "priority",
    "source_url",
    "screenshot_path",
    "status",
]

RANKING_FIELDS = ["rank", "app", "developer", "region", "store", "chart", "category", "source_url"]


def app_store_url(storefront: str, limit: int) -> str:
    return f"https://rss.applemarketingtools.com/api/v2/{storefront}/apps/top-free/{limit}/apps.json"


def fetch_url(url: str) -> str:
    try:
        with urlopen(url, timeout=30) as response:
            return response.read().decode("utf-8")
    except URLError as error:
        if "CERTIFICATE_VERIFY_FAILED" not in str(error):
            raise
        print(
            "Warning: SSL certificate verification failed; retrying with an unverified context for this request.",
            file=sys.stderr,
        )
        context = ssl._create_unverified_context()
        with urlopen(url, timeout=30, context=context) as response:
            return response.read().decode("utf-8")


def parse_app_store_feed(payload: str, storefront: str, genre: str = "all") -> list[dict[str, object]]:
    data = json.loads(payload)
    results = data.get("feed", {}).get("results", [])

    apps = []
    for index, item in enumerate(results, start=1):
        genres = item.get("genres") or []
        category = genres[0] if genres else genre
        apps.append(
            {
                "rank": index,
                "app": item.get("name", ""),
                "developer": item.get("artistName", ""),
                "url": item.get("url", ""),
                "region": storefront,
                "store": "apple_app_store",
                "chart": "top-free",
                "category": category,
            }
        )
    return apps


def collect_apps(storefront: str, limit: int, fetcher=fetch_url) -> list[dict[str, object]]:
    url = app_store_url(storefront, limit)
    try:
        return parse_app_store_feed(fetcher(url), storefront=storefront)
    except Exception as error:
        print(f"Warning: skipped Apple App Store {storefront} ranking fetch: {error}", file=sys.stderr)
        return []


def priority_for_rank(rank: int) -> str:
    if rank <= 5:
        return "high"
    if rank <= 25:
        return "medium"
    return "low"


def module_for_category(category: str) -> tuple[str, str]:
    normalized = category.lower()
    if any(token in normalized for token in ["photo", "video", "graphics", "design"]):
        return "emerging_creation", "creation"
    return "emerging_consumption", "consumption"


def app_to_signal_row(app: dict[str, object], week: str, date: str) -> dict[str, str]:
    rank = int(app["rank"])
    module, track = module_for_category(str(app.get("category", "")))
    app_name = str(app.get("app", ""))
    region = str(app.get("region", ""))
    category = str(app.get("category", ""))

    return {
        "week": week,
        "date": date,
        "app": app_name,
        "region": region,
        "module": module,
        "track": track,
        "radar_type": "emerging",
        "category": category,
        "signal": f"{app_name} reached #{rank} in Apple App Store top-free chart for {region}.",
        "why_it_matters": "Ranking movement can reveal emerging attention shifts before they become fixed competitors.",
        "tiktok_lite_implication": "Review the product flow, audience, and creation or consumption mechanic before deciding whether to deep dive.",
        "priority": priority_for_rank(rank),
        "source_url": str(app.get("url", "")),
        "screenshot_path": "",
        "status": "needs_review",
    }


def write_rankings(path: Path, apps: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=RANKING_FIELDS)
        writer.writeheader()
        for app in apps:
            writer.writerow(
                {
                    "rank": app["rank"],
                    "app": app["app"],
                    "developer": app["developer"],
                    "region": app["region"],
                    "store": app["store"],
                    "chart": app["chart"],
                    "category": app["category"],
                    "source_url": app["url"],
                }
            )


def append_signals(path: Path, rows: list[dict[str, str]]) -> None:
    file_exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=SIGNAL_FIELDS)
        if not file_exists:
            writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Apple App Store top-free rankings.")
    parser.add_argument("--week", required=True, help="Week key, for example 2026-W24")
    parser.add_argument("--storefront", default="us", help="Apple storefront code, for example us, jp, kr, br")
    parser.add_argument("--limit", type=int, default=25, help="Number of ranked apps to fetch")
    parser.add_argument("--date", default=date.today().isoformat(), help="Collection date in YYYY-MM-DD")
    parser.add_argument("--append-signals", action="store_true", help="Append fetched rankings to data/signals.csv")
    args = parser.parse_args()

    apps = collect_apps(args.storefront, args.limit)
    ranking_path = RANKINGS_DIR / f"apple_app_store_{args.storefront}_{args.week}.csv"
    write_rankings(ranking_path, apps)

    if args.append_signals:
        rows = [app_to_signal_row(app, week=args.week, date=args.date) for app in apps]
        append_signals(SIGNALS_PATH, rows)

    print(f"Wrote {ranking_path}")
    if args.append_signals:
        print(f"Appended {len(apps)} signal candidate(s) to {SIGNALS_PATH}")


if __name__ == "__main__":
    main()

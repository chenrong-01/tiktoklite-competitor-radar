#!/usr/bin/env python3
"""Collect news candidates for regular competitor and emerging product radar."""

from __future__ import annotations

import argparse
import csv
import json
import ssl
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.parse import quote_plus
from urllib.request import urlopen
from xml.etree import ElementTree


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "config" / "news_queries.json"
OUTPUT_DIR = ROOT / "data" / "news_candidates"

CANDIDATE_FIELDS = [
    "week",
    "query_type",
    "query",
    "locale",
    "radar_type",
    "track",
    "title",
    "publisher",
    "published",
    "source_url",
    "status",
]

RELEVANT_TERMS = [
    "app",
    "apps",
    "platform",
    "feature",
    "creator",
    "creators",
    "video",
    "shorts",
    "reels",
    "lens",
    "ai",
    "social",
    "chat",
    "feed",
    "drama",
    "microdrama",
    "camera",
    "photo",
    "voice",
    "companion",
]

IRRELEVANT_PHRASES = [
    "viral social media posts",
    "viral video claims",
    "viral social media showdown",
    "used racial slur",
    "social media star",
    "recent speech",
    "accuses him",
]

EMERGING_PRODUCT_TERMS = [
    "app",
    "apps",
    "platform",
    "tool",
    "tools",
    "product",
    "products",
]


def build_google_news_rss_url(query: str, locale: str = "US", language: str = "en", days: int = 7) -> str:
    dated_query = f"{query} when:{days}d" if days > 0 else query
    encoded_query = quote_plus(dated_query)
    return (
        f"https://news.google.com/rss/search?q={encoded_query}"
        f"&hl={language}-{locale}&gl={locale}&ceid={locale}:{language}"
    )


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


def parse_rss(payload: str) -> list[dict[str, str]]:
    root = ElementTree.fromstring(payload)
    items = []
    for item in root.findall("./channel/item"):
        source = item.find("source")
        items.append(
            {
                "title": text_or_empty(item, "title"),
                "link": text_or_empty(item, "link"),
                "source": source.text.strip() if source is not None and source.text else "",
                "published": text_or_empty(item, "pubDate"),
            }
        )
    return items


def text_or_empty(item: ElementTree.Element, name: str) -> str:
    child = item.find(name)
    return child.text.strip() if child is not None and child.text else ""


def item_to_candidate(
    item: dict[str, str],
    week: str,
    query: str,
    query_type: str,
    locale: str,
) -> dict[str, str]:
    radar_type = "fixed" if query_type == "regular_competitor" else "emerging"
    return {
        "week": week,
        "query_type": query_type,
        "query": query,
        "locale": locale,
        "radar_type": radar_type,
        "track": "needs_classification",
        "title": item["title"],
        "publisher": item["source"],
        "published": item["published"],
        "source_url": item["link"],
        "status": "candidate",
    }


def is_relevant_news_item(item: dict[str, str], query_type: str | None = None) -> bool:
    """L1 recall gate — recall-first: only drop OBVIOUS garbage.

    The old gate required the title to contain a RELEVANT_TERMS whitelist token
    (and, for emerging, an EMERGING_PRODUCT_TERMS token). That whitelist acted as
    a kill-switch at the recall stage and is exactly why real signals (e.g. the
    Fast Company "Multiple Captions" report) were dropped before the agent ever
    saw them. Per the five-layer design, recall must NOT judge to death — the
    pre-rank (scoring) and rank (agent cross-verification) layers do the
    filtering. So here we only drop items matching the explicit garbage phrase
    list; everything else is recalled.
    """
    title = item.get("title", "").lower()
    if any(phrase in title for phrase in IRRELEVANT_PHRASES):
        return False
    return True


def load_queries(path: Path) -> dict[str, list[str]]:
    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def collect_candidates(
    week: str,
    queries: dict[str, list[str]],
    locale: str,
    language: str,
    limit_per_query: int,
    fetcher=fetch_url,
    days: int = 7,
) -> list[dict[str, str]]:
    candidates = []
    for query_type, query_list in queries.items():
        for query in query_list:
            url = build_google_news_rss_url(query, locale=locale, language=language, days=days)
            try:
                payload = fetcher(url)
            except Exception as error:
                print(f"Warning: skipped query {query!r}: {error}", file=sys.stderr)
                continue
            items = [
                item
                for item in parse_rss(payload)
                if is_relevant_news_item(item, query_type=query_type)
            ]
            items = items[:limit_per_query]
            for item in items:
                candidates.append(
                    item_to_candidate(
                        item,
                        week=week,
                        query=query,
                        query_type=query_type,
                        locale=locale,
                    )
                )
    return dedupe_candidates(candidates)


def dedupe_candidates(candidates: list[dict[str, str]]) -> list[dict[str, str]]:
    seen = set()
    unique = []
    for candidate in candidates:
        key = candidate["source_url"] or candidate["title"]
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique


def write_candidates(path: Path, candidates: list[dict[str, str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=CANDIDATE_FIELDS)
        writer.writeheader()
        writer.writerows(candidates)


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect Google News RSS candidates for the radar.")
    parser.add_argument("--week", required=True, help="Week key, for example 2026-W24")
    parser.add_argument("--locale", default="US", help="Google News locale, for example US, GB, JP")
    parser.add_argument("--language", default="en", help="Google News language, for example en, ja")
    parser.add_argument("--limit-per-query", type=int, default=3, help="Number of articles per query")
    parser.add_argument("--days", type=int, default=7, help="Only collect articles from the last N days")
    args = parser.parse_args()

    candidates = collect_candidates(
        week=args.week,
        queries=load_queries(CONFIG_PATH),
        locale=args.locale,
        language=args.language,
        limit_per_query=args.limit_per_query,
        days=args.days,
    )
    output_path = OUTPUT_DIR / f"{args.week}_{args.locale}.csv"
    write_candidates(output_path, candidates)
    print(f"Wrote {output_path}")
    print(f"Collected {len(candidates)} news candidate(s)")


if __name__ == "__main__":
    main()

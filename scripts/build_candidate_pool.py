#!/usr/bin/env python3
"""Build a unified candidate pool from multi-region news candidates."""

from __future__ import annotations

import argparse
import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

OUTPUT_FIELDS = [
    "week",
    "query_type",
    "locale",
    "radar_type",
    "title",
    "publisher",
    "published",
    "source_url",
    "status",
    "reason",
]

EXCLUDE_PHRASES = {
    "monetization": "monetization/trading out of scope",
    "marketplace": "monetization/trading out of scope",
    "creator marketplace": "monetization/trading out of scope",
    "account trading": "monetization/trading out of scope",
    "paid subscription": "monetization/trading out of scope",
    "sports betting": "sports/finance out of scope",
    "dfs": "sports/finance out of scope",
    "crypto": "finance out of scope",
    "digital money": "finance out of scope",
    "short drama": "short drama out of scope",
    "microdrama": "short drama out of scope",
    "celebrity": "non-product signal",
    "scam": "non-product signal",
    "apple watch": "non-product signal",
    "first lady": "non-product signal",
    "snack craze": "non-product signal",
    "pineapple": "non-product signal",
    "politician": "non-product signal",
}

GENERIC_PHRASES = [
    "social media updates",
    "mobile app development",
    "shift from features to experiences",
    "apps you need to know",
]

REGULAR_COMPETITOR_TERMS = [
    "douyin",
    "tiktok",
    "capcut",
    "jianying",
    "xiaohongshu",
    "rednote",
    "instagram",
    "reels",
    "edits",
    "youtube",
    "shorts",
    "snapchat",
    "snap",
    "spectacles",
    "facebook",
    "meta",
    "threads",
    "twitter",
    "grok",
    "kuaishou",
    "kwai",
    "likee",
    "snackvideo",
    "lemon8",
    "reddit",
]

REGULAR_CHANGE_TERMS = [
    "new",
    "launch",
    "launches",
    "rollout",
    "rolls out",
    "test",
    "testing",
    "adds",
    "adding",
    "expand",
    "expanding",
    "feature",
    "update",
    "ai",
    "assistant",
    "desktop",
    "mode",
    "tool",
    "camera",
    "lens",
    "search",
    "feed",
    "recommendation",
    "repost",
    "remix",
    "download",
    "watermark",
    "version",
]

EMERGING_PRODUCT_TERMS = [
    "app",
    "setlog",
    "beeper",
    "noplace",
    "lapse",
    "retro",
    "airchat",
    "ten ten",
    "whee",
    "cara",
    "watermark",
    "repost",
    "remix",
    "download",
]

EMERGING_BEHAVIOR_TERMS = [
    "ai",
    "creator",
    "video",
    "social",
    "tiktok",
    "short video",
    "search",
    "camera",
    "vlog",
    "watermark",
    "repost",
    "remix",
    "download",
    "lens",
    "feed",
    "viral",
    "trend",
    "trending",
]

EMERGING_TOOL_TERMS = [
    "watermark",
    "repost",
    "remix",
    "download",
    "template",
]


def normalize_key(row: dict[str, str]) -> str:
    return (row.get("source_url") or row.get("title") or "").strip().lower()


def has_any(text: str, terms: list[str]) -> bool:
    for term in terms:
        if " " in term or "-" in term:
            if term in text:
                return True
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text):
            return True
    return False


def classify_regular_candidate(title: str) -> dict[str, str]:
    if has_any(title, GENERIC_PHRASES):
        return {"status": "excluded", "reason": "generic roundup or explainer"}
    if not has_any(title, REGULAR_COMPETITOR_TERMS):
        return {"status": "excluded", "reason": "no regular competitor named"}
    if not has_any(title, REGULAR_CHANGE_TERMS):
        return {"status": "excluded", "reason": "no explicit product change"}
    return {"status": "review", "reason": "regular competitor change"}


def classify_emerging_candidate(title: str) -> dict[str, str]:
    if has_any(title, REGULAR_COMPETITOR_TERMS) and not has_any(title, EMERGING_TOOL_TERMS):
        return {"status": "excluded", "reason": "regular competitor signal; review in fixed track"}
    if "video goes viral" in title and not has_any(title, EMERGING_PRODUCT_TERMS):
        return {"status": "excluded", "reason": "non-product viral signal"}
    if has_any(title, GENERIC_PHRASES):
        return {"status": "excluded", "reason": "generic app/industry article"}
    if not has_any(title, EMERGING_PRODUCT_TERMS):
        return {"status": "excluded", "reason": "no specific app/product signal"}
    if not has_any(title, EMERGING_BEHAVIOR_TERMS):
        return {"status": "excluded", "reason": "weak content-ecosystem relevance"}
    return {"status": "review", "reason": "emerging product signal"}


def classify_candidate(row: dict[str, str]) -> dict[str, str]:
    title = (row.get("title") or "").lower()
    for phrase, reason in EXCLUDE_PHRASES.items():
        if phrase in title:
            return {"status": "excluded", "reason": reason}
    if row.get("query_type") == "regular_competitor" or row.get("radar_type") == "fixed":
        return classify_regular_candidate(title)
    if row.get("query_type") == "emerging_product" or row.get("radar_type") == "emerging":
        return classify_emerging_candidate(title)
    if not has_any(title, REGULAR_CHANGE_TERMS + EMERGING_PRODUCT_TERMS + EMERGING_BEHAVIOR_TERMS):
        return {"status": "excluded", "reason": "weak product relevance"}
    return {"status": "review", "reason": "needs PM review"}


def read_candidate_files(root: Path, week: str) -> list[dict[str, str]]:
    rows = []
    for path in sorted((root / "data" / "news_candidates").glob(f"{week}_*.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                rows.append(row)
    return rows


def build_candidate_pool(root: Path, week: str, output_path: Path) -> list[dict[str, str]]:
    seen = set()
    output_rows = []
    for row in read_candidate_files(root, week):
        key = normalize_key(row)
        if not key or key in seen:
            continue
        seen.add(key)
        classification = classify_candidate(row)
        output_rows.append(
            {
                "week": week,
                "query_type": row.get("query_type", ""),
                "locale": row.get("locale", ""),
                "radar_type": row.get("radar_type", ""),
                "title": row.get("title", ""),
                "publisher": row.get("publisher", ""),
                "published": row.get("published", ""),
                "source_url": row.get("source_url", ""),
                "status": classification["status"],
                "reason": classification["reason"],
            }
        )

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)
    return output_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build unified TikTok Lite radar candidate pool.")
    parser.add_argument("--week", required=True)
    args = parser.parse_args()

    output_path = ROOT / "data" / "candidates" / f"{args.week}.csv"
    rows = build_candidate_pool(ROOT, args.week, output_path)
    print(f"Wrote {output_path}")
    print(f"Candidates: {len(rows)}")


if __name__ == "__main__":
    main()

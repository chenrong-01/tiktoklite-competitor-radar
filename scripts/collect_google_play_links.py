#!/usr/bin/env python3
"""Generate Google Play discovery links for Android competitor radar work."""

from __future__ import annotations

import argparse
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "data" / "google_play_checklists"

DEFAULT_MARKETS = [
    "us",
    "gb",
    "jp",
    "kr",
    "br",
    "mx",
    "id",
    "th",
    "vn",
    "ph",
    "my",
    "sa",
    "ae",
    "tr",
    "eg",
]

DEFAULT_CATEGORIES = [
    "SOCIAL",
    "VIDEO_PLAYERS",
    "ENTERTAINMENT",
    "PHOTOGRAPHY",
]

MARKET_LANGUAGES = {
    "ae": "ar",
    "br": "pt-BR",
    "eg": "ar",
    "gb": "en-GB",
    "id": "id",
    "jp": "ja",
    "kr": "ko",
    "mx": "es-419",
    "my": "ms",
    "ph": "en-PH",
    "sa": "ar",
    "th": "th",
    "tr": "tr",
    "us": "en-US",
    "vn": "vi",
}


def build_play_url(market: str, language: str, category: str) -> str:
    return f"https://play.google.com/store/apps/category/{category}?hl={language}&gl={market.upper()}"


def render_checklist(week: str, markets: list[str], categories: list[str]) -> str:
    lines = [
        f"# Google Play Discovery Checklist - {week}",
        "",
        "Use these links to scan Android-first markets for emerging social, creation, video, and entertainment apps.",
        "Capture ranking screenshots, product page screenshots, and any notable update text before adding curated rows to `data/signals.csv`.",
        "",
        "## Market Category Links",
        "",
    ]

    for market in markets:
        language = MARKET_LANGUAGES.get(market.lower(), "en-US")
        for category in categories:
            label = f"{market.upper()} / {category}"
            url = build_play_url(market=market, language=language, category=category)
            lines.append(f"- [ ] {label}: {url}")

    lines.extend(
        [
            "",
            "## Evidence To Capture",
            "",
            "- [ ] Category ranking screenshot",
            "- [ ] App detail page screenshot",
            "- [ ] Version update text",
            "- [ ] Install/download/rating context when visible",
            "- [ ] Creation or consumption mechanic notes",
            "- [ ] TikTok Lite implication",
            "",
            "## Suggested Triage",
            "",
            "- High: top-ranked or fast-rising social/video app with a clear new behavior.",
            "- Medium: relevant product mechanic but unclear growth durability.",
            "- Low: interesting app with weak market or behavior evidence.",
            "",
        ]
    )

    return "\n".join(lines)


def write_checklist(week: str, content: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{week}.md"
    output_path.write_text(content, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Google Play discovery links.")
    parser.add_argument("--week", required=True, help="Week key, for example 2026-W24")
    parser.add_argument("--markets", nargs="*", default=DEFAULT_MARKETS, help="Market codes, for example us br id")
    parser.add_argument("--categories", nargs="*", default=DEFAULT_CATEGORIES, help="Google Play category ids")
    args = parser.parse_args()

    output_path = write_checklist(args.week, render_checklist(args.week, args.markets, args.categories))
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

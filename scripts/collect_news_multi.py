#!/usr/bin/env python3
"""Collect Google News RSS candidates across multiple locales."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

DEFAULT_LOCALES = [
    "US:en",
    "GB:en",
    "JP:ja",
    "KR:ko",
    "BR:pt-BR",
    "ID:id",
    "PH:en",
    "TH:th",
    "VN:vi",
    "MX:es-419",
    "NG:en",
    "ZA:en",
    "KE:en",
    "EG:ar",
]


def parse_locale_spec(spec: str) -> tuple[str, str]:
    if ":" not in spec:
        return spec.upper(), "en"
    locale, language = spec.split(":", 1)
    return locale.upper(), language


def main() -> None:
    parser = argparse.ArgumentParser(description="Collect news candidates for multiple locales.")
    parser.add_argument("--week", required=True, help="Week key, for example 2026-W25")
    parser.add_argument("--locales", nargs="*", default=DEFAULT_LOCALES, help="Locale specs like US:en JP:ja")
    parser.add_argument("--limit-per-query", type=int, default=3)
    parser.add_argument("--days", type=int, default=10)
    args = parser.parse_args()

    script = ROOT / "scripts" / "collect_news_rss.py"
    failures = []
    for spec in args.locales:
        locale, language = parse_locale_spec(spec)
        command = [
            sys.executable,
            str(script),
            "--week",
            args.week,
            "--locale",
            locale,
            "--language",
            language,
            "--limit-per-query",
            str(args.limit_per_query),
            "--days",
            str(args.days),
        ]
        print(f"Collecting news for {locale}:{language}")
        result = subprocess.run(command, cwd=ROOT)
        if result.returncode != 0:
            failures.append(f"{locale}:{language}")

    if failures:
        print(f"Warning: failed locales: {', '.join(failures)}")


if __name__ == "__main__":
    main()

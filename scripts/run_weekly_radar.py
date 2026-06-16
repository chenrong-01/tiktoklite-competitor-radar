#!/usr/bin/env python3
"""One-command weekly runner for TikTok Lite radar."""

from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
from datetime import date
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT_DIR = ROOT / "reports" / "weekly"
FEISHU_DIR = ROOT / "reports" / "feishu"


def iso_week_key(day: date) -> str:
    iso = day.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def run_command(command: list[str], *, continue_on_failure: bool = False) -> int:
    print("+ " + " ".join(command))
    result = subprocess.run(command, cwd=ROOT)
    if result.returncode != 0 and not continue_on_failure:
        raise SystemExit(result.returncode)
    return result.returncode


def load_sources_and_screenshots(week: str) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    signals_path = ROOT / "data" / "signals.csv"
    sources = []
    screenshots = []
    if not signals_path.exists():
        return sources, screenshots

    with signals_path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("week") != week:
                continue
            if row.get("source_url"):
                sources.append({"title": row.get("app", "source"), "url": row["source_url"]})
            if row.get("screenshot_path"):
                screenshots.append({"label": row.get("app", "screenshot"), "path": row["screenshot_path"]})
    return sources, screenshots


def write_feishu_json(
    output_path: Path,
    title: str,
    markdown: str,
    sources: list[dict[str, str]],
    screenshots: list[dict[str, str]],
) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "title": title,
        "markdown": markdown,
        "sources": sources,
        "screenshots": screenshots,
    }
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def generate_reports(week: str) -> tuple[Path, Path]:
    run_command([sys.executable, "scripts/generate_report.py", "--week", week])
    markdown_path = REPORT_DIR / f"{week}.md"
    markdown = markdown_path.read_text(encoding="utf-8")
    sources, screenshots = load_sources_and_screenshots(week)
    feishu_path = FEISHU_DIR / f"{week}.json"
    write_feishu_json(
        feishu_path,
        title=f"TikTok Lite Weekly Radar · {week}",
        markdown=markdown,
        sources=sources,
        screenshots=screenshots,
    )
    return markdown_path, feishu_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Run TikTok Lite weekly radar.")
    parser.add_argument("--week", help="Week key, for example 2026-W25. Defaults to current ISO week.")
    parser.add_argument("--dry-run", action="store_true", help="Skip external collection and only generate reports.")
    parser.add_argument("--skip-screenshots", action="store_true", help="Do not capture source screenshots.")
    args = parser.parse_args()

    week = args.week or iso_week_key(date.today())

    if not args.dry_run:
        run_command([sys.executable, "scripts/collect_signals.py", "--week", week], continue_on_failure=True)
        run_command(
            [
                sys.executable,
                "scripts/collect_news_multi.py",
                "--week",
                week,
                "--limit-per-query",
                "1",
                "--days",
                "7",
            ],
            continue_on_failure=True,
        )
        run_command(
            [
                sys.executable,
                "scripts/collect_google_play_links.py",
                "--week",
                week,
                "--markets",
                "us",
                "br",
                "id",
                "jp",
                "kr",
                "ng",
                "za",
                "ke",
                "eg",
                "--categories",
                "SOCIAL",
                "VIDEO_PLAYERS",
                "ENTERTAINMENT",
                "PHOTOGRAPHY",
            ],
            continue_on_failure=True,
        )
        run_command([sys.executable, "scripts/build_candidate_pool.py", "--week", week], continue_on_failure=True)
        if not args.skip_screenshots:
            run_command(
                [
                    sys.executable,
                    "scripts/capture_pages.py",
                    "--week",
                    week,
                    "--input",
                    "data/signals.csv",
                    "--timeout-ms",
                    "30000",
                    "--wait-until",
                    "domcontentloaded",
                ],
                continue_on_failure=True,
            )

    markdown_path, feishu_path = generate_reports(week)
    print(f"Wrote {markdown_path}")
    print(f"Wrote {feishu_path}")


if __name__ == "__main__":
    main()

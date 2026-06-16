#!/usr/bin/env python3
"""Capture screenshots for App Store and Google Play radar evidence pages."""

from __future__ import annotations

import argparse
import asyncio
import csv
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
SCREENSHOT_INDEX_DIR = ROOT / "data" / "screenshots"
ASSET_SCREENSHOT_DIR = ROOT / "assets" / "screenshots"
URL_RE = re.compile(r"https?://[^\s)]+")


@dataclass(frozen=True)
class ScreenshotTarget:
    week: str
    source: str
    label: str
    url: str


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    return value.strip("-")


def extract_targets_from_csv(path: Path, week: str) -> list[ScreenshotTarget]:
    targets = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row in reader:
            row_week = (row.get("week") or "").strip()
            if row_week and row_week != week:
                continue
            url = (row.get("source_url") or row.get("url") or "").strip()
            if not url:
                continue
            label_parts = [
                row.get("rank", ""),
                row.get("app", ""),
                row.get("region", ""),
                row.get("category", ""),
            ]
            label = " ".join(part.strip() for part in label_parts if part and part.strip())
            targets.append(ScreenshotTarget(week=week, source=path.stem, label=label or "csv-row", url=url))
    return targets


def extract_targets_from_markdown(markdown: str, week: str, source: str) -> list[ScreenshotTarget]:
    targets = []
    for line in markdown.splitlines():
        match = URL_RE.search(line)
        if not match:
            continue
        url = match.group(0).rstrip(".,")
        label_text = line[: match.start()]
        label_text = re.sub(r"^- \[[ xX]\]\s*", "", label_text).strip()
        label_text = label_text.rstrip(":").strip() or urlparse(url).netloc
        targets.append(ScreenshotTarget(week=week, source=source, label=label_text, url=url))
    return targets


def extract_targets_from_markdown_file(path: Path, week: str) -> list[ScreenshotTarget]:
    return extract_targets_from_markdown(path.read_text(encoding="utf-8"), week=week, source=path.stem)


def screenshot_path_for_target(target: ScreenshotTarget) -> Path:
    source_slug = slugify(target.source)
    label_slug = slugify(target.label)
    return Path("assets") / "screenshots" / target.week / f"{source_slug}-{label_slug}.png"


def collect_targets(paths: list[Path], week: str) -> list[ScreenshotTarget]:
    targets = []
    for path in paths:
        if path.suffix.lower() == ".csv":
            targets.extend(extract_targets_from_csv(path, week=week))
        elif path.suffix.lower() in {".md", ".markdown"}:
            targets.extend(extract_targets_from_markdown_file(path, week=week))
        else:
            raise ValueError(f"Unsupported input file type: {path}")
    return dedupe_targets(targets)


def dedupe_targets(targets: list[ScreenshotTarget]) -> list[ScreenshotTarget]:
    seen = set()
    unique = []
    for target in targets:
        if target.url in seen:
            continue
        seen.add(target.url)
        unique.append(target)
    return unique


def limit_targets(targets: list[ScreenshotTarget], max_targets: int | None) -> list[ScreenshotTarget]:
    if max_targets is None:
        return targets
    return targets[:max_targets]


def write_index(week: str, targets: list[ScreenshotTarget]) -> Path:
    SCREENSHOT_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    path = SCREENSHOT_INDEX_DIR / f"{week}.csv"
    with path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["week", "source", "label", "url", "screenshot_path", "status"],
        )
        writer.writeheader()
        for target in targets:
            writer.writerow(
                {
                    "week": target.week,
                    "source": target.source,
                    "label": target.label,
                    "url": target.url,
                    "screenshot_path": screenshot_path_for_target(target),
                    "status": "pending",
                }
            )
    return path


async def capture_targets(targets: list[ScreenshotTarget], timeout_ms: int, wait_until: str) -> None:
    try:
        from playwright.async_api import async_playwright
    except ImportError as error:
        raise RuntimeError(
            "Playwright is not installed. Install it with `python3 -m pip install playwright` "
            "and then run `python3 -m playwright install chromium`."
        ) from error

    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch()
        page = await browser.new_page(viewport={"width": 1440, "height": 1600})
        for target in targets:
            output_path = ROOT / screenshot_path_for_target(target)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            try:
                await page.goto(target.url, wait_until=wait_until, timeout=timeout_ms)
                await page.screenshot(path=str(output_path), full_page=True)
            except Exception as error:
                print(f"Warning: skipped screenshot for {target.url}: {error}")
        await browser.close()


def default_input_paths(week: str) -> list[Path]:
    candidates = [
        ROOT / "data" / "google_play_checklists" / f"{week}.md",
        *sorted((ROOT / "data" / "rankings").glob(f"*_{week}.csv")),
    ]
    return [path for path in candidates if path.exists()]


def main() -> None:
    parser = argparse.ArgumentParser(description="Capture screenshots for radar evidence URLs.")
    parser.add_argument("--week", required=True, help="Week key, for example 2026-W24")
    parser.add_argument("--input", nargs="*", type=Path, help="CSV or Markdown files with URLs")
    parser.add_argument("--dry-run", action="store_true", help="Only write screenshot index, do not open browser")
    parser.add_argument("--max-targets", type=int, help="Capture or index only the first N targets")
    parser.add_argument("--timeout-ms", type=int, default=45000, help="Page navigation timeout")
    parser.add_argument("--wait-until", default="domcontentloaded", help="Playwright goto wait condition")
    args = parser.parse_args()

    input_paths = args.input or default_input_paths(args.week)
    if not input_paths:
        raise SystemExit(f"No input files found for {args.week}. Generate ranking/checklist files first.")

    targets = limit_targets(collect_targets(input_paths, week=args.week), args.max_targets)
    index_path = write_index(args.week, targets)
    print(f"Wrote {index_path}")
    print(f"Found {len(targets)} screenshot target(s)")

    if not args.dry_run:
        asyncio.run(capture_targets(targets, timeout_ms=args.timeout_ms, wait_until=args.wait_until))
        print(f"Captured screenshots under {ASSET_SCREENSHOT_DIR / args.week}")


if __name__ == "__main__":
    main()

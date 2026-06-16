# TikTok Lite Competitor Radar

Lightweight weekly radar for TikTok Lite creation and consumption PM work.

## What This Does

- Keeps a fixed competitor pool for creation and consumption tracking.
- Keeps an open radar for emerging social, content, creator-tool, repost/remix, AI creator, and consumption apps.
- Builds a strict candidate pool from multi-region news before PM review.
- Stores candidate signals in `data/signals.csv`.
- Generates Markdown, Codex-native, and Feishu JSON weekly reports from the signal table.

## Quick Start

```bash
python3 scripts/run_weekly_radar.py --week 2026-W25 --dry-run
```

The Markdown report will be written to `reports/weekly/<week>.md`.
The Feishu-ready JSON payload will be written to `reports/feishu/<week>.json`.

To run external collection, remove `--dry-run`:

```bash
python3 scripts/run_weekly_radar.py --week 2026-W25
```

To present the result directly in Codex with local screenshots:

```bash
python3 scripts/generate_codex_digest.py --week 2026-W25 --print
```

## Suggested Weekly Workflow

1. Run `scripts/run_weekly_radar.py --week <week>` to collect multi-region news candidates, generate Google Play discovery links, build the strict candidate pool, capture source screenshots, and generate reports.
2. Review `data/candidates/<week>.csv` for strict candidates that deserve PM promotion.
3. Promote only useful findings into `data/signals.csv`.
4. Run `scripts/run_weekly_radar.py --week <week> --dry-run` to regenerate Markdown and Feishu JSON from the curated signal table.
5. Run `scripts/generate_codex_digest.py --week <week> --print` when the report should be shown directly in Codex.

## News Candidate Collection

Collect news candidates from Google News RSS:

```bash
python3 scripts/collect_news_rss.py --week 2026-W24 --locale US --language en --limit-per-query 1
```

Queries live in `config/news_queries.json` and cover:

- Regular competitor updates, such as Snapchat, Facebook Reels, X video, Instagram Edits, YouTube Shorts, CapCut, TikTok Lite, Douyin, Xiaohongshu, and Kwai.
- Emerging product discovery, such as viral social apps, short video apps, creator apps, AI companion apps, AI video apps, friend camera apps, campus social apps, voice social apps, watermark removal tools, repost/remix tools, and creator workflow tools.

The raw output is written under `data/news_candidates/`. `scripts/build_candidate_pool.py` merges and filters those raw rows into `data/candidates/<week>.csv`. Treat the unified candidate pool as research input: review, classify, and promote only meaningful items into `data/signals.csv`.

## Feishu Payload

The one-command runner writes a Feishu-ready JSON payload:

```bash
python3 scripts/run_weekly_radar.py --week <week>
```

Expected output:

- `reports/weekly/<week>.md`: human-readable Markdown report
- `reports/feishu/<week>.json`: `{title, markdown, sources, screenshots}` payload for Feishu publishing

The Feishu JSON includes screenshot file paths. A publishing layer can upload those images to Feishu first if inline images are required, then replace local paths with Feishu image tokens or uploaded image URLs.

## App Store Ranking Importer

Fetch one storefront:

```bash
python3 scripts/collect_app_store_rankings.py --week 2026-W24 --storefront us --limit 25
```

Useful storefronts:

```bash
for market in us gb jp kr br mx id th vn ph my sa ae tr eg; do
  python3 scripts/collect_app_store_rankings.py --week 2026-W24 --storefront "$market" --limit 25
done
```

The importer writes raw ranking candidates under `data/rankings/`. Treat them as a discovery queue, not final PM judgement. Use `--append-signals` only when you want every fetched ranking item appended to `data/signals.csv` for manual triage.

## Google Play Discovery Checklist

Generate Android market/category links:

```bash
python3 scripts/collect_google_play_links.py --week 2026-W24
```

Generate a smaller custom checklist:

```bash
python3 scripts/collect_google_play_links.py --week 2026-W24 --markets us br id --categories SOCIAL VIDEO_PLAYERS
```

This script does not claim to produce official Google Play rankings. It creates a repeatable checklist for Android-first market review and screenshot capture. Use it to find candidates, then manually add only meaningful signals to `data/signals.csv`.

## Screenshot Capture

Create a screenshot index without opening a browser:

```bash
python3 scripts/capture_pages.py --week 2026-W24 --dry-run
```

Capture all URLs from the default weekly inputs:

```bash
python3 scripts/capture_pages.py --week 2026-W24
```

Capture only the first target for a quick check:

```bash
python3 scripts/capture_pages.py --week 2026-W24 --max-targets 1
```

Default inputs are:

- `data/google_play_checklists/<week>.md`
- `data/rankings/*_<week>.csv`

Screenshots are saved under `assets/screenshots/<week>/`, and the index is saved to `data/screenshots/<week>.csv`.

If Playwright is missing, install it:

```bash
python3 -m pip install playwright
python3 -m playwright install chromium
```

## Codex Direct Presentation

Generate a Codex-friendly digest:

```bash
python3 scripts/generate_codex_digest.py --week 2026-W24 --print
```

The digest uses absolute local image paths, so captured screenshots can render directly in Codex responses. This is the best output when you want the weekly radar presented in the thread instead of opening report files manually.

## Project Structure

```text
config/
  competitors.json
  markets.json
  sources.json
data/
  signals.csv
docs/
  radar-methodology.md
reports/
  weekly-report-template.md
  weekly/
scripts/
  generate_report.py
assets/
  screenshots/
```

## Verification

Before deploying or changing report logic:

```bash
python3 -m py_compile scripts/*.py
python3 -m unittest discover -s tests
```

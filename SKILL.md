---
name: tiktoklite-competitor-radar
description: Weekly competitor radar for TikTok Lite creation and consumption PM work, built as a 5-layer recommendation-style pipeline (recall → pre-rank → rank → watchpool → output). Collects multi-region news plus REAL App Store and Google Play category Top-Free charts; splits findings into a regular-competitor line and an emerging line; scores rather than kills at pre-rank; cross-verifies signals with A/B/C/D confidence; tracks emerging products in a cross-week watchpool; attaches GIF/video/screenshot demos to regular-competitor new features; and generates Markdown, Codex-native, and Feishu JSON weekly reports. USE WHEN the user asks to run a TikTok Lite competitor radar, build a weekly competitor/candidate report, collect competitor news or app rankings, or generate a Feishu/Codex weekly digest for short-video/social/creator-tool competitors.
---

# TikTok Lite Competitor Radar

Weekly radar for TikTok Lite creation and consumption PM work, modelled as a
recommendation-system funnel. Every knob lives in `config/radar_config.json`, so
tuning or rolling back any layer is a one-line change.

## Architecture — 5 Layers, 2 Lines

The pipeline is a funnel. Each layer narrows the set, and **only the rank layer
(L3) has authority to kill a real signal**. Earlier layers must not judge to
death — that is the lesson from the old keyword whitelist that silently dropped
real signals (e.g. Instagram "Multiple Captions").

| Layer | Name | Role | Script |
| --- | --- | --- | --- |
| L1 | 召回 recall | Cast wide; collect, never kill (only obvious garbage phrases) | `collect_news_*.py`, `collect_*_rankings.py` |
| L2 | 粗排 pre-rank | Organise + score (line split, form gate, priority). Only kills obvious garbage. | `build_candidate_pool.py` |
| L3 | 精排 rank | Agent deep research + A/B/C/D cross-verification. The only kill layer. | agent step → `data/signals.csv` |
| L4 | 观察池 watchpool | Cross-week tracking of emerging products | `update_watchpool.py` |
| L5 | 输出 output | Visual assets + citations + report render | `process_media.py`, `generate_report.py` |
| L6 | 分发 publish | Feishu group card preview + confirmed send | `lark-im` skill |

**Two lines, split by SOURCE (not by query list):**

- **常规竞品线 (regular line)** — a news item whose title names a FIXED competitor
  (from `config/competitors.json`).
- **新兴线 (emerging line)** — every other news item + ALL store-ranking entries.

## L1 — Recall (cast wide)

- Multi-region Google News RSS (`collect_news_multi.py`, default
  `--limit-per-query 3 --days 10`). Queries live in `config/news_queries.json`.
- REAL App Store + Google Play category Top-Free charts per country × genre.
  Google Play uses the Node `google-play-scraper` `list` API via
  `scripts/gp_chart.mjs` (real ranked chart, zero cost — catches hits the old
  webpage scrape missed, e.g. Setlog at KR Social #1).
- The recall gate (`collect_news_rss.is_relevant_news_item`) drops ONLY the
  explicit `IRRELEVANT_PHRASES` garbage list. There is no whitelist kill.

## L2 — Pre-rank (organise + score, do not judge to death)

`build_candidate_pool.py` writes `data/candidates/<week>.csv` with appended
columns `line`, `form`, `priority`. Rules (all from `radar_config.json`):

1. **Line split** by source (see above).
2. **Form 4-category gate** (news only): `creation` / `content` / `tool`;
   "两者皆有/both" = matching more than one. Any match passes. Store rankings skip
   the form gate (already scoped by category) and get ranking de-noise instead
   (drop dev/utility tools and mature incumbents).
3. **Commercialization filter** (monetization **and** incentive terms): on the
   **regular line** any hit ⇒ drop; on the **emerging line** ⇒ keep but annotate
   ("commercialization noted"). Incentives are excluded on the regular line too.
4. **Only-kill-obvious-garbage**: `hard_exclude_terms` drop on both lines.
   Everything else is kept as `review`; `priority` (high/low) only sets triage
   order. Pre-rank never silently kills a candidate worth a look.
5. `--legacy-filter` restores the old whitelist behaviour for a fast rollback.

## L3 — Rank (agent step; the ONLY kill layer)

Read `data/candidates/<week>.csv`, work the `review` rows (high priority first),
research each against official sources, and write fully-populated rows into
`data/signals.csv`. Apply per-SIGNAL (cluster all reports of one feature, score
the signal — not each article) cross-verification:

- **A** — official source confirms it (official blog/newsroom/exec post/in-product).
- **B** — no direct official confirmation, but ≥2 INDEPENDENT domains report it and
  all trace to the official source. Independence = dedup by domain,
  anti-transclusion, anti-same-source-rumor.
- **C** — single/unconfirmed. Regular line: **drop**. Emerging line: admit to the
  **watchpool** for early observation.
- **D** — same-source transcription / pure rumor / mutually copied. **Always drop.**

Acceptance: regular line keeps **A/B**; emerging line keeps **A/B/C**; **D** always
dropped. Record the grade in the `confidence` column.

Also apply **cross-period dedup**: if the same product + feature already shipped in
a prior week (`reports/weekly/*.md`), do not repeat it; note the dedup in the intro.

## L4 — Watchpool (emerging line only, cross-week)

`update_watchpool.py` carries state across weeks in `data/watchpool.csv`.
Members come from emerging-line ranking candidates (stable app identity). Heat =
breadth (markets charted in). Statuses: 新增 / 持续 / 降温 / 退池. Capacity 10
(weakest evicted when over); exit after `cold_weeks_to_exit` (2) cold weeks. The
per-week snapshot `data/watchpool_<week>.csv` feeds the report's 观察池动态 table.

## L5 — Output (visual assets + citations)

- **Regular-competitor new features get a visual demo** showing what the feature
  is and how it is used. Selection priority (agent finds it): official demo
  GIF/video → media hands-on GIF/video → in-product/media screenshot → static
  screenshot placeholder. **Dynamic-first is a hard gate**: if any usable demo
  GIF/video exists in the L3-visited pages, official/social embeds, or targeted
  re-search results, `media_type` MUST be `gif` or `video`; a static screenshot
  cannot pass just because it was found first. Static media is allowed only after
  recording that no demo GIF/video was found. **Reuse-first**: prefer a page
  already visited in L3; only re-search when none found. No in-product screen
  recording unless the user asks (`allow_in_product_recording` is false).
- Use `process_media.py compress` to fit GIFs into the budget
  (`gif_max_bytes` 10MB, `gif_max_chars` 14M; downscale 540px / frame-step 3 /
  128 colors, auto-tightened). `process_media.py check` validates budgets, and
  `process_media.py validate-signals` is mandatory before report render: it
  rejects static media when a dynamic demo is marked available, verifies GIFs are
  truly animated, and prevents Feishu/JSON output from downgrading GIF/video to a
  generic screenshot.
- **Citation**: primary = official source; never an aggregator/entertainment site
  as primary. Fill `cite_primary` and pipe-separated `cite_secondary`.
- `data/signals.csv` carries the new backward-compatible columns: `line`, `form`,
  `confidence`, `media_path`, `media_type`, `cite_primary`, `cite_secondary`.

## L6 — Publish (Feishu document + Lark rich-text post, confirm before send)

After the Feishu document is generated and L5 media placement is verified, prepare
an IM distribution message, but **never send it directly**. The agent must use the
`lark-im` skill for the actual message send and must require explicit user
confirmation before sending.

Confirmation must include all of the following, shown to the user in one preview:

1. **Message type**: Lark rich-text post single message.
2. **Target**: group name and group/chat ID suffix.
3. **Message style**: title, media order, top findings, CTA/report link, and any
   visual emphasis.
4. **Full message content**: the exact text/media mapping to be sent, including the
   Feishu document URL and summary bullets.

Only send after the user explicitly replies with `发送`, `确认`, or `yes`. If the
target group or style is ambiguous, stop and ask for those details. 宁可不发，不可发错.

Validated weekly publish style:

- Format: **rich-text post single message**, not raw interactive card JSON.
- Content order: title → `本周重点` → GIF/demo 1 + finding 1 → GIF/demo 2 +
  finding 2 → GIF/demo 3 + finding 3 → full Feishu report link.
- Media: use the same L5-validated GIF/video assets when available. Do not replace
  an available GIF with a static key frame for the group summary unless the user
  explicitly accepts a static fallback.
- Avoid raw interactive card multi-GIF delivery: GIF `img_key` values can fail card
  validation in this route.
- Avoid Mira `<card>` markdown as a GIF substitute: it can render image positions as
  icon placeholders rather than actual animated media.
- Separate GIF image messages are allowed only as a fallback/debugging path because
  they preserve animation but fragment the reading experience.
- CTA: `查看完整报告（含来源截图）` → generated Feishu document URL.
- Footer/status: `L5 media checked: GIF/video first; static only when fallback recorded`.

### Detail requirement (research-backed)

Every signal must be self-explanatory to a reader who has never seen it:

- `product_overview` — REQUIRED for emerging products (what it is / features /
  how to use + traction). Rendered as "产品详解（是什么 / 功能 / 怎么用）".
- `feature_detail` — REQUIRED for regular competitors (what the feature does and
  how it works, from web + official sources). Rendered as "功能详解".

Use `\n` inside a field for multiple paragraphs.

## Quick Start

Run from the skill directory. `--dry-run` regenerates reports from the curated
signal table without external collection:

```bash
python3 scripts/run_weekly_radar.py --week 2026-W26 --dry-run
```

Full collection (L1→L2→L4 + screenshots, then render):

```bash
python3 scripts/run_weekly_radar.py --week 2026-W26
```

Then perform the L3 agent curation into `data/signals.csv`, re-run with
`--dry-run`, and present:

```bash
python3 scripts/generate_codex_digest.py --week 2026-W26 --print
```

## Key Scripts

- `scripts/run_weekly_radar.py` — one-command runner (L1→L2→L4 + screenshots + render).
- `scripts/collect_news_rss.py` / `collect_news_multi.py` — L1 news recall.
- `scripts/collect_app_store_categories.py` / `collect_google_play_rankings.py`
  (+ `gp_chart.mjs`) — L1 real category charts.
- `scripts/build_candidate_pool.py` — L2 pre-rank (`--legacy-filter` to roll back).
- `scripts/update_watchpool.py` — L4 watchpool update.
- `scripts/process_media.py` — L5 GIF compression + budget check.
- `scripts/generate_report.py` / `generate_codex_digest.py` — L5 render.
- `lark-im` skill — L6 Feishu group card send after target, content, and card style confirmation.

## Outputs

- `reports/weekly/<week>.md` — Markdown report (incl. 观察池动态 table).
- `reports/feishu/<week>.json` — `{title, markdown, sources, screenshots}` payload.
- `data/candidates/<week>.csv` — pre-ranked pool; `data/watchpool.csv` — pool state.
- Screenshots under `assets/screenshots/<week>/`, index `data/screenshots/<week>.csv`.

## Config & Rollback

All knobs are in `config/radar_config.json` (form taxonomy, commercialization
terms, hard-exclude list, priority weights, confidence model, watchpool capacity,
media budget, source priority). A full pre-change snapshot lives in
`~/files/radar-backups/`. To revert the pre-rank to old behaviour, pass
`--legacy-filter` to `build_candidate_pool.py`.

## Verification

```bash
python3 -m py_compile scripts/*.py
python3 -m unittest discover -s tests
```

See `docs/radar-methodology.md` for the full methodology.

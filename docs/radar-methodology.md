# TikTok Lite Competitor Radar Methodology

## Goal

Build a weekly monitoring system for TikTok Lite PM work across creation and consumption. The radar should track fixed competitors and discover emerging apps or categories that may change user behavior.

## Definition: Creation

Creation covers the path from intent to produce content through publication and creator feedback.

Typical surfaces:
- Camera, upload, editing, templates, effects, filters, stickers
- AI video, image-to-video, subtitles, voiceover, avatar, digital human
- Music, sounds, trending materials, challenges, topics
- Drafts, ideas, project management
- Publishing settings, cover, title, tags, privacy
- Creator analytics, monetization, interaction management

Core question: does this reduce the effort or raise the quality of user-generated content?

## Definition: Consumption

Consumption covers the path from opening the app to discovering, watching, interacting, staying, and returning.

Typical surfaces:
- For You feed, following feed, friend feed, search, trends, channels
- Playback, weak network performance, data saving, offline viewing
- Likes, comments, saves, shares, reposts, reactions
- Social graph, messages, groups, co-watching
- Retention mechanics: check-ins, rewards, notifications, streaks
- Content formats: short video, image-text posts, live, games

Core question: does this win user attention or create a new viewing habit?

## Report Structure

The weekly report has six sections / delivery steps:

1. Top Findings: the 3-5 most important discoveries from the week.
2. Regular competitor research: fixed competitors and mature platforms, split into creation-related and consumption-related updates.
3. Emerging products: specific new or fast-rising apps/products. Do not force split this section by creation and consumption.
4. Optional screenshots: only when visual proof is useful and not already shown in a finding card.
5. TikTok Lite recommendations: concise PM judgement for regular competitors and emerging products.
6. Feishu group distribution: send a card only after confirming target group, complete content, and card style.

## Emerging Radar Rule

The emerging product section must not be locked to a fixed app list. It should detect abnormal signals from app stores, news, social media, and internal data platforms.

Each emerging item must be a specific app/product, not only an abstract category. The report can explain the category or mechanism after naming the app.

A signal can enter the weekly report if it meets at least two of these criteria:
- Ranking spike in a country, category, or demographic
- Visible social buzz, news coverage, KOL adoption, or template-style spread
- New creation or consumption behavior, not just a visual reskin
- Clear audience cluster such as Gen Z, students, K-pop fans, anime users, or AI companion users
- Migration potential for TikTok Lite creation, consumption, retention, or sharing
- Market relevance for Southeast Asia, Latin America, South Asia, Middle East, Japan, Korea, Europe, or North America

Include products that affect content behavior even when they are not direct social feeds, such as watermark removal, repost, remix, download, template, AI creator, friend-camera, campus/community, and creator workflow tools.

### Store Ranking Auto-Ingestion

Each week the radar pulls App Store and Google Play **category Top-Free
rankings** (per country × genre) and feeds them straight into the candidate
pool, so emerging products that have not yet attracted press coverage are still
caught:

- App Store genres: Social Networking, Photo & Video, Entertainment.
- Google Play categories: SOCIAL, VIDEO_PLAYERS, PHOTOGRAPHY, ENTERTAINMENT.
- Default markets: us, gb, jp, kr, br, mx, id, th, vn, ph (Top 10 each).
- TikTok / TikTok Lite live under **Entertainment** (App Store) and **Social**
  (Google Play), so the entertainment/social genres are required to see them.

`build_candidate_pool.py` classifies ranking entries automatically:
- Drops developer/utility tools (IDE, SSH/VPN, code editor, store-connect, etc.).
- Drops mature incumbents and existing fixed competitors (TikTok, Instagram,
  YouTube, Netflix, WhatsApp, …) loaded from `config/competitors.json`.
- Collapses the same app across markets into one row; the **number of markets**
  it ranks in is the breadth signal (an app on 9–10 charts is a stronger lead
  than a single-market entry).
- Everything else lands as `status=review` for PM triage.

Exclude signals outside the PM scope:
- Creator monetization, tipping, paid subscriptions, ad revenue share
- E-commerce, affiliate, account trading, creator task marketplace
- Sports betting, finance, pure shopping, pure productivity
- Pure short-drama content apps
- Celebrity/personality viral news, political viral videos, scams, and non-product viral events

## Priority Rubric

High:
- Large ranking spike or visible cross-platform spread
- Clear creation or consumption behavior shift
- High relevance to TikTok Lite markets or product surfaces
- Worth a deep dive within one week

Medium:
- Early traction or strong qualitative signal
- Product mechanic is relevant but market fit is still uncertain
- Worth observing for 2-3 weeks

Low:
- Interesting but weak evidence
- Limited market relevance
- Mention in appendix or backlog only

## Weekly PM Judgement Template

Use this structure for each important signal:

- What happened: concise product/factual signal
- Module: regular competitor creation, regular competitor consumption, or emerging product
- Region: where it happened
- Source: source link, chart link, app store page, news article, version note, or social post
- Optional screenshot: use only when ranking position, UI change, or feature entry needs visual proof
- L5 demo media: for regular-competitor new features, use a demo GIF/video first whenever one exists; static screenshots are fallback only after confirming no dynamic demo was found
- Why it matters: what user behavior it points to
- TikTok Lite implication: what we should learn, monitor, or test
- Priority: high, medium, or low

## Mandatory Detail Research (web search + official sources)

Every signal must carry enough context that a reader who has never seen the
product or feature still understands it. Two CSV fields back this requirement:

- `product_overview` — REQUIRED for emerging products. Explain, in plain
  language: what the product is, what its core features are, and how a user
  actually uses it (the typical flow). Add traction context (rankings, user
  counts, who is driving the spread) when available. Emerging cards render this
  as "产品详解（是什么 / 功能 / 怎么用）" right after "发生了什么".
- `feature_detail` — REQUIRED for regular competitors. Do not just name the
  feature. Use web search and official sources (product blog, help center,
  release notes, reputable tech press) to explain what the feature actually
  does, how it works, and any published metrics. Regular-competitor cards render
  this as "功能详解" right after "发生了什么".

Rules:
- Always research before writing. Never paraphrase a headline as the only
  description. Pull concrete mechanics from at least one primary/official source
  plus one corroborating source where possible.
- Emerging products lead with `product_overview`; regular competitors lead with
  `feature_detail`. The other field is optional and shown second if filled.
- Keep the detail factual and sourced; speculation belongs in "为什么重要" and
  "对 TikTok Lite 的启发", not in the detail fields.
- Use `\n`-separated lines inside a field to render multiple paragraphs (e.g.
  是什么 / 核心功能 / 怎么用 / 热度).

Before group distribution, prepare a Feishu group card preview and require explicit confirmation of the target group, exact content, and card style. The preview must include message type, group name and group/chat ID, hero image or GIF/video key-frame choice, title, subtitle/tag, button text/link, section order, summary bullets, and footer/status text. The default card style is a large-image interactive card: a hero image at the top, up to three numbered top findings, a `查看完整报告（含来源截图）` CTA button, and an L5 media status footer. If the hero source is a GIF/video, extract a representative key frame for the card if animation is not supported, while keeping the full GIF/video in the Feishu document. Send via `lark-im` only after the user replies `发送`, `确认`, or `yes`; if the target or style is ambiguous, stop instead of sending.

## L5 Media Gate: dynamic demo first

Regular-competitor new features must show the feature in use, not merely prove
that an article exists. The media priority is fixed:

1. official demo GIF/video;
2. media hands-on GIF/video;
3. in-product or media screenshot;
4. static screenshot placeholder.

If a usable demo GIF/video exists in an official source, a social embed, a page
visited during L3 verification, or a targeted media re-search, the signal must
ship with `media_type=gif` or `media_type=video`. A PNG/JPG/`screenshot` asset is
not acceptable just because it was easier to fetch first. Static media can pass
only after the curator records that no dynamic demo was found. Before rendering,
run `python3 scripts/process_media.py validate-signals --signals data/signals.csv`;
this checks that dynamic-demo-available rows do not use static assets, GIF files
are actually animated, and Feishu JSON keeps the media `type` instead of reducing
everything to a generic screenshot.

## Signal Table Schema

`data/signals.csv` columns:

`week,date,app,region,module,track,radar_type,category,signal,feature_detail,product_overview,why_it_matters,tiktok_lite_implication,priority,source_url,screenshot_path,status,line,form,confidence,media_path,media_type,cite_primary,cite_secondary`

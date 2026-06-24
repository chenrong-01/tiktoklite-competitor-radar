---
name: tiktoklite-feedback-mining
description: Use when a TikTok Lite PM asks to collect, summarize, or analyze user feedback, reviews, complaints, user voice, feature-related asks, creation/posting/consumption experience issues, competitor short-video app feedback, or entertainment app pain points for TikTok Lite product work.
---

# TikTok Lite Feedback Mining

## Overview

Use this skill to produce evidence-backed user voice summaries for TikTok Lite PM work. The skill collects and clusters feedback, preserves user quotes and source links, and extracts function-related user asks without making product priority decisions.

## Core Rules

- Do not output roadmap decisions, priority rankings, or recommendations unless the user explicitly asks.
- Do not turn every complaint into a suggested feature. Phrase functional output as "users are asking for / implying / struggling with".
- Keep TikTok Lite own-product feedback broad. Include performance, data, login, rewards, ads, safety, content, creation, posting, consumption, support, and market-specific issues.
- Keep competitor and wider web mining focused on creation, posting/publishing, and content consumption experience.
- Preserve source evidence. Every meaningful theme needs user quotes or close paraphrases plus links, platform, market when available, and date/time window when available.
- Separate structured review sources from non-structured community sources. Do not use keyword search when a source can be directly collected by app id/package and time window.
- Mark sample limitations clearly. Do not generalize a single market, platform, subreddit, or article as global evidence.

## Default Scope

Default product:

- TikTok Lite

Default own-product sources:

- Google Play reviews by package id and market
- App Store reviews only in markets where TikTok Lite is confirmed available
- Reddit posts/comments about TikTok Lite
- News/regulatory reports only as context, not as user voice unless they quote users

Default competitor/category sources:

- TikTok, Douyin/Douyin Lite, Kwai/Kuaishou, Likee, SnackVideo
- YouTube Shorts, Instagram Reels, Facebook Reels, Snapchat Spotlight
- CapCut/Jianying and lightweight creator tools when creation workflows are in scope
- Product Hunt or similar product-review pages for emerging creator/short-video tools

## Workflow

1. Clarify the run only if required information is missing. Prefer defaults: last 7 days, key TikTok Lite markets, Chinese output, and all three chains: creation, posting, consumption.
2. Collect structured TikTok Lite reviews directly by app id/package, market, platform, and time window. Do not search for these if direct collection is available.
3. Cluster TikTok Lite own-product feedback broadly by product module and user journey.
4. Find high-density feedback fields for competitor/category mining, then sample comments/posts from those fields. Do not rely on random keyword hits as evidence.
5. Cluster competitor/category feedback only under creation, posting/publishing, and consumption.
6. Extract function-related asks from user language. Use neutral wording and attach quotes.
7. Produce the report with sample counts, source coverage, themes, user voice, functional asks, and limitations.

## Data Source Playbooks

Read `references/source-playbooks.md` when planning or running collection. It defines how to handle:

- Structured app review sources
- Reddit, YouTube, X, Product Hunt, Chinese communities, and news comments
- Reddit Answers as optional enhancement only
- Required source metadata

## Output Format

Use this report structure by default.

### 1. Sample And Source Coverage

Include:

- Time window
- Markets/languages
- Platforms and sample counts
- Collection method: direct review collection, API, search discovery, manual link, or sampled community field
- Major gaps and limitations

### 2. TikTok Lite Own-Product Feedback Overview

Summarize all TikTok Lite themes, not only creation/posting/consumption. Use a compact table:

| Theme | Feedback Summary | User Voice | Source |
|---|---|---|---|

Themes may include performance, data usage, storage, login, rewards, withdrawal, ads, content quality, safety controls, creation, posting, consumption, support, and market availability.

### 3. TikTok Lite Theme Clusters With User Voice

For each important theme:

```text
Theme:
Feedback summary:
User voice:
- "..."
- "..."
Sources:
- Platform, market, date, link
Functional ask expressed or implied:
- Users want/expect/struggle to...
```

### 4. Creation Chain Feedback

Use only own-product, competitor, or category evidence related to:

- Inspiration and deciding what to create
- Camera, recording, editing, templates, effects, filters
- Music/sounds, captions, subtitles, stickers
- AI-assisted creation and lightweight creator workflows

### 5. Posting And Publishing Chain Feedback

Use evidence related to:

- Upload failures, processing, under review, moderation, takedowns
- 0 views, low reach, suspected shadowban, distribution uncertainty
- Covers, titles, hashtags, music availability, publish settings
- Account bans, appeals, support tickets, rule transparency

### 6. Consumption Chain Feedback

Use evidence related to:

- Recommendation quality, repetitive content, interest control
- Ads, shopping/commercial content, content density
- Weak network, playback, data/battery, crashes
- Comments, interaction, toxicity, saves/shares
- Addiction/time control, safety filters, restricted mode

### 7. Function-Related User Asks

List only what users ask for or imply, with evidence. Avoid PM judgment language.

| User Ask | Related Chain | Evidence/User Voice | Source |
|---|---|---|---|

Good phrasing:

- "Users want to understand why a post has 0 views."
- "Users expect feedback controls to reduce shopping videos after they choose not interested."
- "Users want key sounds/music to remain available or be explained when unavailable."

Avoid:

- "Build a better recommendation control feature."
- "High priority."
- "We should launch..."

### 8. User Voice Index

List representative quotes and links by source. Keep quotes short; paraphrase longer content.

### 9. Limitations

State what was not covered, such as missing API credentials, unavailable market reviews, sampled-only community data, login walls, or unverified Reddit Answers.

## Quality Bar

Before presenting a finished report:

- Verify links open or clearly mark any inaccessible source.
- Distinguish user voice from journalist/regulator/company claims.
- Label App Store and Google Play evidence with market and platform.
- For non-structured sources, state that findings are sampled.
- If a theme lacks user quotes or links, mark it as a weak signal or remove it.

# Source Playbooks

## Source Types

### Structured Review Sources

Use direct collection instead of web search.

Sources:

- Google Play reviews
- App Store reviews when TikTok Lite exists in the target market
- Product Hunt product comments when a product page is known

Required metadata:

- Product/app name
- Package id or app id when available
- Platform
- Market/country
- Language
- Date/time window
- Rating if available
- Review text or quote
- Source URL or collection artifact path

Default handling:

1. Collect recent reviews for the requested time window, usually 7 or 30 days.
2. Keep all ratings unless the user asks to focus on negative reviews.
3. Tag by market, language, rating, and platform.
4. Cluster by product module and user journey.
5. Quote representative reviews, not only summaries.

Do not infer global conclusions from one market. For example, an App Store South Africa review only represents App Store ZA evidence.

### Non-Structured Community Sources

Use source-first mining:

1. Find high-density feedback fields.
2. Check field quality.
3. Sample comments/posts.
4. Cluster user voice.
5. Preserve links and sample limitations.

Do not treat a search result snippet as sufficient evidence unless the source cannot be opened and the limitation is stated.

## High-Density Feedback Fields

### Reddit

Good fields:

- Product-specific posts in TikTok, TikTokHelp, TikTokLounge, socialmedia, NewTubers, Instagram, YouTube, CapCut, or market-specific communities
- Problem posts with many replies
- Complaint threads, help threads, uninstall/replacement discussions

Use Reddit Answers only as optional discovery. If the user provides a Reddit Answers result page, read the AI summary and its cited posts/comments, then verify cited sources. Do not require Reddit Answers for a run.

### YouTube Comments

Good fields:

- "fix" videos: 0 views, under review, upload failed, shadowban, FYP problems
- Tutorials: editing, captions, templates, sounds/music, CapCut workflows
- Reviews/comparisons: TikTok Lite vs TikTok, Shorts vs TikTok, Reels vs TikTok

Without YouTube Data API credentials, use YouTube as search discovery or manual-page sampling only. With API credentials, collect comments by video id and include video metadata.

### X

Without X API credentials, treat X as weak search discovery. Direct X pages are often login-gated, rate-limited, or dynamically unavailable.

With API credentials, collect matching posts for the time window and preserve post URLs, author metadata when available, timestamps, and engagement counts.

### Product Hunt And Tool Review Sites

Use for category and workflow signals, especially:

- AI video tools
- Caption/subtitle tools
- Template tools
- Social publishing tools
- Creator workflow products

Treat these as category signals, not TikTok Lite own-product evidence.

### Chinese Communities

Possible sources:

- Zhihu questions and answers
- Bilibili videos and comments
- Xiaohongshu notes and comments
- Weibo posts and topics

Use these as sampled evidence unless a reliable export/API is available. Preserve the original Chinese user voice where possible and summarize in Chinese.

### News And News Comments

Use news articles for context, regulatory background, product changes, and public discourse. Only count news as user voice when it includes user comments or user quotes.

News comments are optional because comment systems are often login-gated, paywalled, or dynamically rendered.

## Journey Tags

Use these tags consistently.

TikTok Lite own-product broad tags:

- performance
- data-battery-storage
- login-account
- rewards-withdrawal
- ads-commerce
- recommendation-content
- safety-control
- creation
- posting-publishing
- consumption
- interaction-community
- support-appeal
- market-availability

Competitor/category chain tags:

- creation
- posting-publishing
- consumption

## Functional Ask Extraction

Extract only from user language. Use neutral phrasing:

- "Users want to..."
- "Users expect..."
- "Users are confused about..."
- "Users struggle to..."
- "Users try to work around..."

Common examples:

- Users want to know why a post has 0 views.
- Users want upload/review status to be understandable.
- Users expect "not interested" to reduce similar ads or shopping videos.
- Users want sounds/music availability to be clear.
- Users want faster captions or less editing effort.

Do not add priority, business impact, roadmap decision, or implementation recommendation unless explicitly requested.

## Report Evidence Standards

Strong evidence:

- Direct app reviews with market, date, rating, and text
- Multiple community comments across more than one high-density field
- API-collected comment samples with timestamps

Medium evidence:

- One high-quality thread with multiple users agreeing
- Product review pages with several relevant comments
- News articles quoting users

Weak evidence:

- One isolated post
- Search result snippets
- News/regulatory claims without user voice
- Reddit Answers summary without cited-source verification

Remove or mark weak signals rather than presenting them as established themes.

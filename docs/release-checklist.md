# Weekly Release Checklist

Use this checklist before publishing a weekly TikTok Lite competitor radar.

## Collection

- [ ] Run the weekly radar collection for the target week.
- [ ] Confirm news candidates were generated.
- [ ] Confirm App Store category rankings were generated.
- [ ] Confirm Google Play category rankings were generated.
- [ ] Confirm the candidate pool exists at `data/candidates/<week>.csv`.

## Curation

- [ ] Review high-priority candidate rows first.
- [ ] Keep only creation/consumption signals.
- [ ] Exclude commercial, monetization, ads, shopping, payment, and subscription signals.
- [ ] Check prior reports for product + feature duplicates.
- [ ] Fill `feature_detail` for regular competitors.
- [ ] Fill `product_overview` for emerging products.
- [ ] Update `data/signals.csv`.
- [ ] Update the watchpool.

## Media gate

- [ ] For each regular-competitor feature, search for official or media demo GIF/video first.
- [ ] Use static fallback only after recording that no usable dynamic demo was found.
- [ ] Compress oversized GIFs.
- [ ] Run media validation before rendering the final report.

## Report and Feishu document

- [ ] Regenerate the Markdown weekly report.
- [ ] Regenerate the Feishu-ready JSON payload.
- [ ] Create or update the Feishu document through the document integration.
- [ ] Verify the Feishu document contains the expected media placement.
- [ ] Save the final Feishu document URL for Lark publishing.

## Lark publishing

- [ ] Prepare the rich-text post single-message summary.
- [ ] Include top GIF-backed signals and one-line explanations.
- [ ] Include the full Feishu report link.
- [ ] Send a private preview when the template or media handling changed.
- [ ] Show the group target, content, and style to the user.
- [ ] Send only after explicit confirmation.
- [ ] Record the sent message ID outside git if needed.

## Repository hygiene

- [ ] Do not commit generated reports unless sanitized as examples.
- [ ] Do not commit screenshots or media unless sanitized as examples.
- [ ] Do not commit tokens, chat IDs, open IDs, message IDs, or private document URLs.
- [ ] Run tests before opening the PR.

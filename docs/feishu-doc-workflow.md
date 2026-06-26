# Feishu Doc Workflow

This radar treats the Feishu document as the full weekly report artifact.

## Role in the L1-L6 workflow

- L1-L4 decide what is worth reporting.
- L5 renders the weekly report and produces a Feishu-ready payload.
- L6 publishes a short group-message summary that links back to the full Feishu document.

The radar repository owns the report content, media metadata, and payload shape. It does not vendor the Feishu/Lark document tool implementation or store credentials.

## Generated artifacts

The weekly runner writes:

- `reports/weekly/<week>.md` — Markdown report for review and archival use.
- `reports/feishu/<week>.json` — Feishu-ready payload with title, markdown body, sources, and screenshot/media metadata.

Generated reports and screenshots are runtime artifacts and should not be committed unless they are explicitly sanitized examples.

## Media requirements

Regular-competitor feature signals should use dynamic demos whenever possible:

1. Official demo GIF/video.
2. Media hands-on GIF/video.
3. In-product/media screenshot.
4. Static fallback only after no usable dynamic demo was found.

Before creating a Feishu document, run the media validation checks so the Feishu payload does not downgrade a GIF/video-backed feature to a generic static screenshot.

## Integration boundary

Use the existing Feishu/Lark document capability in the execution environment to create or update the actual document. This repo should only contain:

- report generation logic;
- Feishu-ready payload examples;
- workflow documentation;
- safe integration scripts if needed.

Do not commit tokens, document tokens, internal document URLs, image tokens, chat IDs, message IDs, or raw private outputs.

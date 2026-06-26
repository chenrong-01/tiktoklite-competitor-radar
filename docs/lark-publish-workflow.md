# Lark Publish Workflow

L6 is the distribution layer for the weekly radar. It is intentionally confirm-before-send.

## Publishing principle

The Feishu document is the full report. The Lark group message is the concise entry point: top signals, dynamic media, and a link to the full report.

Never silently send a group message. Before sending, show the user:

1. message type;
2. target group name and chat ID suffix;
3. full content;
4. visual/message style;
5. full report link.

Only send after the user explicitly replies with `yes`, `确认`, or `发送`.

## Validated message format

For multi-GIF weekly radar delivery, prefer a **rich-text post single message**:

```text
Title: TikTok Lite Competitor Radar · <date range>

本周重点

[GIF 1]
1. <feature title>
<one-line explanation>

[GIF 2]
2. <feature title>
<one-line explanation>

[GIF 3]
3. <feature title>
<one-line explanation>

查看完整报告（含来源截图）
```

This keeps the weekly summary in one message while preserving the mapping between each signal and its dynamic demo.

## Formats tested and rejected

### Raw interactive card with GIF images

Static images can work, but GIF `img_key` values may fail card validation. Do not rely on raw interactive card JSON for multi-GIF weekly delivery.

### Mira `<card>` markdown

This can resemble a card, but image positions may render as icon placeholders instead of actual animated media. Do not use icon placeholders as a substitute for GIFs.

### Separate GIF messages

Separate GIF image messages preserve animation, but the result is fragmented and less readable in a group chat. Use this only as a fallback or debugging test.

## Safety checklist

- [ ] Feishu document has been generated.
- [ ] L5 media validation passed.
- [ ] Dynamic demos are used where available.
- [ ] Static fallback is recorded only when no usable dynamic demo exists.
- [ ] Private preview was checked when changing layout or media handling.
- [ ] Target group and content were confirmed by the user.
- [ ] No credentials, chat IDs, open IDs, message IDs, or private document tokens are committed.

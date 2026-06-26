#!/usr/bin/env python3
"""Generate a TikTok Lite competitor radar weekly report from CSV signals."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_PATH = ROOT / "data" / "signals.csv"
OUTPUT_DIR = ROOT / "reports" / "weekly"

MODULE_TITLES = {
    "fixed_creation": "常规竞品 · 创作",
    "fixed_consumption": "常规竞品 · 消费",
    "emerging_creation": "新兴产品",
    "emerging_consumption": "新兴产品",
}

PRIORITY_TITLES = {
    "high": "高优先级",
    "medium": "中优先级",
    "low": "低优先级",
}

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class Signal:
    week: str
    date: str
    app: str
    region: str
    module: str
    track: str
    radar_type: str
    category: str
    signal: str
    feature_detail: str
    product_overview: str
    why_it_matters: str
    tiktok_lite_implication: str
    priority: str
    source_url: str
    screenshot_path: str
    status: str
    # L5 additions (backward-compatible: default to "" when absent in old CSVs).
    line: str = ""
    form: str = ""
    confidence: str = ""
    media_path: str = ""
    media_type: str = ""
    cite_primary: str = ""
    cite_secondary: str = ""

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "Signal":
        return cls(**{field: row.get(field, "").strip() for field in cls.__dataclass_fields__})


def load_signals(path: Path, week: str) -> list[Signal]:
    if not path.exists():
        raise FileNotFoundError(f"Signals file not found: {path}")

    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [Signal.from_row(row) for row in reader if row.get("week", "").strip() == week]


def sort_signals(signals: list[Signal]) -> list[Signal]:
    return sorted(
        signals,
        key=lambda item: (
            PRIORITY_ORDER.get(item.priority.lower(), 99),
            item.module,
            item.app.lower(),
            item.region.lower(),
        ),
    )


def media_markdown(signal: Signal) -> str | None:
    """Inline visual asset for a signal, placed inside its own product block.

    Prefers an L5-captured media asset (GIF/video/screenshot via media_path);
    falls back to the legacy screenshot_path. A video media_type is rendered as a
    link (markdown cannot inline video), everything else as an image. A publishing
    layer replaces the local path with an uploaded token while keeping position.
    """
    path = signal.media_path or signal.screenshot_path
    if not path:
        return None
    label = f"{signal.app} · {signal.region}".strip(" ·")
    if signal.media_type == "video":
        return f"[▶ {label} — demo video]({path})"
    return f"![{label}]({path})"


def citation_markdown(signal: Signal) -> str:
    """Primary = official source; secondary fills detail. Never aggregator first."""
    primary = signal.cite_primary or signal.source_url
    parts = []
    if primary:
        parts.append(f"[primary]({primary})")
    if signal.cite_secondary:
        for url in signal.cite_secondary.split("|"):
            url = url.strip()
            if url:
                parts.append(f"[ref]({url})")
    return " · ".join(parts) if parts else "source missing"


def render_signal(signal: Signal) -> str:
    source = citation_markdown(signal)
    priority = PRIORITY_TITLES.get(signal.priority.lower(), signal.priority)
    tags = [f"`{MODULE_TITLES.get(signal.module, signal.module)}`", f"`{signal.category}`", f"`{priority}`"]
    if signal.confidence:
        tags.append(f"`置信度 {signal.confidence}`")
    lines = [
        f"### {signal.app} · {signal.region}",
        "",
        " · ".join(tags),
        "",
        f"**发生了什么**  ",
        signal.signal,
        "",
    ]
    # Emerging products lead with a product walkthrough so readers who have never
    # seen the app understand what it is, what it does, and how it is used.
    # Regular competitors lead with a web-researched feature explainer.
    is_emerging = signal.radar_type == "emerging"
    detail_blocks = []
    if is_emerging:
        if signal.product_overview:
            detail_blocks.append(("产品详解（是什么 / 功能 / 怎么用）", signal.product_overview))
        if signal.feature_detail:
            detail_blocks.append(("功能详解", signal.feature_detail))
    else:
        if signal.feature_detail:
            detail_blocks.append(("功能详解", signal.feature_detail))
        if signal.product_overview:
            detail_blocks.append(("产品详解（是什么 / 功能 / 怎么用）", signal.product_overview))
    for label, text in detail_blocks:
        lines.append(f"**{label}**  ")
        lines.extend(_multiline(text))
        lines.append("")
    lines.extend(
        [
            f"**为什么重要**  ",
            signal.why_it_matters,
            "",
            f"**对 TikTok Lite 的启发**  ",
            signal.tiktok_lite_implication,
            "",
            f"**来源**  ",
            source,
            "",
        ]
    )
    media = media_markdown(signal)
    if media:
        lines.extend([media, ""])
    return "\n".join(lines)


def _multiline(text: str) -> list[str]:
    """Render a multi-paragraph detail field as separate markdown lines."""
    parts = [part.strip() for part in text.split("\n") if part.strip()]
    return parts if parts else [text]


def render_signal_group(title: str, signals: list[Signal]) -> list[str]:
    lines = [f"### {title}", ""]
    if signals:
        lines.extend(render_signal(signal) for signal in signals)
    else:
        lines.extend(["本周暂无进入正式报告的发现。", ""])
    return lines


def signals_by_track(signals: list[Signal]) -> dict[str, list[Signal]]:
    grouped: dict[str, list[Signal]] = defaultdict(list)
    for signal in sort_signals(signals):
        grouped[signal.track].append(signal)
    return grouped


def load_watchpool_snapshot(week: str) -> list[dict[str, str]]:
    """Load the per-week watchpool snapshot written by update_watchpool.py (L4)."""
    path = ROOT / "data" / f"watchpool_{week}.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        return list(csv.DictReader(file))


def render_watchpool_section(week: str) -> list[str]:
    rows = load_watchpool_snapshot(week)
    if not rows:
        return []
    status_order = {"新增": 0, "持续": 1, "降温": 2, "退池": 3}
    rows = sorted(
        rows,
        key=lambda r: (status_order.get(r.get("status", ""), 9), -int(r.get("heat", "0") or 0)),
    )
    lines = ["## 观察池动态", ""]
    lines.append("| 产品 | 状态 | 在池周数 | 热度(市场数) | 覆盖市场 |")
    lines.append("| --- | --- | --- | --- | --- |")
    for r in rows:
        lines.append(
            f"| {r.get('app', '')} | {r.get('status', '')} | {r.get('weeks_in_pool', '')} "
            f"| {r.get('heat', '')} | {r.get('markets', '')} |"
        )
    lines.append("")
    return lines


def render_report(week: str, signals: list[Signal]) -> str:
    top_signals = sort_signals(signals)[:5]
    fixed_signals = [signal for signal in signals if signal.radar_type == "fixed"]
    emerging_signals = [signal for signal in signals if signal.radar_type == "emerging"]
    fixed_by_track = signals_by_track(fixed_signals)

    lines = [
        f"# TikTok Lite Weekly Radar · {week}",
        "",
        "## 本周重点结论",
        "",
    ]

    if top_signals:
        for signal in top_signals:
            lines.append(f"- **{signal.app}**：{signal.signal}")
        lines.append("")
    else:
        lines.extend(["本周暂无进入正式报告的发现。", ""])

    lines.extend(["## 常规竞品调研", ""])
    lines.extend(render_signal_group("常规竞品 · 创作相关", fixed_by_track.get("creation", [])))
    lines.extend(render_signal_group("常规竞品 · 消费相关", fixed_by_track.get("consumption", [])))

    lines.extend(["## 新兴产品", ""])
    if emerging_signals:
        lines.extend(render_signal(signal) for signal in sort_signals(emerging_signals))
    else:
        lines.extend(["本周暂无进入正式报告的发现。", ""])

    lines.extend(render_watchpool_section(week))

    lines.extend(
        [
            "## 对 TikTok Lite 的建议",
            "",
            "- **常规竞品**：优先拆解高优先级功能变化对应的创作/消费路径，判断是否会改变用户进入、创作、搜索或互动习惯。",
            "- **新兴产品**：连续观察 2-3 周，看是否出现跨地区报道、榜单上升或同类产品跟进，再判断是否需要单独深挖。",
        ]
    )

    return "\n".join(lines)


def write_report(week: str, content: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{week}.md"
    output_path.write_text(content, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a weekly TikTok Lite competitor radar report.")
    parser.add_argument("--week", required=True, help="ISO-like week key, for example 2026-W24")
    args = parser.parse_args()

    signals = load_signals(SIGNALS_PATH, args.week)
    report = render_report(args.week, signals)
    output_path = write_report(args.week, report)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

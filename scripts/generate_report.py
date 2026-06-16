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
    why_it_matters: str
    tiktok_lite_implication: str
    priority: str
    source_url: str
    screenshot_path: str
    status: str

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


def screenshot_line(signal: Signal) -> str:
    if not signal.screenshot_path:
        return "Screenshot: not attached"

    screenshot = ROOT / signal.screenshot_path
    if screenshot.exists():
        return f"Screenshot: ![{signal.app}]({signal.screenshot_path})"
    return f"Screenshot placeholder: `{signal.screenshot_path}`"


def render_signal(signal: Signal) -> str:
    source = f"[source]({signal.source_url})" if signal.source_url else "source missing"
    priority = PRIORITY_TITLES.get(signal.priority.lower(), signal.priority)
    lines = [
        f"### {signal.app} · {signal.region}",
        "",
        f"`{MODULE_TITLES.get(signal.module, signal.module)}` · `{signal.category}` · `{priority}`",
        "",
        f"**发生了什么**  ",
        signal.signal,
        "",
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
    if signal.screenshot_path:
        lines.extend([screenshot_line(signal).replace("Screenshot: ", ""), ""])
    return "\n".join(lines)


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

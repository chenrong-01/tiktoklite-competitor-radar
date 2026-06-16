#!/usr/bin/env python3
"""Generate a Codex-native visual digest with absolute local image paths."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SIGNALS_PATH = ROOT / "data" / "signals.csv"
OUTPUT_DIR = ROOT / "reports" / "codex"

MODULE_TITLES = {
    "fixed_creation": "常规竞品 · 创作",
    "fixed_consumption": "常规竞品 · 消费",
    "emerging_creation": "新兴产品",
    "emerging_consumption": "新兴产品",
}

TRACK_TITLES = {
    "creation": "创作相关",
    "consumption": "消费相关",
}

PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}
PRIORITY_TITLES = {"high": "高优先级", "medium": "中优先级", "low": "低优先级"}


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


@dataclass(frozen=True)
class ScreenshotEvidence:
    week: str
    source: str
    label: str
    url: str
    screenshot_path: str
    status: str

    @classmethod
    def from_row(cls, row: dict[str, str]) -> "ScreenshotEvidence":
        return cls(**{field: row.get(field, "").strip() for field in cls.__dataclass_fields__})


def load_signals(path: Path, week: str) -> list[Signal]:
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [Signal.from_row(row) for row in reader if row.get("week", "").strip() == week]


def load_screenshot_evidence(root: Path, week: str) -> list[ScreenshotEvidence]:
    path = root / "data" / "screenshots" / f"{week}.csv"
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        return [ScreenshotEvidence.from_row(row) for row in reader if row.get("week", "").strip() == week]


def sort_signals(signals: list[Signal]) -> list[Signal]:
    return sorted(
        signals,
        key=lambda signal: (
            PRIORITY_ORDER.get(signal.priority.lower(), 99),
            signal.module,
            signal.app.lower(),
            signal.region.lower(),
        ),
    )


def image_markdown(root: Path, screenshot_path: str, alt: str) -> str:
    if not screenshot_path:
        return ""
    absolute_path = root / screenshot_path
    if not absolute_path.exists():
        return ""
    return f"![{alt}]({absolute_path})"


def render_signal(root: Path, signal: Signal) -> str:
    source = f"[source]({signal.source_url})" if signal.source_url else "source missing"
    image = image_markdown(root, signal.screenshot_path, signal.app)
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
    if image:
        lines.extend([image, ""])
    return "\n".join(lines)


def render_signal_group(root: Path, title: str, signals: list[Signal]) -> list[str]:
    lines = [f"### {title}", ""]
    if signals:
        lines.extend(render_signal(root, signal) for signal in signals)
    else:
        lines.extend(["本周暂无进入正式报告的发现。", ""])
    return lines


def signals_by_track(signals: list[Signal]) -> dict[str, list[Signal]]:
    grouped: dict[str, list[Signal]] = defaultdict(list)
    for signal in sort_signals(signals):
        grouped[signal.track].append(signal)
    return grouped


def render_evidence_gallery(
    root: Path,
    evidence_items: list[ScreenshotEvidence],
    skipped_paths: set[str] | None = None,
) -> str:
    skipped_paths = skipped_paths or set()
    rendered = []
    for evidence in evidence_items:
        if evidence.screenshot_path in skipped_paths:
            continue
        image = image_markdown(root, evidence.screenshot_path, evidence.label)
        if not image:
            continue
        source = f"[source]({evidence.url})" if evidence.url else "source not attached"
        rendered.append(
            "\n".join(
                [
                    f"### {evidence.label}",
                    "",
                    f"`{evidence.source}` · `{evidence.status}`",
                    "",
                    image,
                    "",
                    f"证据来源：{source}",
                    "",
                ]
            )
        )
    return "\n".join(rendered)


def render_digest(root: Path, week: str, signals: list[Signal], evidence_items: list[ScreenshotEvidence]) -> str:
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
    lines.extend(render_signal_group(root, "常规竞品 · 创作相关", fixed_by_track.get("creation", [])))
    lines.extend(render_signal_group(root, "常规竞品 · 消费相关", fixed_by_track.get("consumption", [])))

    lines.extend(["## 新兴产品", ""])
    if emerging_signals:
        lines.extend(render_signal(root, signal) for signal in sort_signals(emerging_signals))
    else:
        lines.extend(["本周暂无进入正式报告的发现。", ""])

    inline_screenshot_paths = {signal.screenshot_path for signal in signals if signal.screenshot_path}
    gallery = render_evidence_gallery(root, evidence_items, inline_screenshot_paths)
    lines.extend(["## 附加截图", ""])
    if gallery:
        lines.append(gallery)
    else:
        lines.extend(["本周暂无附加截图；以上来源链接为主要证据。", ""])

    lines.extend(
        [
            "## 对 TikTok Lite 的建议",
            "",
            "- **常规竞品**：优先拆解高优先级功能变化对应的创作/消费路径，判断是否会改变用户进入、创作、搜索或互动习惯。",
            "- **新兴产品**：连续观察 2-3 周，看是否出现跨地区报道、榜单上升或同类产品跟进，再判断是否需要单独深挖。",
            "",
        ]
    )

    return "\n".join(lines)


def write_digest(week: str, content: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{week}.md"
    output_path.write_text(content, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate a Codex-native radar digest.")
    parser.add_argument("--week", required=True, help="Week key, for example 2026-W24")
    parser.add_argument("--print", action="store_true", help="Print digest markdown to stdout")
    args = parser.parse_args()

    signals = load_signals(SIGNALS_PATH, args.week)
    evidence_items = load_screenshot_evidence(ROOT, args.week)
    digest = render_digest(ROOT, args.week, signals, evidence_items)
    output_path = write_digest(args.week, digest)
    print(f"Wrote {output_path}")
    if args.print:
        print()
        print(digest)


if __name__ == "__main__":
    main()

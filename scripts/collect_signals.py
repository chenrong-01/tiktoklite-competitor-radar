#!/usr/bin/env python3
"""Create a weekly collection checklist for the TikTok Lite radar."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = ROOT / "config"
OUTPUT_DIR = ROOT / "data" / "collection_checklists"


def load_json(name: str) -> dict:
    with (CONFIG_DIR / name).open("r", encoding="utf-8") as file:
        return json.load(file)


def names(items: list[dict]) -> list[str]:
    output = []
    for item in items:
        aliases = item.get("aliases", [])
        alias_text = f" ({', '.join(aliases)})" if aliases else ""
        output.append(f"{item['name']}{alias_text}")
    return output


def checklist_section(title: str, items: list[str]) -> list[str]:
    lines = [f"## {title}", ""]
    lines.extend(f"- [ ] {item}" for item in items)
    lines.append("")
    return lines


def render_checklist(week: str) -> str:
    competitors = load_json("competitors.json")
    markets = load_json("markets.json")
    sources = load_json("sources.json")

    lines = [
        f"# TikTok Lite Radar Collection Checklist - {week}",
        "",
        "Use this checklist to collect candidate signals before writing `data/signals.csv` rows.",
        "",
    ]

    lines.extend(checklist_section("Creation Fixed Competitors", names(competitors["fixed_creation_competitors"])))
    lines.extend(checklist_section("Consumption Fixed Competitors", names(competitors["fixed_consumption_competitors"])))
    lines.extend(checklist_section("Creation Emerging Categories", competitors["emerging_categories"]["creation"]))
    lines.extend(checklist_section("Consumption Emerging Categories", competitors["emerging_categories"]["consumption"]))

    market_items = []
    for tier, regions in markets.items():
        for region, countries in regions.items():
            market_items.append(f"{tier}: {region} - {', '.join(countries)}")
    lines.extend(checklist_section("Markets", market_items))

    source_items = []
    for group, items in sources.items():
        source_items.extend(f"{group}: {item}" for item in items)
    lines.extend(checklist_section("Sources", source_items))

    lines.extend(
        [
            "## Evidence To Capture",
            "",
            "- [ ] App store ranking screenshot",
            "- [ ] Product page or version update screenshot",
            "- [ ] Core feature flow screenshot",
            "- [ ] News or social buzz source link",
            "- [ ] PM judgement: why it matters and TikTok Lite implication",
            "",
        ]
    )

    return "\n".join(lines)


def write_checklist(week: str, content: str) -> Path:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    output_path = OUTPUT_DIR / f"{week}.md"
    output_path.write_text(content, encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Create a weekly collection checklist.")
    parser.add_argument("--week", required=True, help="ISO-like week key, for example 2026-W24")
    args = parser.parse_args()

    output_path = write_checklist(args.week, render_checklist(args.week))
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()

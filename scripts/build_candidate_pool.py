#!/usr/bin/env python3
"""L2 pre-rank: build the unified candidate pool from news + store rankings.

Design (5-layer radar, recommendation-style funnel)
---------------------------------------------------
This is the **pre-rank** layer. Its job is to ORGANISE and SCORE, not to judge
to death. Per the locked-in design:

* Two lines, split by SOURCE (not by query list):
    - regular line   : a NEWS item whose title names a FIXED competitor.
    - emerging line  : every other news item + ALL store-ranking entries.
* Form 4-category gate (creation / content / tool; "both" = matches >=1 of
  several). Applied to NEWS only — store rankings are already scoped by the
  content category they were pulled from, so they get ranking de-noise instead.
* Commercialization filter (monetization + incentive) applies ONLY to the
  regular line => drop. On the emerging line commercialization is KEPT but
  annotated.
* Only-kill-obvious-garbage: hard_exclude_terms drop on both lines. Everything
  else is KEPT as ``review``; priority (high/low) just tells the agent (L3) what
  to triage first. Pre-rank never silently kills a real signal — that is L3's job.

All knobs live in ``config/radar_config.json`` so adjusting/reverting is a
one-line change. ``--legacy-filter`` restores the old whitelist behaviour for a
fast rollback.

Output schema is backward-compatible: the original columns are preserved and the
new ``line``/``form``/``priority`` columns are appended.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

# Backward-compatible: original columns first, new columns appended at the end.
OUTPUT_FIELDS = [
    "week",
    "query_type",
    "locale",
    "radar_type",
    "title",
    "publisher",
    "published",
    "source_url",
    "status",
    "reason",
    "line",
    "form",
    "priority",
]

# Generic roundup/explainer titles that are never a single actionable signal.
GENERIC_PHRASES = [
    "social media updates",
    "mobile app development",
    "shift from features to experiences",
    "apps you need to know",
]


# --------------------------------------------------------------------------- #
# Config + small helpers
# --------------------------------------------------------------------------- #
def load_radar_config(root: Path) -> dict:
    path = root / "config" / "radar_config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return {}


def normalize_key(row: dict[str, str]) -> str:
    return (row.get("source_url") or row.get("title") or "").strip().lower()


def has_any(text: str, terms) -> bool:
    for term in terms:
        if not term:
            continue
        if " " in term or "-" in term:
            if term in text:
                return True
            continue
        if re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text):
            return True
    return False


def url_has_domain(url: str, domains) -> bool:
    u = (url or "").lower()
    return any(d and d in u for d in domains)


def load_fixed_competitor_terms(root: Path) -> set[str]:
    """Read fixed competitor names + aliases from config/competitors.json."""
    terms: set[str] = set()
    config_path = root / "config" / "competitors.json"
    if not config_path.exists():
        return terms
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return terms
    for key in ("fixed_creation_competitors", "fixed_consumption_competitors"):
        for entry in data.get(key, []):
            name = (entry.get("name") or "").strip().lower()
            if name:
                terms.add(name)
            for alias in entry.get("aliases", []):
                alias = (alias or "").strip().lower()
                if alias:
                    terms.add(alias)
    return terms


# --------------------------------------------------------------------------- #
# L2 v2 classification (source-based lines, form gate, scoring-not-killing)
# --------------------------------------------------------------------------- #
def detect_forms(text: str, form_taxonomy: dict[str, list[str]]) -> list[str]:
    """Return the list of forms (creation/content/tool) the text matches."""
    forms = []
    for form_name, terms in form_taxonomy.items():
        if form_name.startswith("_"):
            continue
        if has_any(text, terms):
            forms.append(form_name)
    return forms


def determine_line(row: dict[str, str], fixed_terms: set[str]) -> str:
    """Source-based split: rankings + non-named news => emerging; named => regular."""
    if row.get("query_type") == "ranking":
        return "emerging"
    title = (row.get("title") or "").lower()
    if has_any(title, fixed_terms):
        return "regular"
    return "emerging"


def commercialization_hit(text: str, config: dict) -> bool:
    terms = config.get("commercialization_terms", {})
    pool = list(terms.get("monetization", [])) + list(terms.get("incentive", []))
    return has_any(text, pool)


def score_priority(
    row: dict[str, str],
    line: str,
    config: dict,
    fixed_terms: set[str],
) -> tuple[str, int]:
    """L2 scoring (NOT a kill switch). Returns (priority, score)."""
    weights = config.get("priority_weights", {})
    title = (row.get("title") or "").lower()
    score = 0
    if has_any(title, fixed_terms):
        score += int(weights.get("named_fixed_competitor", 0))
    if has_any(title, config.get("strong_change_terms", [])):
        score += int(weights.get("strong_change_term", 0))
    if row.get("query_type") == "ranking":
        markets = [m for m in (row.get("locale") or "").split(",") if m.strip()]
        score += len(markets) * int(weights.get("ranking_breadth_per_market", 0))
    official = config.get("source_priority", {}).get("official_domains", [])
    if url_has_domain(row.get("source_url", ""), official):
        score += int(weights.get("official_source_domain", 0))
    high = int(weights.get("high_threshold", 3))
    return ("high" if score >= high else "low"), score


def classify_ranking_v2(
    row: dict[str, str],
    config: dict,
    mature_terms: set[str],
) -> dict[str, str]:
    """Ranking de-noise (emerging line only): drop dev tools + mature incumbents."""
    name = (row.get("title") or "").strip().lower()
    if not name:
        return {"status": "excluded", "reason": "empty ranking entry", "form": ""}
    noise = config.get("ranking_noise", {})
    if has_any(name, noise.get("dev_tool_terms", [])):
        return {
            "status": "excluded",
            "reason": "developer/utility tool, not a content competitor",
            "form": "",
        }
    for term in mature_terms:
        if term and term in name:
            return {
                "status": "excluded",
                "reason": "mature incumbent / fixed competitor",
                "form": "",
            }
    return {"status": "review", "reason": "emerging product from store ranking", "form": "ranking"}


def classify_v2(
    row: dict[str, str],
    line: str,
    config: dict,
    fixed_terms: set[str],
    mature_terms: set[str],
) -> dict[str, str]:
    """Recall-first pre-rank classification. Only kills obvious garbage."""
    title = (row.get("title") or "").lower()

    # Store-ranking entries: skip the form gate (the store category already
    # scopes them) and apply ranking de-noise instead.
    if row.get("query_type") == "ranking":
        result = classify_ranking_v2(row, config, mature_terms)
        return result

    # 1) Only-kill-obvious-garbage (both lines).
    hard = config.get("hard_exclude_terms", {}).get("terms", [])
    if has_any(title, hard):
        return {"status": "excluded", "reason": "hard-excluded off-topic noise", "form": ""}
    if has_any(title, GENERIC_PHRASES):
        return {"status": "excluded", "reason": "generic roundup or explainer", "form": ""}

    # 2) Form 4-category gate (news only). Any form matches => pass.
    forms = detect_forms(title, config.get("form_taxonomy", {}))
    form_label = "+".join(forms)
    if not forms:
        return {"status": "excluded", "reason": "no creation/content/tool form", "form": ""}

    # 3) Commercialization filter — REGULAR line drops, EMERGING line keeps+annotates.
    if commercialization_hit(title, config):
        if line == "regular":
            return {
                "status": "excluded",
                "reason": "commercialization/incentive out of scope (regular line)",
                "form": form_label,
            }
        # emerging line: keep, but flag it for the agent.
        return {
            "status": "review",
            "reason": f"emerging signal (commercialization noted) [{form_label}]",
            "form": form_label,
        }

    # 4) Kept as review; priority is set by the caller.
    reason = "regular competitor change" if line == "regular" else "emerging product signal"
    return {"status": "review", "reason": f"{reason} [{form_label}]", "form": form_label}


# --------------------------------------------------------------------------- #
# Legacy classification (for --legacy-filter rollback)
# --------------------------------------------------------------------------- #
LEGACY_EXCLUDE_PHRASES = {
    "monetization": "monetization/trading out of scope",
    "marketplace": "monetization/trading out of scope",
    "e-commerce": "commerce/ads out of scope",
    "ecommerce": "commerce/ads out of scope",
    "payment": "commerce/ads out of scope",
    "advertising": "commerce/ads out of scope",
    "crypto": "finance out of scope",
    "short drama": "short drama out of scope",
    "celebrity": "non-product signal",
    "scam": "non-product signal",
    "apple watch": "non-product signal",
    "first lady": "non-product signal",
    "politician": "non-product signal",
}

LEGACY_REGULAR_TERMS = [
    "douyin", "tiktok", "capcut", "instagram", "reels", "edits", "youtube",
    "shorts", "snapchat", "snap", "facebook", "meta", "threads", "twitter",
    "kuaishou", "kwai", "likee", "lemon8", "reddit",
]
LEGACY_CHANGE_TERMS = [
    "new", "launch", "rollout", "test", "adds", "feature", "update", "ai",
    "camera", "lens", "search", "feed", "repost", "remix", "download", "watermark",
]
LEGACY_EMERGING_TERMS = ["app", "setlog", "watermark", "repost", "remix", "download"]


def classify_legacy(row: dict[str, str], mature_terms: set[str]) -> dict[str, str]:
    if row.get("query_type") == "ranking":
        name = (row.get("title") or "").strip().lower()
        if not name:
            return {"status": "excluded", "reason": "empty ranking entry"}
        for term in mature_terms:
            if term and term in name:
                return {"status": "excluded", "reason": "mature incumbent / fixed competitor"}
        return {"status": "review", "reason": "emerging product from store ranking"}
    title = (row.get("title") or "").lower()
    for phrase, reason in LEGACY_EXCLUDE_PHRASES.items():
        if phrase in title:
            return {"status": "excluded", "reason": reason}
    if row.get("query_type") == "regular_competitor" or row.get("radar_type") == "fixed":
        if not has_any(title, LEGACY_REGULAR_TERMS):
            return {"status": "excluded", "reason": "no regular competitor named"}
        if not has_any(title, LEGACY_CHANGE_TERMS):
            return {"status": "excluded", "reason": "no explicit product change"}
        return {"status": "review", "reason": "regular competitor change"}
    if not has_any(title, LEGACY_EMERGING_TERMS):
        return {"status": "excluded", "reason": "no specific app/product signal"}
    return {"status": "review", "reason": "emerging product signal"}


# --------------------------------------------------------------------------- #
# IO
# --------------------------------------------------------------------------- #
def read_ranking_files(root: Path, week: str) -> list[dict[str, str]]:
    """Convert App Store + Google Play category ranking CSVs into candidate rows."""
    rows: list[dict[str, str]] = []
    store_by_file = {
        f"app_store_category_{week}.csv": "app_store",
        f"google_play_category_{week}.csv": "google_play",
    }
    for filename, store in store_by_file.items():
        path = root / "data" / "rankings" / filename
        if not path.exists():
            continue
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for entry in csv.DictReader(file):
                rows.append(
                    {
                        "week": week,
                        "query_type": "ranking",
                        "locale": entry.get("country", ""),
                        "radar_type": "emerging",
                        "title": entry.get("app", ""),
                        "publisher": entry.get("developer", ""),
                        "published": f"{store} · {entry.get('genre', '')} · #{entry.get('rank', '')}",
                        "source_url": entry.get("url", ""),
                    }
                )
    return rows


def read_candidate_files(root: Path, week: str) -> list[dict[str, str]]:
    rows = []
    for path in sorted((root / "data" / "news_candidates").glob(f"{week}_*.csv")):
        with path.open("r", encoding="utf-8-sig", newline="") as file:
            for row in csv.DictReader(file):
                rows.append(row)
    return rows


def build_candidate_pool(
    root: Path,
    week: str,
    output_path: Path,
    legacy: bool = False,
) -> list[dict[str, str]]:
    config = load_radar_config(root)
    fixed_terms = load_fixed_competitor_terms(root)
    mature_terms = set(
        config.get("ranking_noise", {}).get("mature_ranking_apps", [])
    ) | fixed_terms

    seen = set()
    output_rows = []

    def emit(row: dict[str, str], line: str, classification: dict[str, str], priority: str) -> None:
        radar_type = "fixed" if line == "regular" else "emerging"
        output_rows.append(
            {
                "week": week,
                "query_type": row.get("query_type", ""),
                "locale": row.get("locale", ""),
                "radar_type": radar_type,
                "title": row.get("title", ""),
                "publisher": row.get("publisher", ""),
                "published": row.get("published", ""),
                "source_url": row.get("source_url", ""),
                "status": classification["status"],
                "reason": classification["reason"],
                "line": line,
                "form": classification.get("form", ""),
                "priority": priority if classification["status"] == "review" else "",
            }
        )

    # 1) News candidates.
    for row in read_candidate_files(root, week):
        key = normalize_key(row)
        if not key or key in seen:
            continue
        seen.add(key)
        if legacy:
            classification = classify_legacy(row, mature_terms)
            line = "regular" if row.get("radar_type") == "fixed" else "emerging"
            classification.setdefault("form", "")
            emit(row, line, classification, "low")
            continue
        line = determine_line(row, fixed_terms)
        classification = classify_v2(row, line, config, fixed_terms, mature_terms)
        priority, _ = score_priority(row, line, config, fixed_terms)
        emit(row, line, classification, priority)

    # 2) Store-ranking candidates (always emerging line). Collapse by app name
    #    and record every chart placement (breadth is the signal).
    ranking_by_app: dict[str, dict[str, object]] = {}
    for row in read_ranking_files(root, week):
        name = (row.get("title") or "").strip()
        if not name:
            continue
        app_key = f"ranking::{name.lower()}"
        if app_key not in ranking_by_app:
            ranking_by_app[app_key] = {"row": row, "placements": [], "locales": set()}
        bucket = ranking_by_app[app_key]
        bucket["placements"].append(row.get("published", ""))  # type: ignore[union-attr]
        if row.get("locale"):
            bucket["locales"].add(row["locale"])  # type: ignore[union-attr]

    for app_key, bucket in ranking_by_app.items():
        base = bucket["row"]  # type: ignore[assignment]
        placements = bucket["placements"]  # type: ignore[assignment]
        locales = sorted(bucket["locales"])  # type: ignore[arg-type]
        row = {
            "week": week,
            "query_type": "ranking",
            "locale": ",".join(locales),
            "radar_type": "emerging",
            "title": base.get("title", ""),
            "publisher": base.get("publisher", ""),
            "published": " | ".join(placements[:8]),
            "source_url": base.get("source_url", ""),
        }
        if legacy:
            classification = classify_legacy(row, mature_terms)
            classification.setdefault("form", "")
            emit(row, "emerging", classification, "low")
            continue
        classification = classify_v2(row, "emerging", config, fixed_terms, mature_terms)
        priority, _ = score_priority(row, "emerging", config, fixed_terms)
        emit(row, "emerging", classification, priority)

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=OUTPUT_FIELDS)
        writer.writeheader()
        writer.writerows(output_rows)
    return output_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Build unified TikTok Lite radar candidate pool (L2 pre-rank).")
    parser.add_argument("--week", required=True)
    parser.add_argument(
        "--legacy-filter",
        action="store_true",
        help="Use the old whitelist-based classification (fast rollback).",
    )
    args = parser.parse_args()

    output_path = ROOT / "data" / "candidates" / f"{args.week}.csv"
    rows = build_candidate_pool(ROOT, args.week, output_path, legacy=args.legacy_filter)
    kept = sum(1 for r in rows if r["status"] == "review")
    regular = sum(1 for r in rows if r["line"] == "regular" and r["status"] == "review")
    emerging = sum(1 for r in rows if r["line"] == "emerging" and r["status"] == "review")
    print(f"Wrote {output_path}")
    print(f"Candidates: {len(rows)} | review: {kept} (regular {regular}, emerging {emerging})")


if __name__ == "__main__":
    main()

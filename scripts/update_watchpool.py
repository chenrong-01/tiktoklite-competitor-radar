#!/usr/bin/env python3
"""L4 watchpool — cross-week tracking list for the EMERGING line only.

The rank layer (L3) evaluates each signal within a single week. The watchpool is
a distinct layer that carries STATE across weeks: an emerging product that is not
yet a confirmed signal still gets watched for a few weeks to see whether it keeps
climbing (a real trend) or fizzles (noise).

Scope & identity
----------------
* Emerging line only (regular competitors are fixed and always watched, so they
  never need a watchpool).
* Members are keyed by app name. The reliable, cross-week-stable source of app
  identity is the store-ranking candidates (``query_type == ranking``), so the
  pool is populated from emerging-line ranking candidates with ``status==review``.
* Heat = breadth this week (number of distinct markets the app charts in).

Lifecycle (all knobs from config/radar_config.json -> watchpool)
----------------------------------------------------------------
* 新增  (new)        : app seen this week that was not in the pool before.
* 持续  (continuing) : app in the pool and seen again this week (cold reset to 0).
* 退池  (exiting)    : app not seen for >= cold_weeks_to_exit weeks -> removed.
* Capacity: if active members exceed ``capacity``, the weakest (lowest heat, then
  fewest weeks_in_pool) are evicted as 退池.

Output: data/watchpool.csv (the persistent state) and a per-week snapshot
data/watchpool_<week>.csv used by the report layer for the 观察池动态 section.
"""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WATCHPOOL_PATH = ROOT / "data" / "watchpool.csv"

FIELDS = [
    "app",
    "developer",
    "url",
    "first_seen_week",
    "last_seen_week",
    "weeks_in_pool",
    "weeks_cold",
    "heat",
    "markets",
    "status",
]


def load_config(root: Path) -> dict:
    path = root / "config" / "radar_config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("watchpool", {})
    except Exception:  # noqa: BLE001
        return {}


def load_watchpool(path: Path) -> dict[str, dict[str, str]]:
    pool: dict[str, dict[str, str]] = {}
    if not path.exists():
        return pool
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            key = (row.get("app") or "").strip().lower()
            if key:
                pool[key] = row
    return pool


def read_emerging_ranking_candidates(root: Path, week: str) -> dict[str, dict[str, str]]:
    """Return this week's emerging ranking review candidates, keyed by app name."""
    path = root / "data" / "candidates" / f"{week}.csv"
    found: dict[str, dict[str, str]] = {}
    if not path.exists():
        return found
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        for row in csv.DictReader(file):
            if row.get("query_type") != "ranking":
                continue
            if row.get("line", "emerging") != "emerging":
                continue
            if row.get("status") != "review":
                continue
            app = (row.get("title") or "").strip()
            if not app:
                continue
            markets = [m for m in (row.get("locale") or "").split(",") if m.strip()]
            found[app.lower()] = {
                "app": app,
                "developer": row.get("publisher", ""),
                "url": row.get("source_url", ""),
                "markets": ",".join(markets),
                "heat": str(len(markets)),
            }
    return found


def update_watchpool(root: Path, week: str) -> list[dict[str, str]]:
    config = load_config(root)
    if not config.get("enabled", True):
        return []
    capacity = int(config.get("capacity", 10))
    cold_to_exit = int(config.get("cold_weeks_to_exit", 2))

    pool = load_watchpool(WATCHPOOL_PATH)
    seen = read_emerging_ranking_candidates(root, week)

    snapshot: list[dict[str, str]] = []

    # 1) Update existing members + add new ones.
    for key, info in seen.items():
        if key in pool:
            row = pool[key]
            row["last_seen_week"] = week
            row["weeks_in_pool"] = str(int(row.get("weeks_in_pool", "0") or 0) + 1)
            row["weeks_cold"] = "0"
            row["heat"] = info["heat"]
            row["markets"] = info["markets"]
            row["developer"] = info["developer"] or row.get("developer", "")
            row["url"] = info["url"] or row.get("url", "")
            row["status"] = "持续"
        else:
            pool[key] = {
                "app": info["app"],
                "developer": info["developer"],
                "url": info["url"],
                "first_seen_week": week,
                "last_seen_week": week,
                "weeks_in_pool": "1",
                "weeks_cold": "0",
                "heat": info["heat"],
                "markets": info["markets"],
                "status": "新增",
            }

    # 2) Age members not seen this week; mark exits.
    exits: list[str] = []
    for key, row in pool.items():
        if key in seen:
            continue
        row["weeks_cold"] = str(int(row.get("weeks_cold", "0") or 0) + 1)
        if int(row["weeks_cold"]) >= cold_to_exit:
            row["status"] = "退池"
            exits.append(key)
        else:
            row["status"] = "降温"

    # 3) Capacity: evict weakest active members beyond capacity.
    active = [k for k in pool if k not in exits]

    def weakness(k: str) -> tuple[int, int]:
        r = pool[k]
        return (int(r.get("heat", "0") or 0), int(r.get("weeks_in_pool", "0") or 0))

    if len(active) > capacity:
        ranked = sorted(active, key=weakness)  # weakest first
        for key in ranked[: len(active) - capacity]:
            pool[key]["status"] = "退池"
            exits.append(key)

    # 4) Build the per-week snapshot, then drop exits from the persistent pool.
    #    Exclude same-week churn: apps that were first seen THIS week and got
    #    immediately capacity-evicted never meaningfully joined the pool, so they
    #    would only flood the 观察池动态 table without carrying any cross-week
    #    signal. Keep genuine members (survivors) and genuine exits (apps that had
    #    lived in the pool in a prior week).
    for key, row in pool.items():
        evicted_on_entry = (
            row.get("status") == "退池"
            and row.get("first_seen_week") == week
        )
        if evicted_on_entry:
            continue
        snapshot.append({field: row.get(field, "") for field in FIELDS})

    for key in exits:
        pool.pop(key, None)

    # 5) Persist.
    WATCHPOOL_PATH.parent.mkdir(parents=True, exist_ok=True)
    with WATCHPOOL_PATH.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        for row in pool.values():
            writer.writerow({field: row.get(field, "") for field in FIELDS})

    snapshot_path = root / "data" / f"watchpool_{week}.csv"
    with snapshot_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(snapshot)

    return snapshot


def main() -> None:
    parser = argparse.ArgumentParser(description="Update the emerging-line watchpool (L4).")
    parser.add_argument("--week", required=True)
    args = parser.parse_args()

    snapshot = update_watchpool(ROOT, args.week)
    new = sum(1 for r in snapshot if r["status"] == "新增")
    cont = sum(1 for r in snapshot if r["status"] == "持续")
    cool = sum(1 for r in snapshot if r["status"] == "降温")
    out = sum(1 for r in snapshot if r["status"] == "退池")
    print(f"Watchpool updated for {args.week}")
    print(f"新增 {new} | 持续 {cont} | 降温 {cool} | 退池 {out}")


if __name__ == "__main__":
    main()

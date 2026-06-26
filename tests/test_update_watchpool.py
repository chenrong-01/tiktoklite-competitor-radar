import csv
import json
import tempfile
import unittest
from pathlib import Path

from scripts import update_watchpool


def write_candidates(root, week, ranking_rows):
    """ranking_rows: list of (app, markets_csv) emerging review ranking entries."""
    cand_dir = root / "data" / "candidates"
    cand_dir.mkdir(parents=True, exist_ok=True)
    fields = [
        "week", "query_type", "locale", "radar_type", "title", "publisher",
        "published", "source_url", "status", "reason", "line", "form", "priority",
    ]
    with (cand_dir / f"{week}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for app, markets in ranking_rows:
            w.writerow({
                "week": week, "query_type": "ranking", "locale": markets,
                "radar_type": "emerging", "title": app, "publisher": "Dev",
                "published": "google_play · social · #1", "source_url": f"https://x/{app}",
                "status": "review", "reason": "emerging product from store ranking",
                "line": "emerging", "form": "ranking", "priority": "high",
            })


def write_config(root, capacity=10, cold=2):
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "radar_config.json").write_text(
        json.dumps({"watchpool": {"capacity": capacity, "cold_weeks_to_exit": cold, "enabled": True}}),
        encoding="utf-8",
    )


class WatchpoolTests(unittest.TestCase):
    def _patch_root(self, root):
        update_watchpool.ROOT = root
        update_watchpool.WATCHPOOL_PATH = root / "data" / "watchpool.csv"

    def test_lifecycle_new_continue_cool_exit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._patch_root(root)
            write_config(root, capacity=10, cold=2)

            # W1: Setlog appears in 2 markets -> 新增
            write_candidates(root, "2026-W25", [("Setlog", "KR,JP")])
            snap = update_watchpool.update_watchpool(root, "2026-W25")
            setlog = [r for r in snap if r["app"] == "Setlog"][0]
            self.assertEqual(setlog["status"], "新增")
            self.assertEqual(setlog["heat"], "2")

            # W2: Setlog seen again -> 持续, weeks_in_pool=2
            write_candidates(root, "2026-W26", [("Setlog", "KR,JP,TH")])
            snap = update_watchpool.update_watchpool(root, "2026-W26")
            setlog = [r for r in snap if r["app"] == "Setlog"][0]
            self.assertEqual(setlog["status"], "持续")
            self.assertEqual(setlog["weeks_in_pool"], "2")
            self.assertEqual(setlog["heat"], "3")

            # W3: not seen -> 降温 (cold=1, < cold_to_exit)
            write_candidates(root, "2026-W27", [])
            snap = update_watchpool.update_watchpool(root, "2026-W27")
            setlog = [r for r in snap if r["app"] == "Setlog"][0]
            self.assertEqual(setlog["status"], "降温")

            # W4: still not seen -> cold=2 >= 2 -> 退池, removed from persistent pool
            write_candidates(root, "2026-W28", [])
            snap = update_watchpool.update_watchpool(root, "2026-W28")
            setlog = [r for r in snap if r["app"] == "Setlog"][0]
            self.assertEqual(setlog["status"], "退池")
            pool = update_watchpool.load_watchpool(update_watchpool.WATCHPOOL_PATH)
            self.assertNotIn("setlog", pool)

    def test_capacity_evicts_weakest(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self._patch_root(root)
            write_config(root, capacity=2, cold=2)
            rows = [("AppA", "US,GB,JP"), ("AppB", "US,GB"), ("AppC", "US")]
            write_candidates(root, "2026-W25", rows)
            snap = update_watchpool.update_watchpool(root, "2026-W25")
            statuses = {r["app"]: r["status"] for r in snap}
            # AppC has lowest heat -> capacity-evicted on entry. Same-week churn is
            # excluded from the snapshot (never meaningfully joined the pool) and
            # is absent from the persistent pool. A and B stay.
            self.assertNotIn("AppC", statuses)
            self.assertEqual(statuses["AppA"], "新增")
            self.assertEqual(statuses["AppB"], "新增")
            pool = update_watchpool.load_watchpool(update_watchpool.WATCHPOOL_PATH)
            self.assertIn("appa", pool)
            self.assertIn("appb", pool)
            self.assertNotIn("appc", pool)


if __name__ == "__main__":
    unittest.main()

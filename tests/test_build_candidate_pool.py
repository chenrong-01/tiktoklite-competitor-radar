import tempfile
import unittest
from pathlib import Path

from scripts.build_candidate_pool import (
    build_candidate_pool,
    classify_v2,
    detect_forms,
    determine_line,
    load_radar_config,
    normalize_key,
)


ROOT = Path(__file__).resolve().parents[1]
CONFIG = load_radar_config(ROOT)
FIXED_TERMS = {
    "tiktok", "instagram", "reels", "edits", "youtube", "shorts", "snapchat",
    "facebook", "capcut", "douyin", "meta",
}
MATURE_TERMS = set(CONFIG.get("ranking_noise", {}).get("mature_ranking_apps", [])) | FIXED_TERMS


class HelperTests(unittest.TestCase):
    def test_normalize_key_uses_url_when_available(self):
        row = {"source_url": "https://example.com/a?x=1", "title": "Title"}
        self.assertEqual(normalize_key(row), "https://example.com/a?x=1")

    def test_detect_forms_matches_creation_and_content(self):
        forms = detect_forms("instagram adds new caption editor for reels", CONFIG["form_taxonomy"])
        self.assertIn("creation", forms)

    def test_determine_line_splits_by_named_competitor(self):
        named = {"query_type": "regular_competitor", "title": "Instagram adds new caption feature"}
        unnamed = {"query_type": "emerging_product", "title": "New friend camera app goes viral"}
        ranking = {"query_type": "ranking", "title": "Setlog"}
        self.assertEqual(determine_line(named, FIXED_TERMS), "regular")
        self.assertEqual(determine_line(unnamed, FIXED_TERMS), "emerging")
        self.assertEqual(determine_line(ranking, FIXED_TERMS), "emerging")


class ClassifyV2Tests(unittest.TestCase):
    def _classify(self, row, line):
        return classify_v2(row, line, CONFIG, FIXED_TERMS, MATURE_TERMS)

    def test_hard_excluded_garbage_dropped_both_lines(self):
        row = {"query_type": "emerging_product", "title": "Politician video goes viral on social app"}
        result = self._classify(row, "emerging")
        self.assertEqual(result["status"], "excluded")

    def test_form_gate_drops_no_form_news(self):
        row = {"query_type": "regular_competitor", "title": "Instagram quarterly earnings beat estimates"}
        result = self._classify(row, "regular")
        self.assertEqual(result["status"], "excluded")
        self.assertIn("form", result["reason"])

    def test_commercialization_dropped_on_regular_line(self):
        row = {"query_type": "regular_competitor", "title": "Instagram adds live shopping checkout for creators"}
        result = self._classify(row, "regular")
        self.assertEqual(result["status"], "excluded")
        self.assertIn("commercialization", result["reason"])

    def test_commercialization_kept_on_emerging_line(self):
        row = {"query_type": "emerging_product", "title": "New creator app adds watch-to-earn rewards feed"}
        result = self._classify(row, "emerging")
        self.assertEqual(result["status"], "review")
        self.assertIn("commercialization noted", result["reason"])

    def test_real_signal_recalled_not_killed(self):
        # The Fast Company "Multiple Captions" case that the old whitelist killed.
        row = {"query_type": "regular_competitor", "title": "Instagram is testing multiple captions on Reels"}
        result = self._classify(row, "regular")
        self.assertEqual(result["status"], "review")

    def test_ranking_dev_tool_dropped(self):
        row = {"query_type": "ranking", "title": "Termius - Modern SSH Client"}
        result = self._classify(row, "emerging")
        self.assertEqual(result["status"], "excluded")
        self.assertIn("developer", result["reason"])

    def test_ranking_incumbent_dropped(self):
        row = {"query_type": "ranking", "title": "TikTok - Videos, Shop & LIVE"}
        result = self._classify(row, "emerging")
        self.assertEqual(result["status"], "excluded")
        self.assertIn("incumbent", result["reason"])

    def test_ranking_emerging_kept(self):
        row = {"query_type": "ranking", "title": "Setlog"}
        result = self._classify(row, "emerging")
        self.assertEqual(result["status"], "review")
        self.assertIn("ranking", result["reason"])


class BuildPoolTests(unittest.TestCase):
    def test_build_candidate_pool_merges_and_dedupes_csvs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "data" / "news_candidates"
            output = root / "data" / "candidates" / "2026-W25.csv"
            input_dir.mkdir(parents=True)
            (root / "config").mkdir(parents=True)
            # Copy real configs so the v2 classifier has its knobs.
            (root / "config" / "radar_config.json").write_text(
                (ROOT / "config" / "radar_config.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "config" / "competitors.json").write_text(
                (ROOT / "config" / "competitors.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            csv_text = (
                "week,query_type,query,locale,radar_type,track,title,publisher,published,source_url,status\n"
                "2026-W25,emerging_product,new social app,US,emerging,needs_classification,New social camera app goes viral,News,Today,https://example.com/a,candidate\n"
                "2026-W25,emerging_product,new social app,GB,emerging,needs_classification,New social camera app goes viral,News,Today,https://example.com/a,candidate\n"
            )
            (input_dir / "2026-W25_US.csv").write_text(csv_text, encoding="utf-8")

            rows = build_candidate_pool(root, "2026-W25", output)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "review")
        self.assertEqual(rows[0]["line"], "emerging")

    def test_build_candidate_pool_ingests_rankings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "data" / "news_candidates"
            rankings_dir = root / "data" / "rankings"
            output = root / "data" / "candidates" / "2026-W25.csv"
            input_dir.mkdir(parents=True)
            rankings_dir.mkdir(parents=True)
            (root / "config").mkdir(parents=True)
            (root / "config" / "radar_config.json").write_text(
                (ROOT / "config" / "radar_config.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (root / "config" / "competitors.json").write_text(
                (ROOT / "config" / "competitors.json").read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (input_dir / "2026-W25_US.csv").write_text(
                "week,query_type,query,locale,radar_type,track,title,publisher,published,source_url,status\n",
                encoding="utf-8",
            )
            (rankings_dir / "app_store_category_2026-W25.csv").write_text(
                "week,date,country,genre,rank,app,developer,url\n"
                "2026-W25,2026-06-22,US,photo_video,1,Sekai,SekaiAI,https://apps.apple.com/sekai\n"
                "2026-W25,2026-06-22,JP,photo_video,2,Sekai,SekaiAI,https://apps.apple.com/sekai\n"
                "2026-W25,2026-06-22,US,entertainment,5,TikTok,ByteDance,https://apps.apple.com/tiktok\n",
                encoding="utf-8",
            )

            rows = build_candidate_pool(root, "2026-W25", output)

        ranking_rows = [r for r in rows if r["query_type"] == "ranking"]
        sekai = [r for r in ranking_rows if r["title"] == "Sekai"]
        self.assertEqual(len(sekai), 1)
        self.assertEqual(sekai[0]["status"], "review")
        self.assertEqual(sekai[0]["line"], "emerging")
        self.assertIn("US", sekai[0]["locale"])
        self.assertIn("JP", sekai[0]["locale"])
        tiktok = [r for r in ranking_rows if r["title"] == "TikTok"]
        self.assertEqual(tiktok[0]["status"], "excluded")


if __name__ == "__main__":
    unittest.main()

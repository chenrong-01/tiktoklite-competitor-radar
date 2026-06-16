import tempfile
import unittest
from pathlib import Path

from scripts.build_candidate_pool import build_candidate_pool, classify_candidate, normalize_key


class BuildCandidatePoolTests(unittest.TestCase):
    def test_normalize_key_uses_url_when_available(self):
        row = {"source_url": "https://example.com/a?x=1", "title": "Title"}
        self.assertEqual(normalize_key(row), "https://example.com/a?x=1")

    def test_classify_candidate_excludes_monetization_and_short_drama(self):
        money = classify_candidate({"title": "Creator monetization marketplace app goes viral"})
        drama = classify_candidate({"title": "Short drama app tops charts"})

        self.assertEqual(money["status"], "excluded")
        self.assertIn("out of scope", money["reason"])
        self.assertEqual(drama["status"], "excluded")
        self.assertIn("short drama", drama["reason"])

    def test_classify_candidate_excludes_non_product_viral_and_generic_app_news(self):
        political_viral = classify_candidate(
            {
                "query_type": "emerging_product",
                "radar_type": "emerging",
                "title": "DK Shivakumar takes a bite of apple, throws them into crowd; video goes viral",
            }
        )
        generic_app = classify_candidate(
            {
                "query_type": "emerging_product",
                "radar_type": "emerging",
                "title": "Mobile App Development Is Changing: The Shift From Features to Experiences",
            }
        )
        scam = classify_candidate(
            {
                "query_type": "emerging_product",
                "radar_type": "emerging",
                "title": "Vir Das buys Apple Watch from Zepto, claims scam, watch video",
            }
        )

        self.assertEqual(political_viral["status"], "excluded")
        self.assertIn("non-product", political_viral["reason"])
        self.assertEqual(generic_app["status"], "excluded")
        self.assertIn("generic", generic_app["reason"])
        self.assertEqual(scam["status"], "excluded")
        self.assertIn("non-product", scam["reason"])

    def test_classify_candidate_keeps_specific_emerging_content_apps(self):
        setlog = classify_candidate(
            {
                "query_type": "emerging_product",
                "radar_type": "emerging",
                "title": "I tried the viral Korean app Setlog for a week",
            }
        )
        watermark = classify_candidate(
            {
                "query_type": "emerging_product",
                "radar_type": "emerging",
                "title": "Watermark remover app goes viral with TikTok repost creators",
            }
        )

        self.assertEqual(setlog["status"], "review")
        self.assertEqual(watermark["status"], "review")

    def test_classify_candidate_requires_regular_competitor_change(self):
        roundup = classify_candidate(
            {
                "query_type": "regular_competitor",
                "radar_type": "fixed",
                "title": "Social media updates and new features to know this week",
            }
        )
        edits = classify_candidate(
            {
                "query_type": "regular_competitor",
                "radar_type": "fixed",
                "title": "Meta's Edits app is getting an AI assistant and a desktop version",
            }
        )
        youtube_industry = classify_candidate(
            {
                "query_type": "regular_competitor",
                "radar_type": "fixed",
                "title": "How YouTube Creators Are Leveling Up to Compete With Studios",
            }
        )

        self.assertEqual(roundup["status"], "excluded")
        self.assertIn("generic", roundup["reason"])
        self.assertEqual(edits["status"], "review")
        self.assertEqual(youtube_industry["status"], "excluded")
        self.assertIn("no explicit", youtube_industry["reason"])

    def test_classify_candidate_keeps_fixed_competitors_out_of_emerging_track(self):
        edits_in_emerging_query = classify_candidate(
            {
                "query_type": "emerging_product",
                "radar_type": "emerging",
                "title": "Meta Challenges CapCut by Expanding Edits Video App to Desktop and Adding AI Assistant",
            }
        )

        self.assertEqual(edits_in_emerging_query["status"], "excluded")
        self.assertIn("regular competitor", edits_in_emerging_query["reason"])

    def test_build_candidate_pool_merges_and_dedupes_csvs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            input_dir = root / "data" / "news_candidates"
            output = root / "data" / "candidates" / "2026-W25.csv"
            input_dir.mkdir(parents=True)
            csv_text = (
                "week,query_type,query,locale,radar_type,track,title,publisher,published,source_url,status\n"
                "2026-W25,emerging_product,new social app,US,emerging,needs_classification,New social app goes viral,News,Today,https://example.com/a,candidate\n"
                "2026-W25,emerging_product,new social app,GB,emerging,needs_classification,New social app goes viral,News,Today,https://example.com/a,candidate\n"
            )
            (input_dir / "2026-W25_US.csv").write_text(csv_text, encoding="utf-8")

            rows = build_candidate_pool(root, "2026-W25", output)

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["status"], "review")


if __name__ == "__main__":
    unittest.main()

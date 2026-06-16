import json
import unittest

from scripts.collect_app_store_rankings import app_to_signal_row, collect_apps, parse_app_store_feed


class AppStoreRankingTests(unittest.TestCase):
    def test_parse_app_store_feed_returns_ranked_apps(self):
        payload = {
            "feed": {
                "results": [
                    {
                        "name": "Setlog",
                        "artistName": "New Chat Inc.",
                        "url": "https://apps.apple.com/us/app/setlog/id6587576438",
                        "genres": ["Social Networking"],
                    },
                    {
                        "name": "Threads",
                        "artistName": "Instagram, Inc.",
                        "url": "https://apps.apple.com/us/app/threads/id6446901002",
                        "genres": ["Social Networking"],
                    },
                ]
            }
        }

        apps = parse_app_store_feed(json.dumps(payload), storefront="us", genre="social-networking")

        self.assertEqual(apps[0]["rank"], 1)
        self.assertEqual(apps[0]["app"], "Setlog")
        self.assertEqual(apps[0]["region"], "us")
        self.assertEqual(apps[0]["category"], "Social Networking")
        self.assertEqual(apps[1]["rank"], 2)

    def test_app_to_signal_row_classifies_social_chart_entry_as_emerging_consumption(self):
        app = {
            "rank": 8,
            "app": "Setlog",
            "developer": "New Chat Inc.",
            "url": "https://apps.apple.com/us/app/setlog/id6587576438",
            "region": "us",
            "store": "apple_app_store",
            "chart": "top-free",
            "category": "Social Networking",
        }

        row = app_to_signal_row(app, week="2026-W24", date="2026-06-11")

        self.assertEqual(row["week"], "2026-W24")
        self.assertEqual(row["app"], "Setlog")
        self.assertEqual(row["module"], "emerging_consumption")
        self.assertEqual(row["track"], "consumption")
        self.assertEqual(row["radar_type"], "emerging")
        self.assertEqual(row["priority"], "medium")
        self.assertIn("#8", row["signal"])
        self.assertEqual(row["source_url"], "https://apps.apple.com/us/app/setlog/id6587576438")

    def test_collect_apps_returns_empty_list_when_fetch_fails(self):
        def failing_fetch(url):
            raise TimeoutError("timed out")

        apps = collect_apps(storefront="us", limit=10, fetcher=failing_fetch)

        self.assertEqual(apps, [])


if __name__ == "__main__":
    unittest.main()

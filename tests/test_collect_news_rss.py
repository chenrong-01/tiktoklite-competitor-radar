import unittest

from scripts.collect_news_rss import (
    build_google_news_rss_url,
    collect_candidates,
    is_relevant_news_item,
    item_to_candidate,
    parse_rss,
)


class CollectNewsRssTests(unittest.TestCase):
    def test_build_google_news_rss_url_encodes_query_and_locale(self):
        url = build_google_news_rss_url("viral social app", locale="US", language="en")

        self.assertEqual(
            url,
            "https://news.google.com/rss/search?q=viral+social+app+when%3A7d&hl=en-US&gl=US&ceid=US:en",
        )

    def test_parse_rss_returns_items(self):
        rss = """<?xml version="1.0" encoding="UTF-8"?>
        <rss><channel>
          <item>
            <title>New social app hits No. 1</title>
            <link>https://news.example.com/story</link>
            <source url="https://news.example.com">Example News</source>
            <pubDate>Thu, 11 Jun 2026 10:00:00 GMT</pubDate>
          </item>
        </channel></rss>
        """

        items = parse_rss(rss)

        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["title"], "New social app hits No. 1")
        self.assertEqual(items[0]["source"], "Example News")

    def test_item_to_candidate_marks_emerging_query_as_emerging_product(self):
        item = {
            "title": "New Gen Z social app goes viral",
            "link": "https://news.example.com/story",
            "source": "Example News",
            "published": "Thu, 11 Jun 2026 10:00:00 GMT",
        }

        candidate = item_to_candidate(
            item,
            week="2026-W24",
            query="viral social app",
            query_type="emerging_product",
            locale="US",
        )

        self.assertEqual(candidate["week"], "2026-W24")
        self.assertEqual(candidate["radar_type"], "emerging")
        self.assertEqual(candidate["track"], "needs_classification")
        self.assertEqual(candidate["source_url"], "https://news.example.com/story")
        self.assertIn("viral social app", candidate["query"])

    def test_is_relevant_news_item_filters_generic_viral_social_media_posts(self):
        self.assertFalse(
            is_relevant_news_item(
                {
                    "title": "Hunter Biden, in viral social media posts, reclaims his narrative",
                    "source": "Example News",
                }
            )
        )
        self.assertTrue(
            is_relevant_news_item(
                {
                    "title": "K-pop stars make an unfiltered video log app go viral",
                    "source": "Business Insider",
                },
                query_type="emerging_product",
            )
        )
        self.assertFalse(
            is_relevant_news_item(
                {
                    "title": "Social Media Star goes viral with music video",
                    "source": "Yahoo",
                },
                query_type="emerging_product",
            )
        )

    def test_collect_candidates_skips_failed_queries(self):
        def fake_fetch(url):
            if "bad" in url:
                raise TimeoutError("timed out")
            return """<?xml version="1.0" encoding="UTF-8"?>
            <rss><channel>
              <item>
                <title>New social app goes viral</title>
                <link>https://news.example.com/good</link>
                <source>Example News</source>
                <pubDate>Thu, 11 Jun 2026 10:00:00 GMT</pubDate>
              </item>
            </channel></rss>
            """

        candidates = collect_candidates(
            week="2026-W24",
            queries={"emerging_product": ["bad query", "good app query"]},
            locale="US",
            language="en",
            limit_per_query=1,
            fetcher=fake_fetch,
        )

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["source_url"], "https://news.example.com/good")


if __name__ == "__main__":
    unittest.main()

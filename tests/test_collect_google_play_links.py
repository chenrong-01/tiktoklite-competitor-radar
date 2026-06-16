import unittest

from scripts.collect_google_play_links import build_play_url, render_checklist


class GooglePlayLinksTests(unittest.TestCase):
    def test_build_play_url_uses_market_language_and_category(self):
        url = build_play_url(market="br", language="pt-BR", category="SOCIAL")

        self.assertEqual(
            url,
            "https://play.google.com/store/apps/category/SOCIAL?hl=pt-BR&gl=BR",
        )

    def test_render_checklist_includes_markets_categories_and_screenshot_tasks(self):
        markdown = render_checklist(
            week="2026-W24",
            markets=["us", "br"],
            categories=["SOCIAL", "VIDEO_PLAYERS"],
        )

        self.assertIn("# Google Play Discovery Checklist - 2026-W24", markdown)
        self.assertIn("US / SOCIAL", markdown)
        self.assertIn("BR / VIDEO_PLAYERS", markdown)
        self.assertIn("App detail page screenshot", markdown)
        self.assertIn("https://play.google.com/store/apps/category/SOCIAL?hl=en-US&gl=US", markdown)


if __name__ == "__main__":
    unittest.main()

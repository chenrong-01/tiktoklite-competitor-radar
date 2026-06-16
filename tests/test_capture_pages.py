import tempfile
import unittest
from pathlib import Path

from scripts.capture_pages import (
    ScreenshotTarget,
    extract_targets_from_csv,
    extract_targets_from_markdown,
    limit_targets,
    screenshot_path_for_target,
    slugify,
)


class CapturePagesTests(unittest.TestCase):
    def test_slugify_creates_stable_ascii_names(self):
        self.assertEqual(slugify("US / SOCIAL: Google Play"), "us-social-google-play")
        self.assertEqual(slugify("Threads: rank #8"), "threads-rank-8")

    def test_extract_targets_from_csv_reads_source_url_rows(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "rankings.csv"
            path.write_text(
                "week,rank,app,region,category,source_url\n"
                "2026-W23,1,Old,us,all,https://example.com/old\n"
                "2026-W24,8,Threads,us,all,https://apps.apple.com/us/app/threads/id6446901002\n",
                encoding="utf-8",
            )

            targets = extract_targets_from_csv(path, week="2026-W24")

        self.assertEqual(
            targets,
            [
                ScreenshotTarget(
                    week="2026-W24",
                    source="rankings",
                    label="8 Threads us all",
                    url="https://apps.apple.com/us/app/threads/id6446901002",
                )
            ],
        )

    def test_extract_targets_from_markdown_reads_google_play_links(self):
        markdown = (
            "- [ ] US / SOCIAL: https://play.google.com/store/apps/category/SOCIAL?hl=en-US&gl=US\n"
            "- [ ] Notes without a URL\n"
        )

        targets = extract_targets_from_markdown(markdown, week="2026-W24", source="google_play")

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0].label, "US / SOCIAL")
        self.assertEqual(
            targets[0].url,
            "https://play.google.com/store/apps/category/SOCIAL?hl=en-US&gl=US",
        )

    def test_screenshot_path_for_target_uses_week_and_label(self):
        target = ScreenshotTarget(
            week="2026-W24",
            source="google_play",
            label="US / SOCIAL",
            url="https://play.google.com/store/apps/category/SOCIAL?hl=en-US&gl=US",
        )

        path = screenshot_path_for_target(target)

        self.assertEqual(path, Path("assets/screenshots/2026-W24/google-play-us-social.png"))

    def test_limit_targets_returns_first_n_targets(self):
        targets = [
            ScreenshotTarget("2026-W24", "source", "one", "https://example.com/1"),
            ScreenshotTarget("2026-W24", "source", "two", "https://example.com/2"),
        ]

        self.assertEqual(limit_targets(targets, 1), targets[:1])
        self.assertEqual(limit_targets(targets, None), targets)


if __name__ == "__main__":
    unittest.main()

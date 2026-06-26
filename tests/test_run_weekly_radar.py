import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from scripts.run_weekly_radar import iso_week_key, write_feishu_json


class RunWeeklyRadarTests(unittest.TestCase):
    def test_iso_week_key_formats_year_and_week(self):
        self.assertEqual(iso_week_key(date(2026, 6, 16)), "2026-W25")

    def test_write_feishu_json_creates_portable_payload(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            write_feishu_json(
                output,
                title="TikTok Lite Weekly Radar · 2026-W25",
                markdown="# Report\n\nBody",
                sources=[{"title": "Source", "url": "https://example.com"}],
                screenshots=[{"label": "Shot", "path": "assets/shot.png"}],
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["title"], "TikTok Lite Weekly Radar · 2026-W25")
        self.assertEqual(payload["markdown"], "# Report\n\nBody")
        self.assertEqual(payload["sources"][0]["url"], "https://example.com")
        self.assertEqual(payload["screenshots"][0]["path"], "assets/shot.png")
    def test_write_feishu_json_preserves_media_type(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output = Path(temp_dir) / "report.json"
            write_feishu_json(
                output,
                title="TikTok Lite Weekly Radar · 2026-W26",
                markdown="# Report\n\nBody",
                sources=[],
                screenshots=[{"label": "Instagram", "path": "assets/demo.gif", "type": "gif"}],
            )

            payload = json.loads(output.read_text(encoding="utf-8"))

        self.assertEqual(payload["screenshots"][0]["path"], "assets/demo.gif")
        self.assertEqual(payload["screenshots"][0]["type"], "gif")


if __name__ == "__main__":
    unittest.main()

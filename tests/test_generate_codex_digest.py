import tempfile
import unittest
from pathlib import Path

from scripts.generate_codex_digest import (
    ScreenshotEvidence,
    Signal,
    image_markdown,
    render_digest,
    render_evidence_gallery,
)


class GenerateCodexDigestTests(unittest.TestCase):
    def test_image_markdown_uses_absolute_path_when_file_exists(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "assets" / "screenshots" / "2026-W24" / "signal.png"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"png")

            markdown = image_markdown(root, "assets/screenshots/2026-W24/signal.png", "Setlog")

        self.assertIn(f"![Setlog]({image_path})", markdown)

    def test_image_markdown_returns_empty_string_when_missing(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            markdown = image_markdown(Path(temp_dir), "assets/screenshots/missing.png", "Missing")

        self.assertEqual(markdown, "")

    def test_render_digest_groups_signals_and_includes_judgement(self):
        signal = Signal(
            week="2026-W24",
            date="2026-06-11",
            app="Setlog",
            region="South Korea",
            module="emerging_creation",
            track="creation",
            radar_type="emerging",
            category="auto vlog",
            signal="Auto-stitches tiny daily clips.",
            feature_detail="",
            product_overview="是什么：朋友共拍 vlog。功能：自动拼接。怎么用：每小时拍 2 秒。",
            why_it_matters="Low-pressure creation.",
            tiktok_lite_implication="Watch auto-vlog creation.",
            priority="medium",
            source_url="https://example.com",
            screenshot_path="",
            status="needs_review",
        )

        digest = render_digest(Path("."), "2026-W24", [signal], [])

        self.assertIn("# TikTok Lite Weekly Radar · 2026-W24", digest)
        self.assertIn("## 常规竞品调研", digest)
        self.assertIn("## 新兴产品", digest)
        self.assertIn("## 新兴产品", digest)
        self.assertIn("### Setlog · South Korea", digest)
        self.assertIn("Watch auto-vlog creation.", digest)
        self.assertIn("产品详解", digest)
        self.assertIn("**来源**", digest)
        self.assertIn("[source](https://example.com)", digest)
        self.assertIn("## 附加截图", digest)
        self.assertIn("`新兴产品`", digest)
        self.assertNotIn("Creation Emerging Radar", digest)
        self.assertNotIn("暂不跟进", digest)

    def test_render_evidence_gallery_includes_existing_images(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "assets" / "screenshots" / "2026-W24" / "play.png"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"png")
            evidence = [
                ScreenshotEvidence(
                    week="2026-W24",
                    source="google_play",
                    label="US / SOCIAL",
                    url="https://play.google.com",
                    screenshot_path="assets/screenshots/2026-W24/play.png",
                    status="pending",
                )
            ]

            gallery = render_evidence_gallery(root, evidence)

        self.assertIn("### US / SOCIAL", gallery)
        self.assertIn(f"![US / SOCIAL]({image_path})", gallery)

    def test_render_digest_does_not_repeat_signal_screenshots_in_gallery(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            image_path = root / "assets" / "screenshots" / "2026-W24" / "signal.png"
            image_path.parent.mkdir(parents=True)
            image_path.write_bytes(b"png")
            signal = Signal(
                week="2026-W24",
                date="2026-06-11",
                app="Setlog",
                region="South Korea",
                module="emerging_creation",
                track="creation",
                radar_type="emerging",
                category="auto vlog",
                signal="Auto-stitches tiny daily clips.",
                feature_detail="",
                product_overview="",
                why_it_matters="Low-pressure creation.",
                tiktok_lite_implication="Watch auto-vlog creation.",
                priority="medium",
                source_url="https://example.com",
                screenshot_path="assets/screenshots/2026-W24/signal.png",
                status="needs_review",
            )
            evidence = [
                ScreenshotEvidence(
                    week="2026-W24",
                    source="signals",
                    label="Setlog duplicate",
                    url="https://example.com",
                    screenshot_path="assets/screenshots/2026-W24/signal.png",
                    status="pending",
                )
            ]

            digest = render_digest(root, "2026-W24", [signal], evidence)

        self.assertEqual(digest.count(f"![Setlog]({image_path})"), 1)
        self.assertNotIn("### Setlog duplicate", digest)


if __name__ == "__main__":
    unittest.main()

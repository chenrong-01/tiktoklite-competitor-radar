import csv
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from scripts.process_media import is_animated_gif, validate_signal_media, validate_signals_csv


BASE_ROW = {
    "week": "2026-W26",
    "date": "2026-06-25",
    "app": "Instagram",
    "region": "Global",
    "module": "fixed_creation",
    "track": "creation",
    "radar_type": "fixed",
    "category": "creation",
    "signal": "Multiple Captions demo",
    "feature_detail": "Feature detail",
    "product_overview": "",
    "why_it_matters": "Why",
    "tiktok_lite_implication": "Implication",
    "priority": "high",
    "source_url": "https://example.com",
    "screenshot_path": "",
    "status": "published",
    "line": "regular",
    "form": "creation",
    "confidence": "A",
    "media_path": "assets/demo.gif",
    "media_type": "gif",
    "cite_primary": "https://example.com",
    "cite_secondary": "",
}


def write_gif(path: Path, *, frames: int) -> None:
    images = []
    for i in range(frames):
        image = Image.new("RGB", (8, 8), color=((i * 80) % 255, (i * 40) % 255, (i * 120) % 255))
        image.putpixel((i % 8, i % 8), (255, 255, 255))
        images.append(image)
    path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(path, save_all=True, append_images=images[1:], duration=80, loop=0)


class ProcessMediaValidationTests(unittest.TestCase):
    def test_rejects_static_when_dynamic_demo_available(self):
        row = dict(BASE_ROW)
        row.update(
            {
                "media_path": "assets/demo.jpg",
                "media_type": "screenshot",
                "dynamic_demo_available": "true",
            }
        )
        with tempfile.TemporaryDirectory() as temp_dir:
            errors = validate_signal_media(row, root=Path(temp_dir))

        self.assertTrue(any("dynamic demo is marked available" in error for error in errors))

    def test_static_requires_no_dynamic_demo_confirmation(self):
        row = dict(BASE_ROW)
        row.update({"media_path": "assets/demo.jpg", "media_type": "screenshot"})
        with tempfile.TemporaryDirectory() as temp_dir:
            errors = validate_signal_media(row, root=Path(temp_dir))

        self.assertTrue(any("Static media is only allowed" in error or "static media is only allowed" in error for error in errors))

        row["dynamic_demo_search_status"] = "no dynamic demo found"
        with tempfile.TemporaryDirectory() as temp_dir:
            errors = validate_signal_media(row, root=Path(temp_dir))

        self.assertEqual(errors, [])

    def test_gif_must_be_truly_animated(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gif_path = root / "assets" / "demo.gif"
            write_gif(gif_path, frames=1)
            row = dict(BASE_ROW)
            row["media_path"] = "assets/demo.gif"

            errors = validate_signal_media(row, root=root)

        self.assertTrue(any("GIF must be an actual animated demo" in error for error in errors))

    def test_animated_gif_passes(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            gif_path = root / "assets" / "demo.gif"
            write_gif(gif_path, frames=3)
            row = dict(BASE_ROW)
            row["media_path"] = "assets/demo.gif"

            errors = validate_signal_media(row, root=root)
            animated, message = is_animated_gif(gif_path)

        self.assertEqual(errors, [])
        self.assertTrue(animated)
        self.assertIn("frames", message)

    def test_validate_signals_csv_reports_row_number(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            csv_path = root / "signals.csv"
            fieldnames = list(BASE_ROW.keys()) + ["dynamic_demo_available"]
            row = dict(BASE_ROW)
            row.update(
                {
                    "media_path": "assets/demo.jpg",
                    "media_type": "screenshot",
                    "dynamic_demo_available": "true",
                }
            )
            with csv_path.open("w", encoding="utf-8", newline="") as file:
                writer = csv.DictWriter(file, fieldnames=fieldnames)
                writer.writeheader()
                writer.writerow(row)

            errors = validate_signals_csv(csv_path, root=root)

        self.assertTrue(errors)
        self.assertIn("row 2", errors[0])


if __name__ == "__main__":
    unittest.main()

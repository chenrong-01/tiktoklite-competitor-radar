#!/usr/bin/env python3
"""L5 media processing — compress + validate visual assets for the report.

Policy (from config/radar_config.json -> media_capture)
-------------------------------------------------------
Regular-competitor new features get a visual asset showing what the feature is
and how it is used. Asset selection priority (the AGENT performs the finding):

  1. official_demo_gif_video         (official blog / newsroom demo)
  2. media_hands_on_gif_video        (TechCrunch/Verge hands-on clip)
  3. in_product_or_media_screenshot
  4. static_screenshot_placeholder   (no animated demo exists)

Reuse-first: prefer a page already visited during L3 cross-verification; only do
a targeted re-search when none is found. No in-product screen recording unless
the user explicitly asks (allow_in_product_recording is false by default).

This module is the deterministic part: given a downloaded GIF, compress it to fit
the size budget (gif_max_chars for base64 inlining, gif_max_bytes on disk) using
the configured downscale/frame-step/palette knobs. The agent calls
``compress_gif`` on each downloaded animation and ``within_budget`` to verify.
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DYNAMIC_MEDIA_TYPES = {"gif", "video", "mp4", "webm", "mov"}
STATIC_MEDIA_TYPES = {"screenshot", "static", "static_screenshot", "png", "jpg", "jpeg", "image"}
DEMO_AVAILABLE_FIELDS = (
    "demo_gif_video_available",
    "dynamic_demo_available",
    "has_dynamic_demo",
    "demo_available",
)
STATIC_FALLBACK_FIELDS = (
    "static_fallback_reason",
    "dynamic_demo_search_status",
    "dynamic_demo_search_note",
    "media_note",
)
class MediaValidationError(ValueError):
    """Raised when L5 media validation fails."""


def load_media_config(root: Path = ROOT) -> dict:
    path = root / "config" / "radar_config.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8")).get("media_capture", {})
    except Exception:  # noqa: BLE001
        return {}


def within_budget(path: Path, config: dict | None = None) -> tuple[bool, str]:
    """Check a media file against the byte + base64-char budgets."""
    config = config or load_media_config()
    max_bytes = int(config.get("gif_max_bytes", 10485760))
    max_chars = int(config.get("gif_max_chars", 14000000))
    if not path.exists():
        return False, f"missing: {path}"
    size = path.stat().st_size
    if size > max_bytes:
        return False, f"{size} bytes > {max_bytes} byte budget"
    # base64 length ~= ceil(size/3)*4
    b64_len = ((size + 2) // 3) * 4
    if b64_len > max_chars:
        return False, f"base64 {b64_len} chars > {max_chars} char budget"
    return True, f"ok ({size} bytes, ~{b64_len} base64 chars)"


def compress_gif(src: Path, dst: Path, config: dict | None = None) -> Path:
    """Downscale + frame-step + palette-reduce a GIF to fit the size budget.

    Iteratively tightens the knobs until the result fits ``gif_max_bytes``.
    Requires Pillow; raises a clear error if it is unavailable.
    """
    try:
        from PIL import Image, ImageSequence
    except ImportError as error:  # noqa: BLE001
        raise RuntimeError(
            "Pillow is required for GIF compression. Install with "
            "`python3 -m pip install --user --break-system-packages Pillow`."
        ) from error

    config = config or load_media_config()
    knobs = config.get("gif_compress", {})
    max_width = int(knobs.get("max_width", 540))
    frame_step = int(knobs.get("frame_step", 3))
    colors = int(knobs.get("colors", 128))
    max_bytes = int(config.get("gif_max_bytes", 10485760))

    dst.parent.mkdir(parents=True, exist_ok=True)

    def render(width: int, step: int, palette: int) -> None:
        with Image.open(src) as im:
            frames = []
            durations = []
            for i, frame in enumerate(ImageSequence.Iterator(im)):
                if i % step != 0:
                    continue
                f = frame.convert("RGBA")
                if f.width > width:
                    ratio = width / f.width
                    f = f.resize((width, max(1, int(f.height * ratio))))
                f = f.convert("P", palette=Image.ADAPTIVE, colors=palette)
                frames.append(f)
                durations.append(frame.info.get("duration", 100))
            if not frames:
                raise RuntimeError("GIF produced no frames after sampling")
            frames[0].save(
                dst,
                save_all=True,
                append_images=frames[1:],
                loop=0,
                duration=durations,
                optimize=True,
                disposal=2,
            )

    width, step, palette = max_width, frame_step, colors
    for _ in range(6):
        render(width, step, palette)
        if dst.stat().st_size <= max_bytes:
            return dst
        # Tighten: shrink width, then drop more frames, then reduce palette.
        width = max(240, int(width * 0.8))
        step += 1
        palette = max(32, int(palette * 0.75))
    return dst  # best effort even if still over budget


def is_animated_gif(path: Path) -> tuple[bool, str]:
    """Return whether a GIF is truly animated, not a renamed static image."""
    if not path.exists():
        return False, f"missing: {path}"
    try:
        from PIL import Image
    except ImportError as error:  # noqa: BLE001
        raise RuntimeError(
            "Pillow is required for GIF animation validation. Install with "
            "`python3 -m pip install --user --break-system-packages Pillow`."
        ) from error
    try:
        with Image.open(path) as im:
            frames = int(getattr(im, "n_frames", 1))
    except Exception as error:  # noqa: BLE001
        return False, f"cannot read GIF frames: {error}"
    if frames <= 1:
        return False, f"GIF is static ({frames} frame)"
    return True, f"animated GIF ({frames} frames)"


def _truthy(value: str | None) -> bool:
    return (value or "").strip().lower() in {"1", "true", "yes", "y", "available", "found"}


def _looks_static_fallback_confirmed(row: dict[str, str]) -> bool:
    for field in STATIC_FALLBACK_FIELDS:
        value = (row.get(field) or "").strip().lower()
        if not value:
            continue
        if any(token in value for token in ("no dynamic", "not found", "none found", "未找到", "无动态")):
            return True
    return False


def _is_regular_new_feature(row: dict[str, str]) -> bool:
    radar_type = (row.get("radar_type") or "").strip().lower()
    line = (row.get("line") or "").strip().lower()
    category = (row.get("category") or "").strip().lower()
    form = (row.get("form") or "").strip().lower()
    status = (row.get("status") or "").strip().lower()
    media_path = (row.get("media_path") or row.get("screenshot_path") or "").strip()
    media_type = (row.get("media_type") or "").strip().lower()
    regular = radar_type in {"fixed", "regular"} or line == "regular"
    not_ranking = form != "ranking" and category != "ranking" and status != "watchpool"
    has_l5_media = bool(media_path or media_type)
    has_dynamic_marker = any(_truthy(row.get(field)) for field in DEMO_AVAILABLE_FIELDS)
    return regular and not_ranking and (has_l5_media or has_dynamic_marker)


def _asset_path(root: Path, media_path: str) -> Path:
    path = Path(media_path)
    return path if path.is_absolute() else root / path


def validate_signal_media(row: dict[str, str], *, root: Path = ROOT, config: dict | None = None) -> list[str]:
    """Validate one signal row against the L5 dynamic-demo-first gate."""
    errors: list[str] = []
    if not _is_regular_new_feature(row):
        return errors

    app = row.get("app", "<unknown app>")
    signal = row.get("signal", "<unknown signal>")
    label = f"{app} — {signal}"
    media_path = (row.get("media_path") or row.get("screenshot_path") or "").strip()
    media_type = (row.get("media_type") or "").strip().lower()
    dynamic_available = any(_truthy(row.get(field)) for field in DEMO_AVAILABLE_FIELDS)

    if not media_path:
        errors.append(f"{label}: regular new feature must include L5 media_path")
        return errors
    if not media_type:
        errors.append(f"{label}: media_type is required so GIF/video is not downgraded to screenshot")

    if dynamic_available and media_type not in DYNAMIC_MEDIA_TYPES:
        errors.append(f"{label}: dynamic demo is marked available, so static media_type={media_type or '<empty>'} is not allowed")

    path = _asset_path(root, media_path)
    if media_type in DYNAMIC_MEDIA_TYPES or path.suffix.lower() == ".gif":
        ok, msg = within_budget(path, config)
        if not ok:
            errors.append(f"{label}: dynamic asset over budget or missing: {msg}")
        if media_type == "gif" or path.suffix.lower() == ".gif":
            gif_ok, gif_msg = is_animated_gif(path)
            if not gif_ok:
                errors.append(f"{label}: GIF must be an actual animated demo: {gif_msg}")
    elif media_type in STATIC_MEDIA_TYPES:
        if not _looks_static_fallback_confirmed(row):
            errors.append(f"{label}: static media is only allowed after confirming no demo GIF/video was found")
    return errors


def validate_signals_csv(path: Path, *, root: Path = ROOT, config: dict | None = None, week: str | None = None) -> list[str]:
    """Validate signal rows and return human-readable L5 errors."""
    config = config or load_media_config(root)
    errors: list[str] = []
    with path.open("r", encoding="utf-8-sig", newline="") as file:
        reader = csv.DictReader(file)
        for row_number, row in enumerate(reader, start=2):
            if week and row.get("week", "").strip() != week:
                continue
            for error in validate_signal_media(row, root=root, config=config):
                errors.append(f"row {row_number}: {error}")
    return errors


def to_base64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode("ascii")


def main() -> None:
    parser = argparse.ArgumentParser(description="Compress/validate a radar media asset (L5).")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_compress = sub.add_parser("compress", help="Compress a GIF to fit the size budget.")
    p_compress.add_argument("--src", required=True, type=Path)
    p_compress.add_argument("--dst", required=True, type=Path)

    p_check = sub.add_parser("check", help="Check a media file against the budget.")
    p_check.add_argument("--path", required=True, type=Path)

    p_validate = sub.add_parser("validate-signals", help="Validate L5 media gates in a signals CSV.")
    p_validate.add_argument("--signals", type=Path, default=ROOT / "data" / "signals.csv")
    p_validate.add_argument("--week", help="Only validate one report week, e.g. 2026-W26")

    args = parser.parse_args()
    config = load_media_config()

    if args.cmd == "compress":
        out = compress_gif(args.src, args.dst, config)
        ok, msg = within_budget(out, config)
        print(f"Wrote {out} — {'OK' if ok else 'OVER BUDGET'}: {msg}")
    elif args.cmd == "check":
        ok, msg = within_budget(args.path, config)
        print(f"{'OK' if ok else 'OVER BUDGET'}: {msg}")
    elif args.cmd == "validate-signals":
        errors = validate_signals_csv(args.signals, root=ROOT, config=config, week=args.week)
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            raise SystemExit(1)
        print(f"OK: L5 media validation passed for {args.signals}")


if __name__ == "__main__":
    main()

from __future__ import annotations

from pathlib import Path

from animation_studio.media.ffmpeg import (
    MediaError,
    media_summary,
    parse_blackdetect,
    probe_media,
    require_media_tools,
    run_command,
)


def inspect_media(path: Path) -> dict:
    return media_summary(probe_media(path))


def quality_report(path: Path, *, expected_width: int | None = None,
                   expected_height: int | None = None, expected_fps: float | None = None) -> dict:
    ffmpeg, _ = require_media_tools()
    probe = probe_media(path)
    summary = media_summary(probe)
    if summary["duration_seconds"] <= 0 or summary["width"] <= 0 or summary["height"] <= 0:
        raise MediaError("Invalid duration or video dimensions")
    errors = run_command([ffmpeg, "-v", "error", "-i", str(path), "-f", "null", "-"])
    black = run_command([
        ffmpeg, "-hide_banner", "-i", str(path), "-vf", "blackdetect=d=0.1:pix_th=0.10",
        "-an", "-f", "null", "-",
    ])
    black_segments = parse_blackdetect(black.stderr)
    checks = {
        "has_video_stream": True,
        "positive_duration": summary["duration_seconds"] > 0,
        "expected_width": expected_width is None or summary["width"] == expected_width,
        "expected_height": expected_height is None or summary["height"] == expected_height,
        "expected_fps": expected_fps is None or (summary["fps"] is not None and abs(summary["fps"] - expected_fps) < 0.02),
        "decode_errors": not bool(errors.stderr.strip()),
    }
    return {
        "file": str(path.resolve()),
        "status": "PASS" if all(checks.values()) else "WARN",
        "checks": checks,
        "media": summary,
        "black_segments": black_segments,
        "black_detection_threshold": {"minimum_seconds": 0.1, "pixel_threshold": 0.10},
        "notes": ["Black detection is a basic signal; review the frames and full clip visually."],
    }


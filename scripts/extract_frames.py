#!/usr/bin/env python3
"""Extract representative frames from a video using FFmpeg.

Requires ffmpeg and ffprobe on PATH. Does not overwrite existing outputs.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path


def run(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, check=True, capture_output=True, text=True)


def probe_duration(video: Path) -> float:
    result = run([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "json", str(video)
    ])
    payload = json.loads(result.stdout)
    duration = float(payload["format"]["duration"])
    if duration <= 0:
        raise ValueError("Video duration must be positive")
    return duration


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("video", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--margin", type=float, default=0.15,
                        help="Seconds away from exact end to avoid seeking beyond final frame")
    args = parser.parse_args()

    if not args.video.is_file():
        parser.error(f"Video not found: {args.video}")
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        parser.error("ffmpeg and ffprobe must be available on PATH")
    if args.margin < 0:
        parser.error("--margin must be >= 0")

    args.out.mkdir(parents=True, exist_ok=True)
    duration = probe_duration(args.video)
    points = {
        "first": min(0.1, duration / 10),
        "middle": duration / 2,
        "last": max(0.0, duration - args.margin),
    }

    for label, timestamp in points.items():
        output = args.out / f"{label}.png"
        if output.exists():
            raise FileExistsError(f"Refusing to overwrite: {output}")
        run([
            "ffmpeg", "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp:.3f}",
            "-i", str(args.video), "-frames:v", "1", "-update", "1", str(output)
        ])
        print(f"{label}: {output} @ {timestamp:.3f}s")

    (args.out / "frames.json").write_text(
        json.dumps({"video": str(args.video), "duration_seconds": duration,
                    "frames": points}, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.CalledProcessError, KeyError, ValueError, FileExistsError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        raise SystemExit(1)

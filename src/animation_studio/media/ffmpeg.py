from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence


class MediaError(RuntimeError):
    """Media could not be inspected, decoded or rendered."""


@dataclass(frozen=True)
class AudioTrack:
    path: Path
    volume: float = 1.0
    label: str = "audio"


def require_media_tools() -> tuple[str, str]:
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        raise MediaError("ffmpeg and ffprobe must be available on PATH")
    return ffmpeg, ffprobe


def run_command(command: Sequence[str]) -> subprocess.CompletedProcess[str]:
    try:
        result = subprocess.run(list(command), check=False, capture_output=True, text=True)
    except OSError as exc:
        raise MediaError(f"Could not start {command[0]}: {exc}") from exc
    if result.returncode:
        detail = result.stderr.strip()[-2000:]
        raise MediaError(f"Command failed ({result.returncode}): {detail}")
    return result


def probe_media(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(path)
    _, ffprobe = require_media_tools()
    result = run_command([
        ffprobe, "-v", "error", "-show_entries",
        "format=filename,format_name,duration,size:stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,duration",
        "-of", "json", str(path),
    ])
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise MediaError("ffprobe returned invalid JSON") from exc
    if not isinstance(payload, dict) or not isinstance(payload.get("streams"), list):
        raise MediaError("ffprobe response did not include streams")
    return payload


def _fraction(value: str | None) -> float | None:
    if not value or value == "0/0":
        return None
    try:
        numerator, denominator = value.split("/", 1)
        return float(numerator) / float(denominator)
    except (ValueError, ZeroDivisionError):
        return None


def media_summary(probe: dict) -> dict:
    format_info = probe.get("format", {})
    streams = probe.get("streams", [])
    video = next((item for item in streams if item.get("codec_type") == "video"), None)
    audio = [item for item in streams if item.get("codec_type") == "audio"]
    if not video:
        raise MediaError("Media has no video stream")
    duration = format_info.get("duration") or video.get("duration")
    try:
        duration_seconds = float(duration)
    except (TypeError, ValueError) as exc:
        raise MediaError("Media duration is unavailable") from exc
    return {
        "path": format_info.get("filename"),
        "container": format_info.get("format_name"),
        "duration_seconds": duration_seconds,
        "size_bytes": int(format_info.get("size", 0) or 0),
        "width": int(video.get("width", 0) or 0),
        "height": int(video.get("height", 0) or 0),
        "fps": _fraction(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        "video_codec": video.get("codec_name"),
        "audio_streams": len(audio),
        "streams": streams,
    }


def extract_representative_frames(video: Path, output_dir: Path, margin_seconds: float = 0.15) -> dict[str, Path]:
    if margin_seconds < 0:
        raise ValueError("margin_seconds must be >= 0")
    summary = media_summary(probe_media(video))
    duration = summary["duration_seconds"]
    if duration <= 0:
        raise MediaError("Video duration must be positive")
    times = {
        "first": min(0.1, duration / 10),
        "middle": duration / 2,
        "last": max(0.0, duration - margin_seconds),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg, _ = require_media_tools()
    outputs: dict[str, Path] = {}
    for label, timestamp in times.items():
        destination = output_dir / f"{label}.png"
        if destination.exists():
            raise FileExistsError(destination)
        run_command([
            ffmpeg, "-hide_banner", "-loglevel", "error", "-ss", f"{timestamp:.3f}",
            "-i", str(video), "-frames:v", "1", "-update", "1", str(destination),
        ])
        outputs[label] = destination
    metadata = {
        "video": str(video.resolve()),
        "duration_seconds": duration,
        "frames": {key: value for key, value in times.items()},
        "paths": {key: str(value.resolve()) for key, value in outputs.items()},
    }
    metadata_path = output_dir / "frames.json"
    if metadata_path.exists():
        raise FileExistsError(metadata_path)
    metadata_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    return outputs


def concat_file_contents(clips: Sequence[Path]) -> str:
    if not clips:
        raise ValueError("At least one clip is required")
    lines = ["ffconcat version 1.0"]
    for clip in clips:
        path = clip.resolve().as_posix().replace("'", "\\'")
        lines.append(f"file '{path}'")
    return "\n".join(lines) + "\n"


def build_render_command(
    concat_list: Path,
    output: Path,
    *,
    width: int,
    height: int,
    fps: int,
    video_codec: str = "libx264",
    audio_codec: str = "aac",
    audio_tracks: Sequence[AudioTrack] = (),
    subtitle_file: Path | None = None,
    overwrite: bool = False,
) -> list[str]:
    if min(width, height, fps) <= 0:
        raise ValueError("width, height and fps must be positive")
    ffmpeg, _ = require_media_tools()
    command = [ffmpeg, "-hide_banner", "-n" if not overwrite else "-y", "-f", "concat", "-safe", "0", "-i", str(concat_list)]
    for track in audio_tracks:
        if track.volume < 0:
            raise ValueError("audio volume must be non-negative")
        command.extend(["-i", str(track.path)])
    subtitle_index = None
    if subtitle_file is not None:
        subtitle_index = 1 + len(audio_tracks)
        command.extend(["-i", str(subtitle_file)])

    command.extend(["-map", "0:v:0"])
    if audio_tracks:
        filters = []
        labels = []
        for i, track in enumerate(audio_tracks, start=1):
            label = f"mix{i}"
            filters.append(f"[{i}:a:0]aresample=48000,volume={track.volume:g}[{label}]")
            labels.append(f"[{label}]")
        if len(labels) == 1:
            filters.append(f"{labels[0]}anull[aout]")
        else:
            filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:duration=longest:normalize=0[aout]")
        command.extend(["-filter_complex", ";".join(filters), "-map", "[aout]"])
    else:
        command.extend(["-map", "0:a?"])
    if subtitle_index is not None:
        command.extend(["-map", f"{subtitle_index}:s:0?"])
    video_filter = f"scale={width}:{height}:force_original_aspect_ratio=decrease,pad={width}:{height}:(ow-iw)/2:(oh-ih)/2,fps={fps}"
    command.extend([
        "-vf", video_filter,
        "-c:v", video_codec, "-preset", "fast", "-threads", "4", "-pix_fmt", "yuv420p",
        "-c:a", audio_codec,
    ])
    if subtitle_index is not None:
        command.extend(["-c:s", "mov_text"])
    command.extend(["-movflags", "+faststart", str(output)])
    return command


def parse_blackdetect(stderr: str) -> list[dict[str, float]]:
    matches = re.findall(
        r"black_start:([0-9.]+)\s+black_end:([0-9.]+)\s+black_duration:([0-9.]+)",
        stderr,
    )
    return [
        {"start_seconds": float(start), "end_seconds": float(end), "duration_seconds": float(duration)}
        for start, end, duration in matches
    ]


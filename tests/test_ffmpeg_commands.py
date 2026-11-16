from pathlib import Path

from animation_studio.media.ffmpeg import AudioTrack, build_render_command, concat_file_contents, parse_blackdetect


def test_render_command_has_safe_no_overwrite_and_normalizes_video(monkeypatch, tmp_path):
    monkeypatch.setattr("animation_studio.media.ffmpeg.require_media_tools", lambda: ("ffmpeg", "ffprobe"))
    command = build_render_command(
        tmp_path / "cut.ffconcat",
        tmp_path / "out.mp4",
        width=1920,
        height=1080,
        fps=30,
    )
    assert command[:4] == ["ffmpeg", "-hide_banner", "-n", "-f"]
    assert "scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,fps=30" in command
    assert "-map" in command and "0:a?" in command


def test_render_command_mixes_audio_and_muxes_subtitles(monkeypatch, tmp_path):
    monkeypatch.setattr("animation_studio.media.ffmpeg.require_media_tools", lambda: ("ffmpeg", "ffprobe"))
    command = build_render_command(
        tmp_path / "cut.ffconcat",
        tmp_path / "out.mp4",
        width=1280,
        height=720,
        fps=24,
        audio_tracks=[AudioTrack(tmp_path / "voice.wav", 1.0, "voice"), AudioTrack(tmp_path / "music.wav", 0.2, "music")],
        subtitle_file=tmp_path / "subtitles.srt",
        overwrite=True,
    )
    assert "-y" in command
    filter_graph = command[command.index("-filter_complex") + 1]
    assert "amix=inputs=2" in filter_graph
    assert "-map" in command and "3:s:0?" in command
    assert "-c:s" in command and "mov_text" in command


def test_concat_file_quotes_paths(tmp_path):
    clip = tmp_path / "clip one.mp4"
    contents = concat_file_contents([clip])
    assert "ffconcat version 1.0" in contents
    assert "file '" in contents
    assert "clip one.mp4" in contents


def test_blackdetect_parser_extracts_segments():
    stderr = "black_start:0 black_end:0.25 black_duration:0.25\n"
    assert parse_blackdetect(stderr) == [{"start_seconds": 0.0, "end_seconds": 0.25, "duration_seconds": 0.25}]


import json
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from animation_studio.cli.main import app
from animation_studio.core.models import Episode, WorkflowStatus
from animation_studio.media.ffmpeg import extract_representative_frames, run_command
from animation_studio.media.qc import inspect_media, quality_report
from animation_studio.storage.files import dump_model, load_model

runner = CliRunner()


def test_project_and_episode_init_do_not_overwrite(tmp_path):
    result = runner.invoke(app, ["project", "init", str(tmp_path), "--title", "Test Film"])
    assert result.exit_code == 0, result.output
    assert (tmp_path / "project.yaml").is_file()
    before = (tmp_path / "project.yaml").read_text(encoding="utf-8")
    second = runner.invoke(app, ["project", "init", str(tmp_path), "--title", "Different"])
    assert second.exit_code != 0
    assert (tmp_path / "project.yaml").read_text(encoding="utf-8") == before
    episode = runner.invoke(app, ["episode", "init", "EP001", "--project-dir", str(tmp_path)])
    assert episode.exit_code == 0, episode.output


def test_storyboard_validate_reports_empty_episode(tmp_path):
    project = runner.invoke(app, ["project", "init", str(tmp_path)])
    assert project.exit_code == 0
    episode = runner.invoke(app, ["episode", "init", "EP001", "--project-dir", str(tmp_path)])
    assert episode.exit_code == 0
    result = runner.invoke(app, ["storyboard", "validate", str(tmp_path / "episodes" / "EP001" / "episode.yaml")])
    assert result.exit_code != 0
    assert "at least one shot" in result.output


def test_cli_generation_gate_requires_storyboard_approval_and_manual_submit_is_non_generating(tmp_path, make_shot):
    assert runner.invoke(app, ["project", "init", str(tmp_path), "--title", "Gate Test"]).exit_code == 0
    assert runner.invoke(app, ["episode", "init", "EP001", "--project-dir", str(tmp_path)]).exit_code == 0
    episode_path = tmp_path / "episodes" / "EP001" / "episode.yaml"
    episode = load_model(episode_path, Episode)
    episode = episode.model_copy(update={"shots": [make_shot()]})
    dump_model(episode, episode_path, overwrite=True)

    plan = runner.invoke(app, ["generation", "plan", str(episode_path), "--shot-id", "SHOT_001"])
    assert plan.exit_code == 0, plan.output
    manifest_path = next((episode_path.parent / "generation").glob("*.json"))
    approve_draft = runner.invoke(app, [
        "generation", "approve", str(manifest_path),
        "--usage-estimate", "1 request",
        "--budget-limit", "one request maximum",
        "--approved-by", "reviewer",
    ], input="y\n")
    assert approve_draft.exit_code != 0
    assert "must be marked APPROVED" in approve_draft.output

    approved_episode = episode.model_copy(update={
        "status": WorkflowStatus.APPROVED,
        "shots": [episode.shots[0].model_copy(update={"status": WorkflowStatus.APPROVED})],
    })
    dump_model(approved_episode, episode_path, overwrite=True)
    approve = runner.invoke(app, [
        "generation", "approve", str(manifest_path),
        "--usage-estimate", "1 request",
        "--budget-limit", "one request maximum",
        "--approved-by", "reviewer",
    ], input="y\n")
    assert approve.exit_code == 0, approve.output
    submit = runner.invoke(app, ["generation", "submit", str(manifest_path)], input="y\n")
    assert submit.exit_code == 0, submit.output
    queue_path = episode_path.parent / "generation" / "jobs.json"
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    assert queue["jobs"][0]["status"] == "awaiting_manual_media"
    assert "No video was created" in submit.output


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg tools are not installed")
def test_synthetic_local_video_inspection_frames_and_qc(tmp_path):
    source = tmp_path / "synthetic.mp4"
    run_command([
        shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-f", "lavfi",
        "-i", "testsrc=size=96x64:rate=12:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(source),
    ])
    summary = inspect_media(source)
    assert summary["duration_seconds"] > 0
    assert summary["width"] == 96 and summary["height"] == 64
    frames = extract_representative_frames(source, tmp_path / "frames")
    assert set(frames) == {"first", "middle", "last"}
    assert all(path.is_file() for path in frames.values())
    report = quality_report(source, expected_width=96, expected_height=64, expected_fps=12)
    assert report["status"] == "PASS"
    assert report["checks"]["decode_errors"]


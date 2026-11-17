import json
import hashlib
import shutil
import subprocess
from pathlib import Path

import pytest
from typer.testing import CliRunner

from animation_studio.cli.main import app
from animation_studio.core.models import ContinuityLedger, Episode, JobQueue, JobStatus, ProjectConfig, ShotJob, WorkflowStatus
from animation_studio.media.ffmpeg import extract_representative_frames, run_command
from animation_studio.media.qc import inspect_media, quality_report
from animation_studio.providers.base import ProviderError, ProviderTask
from animation_studio.services.manifest import approve_manifest, build_manifest
from animation_studio.storage.files import dump_model, load_model

runner = CliRunner()


def _remote_queue(tmp_path):
    assert runner.invoke(app, ["project", "init", str(tmp_path)]).exit_code == 0
    assert runner.invoke(app, ["episode", "init", "EP001", "--project-dir", str(tmp_path)]).exit_code == 0
    config_file = tmp_path / "project.yaml"
    config = load_model(config_file, ProjectConfig)
    experimental_provider = config.provider.model_copy(update={"mode": "muse2api_experimental"})
    dump_model(config.model_copy(update={"provider": experimental_provider}), config_file, overwrite=True)
    queue_file = tmp_path / "episodes" / "EP001" / "generation" / "jobs.json"
    dump_model(JobQueue(episode_id="EP001", jobs=[ShotJob(
        job_id="JOB-REMOTE-001",
        shot_id="SHOT_001",
        provider_mode="muse2api_experimental",
        status=JobStatus.QUEUED,
        task_id="TASK_001",
        prompt="Exact submitted prompt",
        request_parameters={"duration_seconds": 1, "aspect_ratio": "16:9"},
    )]), queue_file, overwrite=False)
    return queue_file


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


def test_continuity_update_resolves_project_relative_frames_from_project_root(tmp_path, monkeypatch, make_shot, state):
    project_root = tmp_path / "project"
    assert runner.invoke(app, ["project", "init", str(project_root)]).exit_code == 0
    assert runner.invoke(app, ["episode", "init", "EP001", "--project-dir", str(project_root)]).exit_code == 0

    episode_file = project_root / "episodes" / "EP001" / "episode.yaml"
    episode = load_model(episode_file, Episode).model_copy(update={"shots": [make_shot()]})
    dump_model(episode, episode_file, overwrite=True)
    frames_dir = project_root / "review_frames"
    frames_dir.mkdir()
    for frame_name in ("first", "middle", "last"):
        (frames_dir / f"{frame_name}.png").write_bytes(b"test-frame")
    state_file = project_root / "observed-end-state.json"
    dump_model(state, state_file, overwrite=False)

    monkeypatch.chdir(tmp_path)
    result = runner.invoke(app, [
        "continuity", "update", str(episode_file),
        "--shot-id", "SHOT_001",
        "--actual-end-state", str(state_file),
        "--frames-dir", "review_frames",
    ])

    assert result.exit_code == 0, result.output
    ledger = load_model(episode_file.parent / "continuity-ledger.yaml", ContinuityLedger)
    observation = ledger.observations[0]
    assert observation.status == "reviewed"
    assert observation.extracted_frames == {
        name: str(frames_dir / f"{name}.png") for name in ("first", "middle", "last")
    }


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

    queue_path = episode_path.parent / "generation" / "jobs.json"
    dump_model(JobQueue(episode_id="EP001", jobs=[ShotJob(
        job_id="JOB-FAILED-ATTEMPT",
        shot_id="SHOT_001",
        provider_mode="manual",
        status=JobStatus.FAILED,
        prompt="Previous failed prompt",
        error="previous attempt failed",
    )]), queue_path, overwrite=False)
    submit = runner.invoke(app, ["generation", "submit", str(manifest_path)], input="y\n")
    assert submit.exit_code == 0, submit.output
    queue = json.loads(queue_path.read_text(encoding="utf-8"))
    assert queue["jobs"][0]["status"] == "failed"
    assert queue["jobs"][1]["status"] == "awaiting_manual_media"
    assert "No video was created" in submit.output


def test_partial_manifest_is_rejected_before_any_request_or_status_change(tmp_path, make_shot, monkeypatch):
    assert runner.invoke(app, ["project", "init", str(tmp_path), "--title", "Partial Gate Test"]).exit_code == 0
    assert runner.invoke(app, ["episode", "init", "EP001", "--project-dir", str(tmp_path)]).exit_code == 0
    episode_file = tmp_path / "episodes" / "EP001" / "episode.yaml"
    first = make_shot()
    second = make_shot(shot_id="SHOT_002", order=2, continuity="C3", depends_on=["SHOT_001"])
    episode = load_model(episode_file, Episode).model_copy(update={
        "status": WorkflowStatus.APPROVED,
        "shots": [
            first.model_copy(update={"status": WorkflowStatus.APPROVED}),
            second.model_copy(update={"status": WorkflowStatus.APPROVED}),
        ],
    })
    dump_model(episode, episode_file, overwrite=True)
    config = load_model(tmp_path / "project.yaml", ProjectConfig)
    manifest = approve_manifest(
        build_manifest(episode, config),
        usage_estimate="2 requests",
        budget_limit="2 requests maximum",
        approved_by="reviewer",
    )
    manifest_file = episode_file.parent / "generation" / f"{manifest.manifest_id}.json"
    dump_model(manifest, manifest_file, overwrite=False)

    def provider_must_not_be_created(*args, **kwargs):
        raise AssertionError("provider should not be created for a partially eligible manifest")

    monkeypatch.setattr("animation_studio.cli.main._make_provider", provider_must_not_be_created)
    result = runner.invoke(app, ["generation", "submit", str(manifest_file)], input="y\n")

    assert result.exit_code != 0
    assert "only partially eligible (1 of 2)" in result.output
    assert "no request was sent" in result.output
    saved_manifest = load_model(manifest_file, type(manifest))
    assert saved_manifest.status == "APPROVED"
    assert not (episode_file.parent / "generation" / "jobs.json").exists()


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg tools are not installed")
def test_manual_media_import_records_provenance_and_review_updates_job_and_ledger(tmp_path, make_shot, state):
    assert runner.invoke(app, ["project", "init", str(tmp_path), "--title", "Import Test"]).exit_code == 0
    assert runner.invoke(app, ["episode", "init", "EP001", "--project-dir", str(tmp_path)]).exit_code == 0
    episode_file = tmp_path / "episodes" / "EP001" / "episode.yaml"
    episode = load_model(episode_file, Episode).model_copy(update={"shots": [make_shot()]})
    dump_model(episode, episode_file, overwrite=True)

    queue_file = episode_file.parent / "generation" / "jobs.json"
    queue = JobQueue(episode_id="EP001", jobs=[ShotJob(
        job_id="JOB-001",
        shot_id="SHOT_001",
        provider_mode="manual",
        status=JobStatus.AWAITING_MANUAL_MEDIA,
        prompt="Exact handoff prompt",
        request_parameters={"duration_seconds": 1, "aspect_ratio": "16:9"},
    )])
    dump_model(queue, queue_file, overwrite=False)
    ledger_file = episode_file.parent / "continuity-ledger.yaml"
    ledger_before = ledger_file.read_bytes() if ledger_file.exists() else None

    invalid_source = tmp_path / "invalid.mp4"
    invalid_source.write_bytes(b"not a video")
    invalid = runner.invoke(app, [
        "generation", "import-media", str(queue_file),
        "--shot-id", "SHOT_001", "--media-file", str(invalid_source),
    ])
    assert invalid.exit_code != 0
    assert "failed ffprobe inspection" in invalid.output
    assert load_model(queue_file, JobQueue).jobs[0].status == JobStatus.AWAITING_MANUAL_MEDIA

    source = tmp_path / "source-clip.mp4"
    run_command([
        shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-f", "lavfi",
        "-i", "testsrc=size=96x64:rate=12:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(source),
    ])
    result = runner.invoke(app, [
        "generation", "import-media", str(queue_file),
        "--shot-id", "SHOT_001", "--media-file", str(source),
        "--provider-model", "Muse Video v1",
    ])

    assert result.exit_code == 0, result.output
    imported = episode_file.parent / "clips" / "SHOT_001" / source.name
    assert imported.is_file() and source.is_file()
    saved_queue = load_model(queue_file, JobQueue)
    saved_job = saved_queue.jobs[0]
    assert saved_job.status == JobStatus.GENERATED
    assert saved_job.output_path == imported.relative_to(tmp_path).as_posix()
    assert saved_job.prompt == "Exact handoff prompt"
    assert saved_job.request_parameters == {"duration_seconds": 1, "aspect_ratio": "16:9"}
    assert saved_job.provider_model == "Muse Video v1"
    assert saved_job.source_media_name == source.name
    assert saved_job.media_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert saved_job.media_imported_at is not None and saved_job.completed_at is not None
    assert saved_job.media_metadata["duration_seconds"] > 0
    ledger_after = ledger_file.read_bytes() if ledger_file.exists() else None
    assert ledger_after == ledger_before

    frames_rel = Path("episodes/EP001/frames/SHOT_001")
    extract_representative_frames(imported, tmp_path / frames_rel)
    observed_state_file = tmp_path / "observed-end-state.yaml"
    dump_model(state, observed_state_file, overwrite=False)
    review = runner.invoke(app, [
        "continuity", "update", str(episode_file),
        "--shot-id", "SHOT_001",
        "--actual-end-state", str(observed_state_file),
        "--frames-dir", frames_rel.as_posix(),
    ])
    assert review.exit_code == 0, review.output
    saved_queue = load_model(queue_file, JobQueue)
    assert saved_queue.jobs[0].status == JobStatus.REVIEWED
    reviewed_ledger = load_model(ledger_file, ContinuityLedger)
    assert reviewed_ledger.observations[0].status == "reviewed"
    assert reviewed_ledger.observations[0].actual_end_state == state

    duplicate = runner.invoke(app, [
        "generation", "import-media", str(queue_file),
        "--shot-id", "SHOT_001", "--media-file", str(source),
    ])
    assert duplicate.exit_code != 0
    assert "must be awaiting manual media" in duplicate.output


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg tools are not installed")
def test_generation_status_downloads_completed_result_and_records_provenance(tmp_path, monkeypatch):
    queue_file = _remote_queue(tmp_path)
    source = tmp_path / "mock-provider-result.mp4"
    run_command([
        shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-f", "lavfi",
        "-i", "testsrc=size=96x64:rate=12:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(source),
    ])

    class CompletedProvider:
        def get_task(self, task_id):
            assert task_id == "TASK_001"
            return ProviderTask(task_id=task_id, status="completed", raw={"model": "mock-video-v1"})

        def download_result(self, task, destination):
            shutil.copyfile(source, destination)
            return destination

    provider = CompletedProvider()
    monkeypatch.setattr("animation_studio.cli.main._make_provider", lambda *args, **kwargs: provider)
    result = runner.invoke(app, ["generation", "status", str(queue_file), "--refresh"])

    assert result.exit_code == 0, result.output
    saved_job = load_model(queue_file, JobQueue).jobs[0]
    output = tmp_path / saved_job.output_path
    assert saved_job.status == JobStatus.GENERATED
    assert output.is_file()
    assert saved_job.provider_model == "mock-video-v1"
    assert saved_job.source_media_name == "TASK_001.mp4"
    assert saved_job.media_sha256 == hashlib.sha256(source.read_bytes()).hexdigest()
    assert saved_job.completed_at is not None
    assert saved_job.media_metadata["duration_seconds"] > 0
    assert saved_job.error is None


@pytest.mark.skipif(not shutil.which("ffmpeg") or not shutil.which("ffprobe"), reason="FFmpeg tools are not installed")
def test_generation_status_reuses_valid_task_scoped_file_without_overwrite(tmp_path, monkeypatch):
    queue_file = _remote_queue(tmp_path)
    destination = tmp_path / "episodes" / "EP001" / "clips" / "SHOT_001" / "TASK_001.mp4"
    destination.parent.mkdir(parents=True)
    run_command([
        shutil.which("ffmpeg"), "-hide_banner", "-loglevel", "error", "-f", "lavfi",
        "-i", "testsrc=size=96x64:rate=12:duration=1", "-c:v", "libx264", "-pix_fmt", "yuv420p", "-an", str(destination),
    ])

    class CompletedProvider:
        def get_task(self, task_id):
            return ProviderTask(task_id=task_id, status="completed", raw={"model": "mock-video-v1"})

        def download_result(self, task, target):
            raise AssertionError("existing task result must not be overwritten or downloaded again")

    provider = CompletedProvider()
    monkeypatch.setattr("animation_studio.cli.main._make_provider", lambda *args, **kwargs: provider)
    result = runner.invoke(app, ["generation", "status", str(queue_file), "--refresh"])

    assert result.exit_code == 0, result.output
    saved_job = load_model(queue_file, JobQueue).jobs[0]
    assert saved_job.status == JobStatus.GENERATED
    assert saved_job.output_path == destination.relative_to(tmp_path).as_posix()
    assert destination.is_file()


def test_generation_status_persists_download_failure_without_marking_generated(tmp_path, monkeypatch):
    queue_file = _remote_queue(tmp_path)

    class UnavailableProvider:
        def get_task(self, task_id):
            return ProviderTask(task_id=task_id, status="completed", raw={})

        def download_result(self, task, destination):
            raise ProviderError("media URL unavailable")

    provider = UnavailableProvider()
    monkeypatch.setattr("animation_studio.cli.main._make_provider", lambda *args, **kwargs: provider)
    result = runner.invoke(app, ["generation", "status", str(queue_file), "--refresh"])

    assert result.exit_code != 0
    assert "no resubmission was attempted" in result.output
    saved_job = load_model(queue_file, JobQueue).jobs[0]
    assert saved_job.status == JobStatus.QUEUED
    assert saved_job.output_path is None
    assert "media URL unavailable" in saved_job.error


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


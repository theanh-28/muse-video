import pytest

from animation_studio.core.models import (
    ContinuityLevel,
    Episode,
    JobStatus,
    ProjectConfig,
    ShotJob,
)
from animation_studio.services.jobs import JobTransitionError, transition_job
from animation_studio.services.manifest import (
    ManifestError,
    approve_manifest,
    build_manifest,
    ensure_approved_unchanged,
)


def test_job_state_transitions_allow_queue_and_completion():
    job = ShotJob(job_id="JOB-1", shot_id="SHOT_001", provider_mode="muse2api_experimental", prompt="p")
    queued = transition_job(job, JobStatus.QUEUED, task_id="task-1")
    running = transition_job(queued, JobStatus.RUNNING)
    completed = transition_job(running, JobStatus.GENERATED, output_path="media/SHOT_001.mp4")
    assert completed.status == JobStatus.GENERATED
    assert completed.task_id == "task-1"


def test_job_state_machine_rejects_skipping_from_planned_to_generated():
    job = ShotJob(job_id="JOB-1", shot_id="SHOT_001", provider_mode="manual", prompt="p")
    with pytest.raises(JobTransitionError, match="planned -> generated"):
        transition_job(job, JobStatus.GENERATED)


def test_failed_job_is_terminal():
    job = ShotJob(job_id="JOB-1", shot_id="SHOT_001", provider_mode="manual", prompt="p")
    failed = transition_job(job, JobStatus.FAILED, error="expired")
    with pytest.raises(JobTransitionError):
        transition_job(failed, JobStatus.QUEUED)


def test_manifest_requires_known_usage_and_budget(episode_factory):
    config = ProjectConfig(project={"id": "p", "title": "p", "language": "vi-VN", "genre": "short", "visual_style": "2D"})
    manifest = build_manifest(episode_factory(), config)
    with pytest.raises(ManifestError, match="known usage estimate"):
        approve_manifest(manifest, usage_estimate="unknown", budget_limit="$5", approved_by="user")
    with pytest.raises(ManifestError, match="budget limit"):
        approve_manifest(manifest, usage_estimate="1 clip; quota delta measured", budget_limit="", approved_by="user")


def test_approved_manifest_hash_detects_prompt_change(episode_factory):
    config = ProjectConfig(project={"id": "p", "title": "p", "language": "vi-VN", "genre": "short", "visual_style": "2D"})
    manifest = build_manifest(episode_factory(), config)
    approved = approve_manifest(
        manifest,
        usage_estimate="1 video request; 1 quota unit",
        budget_limit="1 quota unit maximum",
        approved_by="reviewer",
    )
    ensure_approved_unchanged(approved)
    changed = approved.model_copy(update={"requests": [approved.requests[0].model_copy(update={"prompt": "changed"})]})
    altered = [
        changed,
        approved.model_copy(update={"usage_estimate": "free"}),
        approved.model_copy(update={"budget_limit": "unlimited"}),
        approved.model_copy(update={"approved_by": "different reviewer"}),
        approved.model_copy(update={"approved_at": approved.approved_at.replace(year=approved.approved_at.year - 1)}),
    ]
    for item in altered:
        with pytest.raises(ManifestError, match="changed after approval"):
            ensure_approved_unchanged(item)


def test_manifest_only_includes_exact_requested_shot(episode_factory, make_shot):
    config = ProjectConfig(project={"id": "p", "title": "p", "language": "vi-VN", "genre": "short", "visual_style": "2D"})
    episode = episode_factory([make_shot("SHOT_001", 1), make_shot("SHOT_002", 2)])
    manifest = build_manifest(episode, config, selected_shot_id="SHOT_002")
    assert [item.shot_id for item in manifest.requests] == ["SHOT_002"]
    assert manifest.status == "DRAFT"
    assert manifest.smoke_test is False


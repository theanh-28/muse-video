from __future__ import annotations

import pytest

from animation_studio.core.workflow import ArtifactRevision, ProviderJobState, WorkflowState, content_hash
from animation_studio.studio.generation_safety import (
    GenerationSafetyError,
    approve_asset_generation,
    begin_asset_attempt,
    mark_submission_unknown,
    record_provider_task,
    recover_interrupted_attempts,
    verify_reference_hashes,
)
from animation_studio.studio.models import StudioBrief, StudioRun


def _approved_run() -> StudioRun:
    artifact = ArtifactRevision(artifact_id="appearance:FOX", revision=1, content_hash=content_hash({"fox": 1}))
    workflow = WorkflowState().append_revision(artifact)
    workflow = workflow.approve_current(
        artifact.artifact_id,
        expected_revision=artifact.revision,
        expected_hash=artifact.content_hash,
        approved_by="reviewer",
    )
    return StudioRun(
        run_id="a" * 12,
        status="SCRIPT_APPROVED",
        brief=StudioBrief(brief="A fox finds a letter and returns it to its owner."),
        workflow=workflow,
    )


def _approved_scope(run: StudioRun) -> StudioRun:
    artifact = run.workflow.current("appearance:FOX")
    assert artifact is not None
    return approve_asset_generation(
        run,
        operation_type="IMAGE",
        target_artifact_id=artifact.artifact_id,
        target_revision=artifact.revision,
        target_content_hash=artifact.content_hash,
        request_limit=1,
        approved_by="reviewer",
        usage_basis="One image task; provider credit data is UNKNOWN.",
        provider="muse2api",
        prompt="portrait",
        parameters={"model": "muse-image"},
    )


def test_attempt_is_reserved_before_submission_and_request_limit_is_enforced(tmp_path):
    run = _approved_scope(_approved_run())
    reference = tmp_path / "reference.png"
    reference.write_bytes(b"approved image bytes")
    expected_hash = content_hash({"wrong": "algorithm"})
    # Scope changes are rejected before an intent is reserved.
    with pytest.raises(GenerationSafetyError, match="reference bytes changed"):
        begin_asset_attempt(
            run,
            approval_id=run.asset_generation_approvals[0].approval_id,
            prompt="portrait",
            parameters={"model": "muse-image"},
            provider="muse2api",
            reference_hashes={reference: expected_hash},
        )

    import hashlib

    # This approval intentionally has no reference, so the request must match it.
    run = begin_asset_attempt(run, approval_id=run.asset_generation_approvals[0].approval_id,
        prompt="portrait", parameters={"model": "muse-image"}, provider="muse2api")
    assert run.asset_generation_approvals[0].reserved_requests == 1
    assert run.asset_generation_attempts[0].status == ProviderJobState.SUBMISSION_INTENDED
    with pytest.raises(GenerationSafetyError, match="request limit"):
        begin_asset_attempt(
            run,
            approval_id=run.asset_generation_approvals[0].approval_id,
            prompt="another portrait",
            parameters={"model": "muse-image"},
            provider="muse2api",
        )


def test_unknown_submission_blocks_blind_resubmission_and_task_id_persists():
    run = _approved_scope(_approved_run())
    run = begin_asset_attempt(
        run,
        approval_id=run.asset_generation_approvals[0].approval_id,
        prompt="portrait",
        parameters={"model": "muse-image"},
        provider="muse2api",
    )
    attempt_id = run.asset_generation_attempts[0].attempt_id
    unknown = mark_submission_unknown(run, attempt_id=attempt_id, error="POST timeout")
    assert unknown.asset_generation_attempts[0].status == ProviderJobState.SUBMISSION_UNKNOWN
    with pytest.raises(GenerationSafetyError, match="request limit"):
        begin_asset_attempt(
            unknown,
            approval_id=unknown.asset_generation_approvals[0].approval_id,
            prompt="portrait retry",
            parameters={"model": "muse-image"},
            provider="muse2api",
        )

    fresh = _approved_scope(_approved_run())
    fresh = begin_asset_attempt(
        fresh,
        approval_id=fresh.asset_generation_approvals[0].approval_id,
        prompt="portrait",
        parameters={"model": "muse-image"},
        provider="muse2api",
    )
    task = record_provider_task(fresh, attempt_id=fresh.asset_generation_attempts[0].attempt_id, provider_task_id="task-123")
    assert task.asset_generation_attempts[0].provider_task_id == "task-123"
    assert task.asset_generation_attempts[0].status == ProviderJobState.SUBMITTED


def test_stale_approval_and_restart_recovery_are_safe():
    run = _approved_scope(_approved_run())
    artifact = run.workflow.current("appearance:FOX")
    assert artifact is not None
    newer = ArtifactRevision(
        artifact_id=artifact.artifact_id,
        revision=2,
        content_hash=content_hash({"fox": 2}),
    )
    stale_run = run.model_copy(update={"workflow": run.workflow.append_revision(newer)})
    with pytest.raises(GenerationSafetyError, match="stale"):
        begin_asset_attempt(
            stale_run,
            approval_id=stale_run.asset_generation_approvals[0].approval_id,
            prompt="portrait",
            parameters={"model": "muse-image"},
            provider="muse2api",
        )

    valid = _approved_scope(_approved_run())
    valid = begin_asset_attempt(
        valid,
        approval_id=valid.asset_generation_approvals[0].approval_id,
        prompt="portrait",
        parameters={"model": "muse-image"},
        provider="muse2api",
    )
    recovered = recover_interrupted_attempts(valid)
    assert recovered.asset_generation_attempts[0].status == ProviderJobState.SUBMISSION_UNKNOWN

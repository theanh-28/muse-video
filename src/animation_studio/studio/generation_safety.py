"""Small, durable safety primitives for asset-generation requests.

These helpers deliberately do not submit provider requests.  A caller must save
the returned run while its run-mutation lock is held before it calls a provider.
"""
from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from animation_studio.core.workflow import ArtifactStatus, ProviderJobState
from animation_studio.studio.models import (
    AssetGenerationApproval,
    AssetGenerationAttempt,
    StudioRun,
)


class GenerationSafetyError(ValueError):
    """A request is not safely authorized to reach a provider."""


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def file_content_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def verify_reference_hashes(reference_hashes: dict[Path, str]) -> dict[str, str]:
    """Return normalized hashes after proving referenced bytes still match."""
    normalized: dict[str, str] = {}
    for path, expected_hash in reference_hashes.items():
        if not path.is_file():
            raise GenerationSafetyError(f"reference file is missing: {path}")
        actual_hash = file_content_hash(path)
        if actual_hash != expected_hash:
            raise GenerationSafetyError(f"reference bytes changed: {path}")
        normalized[str(path)] = actual_hash
    return normalized


def approve_asset_generation(
    run: StudioRun,
    *,
    operation_type: str,
    target_artifact_id: str,
    target_revision: int,
    target_content_hash: str,
    request_limit: int,
    approved_by: str,
    usage_basis: str,
) -> StudioRun:
    current = run.workflow.current(target_artifact_id)
    if current is None:
        raise GenerationSafetyError(f"target artifact does not exist: {target_artifact_id}")
    if current.status != ArtifactStatus.APPROVED:
        raise GenerationSafetyError("generation requires an approved current target artifact")
    if current.revision != target_revision or current.content_hash != target_content_hash:
        raise GenerationSafetyError("target artifact revision changed; reload before approving generation")
    approval = AssetGenerationApproval(
        approval_id=uuid4().hex,
        operation_type=operation_type,
        target_artifact_id=target_artifact_id,
        target_revision=target_revision,
        target_content_hash=target_content_hash,
        request_limit=request_limit,
        approved_by=approved_by,
        usage_basis=usage_basis,
    )
    return run.model_copy(update={
        "asset_generation_approvals": [*run.asset_generation_approvals, approval],
    })


def begin_asset_attempt(
    run: StudioRun,
    *,
    approval_id: str,
    prompt: str,
    parameters: dict[str, object],
    provider: str,
    reference_hashes: dict[Path, str] | None = None,
    allow_parallel: bool = False,
) -> StudioRun:
    """Reserve one request and persist an intent before the external POST."""
    approval = next((item for item in run.asset_generation_approvals if item.approval_id == approval_id), None)
    if approval is None:
        raise GenerationSafetyError("generation approval does not exist")
    current = run.workflow.current(approval.target_artifact_id)
    if (
        current is None
        or current.status != ArtifactStatus.APPROVED
        or current.revision != approval.target_revision
        or current.content_hash != approval.target_content_hash
    ):
        raise GenerationSafetyError("generation approval is stale")
    if approval.reserved_requests >= approval.request_limit:
        raise GenerationSafetyError("approved generation request limit is exhausted")
    if not allow_parallel and any(
        attempt.approval_id == approval_id
        and attempt.status in {ProviderJobState.SUBMISSION_INTENDED, ProviderJobState.SUBMISSION_UNKNOWN,
                               ProviderJobState.SUBMITTED, ProviderJobState.RUNNING}
        for attempt in run.asset_generation_attempts
    ):
        raise GenerationSafetyError("an unresolved generation attempt already exists for this approval")
    normalized_references = verify_reference_hashes(reference_hashes or {})
    reserved = approval.model_copy(update={"reserved_requests": approval.reserved_requests + 1})
    attempt = AssetGenerationAttempt(
        attempt_id=uuid4().hex,
        approval_id=approval.approval_id,
        operation_type=approval.operation_type,
        target_artifact_id=approval.target_artifact_id,
        target_revision=approval.target_revision,
        target_content_hash=approval.target_content_hash,
        prompt=prompt,
        parameters=parameters,
        provider=provider,
        reference_hashes=normalized_references,
    )
    return run.model_copy(update={
        "asset_generation_approvals": [reserved if item.approval_id == approval_id else item for item in run.asset_generation_approvals],
        "asset_generation_attempts": [*run.asset_generation_attempts, attempt],
    })


def record_provider_task(run: StudioRun, *, attempt_id: str, provider_task_id: str) -> StudioRun:
    if not provider_task_id.strip():
        raise GenerationSafetyError("provider task ID is required")
    return _replace_attempt(
        run,
        attempt_id,
        status=ProviderJobState.SUBMITTED,
        provider_task_id=provider_task_id,
        submitted_at=utcnow(),
        error=None,
    )


def mark_submission_unknown(run: StudioRun, *, attempt_id: str, error: str) -> StudioRun:
    """Preserve the reservation; callers must reconcile, never blind-retry."""
    return _replace_attempt(
        run,
        attempt_id,
        status=ProviderJobState.SUBMISSION_UNKNOWN,
        error=error[:2400],
    )


def recover_interrupted_attempts(run: StudioRun) -> StudioRun:
    """Turn only unsubmitted intents into an explicit reconciliation state."""
    attempts = [
        attempt.model_copy(update={
            "status": ProviderJobState.SUBMISSION_UNKNOWN,
            "error": "Studio restarted after submission intent; reconcile before retrying.",
        })
        if attempt.status == ProviderJobState.SUBMISSION_INTENDED else attempt
        for attempt in run.asset_generation_attempts
    ]
    return run.model_copy(update={"asset_generation_attempts": attempts})


def _replace_attempt(run: StudioRun, attempt_id: str, **updates: object) -> StudioRun:
    matches = [attempt for attempt in run.asset_generation_attempts if attempt.attempt_id == attempt_id]
    if len(matches) != 1:
        raise GenerationSafetyError("generation attempt record is inconsistent")
    current = matches[0]
    if current.status not in {ProviderJobState.SUBMISSION_INTENDED, ProviderJobState.SUBMISSION_UNKNOWN, ProviderJobState.RUNNING}:
        raise GenerationSafetyError("generation attempt cannot change submission state")
    updated = current.model_copy(update=updates)
    return run.model_copy(update={
        "asset_generation_attempts": [updated if attempt.attempt_id == attempt_id else attempt for attempt in run.asset_generation_attempts],
    })

"""Persisted Character Appearance preparation; provider submission stays opt-in."""
from __future__ import annotations

import hashlib
from pathlib import Path
from uuid import uuid4

from animation_studio.core.workflow import ArtifactDependency, ArtifactRevision, ArtifactStatus, StudioRunStatus, content_hash
from animation_studio.studio.generation_safety import approve_asset_generation, begin_asset_attempt
from animation_studio.studio.models import AppearanceCandidate, AppearanceSpec, StudioRun


class AppearanceError(ValueError):
    pass


def _script_identity(run: StudioRun) -> tuple[int, str]:
    if run.workflow.status != StudioRunStatus.SCRIPT_APPROVED or run.approved_script_revision is None:
        raise AppearanceError("approve the current script before preparing character appearance")
    artifact = run.workflow.current("script")
    if artifact is None or artifact.status != ArtifactStatus.APPROVED:
        raise AppearanceError("approved script artifact is missing")
    return artifact.revision, artifact.content_hash


def prepare_appearance_specs(run: StudioRun) -> StudioRun:
    script_revision, script_hash = _script_identity(run)
    script = run.script_revisions[script_revision - 1]
    existing = {spec.character_id: spec for spec in run.appearance_specs}
    workflow = run.workflow
    specs: list[AppearanceSpec] = list(run.appearance_specs)
    for character in script.characters:
        if not character.main or character.character_id in existing:
            continue
        description = f"{character.name}, {character.role}. Preserve a clear, distinctive silhouette and readable costume."
        spec = AppearanceSpec(
            character_id=character.character_id,
            character_name=character.name,
            source_script_revision=script_revision,
            source_script_hash=script_hash,
            revision=1,
            description=description,
            locked_attributes=[character.name, character.role],
        )
        artifact_id = f"appearance:{character.character_id}"
        workflow = workflow.append_revision(ArtifactRevision(
            artifact_id=artifact_id,
            revision=1,
            content_hash=content_hash(spec.model_dump(mode="json")),
            depends_on=[ArtifactDependency(artifact_id="script", revision=script_revision, content_hash=script_hash)],
        ))
        specs.append(spec)
    return run.model_copy(update={"workflow": workflow, "appearance_specs": specs, "status": StudioRunStatus.ASSET_PREPARATION})


def approve_appearance_spec(run: StudioRun, *, character_id: str, expected_revision: int, expected_hash: str, approved_by: str) -> StudioRun:
    artifact_id = f"appearance:{character_id}"
    workflow = run.workflow.approve_current(
        artifact_id, expected_revision=expected_revision, expected_hash=expected_hash, approved_by=approved_by
    )
    return run.model_copy(update={"workflow": workflow})


def prepare_candidate_attempts(run: StudioRun, *, character_id: str, approval_id: str, count: int = 3) -> StudioRun:
    if count < 1 or count > 12:
        raise AppearanceError("candidate request count must be between 1 and 12")
    spec = next((item for item in run.appearance_specs if item.character_id == character_id), None)
    if spec is None:
        raise AppearanceError("appearance specification does not exist")
    updated = run
    candidates = list(spec.candidates)
    for _ in range(count):
        updated = begin_asset_attempt(
            updated,
            approval_id=approval_id,
            prompt=spec.description,
            parameters={"model": "muse-image", "count": 1},
            provider="muse2api_experimental",
            allow_parallel=True,
        )
        attempt = updated.asset_generation_attempts[-1]
        candidates.append(AppearanceCandidate(candidate_id=uuid4().hex, attempt_id=attempt.attempt_id))
    changed_spec = spec.model_copy(update={"candidates": candidates})
    return updated.model_copy(update={
        "appearance_specs": [changed_spec if item.character_id == character_id else item for item in updated.appearance_specs],
    })


def approve_generation_scope(run: StudioRun, *, character_id: str, expected_revision: int, expected_hash: str, request_limit: int, approved_by: str) -> StudioRun:
    return approve_asset_generation(
        run,
        operation_type="IMAGE",
        target_artifact_id=f"appearance:{character_id}",
        target_revision=expected_revision,
        target_content_hash=expected_hash,
        request_limit=request_limit,
        approved_by=approved_by,
        usage_basis="Each Muse image candidate is one request; provider credits are UNKNOWN.",
    )


def select_candidate(run: StudioRun, *, character_id: str, candidate_id: str) -> StudioRun:
    spec = next((item for item in run.appearance_specs if item.character_id == character_id), None)
    if spec is None or not any(candidate.candidate_id == candidate_id for candidate in spec.candidates):
        raise AppearanceError("appearance candidate does not exist")
    changed = spec.model_copy(update={"selected_candidate_id": candidate_id})
    return run.model_copy(update={"appearance_specs": [changed if item.character_id == character_id else item for item in run.appearance_specs]})

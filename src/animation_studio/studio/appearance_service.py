"""Persisted Character Appearance preparation; provider submission stays opt-in."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path
from uuid import uuid4

from animation_studio.core.workflow import ArtifactDependency, ArtifactRevision, ArtifactStatus, StudioRunStatus, content_hash
from animation_studio.core.workflow import ProviderJobState
from animation_studio.studio.generation_safety import (
    approve_asset_generation, begin_asset_attempt, file_content_hash, mark_submission_unknown, record_provider_task,
)
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
    candidate = next((item for item in (spec.candidates if spec else []) if item.candidate_id == candidate_id), None)
    if candidate is None:
        raise AppearanceError("appearance candidate does not exist")
    if candidate.status != "COMPLETED" or not candidate.image_path or not candidate.content_hash:
        raise AppearanceError("only a completed candidate image can be selected")
    changed = spec.model_copy(update={"selected_candidate_id": candidate_id})
    return run.model_copy(update={"appearance_specs": [changed if item.character_id == character_id else item for item in run.appearance_specs]})


def record_submitted_candidate(run: StudioRun, *, attempt_id: str, provider_task_id: str) -> StudioRun:
    updated = record_provider_task(run, attempt_id=attempt_id, provider_task_id=provider_task_id)
    return _update_candidate_for_attempt(updated, attempt_id, provider_task_id=provider_task_id, status="SUBMITTED")


def record_unknown_candidate_submission(run: StudioRun, *, attempt_id: str, error: str) -> StudioRun:
    return mark_submission_unknown(run, attempt_id=attempt_id, error=error)


def attempt_for_submission(run: StudioRun, attempt_id: str):
    attempt = next((item for item in run.asset_generation_attempts if item.attempt_id == attempt_id), None)
    if attempt is None or attempt.status != ProviderJobState.SUBMISSION_INTENDED:
        raise AppearanceError("only a persisted submission intent may be sent")
    if attempt.operation_type != "IMAGE":
        raise AppearanceError("attempt is not an image request")
    return attempt


def complete_candidate_from_file(run: StudioRun, *, attempt_id: str, source: Path, assets_root: Path) -> StudioRun:
    attempt = next((item for item in run.asset_generation_attempts if item.attempt_id == attempt_id), None)
    if attempt is None or attempt.status not in {ProviderJobState.SUBMITTED, ProviderJobState.RUNNING}:
        raise AppearanceError("candidate attempt is not ready for a downloaded result")
    if not source.is_file() or source.stat().st_size == 0:
        raise AppearanceError("downloaded candidate image is missing or empty")
    header = source.read_bytes()[:12]
    if not (header.startswith(b"\x89PNG\r\n\x1a\n") or header.startswith(b"\xff\xd8\xff") or header[:6] in {b"GIF87a", b"GIF89a"}):
        raise AppearanceError("downloaded candidate is not a supported image")
    destination = assets_root / attempt.target_artifact_id.replace(":", "_") / f"{attempt_id}{source.suffix.lower() or '.png'}"
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        raise AppearanceError("refusing to overwrite an existing candidate image")
    shutil.copyfile(source, destination)
    relative = destination.relative_to(assets_root).as_posix()
    updated = _update_candidate_for_attempt(
        run, attempt_id, image_path=relative, content_hash=file_content_hash(destination), status="COMPLETED"
    )
    attempts = [item.model_copy(update={"status": ProviderJobState.SUCCEEDED, "output_paths": [relative]}) if item.attempt_id == attempt_id else item for item in updated.asset_generation_attempts]
    return updated.model_copy(update={"asset_generation_attempts": attempts})


def approve_selected_candidate(run: StudioRun, *, character_id: str, expected_hash: str, approved_by: str) -> StudioRun:
    spec = next((item for item in run.appearance_specs if item.character_id == character_id), None)
    candidate = next((item for item in (spec.candidates if spec else []) if item.candidate_id == spec.selected_candidate_id), None)
    if candidate is None or candidate.status != "COMPLETED" or candidate.content_hash != expected_hash:
        raise AppearanceError("selected candidate changed; reload before approving")
    reference_id = f"appearance-reference:{character_id}:{uuid4().hex[:12]}"
    changed_candidate = candidate.model_copy(update={"status": "APPROVED"})
    changed_spec = spec.model_copy(update={"approved_candidate_id": candidate.candidate_id, "approved_reference_artifact_id": reference_id,
        "candidates": [changed_candidate if item.candidate_id == candidate.candidate_id else item for item in spec.candidates]})
    artifact = ArtifactRevision(artifact_id=reference_id, revision=1, content_hash=candidate.content_hash, status=ArtifactStatus.DRAFT,
        depends_on=[ArtifactDependency(artifact_id=f"appearance:{character_id}", revision=spec.revision, content_hash=run.workflow.current(f"appearance:{character_id}").content_hash)])
    workflow = run.workflow.append_revision(artifact).approve_current(reference_id, expected_revision=1, expected_hash=candidate.content_hash, approved_by=approved_by)
    return run.model_copy(update={"workflow": workflow, "appearance_specs": [changed_spec if item.character_id == character_id else item for item in run.appearance_specs]})


def _update_candidate_for_attempt(run: StudioRun, attempt_id: str, **updates: object) -> StudioRun:
    changed = False; specs = []
    for spec in run.appearance_specs:
        candidates = []
        for candidate in spec.candidates:
            if candidate.attempt_id == attempt_id:
                candidates.append(candidate.model_copy(update=updates)); changed = True
            else: candidates.append(candidate)
        specs.append(spec.model_copy(update={"candidates": candidates}))
    if not changed: raise AppearanceError("candidate for attempt does not exist")
    return run.model_copy(update={"appearance_specs": specs})

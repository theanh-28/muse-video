from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from uuid import uuid4

from animation_studio.core.continuity import validate_episode_dependencies
from animation_studio.core.models import Episode, GenerationManifest, ManifestRequest, ProjectConfig


class ManifestError(ValueError):
    """A manifest is not safe to approve or submit."""


def build_manifest(
    episode: Episode,
    config: ProjectConfig,
    *,
    selected_shot_id: str | None = None,
) -> GenerationManifest:
    validate_episode_dependencies(episode)
    shots = sorted(episode.shots, key=lambda item: item.order)
    if selected_shot_id:
        selected = next((shot for shot in shots if shot.shot_id == selected_shot_id), None)
        if selected is None:
            raise ManifestError(f"Unknown shot: {selected_shot_id}")
        shots = [selected]
    requests = []
    for shot in shots:
        if not shot.prompt.strip():
            raise ManifestError(f"{shot.shot_id} has no built prompt")
        requests.append(ManifestRequest(
            shot_id=shot.shot_id,
            sequence_id=shot.sequence_id,
            order=shot.order,
            prompt=shot.prompt,
            duration_seconds=shot.planned_duration_seconds,
            aspect_ratio=episode.aspect_ratio,
            references=shot.references,
            depends_on=shot.depends_on,
            continuity_level=shot.continuity_level,
            required_capabilities=shot.provider_capabilities_required,
        ))
    return GenerationManifest(
        manifest_id=f"MAN-{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}",
        episode_id=episode.episode_id,
        provider_mode=config.provider.mode,
        # Selecting a shot limits the manifest; it does not authorize an
        # unverified provider smoke request. Only the explicit CLI flag may do so.
        smoke_test=False,
        requests=requests,
    )


def approval_fingerprint(manifest: GenerationManifest) -> str:
    body = {
        "manifest_version": manifest.manifest_version,
        "manifest_id": manifest.manifest_id,
        "created_at": manifest.created_at.isoformat(),
        "episode_id": manifest.episode_id,
        "provider_mode": manifest.provider_mode,
        "smoke_test": manifest.smoke_test,
        "requests": [item.model_dump(mode="json") for item in manifest.requests],
        "usage_estimate": manifest.usage_estimate,
        "budget_limit": manifest.budget_limit,
        "approved_by": manifest.approved_by,
        "approved_at": manifest.approved_at.isoformat() if manifest.approved_at else None,
    }
    encoded = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def approve_manifest(
    manifest: GenerationManifest,
    *,
    usage_estimate: str,
    budget_limit: str,
    approved_by: str,
) -> GenerationManifest:
    if not usage_estimate.strip() or "unknown" in usage_estimate.lower() or "unverified" in usage_estimate.lower():
        raise ManifestError("A known usage estimate/basis is required before approval")
    if not budget_limit.strip():
        raise ManifestError("A budget limit is required before approval")
    if not approved_by.strip():
        raise ManifestError("approved_by must identify the user who reviewed the manifest")
    approved = manifest.model_copy(update={
        "status": "APPROVED",
        "usage_estimate": usage_estimate.strip(),
        "budget_limit": budget_limit.strip(),
        "approved_by": approved_by.strip(),
        "approved_at": datetime.now(timezone.utc),
        "approved_request_hash": None,
    })
    return approved.model_copy(update={"approved_request_hash": approval_fingerprint(approved)})


def ensure_approved_unchanged(manifest: GenerationManifest) -> None:
    if manifest.status != "APPROVED":
        raise ManifestError("Manifest must be APPROVED before submit")
    if not manifest.usage_estimate or not manifest.budget_limit or not manifest.approved_by:
        raise ManifestError("Manifest is missing its usage, budget or approval record")
    if manifest.approved_request_hash != approval_fingerprint(manifest):
        raise ManifestError("Manifest or approval record changed after approval; plan and approve again")


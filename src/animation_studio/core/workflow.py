"""Versioned Studio workflow primitives.

These models deliberately keep run, artifact, approval, provider-job and QA state
separate.  They are persistence-friendly and do not submit provider requests.
"""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any

from pydantic import Field, model_validator

from animation_studio.core.models import StrictModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def content_hash(value: Any) -> str:
    """Return a stable hash for a JSON-compatible artifact payload."""
    encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


class StudioRunStatus(StrEnum):
    BRIEF_RECEIVED = "BRIEF_RECEIVED"
    SCRIPT_GENERATING = "SCRIPT_GENERATING"
    SCRIPT_REVIEW = "SCRIPT_REVIEW"
    SCRIPT_APPROVED = "SCRIPT_APPROVED"
    ASSET_PREPARATION = "ASSET_PREPARATION"
    ASSET_REVIEW = "ASSET_REVIEW"
    ASSETS_APPROVED = "ASSETS_APPROVED"
    NARRATION_PREPARATION = "NARRATION_PREPARATION"
    PLAN_GENERATING = "PLAN_GENERATING"
    PLAN_REVIEW = "PLAN_REVIEW"
    PLAN_APPROVED = "PLAN_APPROVED"
    PRODUCING = "PRODUCING"
    REVIEW_REQUIRED = "REVIEW_REQUIRED"
    ASSEMBLING = "ASSEMBLING"
    FINAL_QA = "FINAL_QA"
    EXPORTED = "EXPORTED"
    PAUSED = "PAUSED"
    FAILED = "FAILED"


class ArtifactStatus(StrEnum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    STALE = "STALE"
    SUPERSEDED = "SUPERSEDED"


class ApprovalStatus(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ProviderJobState(StrEnum):
    NOT_REQUESTED = "NOT_REQUESTED"
    SUBMISSION_INTENDED = "SUBMISSION_INTENDED"
    SUBMISSION_UNKNOWN = "SUBMISSION_UNKNOWN"
    SUBMITTED = "SUBMITTED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"


class QAStatus(StrEnum):
    NOT_RUN = "NOT_RUN"
    PASS = "PASS"
    FAIL = "FAIL"
    NEEDS_REVIEW = "NEEDS_REVIEW"
    NOT_APPLICABLE = "NOT_APPLICABLE"


_TRANSITIONS: dict[StudioRunStatus, set[StudioRunStatus]] = {
    StudioRunStatus.BRIEF_RECEIVED: {StudioRunStatus.SCRIPT_GENERATING, StudioRunStatus.PAUSED, StudioRunStatus.FAILED},
    StudioRunStatus.SCRIPT_GENERATING: {StudioRunStatus.BRIEF_RECEIVED, StudioRunStatus.SCRIPT_REVIEW, StudioRunStatus.SCRIPT_APPROVED, StudioRunStatus.PAUSED, StudioRunStatus.FAILED},
    StudioRunStatus.SCRIPT_REVIEW: {StudioRunStatus.SCRIPT_GENERATING, StudioRunStatus.SCRIPT_APPROVED, StudioRunStatus.PAUSED},
    StudioRunStatus.SCRIPT_APPROVED: {StudioRunStatus.SCRIPT_GENERATING, StudioRunStatus.SCRIPT_REVIEW, StudioRunStatus.ASSET_PREPARATION, StudioRunStatus.PAUSED},
    StudioRunStatus.ASSET_PREPARATION: {StudioRunStatus.ASSET_REVIEW, StudioRunStatus.PAUSED, StudioRunStatus.FAILED},
    StudioRunStatus.ASSET_REVIEW: {StudioRunStatus.ASSET_PREPARATION, StudioRunStatus.ASSETS_APPROVED, StudioRunStatus.PAUSED},
    StudioRunStatus.ASSETS_APPROVED: {StudioRunStatus.NARRATION_PREPARATION, StudioRunStatus.PLAN_GENERATING, StudioRunStatus.PAUSED},
    StudioRunStatus.NARRATION_PREPARATION: {StudioRunStatus.PLAN_GENERATING, StudioRunStatus.PAUSED, StudioRunStatus.FAILED},
    StudioRunStatus.PLAN_GENERATING: {StudioRunStatus.PLAN_REVIEW, StudioRunStatus.PAUSED, StudioRunStatus.FAILED},
    StudioRunStatus.PLAN_REVIEW: {StudioRunStatus.PLAN_GENERATING, StudioRunStatus.PLAN_APPROVED, StudioRunStatus.PAUSED},
    StudioRunStatus.PLAN_APPROVED: {StudioRunStatus.PRODUCING, StudioRunStatus.PAUSED},
    StudioRunStatus.PRODUCING: {StudioRunStatus.REVIEW_REQUIRED, StudioRunStatus.ASSEMBLING, StudioRunStatus.PAUSED, StudioRunStatus.FAILED},
    StudioRunStatus.REVIEW_REQUIRED: {StudioRunStatus.PRODUCING, StudioRunStatus.ASSEMBLING, StudioRunStatus.PAUSED},
    StudioRunStatus.ASSEMBLING: {StudioRunStatus.FINAL_QA, StudioRunStatus.PAUSED, StudioRunStatus.FAILED},
    StudioRunStatus.FINAL_QA: {StudioRunStatus.EXPORTED, StudioRunStatus.REVIEW_REQUIRED, StudioRunStatus.PAUSED, StudioRunStatus.FAILED},
    StudioRunStatus.PAUSED: set(StudioRunStatus) - {StudioRunStatus.EXPORTED},
    StudioRunStatus.FAILED: {StudioRunStatus.PAUSED},
    StudioRunStatus.EXPORTED: set(),
}


class ApprovalRecord(StrictModel):
    status: ApprovalStatus = ApprovalStatus.PENDING
    approved_by: str | None = None
    approved_at: datetime | None = None
    artifact_hash: str | None = None
    artifact_id: str | None = None
    revision: int | None = None

    @model_validator(mode="after")
    def approved_record_is_complete(self) -> "ApprovalRecord":
        if self.status == ApprovalStatus.APPROVED and not (
            self.approved_by and self.approved_at and self.artifact_hash and self.artifact_id and self.revision
        ):
            raise ValueError("approved records require approver, artifact ID, revision, timestamp, and artifact hash")
        return self


class ArtifactRevision(StrictModel):
    artifact_id: str = Field(min_length=1, max_length=120)
    revision: int = Field(ge=1)
    created_at: datetime = Field(default_factory=utcnow)
    content_hash: str = Field(min_length=64, max_length=64)
    status: ArtifactStatus = ArtifactStatus.DRAFT
    depends_on: list[str] = Field(default_factory=list)
    approval: ApprovalRecord = Field(default_factory=ApprovalRecord)


class WorkflowState(StrictModel):
    schema_version: int = 2
    status: StudioRunStatus = StudioRunStatus.BRIEF_RECEIVED
    artifacts: dict[str, list[ArtifactRevision]] = Field(default_factory=dict)

    def transition(self, target: StudioRunStatus) -> "WorkflowState":
        if target == self.status:
            return self
        if target not in _TRANSITIONS[self.status]:
            raise ValueError(f"Invalid studio workflow transition: {self.status} -> {target}")
        return self.model_copy(update={"status": target})

    def current(self, artifact_id: str) -> ArtifactRevision | None:
        revisions = self.artifacts.get(artifact_id, [])
        return revisions[-1] if revisions else None

    def append_revision(self, artifact: ArtifactRevision) -> "WorkflowState":
        revisions = list(self.artifacts.get(artifact.artifact_id, []))
        if revisions and artifact.revision != revisions[-1].revision + 1:
            raise ValueError("artifact revisions must increment by exactly one")
        if not revisions and artifact.revision != 1:
            raise ValueError("first artifact revision must be 1")
        if revisions and revisions[-1].status in {ArtifactStatus.DRAFT, ArtifactStatus.APPROVED}:
            revisions[-1] = revisions[-1].model_copy(update={"status": ArtifactStatus.SUPERSEDED})
        artifacts = dict(self.artifacts)
        artifacts[artifact.artifact_id] = [*revisions, artifact]
        return self.model_copy(update={"artifacts": artifacts})

    def stale_dependents(self, dependency_id: str) -> "WorkflowState":
        artifacts = {key: list(value) for key, value in self.artifacts.items()}
        for revisions in artifacts.values():
            current = revisions[-1] if revisions else None
            if current and dependency_id in current.depends_on and current.status == ArtifactStatus.APPROVED:
                revisions[-1] = current.model_copy(update={"status": ArtifactStatus.STALE})
        return self.model_copy(update={"artifacts": artifacts})

    def approve_current(
        self, artifact_id: str, *, expected_revision: int, expected_hash: str, approved_by: str
    ) -> "WorkflowState":
        """Approve exactly the revision the client reviewed; reject stale tabs."""
        current = self.current(artifact_id)
        if current is None:
            raise ValueError(f"artifact does not exist: {artifact_id}")
        if current.status != ArtifactStatus.DRAFT:
            raise ValueError("only a current DRAFT artifact can be approved")
        if current.revision != expected_revision or current.content_hash != expected_hash:
            raise ValueError("artifact revision changed; reload before approving")
        approved = current.model_copy(update={
            "status": ArtifactStatus.APPROVED,
            "approval": ApprovalRecord(
                status=ApprovalStatus.APPROVED, approved_by=approved_by, approved_at=utcnow(),
                artifact_hash=current.content_hash, artifact_id=artifact_id, revision=current.revision,
            ),
        })
        artifacts = dict(self.artifacts)
        artifacts[artifact_id] = [*artifacts[artifact_id][:-1], approved]
        return self.model_copy(update={"artifacts": artifacts})

from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from animation_studio.core.models import (
    CharacterBible,
    ContinuityLock,
    Costume,
    ContinuityLedger,
    Episode,
    ShotState,
    WorldBible,
)


class StudioBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: str = Field(min_length=20, max_length=8000)
    title_hint: str = Field(default="", max_length=160)
    audience: str = Field(default="Gia đình", max_length=240)
    genre: str = Field(default="Hoạt hình ngắn", max_length=240)
    visual_style: str = Field(default="", max_length=500)
    language: str = Field(default="vi-VN", min_length=2, max_length=20)
    episode_duration_seconds: int = Field(default=30, ge=20, le=180)
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "16:9"
    provider_mode: Literal["muse2api_experimental"] = "muse2api_experimental"

    @model_validator(mode="before")
    @classmethod
    def ignore_legacy_shot_count(cls, value):
        if isinstance(value, dict) and "shot_count" in value:
            value = dict(value)
            value.pop("shot_count")
        return value


class CharacterIdentityFact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str = Field(min_length=1, max_length=80)
    value: str = Field(min_length=1, max_length=500)


class CodexCharacter(BaseModel):
    """JSON-schema-friendly character draft, converted to the project Bible model."""

    model_config = ConfigDict(extra="forbid")

    character_id: str = Field(pattern=r"^[A-Z0-9_-]+$")
    canonical_name: str = Field(min_length=1, max_length=120)
    role: str = Field(default="", max_length=300)
    story_function: str = Field(default="", max_length=1000)
    identity_facts: list[CharacterIdentityFact] = Field(default_factory=list, max_length=24)
    continuity_locks: list[ContinuityLock] = Field(default_factory=list, max_length=20)
    costumes: list[Costume] = Field(default_factory=list, max_length=12)
    notes: list[str] = Field(default_factory=list, max_length=20)

    def to_bible(self) -> CharacterBible:
        return CharacterBible(
            character_id=self.character_id,
            canonical_name=self.canonical_name,
            role=self.role,
            story_function=self.story_function,
            immutable_identity={fact.key: fact.value for fact in self.identity_facts},
            continuity_locks=self.continuity_locks,
            costumes=self.costumes,
            notes=self.notes,
        )


class CreativePackage(BaseModel):
    """Schema-constrained Codex output; all creative material starts as DRAFT."""

    model_config = ConfigDict(extra="forbid")

    project_title: str = Field(min_length=1, max_length=160)
    genre: str = Field(min_length=1, max_length=240)
    visual_style: str = Field(min_length=1, max_length=500)
    logline: str = Field(min_length=1, max_length=1000)
    synopsis: str = Field(min_length=1, max_length=5000)
    project_bible_markdown: str = Field(min_length=1, max_length=12000)
    character_bibles: list[CodexCharacter] = Field(min_length=1, max_length=8)
    world_bible: WorldBible
    episode: Episode
    codex_notes: list[str] = Field(default_factory=list, max_length=20)


class ContinuityAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actual_end_state: ShotState
    reviewer_notes: list[str] = Field(default_factory=list, max_length=20)
    continuity_risks: list[str] = Field(default_factory=list, max_length=20)


class CreativeApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool


class GenerationPlanRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    shot_id: str = Field(pattern=r"^[A-Z0-9_-]+$")


class GenerationApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    usage_estimate: str = Field(min_length=8, max_length=1000)
    budget_limit: str = Field(min_length=3, max_length=1000)
    approved_by: str = Field(min_length=1, max_length=120)


class GenerationSubmitRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation: str = Field(min_length=8, max_length=200)


class ContinuityReviewAcceptRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool


class StudioRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    run_id: str
    status: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    brief: StudioBrief
    analysis: CreativePackage | None = None
    project_dir: str | None = None
    deferred_shots: list[str] = Field(default_factory=list)
    selected_shot_id: str | None = None
    manifest_path: str | None = None
    manifest_summary: dict[str, object] | None = None
    task_id: str | None = None
    media_path: str | None = None
    conformed_media_path: str | None = None
    frames_dir: str | None = None
    media_metadata: dict[str, object] | None = None
    source_qc_report: dict[str, object] | None = None
    qc_report: dict[str, object] | None = None
    export_path: str | None = None
    continuity_assessment: ContinuityAssessment | None = None
    next_shot_prompt: str | None = None
    error: str | None = None
    codex_usage: dict[str, int] | None = None

    @model_validator(mode="after")
    def keep_error_for_failed_runs(self) -> "StudioRun":
        if self.status == "FAILED" and not self.error:
            raise ValueError("failed studio runs must include an error")
        return self


class ContinuityReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ledger: ContinuityLedger
    next_shot_id: str | None = None

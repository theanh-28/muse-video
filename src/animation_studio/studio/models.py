from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal
from enum import StrEnum

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
from animation_studio.core.workflow import WorkflowState
from animation_studio.studio.scripts import ScriptPackage


class StudioBrief(BaseModel):
    model_config = ConfigDict(extra="forbid")

    brief: str = Field(min_length=20, max_length=8000)
    title_hint: str = Field(default="", max_length=160)
    audience: str = Field(default="Gia đình", max_length=240)
    genre: str = Field(default="Hoạt hình ngắn", max_length=240)
    visual_style: str = Field(default="", max_length=500)
    language: str = Field(default="en", min_length=2, max_length=20)
    episode_duration_seconds: int = Field(default=35, ge=5, le=180)
    aspect_ratio: Literal["16:9", "9:16", "1:1"] = "9:16"
    provider_mode: Literal["muse2api_experimental"] = "muse2api_experimental"
    autopilot: bool = False

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


class CodexPromptDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt: str = Field(min_length=40, max_length=20000)


class ContinuityAssessment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    actual_end_state: ShotState
    reviewer_notes: list[str] = Field(default_factory=list, max_length=20)
    continuity_risks: list[str] = Field(default_factory=list, max_length=20)


class YouTubeMetadataRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamped_transcript: str = Field(default="", max_length=100000)


class YouTubeTitleOption(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=100)
    thumbnail_text: str = Field(default="", max_length=60)
    rationale: str = Field(min_length=1, max_length=500)


class YouTubeThumbnailConcept(BaseModel):
    model_config = ConfigDict(extra="forbid")

    concept_id: str = Field(pattern=r"^[A-Z0-9_-]+$")
    focal_idea: str = Field(min_length=1, max_length=400)
    visual_elements: list[str] = Field(min_length=1, max_length=3)
    framing: str = Field(min_length=1, max_length=300)
    background_contrast: str = Field(min_length=1, max_length=300)
    overlay_text: str = Field(default="", max_length=80)
    emotion_or_hook: str = Field(min_length=1, max_length=240)
    image_prompt: str = Field(min_length=1, max_length=2000)
    recommendation: Literal["lead", "alternative", "reserve"]


class YouTubeChapterDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    timestamp: str = Field(min_length=4, max_length=8)
    title: str = Field(min_length=1, max_length=100)


class YouTubeMetadataDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    observed_facts: list[str] = Field(min_length=1, max_length=24)
    uncertainties: list[str] = Field(default_factory=list, max_length=24)
    topic_phrases: list[str] = Field(min_length=1, max_length=8)
    title_options: list[YouTubeTitleOption] = Field(min_length=10, max_length=10)
    selected_title: str = Field(min_length=1, max_length=100)
    thumbnail_concepts: list[YouTubeThumbnailConcept] = Field(min_length=3, max_length=3)
    description: str = Field(min_length=1, max_length=5000)
    tags: list[str] = Field(default_factory=list)
    hashtags: list[str] = Field(default_factory=list, max_length=60)
    chapters: list[YouTubeChapterDraft] = Field(default_factory=list, max_length=12)
    chapters_note: str = Field(min_length=1, max_length=1000)
    editorial_notes: list[str] = Field(default_factory=list, max_length=24)


class CreativeApproval(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirm: bool


class ScriptApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    approved_by: str = Field(min_length=1, max_length=120)
    expected_revision: int = Field(ge=1)
    expected_content_hash: str = Field(min_length=64, max_length=64)


class ScriptFeedbackRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    feedback: str = Field(min_length=1, max_length=4000)
    expected_revision: int = Field(ge=1)
    expected_content_hash: str = Field(min_length=64, max_length=64)


class AuthoringOperationStatus(StrEnum):
    STARTED = "STARTED"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    INTERRUPTED = "INTERRUPTED"


class AuthoringOperation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: str
    kind: Literal["INITIAL_SCRIPT", "SCRIPT_REVISION"]
    previous_status: str
    base_revision: int | None = None
    base_content_hash: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None
    status: AuthoringOperationStatus = AuthoringOperationStatus.STARTED
    result_revision: int | None = None
    error: str | None = None
    usage: dict[str, int] | None = None


class ScriptEditRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    script: ScriptPackage
    expected_revision: int = Field(ge=1)
    expected_content_hash: str = Field(min_length=64, max_length=64)


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
    workflow: WorkflowState = Field(default_factory=WorkflowState)
    script_revisions: list[ScriptPackage] = Field(default_factory=list)
    approved_script_revision: int | None = None
    authoring_operations: list[AuthoringOperation] = Field(default_factory=list)
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
    autopilot_stage: str | None = None
    autopilot_current_shot: str | None = None
    autopilot_shot_index: int = 0
    autopilot_shot_count: int = 0
    youtube_metadata_dir: str | None = None
    youtube_metadata_summary: dict[str, object] | None = None

    @model_validator(mode="after")
    def keep_error_for_failed_runs(self) -> "StudioRun":
        if self.status == "FAILED" and not self.error:
            raise ValueError("failed studio runs must include an error")
        return self


class ContinuityReviewRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ledger: ContinuityLedger
    next_shot_id: str | None = None

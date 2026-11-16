from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", use_enum_values=True)


class WorkflowStatus(StrEnum):
    PLAN = "PLAN"
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"
    GENERATING = "GENERATING"
    GENERATED = "GENERATED"
    QC_PASSED = "QC_PASSED"
    EXPORTED = "EXPORTED"


class ContinuityLevel(StrEnum):
    C0 = "C0"
    C1 = "C1"
    C2 = "C2"
    C3 = "C3"


class JobStatus(StrEnum):
    PLANNED = "planned"
    AWAITING_MANUAL_MEDIA = "awaiting_manual_media"
    QUEUED = "queued"
    RUNNING = "running"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    QC_PASSED = "qc_passed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ShotState(StrictModel):
    screen_position: str = Field(min_length=1)
    body_orientation: str = Field(min_length=1)
    eyeline: str = Field(min_length=1)
    pose_or_motion: str = Field(min_length=1)
    left_hand: str = "unspecified"
    right_hand: str = "unspecified"
    held_props: list[str] = Field(default_factory=list)
    costume_condition: str = "unspecified"
    injuries_or_marks: str = "none"
    environment: str = Field(min_length=1)
    prop_positions: list[str] = Field(default_factory=list)
    lighting: str = "unspecified"
    camera_state: str = Field(min_length=1)
    story_state: str = "unspecified"


class ActionBeat(StrictModel):
    beat: int = Field(ge=1)
    time_range: str = ""
    action: str = Field(min_length=1)
    camera_change: str = ""
    audio_cue: str = ""


class CameraSpec(StrictModel):
    shot_size: str = Field(min_length=1)
    angle: str = Field(min_length=1)
    movement: str = Field(min_length=1)
    lens_look: str = ""
    screen_direction: str = ""
    focus: str = ""


class AudioSpec(StrictModel):
    dialogue: list[str] = Field(default_factory=list)
    narration: str = ""
    sfx: list[str] = Field(default_factory=list)
    music: str = ""


class ReferenceSpec(StrictModel):
    path: str = Field(min_length=1)
    role: str = Field(min_length=1)
    governs: str = ""
    media_type: Literal["image", "video", "audio", "file"] = "image"


class Shot(StrictModel):
    shot_id: str = Field(pattern=r"^[A-Z0-9_-]+$")
    sequence_id: str = Field(min_length=1)
    order: int = Field(ge=1)
    planned_duration_seconds: float = Field(gt=0)
    continuity_level: ContinuityLevel
    status: WorkflowStatus = WorkflowStatus.DRAFT
    purpose: str = Field(min_length=1)
    characters_on_screen: list[str] = Field(default_factory=list)
    characters_off_screen: list[str] = Field(default_factory=list)
    start_state: ShotState
    action_beats: list[ActionBeat] = Field(min_length=1)
    end_state: ShotState
    camera: CameraSpec
    lighting: str = ""
    audio: AudioSpec = Field(default_factory=AudioSpec)
    references: list[ReferenceSpec] = Field(default_factory=list)
    reference_plan: str = Field(min_length=1)
    prompt: str = ""
    negative_constraints: list[str] = Field(default_factory=list)
    qa_checks: list[str] = Field(min_length=1)
    depends_on: list[str] = Field(default_factory=list)
    continuity_locks: list[str] = Field(default_factory=list)
    provider_capabilities_required: list[str] = Field(default_factory=list)

    @field_validator("action_beats")
    @classmethod
    def action_beats_are_ordered(cls, beats: list[ActionBeat]) -> list[ActionBeat]:
        numbers = [beat.beat for beat in beats]
        if numbers != sorted(numbers) or len(numbers) != len(set(numbers)):
            raise ValueError("action_beats must have unique, increasing beat numbers")
        return beats


class Episode(StrictModel):
    episode_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    title: str = Field(min_length=1)
    language: str = Field(min_length=2)
    visual_style: str = Field(min_length=1)
    aspect_ratio: str = "16:9"
    target_fps: int = Field(default=30, ge=1, le=120)
    status: WorkflowStatus = WorkflowStatus.DRAFT
    characters: list[str] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    shots: list[Shot] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_ids_and_orders(self) -> "Episode":
        ids = [shot.shot_id for shot in self.shots]
        orders = [shot.order for shot in self.shots]
        if len(ids) != len(set(ids)):
            raise ValueError("shot_id values must be unique")
        if len(orders) != len(set(orders)):
            raise ValueError("shot order values must be unique")
        return self


class ContinuityLock(StrictModel):
    lock_id: str = Field(min_length=1)
    category: str = Field(min_length=1)
    locked_phrase: str = Field(min_length=1)
    immutable: bool = True
    applies_to_shots: list[str] = Field(default_factory=list)


class Costume(StrictModel):
    costume_id: str = Field(min_length=1)
    description: str = Field(min_length=1)
    colors: list[str] = Field(default_factory=list)
    accessories: list[str] = Field(default_factory=list)
    applies_to_shots: list[str] = Field(default_factory=list)


class CharacterBible(StrictModel):
    character_id: str = Field(pattern=r"^[A-Z0-9_-]+$")
    canonical_name: str = Field(min_length=1)
    role: str = ""
    story_function: str = ""
    immutable_identity: dict[str, str | list[str]] = Field(default_factory=dict)
    continuity_locks: list[ContinuityLock] = Field(default_factory=list)
    costumes: list[Costume] = Field(default_factory=list)
    reference_assets: dict[str, str] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class LocationBible(StrictModel):
    location_id: str = Field(pattern=r"^[A-Z0-9_-]+$")
    canonical_name: str = Field(min_length=1)
    geography: str = ""
    fixed_landmarks: list[str] = Field(default_factory=list)
    time_of_day: str = ""
    weather: str = ""
    lighting_lock: str = ""
    palette_lock: str = ""
    reference_assets: list[str] = Field(default_factory=list)


class PropBible(StrictModel):
    prop_id: str = Field(pattern=r"^[A-Z0-9_-]+$")
    canonical_name: str = Field(min_length=1)
    appearance: str = ""
    initial_owner: str = ""
    state_rules: list[str] = Field(default_factory=list)
    reference_assets: list[str] = Field(default_factory=list)


class WorldBible(StrictModel):
    locations: list[LocationBible] = Field(default_factory=list)
    props: list[PropBible] = Field(default_factory=list)
    status: WorkflowStatus = WorkflowStatus.DRAFT


class ProjectOutput(StrictModel):
    aspect_ratio: str = "16:9"
    target_width: int = Field(default=1920, ge=1)
    target_height: int = Field(default=1080, ge=1)
    target_fps: int = Field(default=30, ge=1, le=120)
    container: str = "mp4"
    video_codec: str = "libx264"
    audio_codec: str = "aac"


class ProductionSettings(StrictModel):
    target_shot_duration_seconds: float = Field(default=10, gt=0)
    max_concurrent_jobs: int = Field(default=1, ge=1, le=1)
    max_retries: int = Field(default=1, ge=0, le=1)
    require_approval_before_generation: bool = True
    sequential_continuity_generation: bool = True


class ProviderSettings(StrictModel):
    mode: Literal["manual", "muse2api_experimental", "official_api"] = "manual"
    base_url: str = "http://127.0.0.1:18610/v1"
    api_key_env: str = "MUSE2API_API_KEY"
    verified_for_submission: bool = False
    supports_image_reference: bool | None = None
    supports_video_reference: bool | None = None
    supports_snapshot_continuation: bool | None = None
    max_duration_seconds: int | None = None


class ProjectPaths(StrictModel):
    projects_dir: str = "projects"
    output_dir: str = "output"


class ProjectConfig(StrictModel):
    project: dict[str, str]
    output: ProjectOutput = Field(default_factory=ProjectOutput)
    production: ProductionSettings = Field(default_factory=ProductionSettings)
    provider: ProviderSettings = Field(default_factory=ProviderSettings)
    paths: ProjectPaths = Field(default_factory=ProjectPaths)


class ManifestRequest(StrictModel):
    shot_id: str
    sequence_id: str
    order: int
    prompt: str = Field(min_length=1)
    duration_seconds: float = Field(gt=0)
    aspect_ratio: str
    references: list[ReferenceSpec] = Field(default_factory=list)
    depends_on: list[str] = Field(default_factory=list)
    continuity_level: ContinuityLevel
    required_capabilities: list[str] = Field(default_factory=list)


class GenerationManifest(StrictModel):
    manifest_version: int = 1
    manifest_id: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    episode_id: str
    provider_mode: Literal["manual", "muse2api_experimental", "official_api"]
    smoke_test: bool = False
    status: Literal["DRAFT", "APPROVED", "SUBMITTED"] = "DRAFT"
    requests: list[ManifestRequest] = Field(min_length=1)
    usage_estimate: str | None = None
    budget_limit: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    approved_request_hash: str | None = None


class ShotJob(StrictModel):
    job_id: str
    shot_id: str = Field(pattern=r"^[A-Z0-9_-]+$")
    provider_mode: str
    status: JobStatus = JobStatus.PLANNED
    task_id: str | None = None
    prompt: str
    request_parameters: dict[str, object] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: datetime | None = None
    output_path: str | None = None
    provider_model: str | None = None
    source_media_name: str | None = None
    media_sha256: str | None = None
    media_imported_at: datetime | None = None
    media_metadata: dict[str, object] | None = None
    error: str | None = None


class JobQueue(StrictModel):
    episode_id: str = Field(pattern=r"^[A-Za-z0-9_-]+$")
    jobs: list[ShotJob] = Field(default_factory=list)


class ContinuityEntry(StrictModel):
    shot_id: str
    status: Literal["not_generated", "generated", "reviewed", "qc_passed"] = "not_generated"
    actual_end_state: ShotState | None = None
    extracted_frames: dict[str, str | None] = Field(default_factory=lambda: {
        "first": None, "middle": None, "last": None,
    })
    continuity_risks: list[str] = Field(default_factory=list)
    reviewer_notes: list[str] = Field(default_factory=list)


class NextShotHandoff(StrictModel):
    required_reference_images: list[str] = Field(default_factory=list)
    required_locks: list[str] = Field(default_factory=list)
    action_must_continue_from: str = ""
    action_must_not_repeat: str = ""
    screen_direction: str = ""
    camera_handoff: str = ""


class ContinuityLedger(StrictModel):
    episode_id: str
    updated_at: datetime | None = None
    source_of_truth: str = "observed_media_over_storyboard_when_they_conflict"
    last_completed_shot_id: str | None = None
    observations: list[ContinuityEntry] = Field(default_factory=list)
    next_shot_handoff: NextShotHandoff = Field(default_factory=NextShotHandoff)


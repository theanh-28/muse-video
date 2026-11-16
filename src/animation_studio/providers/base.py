from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from animation_studio.core.models import ReferenceSpec


class ProviderError(RuntimeError):
    """Provider failure safe to persist in a project task record."""


class ProviderNotReady(ProviderError):
    """Provider is not enabled or its live behavior has not been verified."""


@dataclass(frozen=True)
class ProviderCapabilities:
    provider: str
    live_verified: bool = False
    supports_image_reference: bool | None = None
    supports_video_reference: bool | None = None
    supports_native_continuation: bool | None = None
    min_duration_seconds: int | None = None
    max_duration_seconds: int | None = None
    aspect_ratios: tuple[str, ...] = ()
    evidence: str = ""


@dataclass(frozen=True)
class VideoRequest:
    shot_id: str
    prompt: str
    duration_seconds: float
    aspect_ratio: str
    references: tuple[ReferenceSpec, ...] = ()
    parameters: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ProviderTask:
    task_id: str | None
    status: str
    raw: dict[str, Any] = field(default_factory=dict)


class VideoProvider(Protocol):
    def capabilities(self) -> ProviderCapabilities: ...

    def submit(self, request: VideoRequest) -> ProviderTask: ...

    def get_task(self, task_id: str) -> ProviderTask: ...

    def download_result(self, task: ProviderTask, destination: Path) -> Path: ...


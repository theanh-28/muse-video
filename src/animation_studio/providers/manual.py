from pathlib import Path

from animation_studio.providers.base import (
    ProviderCapabilities,
    ProviderNotReady,
    ProviderTask,
    VideoRequest,
)


class ManualProvider:
    """Offline handoff provider. It never opens Muse or submits a request."""

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="manual",
            evidence="Manual prompt and media handoff; Muse account capability is unknown.",
        )

    def submit(self, request: VideoRequest) -> ProviderTask:
        return ProviderTask(
            task_id=None,
            status="awaiting_manual_media",
            raw={"shot_id": request.shot_id, "submission": "manual_handoff_only"},
        )

    def get_task(self, task_id: str) -> ProviderTask:
        raise ProviderNotReady("ManualProvider has no remote task IDs to poll")

    def download_result(self, task: ProviderTask, destination: Path) -> Path:
        raise ProviderNotReady("Import the manually generated file with its project path")


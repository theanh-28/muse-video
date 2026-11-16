from __future__ import annotations

import base64
import ipaddress
import mimetypes
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

from animation_studio.providers.base import (
    ProviderCapabilities,
    ProviderError,
    ProviderNotReady,
    ProviderTask,
    VideoRequest,
)

MAX_REFERENCE_ITEMS = 10
MAX_REFERENCE_ITEM_BYTES = 40 * 1024 * 1024
MAX_REFERENCE_TOTAL_BYTES = 100 * 1024 * 1024
MAX_RESULT_BYTES = 2 * 1024 * 1024 * 1024
AUDITED_UPSTREAM_COMMIT = "19db32a3d6ef50dc87567a8ee0e35dd50c8f7837"


def _is_loopback(host: str | None) -> bool:
    if not host:
        return False
    if host.lower() == "localhost":
        return True
    try:
        return ipaddress.ip_address(host).is_loopback
    except ValueError:
        return False


class Muse2ApiProvider:
    """Experimental adapter for the local, unofficial Muse2API gateway.

    The adapter is disabled unless a caller explicitly enables submission. It
    never imports or stores Muse cookies; only the gateway's bearer key is read
    from the process environment.
    """

    def __init__(
        self,
        base_url: str,
        api_key: str | None = None,
        project_root: Path | None = None,
        submission_enabled: bool = False,
        timeout_seconds: float = 300,
        max_result_bytes: int = MAX_RESULT_BYTES,
    ) -> None:
        parsed = urlsplit(base_url.rstrip("/"))
        if parsed.scheme not in {"http", "https"} or not _is_loopback(parsed.hostname):
            raise ProviderNotReady("Muse2API must use a loopback-only HTTP(S) base URL")
        if not parsed.path.rstrip("/").endswith("/v1"):
            raise ProviderNotReady("Muse2API base URL must end with /v1")
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.getenv("MUSE2API_API_KEY") or os.getenv("MUSE2API_KEY")
        self.project_root = (project_root or Path.cwd()).resolve()
        self.submission_enabled = submission_enabled
        self.timeout_seconds = timeout_seconds
        self.max_result_bytes = max_result_bytes

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider="muse2api_experimental",
            live_verified=False,
            supports_image_reference=True,
            supports_video_reference=True,
            supports_native_continuation=False,
            min_duration_seconds=None,
            max_duration_seconds=None,
            aspect_ratios=(),
            evidence=(
                f"Static source audit at {AUDITED_UPSTREAM_COMMIT}: image/video reference fields "
                "exist; no enforced output-duration/aspect limits or native snapshot ID. "
                "Live account and generation behavior are unverified."
            ),
        )

    def _client(self):
        try:
            import httpx
        except ImportError as exc:  # pragma: no cover - environment-dependent
            raise ProviderNotReady("Install the optional 'http' dependency to use Muse2API") from exc
        if not self.api_key:
            raise ProviderNotReady("Set MUSE2API_API_KEY outside the project before use")
        return httpx.Client(
            timeout=self.timeout_seconds,
            follow_redirects=False,
            headers={"Authorization": f"Bearer {self.api_key}"},
        )

    def _reference_payload(self, request: VideoRequest) -> dict[str, list[dict[str, str]]]:
        if len(request.references) > MAX_REFERENCE_ITEMS:
            raise ProviderError(f"Too many reference files (max {MAX_REFERENCE_ITEMS})")
        refs: dict[str, list[dict[str, str]]] = {"images": [], "videos": []}
        total = 0
        for reference in request.references:
            source = (self.project_root / reference.path).resolve()
            if not source.is_relative_to(self.project_root):
                raise ProviderError(f"Reference path must stay inside the project: {reference.path}")
            if not source.is_file():
                raise ProviderError(f"Reference file not found: {reference.path}")
            size = source.stat().st_size
            total += size
            if size > MAX_REFERENCE_ITEM_BYTES:
                raise ProviderError(f"Reference file exceeds 40 MiB: {reference.path}")
            if total > MAX_REFERENCE_TOTAL_BYTES:
                raise ProviderError("Combined reference files exceed 100 MiB")
            mime, _ = mimetypes.guess_type(source.name)
            if not mime or not (mime.startswith("image/") or mime.startswith("video/")):
                raise ProviderError(f"Unsupported reference MIME type: {reference.path}")
            data_url = f"data:{mime};base64," + base64.b64encode(source.read_bytes()).decode("ascii")
            target = "videos" if reference.media_type == "video" else "images"
            refs[target].append({"url": data_url})
        return {name: values for name, values in refs.items() if values}

    def submit(self, request: VideoRequest) -> ProviderTask:
        if not self.submission_enabled:
            raise ProviderNotReady("Muse2API submission is disabled until an approved test/manifest enables it")
        if not self.api_key:
            raise ProviderNotReady("Set MUSE2API_API_KEY outside the project before use")
        if not request.prompt.strip():
            raise ProviderError("Prompt must not be empty")
        if int(request.duration_seconds) != request.duration_seconds:
            raise ProviderError("Muse2API duration must be an integer number of seconds")
        payload: dict[str, Any] = {
            "prompt": request.prompt,
            "duration": int(request.duration_seconds),
            "size": request.aspect_ratio,
        }
        payload.update(self._reference_payload(request))
        try:
            with self._client() as client:
                response = client.post(f"{self.base_url}/videos", json=payload)
        except Exception as exc:
            # A failed/uncertain POST is not retried: the gateway may have accepted it.
            raise ProviderError(f"Muse2API submission outcome is uncertain; do not resubmit automatically ({type(exc).__name__})") from exc
        if response.status_code in {401, 403}:
            raise ProviderError(f"Muse2API authentication/access failed with HTTP {response.status_code}; queue stopped")
        if response.status_code == 429:
            raise ProviderError("Muse2API returned HTTP 429; queue stopped without resubmission")
        if response.status_code >= 500:
            raise ProviderError(f"Muse2API returned HTTP {response.status_code}; queue stopped without resubmission")
        try:
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise ProviderError("Muse2API returned an invalid submission response") from exc
        task_id = data.get("id") or data.get("task_id")
        if not isinstance(task_id, str) or not task_id:
            raise ProviderError("Muse2API response did not contain a task ID")
        return ProviderTask(task_id=task_id, status=str(data.get("status", "queued")), raw=data)

    def get_task(self, task_id: str) -> ProviderTask:
        if not re.fullmatch(r"[A-Za-z0-9_-]+", task_id):
            raise ProviderError("Invalid task ID")
        try:
            with self._client() as client:
                response = client.get(f"{self.base_url}/videos/{task_id}")
        except Exception as exc:
            raise ProviderError(f"Muse2API task polling failed ({type(exc).__name__})") from exc
        if response.status_code in {401, 403}:
            raise ProviderError(f"Muse2API authentication/access failed with HTTP {response.status_code}; queue stopped")
        if response.status_code == 429:
            raise ProviderError("Muse2API returned HTTP 429 while polling")
        try:
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            raise ProviderError("Muse2API returned an invalid task response") from exc
        return ProviderTask(task_id=task_id, status=str(data.get("status", "unknown")), raw=data)

    def download_result(self, task: ProviderTask, destination: Path) -> Path:
        raw_url = task.raw.get("url")
        if not raw_url and isinstance(task.raw.get("result"), dict):
            raw_url = task.raw["result"].get("url")
        if not isinstance(raw_url, str) or not raw_url:
            raise ProviderError("Completed task does not contain a media URL")
        url = urljoin(self.base_url + "/", raw_url)
        configured = urlsplit(self.base_url)
        target = urlsplit(url)
        if (target.scheme, target.hostname, target.port) != (
            configured.scheme, configured.hostname, configured.port
        ):
            raise ProviderError("Refusing media download from a host other than the configured gateway")
        destination = destination.resolve()
        if destination.exists():
            raise ProviderError(f"Refusing to overwrite media: {destination}")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_name(destination.name + ".part")
        if temp.exists():
            raise ProviderError(f"Temporary download already exists: {temp}")
        written = 0
        try:
            with self._client() as client:
                with client.stream("GET", url) as response:
                    response.raise_for_status()
                    content_type = response.headers.get("content-type", "").split(";", 1)[0]
                    if content_type and not content_type.startswith("video/"):
                        raise ProviderError(f"Unexpected media MIME type: {content_type}")
                    with temp.open("xb") as stream:
                        for chunk in response.iter_bytes(1024 * 1024):
                            written += len(chunk)
                            if written > self.max_result_bytes:
                                raise ProviderError("Media download exceeded the configured size limit")
                            stream.write(chunk)
            if written == 0:
                raise ProviderError("Media download was empty")
            temp.replace(destination)
            return destination
        except Exception:
            if temp.exists():
                temp.unlink()
            raise


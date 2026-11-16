from pathlib import Path

import pytest
import httpx

from animation_studio.core.models import ReferenceSpec
from animation_studio.providers.base import ProviderNotReady, VideoRequest
from animation_studio.providers.manual import ManualProvider
from animation_studio.providers.muse2api import Muse2ApiProvider


def test_manual_provider_never_submits_to_network():
    provider = ManualProvider()
    result = provider.submit(VideoRequest("SHOT_001", "prompt", 10, "16:9"))
    assert result.status == "awaiting_manual_media"
    assert result.task_id is None


def test_muse_provider_rejects_public_gateway_url():
    with pytest.raises(ProviderNotReady, match="loopback-only"):
        Muse2ApiProvider("https://example.com/v1", api_key="key")


def test_muse_provider_defaults_to_submission_disabled():
    provider = Muse2ApiProvider("http://127.0.0.1:18610/v1", api_key="key")
    with pytest.raises(ProviderNotReady, match="submission is disabled"):
        provider.submit(VideoRequest("SHOT_001", "prompt", 5, "16:9"))


def test_muse_provider_encodes_local_reference_as_data_url(tmp_path):
    (tmp_path / "assets").mkdir()
    image_path = tmp_path / "assets" / "reference.png"
    image_path.write_bytes(b"synthetic image bytes")
    provider = Muse2ApiProvider("http://localhost:18610/v1", api_key="key", project_root=tmp_path)
    payload = provider._reference_payload(VideoRequest(
        "SHOT_001", "prompt", 5, "16:9",
        references=(ReferenceSpec(path="assets/reference.png", role="character", media_type="image"),),
    ))
    assert payload["images"][0]["url"].startswith("data:image/png;base64,")
    assert "videos" not in payload


def test_muse_provider_rejects_path_escape(tmp_path):
    outside = tmp_path.parent / "outside.png"
    outside.write_bytes(b"x")
    provider = Muse2ApiProvider("http://localhost:18610/v1", api_key="key", project_root=tmp_path)
    with pytest.raises(Exception, match="stay inside the project"):
        provider._reference_payload(VideoRequest(
            "SHOT_001", "prompt", 5, "16:9",
            references=(ReferenceSpec(path="../outside.png", role="reference"),),
        ))


def test_muse_task_id_rejects_path_injection():
    provider = Muse2ApiProvider("http://localhost:18610/v1", api_key="key")
    with pytest.raises(Exception, match="Invalid task ID"):
        provider.get_task("../../other")


def test_muse_submit_matches_audited_task_contract_without_network(monkeypatch):
    seen = {}

    def handler(request):
        seen["method"] = request.method
        seen["url"] = str(request.url)
        seen["payload"] = request.read().decode("utf-8")
        return httpx.Response(202, json={"id": "task-123", "status": "queued"})

    provider = Muse2ApiProvider("http://127.0.0.1:18610/v1", api_key="test-key", submission_enabled=True)
    monkeypatch.setattr(provider, "_client", lambda: httpx.Client(
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer test-key"},
    ))
    task = provider.submit(VideoRequest("SHOT_001", "A short test prompt", 5, "16:9"))
    assert task.task_id == "task-123"
    assert task.status == "queued"
    assert seen["method"] == "POST"
    assert seen["url"].endswith("/v1/videos")
    assert '"duration":5' in seen["payload"]
    assert '"size":"16:9"' in seen["payload"]


def test_muse_poll_and_download_use_same_gateway_origin(monkeypatch, tmp_path):
    def handler(request):
        if request.url.path.endswith("/task-123"):
            return httpx.Response(200, json={"id": "task-123", "status": "completed", "result": {"url": "http://localhost:18610/v1/media/out.mp4"}})
        if request.url.path.endswith("/out.mp4"):
            return httpx.Response(200, content=b"synthetic-mp4-bytes", headers={"content-type": "video/mp4"})
        return httpx.Response(404)

    provider = Muse2ApiProvider("http://localhost:18610/v1", api_key="test-key", submission_enabled=True)
    monkeypatch.setattr(provider, "_client", lambda: httpx.Client(
        transport=httpx.MockTransport(handler),
        headers={"Authorization": "Bearer test-key"},
    ))
    task = provider.get_task("task-123")
    assert task.status == "completed"
    output = provider.download_result(task, tmp_path / "media" / "shot.mp4")
    assert output.read_bytes() == b"synthetic-mp4-bytes"


def test_muse_download_refuses_other_origin(tmp_path):
    provider = Muse2ApiProvider("http://localhost:18610/v1", api_key="test-key", submission_enabled=True)
    task = type("Task", (), {"raw": {"url": "https://example.com/private.mp4"}})()
    with pytest.raises(Exception, match="other than the configured gateway"):
        provider.download_result(task, tmp_path / "out.mp4")


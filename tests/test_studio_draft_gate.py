import json

import pytest
from fastapi.testclient import TestClient

from animation_studio.studio import service, web_app
from animation_studio.studio.models import StudioBrief, StudioRun


@pytest.fixture
def draft_client(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(service, "STUDIO_PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(web_app, "STUDIO_PROJECTS_DIR", tmp_path / "projects")
    calls = {"analysis": 0, "autopilot": 0, "submit": 0}

    def analyze(run_id):
        calls["analysis"] += 1
        run = service.get_run(run_id)
        return service.save_run(run.model_copy(update={"status": "DRAFT_READY"}))

    async def autopilot(run_id):
        calls["autopilot"] += 1

    monkeypatch.setattr(web_app, "analyze_run", analyze)
    monkeypatch.setattr(web_app, "run_autopilot", autopilot)
    app = web_app.create_app()
    with TestClient(app, base_url="http://localhost") as client:
        client.headers["x-studio-token"] = app.state.session_token
        yield client, calls, tmp_path


@pytest.mark.parametrize("autopilot", [None, False])
def test_create_run_only_schedules_draft(draft_client, autopilot):
    client, calls, tmp_path = draft_client
    payload = {"brief": "A small fox finds a lost letter and returns it home."}
    if autopilot is not None:
        payload["autopilot"] = autopilot
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 200, response.text
    run_id = response.json()["run_id"]
    assert client.get(f"/api/runs/{run_id}").json()["status"] == "DRAFT_READY"
    assert calls == {"analysis": 1, "autopilot": 0, "submit": 0}
    assert len(list((tmp_path / "runs").glob("*.json"))) == 1


def test_autopilot_true_is_rejected_before_run_or_background_work(draft_client):
    client, calls, tmp_path = draft_client
    response = client.post("/api/runs", json={
        "brief": "A small fox finds a lost letter and returns it home.",
        "autopilot": True,
    })
    assert response.status_code == 422
    assert "duyệt kế hoạch" in response.json()["detail"]
    assert calls == {"analysis": 0, "autopilot": 0, "submit": 0}
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("legacy_autopilot", [None, True])
def test_legacy_run_remains_readable(draft_client, legacy_autopilot):
    client, calls, tmp_path = draft_client
    run = StudioRun(
        run_id="abcdef123456",
        status="SUBMITTED",
        brief=StudioBrief(brief="A small fox finds a lost letter and returns it home."),
        task_id="TASK-OLD",
    )
    record = run.model_dump(mode="json")
    if legacy_autopilot is None:
        record["brief"].pop("autopilot")
    else:
        record["brief"]["autopilot"] = True
    runs_dir = tmp_path / "runs"
    runs_dir.mkdir()
    (runs_dir / "abcdef123456.json").write_text(json.dumps(record), encoding="utf-8")
    response = client.get("/api/runs/abcdef123456")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "SUBMITTED"
    assert response.json()["task_id"] == "TASK-OLD"
    assert calls == {"analysis": 0, "autopilot": 0, "submit": 0}


def test_script_studio_asset_exposes_revision_bound_mutations(draft_client):
    client, _calls, _tmp_path = draft_client
    response = client.get("/assets/script-studio.js")
    assert response.status_code == 200
    assert "expected_revision" in response.text
    assert "expected_content_hash" in response.text
    assert "document.querySelectorAll('.script-actions button')" in response.text


def test_initial_script_retry_uses_existing_run(draft_client, monkeypatch):
    client, calls, _tmp_path = draft_client
    run = service.create_run(StudioBrief(brief="A small fox finds a lost letter and returns it home."))

    def retry(run_id):
        calls["analysis"] += 1
        return service.save_run(service.get_run(run_id).model_copy(update={"status": "SCRIPT_REVIEW"}))

    monkeypatch.setattr(web_app, "generate_script_run", retry)
    response = client.post(f"/api/runs/{run.run_id}/script/retry")
    assert response.status_code == 200, response.text
    assert response.json()["run_id"] == run.run_id
    assert calls["analysis"] == 1

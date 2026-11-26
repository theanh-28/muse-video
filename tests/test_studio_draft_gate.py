import json

import pytest
from fastapi.testclient import TestClient

from animation_studio.core.models import Episode, JobQueue, LocationBible, ProjectConfig, ShotJob, JobStatus, WorkflowStatus, WorldBible
from animation_studio.services.manifest import approve_manifest, build_manifest
from animation_studio.storage.files import dump_model, load_model
from animation_studio.studio import service, web_app
from animation_studio.studio.models import CodexCharacter, CreativePackage, StudioBrief, StudioRun


@pytest.fixture
def draft_setup(tmp_path, monkeypatch, make_shot):
    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(service, "STUDIO_PROJECTS_DIR", tmp_path / "projects")
    monkeypatch.setattr(web_app, "STUDIO_PROJECTS_DIR", tmp_path / "projects")
    shots = [make_shot(shot_id=f"SHOT_{index:03d}", order=index, prompt="") for index in range(1, 6)]
    package = CreativePackage(
        project_title="Lantern",
        genre="Family animation",
        visual_style="stylized 2D painted animation",
        logline="A keeper restores a lantern.",
        synopsis="The keeper notices a weak light and restores it.",
        project_bible_markdown="A quiet harbor story.",
        character_bibles=[CodexCharacter(character_id="CHAR_A", canonical_name="Keeper")],
        world_bible=WorldBible(locations=[LocationBible(location_id="LOC_A", canonical_name="Harbor")]),
        episode=Episode(
            episode_id="EP001", title="Lantern", language="vi-VN",
            visual_style="stylized 2D painted animation", aspect_ratio="16:9",
            characters=["CHAR_A"], locations=["LOC_A"], shots=shots,
        ),
    )
    calls = {"llm": 0, "approve": 0, "budget": 0, "send": 0}

    def llm(*args, **kwargs):
        calls["llm"] += 1
        return package, {"input_tokens": 1}

    def forbidden(name):
        def fail(*args, **kwargs):
            calls[name] += 1
            raise AssertionError(f"Unexpected {name}")
        return fail

    monkeypatch.setattr(service, "complete_structured", llm)
    monkeypatch.setattr(service, "approve_creative_plan", forbidden("approve"))
    monkeypatch.setattr(service, "approve_generation", forbidden("budget"))
    monkeypatch.setattr(service, "_invoke_cli", forbidden("send"))
    app = web_app.create_app()
    with TestClient(app, base_url="http://localhost") as client:
        client.headers["x-studio-token"] = app.state.session_token
        yield client, calls, package, tmp_path


@pytest.mark.parametrize("autopilot", [None, False])
def test_create_run_persists_real_draft(draft_setup, autopilot):
    client, calls, package, tmp_path = draft_setup
    payload = {"brief": "A harbor keeper notices a lantern fading and restores its light.",
               "episode_duration_seconds": 50}
    if autopilot is not None:
        payload["autopilot"] = autopilot
    response = client.post("/api/runs", json=payload)
    assert response.status_code == 200, response.text
    stored = client.get(f"/api/runs/{response.json()['run_id']}")
    assert stored.status_code == 200
    assert stored.json()["status"] == "DRAFT_READY"
    # Use the persisted project path, then verify it stays inside the temporary root.
    from pathlib import Path
    project = Path(stored.json()["project_dir"])
    assert project.is_relative_to(tmp_path / "projects")
    episode = load_model(project / "episodes/EP001/episode.yaml", Episode)
    assert episode.status == WorkflowStatus.DRAFT
    assert all(shot.status == WorkflowStatus.DRAFT for shot in episode.shots)
    assert episode.shots[0].action_beats[0].action == package.episode.shots[0].action_beats[0].action
    queue = load_model(project / "episodes/EP001/generation/jobs.json", JobQueue)
    assert queue.jobs == []
    assert not list((project / "episodes/EP001/generation").glob("MAN-*"))
    assert calls == {"llm": 1, "approve": 0, "budget": 0, "send": 0}


def test_autopilot_true_rejected_before_work(draft_setup):
    client, calls, _, tmp_path = draft_setup
    response = client.post("/api/runs", json={"brief": "A harbor keeper notices a lantern fading and restores its light.", "autopilot": True})
    assert response.status_code == 422
    assert "duyệt kế hoạch" in response.json()["detail"]
    assert calls == {"llm": 0, "approve": 0, "budget": 0, "send": 0}
    assert not (tmp_path / "runs").exists()


@pytest.mark.parametrize("mode", ["missing", "autopilot"])
def test_saved_run_read_does_not_start_work(draft_setup, mode):
    client, calls, _, tmp_path = draft_setup
    run = StudioRun(run_id="abcdef123456", status="SUBMITTED",
                    brief=StudioBrief(brief="A harbor keeper notices a lantern fading and restores its light."),
                    task_id="TASK-OLD")
    record = run.model_dump(mode="json")
    if mode == "missing":
        record["brief"].pop("autopilot")
    else:
        record["brief"]["autopilot"] = True
        record.update(autopilot_stage="polling_muse", autopilot_current_shot="SHOT_003",
                      autopilot_shot_index=3, autopilot_shot_count=5)
    folder = tmp_path / "runs"
    folder.mkdir()
    (folder / "abcdef123456.json").write_text(json.dumps(record), encoding="utf-8")
    response = client.get("/api/runs/abcdef123456")
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "SUBMITTED"
    assert response.json()["task_id"] == "TASK-OLD"
    if mode == "autopilot":
        assert response.json()["autopilot_stage"] == "polling_muse"
        assert response.json()["autopilot_shot_index"] == 3
    assert calls == {"llm": 0, "approve": 0, "budget": 0, "send": 0}


def test_studio_manual_submit_gates_and_sends_once(draft_setup, monkeypatch):
    client, calls, _, _ = draft_setup
    response = client.post("/api/runs", json={
        "brief": "A harbor keeper notices a lantern fading and restores its light.",
        "episode_duration_seconds": 50,
    })
    run_id = response.json()["run_id"]
    run = service.get_run(run_id)
    with pytest.raises(service.StudioWorkflowError, match="Approve the usage"):
        service.submit_generation(run_id, "SEND anything")
    from pathlib import Path
    root = Path(run.project_dir)
    episode = load_model(root / "episodes/EP001/episode.yaml", Episode)
    first = episode.shots[0].model_copy(update={"prompt": "The keeper watches the lantern flicker."})
    episode = episode.model_copy(update={"shots": [first, *episode.shots[1:]]})
    config = load_model(root / "project.yaml", ProjectConfig)
    manifest = approve_manifest(build_manifest(episode, config, selected_shot_id="SHOT_001"),
                                usage_estimate="one video request", budget_limit="one request", approved_by="Test user")
    manifest_path = root / "episodes/EP001/generation" / f"{manifest.manifest_id}.json"
    dump_model(manifest, manifest_path, overwrite=False)
    service.save_run(run.model_copy(update={"status": "MANIFEST_APPROVED", "manifest_path": str(manifest_path)}))
    with pytest.raises(service.StudioWorkflowError, match="exact confirmation"):
        service.submit_generation(run_id, "SEND wrong")
    changed = manifest.model_copy(update={"budget_limit": "two requests"})
    dump_model(changed, manifest_path, overwrite=True)
    with pytest.raises(ValueError, match="changed after approval"):
        service.submit_generation(run_id, f"SEND {manifest.manifest_id}")
    dump_model(manifest, manifest_path, overwrite=True)

    def fake_submit(*args, **kwargs):
        calls["send"] += 1
        queue_path = manifest_path.parent / "jobs.json"
        queue = load_model(queue_path, JobQueue)
        job = ShotJob(job_id="JOB-001", shot_id="SHOT_001", provider_mode="muse2api_experimental",
                      status=JobStatus.QUEUED, task_id="TASK-001", prompt=first.prompt)
        dump_model(queue.model_copy(update={"jobs": [job]}), queue_path, overwrite=True)
        return "submitted"

    monkeypatch.setattr(service, "_invoke_cli", fake_submit)
    submitted = service.submit_generation(run_id, f"SEND {manifest.manifest_id}")
    assert submitted.status == "SUBMITTED"
    assert submitted.task_id == "TASK-001"
    assert calls["send"] == 1

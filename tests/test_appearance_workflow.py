from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from animation_studio.core.workflow import StudioRunStatus
from animation_studio.studio import service
from animation_studio.studio import appearance_service
from animation_studio.providers.base import ProviderTask
from animation_studio.studio.models import StudioBrief
from animation_studio.studio import web_app
from animation_studio.studio.scripts import DialogueLine, ScreenPresence, ScriptCharacter, ScriptPackage, SpeakerType, SpeechSource, StoryBeat


def _script() -> ScriptPackage:
    return ScriptPackage(
        title="The Letter", logline="Friends return a letter.", story_intent="Kindness connects friends.",
        audience_takeaway="Small help matters.", setup="A fox finds a letter.", development="An otter joins.",
        payoff="The owner smiles.", ending="Friends walk home.",
        characters=[ScriptCharacter(character_id="FOX", name="Fox", role="hero", main=True)],
        story_beats=[StoryBeat(beat_id="BEAT_001", description="Find letter", visual_actions=["Letter visible"])],
        mandatory_visual_details=["sealed letter"],
        dialogue=[DialogueLine(line_id="LINE_001", speaker_id="FOX", exact_text="I found it.", language="en", emotion="warm", delivery_notes="gentle", speaker_type=SpeakerType.CHARACTER, speech_source=SpeechSource.MUSE, screen_presence=ScreenPresence.ON_SCREEN)],
        target_duration_seconds=35,
    )


def test_approved_script_prepares_two_main_appearance_specs_and_six_intents(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    package = _script()
    package = package.model_copy(update={"characters": [
        *package.characters,
        package.characters[0].model_copy(update={"character_id": "OTTER", "name": "Otter", "main": True}),
    ]})
    monkeypatch.setattr(service, "complete_structured", lambda _prompt, _model: (package, None))
    run = service.generate_script_run(service.create_run(StudioBrief(brief="A fox and an otter return a lost letter together.")).run_id)
    script = run.workflow.current("script")
    run = service.approve_script(run.run_id, approved_by="reviewer", expected_revision=script.revision, expected_content_hash=script.content_hash)
    prepared = service.prepare_appearance(run.run_id)
    assert prepared.status == StudioRunStatus.ASSET_PREPARATION
    assert {item.character_id for item in prepared.appearance_specs} == {"FOX", "OTTER"}
    for spec in prepared.appearance_specs:
        artifact = prepared.workflow.current(f"appearance:{spec.character_id}")
        prepared = service.approve_appearance_specification(
            prepared.run_id, character_id=spec.character_id, expected_revision=artifact.revision,
            expected_content_hash=artifact.content_hash, approved_by="reviewer",
        )
        prepared = service.approve_appearance_generation(
            prepared.run_id, character_id=spec.character_id, expected_revision=artifact.revision,
            expected_content_hash=artifact.content_hash, request_limit=3, approved_by="reviewer",
        )
    for spec in prepared.appearance_specs:
        approval = next(item for item in prepared.asset_generation_approvals if item.target_artifact_id == f"appearance:{spec.character_id}")
        prepared = service.prepare_appearance_candidates(prepared.run_id, character_id=spec.character_id, approval_id=approval.approval_id)
    assert len(prepared.asset_generation_attempts) == 6
    assert all(attempt.status == "SUBMISSION_INTENDED" for attempt in prepared.asset_generation_attempts)
    with pytest.raises(appearance_service.AppearanceError, match="completed candidate"):
        service.select_appearance_candidate(prepared.run_id, character_id="FOX", candidate_id=prepared.appearance_specs[0].candidates[0].candidate_id)
    assert len(prepared.asset_generation_attempts) == 6


def test_completed_image_can_be_selected_and_approved_as_immutable_reference(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    package = _script()
    monkeypatch.setattr(service, "complete_structured", lambda _prompt, _model: (package, None))
    run = service.generate_script_run(service.create_run(StudioBrief(brief="A fox returns a lost letter to its owner today.")).run_id)
    script = run.workflow.current("script")
    run = service.approve_script(run.run_id, approved_by="reviewer", expected_revision=script.revision, expected_content_hash=script.content_hash)
    run = service.prepare_appearance(run.run_id)
    artifact = run.workflow.current("appearance:FOX")
    run = service.approve_appearance_specification(run.run_id, character_id="FOX", expected_revision=artifact.revision, expected_content_hash=artifact.content_hash, approved_by="reviewer")
    run = service.approve_appearance_generation(run.run_id, character_id="FOX", expected_revision=artifact.revision, expected_content_hash=artifact.content_hash, request_limit=1, approved_by="reviewer")
    approval = run.asset_generation_approvals[0]
    run = service.prepare_appearance_candidates(run.run_id, character_id="FOX", approval_id=approval.approval_id, count=1)
    attempt = run.asset_generation_attempts[0]
    run = appearance_service.record_submitted_candidate(run, attempt_id=attempt.attempt_id, provider_task_id="mock-task")
    source = tmp_path / "mock.png"
    from PIL import Image
    Image.new("RGB", (2, 2), "red").save(source, format="PNG")
    run = appearance_service.complete_candidate_from_file(run, attempt_id=attempt.attempt_id, source=source, assets_root=tmp_path / "assets")
    candidate = run.appearance_specs[0].candidates[0]
    selected = appearance_service.select_candidate(run, character_id="FOX", candidate_id=candidate.candidate_id)
    approved = appearance_service.approve_selected_candidate(selected, character_id="FOX", expected_hash=candidate.content_hash, approved_by="reviewer")
    assert approved.appearance_specs[0].approved_candidate_id == candidate.candidate_id
    assert approved.workflow.current(approved.appearance_specs[0].approved_reference_artifact_id).content_hash == candidate.content_hash


def test_service_submits_existing_intent_with_its_stable_idempotency_key(tmp_path, monkeypatch):
    class MockProvider:
        def __init__(self): self.request = None
        def submit_image(self, request): self.request = request; return ProviderTask(task_id="mock-task", status="queued", raw={})
    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    package = _script(); monkeypatch.setattr(service, "complete_structured", lambda _p, _m: (package, None))
    run = service.generate_script_run(service.create_run(StudioBrief(brief="A fox returns a lost letter to its owner today.")).run_id)
    script = run.workflow.current("script"); run = service.approve_script(run.run_id, approved_by="r", expected_revision=script.revision, expected_content_hash=script.content_hash)
    run = service.prepare_appearance(run.run_id); artifact = run.workflow.current("appearance:FOX")
    run = service.approve_appearance_specification(run.run_id, character_id="FOX", expected_revision=artifact.revision, expected_content_hash=artifact.content_hash, approved_by="r")
    run = service.approve_appearance_generation(run.run_id, character_id="FOX", expected_revision=artifact.revision, expected_content_hash=artifact.content_hash, request_limit=1, approved_by="r")
    run = service.prepare_appearance_candidates(run.run_id, character_id="FOX", approval_id=run.asset_generation_approvals[0].approval_id, count=1)
    provider = MockProvider(); submitted = service.submit_appearance_candidate(run.run_id, attempt_id=run.asset_generation_attempts[0].attempt_id, provider=provider)
    assert provider.request.idempotency_key == run.asset_generation_attempts[0].attempt_id
    assert submitted.asset_generation_attempts[0].provider_task_id == "mock-task"


def test_two_character_six_intent_scopes_preserve_request_limits(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    package = _script().model_copy(update={"characters": [
        *_script().characters,
        _script().characters[0].model_copy(update={"character_id":"OTTER", "name":"Otter"}),
    ]})
    monkeypatch.setattr(service, "complete_structured", lambda _p, _m: (package, None))
    run = service.generate_script_run(service.create_run(StudioBrief(brief="A fox and otter return a lost letter to their owner.")).run_id)
    script=run.workflow.current("script"); run=service.approve_script(run.run_id,approved_by="r",expected_revision=script.revision,expected_content_hash=script.content_hash)
    run=service.prepare_appearance(run.run_id)
    for spec in run.appearance_specs:
        art=run.workflow.current(f"appearance:{spec.character_id}")
        run=service.approve_appearance_specification(run.run_id,character_id=spec.character_id,expected_revision=art.revision,expected_content_hash=art.content_hash,approved_by="r")
        run=service.approve_appearance_generation(run.run_id,character_id=spec.character_id,expected_revision=art.revision,expected_content_hash=art.content_hash,request_limit=3,approved_by="r")
    for approval in run.asset_generation_approvals:
        character_id=approval.target_artifact_id.split(":",1)[1]
        run=service.prepare_appearance_candidates(run.run_id,character_id=character_id,approval_id=approval.approval_id,count=3)
    assert len(run.asset_generation_attempts)==6
    assert all(item.reserved_requests==3 for item in run.asset_generation_approvals)


def test_editing_appearance_appends_revision_and_preserves_candidate_history(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    package = _script(); monkeypatch.setattr(service, "complete_structured", lambda _p, _m: (package, None))
    run = service.generate_script_run(service.create_run(StudioBrief(brief="A fox returns a lost letter to its owner today.")).run_id)
    script = run.workflow.current("script")
    run = service.approve_script(run.run_id, approved_by="r", expected_revision=script.revision, expected_content_hash=script.content_hash)
    run = service.prepare_appearance(run.run_id)
    artifact = run.workflow.current("appearance:FOX")
    revised = service.edit_appearance_specification(
        run.run_id, character_id="FOX", expected_revision=artifact.revision,
        expected_content_hash=artifact.content_hash, description="A small orange fox with a blue coat.",
        locked_attributes=["orange fur", "blue coat"],
    )
    current = revised.workflow.current("appearance:FOX")
    assert current.revision == 2 and current.status == "DRAFT"
    assert revised.appearance_specs[0].revision == 2
    assert revised.appearance_spec_history[0].revision == 1


def test_cross_character_scope_is_rejected_even_when_descriptions_match(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    package = _script().model_copy(update={"characters": [*_script().characters, _script().characters[0].model_copy(update={"character_id": "OTTER", "name": "Otter"})]})
    monkeypatch.setattr(service, "complete_structured", lambda _p, _m: (package, None))
    run = service.generate_script_run(service.create_run(StudioBrief(brief="A fox and an otter return a lost letter together.")).run_id)
    script = run.workflow.current("script"); run = service.approve_script(run.run_id, approved_by="r", expected_revision=script.revision, expected_content_hash=script.content_hash)
    run = service.prepare_appearance(run.run_id)
    # Identical descriptions must not make an approval portable across characters.
    fox, otter = run.appearance_specs
    run = run.model_copy(update={"appearance_specs": [fox.model_copy(update={"description": "same"}), otter.model_copy(update={"description": "same"})]})
    for spec in run.appearance_specs:
        art = run.workflow.current(f"appearance:{spec.character_id}")
        run = service.approve_appearance_specification(run.run_id, character_id=spec.character_id, expected_revision=art.revision, expected_content_hash=art.content_hash, approved_by="r")
    fox_art = run.workflow.current("appearance:FOX")
    run = service.approve_appearance_generation(run.run_id, character_id="FOX", expected_revision=fox_art.revision, expected_content_hash=fox_art.content_hash, request_limit=1, approved_by="r")
    with pytest.raises(appearance_service.AppearanceError, match="does not authorize"):
        appearance_service.prepare_candidate_attempts(run, character_id="OTTER", approval_id=run.asset_generation_approvals[0].approval_id, count=1)
    assert not run.asset_generation_attempts


def test_full_six_image_api_workflow_uses_claimed_persisted_intents(tmp_path, monkeypatch):
    class FakeImageProvider:
        def __init__(self): self.posts = []; self.polls = {}
        def submit_image(self, request):
            run = service.get_run(active_run[0])
            attempt = next(item for item in run.asset_generation_attempts if item.attempt_id == request.idempotency_key)
            assert attempt.status == "SUBMISSION_CLAIMED" and attempt.request_fingerprint
            self.posts.append(request); task_id = f"task-{len(self.posts)}"; self.polls[task_id] = 0
            return ProviderTask(task_id=task_id, status="queued", raw={})
        def get_image_task(self, task_id):
            self.polls[task_id] += 1
            return ProviderTask(task_id=task_id, status="running" if self.polls[task_id] == 1 else "completed", raw={"url": f"/media/{task_id}"})
        def download_image_result(self, task, destination):
            from PIL import Image
            Image.new("RGB", (4, 4), (len(self.posts) * 20 % 255, 20, 60)).save(destination, format="PNG")
            return destination

    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(web_app, "RUNS_DIR", tmp_path / "runs")
    package = _script().model_copy(update={"characters": [*_script().characters, _script().characters[0].model_copy(update={"character_id": "OTTER", "name": "Otter"})]})
    monkeypatch.setattr(service, "complete_structured", lambda _p, _m: (package, None))
    run = service.generate_script_run(service.create_run(StudioBrief(brief="A fox and an otter return a lost letter together.")).run_id)
    script = run.workflow.current("script"); run = service.approve_script(run.run_id, approved_by="r", expected_revision=script.revision, expected_content_hash=script.content_hash)
    active_run = [run.run_id]
    provider = FakeImageProvider(); app = web_app.create_app(); app.state.appearance_provider = provider
    with TestClient(app, base_url="http://localhost") as client:
        client.headers["x-studio-token"] = app.state.session_token
        response = client.post(f"/api/runs/{run.run_id}/appearance/prepare"); assert response.status_code == 200, response.text
        prepared_data = response.json()
        for spec in prepared_data["appearance_specs"]:
            art = prepared_data["workflow"]["artifacts"][f"appearance:{spec['character_id']}"][-1]
            response = client.post(f"/api/runs/{run.run_id}/appearance/specification/approve", json={"character_id": spec["character_id"], "expected_revision": art["revision"], "expected_content_hash": art["content_hash"], "approved_by":"r"}); assert response.status_code == 200, response.text
            response = client.post(f"/api/runs/{run.run_id}/appearance/generation/approve", json={"character_id": spec["character_id"], "expected_revision": art["revision"], "expected_content_hash": art["content_hash"], "request_limit":3, "approved_by":"r"}); assert response.status_code == 200, response.text
        run_data = client.get(f"/api/runs/{run.run_id}").json()
        for approval in run_data["asset_generation_approvals"]:
            char = approval["target_artifact_id"].split(":", 1)[1]
            response = client.post(f"/api/runs/{run.run_id}/appearance/candidates/prepare", json={"character_id":char, "approval_id":approval["approval_id"], "count":3}); assert response.status_code == 200, response.text
        run_data = client.get(f"/api/runs/{run.run_id}").json()
        assert len(run_data["asset_generation_attempts"]) == 6
        for attempt in run_data["asset_generation_attempts"]:
            response = client.post(f"/api/runs/{run.run_id}/appearance/submit", json={"attempt_id":attempt["attempt_id"]}); assert response.status_code == 200, response.text
            # Duplicate cannot reach the fake provider a second time.
            duplicate = client.post(f"/api/runs/{run.run_id}/appearance/submit", json={"attempt_id":attempt["attempt_id"]}); assert duplicate.status_code == 409
        assert len(provider.posts) == 6
        for attempt in client.get(f"/api/runs/{run.run_id}").json()["asset_generation_attempts"]:
            assert client.post(f"/api/runs/{run.run_id}/appearance/refresh", json={"attempt_id":attempt["attempt_id"]}).status_code == 200
            assert client.post(f"/api/runs/{run.run_id}/appearance/refresh", json={"attempt_id":attempt["attempt_id"]}).status_code == 200
        run_data = client.get(f"/api/runs/{run.run_id}").json()
        for spec in run_data["appearance_specs"]:
            candidate = next(item for item in spec["candidates"] if item["status"] == "COMPLETED")
            assert client.get(f"/api/runs/{run.run_id}/appearance-image/{candidate['candidate_id']}").status_code == 200
            assert client.post(f"/api/runs/{run.run_id}/appearance/candidate/select", json={"character_id":spec["character_id"], "candidate_id":candidate["candidate_id"]}).status_code == 200
            assert client.post(f"/api/runs/{run.run_id}/appearance/reference/approve", json={"character_id":spec["character_id"], "expected_content_hash":candidate["content_hash"], "approved_by":"r"}).status_code == 200
    persisted = service.get_run(run.run_id)
    assert len(provider.posts) == 6
    for spec in persisted.appearance_specs:
        approved = persisted.workflow.current(spec.approved_reference_artifact_id)
        assert approved and approved.depends_on[0].artifact_id == f"appearance:{spec.character_id}"

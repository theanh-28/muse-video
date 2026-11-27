from __future__ import annotations

import pytest
from animation_studio.core.workflow import StudioRunStatus
from animation_studio.studio import service
from animation_studio.studio import appearance_service
from animation_studio.studio.models import StudioBrief
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
    source.write_bytes(b"\x89PNG\r\n\x1a\n" + b"synthetic image")
    run = appearance_service.complete_candidate_from_file(run, attempt_id=attempt.attempt_id, source=source, assets_root=tmp_path / "assets")
    candidate = run.appearance_specs[0].candidates[0]
    selected = appearance_service.select_candidate(run, character_id="FOX", candidate_id=candidate.candidate_id)
    approved = appearance_service.approve_selected_candidate(selected, character_id="FOX", expected_hash=candidate.content_hash, approved_by="reviewer")
    assert approved.appearance_specs[0].approved_candidate_id == candidate.candidate_id
    assert approved.workflow.current(approved.appearance_specs[0].approved_reference_artifact_id).content_hash == candidate.content_hash

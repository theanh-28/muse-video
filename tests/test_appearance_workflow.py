from __future__ import annotations

from animation_studio.core.workflow import StudioRunStatus
from animation_studio.studio import service
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
    selected = service.select_appearance_candidate(prepared.run_id, character_id="FOX", candidate_id=prepared.appearance_specs[0].candidates[0].candidate_id)
    assert selected.appearance_specs[0].selected_candidate_id == prepared.appearance_specs[0].candidates[0].candidate_id
    assert len(selected.asset_generation_attempts) == 6

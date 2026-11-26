from __future__ import annotations

import pytest

from animation_studio.core.workflow import ArtifactRevision, ArtifactStatus, StudioRunStatus, WorkflowState, content_hash
from animation_studio.studio import service
from animation_studio.studio.models import StudioBrief
from animation_studio.studio.scripts import (
    DialogueLine,
    ScreenPresence,
    ScriptCharacter,
    ScriptPackage,
    SpeakerType,
    SpeechSource,
    StoryBeat,
)


def _script(text: str = "The fox waves.") -> ScriptPackage:
    return ScriptPackage(
        title="The Letter",
        logline="A fox returns a letter.",
        story_intent="Kindness creates connection.",
        audience_takeaway="Small help matters.",
        setup="A fox finds a letter.",
        development="The fox follows the address.",
        payoff="The recipient recognizes the sender.",
        ending="The fox walks home smiling.",
        characters=[ScriptCharacter(character_id="FOX", name="Fox", role="hero", main=True)],
        story_beats=[StoryBeat(beat_id="BEAT_001", description="Fox finds letter", visual_actions=["The letter is visible."])],
        mandatory_visual_details=["A sealed letter"],
        dialogue=[DialogueLine(
            line_id="LINE_001", speaker_id="FOX", exact_text=text, language="en",
            emotion="warm", delivery_notes="gentle", speaker_type=SpeakerType.CHARACTER,
            speech_source=SpeechSource.MUSE, screen_presence=ScreenPresence.ON_SCREEN,
        )],
        target_duration_seconds=35,
    )


def test_workflow_rejects_invalid_transition_and_versions_artifacts():
    state = WorkflowState()
    with pytest.raises(ValueError, match="Invalid studio workflow transition"):
        state.transition(StudioRunStatus.PLAN_REVIEW)
    first = ArtifactRevision(artifact_id="script", revision=1, content_hash=content_hash({"v": 1}))
    second = ArtifactRevision(artifact_id="script", revision=2, content_hash=content_hash({"v": 2}))
    revised = state.append_revision(first).append_revision(second)
    assert revised.artifacts["script"][0].status == ArtifactStatus.SUPERSEDED
    assert revised.current("script").revision == 2


def test_narrator_contract_rejects_muse_or_screen_presence():
    with pytest.raises(ValueError, match="narration must use KOKORO"):
        DialogueLine(
            line_id="LINE_001", speaker_id="NARRATOR", exact_text="Once upon a time.", language="en",
            emotion="calm", delivery_notes="even", speaker_type=SpeakerType.NARRATOR,
            speech_source=SpeechSource.MUSE, screen_presence=ScreenPresence.ON_SCREEN,
        )


def test_script_revision_and_approval_are_persisted_without_overwrite(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    run = service.create_run(StudioBrief(brief="A fox returns a lost letter to its owner."))
    # A new run must enter script generation first; fixture provider is used only for this test.
    monkeypatch.setattr(service, "complete_structured", lambda _prompt, _model: (_script(), {"input_tokens": 1}))
    drafted = service.generate_script_run(run.run_id)
    assert drafted.status == StudioRunStatus.SCRIPT_REVIEW
    current = drafted.workflow.current("script")
    revised = service.revise_script(
        run.run_id, _script("I found your letter."), expected_revision=current.revision,
        expected_content_hash=current.content_hash,
    )
    assert len(revised.script_revisions) == 2
    assert revised.workflow.artifacts["script"][0].status == ArtifactStatus.SUPERSEDED
    current = revised.workflow.current("script")
    approved = service.approve_script(
        run.run_id, approved_by="reviewer", expected_revision=current.revision, expected_content_hash=current.content_hash
    )
    assert approved.status == StudioRunStatus.SCRIPT_APPROVED
    assert approved.workflow.current("script").approval.artifact_hash
    restored = service.get_run(run.run_id)
    assert restored.approved_script_revision == 2
    with pytest.raises(service.StudioWorkflowError):
        service.approve_script(
            run.run_id, approved_by="reviewer", expected_revision=current.revision, expected_content_hash=current.content_hash
        )


def test_stale_script_client_cannot_save_or_approve(tmp_path, monkeypatch):
    monkeypatch.setattr(service, "RUNS_DIR", tmp_path / "runs")
    monkeypatch.setattr(service, "complete_structured", lambda _prompt, _model: (_script(), None))
    run = service.generate_script_run(service.create_run(StudioBrief(brief="A fox returns a lost letter to its owner.")).run_id)
    stale = run.workflow.current("script")
    service.revise_script(run.run_id, _script("A newer script."), expected_revision=stale.revision, expected_content_hash=stale.content_hash)
    with pytest.raises(service.StudioWorkflowError, match="changed"):
        service.approve_script(run.run_id, approved_by="reviewer", expected_revision=stale.revision, expected_content_hash=stale.content_hash)

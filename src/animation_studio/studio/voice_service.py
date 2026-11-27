"""Revisioned Muse character-voice preparation; media submission stays in the shared safety lifecycle."""
from __future__ import annotations

from animation_studio.core.workflow import ArtifactDependency, ArtifactRevision, ArtifactStatus, StudioRunStatus, content_hash
from animation_studio.studio.models import MuseVoiceProfile, StudioRun
from animation_studio.studio.scripts import SpeakerType, SpeechSource


class VoiceError(ValueError):
    pass


def _approved_script(run: StudioRun):
    script = run.workflow.current("script")
    if (
        run.workflow.status not in {StudioRunStatus.ASSET_PREPARATION, StudioRunStatus.ASSET_REVIEW}
        or run.approved_script_revision is None
        or script is None
        or script.status != ArtifactStatus.APPROVED
    ):
        raise VoiceError("approve the current script before preparing character voices")
    return script, run.script_revisions[script.revision - 1]


def required_muse_speakers(run: StudioRun) -> set[str]:
    _script_artifact, script = _approved_script(run)
    return {
        line.speaker_id for line in script.dialogue
        if line.speaker_type == SpeakerType.CHARACTER and line.speech_source == SpeechSource.MUSE
    }


def prepare_muse_voice_profiles(run: StudioRun) -> StudioRun:
    script_artifact, script = _approved_script(run)
    existing = {profile.character_id for profile in run.muse_voice_profiles}
    characters = {character.character_id: character for character in script.characters}
    profiles = list(run.muse_voice_profiles)
    workflow = run.workflow
    for speaker_id in required_muse_speakers(run):
        if speaker_id in existing:
            continue
        character = characters[speaker_id]
        lines = [line for line in script.dialogue if line.speaker_id == speaker_id and line.speech_source == SpeechSource.MUSE]
        language = lines[0].language
        reference_id = next((spec.approved_reference_artifact_id for spec in run.appearance_specs if spec.character_id == speaker_id), None)
        profile = MuseVoiceProfile(
            character_id=speaker_id, character_name=character.name, revision=1, language=language,
            canonical_voice_description=f"Natural {language} voice for {character.name}; clear articulation and relaxed pacing.",
            source_script_revision=script_artifact.revision, source_script_hash=script_artifact.content_hash,
            appearance_reference_artifact_id=reference_id,
        )
        dependencies = [ArtifactDependency(artifact_id="script", revision=script_artifact.revision, content_hash=script_artifact.content_hash)]
        if reference_id:
            reference = workflow.current(reference_id)
            if reference and reference.status == ArtifactStatus.APPROVED:
                dependencies.append(ArtifactDependency(artifact_id=reference_id, revision=reference.revision, content_hash=reference.content_hash))
        artifact_id = f"voice-profile:{speaker_id}"
        workflow = workflow.append_revision(ArtifactRevision(
            artifact_id=artifact_id, revision=1, content_hash=content_hash(profile.model_dump(mode="json")), depends_on=dependencies,
        ))
        profiles.append(profile)
    return run.model_copy(update={"workflow": workflow, "muse_voice_profiles": profiles})

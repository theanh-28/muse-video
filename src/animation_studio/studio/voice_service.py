"""Revisioned Muse voice identities. Generation remains explicitly approved."""
from __future__ import annotations

from animation_studio.core.workflow import ArtifactDependency, ArtifactRevision, ArtifactStatus, StudioRunStatus, content_hash
from animation_studio.studio.models import MuseVoiceProfile, StudioRun
from animation_studio.studio.scripts import SpeakerType, SpeechSource


class VoiceError(ValueError):
    pass


def canonical_profile_payload(profile: MuseVoiceProfile) -> dict[str, object]:
    """Operational sample state deliberately cannot change a reviewed hash."""
    return {key: getattr(profile, key) for key in (
        "character_id", "language", "accent", "perceived_age_range", "pitch", "timbre", "articulation",
        "normal_pacing", "distinctive_speaking_characteristics", "canonical_voice_description",
        "source_script_revision", "source_script_hash", "appearance_reference_artifact_id",
        "appearance_reference_revision", "appearance_reference_hash",
    )}


def _approved_script(run: StudioRun, *, for_mutation: bool = True):
    artifact = run.workflow.current("script")
    if artifact is None or artifact.status != ArtifactStatus.APPROVED or run.approved_script_revision != artifact.revision:
        raise VoiceError("current approved script identity is inconsistent")
    if not 1 <= artifact.revision <= len(run.script_revisions):
        raise VoiceError("approved ScriptPackage is missing")
    script = run.script_revisions[artifact.revision - 1]
    if content_hash(script.model_dump(mode="json")) != artifact.content_hash:
        raise VoiceError("approved ScriptPackage bytes do not match its artifact")
    if for_mutation and run.workflow.status not in {StudioRunStatus.ASSET_PREPARATION, StudioRunStatus.ASSET_REVIEW}:
        raise VoiceError("voice preparation is not available in the current workflow stage")
    return artifact, script


def required_muse_speakers(run: StudioRun) -> list[str]:
    _artifact, script = _approved_script(run, for_mutation=False)
    spoken = {line.speaker_id for line in script.dialogue if line.speaker_type == SpeakerType.CHARACTER and line.speech_source == SpeechSource.MUSE}
    return [character.character_id for character in script.characters if character.character_id in spoken]


def _reference_dependency(run: StudioRun, character_id: str, main: bool):
    spec = next((item for item in run.appearance_specs if item.character_id == character_id), None)
    reference_id = spec.approved_reference_artifact_id if spec else None
    if not reference_id:
        if main:
            raise VoiceError(f"speaking main character {character_id} needs an approved appearance reference")
        return None, None, None
    reference = run.workflow.current(reference_id)
    if reference is None or reference.status != ArtifactStatus.APPROVED or not reference_id.startswith(f"appearance-reference:{character_id}:"):
        raise VoiceError(f"appearance reference for {character_id} is not current and approved")
    return reference_id, reference.revision, reference.content_hash


def _new_profile(run: StudioRun, character_id: str, previous: MuseVoiceProfile | None = None) -> MuseVoiceProfile:
    artifact, script = _approved_script(run)
    character = next(item for item in script.characters if item.character_id == character_id)
    lines = [line for line in script.dialogue if line.speaker_id == character_id and line.speaker_type == SpeakerType.CHARACTER and line.speech_source == SpeechSource.MUSE]
    ref_id, ref_revision, ref_hash = _reference_dependency(run, character_id, character.main)
    values = previous.model_dump(exclude={"character_id", "character_name", "revision", "language", "canonical_voice_description", "source_script_revision", "source_script_hash", "appearance_reference_artifact_id", "appearance_reference_revision", "appearance_reference_hash", "samples", "selected_sample_id", "approved_voice_artifact_id"}) if previous else {}
    return MuseVoiceProfile(**values, character_id=character_id, character_name=character.name, revision=(previous.revision + 1 if previous else 1), language=lines[0].language,
        canonical_voice_description=(previous.canonical_voice_description if previous else f"Manual fallback: natural {lines[0].language} voice for {character.name}; clear articulation and relaxed pacing."),
        source_script_revision=artifact.revision, source_script_hash=artifact.content_hash, appearance_reference_artifact_id=ref_id,
        appearance_reference_revision=ref_revision, appearance_reference_hash=ref_hash)


def _append_profile(run: StudioRun, profile: MuseVoiceProfile, history: list[MuseVoiceProfile]) -> StudioRun:
    script_artifact, _ = _approved_script(run)
    dependencies = [ArtifactDependency(artifact_id="script", revision=script_artifact.revision, content_hash=script_artifact.content_hash)]
    if profile.appearance_reference_artifact_id:
        dependencies.append(ArtifactDependency(artifact_id=profile.appearance_reference_artifact_id, revision=profile.appearance_reference_revision, content_hash=profile.appearance_reference_hash))
    artifact_id = f"voice-profile:{profile.character_id}"
    workflow = run.workflow.stale_dependents(artifact_id).append_revision(ArtifactRevision(artifact_id=artifact_id, revision=profile.revision, content_hash=content_hash(canonical_profile_payload(profile)), depends_on=dependencies))
    profiles = [profile if item.character_id == profile.character_id else item for item in run.muse_voice_profiles]
    if not any(item.character_id == profile.character_id for item in profiles): profiles.append(profile)
    return run.model_copy(update={"workflow": workflow, "muse_voice_profiles": profiles, "muse_voice_profile_history": history})


def prepare_muse_voice_profiles(run: StudioRun) -> StudioRun:
    _approved_script(run)
    updated = run
    for character_id in required_muse_speakers(run):
        current = next((item for item in updated.muse_voice_profiles if item.character_id == character_id), None)
        candidate = _new_profile(updated, character_id, current)
        artifact = updated.workflow.current(f"voice-profile:{character_id}")
        if current and artifact and artifact.content_hash == content_hash(canonical_profile_payload(candidate)):
            continue
        updated = _append_profile(updated, candidate, [*updated.muse_voice_profile_history, current] if current else list(updated.muse_voice_profile_history))
    return updated


def edit_muse_voice_profile(run: StudioRun, *, character_id: str, expected_revision: int, expected_hash: str, canonical_voice_description: str, **fields: str) -> StudioRun:
    _approved_script(run)
    current = next((item for item in run.muse_voice_profiles if item.character_id == character_id), None)
    artifact = run.workflow.current(f"voice-profile:{character_id}")
    if not current or not artifact or (artifact.revision, artifact.content_hash) != (expected_revision, expected_hash):
        raise VoiceError("voice profile changed; reload before editing")
    if not canonical_voice_description.strip(): raise VoiceError("canonical voice description must not be blank")
    allowed = {key: value for key, value in fields.items() if key in {"accent", "perceived_age_range", "pitch", "timbre", "articulation", "normal_pacing", "distinctive_speaking_characteristics"}}
    revised = _new_profile(run, character_id, current).model_copy(update={"canonical_voice_description": canonical_voice_description, **allowed})
    return _append_profile(run, revised, [*run.muse_voice_profile_history, current])


def approve_muse_voice_profile(run: StudioRun, *, character_id: str, expected_revision: int, expected_hash: str, approved_by: str) -> StudioRun:
    _approved_script(run)
    return run.model_copy(update={"workflow": run.workflow.approve_current(f"voice-profile:{character_id}", expected_revision=expected_revision, expected_hash=expected_hash, approved_by=approved_by)})

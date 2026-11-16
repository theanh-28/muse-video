from __future__ import annotations

from animation_studio.core.models import CharacterBible, Episode, Shot, ShotState, WorldBible


def build_shot_prompt(
    shot: Shot,
    visual_style: str,
    character_bibles: list[CharacterBible] | None = None,
    aspect_ratio: str = "16:9",
    previous_observed_state: ShotState | None = None,
    previous_last_frame: str | None = None,
    world_bible: WorldBible | None = None,
    episode_locations: list[str] | None = None,
) -> str:
    bibles_by_id = {item.character_id: item for item in (character_bibles or [])}
    identity_lines: list[str] = []
    for character_id in shot.characters_on_screen:
        bible = bibles_by_id.get(character_id)
        if bible:
            identity_lines.append(f"{bible.canonical_name} ({character_id})")
            identity_lines.extend(
                f"{key}: {value}" for key, value in bible.immutable_identity.items()
            )
            identity_lines.extend(lock.locked_phrase for lock in bible.continuity_locks if lock.immutable)
    identity_lines.extend(shot.continuity_locks)
    if not identity_lines:
        identity_lines.append("Use only the characters and visual facts specified in this shot.")

    beats = []
    for beat in shot.action_beats:
        timing = f"{beat.time_range}: " if beat.time_range else ""
        line = f"{beat.beat}. {timing}{beat.action}"
        if beat.camera_change:
            line += f" Camera: {beat.camera_change}."
        if beat.audio_cue:
            line += f" Sound: {beat.audio_cue}."
        beats.append(line)

    references = [
        f"- {ref.path} ({ref.role}; governs {ref.governs or ref.role}; {ref.media_type})"
        for ref in shot.references
    ] or ["- None supplied; follow the written state and record continuity risk."]
    negative = "\n".join(f"- {item}" for item in shot.negative_constraints) or "- Do not add unlisted characters, props, costume changes or locations."
    audio = [*shot.audio.dialogue, shot.audio.narration, *shot.audio.sfx, shot.audio.music]
    audio_text = "; ".join(item for item in audio if item.strip()) or "No specified audio; do not invent dialogue."

    handoff = []
    if previous_observed_state is not None:
        handoff.append(f"OBSERVED PREVIOUS END STATE: {previous_observed_state.model_dump_json()}")
    if previous_last_frame:
        handoff.append(f"PREVIOUS LAST-FRAME REFERENCE: {previous_last_frame}; use it to align the initial pose and screen geography.")
    world_lines: list[str] = []
    if world_bible:
        episode_location_filter = set(episode_locations or [])
        for location in world_bible.locations:
            if not episode_location_filter or location.location_id in episode_location_filter:
                world_lines.append(
                    f"{location.location_id} {location.canonical_name}: {location.geography}; "
                    f"landmarks {', '.join(location.fixed_landmarks)}; "
                    f"time {location.time_of_day}; weather {location.weather}; "
                    f"lighting {location.lighting_lock}; palette {location.palette_lock}"
                )
        prop_tokens = " ".join([*shot.start_state.held_props, *shot.start_state.prop_positions,
                                 *shot.end_state.held_props, *shot.end_state.prop_positions])
        for prop in world_bible.props:
            if prop.prop_id in prop_tokens:
                world_lines.append(
                    f"{prop.prop_id} {prop.canonical_name}: {prop.appearance}; "
                    f"initial owner {prop.initial_owner}; state rules {', '.join(prop.state_rules)}"
                )

    return "\n".join([
        f"FORMAT: {shot.planned_duration_seconds:g} seconds, {shot.continuity_level}, aspect ratio {aspect_ratio}",
        f"SHOT: {shot.shot_id} — {shot.purpose}",
        f"VISUAL STYLE: {visual_style}",
        "SUBJECT AND LOCKS:", *[f"- {item}" for item in identity_lines],
        "WORLD AND PROP LOCKS:", *([f"- {item}" for item in world_lines] or ["- Use only the shot's stated location and props."]),
        f"START STATE: {shot.start_state.model_dump_json()}",
        *handoff,
        f"SCENE: {shot.start_state.environment}",
        "ACTION OVER TIME:", *beats,
        f"END STATE: {shot.end_state.model_dump_json()}",
        f"CAMERA: {shot.camera.shot_size}; {shot.camera.angle}; {shot.camera.movement}; {shot.camera.lens_look}; focus {shot.camera.focus}; screen direction {shot.camera.screen_direction}",
        f"LIGHTING: {shot.lighting or shot.start_state.lighting}",
        f"AUDIO: {audio_text}",
        "REFERENCE PLAN:", shot.reference_plan, *references,
        "NEGATIVE CONSTRAINTS:", negative,
        "QA TARGETS:", *[f"- {item}" for item in shot.qa_checks],
    ]).strip()


def build_episode_prompts(episode: Episode, character_bibles: list[CharacterBible] | None = None) -> dict[str, str]:
    return {
        shot.shot_id: build_shot_prompt(shot, episode.visual_style, character_bibles, episode.aspect_ratio)
        for shot in sorted(episode.shots, key=lambda item: item.order)
    }


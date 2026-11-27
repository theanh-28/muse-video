"""Script-authoring models and validation, intentionally separate from shot planning."""
from __future__ import annotations

from enum import StrEnum

from pydantic import Field, model_validator

from animation_studio.core.models import StrictModel


class SpeakerType(StrEnum):
    NARRATOR = "NARRATOR"
    CHARACTER = "CHARACTER"


class SpeechSource(StrEnum):
    KOKORO = "KOKORO"
    MUSE = "MUSE"


class ScreenPresence(StrEnum):
    ON_SCREEN = "ON_SCREEN"
    OFF_SCREEN = "OFF_SCREEN"
    NOT_APPLICABLE = "NOT_APPLICABLE"


class DialogueLine(StrictModel):
    line_id: str = Field(pattern=r"^[A-Z0-9_-]+$")
    speaker_id: str = Field(min_length=1, max_length=120)
    exact_text: str = Field(min_length=1, max_length=4000)
    language: str = Field(min_length=2, max_length=20)
    emotion: str = Field(min_length=1, max_length=240)
    delivery_notes: str = Field(min_length=1, max_length=1000)
    speaker_type: SpeakerType
    speech_source: SpeechSource
    screen_presence: ScreenPresence

    @model_validator(mode="after")
    def source_matches_role(self) -> "DialogueLine":
        if not self.exact_text.strip():
            raise ValueError("exact_text must not be blank")
        if self.speaker_type == SpeakerType.NARRATOR:
            if self.speech_source != SpeechSource.KOKORO or self.screen_presence != ScreenPresence.NOT_APPLICABLE:
                raise ValueError("narration must use KOKORO and NOT_APPLICABLE screen presence")
        elif self.speech_source != SpeechSource.MUSE or self.screen_presence == ScreenPresence.NOT_APPLICABLE:
            raise ValueError("character speech must use MUSE and be ON_SCREEN or OFF_SCREEN")
        return self


class StoryBeat(StrictModel):
    beat_id: str = Field(pattern=r"^[A-Z0-9_-]+$")
    description: str = Field(min_length=1, max_length=2000)
    visual_actions: list[str] = Field(default_factory=list, max_length=12)


class ScriptCharacter(StrictModel):
    character_id: str = Field(pattern=r"^[A-Z0-9_-]+$")
    name: str = Field(min_length=1, max_length=120)
    role: str = Field(min_length=1, max_length=500)
    main: bool = False


class ScriptPackage(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    logline: str = Field(min_length=1, max_length=1000)
    story_intent: str = Field(min_length=1, max_length=2000)
    audience_takeaway: str = Field(min_length=1, max_length=2000)
    setup: str = Field(min_length=1, max_length=3000)
    development: str = Field(min_length=1, max_length=3000)
    payoff: str = Field(default="", max_length=3000)
    ending: str = Field(min_length=1, max_length=3000)
    characters: list[ScriptCharacter] = Field(default_factory=list, max_length=16)
    story_beats: list[StoryBeat] = Field(min_length=1, max_length=24)
    mandatory_visual_details: list[str] = Field(default_factory=list, max_length=30)
    dialogue: list[DialogueLine] = Field(default_factory=list, max_length=80)
    target_duration_seconds: int = Field(ge=1, le=180)

    @model_validator(mode="after")
    def unique_script_ids_and_speakers(self) -> "ScriptPackage":
        character_values = [character.character_id for character in self.characters]
        if len(character_values) != len(set(character_values)):
            raise ValueError("character_id values must be unique")
        beat_ids = [beat.beat_id for beat in self.story_beats]
        if len(beat_ids) != len(set(beat_ids)):
            raise ValueError("story beat_id values must be unique")
        line_ids = [line.line_id for line in self.dialogue]
        if len(line_ids) != len(set(line_ids)):
            raise ValueError("dialogue line_id values must be unique")
        character_ids = {character.character_id for character in self.characters}
        invalid = [line.speaker_id for line in self.dialogue if line.speaker_type == SpeakerType.CHARACTER and line.speaker_id not in character_ids]
        if invalid:
            raise ValueError("character dialogue speaker_id must refer to a script character")
        return self

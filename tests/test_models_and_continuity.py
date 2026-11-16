from pydantic import ValidationError
import pytest

from animation_studio.core.continuity import (
    ContinuityError,
    can_advance,
    record_review,
    validate_episode_dependencies,
)
from animation_studio.core.models import ContinuityLedger, ShotState


def test_shot_requires_start_end_states_and_qa(make_shot):
    shot = make_shot()
    assert shot.start_state.screen_position == "center-left"
    assert shot.end_state.pose_or_motion == "standing still"
    assert shot.qa_checks

    invalid = shot.model_dump()
    invalid.pop("end_state")
    with pytest.raises(ValidationError):
        type(shot).model_validate(invalid)


def test_episode_rejects_duplicate_ids(episode_factory, make_shot):
    with pytest.raises(ValidationError, match="shot_id values must be unique"):
        episode_factory([make_shot("SHOT_001", 1), make_shot("SHOT_001", 2)])


def test_c3_requires_previous_shot_dependency(episode_factory, make_shot):
    episode = episode_factory([
        make_shot("SHOT_001", 1),
        make_shot("SHOT_002", 2, continuity="C3", depends_on=[]),
    ])
    with pytest.raises(ContinuityError, match="immediate predecessor"):
        validate_episode_dependencies(episode)


def test_dependency_must_be_earlier(episode_factory, make_shot):
    episode = episode_factory([
        make_shot("SHOT_001", 1, depends_on=["SHOT_002"]),
        make_shot("SHOT_002", 2),
    ])
    with pytest.raises(ContinuityError, match="must be an earlier shot"):
        validate_episode_dependencies(episode)


def test_c3_cannot_advance_before_review(episode_factory, make_shot):
    previous = make_shot("SHOT_001", 1)
    next_shot = make_shot("SHOT_002", 2, continuity="C3", depends_on=["SHOT_001"])
    with pytest.raises(ContinuityError, match="must be reviewed"):
        can_advance(previous, next_shot, ContinuityLedger(episode_id="EP001"))


def test_review_requires_first_middle_last_frames(state):
    ledger = ContinuityLedger(episode_id="EP001")
    with pytest.raises(ContinuityError, match="missing reviewed frame paths"):
        record_review(ledger, "SHOT_001", state, {"last": "last.png"})


def test_review_records_observed_state_and_handoff(state):
    ledger = ContinuityLedger(episode_id="EP001")
    updated = record_review(
        ledger,
        "SHOT_001",
        state,
        {"first": "first.png", "middle": "middle.png", "last": "last.png"},
        ["Lantern stayed in the keeper's left hand."],
        ["Mist obscures the far shoreline."],
    )
    entry = updated.observations[0]
    assert entry.status == "reviewed"
    assert entry.actual_end_state == state
    assert entry.extracted_frames["last"] == "last.png"
    assert updated.last_completed_shot_id == "SHOT_001"


def test_character_bible_model_has_locked_identity():
    from animation_studio.core.models import CharacterBible, ContinuityLock

    bible = CharacterBible(
        character_id="CHAR_A",
        canonical_name="Lan",
        immutable_identity={"face": "round face", "hair": "short black hair"},
        continuity_locks=[ContinuityLock(lock_id="LOOK_01", category="appearance", locked_phrase="Short black hair.")],
    )
    assert bible.continuity_locks[0].immutable is True


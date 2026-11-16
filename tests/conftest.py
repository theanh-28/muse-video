import pytest

from animation_studio.core.models import (
    ActionBeat,
    CameraSpec,
    ContinuityLevel,
    Episode,
    Shot,
    ShotState,
)


@pytest.fixture
def state():
    return ShotState(
        screen_position="center-left",
        body_orientation="three-quarter toward frame right",
        eyeline="toward lantern",
        pose_or_motion="standing still",
        held_props=[],
        environment="misty harbor pier",
        camera_state="medium shot, static camera",
    )


@pytest.fixture
def make_shot(state):
    def build(shot_id="SHOT_001", order=1, continuity="C1", depends_on=None, prompt="A keeper waits by a lantern."):
        return Shot(
            shot_id=shot_id,
            sequence_id="SEQ_001",
            order=order,
            planned_duration_seconds=10,
            continuity_level=ContinuityLevel(continuity),
            purpose="Show the harbor keeper noticing a dim lantern.",
            characters_on_screen=["CHAR_A"],
            start_state=state,
            action_beats=[ActionBeat(beat=1, time_range="0-10s", action="The keeper watches the lantern flicker.")],
            end_state=state,
            camera=CameraSpec(shot_size="medium", angle="eye-level", movement="static"),
            reference_plan="No reference image supplied; treat this as an independent opening shot.",
            prompt=prompt,
            qa_checks=["Character remains on frame left.", "Lantern is visible."],
            depends_on=depends_on or [],
        )
    return build


@pytest.fixture
def episode_factory(make_shot):
    def build(shots=None):
        return Episode(
            episode_id="EP001",
            title="Lantern",
            language="vi-VN",
            visual_style="stylized 2D painted animation",
            shots=shots if shots is not None else [make_shot()],
        )
    return build


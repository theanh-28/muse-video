from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from animation_studio.core.models import (
    ContinuityEntry,
    ContinuityLedger,
    Episode,
    Shot,
    ShotState,
)


class ContinuityError(ValueError):
    """A shot cannot advance without a valid continuity handoff."""


def validate_episode_dependencies(episode: Episode) -> None:
    shots = sorted(episode.shots, key=lambda item: item.order)
    if not shots:
        raise ContinuityError("storyboard must contain at least one shot")
    orders = [shot.order for shot in shots]
    if orders != list(range(1, len(orders) + 1)):
        raise ContinuityError("shot orders must be contiguous starting at 1")

    known = {shot.shot_id: shot for shot in shots}
    for shot in shots:
        if len(shot.depends_on) != len(set(shot.depends_on)):
            raise ContinuityError(f"{shot.shot_id}: duplicate dependency")
        for dep_id in shot.depends_on:
            dependency = known.get(dep_id)
            if dependency is None:
                raise ContinuityError(f"{shot.shot_id}: unknown dependency {dep_id}")
            if dependency.order >= shot.order:
                raise ContinuityError(
                    f"{shot.shot_id}: dependency {dep_id} must be an earlier shot"
                )
        if shot.continuity_level == "C3" and shot.order > 1:
            predecessor = next((item for item in shots if item.order == shot.order - 1), None)
            if predecessor is None or predecessor.shot_id not in shot.depends_on:
                raise ContinuityError(
                    f"{shot.shot_id}: C3 requires immediate predecessor in depends_on"
                )


def can_advance(previous: Shot, next_shot: Shot, ledger: ContinuityLedger) -> None:
    if previous.shot_id not in next_shot.depends_on:
        raise ContinuityError(
            f"{next_shot.shot_id} does not declare dependency on {previous.shot_id}"
        )
    entry = next((item for item in ledger.observations if item.shot_id == previous.shot_id), None)
    if entry is None or entry.status not in ("reviewed", "qc_passed"):
        raise ContinuityError(
            f"{previous.shot_id} must be reviewed before {next_shot.shot_id} can advance"
        )
    if entry.actual_end_state is None:
        raise ContinuityError(f"{previous.shot_id} has no observed actual_end_state")


def record_review(
    ledger: ContinuityLedger,
    shot_id: str,
    actual_end_state: ShotState,
    frame_paths: dict[str, Path | str],
    reviewer_notes: list[str] | None = None,
    continuity_risks: list[str] | None = None,
) -> ContinuityLedger:
    required = {"first", "middle", "last"}
    missing = required - set(frame_paths)
    if missing:
        raise ContinuityError(f"missing reviewed frame paths: {', '.join(sorted(missing))}")
    for label in required:
        if not str(frame_paths[label]).strip():
            raise ContinuityError(f"{label} frame path must not be empty")

    new_entry = ContinuityEntry(
        shot_id=shot_id,
        status="reviewed",
        actual_end_state=actual_end_state,
        extracted_frames={label: str(frame_paths[label]) for label in sorted(required)},
        reviewer_notes=reviewer_notes or [],
        continuity_risks=continuity_risks or [],
    )
    entries = [entry for entry in ledger.observations if entry.shot_id != shot_id]
    entries.append(new_entry)
    entries.sort(key=lambda item: item.shot_id)
    return ledger.model_copy(update={
        "observations": entries,
        "updated_at": datetime.now(timezone.utc),
        "last_completed_shot_id": shot_id,
    })


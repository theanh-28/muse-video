from __future__ import annotations

import pytest

from animation_studio.core.workflow import (
    ArtifactDependency,
    ArtifactRevision,
    ArtifactStatus,
    StudioRunStatus,
    WorkflowState,
    content_hash,
)


def _artifact(
    artifact_id: str,
    revision: int = 1,
    *,
    depends_on: list[ArtifactDependency | str] | None = None,
) -> ArtifactRevision:
    return ArtifactRevision(
        artifact_id=artifact_id,
        revision=revision,
        content_hash=content_hash({"artifact": artifact_id, "revision": revision}),
        depends_on=depends_on or [],
    )


def _approve(state: WorkflowState, artifact_id: str) -> WorkflowState:
    current = state.current(artifact_id)
    assert current is not None
    return state.approve_current(
        artifact_id,
        expected_revision=current.revision,
        expected_hash=current.content_hash,
        approved_by="reviewer",
    )


def test_approval_requires_exact_approved_dependency_revision_and_hash():
    state = _approve(WorkflowState().append_revision(_artifact("script")), "script")
    source = state.current("script")
    assert source is not None
    dependent = _artifact(
        "appearance",
        depends_on=[
            ArtifactDependency(
                artifact_id="script", revision=source.revision, content_hash=source.content_hash
            )
        ],
    )
    approved = _approve(state.append_revision(dependent), "appearance")
    assert approved.current("appearance").status == ArtifactStatus.APPROVED

    stale_reference = _artifact(
        "plan",
        depends_on=[ArtifactDependency(artifact_id="script", revision=1, content_hash="f" * 64)],
    )
    with pytest.raises(ValueError, match="dependency revision changed"):
        _approve(approved.append_revision(stale_reference), "plan")


def test_legacy_dependency_is_readable_but_cannot_be_newly_approved():
    state = WorkflowState().append_revision(_artifact("legacy-dependent", depends_on=["script"]))
    with pytest.raises(ValueError, match="legacy dependency records"):
        _approve(state, "legacy-dependent")


def test_stale_dependents_invalidates_draft_and_approved_descendants_only():
    state = _approve(WorkflowState().append_revision(_artifact("script")), "script")
    script = state.current("script")
    assert script is not None
    appearance = _artifact(
        "appearance",
        depends_on=[ArtifactDependency(artifact_id="script", revision=1, content_hash=script.content_hash)],
    )
    state = _approve(state.append_revision(appearance), "appearance")
    appearance = state.current("appearance")
    assert appearance is not None
    plan = _artifact(
        "plan",
        depends_on=[ArtifactDependency(artifact_id="appearance", revision=1, content_hash=appearance.content_hash)],
    )
    unrelated = _artifact("unrelated")
    state = _approve(state.append_revision(plan), "plan").append_revision(unrelated)

    invalidated = state.stale_dependents("script")
    assert invalidated.current("appearance").status == ArtifactStatus.STALE
    assert invalidated.current("plan").status == ArtifactStatus.STALE
    assert invalidated.current("unrelated").status == ArtifactStatus.DRAFT
    assert invalidated.artifacts["appearance"][0].approval.status == "APPROVED"


def test_append_rejects_explicit_dependency_cycle():
    state = WorkflowState().append_revision(
        _artifact(
            "appearance",
            depends_on=[ArtifactDependency(artifact_id="plan", revision=1, content_hash="a" * 64)],
        )
    )
    with pytest.raises(ValueError, match="cycle"):
        state.append_revision(
            _artifact(
                "plan",
                depends_on=[
                    ArtifactDependency(
                        artifact_id="appearance",
                        revision=1,
                        content_hash=state.current("appearance").content_hash,
                    )
                ],
            )
        )


def test_paused_or_failed_state_cannot_jump_to_production_or_final_qa():
    paused = WorkflowState(status=StudioRunStatus.PAUSED)
    failed = WorkflowState(status=StudioRunStatus.FAILED)
    with pytest.raises(ValueError, match="Invalid studio workflow transition"):
        paused.transition(StudioRunStatus.PRODUCING)
    with pytest.raises(ValueError, match="Invalid studio workflow transition"):
        failed.transition(StudioRunStatus.FINAL_QA)

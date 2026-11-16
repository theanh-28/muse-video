from __future__ import annotations

from datetime import datetime, timezone

from animation_studio.core.models import JobStatus, ShotJob


class JobTransitionError(ValueError):
    """An invalid generation job state transition was requested."""


ALLOWED_TRANSITIONS: dict[JobStatus, set[JobStatus]] = {
    JobStatus.PLANNED: {JobStatus.AWAITING_MANUAL_MEDIA, JobStatus.QUEUED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.AWAITING_MANUAL_MEDIA: {JobStatus.GENERATED, JobStatus.FAILED, JobStatus.CANCELLED},
    JobStatus.QUEUED: {JobStatus.RUNNING, JobStatus.GENERATED, JobStatus.FAILED},
    JobStatus.RUNNING: {JobStatus.GENERATED, JobStatus.FAILED},
    JobStatus.GENERATED: {JobStatus.REVIEWED, JobStatus.FAILED},
    JobStatus.REVIEWED: {JobStatus.QC_PASSED},
    JobStatus.QC_PASSED: set(),
    JobStatus.FAILED: set(),
    JobStatus.CANCELLED: set(),
}


def transition_job(job: ShotJob, new_status: JobStatus, **updates: object) -> ShotJob:
    current = JobStatus(job.status)
    if new_status not in ALLOWED_TRANSITIONS[current]:
        raise JobTransitionError(f"invalid job transition: {current.value} -> {new_status.value}")
    return job.model_copy(update={
        **updates,
        "status": new_status,
        "updated_at": datetime.now(timezone.utc),
    })


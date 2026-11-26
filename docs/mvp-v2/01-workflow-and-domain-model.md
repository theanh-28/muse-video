# M1 — Workflow and domain model

## Before and after

Previously `StudioRun.status` was one mutable string and did not distinguish artifact, approval, provider-job, or QA state. New `core/workflow.py` introduces `StudioRunStatus`, `ArtifactStatus`, `ApprovalStatus`, `ProviderJobState`, `QAStatus`, validated run transitions, content hashes, versioned `ArtifactRevision`, and `ApprovalRecord`.

`StudioRun` now persists a schema-versioned `WorkflowState`, a script revision history, and the approved script revision. Fields have defaults, so legacy records load without migration or deletion.

## Persistence and concurrency

`storage.write_text(..., overwrite=True)` now writes a flushed temporary file and atomically replaces the destination. Existing root containment remains in `resolve_inside`. Script mutation uses a per-run in-process `RLock`, matching the supported local single-worker server and preventing two simultaneous browser approvals from both succeeding. Original artifacts are never overwritten; revisions retain their hash and timestamps.

Dependency invalidation is modeled by `WorkflowState.stale_dependents`; M3+ must attach actual asset/plan dependencies before it can invalidate their revisions. Provider jobs and QA are modeled independently but their orchestration is M5/M6 work.

## Contract and verification

Allowed transitions are backend-enforced; frontend strings cannot bypass them. An approved record requires approver, timestamp, and matching artifact hash. Tests in `tests/test_workflow_and_script_authoring.py` prove invalid transition rejection, revision preservation, persistence, and duplicate approval rejection.

Commands run: `uv run pytest -q` (46 passed, 1 warning after M1/M2); `uv run python scripts/validate_skills.py` is rerun before delivery. Limitations: no cross-process file lock and no M3 dependency graph producer yet. Rollback is compatible: remove new optional fields only after preserving their persisted data; no startup migration is performed.

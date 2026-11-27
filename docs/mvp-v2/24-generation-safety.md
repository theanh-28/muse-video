# Generation safety primitives

## Context

Muse image tasks may consume provider usage. Before Character Appearance can submit them, Studio must persist an exact approval and an attempt intent rather than treating an ambiguous POST as an ordinary retry.

## Behaviour

`AssetGenerationApproval` binds one operation type to an approved artifact ID, revision, content hash, request limit, approver, and usage basis. `AssetGenerationAttempt` is created in `SUBMISSION_INTENDED` before any provider POST and records its immutable prompt, parameters, reference hashes, provider, and target identity.

The safety helpers in `studio/generation_safety.py` reserve a request, reject stale approvals and exhausted limits, verify every reference file byte hash, persist a returned provider task ID, and mark uncertain POST outcomes `SUBMISSION_UNKNOWN`. Reservations are retained after an unknown outcome; callers must reconcile the existing task and cannot blindly resubmit. Restart recovery similarly changes only unsubmitted intents to `SUBMISSION_UNKNOWN`.

## Dependency contract

`ArtifactDependency` binds dependencies to artifact ID, revision, and content hash. Approval verifies the exact current approved dependency. Dependency changes recursively stale both draft and approved current descendants while retaining historic revisions and approval records. Legacy string dependencies remain readable and are invalidated conservatively, but cannot approve a new production artifact because their source identity is unknown.

## Verification

`uv run pytest tests/test_workflow_dependencies.py tests/test_generation_safety.py tests/test_storage_locking.py -q` passed (9 tests) during implementation. These tests use no live provider or media request.

## Limitations

The primitives do not submit a live request themselves. Character Appearance must save each returned run under its mutation transaction before calling the opt-in Muse adapter. Provider credits remain `UNKNOWN` unless a provider supplies trustworthy evidence. This is local-machine advisory locking, not distributed coordination.

## Scope binding update (2026-11-27)

New approvals persist a canonical SHA-256 request scope containing provider, exact prompt, parameters, and reference-byte hashes. Historical approvals without this scope remain readable but cannot authorize another provider POST. Before POST, `claim_asset_attempt()` rechecks the exact current target/dependencies, request fingerprint, request limit, and reference bytes, then persists `SUBMISSION_CLAIMED` under the run lock. An unresolved result blocks overlapping scopes for the logical target, even for parallel image candidates. Restart recovery turns unsubmitted or claimed intents into `SUBMISSION_UNKNOWN`; it never sends a new request.

Verification: `uv run pytest -q tests/test_generation_safety.py tests/test_appearance_workflow.py tests/test_workflow_and_script_authoring.py` passed 15 deterministic tests on 2026-11-27. No provider or external AI call was made.

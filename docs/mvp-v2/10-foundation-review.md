# M1-R foundation review

Reviewed `bd76fb0..50212a6` and reproduced the following finding before applying the fix.

| Severity | Finding | File/symbol | Actual behavior | Fix and test | Status |
|---|---|---|---|---|---|
| P1 | Approval lacked client concurrency binding | `ApprovalRecord`, `approve_script` | A delayed browser could approve the current draft without proving it reviewed that revision/hash. | Approval now records artifact ID/revision/hash and requires expected revision/hash. `test_stale_script_client_cannot_save_or_approve`. | Fixed |
| P1 | Revision append could race after structured generation | `generate_script_run` | Two completions could read the same run and compete to persist a next revision. | Reload/check/append is inside per-run mutation lock. | Fixed |
| P2 | Dependency invalidation had no invocation in script revisions | `_append_script_revision` | Dependent approved artifacts would remain current after script revision. | Script revision marks direct dependents stale before append. | Fixed foundation |
| P2 | Cross-process mutation safety | local JSON store | Atomic replacement protects a file, but no portable inter-process lock exists. | Single local worker is still the supported deployment; live automatic generation remains disabled. | Deferred |

Atomic write failure preserves the previous file because replacement happens only after the temporary file has been flushed. Legacy `StudioRun` fields remain optional/defaulted and existing legacy route tests continue to pass.

Verification: `uv run pytest -q` → 47 passed, 1 warning. No provider request was made.

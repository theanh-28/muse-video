# Transactional script authoring operations

Script authoring now persists a minimal operation record before invoking the structured runtime. The record includes its ID, kind, prior state, optional base revision/hash, timestamps, terminal status, result revision, error, and usage.

Only one `STARTED` authoring operation is permitted per run. A stale feedback revision is rejected before invocation. Completion reloads the run under its mutation lock, appends the revision and records usage plus terminal operation state in the same save. Failures restore the previous workflow status and preserve the prior script/revision history.

Run mutations now acquire an OS advisory lock in addition to the in-process lock. The lock is scoped to the run storage root and is released by the operating system when a process ends. A second local process receives a clear lock error rather than continuing a concurrent read-modify-write transaction.

Interrupted authoring is recovered only by the explicit server-lifecycle recovery function. It marks `STARTED` operations `INTERRUPTED`, restores the recorded workflow state only when that state remains valid, and never calls the authoring runtime. Restoring `SCRIPT_APPROVED` additionally requires the recorded approved script revision and approval record.

Verified with `uv run pytest tests/test_workflow_and_script_authoring.py tests/test_storage_locking.py -q` (7 passed at the time of this change). Browser refresh does not invoke recovery. Multi-host or distributed locking remains out of scope.

Completion and failure verify the exact persisted operation ID, `STARTED` lifecycle state, `SCRIPT_GENERATING` workflow state, and stored base revision/hash. Operation replacement is ID-based, never positional. Feedback requires nonblank feedback, an expected revision/hash, and an existing script; initial generation is permitted only before a script exists.

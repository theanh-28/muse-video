# Transactional script authoring operations

Script authoring now persists a minimal operation record before invoking the structured runtime. The record includes its ID, kind, prior state, optional base revision/hash, timestamps, terminal status, result revision, error, and usage.

Only one `STARTED` authoring operation is permitted per run. A stale feedback revision is rejected before invocation. Completion reloads the run under its mutation lock, appends the revision and records usage plus terminal operation state in the same save. Failures restore the previous workflow status and preserve the prior script/revision history.

This is local single-worker protection only; cross-process locking and restart interruption recovery remain pending. Verified with `uv run pytest tests/test_workflow_and_script_authoring.py -q` (6 passed).

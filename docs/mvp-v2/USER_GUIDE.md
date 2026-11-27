# MVP v2 user guide (M0–M2)

Start the local Studio as documented in `README_VI.md`. Create a run with a brief; the backend creates a script draft only. Review the `script_revisions` in the run response, send an edited package or feedback revision, then approve with an `approved_by` name. At `SCRIPT_APPROVED`, stop: character/voice preparation and production planning are intentionally not in this session.

The Script Studio view presents script fields, dialogue, revision history, feedback, save and approval controls. It sends the current revision/hash with every revision-sensitive request. Character and voice preparation remain unavailable after approval.

Refresh is safe: runs persist under `data/studio/runs`. Do not edit persisted JSON manually. A failed Codex draft remains `FAILED` with a user-actionable error and no provider media request.

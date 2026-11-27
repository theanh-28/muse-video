# MVP v2 user guide (M0–M2)

Start the local Studio as documented in `README_VI.md`. Create a run with a brief; the backend creates a script draft only. Review the `script_revisions` in the run response, send an edited package or feedback revision, then approve with an `approved_by` name. At `SCRIPT_APPROVED`, stop: character/voice preparation and production planning are intentionally not in this session.

The Brief screen defaults to English film language and a 9:16 frame. The brief itself may be written in Vietnamese; genre and shot count are not required inputs.

The Script Studio view presents script fields, dialogue, revision history, feedback, save and approval controls. It sends the current revision/hash with every revision-sensitive request. Character and voice preparation remain unavailable after approval.

If initial script authoring fails before any script exists, use the explicit retry action on the same run. It does not create a new run or automatically retry an AI request.

Refresh is safe: runs persist under `data/studio/runs`. Do not edit persisted JSON manually. A failed Codex draft remains `FAILED` with a user-actionable error and no provider media request.

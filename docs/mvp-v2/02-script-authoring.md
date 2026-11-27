# M2 — Script authoring

## Behavior change

New runs begin at `BRIEF_RECEIVED`. The compatibility entry point `analyze_run` now calls `generate_script_run`, which invokes Codex with `project_authoring_context(stage="script")` and accepts only `ScriptPackage`; it does not create a storyboard, bible, prompt, manifest, or provider request. The old combined implementation is retained privately as `_legacy_analyze_run` for historical code reading, while legacy persisted records remain readable.

`ScriptPackage` stores title, logline, intent, audience takeaway, setup/development/payoff/ending, characters, visual actions, mandatory details and exact dialogue. `DialogueLine` enforces narrator→Kokoro/NOT_APPLICABLE and character→Muse, while preserving exact text. No-dialogue scripts are valid.

## API and use

- `POST /api/runs` creates a brief and schedules script drafting.
- `PUT /api/runs/{run_id}/script` saves a user-edited revision while in `SCRIPT_REVIEW`.
- `POST /api/runs/{run_id}/script/revise` requests a fresh structured revision from feedback.
- `POST /api/runs/{run_id}/approve-script` records the reviewer and approves only the current draft.

Each revision receives stable `script` identity, sequential revision number, timestamp, content hash, and approval record. Editing after a draft creates a new revision rather than overwriting it. Script approval is the only route to `SCRIPT_APPROVED`; downstream planning is intentionally not implemented in this session.

The early timing guard rejects dialogue whose word count exceeds four words/second across the requested duration. This is a conservative warning gate, not measured narration duration; measured audio is deferred to M4. No Muse call is reachable in this stage.

Tests cover script revision history, exact source contracts, approval persistence, and invalid repeated approval. Known limitations: the existing M8 UI has not yet added a Script Review screen; these backend APIs are usable but not a complete M8 UI. No live AI/provider request was made.

Validation also rejects blank dialogue text, duplicate character/beat/dialogue IDs, and character dialogue marked `NOT_APPLICABLE` on screen. It preserves exact user text rather than trimming or rewriting it.

Feedback authoring receives the complete current `ScriptPackage`, its content hash, the original brief, and feedback. An approved script can be reopened into a new draft revision; the prior approval remains historical and the new revision requires a new approval.

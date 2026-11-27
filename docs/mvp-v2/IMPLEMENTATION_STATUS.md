# Implementation status

| Milestone | Status | Evidence | Notes |
|---|---|---|---|
| M0 baseline audit | DONE | `00-baseline-audit.md` | FFmpeg tools unavailable locally |
| M1-R workflow hardening | PARTIAL | `10-foundation-review.md`, `19-run-transaction-and-authoring-operations.md`, `24-generation-safety.md` | Revision-bound dependencies, transitive invalidation, local process locking, and explicit recovery are implemented; production submission integration remains pending. |
| M2 script authoring | PARTIAL | `studio/scripts.py`, Script Studio UI, service/API tests | Brief, review, edit, feedback, history and approval UI implemented; browser automation/live authoring remain unverified |
| M3–M9 | NOT_STARTED | Directive scope | No live provider calls made |

Last verified full regression: 65 passed, 1 third-party `starlette.testclient` deprecation warning. Skill validation passed for all 8 project-local skills. No live provider request was made.

## Character Appearance delivery note

M3 is PARTIAL: persisted main-character specifications, scope approval, and image intents are available in the local Studio. Candidate task polling/download and exact reference-image approval are not yet integrated, so no generated image is represented as approved.

## Directive 004 delivery note

The legacy CLI `auto` command is intentionally disabled until the approved-assets orchestrator exists. This prevents it from bypassing the required Script Review approval gate after the Studio authoring workflow changed to `SCRIPT_REVIEW`.

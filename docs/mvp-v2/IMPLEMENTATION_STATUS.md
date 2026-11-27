# Implementation status

| Milestone | Status | Evidence | Notes |
|---|---|---|---|
| M0 baseline audit | DONE | `00-baseline-audit.md` | FFmpeg tools unavailable locally |
| M1-R workflow hardening | PARTIAL | `10-foundation-review.md`, `19-run-transaction-and-authoring-operations.md`, `24-generation-safety.md` | Revision-bound dependencies, transitive invalidation, local process locking, and explicit recovery are implemented; production submission integration remains pending. |
| M2 script authoring | PARTIAL | `studio/scripts.py`, Script Studio UI, service/API tests | Brief, review, edit, feedback, history and approval UI implemented; browser automation/live authoring remain unverified |
| M3–M9 | NOT_STARTED | Directive scope | No live provider calls made |

Last verified focused result: 16 passed across authoring, dependency, generation-safety, and process-lock tests. Full regression must be rerun before the next milestone is accepted.

## Directive 004 delivery note

The legacy CLI `auto` command is intentionally disabled until the approved-assets orchestrator exists. This prevents it from bypassing the required Script Review approval gate after the Studio authoring workflow changed to `SCRIPT_REVIEW`.

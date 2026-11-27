# Implementation status

| Milestone | Status | Evidence | Notes |
|---|---|---|---|
| M0 baseline audit | DONE | `00-baseline-audit.md` | FFmpeg tools unavailable locally |
| M1-R workflow hardening | DONE | `10-foundation-review.md`, stale-client tests | Expected revision/hash contract added; cross-process lock remains deferred |
| M2 script authoring | PARTIAL | `studio/scripts.py`, Script Studio UI, service/API tests | Brief, review, edit, feedback, history and approval UI implemented; browser automation/live authoring remain unverified |
| M3–M9 | NOT_STARTED | Directive scope | No live provider calls made |

Last verified regression result: 52 passed, 1 warning. Update this file at every subsequent milestone.

## Directive 004 delivery note

The legacy CLI `auto` command is intentionally disabled until the approved-assets orchestrator exists. This prevents it from bypassing the required Script Review approval gate after the Studio authoring workflow changed to `SCRIPT_REVIEW`.

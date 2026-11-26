# M0 — Baseline audit

## Context and evidence

Audited at starting HEAD `bd76fb0626b574cb228a300c4491e5931dbb4c71` on branch `codex/studio-work-in-progress`, before this implementation branch was created. `origin` fetch/push was `https://github.com/theanh-28/muse-video.git`. The working tree contained nine pre-existing, unstaged deletions under `projects/studio/tran-au-nguoi-que-653261/episodes/EP001/metadata/`; they were preserved and excluded from this work.

Actual entry points are `src/animation_studio/cli/main.py`, `studio/web_app.py`, `studio/service.py`, `studio/models.py`, `studio/codex.py`, core models/continuity, services manifest/prompts/jobs, media ffmpeg/qc, and storage files. The expected paths all existed. The project uses Python/Pydantic/PyYAML/Typer/FastAPI and project-local JSON/YAML storage as required.

## Existing workflow and endpoints

Before M1/M2, `create_run` scheduled `analyze_run`; that Codex call generated a single `CreativePackage` containing project bible, character/world bibles, an `Episode`, and its storyboard. `approve_creative_plan`, per-shot manifest creation, approval/submission, polling, continuity review and export were implemented in `studio/service.py`.

Existing web routes included health, run list/create/detail, approve-plan, manifest, approve-generation, submit/refresh, continuity review/accept, media/frame serving, export, and YouTube metadata. Local-only binding, host/origin validation, CSRF token, structured models, and path containment were present.

## Capability classification

| Function | Classification | Evidence |
|---|---|---|
| Legacy draft-to-storyboard workflow | IMPLEMENTED | service/web routes and `test_studio_draft_gate.py` |
| Manual provider lifecycle | IMPLEMENTED | provider/service/tests |
| Muse2API adapter | PARTIAL / experimental | adapter exists; capability flags default unverified |
| Native Muse image/reference/voice APIs | UNVERIFIED | no verified production contract in application code |
| Kokoro narration | MISSING | no provider boundary or runtime integration |
| Durable versioned artifact workflow | MISSING | run stored one mutable record/status string |
| Approval history/invalidation | PARTIAL | generation manifest approval exists; no generic artifact revisions |
| Batch sequential orchestrator | PARTIAL | legacy autopilot/per-shot flow, not M5 durable batch contract |
| FFmpeg inspection/conform/export | IMPLEMENTED (code), UNVERIFIED (environment) | media modules/tests; binaries absent from PATH |
| Evidence-aware cinematic QA | PARTIAL | technical QC and continuity review exist; M6 contract absent |
| UI production screens M1–M8 | PARTIAL | legacy single-page UI exists; staged screens absent |

## Baseline commands and results

- `uv sync --extra http --extra web --extra test`: pass.
- `uv run python scripts/validate_skills.py`: pass, 8 skills validated.
- `uv run pytest -q`: pass, 43 passed, 1 FastAPI/httpx deprecation warning.
- `uv run python -m animation_studio.cli.main --help`: pass.
- `ffmpeg -version` and `ffprobe -version`: failed because both executables were absent from PATH.

## Gap analysis and reuse plan

M1 reuses Pydantic, `StudioRun`, core models, storage containment, and the run-file store; it adds typed state separation, revision metadata and atomic replacement. M2 reuses the Codex structured bridge and explicit `project_authoring_context`, but separates script output from `CreativePackage` and `Episode`. M3–M9 are not implemented in this session.

Risks: a legacy run status is a free-form string; legacy files must remain readable. Atomic writes protect files, and in-process locks cover the configured single local web worker, but a cross-process storage lock is not yet implemented. FFmpeg and live provider capability remain unverified locally.

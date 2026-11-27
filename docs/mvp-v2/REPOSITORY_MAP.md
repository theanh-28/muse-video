# Repository map

## Layout and entry points

- `src/animation_studio/cli/main.py` provides the Typer CLI: project, episode, storyboard, prompts, generation, media, continuity, web, and legacy `auto` commands.
- `src/animation_studio/studio/web_app.py` constructs the loopback-only FastAPI Studio API and serves `studio/static/index.html`, `app.js`, and `app.css`.
- `start.ps1`, `start.bat`, `Dockerfile`, and `docker-compose.yml` are local startup/deployment material. `pyproject.toml` and `uv.lock` define the Python environment.

## Application modules

- `core/models.py` defines project, episode, shot, provider, manifest, job, and continuity Pydantic models. `core/continuity.py` validates dependencies and records observed continuity.
- `core/workflow.py` contains the v2 workflow state machine, versioned artifact records, approvals, dependency invalidation foundation, and content hashing.
- `storage/files.py` provides root containment, JSON/YAML load/dump, and atomic replacement for overwrite writes.
- `services/prompts.py`, `manifest.py`, and `jobs.py` own prompt construction, manifest approval/hash checks, and job transitions.
- `providers/base.py`, `manual.py`, and `muse2api.py` define the provider boundary, manual media workflow, and opt-in experimental gateway adapter.
- `media/ffmpeg.py` and `media/qc.py` inspect/conform media and produce technical QC evidence.

## Studio workflow

`studio/service.py` remains the compatibility facade for persisted Studio runs, legacy generation/continuity/export flow, and v2 script use cases. `studio/models.py` defines request/run models. `studio/scripts.py` defines structured script, beat, character, and dialogue contracts. `studio/codex.py` runs structured Codex/OpenAI/Gemini authoring and injects project-local instruction context. `studio/youtube_metadata.py` retains the existing local metadata draft workflow.

Current v2 implementation is limited to brief-to-script authoring foundation: `BRIEF_RECEIVED`, `SCRIPT_GENERATING`, `SCRIPT_REVIEW`, and `SCRIPT_APPROVED`. Appearance/voice, production planning, batch generation, cinematic QA, mixed-audio assembly, and final v2 export remain unimplemented.

## API and frontend

Existing web routes cover health, run creation/list/detail, legacy plan/manifest/generation/continuity/export actions, script edit/feedback/approval, media/frame access, and YouTube metadata. The frontend is vanilla HTML/CSS/JavaScript in `studio/static/`; it currently primarily renders the legacy storyboard workflow. Script Review UI completion is pending.

## Project assets and runtime source

- `projects/_template/` contains empty project structure; `projects/demo/` is a tracked example with bibles, manifests, prompts, and QC records.
- `templates/`, `schemas/`, and `config/project.example.yaml` provide authoring/configuration references.
- `runtime/muse2api/` vendors the permitted gateway source and its tests. Runtime mutable `data/`, `.env`, sessions, and browser state are intentionally ignored.
- `.agents/skills/` contains project-local animation and YouTube skills. `AGENTS.md` states repository operating rules.

## Tests and verification

`tests/` covers CLI/media, FFmpeg commands, jobs/manifests, core continuity, providers, draft gates, and workflow/script authoring. `scripts/validate_skills.py` validates local skills. Primary checks are `uv sync --locked --extra http --extra web --extra test`, `uv run pytest -q`, `uv run python scripts/validate_skills.py`, and `uv run python -m animation_studio.cli.main --help`.

## Persistence, safety, and blockers

Run records reside under `data/studio/runs` at runtime and are ignored because they can contain user project state. Project-local storage is the source of truth; path containment and atomic overwrite are implemented. Current locking is in-process only; cross-process mutation protection remains a documented limitation. Live generation is experimental and opt-in; no capability is live-verified merely by source inspection.

## Intentionally untracked material

`.gitignore` excludes credentials (`.env`, cookies, sessions, accounts), browser profiles, runtime gateway data, generated/private studio projects and media, virtual environments, caches, worktrees, and temporary test outputs. These exclusions prevent private data and generated artifacts from reaching GitHub. No application source directory is ignored by rule.

## Setup

Install Python 3.11+, uv, and FFmpeg/ffprobe for media features. Run `uv sync --locked --extra http --extra web --extra test`, then use the CLI command above or `uv run python -m animation_studio.cli.main web`. Configure local secrets only through ignored environment files or environment variables; see `README_VI.md`, `docs/MUSE2API_DEPLOYMENT.md`, and `docs/GENERATION_SAFETY.md`.

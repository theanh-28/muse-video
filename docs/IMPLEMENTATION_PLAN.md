# Implementation Plan — Muse Animation Studio MVP

**Status:** local MVP implemented; real generation remains gated  
**Audit date:** 2026-11-16  
**Implementation checkpoint:** 2026-11-17

## Decisions carried forward

- The project-local data files remain the creative and production source of truth.
- Manual Muse work is the default provider mode. The local CLI prepares prompts, manifests, task records and media handoff; it does not pretend to automate a Muse session.
- Muse2API is experimental. Its upstream code has been inspected, but the user account and a real generation request have not been verified. No generation call is permitted until a concrete manifest and usage budget are approved. The provider must remain opt-in and must stop rather than retry a failed submission.
- No official Meta video-generation API was found in the official Model API material reviewed on 2026-11-16. The reviewed pages describe image generation and video understanding. Recheck before any future official-provider integration.
- Continuity observations describe reviewed media, not planned outcomes. C3 shots depend on the previous shot and cannot advance until the previous result has been inspected.

## Audit snapshot

- Windows, Python 3.13.14, uv 0.13.7, Node 26.3.1, FFmpeg/ffprobe 9.0.2; approximately 38.7 GB free on D: at implementation start.
- Muse browser account access remains unverified. The current Windows browser surface was unavailable to the Computer Use integration in the audit turn.
- No third-party skill was installed. A project-local `anistudio-story-continuity` skill is being authored. Upstream repository audit notes and commit IDs are in `THIRD_PARTY_SKILLS.md` and `RESEARCH_NOTES.md`.
- Upstream Muse2API source inspected at commit `19db32a3d6ef50dc87567a8ee0e35dd50c8f7837` (app reports version 1.6.11). `POST /v1/videos` creates an asynchronous task, `GET /v1/videos/{task_id}` returns task state, and generated media is served from `/v1/media/{name}`. The Pydantic request accepts a duration integer without an enforced min/max; its prompt builder defaults to 6 seconds. Aspect ratio and resolution are prompt inputs, not verified output guarantees. Image, video, audio and file references are accepted by the current code, with 10-reference, 40 MiB per item, 100 MiB total limits; supported reference video requires parseable duration metadata and is limited to 120 seconds. There is no native continuation/snapshot ID in the request model. These are static source findings, not live account capabilities.
- Muse2API stores account cookies in `data/accounts.json` as JSON. Treat its data directory and API key as credentials; bind only to loopback and never copy session data into this project.

## Implementation checkpoint — 2026-11-17

- Stages 1–3 are implemented: provider/continuity ADRs, project-local Codex skill, Typer authoring workflow, Pydantic bibles/storyboards, and continuity ledger rules.
- Stage 4 is implemented for offline/manual use: ManualProvider is the default; Muse2API has a separate experimental adapter with mocked contract tests only. Neither gateway compatibility nor the user's Muse account is live-verified.
- Stage 5 is implemented and tested against a synthetic local fixture with installed FFmpeg/ffprobe. No Muse-generated media was used.
- Stage 6 has a configurable five-shot DRAFT demo. Only SHOT_001 has a prompt and a one-shot DRAFT manifest; later dependent prompts remain deferred until their predecessor clip is actually reviewed.
- Unit tests: 31 passed. `compileall` and the Codex Skill structure validator passed. These checks do not verify live provider access.
- No generation request was sent. The demo manifest has no usage estimate or budget and is not approved. Real video remains gated on provider/access verification plus the user's explicit approval of a concrete manifest and usage cap.

## Delivery stages

### Stage 1 — Plan and provider/continuity ADRs

- Record provider comparison, audit evidence, risks and rollback path.
- Keep uncertain provider capabilities explicitly `unknown` or `not live verified`.
- **Exit:** implementation choices and safe generation gate are documented.

### Stage 2 — Codex workflow and project/episode authoring

- Add one small project-local skill for script, bible, storyboard, prompt and ledger work.
- Build a Typer CLI for project and episode initialization, storyboard validation and prompt packaging.
- Keep templates editable and outputs inside the selected project. Do not overwrite source assets.
- **Exit:** project/episode files initialize deterministically; invalid storyboards report actionable field paths.

### Stage 3 — Character Bible and Continuity Engine

- Model project, character/world/prop bibles, shot start/end state, references, action beats and QA checks with Pydantic.
- Validate unique IDs, ordered shots, dependency existence and backward-only dependencies. C3 requires the preceding shot as a dependency.
- Update the ledger only from explicit reviewed observations; retain first/middle/last frame paths and continuity risks.
- **Exit:** schema and continuity rule unit tests pass; no planned state is silently recorded as observed state.

### Stage 4 — Provider boundary and task records

- Ship `ManualProvider` as the default, for prompt handoff and imported media.
- Implement Muse2API behind a separate experimental adapter using the inspected request/task/download contract. Never include cookies; read only the gateway bearer key from the process environment.
- Do not enable real submission by default. Planning writes a DRAFT manifest only. Approval requires a usage estimate and budget limit; submission requires the approved manifest hash and a second explicit action-time confirmation. No POST retry is automatic.
- Keep maximum concurrency at 1. Gate C3 submissions on the preceding shot's reviewed ledger entry and reference plan.
- **Exit:** queue transition tests pass; mocked adapter tests pass. These do not certify upstream compatibility or account access.

### Stage 5 — Media inspection, render and QC

- Use ffprobe for stream/container/duration/resolution/FPS inspection.
- Extract first, middle and last frames without overwriting existing outputs.
- Build FFmpeg commands for ordered cut-list concatenation, optional audio/subtitle inputs, MP4 export and basic decode/black-frame QC.
- Write QC reports under project output directories. Fail on missing media, invalid inputs or overwrite attempts unless the user explicitly selects a safe replacement option.
- **Exit:** unit tests for FFmpeg command construction and QC parsing pass; one synthetic local fixture is decoded/inspected/rendered with the installed FFmpeg toolchain. This does not represent generated Muse media.

### Stage 6 — Draft demo project and handoff

- Provide a configurable 1-character/1-location, 5–8-shot draft example with storyboard and prompt files, Character Bible and Continuity Ledger.
- Mark all creative material DRAFT; no prompt or storyboard can submit until the manifest approval gate is used.
- Produce a generation manifest for review only when the user supplies or accepts the demo creative choices and a usage basis. Unknown duration or usage stays visible as unknown.
- **Exit:** all MVP commands are available, tests pass, and reports distinguish simulated/manual steps from live generation.

## CLI surface

```text
anistudio project init
anistudio episode init
anistudio storyboard validate
anistudio prompts build
anistudio generation plan
anistudio generation approve        # explicit budget/usage approval
anistudio generation submit         # second confirmation; provider-dependent
anistudio generation status
anistudio media inspect
anistudio continuity update
anistudio episode render
anistudio episode qc
```

`generation plan` is always local and non-submitting. `generation submit` rejects a DRAFT manifest, a changed approved manifest, unknown usage basis, missing budget, stale dependencies or a provider not enabled for submission.

## Verification and limits

- Run the project's unit test suite and the skill structure validator after implementation.
- Use mocked HTTP responses for Muse2API adapter tests. Do not call a real generation endpoint during implementation.
- A real provider smoke test remains a separate, user-approved generation with its own exact prompt, duration, reference files and usage cap. Until then, capability claims remain unverified.
- Browser access to the user's Muse account, referral-token applicability, actual output duration/aspect ratio, reference adherence and continuity quality remain unknown.

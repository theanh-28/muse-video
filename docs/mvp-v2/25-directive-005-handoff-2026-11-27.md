# Directive 005 recovery handoff (2026-11-27)

## Scope and provenance

- Previous independently reviewed SHA: `abd795a799b2916f7ebabcf99732d38f25855e34`.
- The branch already contained twelve subsequent Appearance-related commits through `ffd48669e5bd499534fc90c8a30419f9ee883142`.
- This checkpoint preserves the separate interrupted Muse Voice Studio WIP found unstaged in the working tree. It is not evidence that Directive 005 is complete.

## Existing completed source after the reviewed SHA

The committed Appearance slice is integrated through `studio/appearance_service.py`, `studio/service.py`, `studio/web_app.py`, and `studio/static/appearance-studio.js`. It persists revision-bound image scope approvals and pre-POST claims, reconciles task states, fully decodes candidate images with Pillow, serves verified previews, and permits reference approval. `tests/test_appearance_workflow.py` includes an offline fake-provider two-character/six-image API workflow. No live Muse request was made for this work.

## Preserved interrupted WIP

- `src/animation_studio/studio/models.py`: adds `MuseVoiceSample`, `MuseVoiceProfile`, and durable current/history lists on `StudioRun`.
- `src/animation_studio/studio/voice_service.py`: adds `_approved_script`, `required_muse_speakers`, and `prepare_muse_voice_profiles`. It derives one profile per character dialogue speaker using `SpeechSource.MUSE`, records dependency on the approved script, and optionally records an already approved appearance reference dependency.
- `src/animation_studio/studio/service.py`: adds locked `prepare_muse_voices(run_id)` persistence.
- `src/animation_studio/studio/web_app.py`: adds `POST /api/runs/{run_id}/voice/muse/prepare`.

## Incomplete and unverified

- There is no `voice-studio.js` despite `web_app.py` allowing that static filename, and `index.html` does not load or render a Voice Studio. The endpoint is therefore not connected to the browser application.
- No tests exercise the voice preparation endpoint or `voice_service`.
- `MuseVoiceSample` is model-only: no safety-bound request construction, provider submission, polling, media download, sample selection, or voice approval exists.
- `MuseVoiceProfile` has no revision/edit/approval lifecycle and `muse_voice_profile_history` is not used by the service.
- `StudioRunStatus.ASSETS_APPROVED` is not reached by this WIP. There is no final asset-bundle gate.
- No Kokoro provider/module, narrator generation, model download, or runtime integration exists.
- The deterministic voice description is only a placeholder. It has not been reviewed as an approved voice bible or evaluated against any provider contract.

## Verification performed during recovery

| Command | Actual result |
|---|---|
| `uv run pytest -q` | Passed: 70 tests. One third-party Starlette TestClient/httpx deprecation warning. |
| `uv run python scripts/validate_skills.py` | Passed: 8 project-local skills validated. |
| `git diff --check` | Passed: no output. |
| `node --check src/animation_studio/studio/static/appearance-studio.js` | Passed: no output. |

No live provider calls, external AI authoring calls, or model downloads occurred during recovery. The new voice WIP itself has no dedicated test coverage, so the green suite does not validate its runtime behavior.

## Continuation point

Begin technical review at `src/animation_studio/studio/voice_service.py:prepare_muse_voice_profiles` and the endpoint wiring in `src/animation_studio/studio/web_app.py`. Decide and implement the required lifecycle before exposing it in the UI: revision-bound voice authoring, exact approval scope, shared safe submission claim, task reconciliation, sample media validation/selection/approval, and the asset-bundle gate. Implement Kokoro separately behind an explicit provider boundary; no dependency or model was installed by this checkpoint.

## Preservation note

Only the four voice-WIP source files and this handoff/status documentation belong to this recovery checkpoint. No `projects/.../metadata/` deletion was present in the observed working tree, and no unrelated user change is staged by this checkpoint.

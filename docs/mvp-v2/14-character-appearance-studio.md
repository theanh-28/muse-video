# Character Appearance Studio

## Current behaviour

After an approved script, the Studio derives one persisted Appearance Specification for every main character. Each specification is bound to the exact approved script revision/hash and creates a revision-bound `appearance:<character-id>` artifact. Users separately approve the specification and then an image-generation scope; the latter is limited to a fixed number of one-image Muse requests with usage recorded as `UNKNOWN`.

The Appearance screen supports preparation, specification approval, a three-request scope, persisted candidate intents, and local candidate selection. Each intent uses the durable attempt mechanism and is written before a provider request could be made. The screen explicitly reports that live submission remains disabled.

## Technical decisions

`studio/appearance_service.py` provides the application use cases. `studio/service.py` keeps run locking and atomic persistence. The existing Muse adapter is reused for later submit/poll/download; no gateway was added. Candidate generation currently stops at persisted `SUBMISSION_INTENDED` records, so no provider POST, image file, or fake preview is produced without a separately authorized live integration.

## Verification

`tests/test_appearance_workflow.py` uses a two-main-character approved script, creates two specifications, approves two scopes, and persists six independent image intents. It also proves candidate selection makes no new request. `node --check src/animation_studio/studio/static/appearance-studio.js` passed.

## Limitations

Mock-backed service tests now cover task-ID persistence, byte-validated candidate finalization, completed-only selection, and immutable final-reference approval. Gateway submit/poll/download has not yet been wired through the service/API, and the UI therefore cannot display a real provider result. Live Muse remains disabled.

The service now submits an existing persisted intent with that attempt ID as the adapter idempotency key and immediately persists the returned provider task ID. A provider error is retained as `SUBMISSION_UNKNOWN`, not retried. Poll/download API wiring and image preview serving remain pending.

Submit and refresh endpoints now use an injected mock provider in tests or a submission-disabled Muse adapter by default. Completed candidate bytes are served only from the run-contained appearance directory after path validation.

The Appearance screen now renders validated completed-image previews, task state/errors, persisted submit/refresh actions, completed-only selection, and final reference approval. Browser interaction remains unverified; JavaScript syntax and backend regression tests passed.

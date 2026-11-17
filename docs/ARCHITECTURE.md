# Kiến trúc Muse Animation Studio

## Mục tiêu

Giao diện local nhận brief từ người dùng, gọi Codex CLI để phân tích thành package sản xuất có schema, rồi điều phối storyboard, prompt, manifest, Muse, continuity, QC và export. Dữ liệu dự án trên đĩa vẫn là nguồn sự thật; giao diện đọc/ghi cùng các Pydantic model và services của CLI.

## Luồng hệ thống

```text
Browser (127.0.0.1:8765)
        |
        v
FastAPI local web app + CSRF session token
        |
        +----> Codex CLI (ephemeral, read-only, strict JSON schema)
        |         - uses empty temporary working directory
        |         - receives brief and selected rule context only
        |         - MUSE2API credentials removed from child environment
        |         - returns DRAFT Bible/storyboard package
        |
        v
Validated project files (DRAFT)
        |
        +---- user approves creative plan
        v
Prompts + one-shot manifest
        |
        +---- user approves usage/budget
        +---- explicit SEND <manifest-id> action
        v
Muse2API loopback adapter (one active request)
        |
        v
Task polling -> download -> ffprobe -> frame extraction -> FFmpeg conform/decode/QC
        |
        +---- user chooses Codex review (first/middle/last images only)
        +---- user accepts observation -> continuity ledger -> next prompt
        v
Sequential episode render -> QC -> MP4
```

## Components

- **Codex CLI bridge:** `codex exec` runs ephemerally in a temporary empty directory with `--sandbox read-only`, `--ignore-user-config`, `--output-schema` and `--json`. The app passes only the creative brief, project rules and explicitly selected review frames. It parses and validates the final JSON before writing any project files.
- **Web app:** FastAPI/Uvicorn serves a small packaged HTML/CSS/JS interface. It binds only to `127.0.0.1`, disables API docs/CORS, checks the Host and Origin and requires a per-process session token for mutations. The browser can follow task status without sending credentials.
- **Production service:** `animation_studio.studio.service` reuses the project's Pydantic models, continuity engine, prompt builder, manifest service, Muse provider boundary, FFmpeg tools and YAML/JSON storage. New projects are isolated under `projects/studio/<project-id>/`; DRAFT analysis cannot overwrite the demo or another project.
- **Muse2API:** non-official experimental gateway, loopback only. The web app prepares one-shot manifests and permits only one active studio request across runs. It never retries a generation request.
- **Media workflow:** after completion, the app records the original provider clip, extracts first/middle/last frames, runs decode/QC, and creates a conform copy if the source profile differs. Generated media stays local and is excluded from Git.
- **Continuity:** Codex can assess selected still frames only after the user asks. The app displays the assessment and waits for user acceptance before updating the ledger and preparing a dependent shot prompt.

## Approval and workflow boundaries

- Codex analysis creates a complete project/episode/Bible package with `DRAFT` status. It does not call Muse.
- A user action approves the creative plan. The app then changes the saved workflow statuses and builds the first prompt; dependent prompts remain deferred.
- Each generation manifest contains exactly one shot. The user reviews its exact prompt and parameters, enters an estimate/basis and cap, approves that manifest, then types `SEND <manifest-id>` to submit.
- Polling is bounded to 30 minutes. Provider or QC errors are recorded and stop the automatic flow; polling may be repeated manually, but submission is never repeated automatically.
- Every C3 dependent shot needs an accepted continuity review of the predecessor and a saved last-frame reference before prompt/manifest creation.
- Episode export is available only after all included shots have reviewed media and `QC_PASSED` status.

## Privacy and security

- The web server must bind to loopback. Do not expose the port via LAN, reverse proxy, tunnel or public host.
- Muse bearer key stays in the web-server environment and is removed from the Codex child environment. Muse cookies/session data remain in the separate Muse2API runtime.
- Codex request input and opt-in frame review use the user's existing Codex CLI authentication and may consume Codex usage. Muse generation consumes Muse-side usage.
- Runs are stored under ignored `data/studio/runs/`. Projects persist under `projects/studio/`; media and frame extracts remain local/ignored.
- No automatic account rotation, batch generation, publishing or upload to external services.

## Stack

- Python 3.11+, `uv`, Pydantic, PyYAML, Typer.
- Optional `web` extra: FastAPI, Uvicorn and HTTPX.
- Vanilla browser assets packaged with the Python wheel; no React build or JavaScript package manager required.
- FFmpeg/ffprobe must be installed separately and available on `PATH`.

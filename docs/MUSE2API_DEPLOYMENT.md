# Muse2API Local Deployment

## Runtime

- Upstream source: `czg86389-hub/muse2api` at commit `19db32a3d6ef50dc87567a8ee0e35dd50c8f7837` (version 1.6.11).
- Local checkout: `D:\muse2api-runtime`, branch `codex/local-loopback-deploy`.
- Local Compose hardening: publish only `127.0.0.1:18610`, bind inside the container to `0.0.0.0`, require `MUSE2API_KEY`, and set `MUSE2API_CONCURRENCY=1`.
- Persistent account/session/task/media data is stored in `D:\muse2api-runtime\data`. Never copy this directory into this project or commit it.
- `.env` contains the locally generated gateway bearer key. It is ignored by the upstream repository; do not paste its contents into chat, Git, manifests or logs.

The upstream Compose file originally published `18610:18610` on every host interface. The local branch restricts the host side to loopback; the gateway must remain local and must not be exposed through a public reverse proxy.

## Start and stop

Run these commands from `D:\muse2api-runtime`:

```powershell
docker compose up -d --build
docker compose ps
docker compose down
```

`down` stops the service and keeps `data/` and `.env`. Do not use `down -v` or remove the runtime directory if you need to preserve local state.

## Connect the project CLI

`projects/demo/project.yaml` points to `http://127.0.0.1:18610/v1`, reads the bearer key from `MUSE2API_API_KEY`, and uses `muse2api_experimental`. In a PowerShell window where the CLI will run, load the key for that process without printing it:

```powershell
$keyLine = Get-Content 'D:\muse2api-runtime\.env' | Where-Object { $_.StartsWith('MUSE2API_KEY=') }
$env:MUSE2API_API_KEY = $keyLine.Substring('MUSE2API_KEY='.Length)
```

The project remains **unverified for submission**. Reference capabilities, account access and output duration remain unknown. `generation submit` must not be used until a concrete one-shot manifest has a measured usage basis and explicit user approval. The existing DRAFT manifest was created for `manual`; create a fresh plan under the experimental provider before any future approved submission.

## Current deployment boundary

- Deployment verified on 2026-11-17: image built from the pinned checkout; container was running; host port resolved to `127.0.0.1:18610`; authenticated `GET /v1/models` returned HTTP 200. At that deployment checkpoint the account store contained 0 accounts.
- A later user-provided dashboard screenshot showed one enabled, Healthy account with about 2 days remaining. The user confirmed the quota reading; the screenshot itself showed the quota field as unchecked. No cookie/session data was read or copied into this project.
- A later authenticated `GET /v1/models` returned `muse-spark`, `muse-image`, and `muse-video`. This verifies gateway authentication and model listing only, not successful video generation.
- One approved smoke-test request was sent for `SHOT_001` (10-second target, 16:9, no references). Gateway task `task_dc27ab1f21e14211a8e5` was accepted as queued, then failed with `账号额度不足` (account quota insufficient). The CLI recorded the failed task; no result media was downloaded or validated, and no retry was sent.
- Follow-up quota probe on the same account returned `Free plan`, 8% weekly usage, reset `Nov 22`, `2B tokens left`, and 0% extra-token usage. The user's earlier screenshot showed 5% weekly usage and the same 2B balance. This does not support a general account-wide quota exhaustion diagnosis; it does not rule out a video-specific allowance.
- The error is produced by the pinned gateway's UI-text heuristic in `D:\muse2api-runtime\engine.py:1361-1362`: matching any of `额度不足`, `积分不足`, `out of credits`, `达到上限`, or `token limit` in the page tail becomes the same generic `账号额度不足` error. The quota counters are not consulted by that branch, and the matched page text is not saved in the task record. Therefore the exact upstream rejection or a false-positive match cannot be distinguished from persisted evidence. The task record's account ID matches the dashboard account. Chromium logs did not retain the matching text.
- The test manifest and failed job record are stored under `projects/demo/episodes/EP001/generation/`. Do not retry this task. Any further generation requires preserving the original Muse page error and approving a fresh one-shot manifest; do not treat the generic error as a measured quota value.
- API-key/model-list checks are connectivity checks only. They do not prove Muse session validity or video-generation capability.
- If the gateway is unavailable, switch `provider.mode` back to `manual`; create a new manifest after changing provider mode.
- Use one account only if account access is later configured. Do not enable multi-account pools, rotation or automatic failover.

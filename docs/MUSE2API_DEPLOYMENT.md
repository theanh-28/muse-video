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

The project remains **experimental**. One approved six-second video request has succeeded on the current account/session, which verifies one live submission and result download only. It does not verify batch generation, account-wide quota, reference support, continuation support or reliable output parameters. Future requests still require a fresh one-shot manifest, an explicit usage estimate and budget approval; automatic retries remain disabled.

## Current deployment boundary

- Deployment verified on 2026-11-17: image built from the pinned checkout; container was running; host port resolved to `127.0.0.1:18610`; authenticated `GET /v1/models` returned HTTP 200. At that deployment checkpoint the account store contained 0 accounts.
- A later user-provided dashboard screenshot showed one enabled, Healthy account with about 2 days remaining. The user confirmed the quota reading; the screenshot itself showed the quota field as unchecked. No cookie/session data was read or copied into this project.
- A later authenticated `GET /v1/models` returned `muse-spark`, `muse-image`, and `muse-video`. This verifies gateway authentication and model listing only, not successful video generation.
- The first approved `SHOT_001` request (10-second target, 16:9, no references) was accepted as task `task_dc27ab1f21e14211a8e5` and then failed with `账号额度不足`. No media was returned. The original task remains recorded as failed; it was not retried.
- Follow-up quota probe on the same account returned `Free plan`, 8% weekly usage, reset `Nov 22`, `2B tokens left`, and 0% extra-token usage. The user's earlier screenshot showed 5% weekly usage and the same 2B balance. This does not support a general account-wide quota exhaustion diagnosis; it does not rule out a video-specific allowance.
- The generic classifier was corrected in the local Muse2API checkout at `D:\muse2api-runtime`, commit `380bc8f`: it now prefers the current assistant response, requires explicit quota/credit language and preserves a short sanitized diagnostic excerpt. This improves future failure evidence but cannot recover the missing text from the first attempt.
- A separate, explicitly approved six-second diagnostic request was accepted as task `task_32626c256d564b47ae93` and completed. The gateway downloaded `projects/demo/episodes/EP001/clips/SHOT_001/task_32626c256d564b47ae93.mp4`; ffprobe found H.264/AAC, 1280x720, 24 fps, six seconds. Full FFmpeg decode completed without errors.
- The source clip was conformed with FFmpeg to `projects/demo/episodes/EP001/clips/SHOT_001/task_32626c256d564b47ae93_1080p30.mp4` (1920x1080, 30 fps, H.264/AAC, six seconds). The upscale/frame-rate conversion matches the project export profile but does not add source detail. The project QC report is `projects/demo/output/qc/task_32626c256d564b47ae93_1080p30.20261117T081531Z.qc.json` and reports `PASS`.
- The smoke prompt intentionally tested the opening look rather than the full approved ten-second story shot. The exact sent prompt record is preserved in `generation/jobs.json`; its `0–2` time-range dash was mojibaked to `0â€“2` by the PowerShell prompt-file read. The output still completed. Future prompt-file reads must use UTF-8, and this clip must not be treated as the final story opening.
- The post-generation quota meter was not refreshed, so the usage consumed by the successful task is unknown. No cause has been proven for the first task's failure; the second success does not show whether the difference came from duration, transient session state or the old heuristic.
- The continuity ledger records the observed end frame and explicitly notes the tighter-than-planned framing and diagnostic-shot limits. Dependent shot prompts remain deferred until they are planned from this observation.
- Do not automatically retry any task. Every future generation remains a separately approved one-shot request with an explicit cap.
- API-key/model-list checks are connectivity checks only. They do not prove Muse session validity or video-generation capability.
- If the gateway is unavailable, switch `provider.mode` back to `manual`; create a new manifest after changing provider mode.
- Use one account only if account access is later configured. Do not enable multi-account pools, rotation or automatic failover.

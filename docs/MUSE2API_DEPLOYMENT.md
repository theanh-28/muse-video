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

- Deployment verified on 2026-11-17: image built from the pinned checkout; container is running; host port resolves to `127.0.0.1:18610`; authenticated `GET /v1/models` returned HTTP 200 with 3 model entries; account store contains 0 accounts.
- Gateway process may run with no Muse account imported.
- No Muse credentials/session were imported and no generation request was sent during deployment.
- API-key/model-list checks are connectivity checks only. They do not prove Muse session validity or video-generation capability.
- If the gateway is unavailable, switch `provider.mode` back to `manual`; create a new manifest after changing provider mode.
- Use one account only if account access is later configured. Do not enable multi-account pools, rotation or automatic failover.

# Local Docker Compose setup

The repository root `docker-compose.yml` starts Muse2API and the Studio on the same private Docker bridge network. The host publishes both interfaces on loopback only.

On this workspace, `.env` was generated with a random `MUSE2API_KEY`; it is ignored by Git. Add an `OPENAI_API_KEY` or `GEMINI_API_KEY` value to `.env` for LLM planning in the Studio container. Do not commit `.env`.

Start both services with:

```powershell
docker compose up -d --build
```

Open `http://127.0.0.1:8765`. Muse session data stays in `runtime/muse2api/data/` on the host and is mounted into `/app/data` in the gateway. The directory is ignored by Git and excluded from the gateway image build context.

## Auto-Pilot provider checks

Auto-Pilot submits one shot at a time and does not retry provider failures. A new project marks Muse2API as unverified. Its first one-shot manifest is recorded as a smoke test; the project is marked verified only after the generated video downloads, conforms, and passes QC. Later shots can then use ordinary approved manifests. Muse2API does not provide a monetary price quote, so the run records a cap of one submission per shot rather than a currency estimate.

The gateway is an unofficial integration. A valid saved session does not guarantee that Muse will accept a request or that the account has generation capacity.

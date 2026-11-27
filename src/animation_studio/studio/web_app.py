from __future__ import annotations

import asyncio
import hmac
import os
import secrets
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse

from animation_studio.studio.codex import codex_executable
from animation_studio.studio.codex import CodexBridgeError
from animation_studio.studio.models import (
    CreativeApproval,
    GenerationApprovalRequest,
    GenerationPlanRequest,
    GenerationSubmitRequest,
    StudioBrief,
    ScriptApprovalRequest,
    ScriptFeedbackRequest,
    ScriptEditRequest,
    ContinuityReviewAcceptRequest,
    YouTubeMetadataRequest,
    AppearanceApprovalRequest,
    AppearanceCandidateRequest,
    AppearanceSelectionRequest,
    AppearanceReferenceApprovalRequest,
    AppearanceAttemptRequest,
    AppearanceEditRequest,
    MuseVoiceEditRequest,
    MuseVoiceApprovalRequest,
)
from animation_studio.studio.service import (
    RUNS_DIR,
    STUDIO_PROJECTS_DIR,
    SUBMIT_LOCK,
    accept_continuity_review,
    analyze_continuity,
    analyze_run,
    generate_script_run,
    approve_creative_plan,
    approve_generation,
    create_run,
    export_episode,
    get_run,
    list_runs,
    prepare_generation,
    refresh_generation,
    submit_generation,
    run_autopilot,
    approve_script,
    revise_script,
    prepare_appearance,
    approve_appearance_specification,
    edit_appearance_specification,
    approve_appearance_generation,
    prepare_appearance_candidates,
    select_appearance_candidate,
    approve_selected_appearance_candidate,
    submit_appearance_candidate,
    refresh_appearance_candidate,
    prepare_muse_voices,
    edit_muse_voice,
    approve_muse_voice,
)
from animation_studio.studio.scripts import ScriptPackage
from animation_studio.studio.youtube_metadata import draft_youtube_metadata
from animation_studio.providers.muse2api import Muse2ApiProvider, is_gateway_host_allowed


def _load_dotenv_if_present() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    env_file = repo_root / ".env"
    if env_file.is_file():
        try:
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip().strip("'\"")
                    if k and k not in os.environ:
                        os.environ[k] = v
            if "MUSE2API_KEY" in os.environ and "MUSE2API_API_KEY" not in os.environ:
                os.environ["MUSE2API_API_KEY"] = os.environ["MUSE2API_KEY"]
        except Exception:
            pass


_load_dotenv_if_present()

STATIC_DIR = Path(__file__).parent / "static"
LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}


def _public(run):
    return run.model_dump(mode="json")


def _gateway_status() -> dict[str, object]:
    base_url = os.getenv("MUSE2API_BASE_URL", "http://127.0.0.1:18610/v1").rstrip("/")
    key = os.getenv("MUSE2API_API_KEY") or os.getenv("MUSE2API_KEY")
    parsed = urlsplit(base_url)
    if not is_gateway_host_allowed(parsed.hostname):
        return {"connected": False, "detail": "Gateway must use a loopback or explicitly allowed container-network URL"}
    if not key:
        return {"connected": False, "detail": "Set MUSE2API_API_KEY in the PowerShell session"}
    try:
        import httpx

        response = httpx.get(
            f"{base_url}/models",
            headers={"Authorization": f"Bearer {key}"},
            timeout=3.0,
            follow_redirects=False,
        )
        response.raise_for_status()
        payload = response.json()
        models = payload.get("data", []) if isinstance(payload, dict) else []
        names = [item.get("id") for item in models if isinstance(item, dict) and isinstance(item.get("id"), str)]
        return {"connected": True, "models": names}
    except Exception as exc:
        return {"connected": False, "detail": f"Gateway check failed ({type(exc).__name__})"}


def create_app() -> FastAPI:
    app = FastAPI(title="Muse Animation Studio", docs_url=None, redoc_url=None, openapi_url=None)
    app.state.session_token = secrets.token_urlsafe(32)
    app.state.poll_tasks = {}
    app.state.appearance_provider = None

    @app.middleware("http")
    async def local_only_and_csrf(request: Request, call_next):
        host = request.url.hostname
        if host not in LOOPBACK_HOSTS:
            return JSONResponse({"detail": "The studio is available only on this computer."}, status_code=403)
        if request.method not in {"GET", "HEAD", "OPTIONS"}:
            origin = request.headers.get("origin")
            if origin and urlsplit(origin).hostname not in LOOPBACK_HOSTS:
                return JSONResponse({"detail": "Cross-origin requests are blocked."}, status_code=403)
            token = request.headers.get("x-studio-token", "")
            if not hmac.compare_digest(token, app.state.session_token):
                return JSONResponse({"detail": "Invalid local studio session."}, status_code=403)
            length = request.headers.get("content-length")
            if length and length.isdigit() and int(length) > 1_000_000:
                return JSONResponse({"detail": "Request body is too large."}, status_code=413)
        return await call_next(request)

    @app.exception_handler(ValueError)
    async def workflow_error_handler(_request: Request, exc: ValueError):
        return JSONResponse({"detail": str(exc)}, status_code=409)

    @app.exception_handler(CodexBridgeError)
    async def codex_error_handler(_request: Request, exc: CodexBridgeError):
        return JSONResponse({"detail": str(exc)}, status_code=502)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        path = STATIC_DIR / "index.html"
        if not path.is_file():
            raise HTTPException(status_code=500, detail="Studio UI assets are missing")
        html = path.read_text(encoding="utf-8").replace("__STUDIO_TOKEN__", app.state.session_token)
        return HTMLResponse(html)

    @app.get("/assets/{asset_name}")
    async def assets(asset_name: str):
        if asset_name not in {"app.js", "app.css", "script-studio.js", "appearance-studio.js", "voice-studio.js"}:
            raise HTTPException(status_code=404)
        path = STATIC_DIR / asset_name
        return FileResponse(path)

    @app.get("/api/health")
    async def health():
        backend_available = codex_executable() is not None or bool(
            os.getenv("OPENAI_API_KEY", "").strip() or os.getenv("GEMINI_API_KEY", "").strip()
        )
        return {
            "codex_available": backend_available,
            "llm_backend": "Codex CLI" if codex_executable() else (
                "OpenAI API" if os.getenv("OPENAI_API_KEY", "").strip() else (
                    "Gemini API" if os.getenv("GEMINI_API_KEY", "").strip() else None
                )
            ),
            "gateway": await asyncio.to_thread(_gateway_status),
            "studio_projects": str(STUDIO_PROJECTS_DIR),
        }

    @app.get("/api/runs")
    async def runs():
        return [
            {
                "run_id": run.run_id,
                "status": run.status,
                "updated_at": run.updated_at.isoformat(),
                "title": run.analysis.project_title if run.analysis else (run.brief.title_hint or run.brief.brief[:48]),
            }
            for run in list_runs()
        ]

    @app.post("/api/runs")
    async def start_run(brief: StudioBrief, background_tasks: BackgroundTasks):
        if brief.autopilot:
            raise HTTPException(status_code=422, detail="Hãy tạo bản nháp và duyệt kế hoạch trước khi sản xuất.")
        run = create_run(brief)
        background_tasks.add_task(analyze_run, run.run_id)
        return _public(run)

    @app.get("/api/runs/{run_id}")
    async def run_detail(run_id: str):
        return _public(get_run(run_id))

    @app.post("/api/runs/{run_id}/approve-plan")
    async def approve_plan(run_id: str, payload: CreativeApproval):
        return _public(await asyncio.to_thread(approve_creative_plan, run_id, confirm=payload.confirm))

    @app.put("/api/runs/{run_id}/script")
    async def edit_script(run_id: str, payload: ScriptEditRequest):
        return _public(await asyncio.to_thread(
            revise_script, run_id, payload.script, expected_revision=payload.expected_revision,
            expected_content_hash=payload.expected_content_hash
        ))

    @app.post("/api/runs/{run_id}/script/revise")
    async def revise_script_with_feedback(run_id: str, payload: ScriptFeedbackRequest):
        return _public(await asyncio.to_thread(
            generate_script_run, run_id, feedback=payload.feedback,
            expected_revision=payload.expected_revision, expected_content_hash=payload.expected_content_hash,
        ))

    @app.post("/api/runs/{run_id}/script/retry")
    async def retry_initial_script(run_id: str):
        """Explicitly retry a failed initial authoring operation on the same run."""
        return _public(await asyncio.to_thread(generate_script_run, run_id))

    @app.post("/api/runs/{run_id}/approve-script")
    async def approve_script_revision(run_id: str, payload: ScriptApprovalRequest):
        return _public(await asyncio.to_thread(
            approve_script, run_id, approved_by=payload.approved_by,
            expected_revision=payload.expected_revision, expected_content_hash=payload.expected_content_hash,
        ))

    @app.post("/api/runs/{run_id}/appearance/prepare")
    async def prepare_appearance_stage(run_id: str):
        return _public(await asyncio.to_thread(prepare_appearance, run_id))

    @app.post("/api/runs/{run_id}/appearance/specification/approve")
    async def approve_appearance_spec(run_id: str, payload: AppearanceApprovalRequest):
        return _public(await asyncio.to_thread(
            approve_appearance_specification, run_id, character_id=payload.character_id,
            expected_revision=payload.expected_revision, expected_content_hash=payload.expected_content_hash,
            approved_by=payload.approved_by,
        ))

    @app.put("/api/runs/{run_id}/appearance/specification")
    async def edit_appearance_spec(run_id: str, payload: AppearanceEditRequest):
        return _public(await asyncio.to_thread(
            edit_appearance_specification, run_id, character_id=payload.character_id,
            expected_revision=payload.expected_revision, expected_content_hash=payload.expected_content_hash,
            description=payload.description, locked_attributes=payload.locked_attributes,
        ))

    @app.post("/api/runs/{run_id}/appearance/generation/approve")
    async def approve_appearance_scope(run_id: str, payload: AppearanceApprovalRequest):
        return _public(await asyncio.to_thread(
            approve_appearance_generation, run_id, character_id=payload.character_id,
            expected_revision=payload.expected_revision, expected_content_hash=payload.expected_content_hash,
            request_limit=payload.request_limit, approved_by=payload.approved_by,
        ))

    @app.post("/api/runs/{run_id}/appearance/candidates/prepare")
    async def prepare_candidates(run_id: str, payload: AppearanceCandidateRequest):
        return _public(await asyncio.to_thread(
            prepare_appearance_candidates, run_id, character_id=payload.character_id,
            approval_id=payload.approval_id, count=payload.count,
        ))

    @app.post("/api/runs/{run_id}/appearance/candidate/select")
    async def choose_candidate(run_id: str, payload: AppearanceSelectionRequest):
        return _public(await asyncio.to_thread(
            select_appearance_candidate, run_id, character_id=payload.character_id, candidate_id=payload.candidate_id,
        ))

    @app.post("/api/runs/{run_id}/appearance/reference/approve")
    async def approve_appearance_reference(run_id: str, payload: AppearanceReferenceApprovalRequest):
        return _public(await asyncio.to_thread(
            approve_selected_appearance_candidate, run_id, character_id=payload.character_id,
            expected_hash=payload.expected_content_hash, approved_by=payload.approved_by,
        ))

    def appearance_provider():
        if app.state.appearance_provider is not None:
            return app.state.appearance_provider
        return Muse2ApiProvider(os.getenv("MUSE2API_BASE_URL", "http://127.0.0.1:18610/v1"), submission_enabled=False)

    @app.post("/api/runs/{run_id}/appearance/submit")
    async def submit_appearance(run_id: str, payload: AppearanceAttemptRequest):
        return _public(await asyncio.to_thread(submit_appearance_candidate, run_id, attempt_id=payload.attempt_id, provider=appearance_provider()))

    @app.post("/api/runs/{run_id}/appearance/refresh")
    async def refresh_appearance(run_id: str, payload: AppearanceAttemptRequest):
        return _public(await asyncio.to_thread(refresh_appearance_candidate, run_id, attempt_id=payload.attempt_id, provider=appearance_provider()))

    @app.post("/api/runs/{run_id}/voice/muse/prepare")
    async def prepare_muse_voice_profiles(run_id: str):
        return _public(await asyncio.to_thread(prepare_muse_voices, run_id))

    @app.put("/api/runs/{run_id}/voice/muse/profile")
    async def edit_muse_voice_profile(run_id: str, payload: MuseVoiceEditRequest):
        return _public(await asyncio.to_thread(edit_muse_voice, run_id, **payload.model_dump()))

    @app.post("/api/runs/{run_id}/voice/muse/profile/approve")
    async def approve_muse_voice_profile(run_id: str, payload: MuseVoiceApprovalRequest):
        return _public(await asyncio.to_thread(approve_muse_voice, run_id, **payload.model_dump()))

    @app.post("/api/runs/{run_id}/manifest")
    async def make_manifest(run_id: str, payload: GenerationPlanRequest):
        return _public(await asyncio.to_thread(prepare_generation, run_id, payload.shot_id))

    @app.post("/api/runs/{run_id}/approve-generation")
    async def approve_manifest(run_id: str, payload: GenerationApprovalRequest):
        return _public(await asyncio.to_thread(approve_generation, run_id, payload))

    @app.post("/api/runs/{run_id}/submit")
    async def submit(run_id: str, payload: GenerationSubmitRequest):
        # Serialize submit clicks so a double click cannot create duplicate Muse tasks.
        async with SUBMIT_LOCK:
            run = await asyncio.to_thread(submit_generation, run_id, payload.confirmation)
        task = asyncio.create_task(poll_until_terminal(run_id))
        app.state.poll_tasks[run_id] = task
        return _public(run)

    @app.post("/api/runs/{run_id}/refresh")
    async def refresh(run_id: str):
        return _public(await asyncio.to_thread(refresh_generation, run_id))

    @app.post("/api/runs/{run_id}/continuity-review")
    async def continuity_review(run_id: str):
        return _public(await asyncio.to_thread(analyze_continuity, run_id))

    @app.post("/api/runs/{run_id}/accept-review")
    async def accept_review(run_id: str, payload: ContinuityReviewAcceptRequest):
        return _public(await asyncio.to_thread(accept_continuity_review, run_id, confirm=payload.confirm))

    @app.get("/api/runs/{run_id}/video/{kind}")
    async def video(run_id: str, kind: str):
        if kind not in {"source", "master", "export"}:
            raise HTTPException(status_code=404)
        run = get_run(run_id)
        root = Path(run.project_dir or "").resolve()
        relative = run.export_path if kind == "export" else (run.conformed_media_path if kind == "master" else run.media_path)
        if not relative:
            raise HTTPException(status_code=404, detail="Video is not ready")
        path = (root / relative).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(status_code=404, detail="Video file is unavailable")
        return FileResponse(path, media_type="video/mp4", headers={"Accept-Ranges": "bytes"})

    @app.get("/api/runs/{run_id}/appearance-image/{candidate_id}")
    async def appearance_image(run_id: str, candidate_id: str):
        run = get_run(run_id)
        all_specs = [*run.appearance_specs, *run.appearance_spec_history]
        candidate = next((candidate for spec in all_specs for candidate in spec.candidates if candidate.candidate_id == candidate_id), None)
        if candidate is None or candidate.status not in {"COMPLETED", "APPROVED"} or not candidate.image_path:
            raise HTTPException(status_code=404, detail="Appearance image is unavailable")
        root = (RUNS_DIR / run_id / "appearance").resolve()
        path = (root / candidate.image_path).resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(status_code=404, detail="Appearance image is unavailable")
        return FileResponse(path, media_type=candidate.media_type or "application/octet-stream")

    @app.get("/api/runs/{run_id}/frame/{label}")
    async def frame(run_id: str, label: str):
        if label not in {"first", "middle", "last"}:
            raise HTTPException(status_code=404)
        run = get_run(run_id)
        if not run.frames_dir:
            raise HTTPException(status_code=404)
        root = Path(run.project_dir or "").resolve()
        directory = (root / (run.frames_dir or "")).resolve()
        path = (directory / f"{label}.png").resolve()
        if not path.is_relative_to(root) or not path.is_file():
            raise HTTPException(status_code=404)
        return FileResponse(path, media_type="image/png")

    @app.post("/api/runs/{run_id}/export")
    async def export(run_id: str):
        return _public(await asyncio.to_thread(export_episode, run_id))

    @app.post("/api/runs/{run_id}/youtube-metadata")
    async def youtube_metadata(run_id: str, payload: YouTubeMetadataRequest):
        return _public(await asyncio.to_thread(draft_youtube_metadata, run_id, payload))

    async def poll_until_terminal(run_id: str):
        try:
            for _ in range(360):  # up to 30 minutes; polling never resubmits
                async with app.state.poll_lock:
                    run = await asyncio.to_thread(refresh_generation, run_id)
                if run.status not in {"SUBMITTED", "RUNNING"}:
                    return
                await asyncio.sleep(5)
        finally:
            app.state.poll_tasks.pop(run_id, None)

    app.state.poll_lock = asyncio.Lock()
    return app

from __future__ import annotations

import getpass
import hashlib
import json
import os
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import typer
import yaml
from pydantic import ValidationError

from animation_studio.core.continuity import (
    ContinuityError,
    can_advance,
    record_review,
    validate_episode_dependencies,
)
from animation_studio.core.models import (
    CharacterBible,
    ContinuityLedger,
    Episode,
    GenerationManifest,
    JobQueue,
    JobStatus,
    ProjectConfig,
    ShotJob,
    ShotState,
    WorldBible,
)
from animation_studio.media.ffmpeg import (
    AudioTrack,
    MediaError,
    build_render_command,
    concat_file_contents,
    extract_representative_frames,
    run_command,
)
from animation_studio.media.qc import inspect_media, quality_report
from animation_studio.providers.base import ProviderError, ProviderNotReady, VideoRequest
from animation_studio.providers.manual import ManualProvider
from animation_studio.providers.muse2api import Muse2ApiProvider
from animation_studio.services.jobs import JobTransitionError, transition_job
from animation_studio.services.manifest import (
    ManifestError,
    approval_fingerprint,
    approve_manifest,
    build_manifest,
    ensure_approved_unchanged,
)
from animation_studio.services.prompts import build_shot_prompt
from animation_studio.storage.files import (
    StorageError,
    dump_model,
    load_mapping,
    load_model,
    resolve_inside,
    write_text,
)

app = typer.Typer(help="Codex-directed animation production pipeline", no_args_is_help=True)
project_app = typer.Typer(help="Project setup", no_args_is_help=True)
episode_app = typer.Typer(help="Episode and media workflow", no_args_is_help=True)
storyboard_app = typer.Typer(help="Storyboard validation", no_args_is_help=True)
prompts_app = typer.Typer(help="Prompt package", no_args_is_help=True)
generation_app = typer.Typer(help="Generation manifest and job lifecycle", no_args_is_help=True)
media_app = typer.Typer(help="Media inspection", no_args_is_help=True)
continuity_app = typer.Typer(help="Continuity ledger", no_args_is_help=True)
MAX_IMPORTED_MEDIA_BYTES = 2 * 1024 * 1024 * 1024

# Some Windows launchers expose a legacy console encoding (for example cp1252).
# Keep Unicode storyboard content from crashing CLI output in those terminals.
for _stream in (sys.stdout, sys.stderr):
    if hasattr(_stream, "reconfigure"):
        try:
            _stream.reconfigure(errors="backslashreplace")
        except (OSError, ValueError):
            pass

app.add_typer(project_app, name="project")
app.add_typer(episode_app, name="episode")
app.add_typer(storyboard_app, name="storyboard")
app.add_typer(prompts_app, name="prompts")
app.add_typer(generation_app, name="generation")
app.add_typer(media_app, name="media")
app.add_typer(continuity_app, name="continuity")


def _fail(message: str, code: int = 1) -> None:
    typer.echo(f"Error: {message}", err=True)
    raise typer.Exit(code)


def _load_project(root: Path) -> ProjectConfig:
    path = root.resolve() / "project.yaml"
    try:
        return load_model(path, ProjectConfig)
    except (OSError, ValidationError, StorageError) as exc:
        _fail(f"Cannot load project configuration {path}: {exc}")


def _find_project_root(start: Path) -> Path:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    for path in (current, *current.parents):
        if (path / "project.yaml").is_file():
            return path
    _fail(f"No project.yaml found above {start}; run 'anistudio project init' first")


def _load_episode(path: Path) -> Episode:
    try:
        return load_model(path, Episode)
    except (OSError, ValidationError, StorageError) as exc:
        _fail(f"Cannot load storyboard/episode {path}: {exc}")


def _load_ledger(path: Path, episode_id: str) -> ContinuityLedger:
    if not path.exists():
        return ContinuityLedger(episode_id=episode_id)
    try:
        ledger = load_model(path, ContinuityLedger)
    except (OSError, ValidationError, StorageError) as exc:
        _fail(f"Cannot load continuity ledger {path}: {exc}")
    if ledger.episode_id != episode_id:
        _fail(f"Ledger episode_id {ledger.episode_id} does not match {episode_id}")
    return ledger


def _load_character_bibles(root: Path) -> list[CharacterBible]:
    path = root / "assets" / "character-bible.yaml"
    if not path.exists():
        return []
    try:
        payload = load_mapping(path)
        records = payload.get("characters")
        if isinstance(records, list):
            return [CharacterBible.model_validate(item) for item in records]
        return [CharacterBible.model_validate(payload)]
    except (OSError, ValidationError, StorageError) as exc:
        # Empty starter template is valid as a not-yet-authored bible.
        try:
            raw = load_mapping(path)
        except Exception:
            _fail(f"Invalid Character Bible {path}: {exc}")
        if raw.get("characters") == []:
            return []
        _fail(f"Invalid Character Bible {path}: {exc}")


def _load_world_bible(root: Path) -> WorldBible:
    path = root / "assets" / "world-bible.yaml"
    if not path.exists():
        return WorldBible()
    try:
        return load_model(path, WorldBible)
    except (OSError, ValidationError, StorageError) as exc:
        _fail(f"Invalid World Bible {path}: {exc}")


def _load_queue(path: Path, episode_id: str) -> JobQueue:
    if not path.exists():
        return JobQueue(episode_id=episode_id)
    try:
        queue = load_model(path, JobQueue)
    except (OSError, ValidationError, StorageError) as exc:
        _fail(f"Cannot load job queue {path}: {exc}")
    if queue.episode_id != episode_id:
        _fail("Job queue episode_id does not match the manifest")
    return queue


def _ensure_storyboard_approved(root: Path, manifest: GenerationManifest) -> Episode:
    episode_file = root / "episodes" / manifest.episode_id / "episode.yaml"
    episode = _load_episode(episode_file)
    if episode.status != "APPROVED":
        _fail(f"Episode {episode.episode_id} must be marked APPROVED before manifest approval or submission")
    by_id = {shot.shot_id: shot for shot in episode.shots}
    for request in manifest.requests:
        shot = by_id.get(request.shot_id)
        if shot is None:
            _fail(f"Manifest shot is missing from the current storyboard: {request.shot_id}")
        if shot.status != "APPROVED":
            _fail(f"Shot {shot.shot_id} is {shot.status}; only APPROVED shots may be sent to a provider")
    return episode


def _summary_text(manifest: GenerationManifest) -> str:
    lines = [
        f"Manifest: {manifest.manifest_id}",
        f"Episode: {manifest.episode_id}",
        f"Provider: {manifest.provider_mode}",
        f"Requests: {len(manifest.requests)}",
        f"Estimated usage basis: {manifest.usage_estimate or 'NOT SET'}",
        f"Budget limit: {manifest.budget_limit or 'NOT SET'}",
    ]
    for item in manifest.requests:
        lines.append(
            f"- {item.order}. {item.shot_id}: {item.duration_seconds:g}s, {item.aspect_ratio}, "
            f"continuity {item.continuity_level}, refs {len(item.references)}, deps {item.depends_on}"
        )
        lines.append(f"  Prompt: {item.prompt.replace(chr(10), ' ')[:180]}")
    return "\n".join(lines)


@project_app.command("init")
def project_init(
    path: Path = typer.Argument(Path("."), help="Project root directory"),
    title: str = typer.Option("Untitled Animation", help="Project title"),
    language: str = typer.Option("vi-VN", help="Creative document language"),
) -> None:
    root = path.resolve()
    config_path = root / "project.yaml"
    if config_path.exists():
        _fail(f"Project already exists: {config_path}")
    root.mkdir(parents=True, exist_ok=True)
    normalized_title = unicodedata.normalize("NFKD", title.replace("đ", "d").replace("Đ", "D"))
    ascii_title = "".join(char for char in normalized_title if not unicodedata.combining(char))
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-") or "animation-project"
    config = ProjectConfig(project={
        "id": slug,
        "title": title,
        "language": language,
        "genre": "to-be-decided",
        "visual_style": "to-be-decided",
    })
    dump_model(config, config_path, overwrite=False)
    (root / "assets").mkdir(exist_ok=True)
    (root / "episodes").mkdir(exist_ok=True)
    (root / "output").mkdir(exist_ok=True)
    write_text(root / "project-bible.md", "# Project Bible\n\nStatus: DRAFT\n\n## Logline\n\n## Premise and world rules\n\n## Visual style lock\n\n## Approved creative decisions\n", overwrite=False)
    write_text(root / "assets" / "character-bible.yaml", "status: DRAFT\ncharacters: []\n", overwrite=False)
    write_text(root / "assets" / "world-bible.yaml", "status: DRAFT\nlocations: []\nprops: []\n", overwrite=False)
    typer.echo(f"Initialized project: {root}")
    typer.echo("Provider mode: manual. No media service or generation request was started.")


@episode_app.command("init")
def episode_init(
    episode_id: str = typer.Argument(..., help="Stable episode ID, e.g. EP001"),
    project_dir: Path = typer.Option(Path("."), "--project-dir", "-p"),
    title: str = typer.Option("Untitled Episode", help="Episode title"),
    language: str | None = typer.Option(None, help="Override project language"),
) -> None:
    root = project_dir.resolve()
    config = _load_project(root)
    if not re.fullmatch(r"[A-Za-z0-9_-]+", episode_id):
        _fail("episode_id may contain only letters, digits, underscore and hyphen")
    episode_dir = resolve_inside(root, Path("episodes") / episode_id)
    episode_file = episode_dir / "episode.yaml"
    if episode_file.exists():
        _fail(f"Episode already exists: {episode_file}")
    episode = Episode(
        episode_id=episode_id,
        title=title,
        language=language or config.project.get("language", "vi-VN"),
        visual_style=config.project.get("visual_style", "to-be-decided"),
        aspect_ratio=config.output.aspect_ratio,
        target_fps=config.output.target_fps,
        shots=[],
    )
    episode_dir.mkdir(parents=True, exist_ok=True)
    (episode_dir / "prompts").mkdir(exist_ok=True)
    (episode_dir / "generation").mkdir(exist_ok=True)
    dump_model(episode, episode_file, overwrite=False)
    dump_model(ContinuityLedger(episode_id=episode_id), episode_dir / "continuity-ledger.yaml", overwrite=False)
    typer.echo(f"Initialized DRAFT episode: {episode_file}")


@storyboard_app.command("validate")
def storyboard_validate(episode_file: Path = typer.Argument(..., exists=True, dir_okay=False)) -> None:
    episode = _load_episode(episode_file)
    try:
        validate_episode_dependencies(episode)
    except ContinuityError as exc:
        _fail(str(exc))
    missing_prompts = [shot.shot_id for shot in episode.shots if not shot.prompt.strip()]
    typer.echo(f"Valid storyboard: {episode.episode_id}, {len(episode.shots)} shot(s)")
    if missing_prompts:
        typer.echo("Prompts not built yet: " + ", ".join(missing_prompts))


@prompts_app.command("build")
def prompts_build(
    episode_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    shot_id: str | None = typer.Option(None, "--shot-id", help="Build one eligible shot prompt"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Rebuild existing prompt text"),
) -> None:
    episode = _load_episode(episode_file)
    if not episode.shots:
        _fail("Episode has no shots")
    root = _find_project_root(episode_file)
    bibles = _load_character_bibles(root)
    world_bible = _load_world_bible(root)
    ledger = _load_ledger(episode_file.parent / "continuity-ledger.yaml", episode.episode_id)
    prompt_dir = episode_file.parent / "prompts"
    prompt_dir.mkdir(parents=True, exist_ok=True)
    updated = []
    built: list[str] = []
    deferred: list[str] = []
    for shot in episode.shots:
        if shot_id and shot.shot_id != shot_id:
            updated.append(shot)
            continue
        if shot.prompt.strip() and not overwrite:
            updated.append(shot)
            continue
        previous_state = None
        previous_frame = None
        previous_frame_disk_path = None
        references = list(shot.references)
        if shot.depends_on:
            dependencies_ready = True
            for dependency_id in shot.depends_on:
                entry = next((item for item in ledger.observations if item.shot_id == dependency_id), None)
                if entry is None or entry.status not in ("reviewed", "qc_passed") or entry.actual_end_state is None:
                    dependencies_ready = False
                    break
                previous_state = entry.actual_end_state
                previous_frame = (entry.extracted_frames or {}).get("last")
            previous_frame_disk_path = Path(previous_frame).resolve() if previous_frame else None
            if not dependencies_ready or not previous_frame_disk_path or not previous_frame_disk_path.is_file():
                deferred.append(shot.shot_id)
                updated.append(shot)
                continue
            relative_frame = previous_frame_disk_path.relative_to(root).as_posix()
            previous_frame = relative_frame
            if not any(ref.path == relative_frame for ref in references):
                from animation_studio.core.models import ReferenceSpec
                references.append(ReferenceSpec(
                    path=relative_frame,
                    role="previous-shot-last-frame",
                    governs="observed start pose, character placement and screen direction",
                    media_type="image",
                ))
        prompt_shot = shot.model_copy(update={"references": references})
        text = build_shot_prompt(
            prompt_shot,
            episode.visual_style,
            bibles,
            episode.aspect_ratio,
            previous_observed_state=previous_state,
            previous_last_frame=previous_frame,
            world_bible=world_bible,
            episode_locations=episode.locations,
        )
        prompt_path = prompt_dir / f"{shot.shot_id}.prompt.txt"
        if prompt_path.exists() and not overwrite:
            _fail(f"Prompt file exists; use --overwrite to regenerate: {prompt_path}")
        write_text(prompt_path, text.rstrip() + "\n", overwrite=overwrite)
        updated.append(prompt_shot.model_copy(update={"prompt": text}))
        built.append(shot.shot_id)
    if shot_id and not built and shot_id not in deferred:
        _fail(f"Shot not found: {shot_id}")
    episode = episode.model_copy(update={"shots": updated})
    dump_model(episode, episode_file, overwrite=True)
    typer.echo(f"Built {len(built)} prompt(s): {', '.join(built) if built else 'none'}")
    if deferred:
        typer.echo("Deferred until the predecessor clip is reviewed: " + ", ".join(deferred))
    typer.echo(f"Prompt files: {prompt_dir}")


@generation_app.command("plan")
def generation_plan(
    episode_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    shot_id: str | None = typer.Option(None, "--shot-id", help="Limit the manifest to one shot"),
    smoke_test: bool = typer.Option(False, "--smoke-test", help="Mark this as one user-approved provider smoke test"),
) -> None:
    episode = _load_episode(episode_file)
    root = _find_project_root(episode_file)
    config = _load_project(root)
    if smoke_test and not shot_id:
        _fail("--smoke-test requires --shot-id so the manifest contains exactly one request")
    try:
        validate_episode_dependencies(episode)
        ledger = _load_ledger(episode_file.parent / "continuity-ledger.yaml", episode.episode_id)
        shot_map = {shot.shot_id: shot for shot in episode.shots}
        selected_shots = [shot_map[shot_id]] if shot_id in shot_map else (episode.shots if not shot_id else [])
        if shot_id and not selected_shots:
            _fail(f"Unknown shot: {shot_id}")
        for shot in selected_shots:
            for dependency_id in shot.depends_on:
                previous = shot_map[dependency_id]
                can_advance(previous, shot, ledger)
        manifest = build_manifest(episode, config, selected_shot_id=shot_id)
        if smoke_test:
            manifest = manifest.model_copy(update={"smoke_test": True})
    except (ManifestError, ContinuityError, ValidationError) as exc:
        _fail(str(exc))
    output_dir = episode_file.parent / "generation"
    output_dir.mkdir(parents=True, exist_ok=True)
    output = output_dir / f"{manifest.manifest_id}.json"
    dump_model(manifest, output, overwrite=False)
    typer.echo(_summary_text(manifest))
    typer.echo(f"DRAFT manifest written: {output}")
    typer.echo("No request was sent. Usage remains unapproved until a known estimate and budget are recorded.")


@generation_app.command("approve")
def generation_approve(
    manifest_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    usage_estimate: str = typer.Option(..., "--usage-estimate", prompt="Observed/estimated provider usage"),
    budget_limit: str = typer.Option(..., "--budget-limit", prompt="Maximum approved usage or spend"),
    approved_by: str = typer.Option(getpass.getuser(), "--approved-by", help="Name or stable reviewer label"),
) -> None:
    try:
        manifest = load_model(manifest_file, GenerationManifest)
        root = _find_project_root(manifest_file)
        _ensure_storyboard_approved(root, manifest)
        typer.echo(_summary_text(manifest))
        typer.echo("Approval is for this exact request set and the usage/budget shown above.")
        if not typer.confirm("Approve this manifest and budget?", default=False):
            _fail("Manifest approval cancelled", code=2)
        approved = approve_manifest(
            manifest,
            usage_estimate=usage_estimate,
            budget_limit=budget_limit,
            approved_by=approved_by,
        )
        dump_model(approved, manifest_file, overwrite=True)
    except (ValidationError, ManifestError, OSError, StorageError) as exc:
        _fail(str(exc))
    typer.echo(f"Approved manifest {approved.manifest_id}; request hash {approved.approved_request_hash}")


def _make_provider(config: ProjectConfig, root: Path, *, allow_smoke_test: bool = False):
    mode = config.provider.mode
    if mode == "manual":
        return ManualProvider()
    if mode == "muse2api_experimental":
        api_key = os.getenv(config.provider.api_key_env)
        enabled = config.provider.verified_for_submission or allow_smoke_test
        return Muse2ApiProvider(
            base_url=config.provider.base_url,
            api_key=api_key,
            project_root=root,
            submission_enabled=enabled,
        )
    raise ProviderNotReady("No official video-generation provider adapter has been verified")


@generation_app.command("submit")
def generation_submit(manifest_file: Path = typer.Argument(..., exists=True, dir_okay=False)) -> None:
    try:
        manifest = load_model(manifest_file, GenerationManifest)
        ensure_approved_unchanged(manifest)
    except (ValidationError, ManifestError, OSError, StorageError) as exc:
        _fail(str(exc))
    root = _find_project_root(manifest_file)
    config = _load_project(root)
    if config.provider.mode != manifest.provider_mode:
        _fail("Provider mode changed after planning; create and approve a fresh manifest")
    if config.provider.mode == "muse2api_experimental" and not config.provider.verified_for_submission and not manifest.smoke_test:
        _fail("Muse2API is unverified. Only an explicitly approved one-shot smoke-test manifest may submit.")

    episode = _ensure_storyboard_approved(root, manifest)
    episode_file = root / "episodes" / manifest.episode_id / "episode.yaml"
    ledger = _load_ledger(episode_file.parent / "continuity-ledger.yaml", episode.episode_id)
    shots_by_id = {shot.shot_id: shot for shot in episode.shots}
    eligible = []
    for request in manifest.requests:
        shot = shots_by_id.get(request.shot_id)
        if shot is None:
            _fail(f"Manifest shot no longer exists in storyboard: {request.shot_id}")
        if request.depends_on:
            for dep_id in request.depends_on:
                previous = shots_by_id.get(dep_id)
                if previous is None:
                    _fail(f"Missing dependency shot {dep_id}")
                try:
                    can_advance(previous, shot, ledger)
                except ContinuityError:
                    break
            else:
                eligible.append(request)
        else:
            eligible.append(request)
        if request.continuity_level == "C3":
            break
        if len(eligible) < len([r for r in manifest.requests if r.order <= request.order]):
            break
    if not eligible:
        _fail("No shot is eligible: review the predecessor clip and update the continuity ledger first")
    if len(eligible) < len(manifest.requests):
        typer.echo(f"Continuity gate: submitting {len(eligible)} of {len(manifest.requests)} approved request(s) this turn.")
    typer.echo(_summary_text(manifest))
    typer.echo(f"Usage basis: {manifest.usage_estimate}; approved limit: {manifest.budget_limit}")
    if not typer.confirm(f"Submit {len(eligible)} request(s) to {manifest.provider_mode}?", default=False):
        _fail("Submission cancelled", code=2)

    try:
        provider = _make_provider(config, root, allow_smoke_test=manifest.smoke_test)
    except ProviderNotReady as exc:
        _fail(str(exc))
    queue_path = manifest_file.parent / "jobs.json"
    queue = _load_queue(queue_path, manifest.episode_id)
    existing_ids = {job.shot_id for job in queue.jobs}
    for request in eligible:
        if request.shot_id in existing_ids:
            _fail(f"A job already exists for {request.shot_id}; inspect queue before continuing")
        job = ShotJob(
            job_id=f"JOB-{manifest.manifest_id}-{request.shot_id}",
            shot_id=request.shot_id,
            provider_mode=manifest.provider_mode,
            status=JobStatus.PLANNED,
            prompt=request.prompt,
            request_parameters={
                "duration_seconds": request.duration_seconds,
                "aspect_ratio": request.aspect_ratio,
                "references": [ref.model_dump(mode="json") for ref in request.references],
                "continuity_level": request.continuity_level,
                "depends_on": request.depends_on,
            },
        )
        queue.jobs.append(job)
        video_request = VideoRequest(
            shot_id=request.shot_id,
            prompt=request.prompt,
            duration_seconds=request.duration_seconds,
            aspect_ratio=request.aspect_ratio,
            references=tuple(request.references),
        )
        try:
            result = provider.submit(video_request)
            next_status = JobStatus.AWAITING_MANUAL_MEDIA if result.status == "awaiting_manual_media" else JobStatus.QUEUED
            updated = transition_job(job, next_status, task_id=result.task_id)
            queue.jobs[-1] = updated
            typer.echo(f"{request.shot_id}: {updated.status}")
        except ProviderError as exc:
            queue.jobs[-1] = transition_job(job, JobStatus.FAILED, error=str(exc))
            dump_model(queue, queue_path, overwrite=True)
            _fail(f"Provider stopped; state saved. {exc}")
    manifest = manifest.model_copy(update={"status": "SUBMITTED"})
    dump_model(manifest, manifest_file, overwrite=True)
    dump_model(queue, queue_path, overwrite=True)
    typer.echo(f"Job queue saved: {queue_path}")
    if config.provider.mode == "manual":
        typer.echo("Manual handoff recorded. No video was created or sent by the CLI.")


@generation_app.command("status")
def generation_status(
    queue_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    refresh: bool = typer.Option(False, "--refresh", help="Poll remote task IDs; never resubmits work"),
) -> None:
    try:
        queue = load_model(queue_file, JobQueue)
    except (ValidationError, OSError, StorageError) as exc:
        _fail(str(exc))
    if refresh:
        root = _find_project_root(queue_file)
        config = _load_project(root)
        if config.provider.mode == "muse2api_experimental":
            provider = _make_provider(config, root)
            jobs = []
            for job in queue.jobs:
                if not job.task_id or job.status not in (JobStatus.QUEUED, JobStatus.RUNNING):
                    jobs.append(job)
                    continue
                try:
                    remote = provider.get_task(job.task_id)
                except ProviderError as exc:
                    _fail(f"Polling stopped at {job.shot_id}; no resubmission was attempted: {exc}")
                status = remote.status.lower()
                if status in {"processing", "running"} and job.status == JobStatus.QUEUED:
                    job = transition_job(job, JobStatus.RUNNING)
                elif status in {"completed", "succeeded", "success", "done"}:
                    if job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                        job = transition_job(job, JobStatus.GENERATED)
                elif status in {"failed", "error"} and job.status in (JobStatus.QUEUED, JobStatus.RUNNING):
                    job = transition_job(job, JobStatus.FAILED, error=str(remote.raw.get("error", "provider failed")))
                jobs.append(job)
            queue = queue.model_copy(update={"jobs": jobs})
            dump_model(queue, queue_file, overwrite=True)
    typer.echo(f"Episode {queue.episode_id}")
    if not queue.jobs:
        typer.echo("No jobs")
    for job in queue.jobs:
        typer.echo(f"{job.shot_id}: {job.status} | task={job.task_id or 'manual'} | output={job.output_path or '-'}")
        if job.error:
            typer.echo(f"  error: {job.error}")


@generation_app.command("import-media")
def generation_import_media(
    queue_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    shot_id: str = typer.Option(..., "--shot-id"),
    media_file: Path = typer.Option(..., "--media-file", exists=True, dir_okay=False),
    provider_model: str | None = typer.Option(None, "--provider-model", help="Model name/version used in the external UI, if known"),
) -> None:
    try:
        queue = load_model(queue_file, JobQueue)
    except (ValidationError, OSError, StorageError) as exc:
        _fail(f"Cannot load job queue {queue_file}: {exc}")
    matches = [job for job in queue.jobs if job.shot_id == shot_id]
    if len(matches) != 1:
        _fail(f"Expected one job for {shot_id}; found {len(matches)}")
    job = matches[0]
    if job.provider_mode != "manual":
        _fail(f"{shot_id} uses {job.provider_mode}; import-media only accepts ManualProvider jobs")
    if job.status != JobStatus.AWAITING_MANUAL_MEDIA:
        _fail(f"{shot_id} must be awaiting manual media, current status is {job.status}")

    root = _find_project_root(queue_file)
    episode_file = root / "episodes" / queue.episode_id / "episode.yaml"
    episode = _load_episode(episode_file)
    if episode.episode_id != queue.episode_id:
        _fail("Job queue episode_id does not match the episode storyboard")
    if shot_id not in {shot.shot_id for shot in episode.shots}:
        _fail(f"Shot not found in storyboard: {shot_id}")

    source = media_file.resolve()
    try:
        source_size = source.stat().st_size
    except OSError as exc:
        _fail(f"Cannot inspect source media {source}: {exc}")
    if source_size <= 0:
        _fail("Manual media file is empty")
    if source_size > MAX_IMPORTED_MEDIA_BYTES:
        _fail(f"Manual media exceeds the 2 GiB import limit: {source}")
    try:
        summary = inspect_media(source)
    except (MediaError, OSError, ValueError) as exc:
        _fail(f"Manual media failed ffprobe inspection: {exc}")
    if summary["duration_seconds"] <= 0 or summary["width"] <= 0 or summary["height"] <= 0:
        _fail("Manual media must have a positive duration and video dimensions")

    relative_output = Path("episodes") / queue.episode_id / "clips" / shot_id / source.name
    try:
        destination = resolve_inside(root, relative_output)
    except StorageError as exc:
        _fail(str(exc))
    if destination.exists():
        _fail(f"Refusing to overwrite imported media: {destination}")

    digest = hashlib.sha256()
    created_output = False
    try:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with source.open("rb") as incoming, destination.open("xb") as outgoing:
            created_output = True
            while chunk := incoming.read(1024 * 1024):
                digest.update(chunk)
                outgoing.write(chunk)
        imported_at = datetime.now(timezone.utc)
        metadata = {
            "duration_seconds": summary["duration_seconds"],
            "width": summary["width"],
            "height": summary["height"],
            "fps": summary["fps"],
            "video_codec": summary["video_codec"],
            "audio_streams": summary["audio_streams"],
            "size_bytes": summary["size_bytes"],
        }
        updated_job = transition_job(
            job,
            JobStatus.GENERATED,
            output_path=destination.relative_to(root).as_posix(),
            provider_model=provider_model.strip() if provider_model and provider_model.strip() else None,
            source_media_name=source.name,
            media_sha256=digest.hexdigest(),
            media_imported_at=imported_at,
            completed_at=imported_at,
            media_metadata=metadata,
        )
        updated_jobs = [updated_job if item.shot_id == shot_id else item for item in queue.jobs]
        dump_model(queue.model_copy(update={"jobs": updated_jobs}), queue_file, overwrite=True)
    except (OSError, StorageError, JobTransitionError) as exc:
        if created_output:
            destination.unlink(missing_ok=True)
        _fail(f"Could not import media for {shot_id}: {exc}")
    typer.echo(f"Imported and verified {source.name} for {shot_id}")
    typer.echo(f"Output: {destination.relative_to(root).as_posix()}")
    typer.echo(f"SHA-256: {digest.hexdigest()}")
    typer.echo("Job status: generated; continuity ledger remains unchanged until the clip is reviewed.")


@media_app.command("inspect")
def media_inspect(
    media_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    project_dir: Path = typer.Option(Path("."), "--project-dir", "-p"),
    frames_dir: Path | None = typer.Option(None, "--frames-dir", help="Project-relative output path for first/middle/last frames"),
) -> None:
    try:
        summary = inspect_media(media_file.resolve())
        typer.echo(json.dumps(summary, ensure_ascii=False, indent=2))
        if frames_dir is not None:
            root = project_dir.resolve()
            destination = resolve_inside(root, frames_dir)
            frames = extract_representative_frames(media_file.resolve(), destination)
            typer.echo("Extracted frames: " + ", ".join(f"{key}={value}" for key, value in frames.items()))
    except (MediaError, OSError, StorageError, ValueError) as exc:
        _fail(str(exc))


@continuity_app.command("update")
def continuity_update(
    episode_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    shot_id: str = typer.Option(..., "--shot-id"),
    actual_end_state_file: Path = typer.Option(..., "--actual-end-state", exists=True, dir_okay=False),
    frames_dir: Path = typer.Option(..., "--frames-dir", file_okay=False),
    note: list[str] = typer.Option([], "--note", help="Observation or inference note; repeat as needed"),
    risk: list[str] = typer.Option([], "--risk", help="Continuity risk; repeat as needed"),
) -> None:
    episode = _load_episode(episode_file)
    if shot_id not in {shot.shot_id for shot in episode.shots}:
        _fail(f"Shot not found in storyboard: {shot_id}")
    root = _find_project_root(episode_file)
    try:
        resolved_frames_dir = resolve_inside(root, frames_dir)
        if not resolved_frames_dir.is_dir():
            _fail(f"Frames directory not found inside project: {resolved_frames_dir}")
        state = load_model(actual_end_state_file, ShotState)
    except (ValidationError, OSError, StorageError) as exc:
        _fail(f"Invalid observed end state: {exc}")
    frame_paths = {label: resolved_frames_dir / f"{label}.png" for label in ("first", "middle", "last")}
    missing = [str(path) for path in frame_paths.values() if not path.is_file()]
    if missing:
        _fail("Missing representative frame(s): " + ", ".join(missing))
    ledger_path = episode_file.parent / "continuity-ledger.yaml"
    ledger = _load_ledger(ledger_path, episode.episode_id)
    queue_path = episode_file.parent / "generation" / "jobs.json"
    queue = _load_queue(queue_path, episode.episode_id) if queue_path.exists() else None
    updated_queue = None
    if queue is not None:
        jobs = [job for job in queue.jobs if job.shot_id == shot_id]
        if len(jobs) > 1:
            _fail(f"Multiple jobs found for {shot_id}; resolve the queue before review")
        if jobs:
            job = jobs[0]
            if job.status == JobStatus.GENERATED:
                if not job.output_path:
                    _fail(f"{shot_id} has no recorded media output; import or download it before review")
                try:
                    media_path = resolve_inside(root, job.output_path)
                except StorageError as exc:
                    _fail(f"Invalid media output path for {shot_id}: {exc}")
                if not media_path.is_file():
                    _fail(f"Recorded media output is missing for {shot_id}: {media_path}")
                reviewed_job = transition_job(job, JobStatus.REVIEWED)
                updated_queue = queue.model_copy(update={
                    "jobs": [reviewed_job if item.shot_id == shot_id else item for item in queue.jobs]
                })
            elif job.status not in (JobStatus.REVIEWED, JobStatus.QC_PASSED):
                _fail(f"{shot_id} must have imported/generated media before continuity review; current job status is {job.status}")
    try:
        updated = record_review(ledger, shot_id, state, frame_paths, note, risk)
    except ContinuityError as exc:
        _fail(str(exc))
    dump_model(updated, ledger_path, overwrite=True)
    if updated_queue is not None:
        dump_model(updated_queue, queue_path, overwrite=True)
    typer.echo(f"Recorded reviewed media state for {shot_id} in {ledger_path}")


@episode_app.command("render")
def episode_render(
    cut_list_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    project_dir: Path = typer.Option(Path("."), "--project-dir", "-p"),
    output_file: Path | None = typer.Option(None, "--out", help="Output MP4 path inside the project"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Replace only the specified output MP4"),
) -> None:
    root = project_dir.resolve()
    config = _load_project(root)
    try:
        cut_list = load_mapping(cut_list_file)
        clips = cut_list.get("clips")
        if not isinstance(clips, list) or not clips:
            _fail("Cut list must include a non-empty clips array")
        clip_paths = [resolve_inside(root, item["path"]) for item in clips]
        for clip in clip_paths:
            if not clip.is_file():
                _fail(f"Missing source clip: {clip}")
        output_dir = resolve_inside(root, config.paths.output_dir)
        output = resolve_inside(root, output_file or (output_dir / f"{cut_list.get('episode_id', 'episode')}.mp4"))
        if output.exists() and not overwrite:
            _fail(f"Output exists; pass --overwrite to replace: {output}")
        audio_tracks = [
            AudioTrack(
                path=resolve_inside(root, item["path"]),
                volume=float(item.get("volume", 1.0)),
                label=str(item.get("label", "audio")),
            )
            for item in cut_list.get("audio_tracks", [])
        ]
        subtitle = cut_list.get("subtitle")
        subtitle_path = resolve_inside(root, subtitle) if subtitle else None
        if any(not item.path.is_file() for item in audio_tracks) or (subtitle_path and not subtitle_path.is_file()):
            _fail("Audio/subtitle input does not exist")
        output.parent.mkdir(parents=True, exist_ok=True)
        list_file = output.parent / f".{output.stem}.{uuid4().hex}.ffconcat"
        write_text(list_file, concat_file_contents(clip_paths), overwrite=False)
        try:
            command = build_render_command(
                list_file,
                output,
                width=config.output.target_width,
                height=config.output.target_height,
                fps=config.output.target_fps,
                video_codec=config.output.video_codec,
                audio_codec=config.output.audio_codec,
                audio_tracks=audio_tracks,
                subtitle_file=subtitle_path,
                overwrite=overwrite,
            )
            run_command(command)
        finally:
            list_file.unlink(missing_ok=True)
    except (MediaError, OSError, StorageError, ValueError, KeyError) as exc:
        _fail(str(exc))
    typer.echo(f"Rendered: {output}")


@episode_app.command("qc")
def episode_qc(
    media_file: Path = typer.Argument(..., exists=True, dir_okay=False),
    project_dir: Path = typer.Option(Path("."), "--project-dir", "-p"),
) -> None:
    root = project_dir.resolve()
    config = _load_project(root)
    try:
        report = quality_report(
            media_file.resolve(),
            expected_width=config.output.target_width,
            expected_height=config.output.target_height,
            expected_fps=config.output.target_fps,
        )
        report_dir = resolve_inside(root, Path(config.paths.output_dir) / "qc")
        report_dir.mkdir(parents=True, exist_ok=True)
        report_path = report_dir / f"{media_file.stem}.{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.qc.json"
        write_text(report_path, json.dumps(report, ensure_ascii=False, indent=2) + "\n", overwrite=False)
    except (MediaError, OSError, StorageError, ValueError) as exc:
        _fail(str(exc))
    typer.echo(f"QC {report['status']}: {report_path}")
    typer.echo(json.dumps(report["checks"], indent=2))


if __name__ == "__main__":
    app()


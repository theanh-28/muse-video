from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel, ValidationError


T = TypeVar("T", bound=BaseModel)
REPO_ROOT = Path(__file__).resolve().parents[3]
_SECRET_ENV_MARKERS = ("MUSE2API", "COOKIE", "SESSION", "PASSWORD", "SECRET")


class CodexBridgeError(RuntimeError):
    """Codex CLI is unavailable or did not return valid schema-constrained JSON."""


def codex_executable() -> str | None:
    configured = os.getenv("ANISTUDIO_CODEX_EXE", "").strip()
    return configured or shutil.which("codex")


def _safe_environment() -> dict[str, str]:
    env = os.environ.copy()
    for key in tuple(env):
        if any(marker in key.upper() for marker in _SECRET_ENV_MARKERS):
            env.pop(key, None)
    return env


def _events(stdout: str) -> tuple[str | None, dict[str, int] | None]:
    final_text = None
    usage = None
    for line in stdout.splitlines():
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "item.completed":
            item = event.get("item", {})
            if item.get("type") == "agent_message" and isinstance(item.get("text"), str):
                final_text = item["text"]
        if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
            usage = {
                key: int(value)
                for key, value in event["usage"].items()
                if isinstance(value, int)
            }
    return final_text, usage


def _strict_output_schema(model: type[BaseModel]) -> dict[str, object]:
    """Adapt Pydantic JSON Schema to the strict subset accepted by Codex output-schema."""
    schema = model.model_json_schema()

    def normalize(node):
        if isinstance(node, dict):
            node.pop("default", None)
            for value in tuple(node.values()):
                normalize(value)
            if node.get("type") == "object" and isinstance(node.get("properties"), dict):
                node["additionalProperties"] = False
                node["required"] = list(node["properties"].keys())
        elif isinstance(node, list):
            for value in node:
                normalize(value)

    normalize(schema)
    return schema


def complete_structured(
    prompt: str,
    output_model: type[T],
    *,
    images: list[Path] | None = None,
    timeout_seconds: int = 900,
) -> tuple[T, dict[str, int] | None]:
    executable = codex_executable()
    if not executable:
        raise CodexBridgeError(
            "Codex CLI was not found. Install/sign in to Codex CLI or set ANISTUDIO_CODEX_EXE."
        )
    for image in images or []:
        if not image.is_file():
            raise CodexBridgeError(f"Requested Codex image does not exist: {image.name}")

    # Codex receives a temporary empty working directory, not the project tree.
    # The structured prompt and selected images are the only project inputs.
    with tempfile.TemporaryDirectory(prefix="anistudio-codex-") as directory:
        workdir = Path(directory)
        schema_path = workdir / "response.schema.json"
        schema_path.write_text(
            json.dumps(_strict_output_schema(output_model), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        command = [
            executable,
            "exec",
            "--ephemeral",
            "--ignore-user-config",
            "--skip-git-repo-check",
            "--sandbox",
            "read-only",
            "--json",
            "--output-schema",
            str(schema_path),
            "--cd",
            str(workdir),
        ]
        for image in images or []:
            command.extend(["--image", str(image.resolve())])
        command.append("-")
        creationflags = getattr(subprocess, "CREATE_NO_WINDOW", 0)
        try:
            result = subprocess.run(
                command,
                input=prompt,
                text=True,
                encoding="utf-8",
                capture_output=True,
                timeout=timeout_seconds,
                env=_safe_environment(),
                creationflags=creationflags,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise CodexBridgeError(
                f"Codex analysis exceeded {timeout_seconds} seconds; no project files were written."
            ) from exc
        except OSError as exc:
            raise CodexBridgeError(f"Could not start Codex CLI ({type(exc).__name__}).") from exc

        event_text, usage = _events(result.stdout)
        if result.returncode != 0:
            detail = "\n".join(part for part in (result.stderr, result.stdout) if part.strip()).strip()
            if not detail:
                detail = event_text or "Codex CLI exited without details"
            raise CodexBridgeError(detail[-2400:])
        raw = event_text
        if not raw:
            raise CodexBridgeError("Codex CLI completed without a final structured response.")
        try:
            data = json.loads(raw)
            return output_model.model_validate(data), usage
        except (json.JSONDecodeError, ValidationError) as exc:
            raise CodexBridgeError(
                "Codex response did not match the required production schema; nothing was written. "
                f"Details: {str(exc)[:1200]}"
            ) from exc


_COMMON_AUTHORING_PATHS = [
    REPO_ROOT / "AGENTS.md",
    REPO_ROOT / "docs" / "RESEARCH_NOTES.md",
    REPO_ROOT / "docs" / "CONTINUITY_SPEC.md",
    REPO_ROOT / "docs" / "GENERATION_SAFETY.md",
    REPO_ROOT / "config" / "project.example.yaml",
]

_STAGE_SKILL_SECTIONS = {
    ("storyboard", ".agents/skills/anistudio-cinematic-qa/SKILL.md"):
        "Camera and lighting during planning",
}

_STAGE_SKILL_PATHS = {
    "storyboard": [
        ".agents/skills/anistudio-story-continuity/SKILL.md",
        ".agents/skills/anistudio-drama-workbench/SKILL.md",
        ".agents/skills/anistudio-drama-workbench/references/shot-design-checklist.md",
        ".agents/skills/anistudio-cinematic-qa/SKILL.md",
    ],
    "shot_prompt": [
        ".agents/skills/anistudio-story-continuity/SKILL.md",
        ".agents/skills/anistudio-muse-prompting/SKILL.md",
        ".agents/skills/anistudio-muse-prompting/references/prompt-structure.md",
    ],
    "continuity_review": [
        ".agents/skills/anistudio-story-continuity/SKILL.md",
        ".agents/skills/anistudio-cinematic-qa/SKILL.md",
        ".agents/skills/anistudio-cinematic-qa/references/cinematic-and-evidence-checklist.md",
    ],
    "youtube_metadata": [
        ".agents/skills/yt/references/operating-guide.md",
        ".agents/skills/yt-package/SKILL.md",
        ".agents/skills/yt-thumbnail/SKILL.md",
        ".agents/skills/yt-seo/SKILL.md",
        ".agents/skills/yt-seo/references/youtube-metadata.md",
        "config/youtube/THEANHREVIEW_PROFILE.md",
    ],
}


def project_authoring_context(stage: str = "storyboard", *, include_chapters: bool = False) -> str:
    """Load the project rules and only the skill instructions relevant to this LLM stage.

    Structured Codex runs use a temporary working directory and ignore Codex config, so
    project-local skills must be passed as prompt context instead of relying on discovery.
    """
    if stage not in _STAGE_SKILL_PATHS:
        raise ValueError(f"Unknown authoring stage: {stage}")
    skill_paths = list(_STAGE_SKILL_PATHS[stage])
    if include_chapters and stage == "youtube_metadata":
        skill_paths.append(".agents/skills/yt-chapters/SKILL.md")
    sections = []
    for path in _COMMON_AUTHORING_PATHS:
        if not path.is_file():
            raise CodexBridgeError(f"Required project context file is missing: {path.relative_to(REPO_ROOT).as_posix()}")
        sections.append(f"## {path.relative_to(REPO_ROOT).as_posix()}\n{path.read_text(encoding='utf-8')}")
    for relative in skill_paths:
        path = REPO_ROOT / relative
        if not path.is_file():
            raise CodexBridgeError(f"Required project skill file is missing: {relative}")
        content = path.read_text(encoding="utf-8")
        section_name = _STAGE_SKILL_SECTIONS.get((stage, relative))
        if section_name:
            heading = f"## {section_name}"
            lines = content.splitlines()
            try:
                start = lines.index(heading)
            except ValueError as exc:
                raise CodexBridgeError(f"Required skill section is missing: {heading} ({relative})") from exc
            end = next((index for index in range(start + 1, len(lines)) if lines[index].startswith("## ")), len(lines))
            content = "\n".join(lines[start:end]).strip()
        sections.append(f"## {relative}\n{content}")
    return "\n\n".join(sections)

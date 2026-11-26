from __future__ import annotations

import json
import os
import tempfile
import threading
from pathlib import Path
from typing import Any, TypeVar

import yaml
from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)
_WRITE_LOCK = threading.RLock()


class StorageError(ValueError):
    """Invalid project path or unsafe file operation."""


def resolve_inside(root: Path, candidate: str | Path) -> Path:
    root = root.resolve()
    path = (root / candidate).resolve() if not Path(candidate).is_absolute() else Path(candidate).resolve()
    if not path.is_relative_to(root):
        raise StorageError(f"Path must remain inside project root: {candidate}")
    return path


def load_mapping(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(path)
    suffix = path.suffix.lower()
    text = path.read_text(encoding="utf-8")
    if suffix == ".json":
        payload = json.loads(text)
    elif suffix in {".yaml", ".yml"}:
        payload = yaml.safe_load(text)
    else:
        raise StorageError(f"Expected .yaml, .yml or .json: {path}")
    if not isinstance(payload, dict):
        raise StorageError(f"Expected a mapping at the document root: {path}")
    return payload


def load_model(path: Path, model_type: type[T]) -> T:
    return model_type.model_validate(load_mapping(path))


def dump_model(model: BaseModel, path: Path, *, overwrite: bool = True) -> Path:
    payload = model.model_dump(mode="json", exclude_none=False)
    if path.suffix.lower() == ".json":
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        text = yaml.safe_dump(payload, allow_unicode=True, sort_keys=False, default_flow_style=False)
    write_text(path, text, overwrite=overwrite)
    return path


def write_text(path: Path, text: str, *, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with _WRITE_LOCK:
        if not overwrite:
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
            return
        descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent, text=True)
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
                stream.write(text)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if temporary.exists():
                temporary.unlink()


"""Deterministic fingerprints for visual datasets and effective configuration."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO

from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION, VisualEngineConfig
from ade.visual.errors import VisualIntegrityError

DEFAULT_HASH_CHUNK_SIZE = 1024 * 1024
_WINDOWS_DRIVE = re.compile(r"^[A-Za-z]:")


@dataclass(frozen=True)
class VisualFileFingerprint:
    """Content identity for one dataset file."""

    relative_path: str
    sha256: str
    size_bytes: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "relative_path": self.relative_path,
            "sha256": self.sha256,
            "size_bytes": self.size_bytes,
        }


@dataclass(frozen=True)
class VisualDatasetFingerprint:
    """Stable dataset identity independent of enumeration and host paths."""

    schema_version: int
    fingerprint: str
    configuration_fingerprint: str
    backend_id: str
    backend_version: str
    files: tuple[VisualFileFingerprint, ...]

    @property
    def file_count(self) -> int:
        return len(self.files)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fingerprint": self.fingerprint,
            "configuration_fingerprint": self.configuration_fingerprint,
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "files": [item.to_dict() for item in self.files],
        }


def normalize_relative_path(value: str | Path) -> str:
    """Return one canonical POSIX-style relative path for any host syntax."""

    raw = str(value).replace("\\", "/")
    if not raw or raw.startswith("/") or _WINDOWS_DRIVE.match(raw):
        raise VisualIntegrityError("Fingerprint paths must be non-empty and relative")
    parts: list[str] = []
    for part in PurePosixPath(raw).parts:
        if part in {"", "."}:
            continue
        if part == "..":
            raise VisualIntegrityError("Fingerprint paths must not traverse parent directories")
        parts.append(part)
    if not parts:
        raise VisualIntegrityError("Fingerprint paths must identify a file")
    return "/".join(parts)


def sha256_stream(stream: BinaryIO, *, chunk_size: int = DEFAULT_HASH_CHUNK_SIZE) -> str:
    """Hash a binary stream without loading the complete content into memory."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    digest = hashlib.sha256()
    while chunk := stream.read(chunk_size):
        digest.update(chunk)
    return digest.hexdigest()


def sha256_file(path: Path, *, chunk_size: int = DEFAULT_HASH_CHUNK_SIZE) -> str:
    """Return the streaming SHA-256 digest for a local file."""

    with path.open("rb") as stream:
        return sha256_stream(stream, chunk_size=chunk_size)


def fingerprint_configuration(config: VisualEngineConfig | Mapping[str, Any]) -> str:
    """Return a canonical hash of effective typed visual configuration."""

    typed = (
        config
        if isinstance(config, VisualEngineConfig)
        else VisualEngineConfig.from_mapping(config)
    )
    payload = _canonical_json(typed.to_dict()).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def fingerprint_visual_content(
    root: Path,
    files: Iterable[Path],
    config: VisualEngineConfig,
    *,
    chunk_size: int = DEFAULT_HASH_CHUNK_SIZE,
) -> str:
    """Return a configuration-independent identity for dataset-role isolation."""

    entries = _fingerprint_visual_files(root, files, config, chunk_size=chunk_size)
    identity = {
        "schema_version": VISUAL_ENGINE_SCHEMA_VERSION,
        "files": [entry.to_dict() for entry in entries],
    }
    return hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()


def fingerprint_visual_dataset(
    root: Path,
    files: Iterable[Path],
    config: VisualEngineConfig,
    *,
    chunk_size: int = DEFAULT_HASH_CHUNK_SIZE,
) -> VisualDatasetFingerprint:
    """Fingerprint selected dataset files using paths, content, config, and backend identity."""

    entries = _fingerprint_visual_files(root, files, config, chunk_size=chunk_size)
    config_fingerprint = fingerprint_configuration(config)
    identity = {
        "schema_version": VISUAL_ENGINE_SCHEMA_VERSION,
        "configuration_fingerprint": config_fingerprint,
        "backend_id": config.backend_id,
        "backend_version": config.backend_version,
        "files": [entry.to_dict() for entry in entries],
    }
    fingerprint = hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()
    return VisualDatasetFingerprint(
        schema_version=VISUAL_ENGINE_SCHEMA_VERSION,
        fingerprint=fingerprint,
        configuration_fingerprint=config_fingerprint,
        backend_id=config.backend_id,
        backend_version=config.backend_version,
        files=entries,
    )


def _fingerprint_visual_files(
    root: Path,
    files: Iterable[Path],
    config: VisualEngineConfig,
    *,
    chunk_size: int,
) -> tuple[VisualFileFingerprint, ...]:
    """Validate and hash a bounded visual file set once in canonical order."""

    config.validate()
    resolved_root = root.resolve()
    if not resolved_root.exists() or not resolved_root.is_dir():
        raise FileNotFoundError(f"Dataset root is not a directory: {root}")

    selected: dict[str, Path] = {}
    for candidate in files:
        resolved = candidate.resolve()
        try:
            relative = resolved.relative_to(resolved_root)
        except ValueError as error:
            raise VisualIntegrityError(
                "Dataset files must resolve inside the dataset root",
                context={"path": str(candidate)},
            ) from error
        normalized = normalize_relative_path(relative)
        if normalized in selected:
            raise VisualIntegrityError(
                "Dataset file paths must be unique after normalization",
                context={"relative_path": normalized},
            )
        if not resolved.is_file():
            raise VisualIntegrityError(
                "Dataset fingerprint inputs must be files",
                context={"relative_path": normalized},
            )
        selected[normalized] = resolved

    if not selected:
        raise VisualIntegrityError("At least one file is required for a dataset fingerprint")
    if len(selected) > config.resources.max_files:
        raise VisualIntegrityError("Dataset exceeds configured max_files resource limit")

    max_bytes = config.resources.max_file_size_mb * 1024 * 1024
    entries: list[VisualFileFingerprint] = []
    for normalized in sorted(selected):
        path = selected[normalized]
        size = path.stat().st_size
        if size > max_bytes:
            raise VisualIntegrityError(
                "Dataset file exceeds configured max_file_size_mb",
                context={"relative_path": normalized, "size_bytes": size},
            )
        entries.append(
            VisualFileFingerprint(
                relative_path=normalized,
                sha256=sha256_file(path, chunk_size=chunk_size),
                size_bytes=size,
            )
        )
    return tuple(entries)


def fingerprint_visual_directory(
    root: Path,
    config: VisualEngineConfig,
    *,
    extensions: Iterable[str] | None = None,
) -> VisualDatasetFingerprint:
    """Fingerprint regular files below a directory in deterministic order."""

    allowed = {item.lower() for item in extensions} if extensions is not None else None
    files = (
        path
        for path in root.rglob("*")
        if path.is_file() and (allowed is None or path.suffix.lower() in allowed)
    )
    return fingerprint_visual_dataset(root, files, config)


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

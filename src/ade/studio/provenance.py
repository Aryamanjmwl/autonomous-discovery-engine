"""Content identity and effective configuration capture for Studio runs."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ade.config import load_config
from ade.studio.service import StudioPaths, resolve_workspace_input
from ade.visual.fingerprints import normalize_relative_path, sha256_file
from ade.visual.temporal_manifests import (
    load_temporal_manifest,
    resolve_temporal_dataset_root,
    serialize_temporal_manifest,
)

_PROVENANCE_SCHEMA_VERSION = "1.0"


@dataclass(frozen=True)
class StudioRunProvenance:
    """Immutable provenance captured immediately before a Studio workflow runs."""

    input_fingerprint: dict[str, object]
    effective_configuration: dict[str, object]


def capture_image_folder_provenance(
    input_path: Path | str,
    config_path: Path | str | None,
    *,
    paths: StudioPaths,
) -> StudioRunProvenance:
    """Fingerprint image candidates and snapshot the fully merged ADE configuration."""

    source = resolve_workspace_input(input_path, paths, kind="input path")
    if not source.is_dir():
        raise ValueError("Only visual/image-folder analysis is supported in ADE Studio.")
    resolved_config = (
        resolve_workspace_input(config_path, paths, kind="config file")
        if config_path is not None
        else None
    )
    if resolved_config is not None and not resolved_config.is_file():
        raise ValueError("Config path must identify a local file.")
    config = load_config(resolved_config)
    validation = config.get("validation", {})
    extensions = {
        str(value).lower()
        for value in validation.get("supported_image_extensions", [])
    }
    files = [
        candidate
        for candidate in source.rglob("*")
        if candidate.is_file() and candidate.suffix.lower() in extensions
    ]
    return StudioRunProvenance(
        input_fingerprint=_fingerprint_files("image_folder", source, files),
        effective_configuration=_configuration_snapshot(config),
    )


def capture_temporal_provenance(
    manifest_path: Path | str,
    *,
    strategy: str,
    patch_size: int | None,
    top_k: int,
    patch_top_k: int,
    paths: StudioPaths,
) -> StudioRunProvenance:
    """Fingerprint a temporal manifest and its referenced local files."""

    manifest = resolve_workspace_input(
        manifest_path,
        paths,
        kind="temporal manifest",
    )
    if not manifest.is_file():
        raise ValueError("Temporal manifest path must identify a local file.")
    sequence = load_temporal_manifest(manifest, strict=True)
    root = resolve_temporal_dataset_root(sequence, manifest)
    manifest_identity = json.loads(serialize_temporal_manifest(sequence))
    manifest_identity["dataset_root"] = "."
    canonical_manifest = _canonical_json(manifest_identity).encode("utf-8")
    entries = [
        _file_entry(
            "manifest",
            hashlib.sha256(canonical_manifest).hexdigest(),
            len(canonical_manifest),
        )
    ]
    referenced: dict[str, Path] = {}
    for observation in sequence.observations:
        referenced[f"image:{observation.source_path}"] = root / observation.source_path
        if observation.mask_path is not None:
            referenced[f"mask:{observation.mask_path}"] = root / observation.mask_path
    entries.extend(
        _file_entry(label, sha256_file(path), path.stat().st_size)
        for label, path in sorted(referenced.items())
    )
    return StudioRunProvenance(
        input_fingerprint=_fingerprint_entries("temporal_sequence", entries),
        effective_configuration=_configuration_snapshot(
            {
                "strategy": strategy,
                "patch_size": patch_size,
                "top_k": top_k,
                "patch_top_k": patch_top_k,
            }
        ),
    )


def _fingerprint_files(kind: str, root: Path, files: list[Path]) -> dict[str, object]:
    resolved_root = root.resolve()
    normalized = sorted(
        (
            normalize_relative_path(path.resolve().relative_to(resolved_root)),
            path,
        )
        for path in files
    )
    entries = [
        _file_entry(relative_path, sha256_file(path), path.stat().st_size)
        for relative_path, path in normalized
    ]
    return _fingerprint_entries(kind, entries)


def _file_entry(relative_path: str, digest: str, size_bytes: int) -> dict[str, object]:
    return {
        "relative_path": relative_path,
        "sha256": digest,
        "size_bytes": size_bytes,
    }


def _fingerprint_entries(kind: str, entries: list[dict[str, object]]) -> dict[str, object]:
    identity = {
        "schema_version": _PROVENANCE_SCHEMA_VERSION,
        "kind": kind,
        "files": entries,
    }
    sizes = [entry["size_bytes"] for entry in entries]
    if not all(isinstance(size, int) for size in sizes):  # pragma: no cover
        raise TypeError("Fingerprint entry sizes must be integers")
    return {
        "schema_version": _PROVENANCE_SCHEMA_VERSION,
        "kind": kind,
        "algorithm": "sha256",
        "digest": _sha256_json(identity),
        "file_count": len(entries),
        "total_size_bytes": sum(size for size in sizes if isinstance(size, int)),
    }


def _configuration_snapshot(config: dict[str, Any]) -> dict[str, object]:
    return {
        "schema_version": _PROVENANCE_SCHEMA_VERSION,
        "fingerprint": _sha256_json(config),
        "values": config,
    }


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )

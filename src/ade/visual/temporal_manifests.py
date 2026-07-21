"""Canonical codecs and validation for temporal observation manifests."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from datetime import datetime
from pathlib import Path, PurePosixPath
from typing import Any, TypeAlias

from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.errors import VisualIntegrityError, VisualManifestError
from ade.visual.fingerprints import normalize_relative_path
from ade.visual.temporal_contracts import TemporalObservation, TemporalObservationSequence

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
TemporalSortKey: TypeAlias = tuple[int, datetime | int, str]


def load_temporal_manifest(path: Path, *, strict: bool = False) -> TemporalObservationSequence:
    try:
        manifest = deserialize_temporal_manifest(path.read_bytes())
    except OSError as error:
        raise VisualManifestError("Temporal manifest could not be read") from error
    validate_temporal_manifest(manifest, manifest_path=path, strict=strict)
    return _ordered(manifest)


def serialize_temporal_manifest(manifest: TemporalObservationSequence) -> str:
    validate_temporal_manifest(manifest)
    return json.dumps(
        asdict(_ordered(manifest)),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def deserialize_temporal_manifest(payload: str | bytes) -> TemporalObservationSequence:
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise VisualManifestError("Temporal manifest is not valid UTF-8 JSON") from error
    data = _dict(data, "temporal manifest")
    _fields(
        data,
        {
            "schema_version",
            "dataset_name",
            "dataset_version",
            "dataset_root",
            "sequence_id",
            "scene_id",
            "entity_id",
            "observations",
            "metadata",
        },
    )
    observations = tuple(_observation(item) for item in _list(data["observations"], "observations"))
    result = TemporalObservationSequence(
        _int(data["schema_version"], "schema_version"),
        _string(data["dataset_name"], "dataset_name"),
        _string(data["dataset_version"], "dataset_version"),
        _string(data["dataset_root"], "dataset_root"),
        _string(data["sequence_id"], "sequence_id"),
        observations,
        _optional_string(data["scene_id"], "scene_id"),
        _optional_string(data["entity_id"], "entity_id"),
        _dict(data["metadata"], "metadata"),
    )
    validate_temporal_manifest(result)
    return _ordered(result)


def validate_temporal_manifest(
    manifest: TemporalObservationSequence,
    *,
    manifest_path: Path | None = None,
    strict: bool = False,
) -> None:
    if manifest.schema_version != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Temporal manifest schema version is unsupported")
    if not all(
        x.strip() for x in (manifest.dataset_name, manifest.dataset_version, manifest.sequence_id)
    ):
        raise VisualManifestError("Dataset name, version, and sequence ID must be non-empty")
    if len(manifest.observations) < 2:
        raise VisualIntegrityError("Temporal sequence must contain at least two observations")
    root = resolve_temporal_dataset_root(manifest, manifest_path)
    ids: set[str] = set()
    order_keys: set[object] = set()
    uses_timestamps = all(
        item.timestamp is not None and item.sequence_index is None for item in manifest.observations
    )
    uses_indexes = all(
        item.sequence_index is not None and item.timestamp is None for item in manifest.observations
    )
    if not (uses_timestamps or uses_indexes):
        raise VisualManifestError(
            "Observations must consistently use exactly one timestamp or sequence_index"
        )
    for item in manifest.observations:
        if not item.observation_id.strip() or item.observation_id in ids:
            raise VisualIntegrityError("Temporal observation IDs must be non-empty and unique")
        ids.add(item.observation_id)
        key: object
        if uses_timestamps:
            key = _valid_timestamp(item.timestamp)
        else:
            assert item.sequence_index is not None
            if item.sequence_index < 0:
                raise VisualManifestError("sequence_index must be non-negative")
            key = item.sequence_index
        if key in order_keys:
            raise VisualIntegrityError("Temporal observation ordering values must be unique")
        order_keys.add(key)
        image = _contained(root, _canonical_path(item.source_path, "source_path"))
        mask = (
            _contained(root, _canonical_path(item.mask_path, "mask_path"))
            if item.mask_path
            else None
        )
        if (
            item.width is not None
            and item.width <= 0
            or item.height is not None
            and item.height <= 0
        ):
            raise VisualManifestError("Image dimensions must be positive when provided")
        if item.image_sha256 is not None and not _SHA256.fullmatch(item.image_sha256):
            raise VisualManifestError("image_sha256 must be a lowercase SHA-256 digest")
        _json_safe(item.metadata)
        if strict and not image.is_file():
            raise VisualIntegrityError(
                "Strict temporal validation requires every image file to exist",
                context={"observation_id": item.observation_id, "source_path": item.source_path},
            )
        if strict and mask is not None and not mask.is_file():
            raise VisualIntegrityError(
                "Strict temporal validation requires every declared mask file to exist"
            )
    _json_safe(manifest.metadata)


def resolve_temporal_dataset_root(manifest: TemporalObservationSequence, path: Path | None) -> Path:
    value = manifest.dataset_root
    if not value.strip() or ".." in PurePosixPath(value.replace("\\", "/")).parts:
        raise VisualIntegrityError(
            "dataset_root must be non-empty and must not contain parent traversal"
        )
    root = Path(value)
    if not root.is_absolute():
        root = (path.resolve().parent if path else Path.cwd().resolve()) / root
    return root.resolve()


def _ordered(value: TemporalObservationSequence) -> TemporalObservationSequence:
    return TemporalObservationSequence(
        value.schema_version,
        value.dataset_name,
        value.dataset_version,
        value.dataset_root,
        value.sequence_id,
        tuple(sorted(value.observations, key=_temporal_sort_key)),
        value.scene_id,
        value.entity_id,
        value.metadata,
    )


def _temporal_sort_key(observation: TemporalObservation) -> TemporalSortKey:
    if observation.timestamp is not None:
        return (0, _valid_timestamp(observation.timestamp), observation.observation_id)
    assert observation.sequence_index is not None
    return (1, observation.sequence_index, observation.observation_id)


def _observation(value: object) -> TemporalObservation:
    data = _dict(value, "observation")
    _fields(
        data,
        {
            "observation_id",
            "source_path",
            "timestamp",
            "sequence_index",
            "entity_id",
            "scene_id",
            "metadata",
            "width",
            "height",
            "image_sha256",
            "mask_path",
        },
    )
    return TemporalObservation(
        _string(data["observation_id"], "observation_id"),
        _string(data["source_path"], "source_path"),
        _optional_string(data["timestamp"], "timestamp"),
        _optional_int(data["sequence_index"], "sequence_index"),
        _optional_string(data["entity_id"], "entity_id"),
        _optional_string(data["scene_id"], "scene_id"),
        _dict(data["metadata"], "metadata"),
        _optional_int(data["width"], "width"),
        _optional_int(data["height"], "height"),
        _optional_string(data["image_sha256"], "image_sha256"),
        _optional_string(data["mask_path"], "mask_path"),
    )


def _valid_timestamp(value: str | None) -> datetime:
    assert value is not None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise VisualManifestError("timestamp must be a valid ISO-8601 value") from error
    if parsed.tzinfo is None:
        raise VisualManifestError("timestamp must include a timezone offset")
    return parsed


def _canonical_path(value: str, name: str) -> str:
    normalized = normalize_relative_path(value)
    if normalized != value:
        raise VisualIntegrityError(f"{name} must be a canonical relative path")
    return normalized


def _contained(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise VisualIntegrityError("Temporal path resolves outside dataset root") from error
    return path


def _json_safe(value: object) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise VisualManifestError("Metadata must contain finite JSON-safe values") from error


def _fields(data: dict[str, Any], expected: set[str]) -> None:
    if set(data) != expected:
        raise VisualManifestError("Temporal manifest fields do not match the schema")


def _dict(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VisualManifestError(f"{name} must be an object")
    return value


def _list(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise VisualManifestError(f"{name} must be a list")
    return value


def _string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise VisualManifestError(f"{name} must be a string")
    return value


def _optional_string(value: object, name: str) -> str | None:
    return None if value is None else _string(value, name)


def _int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise VisualManifestError(f"{name} must be an integer")
    return value


def _optional_int(value: object, name: str) -> int | None:
    return None if value is None else _int(value, name)

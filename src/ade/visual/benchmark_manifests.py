"""Canonical manifest codecs and validation for externally provisioned benchmarks."""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path, PurePosixPath
from typing import Any

from ade.visual.benchmark_contracts import (
    VisualBenchmarkDatasetManifest,
    VisualBenchmarkLabel,
    VisualBenchmarkSample,
    VisualBenchmarkSplit,
)
from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.errors import VisualIntegrityError, VisualManifestError
from ade.visual.fingerprints import normalize_relative_path

_SPLIT_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]*$")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def load_visual_benchmark_manifest(
    path: Path, *, strict: bool = False
) -> VisualBenchmarkDatasetManifest:
    """Load and validate a canonical JSON benchmark manifest."""

    try:
        payload = path.read_bytes()
    except OSError as error:
        raise VisualManifestError("Benchmark manifest could not be read") from error
    manifest = deserialize_visual_benchmark_manifest(payload)
    validate_visual_benchmark_manifest(manifest, manifest_path=path, strict=strict)
    return manifest


def deserialize_visual_benchmark_manifest(
    payload: str | bytes,
) -> VisualBenchmarkDatasetManifest:
    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise VisualManifestError("Benchmark manifest is not valid UTF-8 JSON") from error
    if not isinstance(data, dict):
        raise VisualManifestError("Benchmark manifest root must be an object")
    _fields(
        data,
        {
            "schema_version",
            "dataset_name",
            "dataset_version",
            "dataset_root",
            "splits",
            "dataset_sha256",
            "metadata",
        },
        "benchmark manifest",
    )
    try:
        splits = tuple(_split(item) for item in _list(data["splits"], "splits"))
        manifest = VisualBenchmarkDatasetManifest(
            schema_version=_int(data["schema_version"], "schema_version"),
            dataset_name=_string(data["dataset_name"], "dataset_name"),
            dataset_version=_string(data["dataset_version"], "dataset_version"),
            dataset_root=_string(data["dataset_root"], "dataset_root"),
            splits=tuple(sorted(splits, key=lambda item: item.name)),
            dataset_sha256=_optional_string(data["dataset_sha256"], "dataset_sha256"),
            metadata=_dict(data["metadata"], "metadata"),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, VisualManifestError):
            raise
        raise VisualManifestError("Benchmark manifest values are invalid") from error
    validate_visual_benchmark_manifest(manifest)
    return manifest


def serialize_visual_benchmark_manifest(manifest: VisualBenchmarkDatasetManifest) -> str:
    """Return canonical JSON with deterministic split and sample ordering."""

    validate_visual_benchmark_manifest(manifest)
    ordered = VisualBenchmarkDatasetManifest(
        manifest.schema_version,
        manifest.dataset_name,
        manifest.dataset_version,
        manifest.dataset_root,
        tuple(
            VisualBenchmarkSplit(
                split.name, tuple(sorted(split.samples, key=lambda x: x.sample_id))
            )
            for split in sorted(manifest.splits, key=lambda x: x.name)
        ),
        manifest.dataset_sha256,
        manifest.metadata,
    )
    payload = asdict(ordered)
    for split in payload["splits"]:
        for sample in split["samples"]:
            sample["label"] = sample["label"].value
    return json.dumps(
        payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def validate_visual_benchmark_manifest(
    manifest: VisualBenchmarkDatasetManifest,
    *,
    manifest_path: Path | None = None,
    strict: bool = False,
) -> None:
    """Validate identities, labels, containment, checksums, and optional file existence."""

    if manifest.schema_version != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Benchmark manifest schema version is unsupported")
    if not manifest.dataset_name.strip() or not manifest.dataset_version.strip():
        raise VisualManifestError("Dataset name and version must be non-empty")
    root = _resolve_dataset_root(manifest.dataset_root, manifest_path)
    _checksum(manifest.dataset_sha256, "dataset_sha256")
    _json_safe(manifest.metadata, "manifest metadata")
    if not manifest.splits:
        raise VisualManifestError("Benchmark manifest must contain at least one split")
    split_names: set[str] = set()
    sample_ids: set[str] = set()
    image_paths: set[str] = set()
    total = 0
    for split in manifest.splits:
        if not _SPLIT_NAME.fullmatch(split.name) or split.name in split_names:
            raise VisualManifestError("Benchmark split names must be valid and unique")
        split_names.add(split.name)
        for sample in split.samples:
            total += 1
            if not sample.sample_id.strip() or sample.sample_id in sample_ids:
                raise VisualIntegrityError("Benchmark sample IDs must be non-empty and unique")
            sample_ids.add(sample.sample_id)
            if not isinstance(sample.label, VisualBenchmarkLabel):
                raise VisualManifestError("Benchmark sample label is invalid")
            image_relative = normalize_relative_path(sample.image_path)
            if image_relative != sample.image_path or image_relative in image_paths:
                raise VisualIntegrityError("Benchmark image paths must be canonical and unique")
            image_paths.add(image_relative)
            image = _contained(root, image_relative)
            mask = None
            if sample.mask_path is not None:
                mask_relative = normalize_relative_path(sample.mask_path)
                if mask_relative != sample.mask_path:
                    raise VisualIntegrityError("Benchmark mask path must be canonical")
                mask = _contained(root, mask_relative)
            _checksum(sample.image_sha256, "image_sha256")
            _checksum(sample.mask_sha256, "mask_sha256")
            _json_safe(sample.metadata, "sample metadata")
            if strict and not image.is_file():
                raise VisualIntegrityError(
                    "Strict benchmark validation requires every image file to exist",
                    context={"sample_id": sample.sample_id, "image_path": image_relative},
                )
            if strict and mask is not None and not mask.is_file():
                raise VisualIntegrityError(
                    "Strict benchmark validation requires every declared mask file to exist",
                    context={"sample_id": sample.sample_id, "mask_path": sample.mask_path},
                )
    if total == 0:
        raise VisualIntegrityError("Benchmark manifest must contain at least one sample")


def resolve_visual_benchmark_root(manifest: VisualBenchmarkDatasetManifest, path: Path) -> Path:
    return _resolve_dataset_root(manifest.dataset_root, path)


def _split(value: object) -> VisualBenchmarkSplit:
    data = _dict(value, "split")
    _fields(data, {"name", "samples"}, "split")
    samples = tuple(_sample(item) for item in _list(data["samples"], "samples"))
    return VisualBenchmarkSplit(
        _string(data["name"], "split name"),
        tuple(sorted(samples, key=lambda item: item.sample_id)),
    )


def _sample(value: object) -> VisualBenchmarkSample:
    data = _dict(value, "sample")
    _fields(
        data,
        {
            "sample_id",
            "image_path",
            "label",
            "mask_path",
            "anomaly_type",
            "category",
            "image_sha256",
            "mask_sha256",
            "metadata",
        },
        "sample",
    )
    try:
        label = VisualBenchmarkLabel(_string(data["label"], "label"))
    except ValueError as error:
        raise VisualManifestError("Benchmark label must be normal, anomaly, or unknown") from error
    return VisualBenchmarkSample(
        sample_id=_string(data["sample_id"], "sample_id"),
        image_path=_string(data["image_path"], "image_path"),
        label=label,
        mask_path=_optional_string(data["mask_path"], "mask_path"),
        anomaly_type=_optional_string(data["anomaly_type"], "anomaly_type"),
        category=_optional_string(data["category"], "category"),
        image_sha256=_optional_string(data["image_sha256"], "image_sha256"),
        mask_sha256=_optional_string(data["mask_sha256"], "mask_sha256"),
        metadata=_dict(data["metadata"], "metadata"),
    )


def _resolve_dataset_root(value: str, manifest_path: Path | None) -> Path:
    if not value.strip():
        raise VisualManifestError("dataset_root must be non-empty")
    portable = value.replace("\\", "/")
    if ".." in PurePosixPath(portable).parts:
        raise VisualIntegrityError("dataset_root must not contain parent traversal")
    root = Path(value)
    if not root.is_absolute():
        base = manifest_path.resolve().parent if manifest_path is not None else Path.cwd().resolve()
        root = base / root
    return root.resolve()


def _contained(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    try:
        path.relative_to(root)
    except ValueError as error:
        raise VisualIntegrityError("Benchmark sample path resolves outside dataset root") from error
    return path


def _checksum(value: str | None, name: str) -> None:
    if value is not None and not _SHA256.fullmatch(value):
        raise VisualManifestError(f"{name} must be a lowercase SHA-256 digest")


def _json_safe(value: object, name: str) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise VisualManifestError(f"{name} must contain finite JSON-safe values") from error


def _fields(data: dict[str, Any], expected: set[str], name: str) -> None:
    if set(data) != expected:
        raise VisualManifestError(f"{name} fields do not match the schema")


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

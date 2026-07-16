"""Immutable, integrity-checked storage for visual reference memory."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import shutil
import tempfile
from collections.abc import Iterable, Mapping
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

import numpy as np

from ade import __version__
from ade.visual.contracts import VisualArtifactManifest, VisualDatasetRole
from ade.visual.coreset import select_reference_coreset
from ade.visual.errors import (
    VisualContractVersionError,
    VisualDatasetRoleError,
    VisualIntegrityError,
    VisualManifestError,
)
from ade.visual.fingerprints import normalize_relative_path, sha256_file
from ade.visual.manifests import validate_artifact_integrity, write_manifest
from ade.visual.reference_contracts import (
    REFERENCE_MEMORY_SCHEMA_VERSION,
    LoadedReferenceMemory,
    ReferenceMemoryManifest,
    ReferenceVectorRecord,
    validate_reference_records,
)

_MEMORY_FILES = {"manifest.json", "vectors.npy", "records.jsonl"}
_HEX_DIGEST_LENGTH = 64


def build_reference_memory(
    records: Iterable[ReferenceVectorRecord],
    *,
    storage_root: Path,
    dataset_role: VisualDatasetRole,
    reference_dataset_fingerprint: str,
    configuration_fingerprint: str,
    backend_id: str,
    backend_version: str,
    distance_metric: str = "euclidean",
    coreset_strategy: str = "none",
    coreset_parameters: Mapping[str, Any] | None = None,
    maximum_vectors: int = 10_000,
    selection_ratio: float | None = None,
    random_seed: int = 42,
    query_dataset_fingerprint: str | None = None,
    validation_dataset_fingerprint: str | None = None,
) -> LoadedReferenceMemory:
    """Build or resolve one content-derived immutable reference-memory version."""

    _validate_reference_identity(
        dataset_role,
        reference_dataset_fingerprint,
        query_dataset_fingerprint,
        validation_dataset_fingerprint,
    )
    _validate_digest(configuration_fingerprint, "configuration_fingerprint")
    if not backend_id.strip() or not backend_version.strip():
        raise VisualIntegrityError("Reference-memory backend identity must be non-empty")
    if distance_metric not in {"euclidean", "cosine"}:
        raise VisualIntegrityError("Reference-memory metric must be euclidean or cosine")
    input_records = tuple(records)
    selection = select_reference_coreset(
        input_records,
        strategy=coreset_strategy,
        maximum_vectors=maximum_vectors,
        selection_ratio=selection_ratio,
        seed=random_seed,
        distance_metric=distance_metric,
    )
    materialized = selection.records
    dimension = validate_reference_records(materialized)
    vectors = np.ascontiguousarray(
        np.stack([record.vector for record in materialized]), dtype=np.float32
    )
    parameters = dict(selection.parameters)
    parameters.update(coreset_parameters or {})
    _ensure_json_safe(parameters, "coreset_parameters")
    memory_id = derive_reference_memory_id(
        materialized,
        reference_dataset_fingerprint=reference_dataset_fingerprint,
        configuration_fingerprint=configuration_fingerprint,
        backend_id=backend_id,
        backend_version=backend_version,
        distance_metric=distance_metric,
        coreset_strategy=coreset_strategy,
        coreset_parameters=parameters,
        random_seed=random_seed,
    )

    root = storage_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / memory_id
    if destination.exists():
        return load_reference_memory(
            destination,
            expected_backend_id=backend_id,
            expected_backend_version=backend_version,
            expected_dimension=dimension,
            expected_metric=distance_metric,
            expected_configuration_fingerprint=configuration_fingerprint,
        )

    temporary = Path(tempfile.mkdtemp(prefix=f".{memory_id}.", suffix=".tmp", dir=root))
    try:
        vector_path = temporary / "vectors.npy"
        with vector_path.open("wb") as stream:
            np.save(stream, vectors, allow_pickle=False)
            stream.flush()
            os.fsync(stream.fileno())
        metadata_path = temporary / "records.jsonl"
        with metadata_path.open("w", encoding="utf-8", newline="\n") as stream:
            for record in materialized:
                stream.write(_canonical_json(record.metadata_dict()) + "\n")
            stream.flush()
            os.fsync(stream.fileno())

        manifest = ReferenceMemoryManifest(
            schema_version=REFERENCE_MEMORY_SCHEMA_VERSION,
            memory_id=memory_id,
            created_at=datetime.now(UTC).isoformat(),
            reference_dataset_fingerprint=reference_dataset_fingerprint,
            configuration_fingerprint=configuration_fingerprint,
            backend_id=backend_id,
            backend_version=backend_version,
            vector_count=len(materialized),
            embedding_dimension=dimension,
            dtype="float32",
            distance_metric=distance_metric,
            coreset_strategy=coreset_strategy,
            coreset_parameters=parameters,
            random_seed=random_seed,
            vector_artifact=_artifact(vector_path, "reference-vectors", "numpy-array"),
            metadata_artifact=_artifact(metadata_path, "reference-records", "jsonl"),
            ade_version=__version__,
            python_version=platform.python_version(),
            completion_state="completed",
        )
        write_manifest(temporary / "manifest.json", serialize_reference_memory_manifest(manifest))
        validate_reference_memory(temporary, expected_memory_id=memory_id)
        try:
            os.rename(temporary, destination)
        except FileExistsError:
            return load_reference_memory(destination)
        temporary = Path()
        return load_reference_memory(destination)
    except (OSError, ValueError) as error:
        if isinstance(error, VisualIntegrityError | VisualManifestError):
            raise
        raise VisualIntegrityError(
            "Reference memory build failed before atomic publication",
            context={"memory_id": memory_id, "storage_root": str(root)},
        ) from error
    finally:
        if temporary != Path() and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def derive_reference_memory_id(
    records: tuple[ReferenceVectorRecord, ...],
    *,
    reference_dataset_fingerprint: str,
    configuration_fingerprint: str,
    backend_id: str,
    backend_version: str,
    distance_metric: str,
    coreset_strategy: str,
    coreset_parameters: Mapping[str, Any],
    random_seed: int,
) -> str:
    """Derive a stable ID from immutable content and provenance, excluding time."""

    validate_reference_records(records)
    vector_hash = hashlib.sha256()
    metadata_hash = hashlib.sha256()
    for record in records:
        vector_hash.update(np.asarray(record.vector, dtype="<f4", order="C").tobytes(order="C"))
        metadata_hash.update((_canonical_json(record.metadata_dict()) + "\n").encode("utf-8"))
    identity = {
        "schema_version": REFERENCE_MEMORY_SCHEMA_VERSION,
        "reference_dataset_fingerprint": reference_dataset_fingerprint,
        "configuration_fingerprint": configuration_fingerprint,
        "backend_id": backend_id,
        "backend_version": backend_version,
        "distance_metric": distance_metric,
        "coreset_strategy": coreset_strategy,
        "coreset_parameters": dict(coreset_parameters),
        "random_seed": random_seed,
        "vector_count": len(records),
        "embedding_dimension": int(records[0].vector.size),
        "vectors_sha256": vector_hash.hexdigest(),
        "records_sha256": metadata_hash.hexdigest(),
    }
    return hashlib.sha256(_canonical_json(identity).encode("utf-8")).hexdigest()


def load_reference_memory(
    memory_root: Path,
    *,
    memory_map: bool = True,
    expected_backend_id: str | None = None,
    expected_backend_version: str | None = None,
    expected_dimension: int | None = None,
    expected_metric: str | None = None,
    expected_configuration_fingerprint: str | None = None,
) -> LoadedReferenceMemory:
    """Load a fully validated immutable reference memory, optionally memory mapped."""

    manifest = validate_reference_memory(
        memory_root,
        expected_backend_id=expected_backend_id,
        expected_backend_version=expected_backend_version,
        expected_dimension=expected_dimension,
        expected_metric=expected_metric,
        expected_configuration_fingerprint=expected_configuration_fingerprint,
    )
    vector_path = memory_root.resolve() / manifest.vector_artifact.relative_path
    mmap_mode: Literal["r"] | None = "r" if memory_map else None
    try:
        vectors = np.load(vector_path, allow_pickle=False, mmap_mode=mmap_mode)
    except (OSError, ValueError) as error:
        raise VisualIntegrityError("Reference vector payload cannot be loaded") from error
    raw_records = _read_metadata(memory_root.resolve() / manifest.metadata_artifact.relative_path)
    records = tuple(
        _record_from_payload(payload, vectors[index]) for index, payload in enumerate(raw_records)
    )
    return LoadedReferenceMemory(memory_root.resolve(), manifest, vectors, records)


def validate_reference_memory(
    memory_root: Path,
    *,
    expected_memory_id: str | None = None,
    expected_backend_id: str | None = None,
    expected_backend_version: str | None = None,
    expected_dimension: int | None = None,
    expected_metric: str | None = None,
    expected_configuration_fingerprint: str | None = None,
) -> ReferenceMemoryManifest:
    """Validate layout, manifest, payload integrity, and compatibility."""

    root = memory_root.resolve()
    if not root.is_dir():
        raise VisualIntegrityError("Reference memory root must be a directory")
    actual_files = {path.name for path in root.iterdir()}
    if actual_files != _MEMORY_FILES or any(not path.is_file() for path in root.iterdir()):
        raise VisualIntegrityError(
            "Reference memory contains missing or unexpected files",
            context={"expected": sorted(_MEMORY_FILES), "actual": sorted(actual_files)},
        )
    manifest = deserialize_reference_memory_manifest((root / "manifest.json").read_bytes())
    if manifest.completion_state != "completed":
        raise VisualIntegrityError("Reference memory is not completed")
    if expected_memory_id is not None and manifest.memory_id != expected_memory_id:
        raise VisualIntegrityError("Reference memory ID does not match expected content identity")
    if root.name != manifest.memory_id and expected_memory_id is None:
        raise VisualIntegrityError("Reference memory directory name must match memory ID")
    _check_compatibility(
        manifest,
        expected_backend_id,
        expected_backend_version,
        expected_dimension,
        expected_metric,
        expected_configuration_fingerprint,
    )
    vector_path = validate_artifact_integrity(manifest.vector_artifact, root)
    metadata_path = validate_artifact_integrity(manifest.metadata_artifact, root)
    try:
        vectors = np.load(vector_path, allow_pickle=False, mmap_mode="r")
    except (OSError, ValueError) as error:
        raise VisualIntegrityError("Reference vector payload is malformed") from error
    if vectors.dtype != np.dtype("float32") or vectors.ndim != 2:
        raise VisualIntegrityError("Reference vectors must be a two-dimensional float32 array")
    if not vectors.flags.c_contiguous:
        raise VisualIntegrityError("Reference vectors must be C-contiguous")
    if vectors.shape != (manifest.vector_count, manifest.embedding_dimension):
        raise VisualIntegrityError("Reference vector shape does not match manifest")
    if not np.all(np.isfinite(vectors)):
        raise VisualIntegrityError("Reference vector payload contains non-finite values")
    payloads = _read_metadata(metadata_path)
    if len(payloads) != manifest.vector_count:
        raise VisualIntegrityError("Reference metadata count does not match vector count")
    records = tuple(
        _record_from_payload(payload, vectors[index])
        for index, payload in enumerate(payloads)
    )
    validate_reference_records(records)
    derived_memory_id = derive_reference_memory_id(
        records,
        reference_dataset_fingerprint=manifest.reference_dataset_fingerprint,
        configuration_fingerprint=manifest.configuration_fingerprint,
        backend_id=manifest.backend_id,
        backend_version=manifest.backend_version,
        distance_metric=manifest.distance_metric,
        coreset_strategy=manifest.coreset_strategy,
        coreset_parameters=manifest.coreset_parameters,
        random_seed=manifest.random_seed,
    )
    if derived_memory_id != manifest.memory_id:
        raise VisualIntegrityError("Reference memory ID does not match payload content")
    return manifest


def serialize_reference_memory_manifest(manifest: ReferenceMemoryManifest) -> str:
    """Return canonical JSON after strict reference-manifest validation."""

    _validate_manifest(manifest)
    return _canonical_json(_manifest_dict(manifest))


def deserialize_reference_memory_manifest(payload: str | bytes) -> ReferenceMemoryManifest:
    """Parse strict canonical-compatible reference-memory manifest JSON."""

    try:
        data = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise VisualManifestError("Reference-memory manifest is not valid JSON") from error
    if not isinstance(data, dict):
        raise VisualManifestError("Reference-memory manifest root must be an object")
    expected = set(_manifest_dict_keys())
    if set(data) != expected:
        raise VisualManifestError(
            "Reference-memory manifest fields do not match schema",
            context={
                "missing": sorted(expected - set(data)),
                "unknown": sorted(set(data) - expected),
            },
        )
    try:
        manifest = ReferenceMemoryManifest(
            schema_version=_strict_int(data["schema_version"], "schema_version"),
            memory_id=_strict_str(data["memory_id"], "memory_id"),
            created_at=_strict_str(data["created_at"], "created_at"),
            reference_dataset_fingerprint=_strict_str(
                data["reference_dataset_fingerprint"], "reference_dataset_fingerprint"
            ),
            configuration_fingerprint=_strict_str(
                data["configuration_fingerprint"], "configuration_fingerprint"
            ),
            backend_id=_strict_str(data["backend_id"], "backend_id"),
            backend_version=_strict_str(data["backend_version"], "backend_version"),
            vector_count=_strict_int(data["vector_count"], "vector_count"),
            embedding_dimension=_strict_int(
                data["embedding_dimension"], "embedding_dimension"
            ),
            dtype=_strict_str(data["dtype"], "dtype"),
            distance_metric=_strict_str(data["distance_metric"], "distance_metric"),
            coreset_strategy=_strict_str(data["coreset_strategy"], "coreset_strategy"),
            coreset_parameters=_strict_mapping(data["coreset_parameters"], "coreset_parameters"),
            random_seed=_strict_int(data["random_seed"], "random_seed"),
            vector_artifact=_artifact_from_dict(data["vector_artifact"]),
            metadata_artifact=_artifact_from_dict(data["metadata_artifact"]),
            ade_version=_strict_str(data["ade_version"], "ade_version"),
            python_version=_strict_str(data["python_version"], "python_version"),
            completion_state=_strict_str(data["completion_state"], "completion_state"),
        )
    except (TypeError, ValueError) as error:
        if isinstance(error, VisualManifestError):
            raise
        raise VisualManifestError("Reference-memory manifest contains invalid values") from error
    _validate_manifest(manifest)
    return manifest


def _artifact(path: Path, artifact_id: str, artifact_type: str) -> VisualArtifactManifest:
    return VisualArtifactManifest(
        schema_version=1,
        artifact_id=artifact_id,
        artifact_type=artifact_type,
        relative_path=path.name,
        sha256=sha256_file(path),
        size_bytes=path.stat().st_size,
        media_type="application/octet-stream" if path.suffix == ".npy" else "application/x-ndjson",
    )


def _artifact_dict(artifact: VisualArtifactManifest) -> dict[str, Any]:
    return {
        "schema_version": artifact.schema_version,
        "artifact_id": artifact.artifact_id,
        "artifact_type": artifact.artifact_type,
        "relative_path": artifact.relative_path,
        "sha256": artifact.sha256,
        "size_bytes": artifact.size_bytes,
        "media_type": artifact.media_type,
    }


def _artifact_from_dict(value: object) -> VisualArtifactManifest:
    data = _strict_mapping(value, "artifact")
    expected = {
        "schema_version",
        "artifact_id",
        "artifact_type",
        "relative_path",
        "sha256",
        "size_bytes",
        "media_type",
    }
    if set(data) != expected:
        raise VisualManifestError("Reference artifact fields do not match schema")
    media_type = data["media_type"]
    if media_type is not None and not isinstance(media_type, str):
        raise VisualManifestError("artifact.media_type must be a string or null")
    return VisualArtifactManifest(
        _strict_int(data["schema_version"], "artifact.schema_version"),
        _strict_str(data["artifact_id"], "artifact.artifact_id"),
        _strict_str(data["artifact_type"], "artifact.artifact_type"),
        _strict_str(data["relative_path"], "artifact.relative_path"),
        _strict_str(data["sha256"], "artifact.sha256"),
        _strict_int(data["size_bytes"], "artifact.size_bytes"),
        media_type,
    )


def _validate_manifest(manifest: ReferenceMemoryManifest) -> None:
    if manifest.schema_version != REFERENCE_MEMORY_SCHEMA_VERSION:
        raise VisualContractVersionError(
            f"Unsupported reference-memory schema version: {manifest.schema_version}"
        )
    for name, digest in {
        "memory_id": manifest.memory_id,
        "reference_dataset_fingerprint": manifest.reference_dataset_fingerprint,
        "configuration_fingerprint": manifest.configuration_fingerprint,
    }.items():
        _validate_digest(digest, name)
    if manifest.vector_count <= 0 or manifest.embedding_dimension <= 0:
        raise VisualManifestError("Reference-memory counts and dimensions must be positive")
    if manifest.dtype != "float32" or manifest.distance_metric not in {"euclidean", "cosine"}:
        raise VisualManifestError("Reference-memory dtype or metric is unsupported")
    if manifest.completion_state != "completed":
        raise VisualManifestError("Reference-memory completion_state must be completed")
    for artifact in (manifest.vector_artifact, manifest.metadata_artifact):
        normalized = normalize_relative_path(artifact.relative_path)
        if normalized != artifact.relative_path or "/" in artifact.relative_path:
            raise VisualManifestError("Reference-memory artifact paths must be canonical filenames")
    try:
        datetime.fromisoformat(manifest.created_at)
    except ValueError as error:
        raise VisualManifestError("created_at must be an ISO-8601 timestamp") from error


def _manifest_dict(manifest: ReferenceMemoryManifest) -> dict[str, Any]:
    return {
        "schema_version": manifest.schema_version,
        "memory_id": manifest.memory_id,
        "created_at": manifest.created_at,
        "reference_dataset_fingerprint": manifest.reference_dataset_fingerprint,
        "configuration_fingerprint": manifest.configuration_fingerprint,
        "backend_id": manifest.backend_id,
        "backend_version": manifest.backend_version,
        "vector_count": manifest.vector_count,
        "embedding_dimension": manifest.embedding_dimension,
        "dtype": manifest.dtype,
        "distance_metric": manifest.distance_metric,
        "coreset_strategy": manifest.coreset_strategy,
        "coreset_parameters": dict(manifest.coreset_parameters),
        "random_seed": manifest.random_seed,
        "vector_artifact": _artifact_dict(manifest.vector_artifact),
        "metadata_artifact": _artifact_dict(manifest.metadata_artifact),
        "ade_version": manifest.ade_version,
        "python_version": manifest.python_version,
        "completion_state": manifest.completion_state,
    }


def _manifest_dict_keys() -> tuple[str, ...]:
    return (
        "schema_version", "memory_id", "created_at", "reference_dataset_fingerprint",
        "configuration_fingerprint", "backend_id", "backend_version", "vector_count",
        "embedding_dimension", "dtype", "distance_metric", "coreset_strategy",
        "coreset_parameters", "random_seed", "vector_artifact", "metadata_artifact",
        "ade_version", "python_version", "completion_state",
    )


def _read_metadata(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    try:
        with path.open("r", encoding="utf-8") as stream:
            for line_number, line in enumerate(stream, start=1):
                if not line.endswith("\n") or not line.strip():
                    raise VisualIntegrityError(
                        "Reference metadata JSONL is truncated or contains blank records",
                        context={"line": line_number},
                    )
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise VisualIntegrityError("Reference metadata records must be objects")
                records.append(value)
    except (OSError, json.JSONDecodeError, UnicodeDecodeError) as error:
        if isinstance(error, VisualIntegrityError):
            raise
        raise VisualIntegrityError("Reference metadata JSONL is malformed") from error
    return records


def _record_from_payload(payload: Mapping[str, Any], vector: np.ndarray) -> ReferenceVectorRecord:
    expected = {
        "vector_id",
        "source_identity",
        "x",
        "y",
        "width",
        "height",
        "scale_id",
        "scale_label",
        "metadata",
    }
    if set(payload) != expected:
        raise VisualIntegrityError("Reference metadata record fields do not match schema")
    return ReferenceVectorRecord(
        vector_id=_strict_str(payload["vector_id"], "vector_id"),
        source_identity=_strict_str(payload["source_identity"], "source_identity"),
        vector=np.asarray(vector),
        x=_optional_int(payload["x"], "x"), y=_optional_int(payload["y"], "y"),
        width=_optional_int(payload["width"], "width"),
        height=_optional_int(payload["height"], "height"),
        scale_id=_optional_str(payload["scale_id"], "scale_id"),
        scale_label=_optional_str(payload["scale_label"], "scale_label"),
        metadata=_strict_mapping(payload["metadata"], "metadata"),
    )


def _check_compatibility(
    manifest: ReferenceMemoryManifest,
    backend_id: str | None,
    backend_version: str | None,
    dimension: int | None,
    metric: str | None,
    configuration_fingerprint: str | None,
) -> None:
    checks = {
        "backend_id": (manifest.backend_id, backend_id),
        "backend_version": (manifest.backend_version, backend_version),
        "embedding_dimension": (manifest.embedding_dimension, dimension),
        "distance_metric": (manifest.distance_metric, metric),
        "configuration_fingerprint": (
            manifest.configuration_fingerprint,
            configuration_fingerprint,
        ),
    }
    for name, (actual, expected) in checks.items():
        if expected is not None and actual != expected:
            raise VisualIntegrityError(
                f"Reference memory is incompatible with expected {name}",
                context={"expected": expected, "actual": actual},
            )


def _validate_reference_identity(
    role: VisualDatasetRole,
    reference: str,
    query: str | None,
    validation: str | None,
) -> None:
    if role is not VisualDatasetRole.REFERENCE:
        raise VisualDatasetRoleError(
            "Reference memory may only be built from the reference dataset role",
            context={"provided_role": role.value},
        )
    _validate_digest(reference, "reference_dataset_fingerprint")
    conflicts = [
        name
        for name, value in (("query", query), ("validation", validation))
        if value == reference
    ]
    if conflicts:
        raise VisualDatasetRoleError(
            "Reference dataset fingerprint conflicts with another dataset role",
            context={"roles": ["reference", *conflicts], "fingerprint": reference},
        )


def _validate_digest(value: str, name: str) -> None:
    invalid_character = any(
        character not in "0123456789abcdef" for character in value
    )
    if len(value) != _HEX_DIGEST_LENGTH or invalid_character:
        raise VisualIntegrityError(f"{name} must be a lowercase SHA-256 digest")


def _ensure_json_safe(value: object, name: str) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise VisualIntegrityError(f"{name} must be JSON-safe") from error


def _strict_mapping(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VisualManifestError(f"{name} must be an object")
    return dict(value)


def _strict_str(value: object, name: str) -> str:
    if not isinstance(value, str) or not value:
        raise VisualManifestError(f"{name} must be a non-empty string")
    return value


def _optional_str(value: object, name: str) -> str | None:
    return None if value is None else _strict_str(value, name)


def _strict_int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise VisualManifestError(f"{name} must be an integer")
    return value


def _optional_int(value: object, name: str) -> int | None:
    return None if value is None else _strict_int(value, name)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )

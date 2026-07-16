"""Strict codecs and integrity checks for versioned visual manifests."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.contracts import (
    VisualArtifactManifest,
    VisualDatasetRole,
    VisualReproducibilityManifest,
)
from ade.visual.errors import (
    VisualContractVersionError,
    VisualIntegrityError,
    VisualManifestError,
)
from ade.visual.fingerprints import normalize_relative_path, sha256_file

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def serialize_artifact_manifest(manifest: VisualArtifactManifest) -> str:
    """Serialize a validated artifact manifest to canonical JSON."""

    _validate_artifact(manifest)
    return _canonical_json(
        {
            "schema_version": manifest.schema_version,
            "artifact_id": manifest.artifact_id,
            "artifact_type": manifest.artifact_type,
            "relative_path": manifest.relative_path,
            "sha256": manifest.sha256,
            "size_bytes": manifest.size_bytes,
            "media_type": manifest.media_type,
        }
    )


def deserialize_artifact_manifest(payload: str | bytes) -> VisualArtifactManifest:
    """Deserialize artifact JSON with strict fields and types."""

    data = _json_object(payload)
    _require_fields(
        data,
        {
            "schema_version",
            "artifact_id",
            "artifact_type",
            "relative_path",
            "sha256",
            "size_bytes",
            "media_type",
        },
    )
    manifest = VisualArtifactManifest(
        schema_version=_int(data["schema_version"], "schema_version"),
        artifact_id=_string(data["artifact_id"], "artifact_id"),
        artifact_type=_string(data["artifact_type"], "artifact_type"),
        relative_path=_string(data["relative_path"], "relative_path"),
        sha256=_string(data["sha256"], "sha256"),
        size_bytes=_int(data["size_bytes"], "size_bytes"),
        media_type=_optional_string(data["media_type"], "media_type"),
    )
    _validate_artifact(manifest)
    return manifest


def serialize_reproducibility_manifest(manifest: VisualReproducibilityManifest) -> str:
    """Serialize validated reproducibility provenance to canonical JSON."""

    _validate_reproducibility(manifest)
    return _canonical_json(
        {
            "schema_version": manifest.schema_version,
            "dataset_fingerprints": {
                role.value: fingerprint
                for role, fingerprint in sorted(
                    manifest.dataset_fingerprints.items(), key=lambda item: item[0].value
                )
            },
            "configuration_fingerprint": manifest.configuration_fingerprint,
            "backend_id": manifest.backend_id,
            "backend_version": manifest.backend_version,
            "random_seed": manifest.random_seed,
            "deterministic": manifest.deterministic,
            "python_version": manifest.python_version,
            "ade_version": manifest.ade_version,
            "device": manifest.device,
        }
    )


def deserialize_reproducibility_manifest(
    payload: str | bytes,
) -> VisualReproducibilityManifest:
    """Deserialize reproducibility JSON with strict fields and role validation."""

    data = _json_object(payload)
    _require_fields(
        data,
        {
            "schema_version",
            "dataset_fingerprints",
            "configuration_fingerprint",
            "backend_id",
            "backend_version",
            "random_seed",
            "deterministic",
            "python_version",
            "ade_version",
            "device",
        },
    )
    raw_fingerprints = data["dataset_fingerprints"]
    if not isinstance(raw_fingerprints, dict):
        raise VisualManifestError("dataset_fingerprints must be an object")
    try:
        fingerprints = {
            VisualDatasetRole(_string(role, "dataset role")): _string(value, "fingerprint")
            for role, value in raw_fingerprints.items()
        }
    except ValueError as error:
        raise VisualManifestError(f"Unsupported dataset role: {error}") from error
    manifest = VisualReproducibilityManifest(
        schema_version=_int(data["schema_version"], "schema_version"),
        dataset_fingerprints=fingerprints,
        configuration_fingerprint=_string(
            data["configuration_fingerprint"], "configuration_fingerprint"
        ),
        backend_id=_string(data["backend_id"], "backend_id"),
        backend_version=_string(data["backend_version"], "backend_version"),
        random_seed=_int(data["random_seed"], "random_seed"),
        deterministic=_bool(data["deterministic"], "deterministic"),
        python_version=_string(data["python_version"], "python_version"),
        ade_version=_string(data["ade_version"], "ade_version"),
        device=_string(data["device"], "device"),
    )
    _validate_reproducibility(manifest)
    return manifest


def write_manifest(path: Path, payload: str, *, allow_replace: bool = False) -> Path:
    """Atomically publish canonical manifest JSON without replacing by default."""

    destination = path.resolve()
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    operation = "write_temporary"
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=destination.parent,
            prefix=f".{destination.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(payload.rstrip("\r\n") + "\n")
            stream.flush()
            os.fsync(stream.fileno())

        operation = "replace" if allow_replace else "publish"
        if allow_replace:
            os.replace(temporary_path, destination)
        else:
            os.link(temporary_path, destination)
            temporary_path.unlink()
        temporary_path = None
        return destination
    except OSError as error:
        if isinstance(error, FileExistsError) and destination.exists() and not allow_replace:
            message = "Manifest already exists; pass allow_replace=True to replace it explicitly"
        else:
            message = "Manifest could not be published atomically"
        raise VisualIntegrityError(
            message,
            context={
                "path": str(destination),
                "operation": operation,
                "allow_replace": allow_replace,
            },
        ) from error
    finally:
        if temporary_path is not None:
            try:
                temporary_path.unlink(missing_ok=True)
            except OSError:
                pass


def read_artifact_manifest(path: Path) -> VisualArtifactManifest:
    return deserialize_artifact_manifest(path.read_bytes())


def read_reproducibility_manifest(path: Path) -> VisualReproducibilityManifest:
    return deserialize_reproducibility_manifest(path.read_bytes())


def validate_artifact_integrity(manifest: VisualArtifactManifest, root: Path) -> Path:
    """Resolve an artifact inside root and verify its size and content digest."""

    _validate_artifact(manifest)
    artifact = (root.resolve() / manifest.relative_path).resolve()
    try:
        artifact.relative_to(root.resolve())
    except ValueError as error:
        raise VisualIntegrityError("Artifact path resolves outside the manifest root") from error
    if not artifact.is_file():
        raise VisualIntegrityError(f"Artifact does not exist: {manifest.relative_path}")
    if artifact.stat().st_size != manifest.size_bytes or sha256_file(artifact) != manifest.sha256:
        raise VisualIntegrityError(
            "Artifact content does not match its manifest",
            context={"relative_path": manifest.relative_path},
        )
    return artifact


def _validate_artifact(manifest: VisualArtifactManifest) -> None:
    _validate_version(manifest.schema_version)
    for name, value in {
        "artifact_id": manifest.artifact_id,
        "artifact_type": manifest.artifact_type,
    }.items():
        if not value.strip():
            raise VisualManifestError(f"{name} must be non-empty")
    normalized = normalize_relative_path(manifest.relative_path)
    if normalized != manifest.relative_path:
        raise VisualManifestError("relative_path must already use canonical normalization")
    if not _SHA256.fullmatch(manifest.sha256):
        raise VisualManifestError("sha256 must be a lowercase 64-character digest")
    if manifest.size_bytes < 0:
        raise VisualManifestError("size_bytes must be non-negative")
    if manifest.media_type is not None and not manifest.media_type.strip():
        raise VisualManifestError("media_type must be non-empty when provided")


def _validate_reproducibility(manifest: VisualReproducibilityManifest) -> None:
    _validate_version(manifest.schema_version)
    if VisualDatasetRole.QUERY not in manifest.dataset_fingerprints:
        raise VisualManifestError("dataset_fingerprints must include the query role")
    for role, fingerprint in manifest.dataset_fingerprints.items():
        if not isinstance(role, VisualDatasetRole) or not _SHA256.fullmatch(fingerprint):
            raise VisualManifestError("dataset fingerprints must use supported roles and SHA-256")
    roles_by_fingerprint: dict[str, list[str]] = {}
    for role, fingerprint in manifest.dataset_fingerprints.items():
        roles_by_fingerprint.setdefault(fingerprint, []).append(role.value)
    for fingerprint, roles in roles_by_fingerprint.items():
        if len(roles) > 1:
            raise VisualManifestError(
                "Identical dataset content cannot be assigned to multiple roles",
                context={"fingerprint": fingerprint, "roles": sorted(roles)},
            )
    if not _SHA256.fullmatch(manifest.configuration_fingerprint):
        raise VisualManifestError("configuration_fingerprint must be SHA-256")
    for name, value in {
        "backend_id": manifest.backend_id,
        "backend_version": manifest.backend_version,
        "python_version": manifest.python_version,
        "ade_version": manifest.ade_version,
        "device": manifest.device,
    }.items():
        if not value.strip():
            raise VisualManifestError(f"{name} must be non-empty")
    if manifest.random_seed < 0 or manifest.random_seed > 2**32 - 1:
        raise VisualManifestError("random_seed is outside the supported range")


def _validate_version(value: int) -> None:
    if value != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualContractVersionError(
            f"Unsupported visual manifest schema version: {value}",
            context={"supported_versions": [VISUAL_ENGINE_SCHEMA_VERSION]},
        )


def _json_object(payload: str | bytes) -> dict[str, Any]:
    try:
        value = json.loads(payload)
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise VisualManifestError("Manifest is not valid UTF-8 JSON") from error
    if not isinstance(value, dict):
        raise VisualManifestError("Manifest root must be an object")
    return value


def _require_fields(data: Mapping[str, Any], expected: set[str]) -> None:
    actual = set(data)
    if actual != expected:
        missing = sorted(expected - actual)
        unknown = sorted(actual - expected)
        raise VisualManifestError(
            "Manifest fields do not match the schema",
            context={"missing": missing, "unknown": unknown},
        )


def _string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise VisualManifestError(f"{name} must be a string")
    return value


def _optional_string(value: object, name: str) -> str | None:
    if value is None:
        return None
    return _string(value, name)


def _int(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise VisualManifestError(f"{name} must be an integer")
    return value


def _bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise VisualManifestError(f"{name} must be a boolean")
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)

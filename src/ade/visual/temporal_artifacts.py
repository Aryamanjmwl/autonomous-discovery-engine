"""Immutable canonical JSON artifacts for temporal change results."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any, cast

from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.errors import VisualIntegrityError, VisualManifestError
from ade.visual.fingerprints import normalize_relative_path, sha256_file
from ade.visual.temporal_contracts import TemporalChangeResult

TEMPORAL_ARTIFACT_TYPE = "temporal-visual-change-result"


def publish_temporal_change_artifact(result: TemporalChangeResult, output_root: Path) -> Path:
    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    payload = _canonical(asdict(result)) + "\n"
    artifact_id = hashlib.sha256(payload.encode()).hexdigest()
    destination = root / artifact_id
    if destination.exists():
        raise VisualIntegrityError("Completed temporal change artifact already exists")
    temporary = Path(tempfile.mkdtemp(prefix=f".{artifact_id}.", suffix=".tmp", dir=root))
    try:
        result_path = temporary / "temporal_change_result.json"
        result_path.write_text(payload, encoding="utf-8", newline="\n")
        _fsync(result_path)
        manifest = {
            "schema_version": VISUAL_ENGINE_SCHEMA_VERSION,
            "artifact_type": TEMPORAL_ARTIFACT_TYPE,
            "artifact_id": artifact_id,
            "result_path": result_path.name,
            "result_sha256": sha256_file(result_path),
            "result_size_bytes": result_path.stat().st_size,
        }
        manifest_path = temporary / "manifest.json"
        manifest_path.write_text(_canonical(manifest) + "\n", encoding="utf-8", newline="\n")
        _fsync(manifest_path)
        validate_temporal_change_artifact(temporary)
        os.rename(temporary, destination)
        temporary = Path()
        return destination
    except (OSError, ValueError) as error:
        if isinstance(error, (VisualIntegrityError, VisualManifestError)):
            raise
        raise VisualIntegrityError("Temporal artifact failed before atomic publication") from error
    finally:
        if temporary != Path() and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def validate_temporal_change_artifact(root: Path) -> dict[str, Any]:
    base = root.resolve()
    try:
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Temporal artifact manifest is malformed") from error
    expected = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "result_path",
        "result_sha256",
        "result_size_bytes",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected:
        raise VisualManifestError("Temporal artifact manifest does not match its schema")
    if (
        manifest["schema_version"] != VISUAL_ENGINE_SCHEMA_VERSION
        or manifest["artifact_type"] != TEMPORAL_ARTIFACT_TYPE
    ):
        raise VisualManifestError("Temporal artifact schema or type is unsupported")
    relative = normalize_relative_path(_string(manifest["result_path"]))
    path = (base / relative).resolve()
    try:
        path.relative_to(base)
    except ValueError as error:
        raise VisualIntegrityError("Temporal result path resolves outside artifact root") from error
    actual = {p.relative_to(base).as_posix() for p in base.rglob("*") if p.is_file()}
    if actual != {"manifest.json", relative}:
        raise VisualIntegrityError("Temporal artifact contains missing or unexpected files")
    if (
        not path.is_file()
        or path.stat().st_size != _int(manifest["result_size_bytes"])
        or sha256_file(path) != _string(manifest["result_sha256"])
    ):
        raise VisualIntegrityError("Temporal result content does not match its manifest")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Temporal result is malformed") from error
    if not isinstance(data, dict) or data.get("schema_version") != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Temporal result schema is unsupported")
    canonical = _canonical(data) + "\n"
    if canonical != path.read_text(encoding="utf-8"):
        raise VisualIntegrityError("Temporal result is not canonical JSON")
    if hashlib.sha256(canonical.encode()).hexdigest() != manifest["artifact_id"]:
        raise VisualIntegrityError("Temporal artifact identity does not match result content")
    return cast(dict[str, Any], data)


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _string(value: object) -> str:
    if not isinstance(value, str):
        raise VisualManifestError("Artifact string field has invalid type")
    return value


def _int(value: object) -> int:
    if not isinstance(value, int) or isinstance(value, bool) or value < 0:
        raise VisualManifestError("Artifact integer field has invalid type")
    return value


def _fsync(path: Path) -> None:
    with path.open("rb+") as stream:
        stream.flush()
        os.fsync(stream.fileno())

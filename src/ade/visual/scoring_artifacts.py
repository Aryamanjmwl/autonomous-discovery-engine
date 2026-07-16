"""Atomic persistence and integrity validation for reference scoring outputs."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import tempfile
import zlib
from pathlib import Path
from typing import Any

import numpy as np

from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION, VisualReferenceScoringConfig
from ade.visual.contracts import VisualArtifactManifest
from ade.visual.errors import VisualIntegrityError, VisualManifestError
from ade.visual.fingerprints import normalize_relative_path, sha256_file
from ade.visual.manifests import validate_artifact_integrity
from ade.visual.scoring_contracts import ReferenceScoringResult


def publish_scoring_artifacts(
    result: ReferenceScoringResult,
    output_root: Path,
    config: VisualReferenceScoringConfig,
) -> tuple[tuple[VisualArtifactManifest, ...], Path]:
    """Publish one immutable content-addressed scoring artifact directory."""

    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    destination = root / result.summary.scoring_id
    if destination.exists():
        raise VisualIntegrityError(
            "Completed scoring artifacts already exist",
            context={"scoring_id": result.summary.scoring_id},
        )
    temporary = Path(
        tempfile.mkdtemp(prefix=f".{result.summary.scoring_id}.", suffix=".tmp", dir=root)
    )
    try:
        artifacts: list[VisualArtifactManifest] = []
        for anomaly_map in result.anomaly_maps:
            stem = _safe_name(anomaly_map.image_id)
            if config.save_raw_maps:
                artifacts.append(
                    _save_array(
                        temporary,
                        f"maps/{stem}.raw.npy",
                        anomaly_map.raw_map,
                        f"raw-map:{anomaly_map.image_id}",
                    )
                )
            if config.save_coverage:
                artifacts.append(
                    _save_array(
                        temporary,
                        f"maps/{stem}.coverage.npy",
                        anomaly_map.coverage_counts,
                        f"coverage:{anomaly_map.image_id}",
                    )
                )
            if config.save_preview and anomaly_map.display_map is not None:
                artifacts.append(
                    _save_preview(
                        temporary,
                        f"previews/{stem}.png",
                        anomaly_map.display_map,
                        f"preview:{anomaly_map.image_id}",
                    )
                )
        summary_payload = _summary_payload(result, artifacts)
        summary_path = temporary / "summary.json"
        summary_path.write_text(
            _canonical_json(summary_payload) + "\n", encoding="utf-8", newline="\n"
        )
        _fsync(summary_path)
        summary_artifact = _artifact(summary_path, temporary, "scoring-summary", "application/json")
        artifacts.append(summary_artifact)
        manifest_payload = {
            "schema_version": VISUAL_ENGINE_SCHEMA_VERSION,
            "scoring_id": result.summary.scoring_id,
            "artifacts": [_artifact_payload(item) for item in artifacts],
        }
        manifest_path = temporary / "manifest.json"
        manifest_path.write_text(
            _canonical_json(manifest_payload) + "\n", encoding="utf-8", newline="\n"
        )
        _fsync(manifest_path)
        validate_scoring_artifacts(temporary, expected_scoring_id=result.summary.scoring_id)
        os.rename(temporary, destination)
        temporary = Path()
        return tuple(artifacts), destination
    except (OSError, ValueError) as error:
        if isinstance(error, VisualIntegrityError | VisualManifestError):
            raise
        raise VisualIntegrityError(
            "Scoring artifacts failed before atomic publication",
            context={"scoring_id": result.summary.scoring_id},
        ) from error
    finally:
        if temporary != Path() and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def validate_scoring_artifacts(
    root: Path, *, expected_scoring_id: str | None = None
) -> tuple[VisualArtifactManifest, ...]:
    """Validate the portable manifest and every declared artifact."""

    base = root.resolve()
    try:
        data = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Scoring artifact manifest is malformed") from error
    if (
        not isinstance(data, dict)
        or set(data) != {"schema_version", "scoring_id", "artifacts"}
        or data["schema_version"] != VISUAL_ENGINE_SCHEMA_VERSION
    ):
        raise VisualManifestError("Scoring artifact manifest does not match its schema")
    if expected_scoring_id is not None and data["scoring_id"] != expected_scoring_id:
        raise VisualIntegrityError("Scoring artifact identity does not match")
    raw = data["artifacts"]
    if not isinstance(raw, list):
        raise VisualManifestError("Scoring artifacts must be a list")
    artifacts = tuple(_artifact_from_payload(item) for item in raw)
    expected = {"manifest.json", *(item.relative_path for item in artifacts)}
    actual = {path.relative_to(base).as_posix() for path in base.rglob("*") if path.is_file()}
    if expected != actual:
        raise VisualIntegrityError(
            "Scoring artifact directory contains missing or unexpected files",
            context={"expected": sorted(expected), "actual": sorted(actual)},
        )
    for artifact in artifacts:
        path = validate_artifact_integrity(artifact, base)
        if artifact.artifact_type in {"numpy-array", "coverage-array"}:
            try:
                np.load(path, allow_pickle=False)
            except (OSError, ValueError) as error:
                raise VisualIntegrityError(
                    "Scoring NumPy artifact cannot be loaded safely"
                ) from error
    return artifacts


def _save_array(
    root: Path, relative: str, array: np.ndarray, artifact_id: str
) -> VisualArtifactManifest:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("wb") as stream:
        np.save(stream, array, allow_pickle=False)
        stream.flush()
        os.fsync(stream.fileno())
    kind = "coverage-array" if "coverage" in relative else "numpy-array"
    return _artifact(path, root, artifact_id, "application/x-npy", kind)


def _save_preview(
    root: Path, relative: str, display: np.ndarray, artifact_id: str
) -> VisualArtifactManifest:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    pixels = np.rint(np.clip(display, 0, 1) * 255).astype(np.uint8)
    height, width = pixels.shape
    scanlines = b"".join(b"\x00" + row.tobytes() for row in pixels)
    payload = b"\x89PNG\r\n\x1a\n"
    payload += _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0))
    payload += _png_chunk(b"IDAT", zlib.compress(scanlines, level=9))
    payload += _png_chunk(b"IEND", b"")
    path.write_bytes(payload)
    _fsync(path)
    return _artifact(path, root, artifact_id, "image/png", "preview")


def _artifact(
    path: Path, root: Path, artifact_id: str, media_type: str, artifact_type: str = "json"
) -> VisualArtifactManifest:
    return VisualArtifactManifest(
        VISUAL_ENGINE_SCHEMA_VERSION,
        artifact_id,
        artifact_type,
        normalize_relative_path(path.relative_to(root)),
        sha256_file(path),
        path.stat().st_size,
        media_type,
    )


def _artifact_payload(item: VisualArtifactManifest) -> dict[str, Any]:
    return {
        "schema_version": item.schema_version,
        "artifact_id": item.artifact_id,
        "artifact_type": item.artifact_type,
        "relative_path": item.relative_path,
        "sha256": item.sha256,
        "size_bytes": item.size_bytes,
        "media_type": item.media_type,
    }


def _artifact_from_payload(value: object) -> VisualArtifactManifest:
    if not isinstance(value, dict):
        raise VisualManifestError("Artifact entry must be an object")
    fields = {
        "schema_version",
        "artifact_id",
        "artifact_type",
        "relative_path",
        "sha256",
        "size_bytes",
        "media_type",
    }
    if set(value) != fields:
        raise VisualManifestError("Artifact entry fields do not match schema")
    try:
        return VisualArtifactManifest(
            int(value["schema_version"]),
            str(value["artifact_id"]),
            str(value["artifact_type"]),
            str(value["relative_path"]),
            str(value["sha256"]),
            int(value["size_bytes"]),
            None if value["media_type"] is None else str(value["media_type"]),
        )
    except (TypeError, ValueError) as error:
        raise VisualManifestError("Artifact entry contains invalid values") from error


def _summary_payload(
    result: ReferenceScoringResult, artifacts: list[VisualArtifactManifest]
) -> dict[str, Any]:
    summary = result.summary
    return {
        "schema_version": VISUAL_ENGINE_SCHEMA_VERSION,
        "scoring_id": summary.scoring_id,
        "calibrated": False,
        "metric": summary.metric,
        "patch_strategy": summary.patch_strategy,
        "neighbor_count": summary.neighbor_count,
        "image_aggregation": summary.image_aggregation,
        "top_fraction": summary.top_fraction,
        "map_projection": summary.map_projection,
        "multi_scale_fusion": summary.multi_scale_fusion,
        "smoothing_sigma": summary.smoothing_sigma,
        "query_dataset_fingerprint": summary.query_dataset_fingerprint,
        "reference_dataset_fingerprint": summary.reference_dataset_fingerprint,
        "reference_memory_id": summary.reference_memory_id,
        "configuration_fingerprint": summary.configuration_fingerprint,
        "backend_id": summary.backend_id,
        "backend_version": summary.backend_version,
        "deterministic": summary.deterministic,
        "device": summary.device,
        "images": [
            {
                "image_id": image.image_id,
                "raw_score": image.raw_score,
                "selected_patch_ids": list(image.selected_patch_ids),
            }
            for image in result.image_scores
        ],
        "maps": [
            {
                "image_id": item.image_id,
                "width": item.width,
                "height": item.height,
                "coverage_fraction": item.coverage_fraction,
                "uncovered_policy": item.uncovered_policy,
            }
            for item in result.anomaly_maps
        ],
        "artifacts": [_artifact_payload(item) for item in artifacts],
    }


def _safe_name(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _fsync(path: Path) -> None:
    with path.open("rb+") as stream:
        os.fsync(stream.fileno())


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    body = kind + payload
    return struct.pack(">I", len(payload)) + body + struct.pack(">I", zlib.crc32(body))

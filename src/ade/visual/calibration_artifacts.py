"""Deterministic JSON persistence for calibration and threshold evaluation results."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ade.visual.calibration_contracts import (
    CalibrationDatasetSummary,
    CalibrationProvenance,
    CalibrationResult,
    FittedCalibrationModel,
    OperatingPointSummary,
    ScoreDistributionSummary,
    ThresholdCandidate,
    ThresholdEvaluationResult,
)
from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.errors import VisualIntegrityError, VisualManifestError
from ade.visual.fingerprints import normalize_relative_path, sha256_file

CALIBRATION_ARTIFACT_TYPE = "visual-calibration-threshold-evaluation"


def publish_calibration_artifact(result: CalibrationResult, output_root: Path) -> Path:
    """Publish one immutable, content-addressed calibration result directory."""

    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    payload = _canonical_json(asdict(result)) + "\n"
    artifact_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    destination = root / artifact_id
    if destination.exists():
        raise VisualIntegrityError("Completed calibration artifact already exists")
    temporary = Path(tempfile.mkdtemp(prefix=f".{artifact_id}.", suffix=".tmp", dir=root))
    try:
        result_path = temporary / "calibration.json"
        result_path.write_text(payload, encoding="utf-8", newline="\n")
        _fsync(result_path)
        manifest = {
            "schema_version": VISUAL_ENGINE_SCHEMA_VERSION,
            "artifact_type": CALIBRATION_ARTIFACT_TYPE,
            "artifact_id": artifact_id,
            "result_path": "calibration.json",
            "result_sha256": sha256_file(result_path),
            "result_size_bytes": result_path.stat().st_size,
        }
        manifest_path = temporary / "manifest.json"
        manifest_path.write_text(_canonical_json(manifest) + "\n", encoding="utf-8", newline="\n")
        _fsync(manifest_path)
        validate_calibration_artifact(temporary)
        os.rename(temporary, destination)
        temporary = Path()
        return destination
    except (OSError, ValueError) as error:
        if isinstance(error, VisualIntegrityError | VisualManifestError):
            raise
        raise VisualIntegrityError(
            "Calibration artifact failed before atomic publication"
        ) from error
    finally:
        if temporary != Path() and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def validate_calibration_artifact(root: Path) -> CalibrationResult:
    """Validate manifest structure, path containment, digest, size, and result schema."""

    base = root.resolve()
    try:
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Calibration artifact manifest is malformed") from error
    expected = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "result_path",
        "result_sha256",
        "result_size_bytes",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected:
        raise VisualManifestError("Calibration artifact manifest does not match its schema")
    if manifest["schema_version"] != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Calibration artifact schema version is unsupported")
    if manifest["artifact_type"] != CALIBRATION_ARTIFACT_TYPE:
        raise VisualManifestError("Calibration artifact type is unsupported")
    relative = normalize_relative_path(_string(manifest["result_path"], "result_path"))
    result_path = (base / relative).resolve()
    try:
        result_path.relative_to(base)
    except ValueError as error:
        raise VisualIntegrityError(
            "Calibration result path resolves outside artifact root"
        ) from error
    actual_files = {path.relative_to(base).as_posix() for path in base.rglob("*") if path.is_file()}
    if actual_files != {"manifest.json", relative}:
        raise VisualIntegrityError("Calibration artifact contains missing or unexpected files")
    size = manifest["result_size_bytes"]
    digest = _string(manifest["result_sha256"], "result_sha256")
    if not isinstance(size, int) or isinstance(size, bool) or size < 0:
        raise VisualManifestError("result_size_bytes must be a non-negative integer")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise VisualManifestError("result_sha256 must be a lowercase SHA-256 digest")
    if (
        not result_path.is_file()
        or result_path.stat().st_size != size
        or sha256_file(result_path) != digest
    ):
        raise VisualIntegrityError("Calibration result content does not match its manifest")
    try:
        raw = result_path.read_bytes()
        data = json.loads(raw)
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Calibration result is malformed") from error
    artifact_id = _string(manifest["artifact_id"], "artifact_id")
    if hashlib.sha256(raw).hexdigest() != artifact_id:
        raise VisualIntegrityError("Calibration artifact identity does not match its content")
    return _result_from_dict(data)


def _result_from_dict(value: object) -> CalibrationResult:
    data = _dict(value, "calibration result")
    try:
        dataset_raw = _dict(data["dataset"], "dataset")
        fitted_raw = _dict(data["fitted_model"], "fitted_model")
        provenance_raw = _dict(data["provenance"], "provenance")
        distribution = _distribution(_dict(dataset_raw["distribution"], "dataset distribution"))
        fitted_distribution = _distribution(
            _dict(fitted_raw["distribution"], "fitted distribution")
        )
        dataset = CalibrationDatasetSummary(
            str(dataset_raw["score_source"]),
            str(dataset_raw["score_type"]),
            int(dataset_raw["score_count"]),
            distribution,
            bool(dataset_raw["labels_available"]),
            _optional_int(dataset_raw["positive_count"]),
            _optional_int(dataset_raw["negative_count"]),
        )
        fitted = FittedCalibrationModel(
            method=fitted_raw["method"],
            fitted_at=str(fitted_raw["fitted_at"]),
            score_source=str(fitted_raw["score_source"]),
            score_count=int(fitted_raw["score_count"]),
            distribution=fitted_distribution,
            calibrated=bool(fitted_raw["calibrated"]),
            config_fingerprint=str(fitted_raw["config_fingerprint"]),
            data_fingerprint=str(fitted_raw["data_fingerprint"]),
            parameters=_dict(fitted_raw["parameters"], "parameters"),
            warnings=tuple(str(item) for item in fitted_raw["warnings"]),
        )
        evaluations = tuple(
            _evaluation(_dict(item, "threshold evaluation"))
            for item in data["threshold_evaluations"]
        )
        operating = tuple(
            OperatingPointSummary(
                str(item["candidate_id"]),
                item["threshold_strategy"],
                float(item["score_threshold"]),
                int(item["selected_count"]),
                float(item["selected_fraction"]),
                bool(item["requires_human_review"]),
            )
            for raw_item in data["operating_points"]
            for item in [_dict(raw_item, "operating point")]
        )
        provenance = CalibrationProvenance(
            str(provenance_raw["source_score_artifact"]),
            str(provenance_raw["source_score_fingerprint"]),
            str(provenance_raw["score_type"]),
            provenance_raw["calibration_method"],
            str(provenance_raw["threshold_strategy"]),
            str(provenance_raw["config_fingerprint"]),
            str(provenance_raw["data_fingerprint"]),
            str(provenance_raw["generated_at"]),
            bool(provenance_raw["calibrated"]),
            bool(provenance_raw["human_review_required"]),
            tuple(str(item) for item in provenance_raw["limitations"]),
        )
        result = CalibrationResult(
            int(data["schema_version"]),
            dataset,
            fitted,
            tuple(float(item) for item in data["calibrated_scores"]),
            evaluations,
            operating,
            provenance,
        )
    except (KeyError, TypeError, ValueError) as error:
        raise VisualManifestError("Calibration result does not match its schema") from error
    if result.schema_version != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Calibration result schema version is unsupported")
    return result


def _distribution(data: dict[str, Any]) -> ScoreDistributionSummary:
    return ScoreDistributionSummary(
        int(data["count"]),
        float(data["minimum"]),
        float(data["maximum"]),
        float(data["mean"]),
        float(data["std"]),
        {str(key): float(value) for key, value in _dict(data["quantiles"], "quantiles").items()},
    )


def _evaluation(data: dict[str, Any]) -> ThresholdEvaluationResult:
    candidate_raw = _dict(data["candidate"], "threshold candidate")
    candidate = ThresholdCandidate(
        candidate_raw["strategy"],
        float(candidate_raw["value"]),
        float(candidate_raw["score_threshold"]),
        float(candidate_raw["score_quantile"]),
        str(candidate_raw["candidate_id"]),
    )
    selected_range = data["score_range_selected"]
    return ThresholdEvaluationResult(
        candidate=candidate,
        selected_count=int(data["selected_count"]),
        selected_fraction=float(data["selected_fraction"]),
        score_range_selected=(
            None if selected_range is None else (float(selected_range[0]), float(selected_range[1]))
        ),
        supervised_metrics_available=bool(data["supervised_metrics_available"]),
        true_positives=_optional_int(data["true_positives"]),
        false_positives=_optional_int(data["false_positives"]),
        true_negatives=_optional_int(data["true_negatives"]),
        false_negatives=_optional_int(data["false_negatives"]),
        precision=_optional_float(data["precision"]),
        recall=_optional_float(data["recall"]),
        f1=_optional_float(data["f1"]),
        warnings=tuple(str(item) for item in data["warnings"]),
    )


def _dict(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VisualManifestError(f"{name} must be an object")
    return value


def _string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise VisualManifestError(f"{name} must be a string")
    return value


def _optional_int(value: object) -> int | None:
    if value is None:
        return None
    if not isinstance(value, int) or isinstance(value, bool):
        raise VisualManifestError("Expected an integer or null")
    return value


def _optional_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise VisualManifestError("Expected a number or null")
    return float(value)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _fsync(path: Path) -> None:
    with path.open("rb+") as stream:
        os.fsync(stream.fileno())

"""Immutable JSON artifacts for visual benchmark validation results."""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Any

from ade.visual.benchmark_contracts import (
    VisualBenchmarkMetricSummary,
    VisualBenchmarkOperatingPointResult,
    VisualBenchmarkPrediction,
    VisualBenchmarkProvenance,
    VisualBenchmarkResult,
)
from ade.visual.calibration_contracts import ScoreDistributionSummary
from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.errors import VisualIntegrityError, VisualManifestError
from ade.visual.fingerprints import normalize_relative_path, sha256_file

BENCHMARK_ARTIFACT_TYPE = "visual-benchmark-evaluation"


def publish_visual_benchmark_artifact(result: VisualBenchmarkResult, output_root: Path) -> Path:
    """Publish one immutable content-addressed evaluation artifact directory."""

    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    payload = _canonical(asdict(result)) + "\n"
    artifact_id = hashlib.sha256(payload.encode()).hexdigest()
    destination = root / artifact_id
    if destination.exists():
        raise VisualIntegrityError("Completed benchmark evaluation artifact already exists")
    temporary = Path(tempfile.mkdtemp(prefix=f".{artifact_id}.", suffix=".tmp", dir=root))
    try:
        result_path = temporary / "benchmark_result.json"
        result_path.write_text(payload, encoding="utf-8", newline="\n")
        _fsync(result_path)
        manifest = {
            "schema_version": VISUAL_ENGINE_SCHEMA_VERSION,
            "artifact_type": BENCHMARK_ARTIFACT_TYPE,
            "artifact_id": artifact_id,
            "result_path": "benchmark_result.json",
            "result_sha256": sha256_file(result_path),
            "result_size_bytes": result_path.stat().st_size,
        }
        manifest_path = temporary / "manifest.json"
        manifest_path.write_text(_canonical(manifest) + "\n", encoding="utf-8", newline="\n")
        _fsync(manifest_path)
        validate_visual_benchmark_artifact(temporary)
        os.rename(temporary, destination)
        temporary = Path()
        return destination
    except (OSError, ValueError) as error:
        if isinstance(error, VisualIntegrityError | VisualManifestError):
            raise
        raise VisualIntegrityError("Benchmark artifact failed before atomic publication") from error
    finally:
        if temporary != Path() and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def validate_visual_benchmark_artifact(root: Path) -> VisualBenchmarkResult:
    """Validate schema, containment, exact files, size, digest, and content identity."""

    base = root.resolve()
    try:
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Benchmark artifact manifest is malformed") from error
    expected = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "result_path",
        "result_sha256",
        "result_size_bytes",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected:
        raise VisualManifestError("Benchmark artifact manifest does not match its schema")
    if manifest["schema_version"] != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Benchmark artifact schema version is unsupported")
    if manifest["artifact_type"] != BENCHMARK_ARTIFACT_TYPE:
        raise VisualManifestError("Benchmark artifact type is unsupported")
    relative = normalize_relative_path(_string(manifest["result_path"], "result_path"))
    result_path = (base / relative).resolve()
    try:
        result_path.relative_to(base)
    except ValueError as error:
        raise VisualIntegrityError(
            "Benchmark result path resolves outside artifact root"
        ) from error
    actual = {path.relative_to(base).as_posix() for path in base.rglob("*") if path.is_file()}
    if actual != {"manifest.json", relative}:
        raise VisualIntegrityError("Benchmark artifact contains missing or unexpected files")
    size = _int(manifest["result_size_bytes"], "result_size_bytes")
    digest = _string(manifest["result_sha256"], "result_sha256")
    if len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
        raise VisualManifestError("result_sha256 must be a lowercase SHA-256 digest")
    if (
        not result_path.is_file()
        or result_path.stat().st_size != size
        or sha256_file(result_path) != digest
    ):
        raise VisualIntegrityError("Benchmark result content does not match its manifest")
    raw = result_path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != _string(manifest["artifact_id"], "artifact_id"):
        raise VisualIntegrityError("Benchmark artifact identity does not match its content")
    try:
        data = json.loads(raw)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Benchmark result is malformed") from error
    return _result(data)


def _result(value: object) -> VisualBenchmarkResult:
    data = _dict(value, "benchmark result")
    _fields(
        data,
        {
            "schema_version",
            "metrics",
            "operating_points",
            "predictions",
            "missing_prediction_ids",
            "provenance",
        },
        "benchmark result",
    )
    try:
        metrics_data = _dict(data["metrics"], "metrics")
        distribution_data = metrics_data["score_distribution"]
        distribution = (
            None
            if distribution_data is None
            else _distribution(_dict(distribution_data, "score distribution"))
        )
        metrics = VisualBenchmarkMetricSummary(
            sample_count=_int(metrics_data["sample_count"], "sample_count"),
            scored_count=_int(metrics_data["scored_count"], "scored_count"),
            labeled_count=_int(metrics_data["labeled_count"], "labeled_count"),
            normal_count=_int(metrics_data["normal_count"], "normal_count"),
            anomaly_count=_int(metrics_data["anomaly_count"], "anomaly_count"),
            unknown_count=_int(metrics_data["unknown_count"], "unknown_count"),
            score_distribution=distribution,
            supervised_metrics_available=_bool(
                metrics_data["supervised_metrics_available"], "supervised_metrics_available"
            ),
            auroc=_optional_float(metrics_data["auroc"]),
            average_precision=_optional_float(metrics_data["average_precision"]),
            precision_at_k=_metric_map(metrics_data["precision_at_k"]),
            recall_at_k=_metric_map(metrics_data["recall_at_k"]),
            selected_count=_int(metrics_data["selected_count"], "selected_count"),
            selected_fraction=_float(metrics_data["selected_fraction"], "selected_fraction"),
            score_range=_optional_range(metrics_data["score_range"]),
            warnings=_strings(metrics_data["warnings"], "warnings"),
        )
        result = VisualBenchmarkResult(
            schema_version=_int(data["schema_version"], "schema_version"),
            metrics=metrics,
            operating_points=tuple(
                _operating(item) for item in _list(data["operating_points"], "operating_points")
            ),
            predictions=tuple(
                _prediction(item) for item in _list(data["predictions"], "predictions")
            ),
            missing_prediction_ids=_strings(
                data["missing_prediction_ids"], "missing_prediction_ids"
            ),
            provenance=_provenance(data["provenance"]),
        )
    except (KeyError, TypeError, ValueError) as error:
        if isinstance(error, VisualManifestError):
            raise
        raise VisualManifestError("Benchmark result does not match its schema") from error
    if result.schema_version != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Benchmark result schema version is unsupported")
    return result


def _distribution(data: dict[str, Any]) -> ScoreDistributionSummary:
    return ScoreDistributionSummary(
        _int(data["count"], "count"),
        _float(data["minimum"], "minimum"),
        _float(data["maximum"], "maximum"),
        _float(data["mean"], "mean"),
        _float(data["std"], "std"),
        {
            str(key): _float(value, "quantile")
            for key, value in _dict(data["quantiles"], "quantiles").items()
        },
    )


def _prediction(value: object) -> VisualBenchmarkPrediction:
    data = _dict(value, "prediction")
    return VisualBenchmarkPrediction(
        _string(data["sample_id"], "sample_id"),
        _float(data["score"], "score"),
        _optional_float(data["calibrated_score"]),
        _optional_bool(data["selected"]),
        _optional_string(data["threshold_id"], "threshold_id"),
        _optional_string(data["score_source"], "score_source"),
        _optional_string(data["evidence_path"], "evidence_path"),
    )


def _operating(value: object) -> VisualBenchmarkOperatingPointResult:
    data = _dict(value, "operating point")
    return VisualBenchmarkOperatingPointResult(
        operating_point_id=_string(data["operating_point_id"], "operating_point_id"),
        strategy=data["strategy"],
        value=_float(data["value"], "value"),
        score_threshold=_float(data["score_threshold"], "score_threshold"),
        selected_count=_int(data["selected_count"], "selected_count"),
        selected_fraction=_float(data["selected_fraction"], "selected_fraction"),
        supervised_metrics_available=_bool(
            data["supervised_metrics_available"], "supervised_metrics_available"
        ),
        true_positives=_optional_int(data["true_positives"]),
        false_positives=_optional_int(data["false_positives"]),
        true_negatives=_optional_int(data["true_negatives"]),
        false_negatives=_optional_int(data["false_negatives"]),
        precision=_optional_float(data["precision"]),
        recall=_optional_float(data["recall"]),
        f1=_optional_float(data["f1"]),
        requires_human_review=_bool(data["requires_human_review"], "requires_human_review"),
        warnings=_strings(data["warnings"], "warnings"),
    )


def _provenance(value: object) -> VisualBenchmarkProvenance:
    data = _dict(value, "provenance")
    return VisualBenchmarkProvenance(
        _string(data["benchmark_manifest_path"], "benchmark_manifest_path"),
        _string(data["benchmark_manifest_fingerprint"], "benchmark_manifest_fingerprint"),
        _string(data["prediction_fingerprint"], "prediction_fingerprint"),
        _string(data["config_fingerprint"], "config_fingerprint"),
        _string(data["dataset_name"], "dataset_name"),
        _string(data["dataset_version"], "dataset_version"),
        _string(data["split_name"], "split_name"),
        _string(data["generated_at"], "generated_at"),
        _string(data["score_type"], "score_type"),
        _bool(data["externally_provisioned"], "externally_provisioned"),
        _bool(data["human_review_required"], "human_review_required"),
        _strings(data["limitations"], "limitations"),
    )


def _dict(value: object, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise VisualManifestError(f"{name} must be an object")
    return value


def _list(value: object, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise VisualManifestError(f"{name} must be a list")
    return value


def _fields(data: dict[str, Any], expected: set[str], name: str) -> None:
    if set(data) != expected:
        raise VisualManifestError(f"{name} fields do not match the schema")


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


def _optional_int(value: object) -> int | None:
    return None if value is None else _int(value, "optional integer")


def _float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise VisualManifestError(f"{name} must be numeric")
    return float(value)


def _optional_float(value: object) -> float | None:
    return None if value is None else _float(value, "optional number")


def _bool(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise VisualManifestError(f"{name} must be boolean")
    return value


def _optional_bool(value: object) -> bool | None:
    return None if value is None else _bool(value, "optional boolean")


def _strings(value: object, name: str) -> tuple[str, ...]:
    return tuple(_string(item, name) for item in _list(value, name))


def _metric_map(value: object) -> dict[str, float | None]:
    return {str(key): _optional_float(item) for key, item in _dict(value, "metric map").items()}


def _optional_range(value: object) -> tuple[float, float] | None:
    if value is None:
        return None
    items = _list(value, "score range")
    if len(items) != 2:
        raise VisualManifestError("score range must contain two values")
    return (_float(items[0], "score range"), _float(items[1], "score range"))


def _canonical(value: object) -> str:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )


def _fsync(path: Path) -> None:
    with path.open("rb+") as stream:
        os.fsync(stream.fileno())

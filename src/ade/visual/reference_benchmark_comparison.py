"""Deterministic comparison artifacts for compatible reference baselines."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal, cast

from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.errors import VisualIntegrityError, VisualManifestError
from ade.visual.fingerprints import normalize_relative_path, sha256_file
from ade.visual.reference_benchmark_artifacts import (
    ReferenceBenchmarkBaseline,
    validate_reference_benchmark_baseline,
)

REFERENCE_BASELINE_COMPARISON_ARTIFACT_TYPE = "reference-benchmark-comparison"
AcceptanceTransition = Literal[
    "unchanged_pass",
    "unchanged_fail",
    "pass_to_fail",
    "fail_to_pass",
]


@dataclass(frozen=True)
class BenchmarkMetricDelta:
    """One descriptive metric change without a significance claim."""

    metric: str
    baseline: float | None
    candidate: float | None
    delta: float | None


@dataclass(frozen=True)
class BenchmarkOperatingPointDelta:
    """Comparable workload and quality changes at one declared operating point."""

    operating_point_id: str
    strategy: str
    value: float
    precision: BenchmarkMetricDelta
    recall: BenchmarkMetricDelta
    f1: BenchmarkMetricDelta
    selected_fraction: BenchmarkMetricDelta


@dataclass(frozen=True)
class ReferenceBenchmarkComparison:
    """Auditable comparison between two compatible immutable baselines."""

    schema_version: int
    baseline_artifact_id: str
    candidate_artifact_id: str
    benchmark_manifest_fingerprint: str
    policy_fingerprint: str
    auroc: BenchmarkMetricDelta
    average_precision: BenchmarkMetricDelta
    missing_prediction_delta: int
    operating_points: tuple[BenchmarkOperatingPointDelta, ...]
    changed_provenance_fields: tuple[str, ...]
    acceptance_transition: AcceptanceTransition
    gate_regression: bool
    human_review_required: bool = True
    limitations: tuple[str, ...] = (
        "Metric deltas are descriptive and do not establish statistical significance.",
        "Acceptance transitions are engineering evidence, not product guarantees.",
    )


def compare_reference_benchmark_baselines(
    baseline_artifact: Path,
    candidate_artifact: Path,
) -> ReferenceBenchmarkComparison:
    """Validate and compare two immutable baseline artifacts."""

    baseline = validate_reference_benchmark_baseline(baseline_artifact)
    candidate = validate_reference_benchmark_baseline(candidate_artifact)
    _validate_compatibility(baseline, candidate)

    baseline_points = {
        (item.strategy, item.value): item for item in baseline.benchmark.operating_points
    }
    candidate_points = {
        (item.strategy, item.value): item for item in candidate.benchmark.operating_points
    }
    point_deltas = tuple(
        BenchmarkOperatingPointDelta(
            operating_point_id=baseline_points[key].operating_point_id,
            strategy=key[0],
            value=key[1],
            precision=_metric_delta(
                "precision",
                baseline_points[key].precision,
                candidate_points[key].precision,
            ),
            recall=_metric_delta(
                "recall",
                baseline_points[key].recall,
                candidate_points[key].recall,
            ),
            f1=_metric_delta(
                "f1",
                baseline_points[key].f1,
                candidate_points[key].f1,
            ),
            selected_fraction=_metric_delta(
                "selected_fraction",
                baseline_points[key].selected_fraction,
                candidate_points[key].selected_fraction,
            ),
        )
        for key in sorted(baseline_points, key=lambda item: (item[0], item[1]))
    )
    transition = _acceptance_transition(
        baseline.acceptance_result.passed,
        candidate.acceptance_result.passed,
    )
    comparison = ReferenceBenchmarkComparison(
        schema_version=VISUAL_ENGINE_SCHEMA_VERSION,
        baseline_artifact_id=_artifact_id(baseline_artifact),
        candidate_artifact_id=_artifact_id(candidate_artifact),
        benchmark_manifest_fingerprint=(
            baseline.benchmark.provenance.benchmark_manifest_fingerprint
        ),
        policy_fingerprint=baseline.acceptance_result.policy_fingerprint,
        auroc=_metric_delta(
            "auroc",
            baseline.benchmark.metrics.auroc,
            candidate.benchmark.metrics.auroc,
        ),
        average_precision=_metric_delta(
            "average_precision",
            baseline.benchmark.metrics.average_precision,
            candidate.benchmark.metrics.average_precision,
        ),
        missing_prediction_delta=(
            len(candidate.benchmark.missing_prediction_ids)
            - len(baseline.benchmark.missing_prediction_ids)
        ),
        operating_points=point_deltas,
        changed_provenance_fields=_changed_provenance_fields(baseline, candidate),
        acceptance_transition=cast(AcceptanceTransition, transition),
        gate_regression=transition == "pass_to_fail",
    )
    _validate_comparison(comparison)
    return comparison


def serialize_reference_benchmark_comparison(
    comparison: ReferenceBenchmarkComparison,
) -> str:
    """Return canonical JSON for one validated comparison."""

    _validate_comparison(comparison)
    return _canonical(asdict(comparison))


def deserialize_reference_benchmark_comparison(
    payload: str | bytes,
) -> ReferenceBenchmarkComparison:
    """Load a strict comparison payload."""

    try:
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Reference benchmark comparison is malformed") from error
    if not isinstance(data, dict):
        raise VisualManifestError("Reference benchmark comparison root must be an object")
    expected = {
        "schema_version",
        "baseline_artifact_id",
        "candidate_artifact_id",
        "benchmark_manifest_fingerprint",
        "policy_fingerprint",
        "auroc",
        "average_precision",
        "missing_prediction_delta",
        "operating_points",
        "changed_provenance_fields",
        "acceptance_transition",
        "gate_regression",
        "human_review_required",
        "limitations",
    }
    if set(data) != expected:
        raise VisualManifestError("Reference benchmark comparison fields do not match its schema")

    operating_raw = data["operating_points"]
    if not isinstance(operating_raw, list):
        raise VisualManifestError("Comparison operating points must be a list")
    operating_points = tuple(_deserialize_operating_point(item) for item in operating_raw)
    provenance_raw = data["changed_provenance_fields"]
    limitations_raw = data["limitations"]
    if not isinstance(provenance_raw, list) or not all(
        isinstance(item, str) for item in provenance_raw
    ):
        raise VisualManifestError("Changed provenance fields must be strings")
    if not isinstance(limitations_raw, list) or not all(
        isinstance(item, str) for item in limitations_raw
    ):
        raise VisualManifestError("Comparison limitations must be strings")

    transition = data["acceptance_transition"]
    if transition not in {
        "unchanged_pass",
        "unchanged_fail",
        "pass_to_fail",
        "fail_to_pass",
    }:
        raise VisualManifestError("Acceptance transition is invalid")
    comparison = ReferenceBenchmarkComparison(
        schema_version=_integer(data["schema_version"], "schema_version"),
        baseline_artifact_id=_digest(
            data["baseline_artifact_id"], "baseline_artifact_id"
        ),
        candidate_artifact_id=_digest(
            data["candidate_artifact_id"], "candidate_artifact_id"
        ),
        benchmark_manifest_fingerprint=_digest(
            data["benchmark_manifest_fingerprint"],
            "benchmark_manifest_fingerprint",
        ),
        policy_fingerprint=_digest(data["policy_fingerprint"], "policy_fingerprint"),
        auroc=_deserialize_metric_delta(data["auroc"]),
        average_precision=_deserialize_metric_delta(data["average_precision"]),
        missing_prediction_delta=_integer(
            data["missing_prediction_delta"], "missing_prediction_delta"
        ),
        operating_points=operating_points,
        changed_provenance_fields=tuple(provenance_raw),
        acceptance_transition=transition,
        gate_regression=_boolean(data["gate_regression"], "gate_regression"),
        human_review_required=_boolean(
            data["human_review_required"], "human_review_required"
        ),
        limitations=tuple(limitations_raw),
    )
    _validate_comparison(comparison)
    return comparison


def publish_reference_benchmark_comparison(
    comparison: ReferenceBenchmarkComparison,
    output_root: Path,
) -> Path:
    """Publish or resolve one content-addressed comparison artifact."""

    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    payload = serialize_reference_benchmark_comparison(comparison) + "\n"
    artifact_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    destination = root / artifact_id
    if destination.exists():
        if validate_reference_benchmark_comparison(destination) == comparison:
            return destination
        raise VisualIntegrityError("Existing benchmark comparison artifact is incompatible")

    temporary = Path(
        tempfile.mkdtemp(prefix=f".{artifact_id}.", suffix=".tmp", dir=root)
    )
    try:
        comparison_path = temporary / "comparison.json"
        comparison_path.write_text(payload, encoding="utf-8", newline="\n")
        _fsync(comparison_path)
        manifest = {
            "schema_version": VISUAL_ENGINE_SCHEMA_VERSION,
            "artifact_type": REFERENCE_BASELINE_COMPARISON_ARTIFACT_TYPE,
            "artifact_id": artifact_id,
            "comparison_path": "comparison.json",
            "comparison_sha256": sha256_file(comparison_path),
            "comparison_size_bytes": comparison_path.stat().st_size,
        }
        manifest_path = temporary / "manifest.json"
        manifest_path.write_text(
            _canonical(manifest) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        _fsync(manifest_path)
        validate_reference_benchmark_comparison(temporary)
        os.rename(temporary, destination)
        temporary = Path()
        return destination
    except (OSError, ValueError) as error:
        if isinstance(error, VisualIntegrityError | VisualManifestError):
            raise
        raise VisualIntegrityError(
            "Reference benchmark comparison failed before atomic publication"
        ) from error
    finally:
        if temporary != Path() and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def validate_reference_benchmark_comparison(root: Path) -> ReferenceBenchmarkComparison:
    """Validate comparison schema, exact files, digest, identity, and content."""

    base = root.resolve()
    try:
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Reference comparison manifest is malformed") from error
    expected = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "comparison_path",
        "comparison_sha256",
        "comparison_size_bytes",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected:
        raise VisualManifestError("Reference comparison manifest does not match its schema")
    if manifest["schema_version"] != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Reference comparison schema version is unsupported")
    if manifest["artifact_type"] != REFERENCE_BASELINE_COMPARISON_ARTIFACT_TYPE:
        raise VisualManifestError("Reference comparison artifact type is unsupported")

    relative = normalize_relative_path(
        _string(manifest["comparison_path"], "comparison_path")
    )
    comparison_path = (base / relative).resolve()
    try:
        comparison_path.relative_to(base)
    except ValueError as error:
        raise VisualIntegrityError(
            "Reference comparison path resolves outside artifact root"
        ) from error
    actual_files = {
        path.relative_to(base).as_posix()
        for path in base.rglob("*")
        if path.is_file()
    }
    if actual_files != {"manifest.json", relative}:
        raise VisualIntegrityError(
            "Reference comparison artifact contains missing or unexpected files"
        )
    size = _integer(manifest["comparison_size_bytes"], "comparison_size_bytes")
    digest = _digest(manifest["comparison_sha256"], "comparison_sha256")
    if (
        not comparison_path.is_file()
        or comparison_path.stat().st_size != size
        or sha256_file(comparison_path) != digest
    ):
        raise VisualIntegrityError(
            "Reference comparison content does not match its manifest"
        )
    raw = comparison_path.read_bytes()
    artifact_id = _digest(manifest["artifact_id"], "artifact_id")
    if hashlib.sha256(raw).hexdigest() != artifact_id:
        raise VisualIntegrityError(
            "Reference comparison identity does not match its content"
        )
    return deserialize_reference_benchmark_comparison(raw)


def _validate_compatibility(
    baseline: ReferenceBenchmarkBaseline,
    candidate: ReferenceBenchmarkBaseline,
) -> None:
    baseline_provenance = baseline.benchmark.provenance
    candidate_provenance = candidate.benchmark.provenance
    identities = (
        ("dataset name", baseline_provenance.dataset_name, candidate_provenance.dataset_name),
        (
            "dataset version",
            baseline_provenance.dataset_version,
            candidate_provenance.dataset_version,
        ),
        ("split", baseline_provenance.split_name, candidate_provenance.split_name),
        (
            "benchmark manifest fingerprint",
            baseline_provenance.benchmark_manifest_fingerprint,
            candidate_provenance.benchmark_manifest_fingerprint,
        ),
        (
            "policy fingerprint",
            baseline.acceptance_result.policy_fingerprint,
            candidate.acceptance_result.policy_fingerprint,
        ),
    )
    mismatches = [name for name, left, right in identities if left != right]
    baseline_samples = {item.sample_id for item in baseline.benchmark.predictions}
    candidate_samples = {item.sample_id for item in candidate.benchmark.predictions}
    if baseline_samples != candidate_samples:
        mismatches.append("prediction sample IDs")

    baseline_points = {
        (item.strategy, item.value): item.operating_point_id
        for item in baseline.benchmark.operating_points
    }
    candidate_points = {
        (item.strategy, item.value): item.operating_point_id
        for item in candidate.benchmark.operating_points
    }
    if baseline_points != candidate_points:
        mismatches.append("operating points")
    if mismatches:
        raise VisualIntegrityError(
            "Reference baselines are not comparable: " + ", ".join(mismatches)
        )


def _changed_provenance_fields(
    baseline: ReferenceBenchmarkBaseline,
    candidate: ReferenceBenchmarkBaseline,
) -> tuple[str, ...]:
    ignored = {"scoring_id"}
    baseline_values = asdict(baseline.reference_scoring)
    candidate_values = asdict(candidate.reference_scoring)
    return tuple(
        name
        for name in sorted(baseline_values)
        if name not in ignored and baseline_values[name] != candidate_values[name]
    )


def _acceptance_transition(
    baseline_passed: bool,
    candidate_passed: bool,
) -> AcceptanceTransition:
    if baseline_passed and candidate_passed:
        return "unchanged_pass"
    if not baseline_passed and not candidate_passed:
        return "unchanged_fail"
    if baseline_passed:
        return "pass_to_fail"
    return "fail_to_pass"


def _metric_delta(
    name: str,
    baseline: float | None,
    candidate: float | None,
) -> BenchmarkMetricDelta:
    delta = None
    if baseline is not None and candidate is not None:
        delta = candidate - baseline
    return BenchmarkMetricDelta(name, baseline, candidate, delta)


def _artifact_id(path: Path) -> str:
    return sha256_file(path.resolve() / "baseline.json")


def _validate_comparison(comparison: ReferenceBenchmarkComparison) -> None:
    if comparison.schema_version != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Reference comparison schema version is unsupported")
    for value, name in (
        (comparison.baseline_artifact_id, "baseline_artifact_id"),
        (comparison.candidate_artifact_id, "candidate_artifact_id"),
        (
            comparison.benchmark_manifest_fingerprint,
            "benchmark_manifest_fingerprint",
        ),
        (comparison.policy_fingerprint, "policy_fingerprint"),
    ):
        _digest(value, name)
    if comparison.human_review_required is not True:
        raise VisualIntegrityError("Reference comparison must require human review")
    expected_regression = comparison.acceptance_transition == "pass_to_fail"
    if comparison.gate_regression != expected_regression:
        raise VisualIntegrityError(
            "Reference comparison regression flag contradicts its transition"
        )
    _validate_metric_delta(comparison.auroc)
    _validate_metric_delta(comparison.average_precision)
    seen: set[tuple[str, float]] = set()
    for point in comparison.operating_points:
        identity = (point.strategy, point.value)
        if identity in seen:
            raise VisualIntegrityError("Comparison operating points must be unique")
        seen.add(identity)
        for metric in (
            point.precision,
            point.recall,
            point.f1,
            point.selected_fraction,
        ):
            _validate_metric_delta(metric)
    if tuple(sorted(set(comparison.changed_provenance_fields))) != (
        comparison.changed_provenance_fields
    ):
        raise VisualIntegrityError(
            "Changed provenance fields must be unique and sorted"
        )


def _validate_metric_delta(metric: BenchmarkMetricDelta) -> None:
    for value in (metric.baseline, metric.candidate, metric.delta):
        if value is not None and not math.isfinite(value):
            raise VisualIntegrityError("Comparison metric values must be finite")
    expected = (
        None
        if metric.baseline is None or metric.candidate is None
        else metric.candidate - metric.baseline
    )
    if metric.delta != expected:
        raise VisualIntegrityError("Comparison metric delta is inconsistent")


def _deserialize_metric_delta(value: object) -> BenchmarkMetricDelta:
    if not isinstance(value, dict) or set(value) != {
        "metric",
        "baseline",
        "candidate",
        "delta",
    }:
        raise VisualManifestError("Comparison metric delta does not match its schema")
    return BenchmarkMetricDelta(
        metric=_string(value["metric"], "metric"),
        baseline=_optional_number(value["baseline"], "baseline"),
        candidate=_optional_number(value["candidate"], "candidate"),
        delta=_optional_number(value["delta"], "delta"),
    )


def _deserialize_operating_point(value: object) -> BenchmarkOperatingPointDelta:
    if not isinstance(value, dict) or set(value) != {
        "operating_point_id",
        "strategy",
        "value",
        "precision",
        "recall",
        "f1",
        "selected_fraction",
    }:
        raise VisualManifestError(
            "Comparison operating point does not match its schema"
        )
    return BenchmarkOperatingPointDelta(
        operating_point_id=_string(value["operating_point_id"], "operating_point_id"),
        strategy=_string(value["strategy"], "strategy"),
        value=_number(value["value"], "value"),
        precision=_deserialize_metric_delta(value["precision"]),
        recall=_deserialize_metric_delta(value["recall"]),
        f1=_deserialize_metric_delta(value["f1"]),
        selected_fraction=_deserialize_metric_delta(value["selected_fraction"]),
    )


def _string(value: object, name: str) -> str:
    if not isinstance(value, str):
        raise VisualManifestError(f"{name} must be a string")
    return value


def _digest(value: object, name: str) -> str:
    result = _string(value, name)
    if len(result) != 64 or any(char not in "0123456789abcdef" for char in result):
        raise VisualManifestError(f"{name} must be a lowercase SHA-256 digest")
    return result


def _boolean(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise VisualManifestError(f"{name} must be boolean")
    return value


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise VisualManifestError(f"{name} must be an integer")
    return value


def _number(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise VisualManifestError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise VisualManifestError(f"{name} must be finite")
    return result


def _optional_number(value: object, name: str) -> float | None:
    if value is None:
        return None
    return _number(value, name)


def _canonical(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _fsync(path: Path) -> None:
    with path.open("rb+") as stream:
        os.fsync(stream.fileno())

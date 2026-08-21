"""Immutable baseline artifacts for executed reference benchmarks."""

from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
from dataclasses import asdict, dataclass, fields
from pathlib import Path
from typing import Any

from ade.visual.benchmark_acceptance import (
    VisualBenchmarkAcceptancePolicy,
    VisualBenchmarkAcceptanceResult,
    deserialize_visual_benchmark_acceptance_policy,
    evaluate_visual_benchmark_acceptance,
    serialize_visual_benchmark_acceptance_policy,
)
from ade.visual.benchmark_artifacts import (
    deserialize_visual_benchmark_result,
    serialize_visual_benchmark_result,
)
from ade.visual.benchmark_contracts import VisualBenchmarkResult
from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.errors import VisualIntegrityError, VisualManifestError
from ade.visual.fingerprints import normalize_relative_path, sha256_file
from ade.visual.reference_benchmark import ReferenceBenchmarkExecution
from ade.visual.scoring_contracts import ReferenceScoringSummary

REFERENCE_BASELINE_ARTIFACT_TYPE = "reference-benchmark-baseline"


@dataclass(frozen=True)
class ReferenceBenchmarkBaseline:
    """Complete immutable evidence for one executed acceptance decision."""

    schema_version: int
    benchmark: VisualBenchmarkResult
    reference_scoring: ReferenceScoringSummary
    acceptance_policy: VisualBenchmarkAcceptancePolicy
    acceptance_result: VisualBenchmarkAcceptanceResult
    human_review_required: bool = True
    limitations: tuple[str, ...] = (
        "Benchmark acceptance is engineering evidence, not a product guarantee.",
        "Candidate anomaly scores remain review-prioritization signals.",
    )


def build_reference_benchmark_baseline(
    execution: ReferenceBenchmarkExecution,
    policy: VisualBenchmarkAcceptancePolicy,
) -> ReferenceBenchmarkBaseline:
    """Combine measured results, scorer provenance, and a predeclared policy."""

    acceptance = evaluate_visual_benchmark_acceptance(execution.benchmark, policy)
    return ReferenceBenchmarkBaseline(
        schema_version=VISUAL_ENGINE_SCHEMA_VERSION,
        benchmark=execution.benchmark,
        reference_scoring=execution.reference_scoring,
        acceptance_policy=policy,
        acceptance_result=acceptance,
    )


def serialize_reference_benchmark_baseline(
    baseline: ReferenceBenchmarkBaseline,
) -> str:
    """Return canonical JSON after validating all cross-record identities."""

    _validate_baseline(baseline)
    return _canonical(asdict(baseline))


def deserialize_reference_benchmark_baseline(
    payload: str | bytes,
) -> ReferenceBenchmarkBaseline:
    """Load and validate a complete baseline JSON payload."""

    try:
        data = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Reference benchmark baseline is malformed") from error
    if not isinstance(data, dict):
        raise VisualManifestError("Reference benchmark baseline root must be an object")
    expected = {
        "schema_version",
        "benchmark",
        "reference_scoring",
        "acceptance_policy",
        "acceptance_result",
        "human_review_required",
        "limitations",
    }
    if set(data) != expected:
        raise VisualManifestError("Reference benchmark baseline fields do not match its schema")

    benchmark = deserialize_visual_benchmark_result(_canonical(data["benchmark"]))
    policy = deserialize_visual_benchmark_acceptance_policy(
        _canonical(data["acceptance_policy"])
    )
    scoring = _deserialize_scoring_summary(data["reference_scoring"])
    acceptance = _deserialize_acceptance_result(data["acceptance_result"])
    limitations_raw = data["limitations"]
    if not isinstance(limitations_raw, list) or not all(
        isinstance(item, str) for item in limitations_raw
    ):
        raise VisualManifestError("Reference benchmark limitations must be strings")
    baseline = ReferenceBenchmarkBaseline(
        schema_version=_integer(data["schema_version"], "schema_version"),
        benchmark=benchmark,
        reference_scoring=scoring,
        acceptance_policy=policy,
        acceptance_result=acceptance,
        human_review_required=_boolean(
            data["human_review_required"],
            "human_review_required",
        ),
        limitations=tuple(limitations_raw),
    )
    _validate_baseline(baseline)
    return baseline


def publish_reference_benchmark_baseline(
    baseline: ReferenceBenchmarkBaseline,
    output_root: Path,
) -> Path:
    """Publish or resolve one content-addressed baseline artifact."""

    root = output_root.resolve()
    root.mkdir(parents=True, exist_ok=True)
    payload = serialize_reference_benchmark_baseline(baseline) + "\n"
    artifact_id = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    destination = root / artifact_id
    if destination.exists():
        if validate_reference_benchmark_baseline(destination) == baseline:
            return destination
        raise VisualIntegrityError("Existing reference baseline artifact is incompatible")

    temporary = Path(
        tempfile.mkdtemp(prefix=f".{artifact_id}.", suffix=".tmp", dir=root)
    )
    try:
        baseline_path = temporary / "baseline.json"
        baseline_path.write_text(payload, encoding="utf-8", newline="\n")
        _fsync(baseline_path)
        manifest = {
            "schema_version": VISUAL_ENGINE_SCHEMA_VERSION,
            "artifact_type": REFERENCE_BASELINE_ARTIFACT_TYPE,
            "artifact_id": artifact_id,
            "baseline_path": "baseline.json",
            "baseline_sha256": sha256_file(baseline_path),
            "baseline_size_bytes": baseline_path.stat().st_size,
        }
        manifest_path = temporary / "manifest.json"
        manifest_path.write_text(
            _canonical(manifest) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        _fsync(manifest_path)
        validate_reference_benchmark_baseline(temporary)
        os.rename(temporary, destination)
        temporary = Path()
        return destination
    except (OSError, ValueError) as error:
        if isinstance(error, VisualIntegrityError | VisualManifestError):
            raise
        raise VisualIntegrityError(
            "Reference baseline failed before atomic publication"
        ) from error
    finally:
        if temporary != Path() and temporary.exists():
            shutil.rmtree(temporary, ignore_errors=True)


def validate_reference_benchmark_baseline(
    root: Path,
) -> ReferenceBenchmarkBaseline:
    """Validate artifact schema, exact files, digest, identity, and content."""

    base = root.resolve()
    try:
        manifest = json.loads((base / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise VisualManifestError("Reference baseline manifest is malformed") from error
    expected = {
        "schema_version",
        "artifact_type",
        "artifact_id",
        "baseline_path",
        "baseline_sha256",
        "baseline_size_bytes",
    }
    if not isinstance(manifest, dict) or set(manifest) != expected:
        raise VisualManifestError("Reference baseline manifest does not match its schema")
    if manifest["schema_version"] != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Reference baseline schema version is unsupported")
    if manifest["artifact_type"] != REFERENCE_BASELINE_ARTIFACT_TYPE:
        raise VisualManifestError("Reference baseline artifact type is unsupported")

    relative = normalize_relative_path(
        _string(manifest["baseline_path"], "baseline_path")
    )
    baseline_path = (base / relative).resolve()
    try:
        baseline_path.relative_to(base)
    except ValueError as error:
        raise VisualIntegrityError(
            "Reference baseline path resolves outside artifact root"
        ) from error
    actual_files = {
        path.relative_to(base).as_posix()
        for path in base.rglob("*")
        if path.is_file()
    }
    if actual_files != {"manifest.json", relative}:
        raise VisualIntegrityError(
            "Reference baseline artifact contains missing or unexpected files"
        )
    size = _integer(manifest["baseline_size_bytes"], "baseline_size_bytes")
    digest = _digest(manifest["baseline_sha256"], "baseline_sha256")
    if (
        not baseline_path.is_file()
        or baseline_path.stat().st_size != size
        or sha256_file(baseline_path) != digest
    ):
        raise VisualIntegrityError(
            "Reference baseline content does not match its manifest"
        )
    raw = baseline_path.read_bytes()
    artifact_id = _digest(manifest["artifact_id"], "artifact_id")
    if hashlib.sha256(raw).hexdigest() != artifact_id:
        raise VisualIntegrityError(
            "Reference baseline identity does not match its content"
        )
    return deserialize_reference_benchmark_baseline(raw)


def _validate_baseline(baseline: ReferenceBenchmarkBaseline) -> None:
    if baseline.schema_version != VISUAL_ENGINE_SCHEMA_VERSION:
        raise VisualManifestError("Reference baseline schema version is unsupported")
    if baseline.human_review_required is not True:
        raise VisualIntegrityError("Reference baseline must require human review")
    expected_acceptance = evaluate_visual_benchmark_acceptance(
        baseline.benchmark,
        baseline.acceptance_policy,
    )
    if baseline.acceptance_result != expected_acceptance:
        raise VisualIntegrityError(
            "Reference baseline acceptance result does not match its policy"
        )
    source = f"reference_scoring:{baseline.reference_scoring.scoring_id}"
    if not baseline.benchmark.predictions or any(
        prediction.score_source != source
        for prediction in baseline.benchmark.predictions
    ):
        raise VisualIntegrityError(
            "Reference baseline predictions do not match scoring provenance"
        )


def _deserialize_scoring_summary(value: object) -> ReferenceScoringSummary:
    if not isinstance(value, dict):
        raise VisualManifestError("Reference scoring summary must be an object")
    expected = {field.name for field in fields(ReferenceScoringSummary)}
    if set(value) != expected:
        raise VisualManifestError(
            "Reference scoring summary fields do not match its schema"
        )
    string_fields = {
        "scoring_id",
        "metric",
        "patch_strategy",
        "image_aggregation",
        "map_projection",
        "multi_scale_fusion",
        "query_dataset_fingerprint",
        "reference_dataset_fingerprint",
        "reference_memory_id",
        "configuration_fingerprint",
        "backend_id",
        "backend_version",
        "device",
        "search_backend",
        "search_backend_version",
        "search_dtype",
        "search_device",
        "search_configuration_fingerprint",
    }
    bool_fields = {"calibrated", "deterministic", "search_deterministic"}
    int_fields = {"neighbor_count", "search_dimension"}
    float_fields = {"top_fraction", "smoothing_sigma"}
    normalized: dict[str, Any] = {}
    for name in string_fields:
        normalized[name] = _string(value[name], name)
    for name in bool_fields:
        normalized[name] = _boolean(value[name], name)
    for name in int_fields:
        normalized[name] = _integer(value[name], name)
    for name in float_fields:
        normalized[name] = _number(value[name], name)
    return ReferenceScoringSummary(**normalized)


def _deserialize_acceptance_result(
    value: object,
) -> VisualBenchmarkAcceptanceResult:
    if not isinstance(value, dict):
        raise VisualManifestError("Benchmark acceptance result must be an object")
    expected = {"passed", "policy_fingerprint", "checks", "failures"}
    if set(value) != expected:
        raise VisualManifestError(
            "Benchmark acceptance result fields do not match its schema"
        )
    checks = value["checks"]
    failures = value["failures"]
    if (
        not isinstance(checks, list)
        or not all(isinstance(item, str) for item in checks)
        or not isinstance(failures, list)
        or not all(isinstance(item, str) for item in failures)
    ):
        raise VisualManifestError("Benchmark acceptance checks and failures must be strings")
    return VisualBenchmarkAcceptanceResult(
        passed=_boolean(value["passed"], "passed"),
        policy_fingerprint=_digest(
            value["policy_fingerprint"],
            "policy_fingerprint",
        ),
        checks=tuple(checks),
        failures=tuple(failures),
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

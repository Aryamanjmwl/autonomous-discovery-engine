"""Explicit acceptance gates for labeled visual benchmark results."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from typing import Any

from ade.visual.benchmark_contracts import (
    BenchmarkOperatingPointStrategy,
    VisualBenchmarkResult,
)
from ade.visual.errors import VisualIntegrityError


@dataclass(frozen=True)
class VisualBenchmarkOperatingPointRequirement:
    """Required quality and workload bounds for one declared operating point."""

    strategy: BenchmarkOperatingPointStrategy
    value: float
    min_precision: float | None = None
    min_recall: float | None = None
    max_selected_fraction: float | None = None


@dataclass(frozen=True)
class VisualBenchmarkAcceptancePolicy:
    """Minimum evidence required for one declared dataset and split."""

    dataset_name: str
    dataset_version: str
    split_name: str
    min_auroc: float | None = None
    min_average_precision: float | None = None
    max_missing_predictions: int = 0
    operating_points: tuple[VisualBenchmarkOperatingPointRequirement, ...] = ()


@dataclass(frozen=True)
class VisualBenchmarkAcceptanceResult:
    """Deterministic outcome of evaluating one result against one policy."""

    passed: bool
    policy_fingerprint: str
    checks: tuple[str, ...]
    failures: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "policy_fingerprint": self.policy_fingerprint,
            "checks": list(self.checks),
            "failures": list(self.failures),
        }


def evaluate_visual_benchmark_acceptance(
    result: VisualBenchmarkResult,
    policy: VisualBenchmarkAcceptancePolicy,
) -> VisualBenchmarkAcceptanceResult:
    """Apply explicit quality and workload requirements without selecting them."""

    _validate_policy(policy)
    checks: list[str] = ["dataset identity", "dataset split"]
    failures: list[str] = []
    provenance = result.provenance
    if (
        provenance.dataset_name != policy.dataset_name
        or provenance.dataset_version != policy.dataset_version
    ):
        failures.append(
            "Benchmark dataset identity does not match the acceptance policy."
        )
    if provenance.split_name != policy.split_name:
        failures.append(
            "Benchmark split "
            f"{provenance.split_name!r} does not match required split "
            f"{policy.split_name!r}."
        )

    if policy.min_auroc is not None:
        checks.append("minimum AUROC")
        _minimum_metric(
            "AUROC",
            result.metrics.auroc,
            policy.min_auroc,
            failures,
        )
    if policy.min_average_precision is not None:
        checks.append("minimum average precision")
        _minimum_metric(
            "average precision",
            result.metrics.average_precision,
            policy.min_average_precision,
            failures,
        )

    checks.append("maximum missing predictions")
    missing_count = len(result.missing_prediction_ids)
    if missing_count > policy.max_missing_predictions:
        failures.append(
            "Missing predictions "
            f"{missing_count} exceed allowed maximum {policy.max_missing_predictions}."
        )

    for requirement in policy.operating_points:
        label = f"{requirement.strategy}={requirement.value:g}"
        checks.append(f"operating point {label}")
        matches = [
            item
            for item in result.operating_points
            if item.strategy == requirement.strategy and item.value == requirement.value
        ]
        if len(matches) != 1:
            failures.append(
                f"Required operating point {label} is absent or not unique."
            )
            continue
        operating_point = matches[0]
        if requirement.min_precision is not None:
            _minimum_metric(
                f"precision at {label}",
                operating_point.precision,
                requirement.min_precision,
                failures,
            )
        if requirement.min_recall is not None:
            _minimum_metric(
                f"recall at {label}",
                operating_point.recall,
                requirement.min_recall,
                failures,
            )
        if (
            requirement.max_selected_fraction is not None
            and operating_point.selected_fraction
            > requirement.max_selected_fraction
        ):
            failures.append(
                f"Selected fraction at {label} is "
                f"{operating_point.selected_fraction:.6g}, above required maximum "
                f"{requirement.max_selected_fraction:.6g}."
            )

    payload = json.dumps(
        asdict(policy),
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return VisualBenchmarkAcceptanceResult(
        passed=not failures,
        policy_fingerprint=hashlib.sha256(payload.encode("utf-8")).hexdigest(),
        checks=tuple(checks),
        failures=tuple(failures),
    )


def _minimum_metric(
    name: str,
    actual: float | None,
    required: float,
    failures: list[str],
) -> None:
    if actual is None:
        failures.append(f"{name} is unavailable; required minimum is {required:.6g}.")
    elif actual < required:
        failures.append(
            f"{name} is {actual:.6g}, below required minimum {required:.6g}."
        )


def _validate_policy(policy: VisualBenchmarkAcceptancePolicy) -> None:
    if not (
        policy.dataset_name.strip()
        and policy.dataset_version.strip()
        and policy.split_name.strip()
    ):
        raise VisualIntegrityError(
            "Acceptance dataset name, version, and split must be non-empty"
        )
    if (
        isinstance(policy.max_missing_predictions, bool)
        or not isinstance(policy.max_missing_predictions, int)
        or policy.max_missing_predictions < 0
    ):
        raise VisualIntegrityError("max_missing_predictions must be a non-negative integer")
    for name, value in (
        ("min_auroc", policy.min_auroc),
        ("min_average_precision", policy.min_average_precision),
    ):
        _fraction(value, name)
    identities: set[tuple[str, float]] = set()
    for requirement in policy.operating_points:
        if requirement.strategy not in {
            "explicit",
            "percentile",
            "top_k",
            "top_fraction",
        }:
            raise VisualIntegrityError("Acceptance operating-point strategy is invalid")
        if (
            isinstance(requirement.value, bool)
            or not isinstance(requirement.value, int | float)
            or not math.isfinite(requirement.value)
        ):
            raise VisualIntegrityError("Acceptance operating-point value must be finite")
        identity = (requirement.strategy, float(requirement.value))
        if identity in identities:
            raise VisualIntegrityError(
                "Acceptance operating-point requirements must be unique"
            )
        identities.add(identity)
        _fraction(requirement.min_precision, "min_precision")
        _fraction(requirement.min_recall, "min_recall")
        _fraction(requirement.max_selected_fraction, "max_selected_fraction")


def _fraction(value: float | None, name: str) -> None:
    if value is None:
        return
    if (
        isinstance(value, bool)
        or not isinstance(value, int | float)
        or not math.isfinite(value)
        or value < 0
        or value > 1
    ):
        raise VisualIntegrityError(f"{name} must be finite and between 0 and 1")

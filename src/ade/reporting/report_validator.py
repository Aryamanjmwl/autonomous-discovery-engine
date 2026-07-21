"""Lightweight validation for ADE JSON reports."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = [
    "project_name",
    "run_id",
    "run_metadata",
    "candidate_anomalies",
    "candidate_unknown_concepts",
    "human_review_required",
]

_DIGEST = re.compile(r"^[0-9a-f]{64}$")
_ADVANCED_EVIDENCE_FIELDS = (
    "reference_scoring_summary",
    "spatial_anomaly_map_summary",
    "calibration_summary",
    "threshold_operating_point_summary",
    "benchmark_validation_summary",
)


@dataclass(frozen=True)
class ReportValidationResult:
    """Validation result for a local ADE JSON report."""

    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def validate_report_file(path: Path | str) -> ReportValidationResult:
    """Validate a JSON report file and return structured diagnostics."""

    report_path = Path(path)
    if not report_path.exists():
        return ReportValidationResult(
            is_valid=False,
            errors=[f"Report file does not exist: {report_path}"],
        )
    if not report_path.is_file():
        return ReportValidationResult(
            is_valid=False,
            errors=[f"Report path is not a file: {report_path}"],
        )

    try:
        report = json.loads(report_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return ReportValidationResult(
            is_valid=False,
            errors=[f"Report is not valid JSON: {error.msg}"],
        )

    if not isinstance(report, dict):
        return ReportValidationResult(
            is_valid=False,
            errors=["Report root must be a JSON object."],
        )

    return validate_report_dict(report)


def validate_report_dict(report: dict[str, Any]) -> ReportValidationResult:
    """Validate the current ADE report shape without making scientific claims."""

    errors: list[str] = []
    warnings: list[str] = []

    for field_name in REQUIRED_FIELDS:
        if field_name not in report:
            errors.append(f"Missing required report field: {field_name}")

    if report.get("human_review_required") is not True:
        errors.append("human_review_required must be true.")

    _require_list(report, "candidate_anomalies", errors)
    _require_list(report, "candidate_unknown_concepts", errors)
    _require_optional_object(report, "review_memory_summary", errors)
    for field_name in _ADVANCED_EVIDENCE_FIELDS:
        _validate_advanced_evidence(report, field_name, errors)
    _warn_for_missing_ids(report.get("candidate_anomalies"), "anomaly_id", warnings)
    _warn_for_missing_ids(report.get("candidate_unknown_concepts"), "concept_id", warnings)
    _warn_for_review_memory_signals(report.get("candidate_anomalies"), warnings)
    _warn_for_review_memory_signals(report.get("candidate_unknown_concepts"), warnings)

    return ReportValidationResult(is_valid=not errors, errors=errors, warnings=warnings)


def _validate_advanced_evidence(
    report: dict[str, Any], field_name: str, errors: list[str]
) -> None:
    if field_name not in report:
        return
    value = report[field_name]
    if not isinstance(value, dict) or not value:
        errors.append(f"{field_name} must be a non-empty object when present.")
        return
    _required_string(value, field_name, "artifact_path", errors)
    fingerprint = value.get("artifact_fingerprint")
    if not isinstance(fingerprint, str) or not _DIGEST.fullmatch(fingerprint):
        errors.append(f"{field_name}.artifact_fingerprint must be a lowercase SHA-256 digest.")
    if value.get("requires_human_review") is not True:
        errors.append(f"{field_name}.requires_human_review must be true.")

    boolean_fields = {
        "reference_scoring_summary": ("calibrated",),
        "spatial_anomaly_map_summary": (),
        "calibration_summary": ("calibrated", "labels_available"),
        "threshold_operating_point_summary": ("calibrated",),
        "benchmark_validation_summary": ("labels_available",),
    }[field_name]
    for key in boolean_fields:
        if not isinstance(value.get(key), bool):
            errors.append(f"{field_name}.{key} must be a boolean.")

    count_fields = {
        "reference_scoring_summary": ("candidate_count",),
        "spatial_anomaly_map_summary": ("map_count",),
        "calibration_summary": ("sample_count",),
        "threshold_operating_point_summary": ("operating_point_count",),
        "benchmark_validation_summary": ("sample_count",),
    }[field_name]
    for key in count_fields:
        if key in value and (
            not isinstance(value[key], int) or isinstance(value[key], bool) or value[key] < 0
        ):
            errors.append(f"{field_name}.{key} must be a non-negative integer.")

    if field_name == "spatial_anomaly_map_summary" and "preview_paths" in value:
        previews = value["preview_paths"]
        if not isinstance(previews, list) or any(
            not isinstance(item, str) or not item or not item.lower().endswith(".png")
            for item in previews
        ):
            errors.append(
                "spatial_anomaly_map_summary.preview_paths must be a list of PNG paths."
            )
    if field_name == "benchmark_validation_summary":
        _required_string(value, field_name, "dataset_name", errors)
        metrics = value.get("metrics")
        if metrics is not None and (
            not isinstance(metrics, dict)
            or any(
                not isinstance(metric, int | float)
                or isinstance(metric, bool)
                or not math.isfinite(float(metric))
                for metric in metrics.values()
            )
        ):
            errors.append(
                "benchmark_validation_summary.metrics must contain finite numeric values."
            )


def _required_string(
    value: dict[str, Any], section: str, key: str, errors: list[str]
) -> None:
    item = value.get(key)
    if not isinstance(item, str) or not item.strip() or "\x00" in item:
        errors.append(f"{section}.{key} must be a non-empty string.")


def _require_list(report: dict[str, Any], field_name: str, errors: list[str]) -> None:
    value = report.get(field_name)
    if value is not None and not isinstance(value, list):
        errors.append(f"{field_name} must be a list.")


def _require_optional_object(
    report: dict[str, Any],
    field_name: str,
    errors: list[str],
) -> None:
    value = report.get(field_name)
    if value is not None and not isinstance(value, dict):
        errors.append(f"{field_name} must be an object when present.")


def _warn_for_missing_ids(value: object, id_field: str, warnings: list[str]) -> None:
    if not isinstance(value, list):
        return
    for index, item in enumerate(value, start=1):
        if isinstance(item, dict) and not item.get(id_field):
            warnings.append(f"{id_field} missing for item {index}.")


def _warn_for_review_memory_signals(value: object, warnings: list[str]) -> None:
    if not isinstance(value, list):
        return
    required_fields = {
        "priority_delta",
        "matched_feedback_count",
        "positive_feedback_count",
        "negative_feedback_count",
        "known_pattern_count",
        "duplicate_count",
        "notes",
        "explanation",
    }
    for index, item in enumerate(value, start=1):
        if not isinstance(item, dict) or "review_memory_signal" not in item:
            continue
        signal = item["review_memory_signal"]
        if not isinstance(signal, dict):
            warnings.append(f"review_memory_signal must be an object for item {index}.")
            continue
        missing = sorted(required_fields.difference(signal))
        if missing:
            warnings.append(
                f"review_memory_signal missing fields for item {index}: "
                + ", ".join(missing)
            )

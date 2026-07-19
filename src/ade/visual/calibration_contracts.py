"""Typed contracts for optional fitted calibration and threshold evaluation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

CalibrationMethod = Literal["identity", "empirical_percentile", "minmax"]
ThresholdStrategy = Literal["explicit", "percentile", "top_fraction"]


@dataclass(frozen=True)
class ScoreDistributionSummary:
    count: int
    minimum: float
    maximum: float
    mean: float
    std: float
    quantiles: dict[str, float]


@dataclass(frozen=True)
class CalibrationDatasetSummary:
    score_source: str
    score_type: str
    score_count: int
    distribution: ScoreDistributionSummary
    labels_available: bool = False
    positive_count: int | None = None
    negative_count: int | None = None


@dataclass(frozen=True)
class CalibrationMethodConfig:
    method: CalibrationMethod = "identity"
    clip: bool = True


@dataclass(frozen=True)
class FittedCalibrationModel:
    method: CalibrationMethod
    fitted_at: str
    score_source: str
    score_count: int
    distribution: ScoreDistributionSummary
    calibrated: bool
    config_fingerprint: str
    data_fingerprint: str
    parameters: dict[str, Any] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class ThresholdCandidate:
    strategy: ThresholdStrategy
    value: float
    score_threshold: float
    score_quantile: float
    candidate_id: str


@dataclass(frozen=True)
class ThresholdEvaluationResult:
    candidate: ThresholdCandidate
    selected_count: int
    selected_fraction: float
    score_range_selected: tuple[float, float] | None
    supervised_metrics_available: bool
    true_positives: int | None = None
    false_positives: int | None = None
    true_negatives: int | None = None
    false_negatives: int | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class OperatingPointSummary:
    candidate_id: str
    threshold_strategy: ThresholdStrategy
    score_threshold: float
    selected_count: int
    selected_fraction: float
    requires_human_review: bool = True


@dataclass(frozen=True)
class CalibrationProvenance:
    source_score_artifact: str
    source_score_fingerprint: str
    score_type: str
    calibration_method: CalibrationMethod
    threshold_strategy: str
    config_fingerprint: str
    data_fingerprint: str
    generated_at: str
    calibrated: bool
    human_review_required: bool = True
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class CalibrationResult:
    schema_version: int
    dataset: CalibrationDatasetSummary
    fitted_model: FittedCalibrationModel
    calibrated_scores: tuple[float, ...]
    threshold_evaluations: tuple[ThresholdEvaluationResult, ...]
    operating_points: tuple[OperatingPointSummary, ...]
    provenance: CalibrationProvenance

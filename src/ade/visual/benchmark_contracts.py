"""Typed contracts for the visual benchmark validation harness."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, Literal

from ade.visual.calibration_contracts import ScoreDistributionSummary


class VisualBenchmarkLabel(StrEnum):
    NORMAL = "normal"
    ANOMALY = "anomaly"
    UNKNOWN = "unknown"


@dataclass(frozen=True)
class VisualBenchmarkSample:
    sample_id: str
    image_path: str
    label: VisualBenchmarkLabel
    mask_path: str | None = None
    anomaly_type: str | None = None
    category: str | None = None
    image_sha256: str | None = None
    mask_sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VisualBenchmarkSplit:
    name: str
    samples: tuple[VisualBenchmarkSample, ...]


@dataclass(frozen=True)
class VisualBenchmarkDatasetManifest:
    schema_version: int
    dataset_name: str
    dataset_version: str
    dataset_root: str
    splits: tuple[VisualBenchmarkSplit, ...]
    dataset_sha256: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class VisualBenchmarkRunConfig:
    split_name: str
    use_calibrated_score: bool = False
    precision_recall_k: tuple[int, ...] = (1, 5, 10)
    explicit_thresholds: tuple[float, ...] = ()
    percentile_thresholds: tuple[float, ...] = ()
    top_k: tuple[int, ...] = ()
    top_fractions: tuple[float, ...] = ()


@dataclass(frozen=True)
class VisualBenchmarkPrediction:
    sample_id: str
    score: float
    calibrated_score: float | None = None
    selected: bool | None = None
    threshold_id: str | None = None
    score_source: str | None = None
    evidence_path: str | None = None


@dataclass(frozen=True)
class VisualBenchmarkMetricSummary:
    sample_count: int
    scored_count: int
    labeled_count: int
    normal_count: int
    anomaly_count: int
    unknown_count: int
    score_distribution: ScoreDistributionSummary | None
    supervised_metrics_available: bool
    auroc: float | None
    average_precision: float | None
    precision_at_k: dict[str, float | None]
    recall_at_k: dict[str, float | None]
    selected_count: int
    selected_fraction: float
    score_range: tuple[float, float] | None
    warnings: tuple[str, ...] = ()


BenchmarkOperatingPointStrategy = Literal["explicit", "percentile", "top_k", "top_fraction"]


@dataclass(frozen=True)
class VisualBenchmarkOperatingPointResult:
    operating_point_id: str
    strategy: BenchmarkOperatingPointStrategy
    value: float
    score_threshold: float
    selected_count: int
    selected_fraction: float
    supervised_metrics_available: bool
    true_positives: int | None = None
    false_positives: int | None = None
    true_negatives: int | None = None
    false_negatives: int | None = None
    precision: float | None = None
    recall: float | None = None
    f1: float | None = None
    requires_human_review: bool = True
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class VisualBenchmarkProvenance:
    benchmark_manifest_path: str
    benchmark_manifest_fingerprint: str
    prediction_fingerprint: str
    config_fingerprint: str
    dataset_name: str
    dataset_version: str
    split_name: str
    generated_at: str
    score_type: str
    externally_provisioned: bool = True
    human_review_required: bool = True
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class VisualBenchmarkResult:
    schema_version: int
    metrics: VisualBenchmarkMetricSummary
    operating_points: tuple[VisualBenchmarkOperatingPointResult, ...]
    predictions: tuple[VisualBenchmarkPrediction, ...]
    missing_prediction_ids: tuple[str, ...]
    provenance: VisualBenchmarkProvenance

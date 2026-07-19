"""Dependency-free evaluation for explicit visual benchmark predictions."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict
from datetime import UTC, datetime

from ade.visual.benchmark_contracts import (
    BenchmarkOperatingPointStrategy,
    VisualBenchmarkDatasetManifest,
    VisualBenchmarkLabel,
    VisualBenchmarkMetricSummary,
    VisualBenchmarkOperatingPointResult,
    VisualBenchmarkPrediction,
    VisualBenchmarkProvenance,
    VisualBenchmarkResult,
    VisualBenchmarkRunConfig,
    VisualBenchmarkSample,
)
from ade.visual.benchmark_manifests import serialize_visual_benchmark_manifest
from ade.visual.calibration import summarize_scores
from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.errors import VisualIntegrityError
from ade.visual.fingerprints import normalize_relative_path


def evaluate_visual_benchmark(
    manifest: VisualBenchmarkDatasetManifest,
    predictions: tuple[VisualBenchmarkPrediction, ...] | list[VisualBenchmarkPrediction],
    config: VisualBenchmarkRunConfig,
    *,
    benchmark_manifest_path: str = "",
    generated_at: str | None = None,
) -> VisualBenchmarkResult:
    """Evaluate explicit predictions without running the ADE pipeline."""

    split = next((item for item in manifest.splits if item.name == config.split_name), None)
    if split is None:
        raise VisualIntegrityError(f"Benchmark split does not exist: {config.split_name}")
    _validate_config(config)
    ordered_predictions = _validate_predictions(predictions, config.use_calibrated_score)
    samples = {item.sample_id: item for item in split.samples}
    prediction_by_id = {item.sample_id: item for item in ordered_predictions}
    extra = sorted(set(prediction_by_id) - set(samples))
    if extra:
        raise VisualIntegrityError(
            "Predictions contain sample IDs outside the selected benchmark split",
            context={"sample_ids": extra},
        )
    scored = [
        (samples[item.sample_id], item, _prediction_score(item, config.use_calibrated_score))
        for item in ordered_predictions
    ]
    missing = tuple(sorted(set(samples) - set(prediction_by_id)))
    metrics = _metrics(tuple(samples.values()), scored, config, missing)
    operating_points = _operating_points(scored, config)
    manifest_json = serialize_visual_benchmark_manifest(manifest)
    provenance = VisualBenchmarkProvenance(
        benchmark_manifest_path=benchmark_manifest_path,
        benchmark_manifest_fingerprint=hashlib.sha256(manifest_json.encode()).hexdigest(),
        prediction_fingerprint=_fingerprint([asdict(item) for item in ordered_predictions]),
        config_fingerprint=_fingerprint(asdict(config)),
        dataset_name=manifest.dataset_name,
        dataset_version=manifest.dataset_version,
        split_name=config.split_name,
        generated_at=generated_at or datetime.now(UTC).isoformat(),
        score_type="calibrated_score" if config.use_calibrated_score else "raw_score",
        limitations=(
            "Benchmark results are validation artifacts, not product guarantees.",
            "Operating points are review-prioritization signals and require human review.",
            "Externally provisioned dataset quality and labels remain the "
            "evaluator's responsibility.",
        ),
    )
    return VisualBenchmarkResult(
        VISUAL_ENGINE_SCHEMA_VERSION,
        metrics,
        operating_points,
        ordered_predictions,
        missing,
        provenance,
    )


def _metrics(
    samples: tuple[VisualBenchmarkSample, ...],
    scored: list[tuple[VisualBenchmarkSample, VisualBenchmarkPrediction, float]],
    config: VisualBenchmarkRunConfig,
    missing: tuple[str, ...],
) -> VisualBenchmarkMetricSummary:
    labels = [sample.label for sample in samples]
    normal_count = labels.count(VisualBenchmarkLabel.NORMAL)
    anomaly_count = labels.count(VisualBenchmarkLabel.ANOMALY)
    unknown_count = labels.count(VisualBenchmarkLabel.UNKNOWN)
    scores = [score for _, _, score in scored]
    labeled_scored = [item for item in scored if item[0].label != VisualBenchmarkLabel.UNKNOWN]
    positives = sum(item[0].label == VisualBenchmarkLabel.ANOMALY for item in labeled_scored)
    negatives = sum(item[0].label == VisualBenchmarkLabel.NORMAL for item in labeled_scored)
    supervised = positives > 0 and negatives > 0
    warnings: list[str] = []
    if missing:
        warnings.append(
            "Some benchmark samples have no prediction and are excluded from score metrics."
        )
    if not positives:
        warnings.append(
            "No scored positive labels are available; positive-class metrics are unavailable."
        )
    if not negatives:
        warnings.append("No scored negative labels are available; AUROC is unavailable.")
    if scores and min(scores) == max(scores):
        warnings.append("All prediction scores are equal; ranking metrics have limited meaning.")
    ranked_labeled = sorted(labeled_scored, key=lambda item: (-item[2], item[0].sample_id))
    precision_at_k: dict[str, float | None] = {}
    recall_at_k: dict[str, float | None] = {}
    for k in sorted(set(config.precision_recall_k)):
        top = ranked_labeled[:k]
        found = sum(item[0].label == VisualBenchmarkLabel.ANOMALY for item in top)
        precision_at_k[str(k)] = found / len(top) if top else None
        recall_at_k[str(k)] = found / positives if positives else None
    explicitly_selected = [item for item in scored if item[1].selected is True]
    return VisualBenchmarkMetricSummary(
        sample_count=len(samples),
        scored_count=len(scored),
        labeled_count=normal_count + anomaly_count,
        normal_count=normal_count,
        anomaly_count=anomaly_count,
        unknown_count=unknown_count,
        score_distribution=summarize_scores(scores) if scores else None,
        supervised_metrics_available=supervised,
        auroc=_auroc(labeled_scored) if supervised else None,
        average_precision=_average_precision(labeled_scored) if positives else None,
        precision_at_k=precision_at_k if positives else {key: None for key in precision_at_k},
        recall_at_k=recall_at_k,
        selected_count=len(explicitly_selected),
        selected_fraction=len(explicitly_selected) / len(scored) if scored else 0.0,
        score_range=(min(scores), max(scores)) if scores else None,
        warnings=tuple(warnings),
    )


def _auroc(
    records: list[tuple[VisualBenchmarkSample, VisualBenchmarkPrediction, float]],
) -> float:
    positives = [
        score for sample, _, score in records if sample.label == VisualBenchmarkLabel.ANOMALY
    ]
    negatives = [
        score for sample, _, score in records if sample.label == VisualBenchmarkLabel.NORMAL
    ]
    favorable = math.fsum(
        1.0 if positive > negative else 0.5 if positive == negative else 0.0
        for positive in positives
        for negative in negatives
    )
    return favorable / (len(positives) * len(negatives))


def _average_precision(
    records: list[tuple[VisualBenchmarkSample, VisualBenchmarkPrediction, float]],
) -> float:
    """Tie-grouped average precision (area under the stepwise precision-recall curve)."""

    positives = sum(sample.label == VisualBenchmarkLabel.ANOMALY for sample, _, _ in records)
    grouped: dict[float, list[VisualBenchmarkSample]] = {}
    for sample, _, score in records:
        grouped.setdefault(score, []).append(sample)
    true_positives = 0
    selected = 0
    previous_recall = 0.0
    area = 0.0
    for score in sorted(grouped, reverse=True):
        group = grouped[score]
        selected += len(group)
        true_positives += sum(item.label == VisualBenchmarkLabel.ANOMALY for item in group)
        recall = true_positives / positives
        precision = true_positives / selected
        area += (recall - previous_recall) * precision
        previous_recall = recall
    return area


def _operating_points(
    scored: list[tuple[VisualBenchmarkSample, VisualBenchmarkPrediction, float]],
    config: VisualBenchmarkRunConfig,
) -> tuple[VisualBenchmarkOperatingPointResult, ...]:
    if not scored:
        return ()
    values = sorted(score for _, _, score in scored)
    selections: list[tuple[BenchmarkOperatingPointStrategy, float, float, set[str]]] = []
    for threshold in config.explicit_thresholds:
        selections.append(("explicit", threshold, threshold, _at_least(scored, threshold)))
    for percentile in config.percentile_thresholds:
        threshold = _quantile(values, percentile / 100)
        selections.append(("percentile", percentile, threshold, _at_least(scored, threshold)))
    ranked = sorted(scored, key=lambda item: (-item[2], item[0].sample_id))
    for k in config.top_k:
        chosen = {item[0].sample_id for item in ranked[:k]}
        threshold = ranked[min(k, len(ranked)) - 1][2]
        selections.append(("top_k", float(k), threshold, chosen))
    for fraction in config.top_fractions:
        count = max(1, math.ceil(len(scored) * fraction))
        threshold = values[-count]
        selections.append(("top_fraction", fraction, threshold, _at_least(scored, threshold)))
    results = [_operating_result(scored, *selection) for selection in selections]
    unique = {item.operating_point_id: item for item in results}
    return tuple(unique[key] for key in sorted(unique))


def _operating_result(
    scored: list[tuple[VisualBenchmarkSample, VisualBenchmarkPrediction, float]],
    strategy: BenchmarkOperatingPointStrategy,
    value: float,
    threshold: float,
    selected_ids: set[str],
) -> VisualBenchmarkOperatingPointResult:
    labeled = [item for item in scored if item[0].label != VisualBenchmarkLabel.UNKNOWN]
    positives = sum(item[0].label == VisualBenchmarkLabel.ANOMALY for item in labeled)
    negatives = sum(item[0].label == VisualBenchmarkLabel.NORMAL for item in labeled)
    supervised = positives > 0 and negatives > 0
    tp = sum(
        item[0].label == VisualBenchmarkLabel.ANOMALY and item[0].sample_id in selected_ids
        for item in labeled
    )
    fp = sum(
        item[0].label == VisualBenchmarkLabel.NORMAL and item[0].sample_id in selected_ids
        for item in labeled
    )
    tn = negatives - fp
    fn = positives - tp
    precision = tp / (tp + fp) if supervised and tp + fp else None
    recall = tp / positives if supervised else None
    f1 = (
        2 * precision * recall / (precision + recall)
        if precision is not None and recall is not None and precision + recall
        else None
    )
    warnings = () if supervised else ("Supervised metrics unavailable at this operating point.",)
    identity = _fingerprint({"strategy": strategy, "value": value, "threshold": threshold})[:16]
    return VisualBenchmarkOperatingPointResult(
        identity,
        strategy,
        value,
        threshold,
        len(selected_ids),
        len(selected_ids) / len(scored),
        supervised,
        tp if supervised else None,
        fp if supervised else None,
        tn if supervised else None,
        fn if supervised else None,
        precision,
        recall,
        f1,
        True,
        warnings,
    )


def _validate_predictions(
    predictions: tuple[VisualBenchmarkPrediction, ...] | list[VisualBenchmarkPrediction],
    use_calibrated: bool,
) -> tuple[VisualBenchmarkPrediction, ...]:
    ids: set[str] = set()
    output: list[VisualBenchmarkPrediction] = []
    for prediction in predictions:
        if not prediction.sample_id.strip() or prediction.sample_id in ids:
            raise VisualIntegrityError("Prediction sample IDs must be non-empty and unique")
        ids.add(prediction.sample_id)
        _finite(prediction.score, "prediction score")
        if prediction.calibrated_score is not None:
            _finite(prediction.calibrated_score, "calibrated score")
        if use_calibrated and prediction.calibrated_score is None:
            raise VisualIntegrityError(
                "Configured calibrated-score evaluation requires fitted scores"
            )
        if prediction.evidence_path is not None:
            normalized = normalize_relative_path(prediction.evidence_path)
            if normalized != prediction.evidence_path:
                raise VisualIntegrityError(
                    "Prediction evidence paths must be canonical and relative"
                )
        output.append(prediction)
    return tuple(sorted(output, key=lambda item: item.sample_id))


def _validate_config(config: VisualBenchmarkRunConfig) -> None:
    if not config.split_name.strip():
        raise ValueError("split_name must be non-empty")
    if any(
        isinstance(k, bool) or not isinstance(k, int) or k <= 0 for k in config.precision_recall_k
    ):
        raise ValueError("precision_recall_k values must be positive integers")
    if any(isinstance(k, bool) or not isinstance(k, int) or k <= 0 for k in config.top_k):
        raise ValueError("top_k operating points must be positive integers")
    for value in (
        *config.explicit_thresholds,
        *config.percentile_thresholds,
        *config.top_fractions,
    ):
        _finite(value, "operating point value")
    if any(value < 0 or value > 100 for value in config.percentile_thresholds):
        raise ValueError("percentile thresholds must be between 0 and 100")
    if any(value <= 0 or value > 1 for value in config.top_fractions):
        raise ValueError("top fractions must be greater than 0 and at most 1")


def _prediction_score(prediction: VisualBenchmarkPrediction, calibrated: bool) -> float:
    value = prediction.calibrated_score if calibrated else prediction.score
    if value is None:
        raise VisualIntegrityError("Calibrated score metadata is missing")
    return float(value)


def _at_least(
    scored: list[tuple[VisualBenchmarkSample, VisualBenchmarkPrediction, float]], threshold: float
) -> set[str]:
    return {sample.sample_id for sample, _, score in scored if score >= threshold}


def _quantile(values: list[float], fraction: float) -> float:
    position = (len(values) - 1) * fraction
    lower, upper = math.floor(position), math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _finite(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float) or not math.isfinite(value):
        raise VisualIntegrityError(f"{name} must be finite and numeric")
    return float(value)


def _fingerprint(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode()).hexdigest()

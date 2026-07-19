"""Dependency-free fitted calibration and threshold-candidate evaluation."""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import asdict
from datetime import UTC, datetime

from ade.visual.calibration_contracts import (
    CalibrationDatasetSummary,
    CalibrationMethodConfig,
    CalibrationProvenance,
    CalibrationResult,
    FittedCalibrationModel,
    OperatingPointSummary,
    ScoreDistributionSummary,
    ThresholdCandidate,
    ThresholdEvaluationResult,
)
from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.errors import VisualIntegrityError

_QUANTILES = (0.0, 0.25, 0.5, 0.75, 1.0)


def fit_calibration(
    scores: Sequence[float],
    config: CalibrationMethodConfig,
    *,
    score_source: str,
    fitted_at: str | None = None,
) -> FittedCalibrationModel:
    """Fit optional score calibration metadata from a held-out/reference distribution."""

    values = _validated_scores(scores)
    if config.method not in {"identity", "empirical_percentile", "minmax"}:
        raise ValueError(f"Unsupported calibration method: {config.method}")
    if not score_source.strip():
        raise ValueError("score_source must be non-empty")
    distribution = summarize_scores(values)
    config_payload = asdict(config)
    warnings: list[str] = []
    parameters: dict[str, object] = {}
    calibrated = config.method != "identity"
    if config.method == "empirical_percentile":
        parameters["reference_scores"] = sorted(values)
        parameters["semantics"] = "right-inclusive empirical cumulative percentile"
    elif config.method == "minmax":
        parameters.update(
            {
                "minimum": distribution.minimum,
                "maximum": distribution.maximum,
                "clip": config.clip,
            }
        )
        if distribution.minimum == distribution.maximum:
            warnings.append("Held-out score range is constant; fitted minmax outputs 0.0.")
    else:
        parameters["semantics"] = "raw score unchanged"
    return FittedCalibrationModel(
        method=config.method,
        fitted_at=fitted_at or datetime.now(UTC).isoformat(),
        score_source=score_source,
        score_count=len(values),
        distribution=distribution,
        calibrated=calibrated,
        config_fingerprint=_fingerprint(config_payload),
        data_fingerprint=_fingerprint(values),
        parameters=parameters,
        warnings=tuple(warnings),
    )


def apply_calibration(scores: Sequence[float], model: FittedCalibrationModel) -> tuple[float, ...]:
    """Apply a fitted transform; calibrated outputs are scores, never probabilities."""

    values = _validated_scores(scores)
    if model.method == "identity":
        return tuple(values)
    if model.method == "empirical_percentile":
        reference = model.parameters.get("reference_scores")
        if not isinstance(reference, list) or not reference:
            raise VisualIntegrityError("Empirical calibration is missing fitted reference scores")
        fitted = _validated_scores(reference)
        return tuple(_upper_bound(fitted, value) / len(fitted) for value in values)
    if model.method == "minmax":
        minimum = _finite_parameter(model, "minimum")
        maximum = _finite_parameter(model, "maximum")
        clip = model.parameters.get("clip")
        if not isinstance(clip, bool) or maximum < minimum:
            raise VisualIntegrityError("Minmax calibration metadata is invalid")
        if maximum == minimum:
            return tuple(0.0 for _ in values)
        output = ((value - minimum) / (maximum - minimum) for value in values)
        return tuple(min(1.0, max(0.0, value)) if clip else value for value in output)
    raise VisualIntegrityError(f"Unsupported fitted calibration method: {model.method}")


def summarize_scores(scores: Sequence[float]) -> ScoreDistributionSummary:
    values = sorted(_validated_scores(scores))
    count = len(values)
    mean = math.fsum(values) / count
    variance = math.fsum((value - mean) ** 2 for value in values) / count
    return ScoreDistributionSummary(
        count=count,
        minimum=values[0],
        maximum=values[-1],
        mean=mean,
        std=math.sqrt(variance),
        quantiles={_quantile_name(q): _linear_quantile(values, q) for q in _QUANTILES},
    )


def generate_threshold_candidates(
    scores: Sequence[float],
    *,
    explicit_thresholds: Sequence[float] = (),
    percentile_thresholds: Sequence[float] = (),
    top_fractions: Sequence[float] = (),
) -> tuple[ThresholdCandidate, ...]:
    """Create deterministic candidate operating points from supported strategies."""

    values = sorted(_validated_scores(scores))
    candidates: list[ThresholdCandidate] = []
    for raw in explicit_thresholds:
        threshold = _finite_float(raw, "explicit threshold")
        candidates.append(_candidate("explicit", threshold, threshold, values))
    for raw in percentile_thresholds:
        percentile = _finite_float(raw, "percentile threshold")
        if percentile < 0 or percentile > 100:
            raise ValueError("percentile thresholds must be between 0 and 100")
        threshold = _linear_quantile(values, percentile / 100)
        candidates.append(_candidate("percentile", percentile, threshold, values))
    for raw in top_fractions:
        fraction = _finite_float(raw, "top_fraction threshold")
        if fraction <= 0 or fraction > 1:
            raise ValueError("top_fraction thresholds must be greater than 0 and at most 1")
        selected = max(1, math.ceil(len(values) * fraction))
        threshold = values[-selected]
        candidates.append(_candidate("top_fraction", fraction, threshold, values))
    unique = {item.candidate_id: item for item in candidates}
    return tuple(unique[key] for key in sorted(unique))


def evaluate_thresholds(
    ids: Sequence[str],
    scores: Sequence[float],
    candidates: Sequence[ThresholdCandidate],
    *,
    labels: Mapping[str, object] | None = None,
) -> tuple[ThresholdEvaluationResult, ...]:
    """Evaluate candidate operating points with labels or workload-only metrics."""

    values = _validated_scores(scores)
    if len(ids) != len(values):
        raise ValueError("ids and scores must have the same length")
    if len(set(ids)) != len(ids) or any(not isinstance(item, str) or not item for item in ids):
        raise VisualIntegrityError("Score IDs must be non-empty and unique")
    normalized_labels = _labels_for_ids(ids, labels)
    output: list[ThresholdEvaluationResult] = []
    for candidate in candidates:
        selected = [
            index for index, score in enumerate(values) if score >= candidate.score_threshold
        ]
        selected_scores = [values[index] for index in selected]
        fraction = len(selected) / len(values)
        if normalized_labels is None:
            output.append(
                ThresholdEvaluationResult(
                    candidate,
                    len(selected),
                    fraction,
                    _score_range(selected_scores),
                    False,
                    warnings=(
                        "Supervised metrics unavailable; this operating point "
                        "estimates review workload only.",
                    ),
                )
            )
            continue
        predicted = set(selected)
        tp = sum(normalized_labels[i] and i in predicted for i in range(len(values)))
        fp = sum(not normalized_labels[i] and i in predicted for i in range(len(values)))
        tn = sum(not normalized_labels[i] and i not in predicted for i in range(len(values)))
        fn = sum(normalized_labels[i] and i not in predicted for i in range(len(values)))
        precision = tp / (tp + fp) if tp + fp else None
        recall = tp / (tp + fn) if tp + fn else None
        f1 = (
            2 * precision * recall / (precision + recall)
            if precision is not None and recall is not None and precision + recall
            else None
        )
        warnings: list[str] = []
        positives = tp + fn
        negatives = tn + fp
        if positives == 0:
            warnings.append("Held-out labels contain no positives; recall and F1 are unavailable.")
        if negatives == 0:
            warnings.append("Held-out labels contain no negatives.")
        if positives and negatives and min(positives, negatives) / len(values) < 0.1:
            warnings.append("Held-out labels are class-imbalanced; interpret metrics cautiously.")
        if precision is None:
            warnings.append("Precision is unavailable because no items were selected.")
        output.append(
            ThresholdEvaluationResult(
                candidate,
                len(selected),
                fraction,
                _score_range(selected_scores),
                True,
                tp,
                fp,
                tn,
                fn,
                precision,
                recall,
                f1,
                tuple(warnings),
            )
        )
    return tuple(output)


def build_calibration_result(
    ids: Sequence[str],
    scores: Sequence[float],
    model: FittedCalibrationModel,
    candidates: Sequence[ThresholdCandidate],
    *,
    score_type: str,
    source_score_artifact: str = "",
    source_score_fingerprint: str = "",
    labels: Mapping[str, object] | None = None,
    generated_at: str | None = None,
) -> CalibrationResult:
    """Build a serializable optional calibration/evaluation result."""

    calibrated_scores = apply_calibration(scores, model)
    evaluations = evaluate_thresholds(ids, calibrated_scores, candidates, labels=labels)
    normalized_labels = _labels_for_ids(ids, labels)
    positives = sum(normalized_labels) if normalized_labels is not None else None
    dataset = CalibrationDatasetSummary(
        model.score_source,
        score_type,
        len(scores),
        summarize_scores(scores),
        normalized_labels is not None,
        positives,
        None if positives is None else len(scores) - positives,
    )
    strategies = sorted({item.strategy for item in candidates})
    provenance = CalibrationProvenance(
        source_score_artifact=source_score_artifact,
        source_score_fingerprint=source_score_fingerprint,
        score_type=score_type,
        calibration_method=model.method,
        threshold_strategy=",".join(strategies) if strategies else "none",
        config_fingerprint=model.config_fingerprint,
        data_fingerprint=model.data_fingerprint,
        generated_at=generated_at or datetime.now(UTC).isoformat(),
        calibrated=model.calibrated,
        limitations=(
            "Calibrated scores are fitted transformations, not universal anomaly probabilities.",
            "Threshold candidates are review-prioritization signals and require human review.",
        ),
    )
    operating = tuple(
        OperatingPointSummary(
            item.candidate.candidate_id,
            item.candidate.strategy,
            item.candidate.score_threshold,
            item.selected_count,
            item.selected_fraction,
        )
        for item in evaluations
    )
    return CalibrationResult(
        VISUAL_ENGINE_SCHEMA_VERSION,
        dataset,
        model,
        calibrated_scores,
        evaluations,
        operating,
        provenance,
    )


def _validated_scores(scores: Sequence[float]) -> list[float]:
    if not scores:
        raise VisualIntegrityError("At least one score is required")
    return [_finite_float(value, "score") for value in scores]


def _finite_float(value: object, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise VisualIntegrityError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise VisualIntegrityError(f"{name} must be finite")
    return result


def _finite_parameter(model: FittedCalibrationModel, name: str) -> float:
    if name not in model.parameters:
        raise VisualIntegrityError(f"Calibration metadata is missing {name}")
    return _finite_float(model.parameters[name], f"calibration {name}")


def _labels_for_ids(ids: Sequence[str], labels: Mapping[str, object] | None) -> list[bool] | None:
    if labels is None or any(item not in labels for item in ids):
        return None
    unknown = set(labels) - set(ids)
    if unknown:
        raise VisualIntegrityError("Labels contain IDs absent from the score set")
    normalized: list[bool] = []
    for item in ids:
        value = labels[item]
        if value in (True, 1):
            normalized.append(True)
        elif value in (False, 0):
            normalized.append(False)
        else:
            raise VisualIntegrityError("Labels must be boolean or binary 0/1 values")
    return normalized


def _linear_quantile(values: Sequence[float], quantile: float) -> float:
    position = (len(values) - 1) * quantile
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    return values[lower] + (values[upper] - values[lower]) * (position - lower)


def _quantile_name(value: float) -> str:
    return f"p{round(value * 100):02d}"


def _upper_bound(values: Sequence[float], target: float) -> int:
    low, high = 0, len(values)
    while low < high:
        middle = (low + high) // 2
        if target < values[middle]:
            high = middle
        else:
            low = middle + 1
    return low


def _candidate(
    strategy: str, value: float, threshold: float, scores: Sequence[float]
) -> ThresholdCandidate:
    quantile = _upper_bound(scores, threshold) / len(scores)
    payload = {"strategy": strategy, "value": value, "score_threshold": threshold}
    return ThresholdCandidate(strategy, value, threshold, quantile, _fingerprint(payload)[:16])  # type: ignore[arg-type]


def _score_range(values: Sequence[float]) -> tuple[float, float] | None:
    return (min(values), max(values)) if values else None


def _fingerprint(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()

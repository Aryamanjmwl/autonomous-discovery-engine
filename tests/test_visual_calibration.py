from __future__ import annotations

import json
from pathlib import Path

import pytest

from ade.visual import (
    CalibrationMethodConfig,
    VisualIntegrityError,
    apply_calibration,
    build_calibration_result,
    evaluate_thresholds,
    fit_calibration,
    generate_threshold_candidates,
    publish_calibration_artifact,
    validate_calibration_artifact,
)


def fitted(method: str):
    return fit_calibration(
        [0.0, 1.0, 2.0, 3.0],
        CalibrationMethodConfig(method=method),  # type: ignore[arg-type]
        score_source="held-out.json",
        fitted_at="2026-01-01T00:00:00+00:00",
    )


def test_identity_calibration_is_not_marked_calibrated() -> None:
    model = fitted("identity")
    assert apply_calibration([0.5, 4.0], model) == (0.5, 4.0)
    assert model.calibrated is False


def test_empirical_percentile_is_fitted_score_not_probability() -> None:
    model = fitted("empirical_percentile")
    assert apply_calibration([-1.0, 0.0, 1.5, 3.0, 4.0], model) == (0, 0.25, 0.5, 1, 1)
    assert model.calibrated is True


def test_minmax_clips_and_constant_range_is_clear() -> None:
    model = fitted("minmax")
    assert apply_calibration([-1.0, 1.5, 4.0], model) == (0, 0.5, 1)
    constant = fit_calibration(
        [2, 2],
        CalibrationMethodConfig(method="minmax"),
        score_source="held-out",
        fitted_at="2026-01-01T00:00:00+00:00",
    )
    assert apply_calibration([1, 2, 3], constant) == (0, 0, 0)
    assert constant.warnings


def test_fitted_metadata_is_deterministic_with_explicit_timestamp() -> None:
    first = fitted("empirical_percentile")
    assert first == fitted("empirical_percentile")
    assert first.score_count == 4
    assert first.distribution.quantiles["p50"] == 1.5
    assert len(first.config_fingerprint) == len(first.data_fingerprint) == 64


@pytest.mark.parametrize("scores", [[], [float("nan")], [float("inf")]])
def test_invalid_scores_rejected(scores: list[float]) -> None:
    with pytest.raises(VisualIntegrityError):
        fit_calibration(scores, CalibrationMethodConfig(), score_source="held-out")


def test_duplicate_ids_rejected() -> None:
    candidate = generate_threshold_candidates([1, 2], explicit_thresholds=[1])[0]
    with pytest.raises(VisualIntegrityError):
        evaluate_thresholds(["same", "same"], [1, 2], [candidate])


def test_explicit_threshold_without_labels_is_workload_only() -> None:
    candidate = generate_threshold_candidates([1, 2, 3], explicit_thresholds=[2])[0]
    result = evaluate_thresholds(["a", "b", "c"], [1, 2, 3], [candidate])[0]
    assert result.selected_count == 2
    assert result.selected_fraction == pytest.approx(2 / 3)
    assert result.score_range_selected == (2, 3)
    assert result.supervised_metrics_available is False
    assert result.precision is None


def test_percentile_and_top_fraction_threshold_candidates() -> None:
    candidates = generate_threshold_candidates(
        [0, 1, 2, 3], percentile_thresholds=[50], top_fractions=[0.25]
    )
    percentile = next(item for item in candidates if item.strategy == "percentile")
    top = next(item for item in candidates if item.strategy == "top_fraction")
    assert percentile.score_threshold == 1.5
    assert top.score_threshold == 3
    assert evaluate_thresholds(["a", "b", "c", "d"], [0, 1, 2, 3], [top])[0].selected_count == 1


def test_supervised_metrics_and_divide_by_zero_safety() -> None:
    candidates = generate_threshold_candidates([0, 1, 2, 3], explicit_thresholds=[2, 4])
    results = evaluate_thresholds(
        ["a", "b", "c", "d"],
        [0, 1, 2, 3],
        candidates,
        labels={"a": 0, "b": 0, "c": 1, "d": 1},
    )
    perfect = next(item for item in results if item.candidate.score_threshold == 2)
    empty = next(item for item in results if item.candidate.score_threshold == 4)
    assert (
        perfect.true_positives,
        perfect.false_positives,
        perfect.true_negatives,
        perfect.false_negatives,
    ) == (2, 0, 2, 0)
    assert (perfect.precision, perfect.recall, perfect.f1) == (1, 1, 1)
    assert empty.precision is None and empty.f1 is None


def test_missing_labels_fall_back_to_unsupervised_and_invalid_labels_rejected() -> None:
    candidate = generate_threshold_candidates([1, 2], explicit_thresholds=[1])[0]
    result = evaluate_thresholds(["a", "b"], [1, 2], [candidate], labels={"a": 1})[0]
    assert result.supervised_metrics_available is False
    with pytest.raises(VisualIntegrityError):
        evaluate_thresholds(["a", "b"], [1, 2], [candidate], labels={"a": 1, "b": "yes"})


def calibration_result():
    model = fitted("minmax")
    candidates = generate_threshold_candidates([0, 1], explicit_thresholds=[0.5])
    return build_calibration_result(
        ["a", "b"],
        [0, 3],
        model,
        candidates,
        score_type="image_raw_score",
        source_score_artifact="scores/summary.json",
        source_score_fingerprint="a" * 64,
        generated_at="2026-01-01T00:00:00+00:00",
    )


def test_artifact_publish_validate_and_corruption(tmp_path: Path) -> None:
    root = publish_calibration_artifact(calibration_result(), tmp_path)
    assert validate_calibration_artifact(root) == calibration_result()
    (root / "calibration.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(VisualIntegrityError):
        validate_calibration_artifact(root)


def test_artifact_path_traversal_rejected(tmp_path: Path) -> None:
    root = publish_calibration_artifact(calibration_result(), tmp_path)
    manifest_path = root / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["result_path"] = "../calibration.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(ValueError):
        validate_calibration_artifact(root)


def test_default_pipeline_configuration_remains_disabled() -> None:
    from ade.visual import VisualReferenceScoringConfig

    assert VisualReferenceScoringConfig().enabled is False

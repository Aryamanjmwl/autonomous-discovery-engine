from __future__ import annotations

import json
from pathlib import Path

import pytest

from ade.visual import (
    VISUAL_ENGINE_SCHEMA_VERSION,
    VisualBenchmarkDatasetManifest,
    VisualBenchmarkLabel,
    VisualBenchmarkPrediction,
    VisualBenchmarkRunConfig,
    VisualBenchmarkSample,
    VisualBenchmarkSplit,
    VisualIntegrityError,
    deserialize_visual_benchmark_manifest,
    evaluate_visual_benchmark,
    load_visual_benchmark_manifest,
    publish_visual_benchmark_artifact,
    serialize_visual_benchmark_manifest,
    validate_visual_benchmark_artifact,
    validate_visual_benchmark_manifest,
)


def sample(sample_id: str, label: VisualBenchmarkLabel, path: str | None = None):
    return VisualBenchmarkSample(sample_id, path or f"images/{sample_id}.png", label)


def manifest(root: Path, samples=None):
    records = samples or (
        sample("n1", VisualBenchmarkLabel.NORMAL),
        sample("a1", VisualBenchmarkLabel.ANOMALY),
        sample("u1", VisualBenchmarkLabel.UNKNOWN),
        sample("n2", VisualBenchmarkLabel.NORMAL),
        sample("a2", VisualBenchmarkLabel.ANOMALY),
    )
    return VisualBenchmarkDatasetManifest(
        VISUAL_ENGINE_SCHEMA_VERSION,
        "tiny-fixture",
        "1",
        str(root),
        (VisualBenchmarkSplit("test", tuple(records)),),
    )


def predictions():
    return (
        VisualBenchmarkPrediction("n1", 0.1),
        VisualBenchmarkPrediction("a1", 0.9, selected=True),
        VisualBenchmarkPrediction("u1", 0.7),
        VisualBenchmarkPrediction("n2", 0.4),
        VisualBenchmarkPrediction("a2", 0.8, selected=True),
    )


def test_manifest_round_trip_validation_and_deterministic_order(tmp_path: Path) -> None:
    value = manifest(tmp_path, tuple(reversed(manifest(tmp_path).splits[0].samples)))
    payload = serialize_visual_benchmark_manifest(value)
    loaded = deserialize_visual_benchmark_manifest(payload)
    assert [item.sample_id for item in loaded.splits[0].samples] == ["a1", "a2", "n1", "n2", "u1"]
    assert serialize_visual_benchmark_manifest(loaded) == payload


def test_manifest_path_traversal_and_duplicate_ids_rejected(tmp_path: Path) -> None:
    with pytest.raises(VisualIntegrityError):
        validate_visual_benchmark_manifest(
            manifest(tmp_path, (sample("x", VisualBenchmarkLabel.NORMAL, "../x.png"),))
        )
    duplicate = (
        sample("x", VisualBenchmarkLabel.NORMAL),
        sample("x", VisualBenchmarkLabel.ANOMALY, "images/y.png"),
    )
    with pytest.raises(VisualIntegrityError):
        validate_visual_benchmark_manifest(manifest(tmp_path, duplicate))


def test_duplicate_image_paths_rejected(tmp_path: Path) -> None:
    records = (
        sample("x", VisualBenchmarkLabel.NORMAL, "images/same.png"),
        sample("y", VisualBenchmarkLabel.ANOMALY, "images/same.png"),
    )
    with pytest.raises(VisualIntegrityError):
        validate_visual_benchmark_manifest(manifest(tmp_path, records))


def test_strict_manifest_requires_images_and_optional_masks(tmp_path: Path) -> None:
    path = tmp_path / "benchmark.json"
    path.write_text(serialize_visual_benchmark_manifest(manifest(tmp_path)), encoding="utf-8")
    with pytest.raises(VisualIntegrityError):
        load_visual_benchmark_manifest(path, strict=True)
    for item in manifest(tmp_path).splits[0].samples:
        image = tmp_path / item.image_path
        image.parent.mkdir(parents=True, exist_ok=True)
        image.write_bytes(b"fixture")
    assert load_visual_benchmark_manifest(path, strict=True).dataset_name == "tiny-fixture"


@pytest.mark.parametrize("score", [float("nan"), float("inf")])
def test_prediction_validation_and_duplicate_rejection(tmp_path: Path, score: float) -> None:
    with pytest.raises(VisualIntegrityError):
        evaluate_visual_benchmark(
            manifest(tmp_path),
            [VisualBenchmarkPrediction("n1", score)],
            VisualBenchmarkRunConfig("test"),
        )
    with pytest.raises(VisualIntegrityError):
        evaluate_visual_benchmark(
            manifest(tmp_path),
            [VisualBenchmarkPrediction("n1", 0.1), VisualBenchmarkPrediction("n1", 0.2)],
            VisualBenchmarkRunConfig("test"),
        )


def test_auroc_average_precision_and_precision_recall_at_k(tmp_path: Path) -> None:
    result = evaluate_visual_benchmark(
        manifest(tmp_path),
        predictions(),
        VisualBenchmarkRunConfig("test", precision_recall_k=(1, 3)),
    )
    assert result.metrics.auroc == 1.0
    assert result.metrics.average_precision == 1.0
    assert result.metrics.precision_at_k == {"1": 1.0, "3": pytest.approx(2 / 3)}
    assert result.metrics.recall_at_k == {"1": 0.5, "3": 1.0}
    assert result.metrics.selected_count == 2


def test_no_positive_and_no_negative_metric_handling(tmp_path: Path) -> None:
    normal = manifest(tmp_path, (sample("n", VisualBenchmarkLabel.NORMAL),))
    normal_result = evaluate_visual_benchmark(
        normal, [VisualBenchmarkPrediction("n", 0.1)], VisualBenchmarkRunConfig("test")
    )
    assert normal_result.metrics.auroc is None
    assert normal_result.metrics.average_precision is None
    anomaly = manifest(tmp_path, (sample("a", VisualBenchmarkLabel.ANOMALY),))
    anomaly_result = evaluate_visual_benchmark(
        anomaly, [VisualBenchmarkPrediction("a", 0.9)], VisualBenchmarkRunConfig("test")
    )
    assert anomaly_result.metrics.auroc is None
    assert anomaly_result.metrics.average_precision == 1.0
    assert anomaly_result.metrics.supervised_metrics_available is False


def test_unknown_only_uses_workload_metrics(tmp_path: Path) -> None:
    unknown = manifest(tmp_path, (sample("u", VisualBenchmarkLabel.UNKNOWN),))
    result = evaluate_visual_benchmark(
        unknown,
        [VisualBenchmarkPrediction("u", 0.5, selected=True)],
        VisualBenchmarkRunConfig("test", top_k=(1,), top_fractions=(1.0,)),
    )
    assert result.metrics.supervised_metrics_available is False
    assert result.metrics.selected_fraction == 1.0
    assert result.metrics.auroc is result.metrics.average_precision is None
    assert all(not item.supervised_metrics_available for item in result.operating_points)


def test_operating_points_and_missing_predictions(tmp_path: Path) -> None:
    result = evaluate_visual_benchmark(
        manifest(tmp_path),
        predictions()[:-1],
        VisualBenchmarkRunConfig(
            "test",
            explicit_thresholds=(0.75,),
            percentile_thresholds=(50,),
            top_k=(1,),
            top_fractions=(0.5,),
        ),
        generated_at="2026-01-01T00:00:00+00:00",
    )
    assert result.missing_prediction_ids == ("a2",)
    assert {item.strategy for item in result.operating_points} == {
        "explicit",
        "percentile",
        "top_k",
        "top_fraction",
    }
    top = next(item for item in result.operating_points if item.strategy == "top_k")
    assert top.selected_count == 1
    assert top.requires_human_review is True


def test_calibrated_score_requires_explicit_values(tmp_path: Path) -> None:
    with pytest.raises(VisualIntegrityError):
        evaluate_visual_benchmark(
            manifest(tmp_path),
            predictions(),
            VisualBenchmarkRunConfig("test", use_calibrated_score=True),
        )


def test_benchmark_artifact_publish_validate_and_corruption(tmp_path: Path) -> None:
    result = evaluate_visual_benchmark(
        manifest(tmp_path),
        predictions(),
        VisualBenchmarkRunConfig("test"),
        generated_at="2026-01-01T00:00:00+00:00",
    )
    root = publish_visual_benchmark_artifact(result, tmp_path / "results")
    assert validate_visual_benchmark_artifact(root) == result
    (root / "benchmark_result.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(VisualIntegrityError):
        validate_visual_benchmark_artifact(root)


def test_artifact_path_traversal_and_unexpected_files_rejected(tmp_path: Path) -> None:
    result = evaluate_visual_benchmark(
        manifest(tmp_path),
        predictions(),
        VisualBenchmarkRunConfig("test"),
        generated_at="2026-01-01T00:00:00+00:00",
    )
    root = publish_visual_benchmark_artifact(result, tmp_path / "results")
    manifest_path = root / "manifest.json"
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    raw["result_path"] = "../result.json"
    manifest_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ValueError):
        validate_visual_benchmark_artifact(root)


def test_prediction_result_order_is_deterministic(tmp_path: Path) -> None:
    first = evaluate_visual_benchmark(
        manifest(tmp_path),
        list(reversed(predictions())),
        VisualBenchmarkRunConfig("test"),
        generated_at="2026-01-01T00:00:00+00:00",
    )
    second = evaluate_visual_benchmark(
        manifest(tmp_path),
        list(predictions()),
        VisualBenchmarkRunConfig("test"),
        generated_at="2026-01-01T00:00:00+00:00",
    )
    assert first == second
    assert [item.sample_id for item in first.predictions] == ["a1", "a2", "n1", "n2", "u1"]


def test_default_pipeline_and_dependencies_remain_unchanged() -> None:
    from ade.visual import VisualReferenceScoringConfig

    assert VisualReferenceScoringConfig().enabled is False
    dependencies = Path("pyproject.toml").read_text(encoding="utf-8")
    assert "scikit-learn" not in dependencies and "scipy" not in dependencies

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from ade.visual import (
    VISUAL_ENGINE_SCHEMA_VERSION,
    VisualBenchmarkAcceptancePolicy,
    VisualBenchmarkDatasetManifest,
    VisualBenchmarkLabel,
    VisualBenchmarkOperatingPointRequirement,
    VisualBenchmarkRunConfig,
    VisualBenchmarkSample,
    VisualBenchmarkSplit,
    VisualEngineConfig,
    VisualIntegrityError,
    benchmark_run_config_from_policy,
    build_reference_benchmark_baseline,
    build_reference_memory_from_images,
    deserialize_visual_benchmark_acceptance_policy,
    evaluate_visual_benchmark_acceptance,
    load_visual_benchmark_acceptance_policy,
    publish_reference_benchmark_baseline,
    run_reference_benchmark,
    serialize_visual_benchmark_acceptance_policy,
    serialize_visual_benchmark_manifest,
    validate_reference_benchmark_baseline,
)


def _write_image(path: Path, value: int) -> None:
    image_module = pytest.importorskip("PIL.Image")
    path.parent.mkdir(parents=True, exist_ok=True)
    image_module.new("RGB", (8, 8), color=(value, value, value)).save(path)


def _benchmark(tmp_path: Path):
    reference_dir = tmp_path / "reference"
    _write_image(reference_dir / "normal.png", 32)
    memory = build_reference_memory_from_images(
        reference_dir=reference_dir,
        storage_root=tmp_path / "memory",
        visual_config=VisualEngineConfig(),
        patch_sizes=[4],
        patch_strides=[4],
        supported_extensions=[".png"],
    )

    benchmark_root = tmp_path / "benchmark"
    values = {
        "normal-1": 32,
        "normal-2": 36,
        "anomaly-1": 220,
        "anomaly-2": 240,
    }
    samples = []
    for sample_id, value in values.items():
        relative = f"images/{sample_id}.png"
        _write_image(benchmark_root / relative, value)
        label = (
            VisualBenchmarkLabel.ANOMALY
            if sample_id.startswith("anomaly")
            else VisualBenchmarkLabel.NORMAL
        )
        samples.append(VisualBenchmarkSample(sample_id, relative, label))
    manifest = VisualBenchmarkDatasetManifest(
        schema_version=VISUAL_ENGINE_SCHEMA_VERSION,
        dataset_name="controlled-reference-fixture",
        dataset_version="1",
        dataset_root=".",
        splits=(VisualBenchmarkSplit("test", tuple(samples)),),
    )
    manifest_path = benchmark_root / "benchmark.json"
    manifest_path.write_text(
        serialize_visual_benchmark_manifest(manifest),
        encoding="utf-8",
    )
    config_path = tmp_path / "reference.yaml"
    config_path.write_text(
        (
            "visual_engine:\n"
            "  execution_mode: reference_anomaly\n"
            "  dataset_roles: [query, reference]\n"
            "  reference_memory:\n"
            "    enabled: true\n"
            f"    manifest_path: \"{memory.manifest_path.as_posix()}\"\n"
            "  reference_scoring:\n"
            "    enabled: true\n"
            "preprocessing:\n"
            "  patch_size: 4\n"
            "  patch_stride: 4\n"
        ),
        encoding="utf-8",
    )
    return manifest_path, config_path


def test_reference_benchmark_runs_real_scoring_with_stable_sample_ids(
    tmp_path: Path,
) -> None:
    manifest_path, config_path = _benchmark(tmp_path)

    execution = run_reference_benchmark(
        manifest_path,
        config_path=config_path,
        run_config=VisualBenchmarkRunConfig(
            "test",
            precision_recall_k=(1, 2),
            top_k=(2,),
        ),
        generated_at="2026-01-01T00:00:00+00:00",
    )

    result = execution.benchmark

    assert result.metrics.scored_count == 4
    assert result.metrics.auroc == 1.0
    assert result.metrics.average_precision == 1.0
    assert result.metrics.precision_at_k == {"1": 1.0, "2": 1.0}
    assert result.metrics.recall_at_k == {"1": 0.5, "2": 1.0}
    assert not result.missing_prediction_ids
    assert {item.sample_id for item in result.predictions} == {
        "normal-1",
        "normal-2",
        "anomaly-1",
        "anomaly-2",
    }
    assert execution.reference_scoring.reference_memory_id
    assert all(
        item.score_source is not None
        and item.score_source.startswith("reference_scoring:")
        for item in result.predictions
    )


def test_acceptance_policy_checks_ranking_and_declared_operating_point(
    tmp_path: Path,
) -> None:
    manifest_path, config_path = _benchmark(tmp_path)
    execution = run_reference_benchmark(
        manifest_path,
        config_path=config_path,
        run_config=VisualBenchmarkRunConfig("test", top_k=(2,)),
        generated_at="2026-01-01T00:00:00+00:00",
    )
    result = execution.benchmark
    policy = VisualBenchmarkAcceptancePolicy(
        dataset_name="controlled-reference-fixture",
        dataset_version="1",
        split_name="test",
        min_auroc=0.9,
        min_average_precision=0.9,
        operating_points=(
            VisualBenchmarkOperatingPointRequirement(
                "top_k",
                2,
                min_precision=0.9,
                min_recall=0.9,
                max_selected_fraction=0.5,
            ),
        ),
    )

    accepted = evaluate_visual_benchmark_acceptance(result, policy)
    rejected = evaluate_visual_benchmark_acceptance(
        result,
        replace(policy, max_missing_predictions=0, operating_points=(
            replace(policy.operating_points[0], max_selected_fraction=0.25),
        )),
    )

    assert accepted.passed is True
    assert len(accepted.policy_fingerprint) == 64
    assert rejected.passed is False
    assert "above required maximum" in rejected.failures[0]


def test_acceptance_fails_closed_when_required_metric_is_unavailable(
    tmp_path: Path,
) -> None:
    manifest_path, config_path = _benchmark(tmp_path)
    execution = run_reference_benchmark(
        manifest_path,
        config_path=config_path,
        run_config=VisualBenchmarkRunConfig("test"),
    )
    result = execution.benchmark
    unavailable = replace(result, metrics=replace(result.metrics, auroc=None))

    outcome = evaluate_visual_benchmark_acceptance(
        unavailable,
        VisualBenchmarkAcceptancePolicy(
            "controlled-reference-fixture",
            "1",
            "test",
            min_auroc=0.8,
        ),
    )

    assert outcome.passed is False
    assert outcome.failures == ("AUROC is unavailable; required minimum is 0.8.",)


def test_acceptance_rejects_invalid_or_duplicate_requirements() -> None:
    duplicate = VisualBenchmarkOperatingPointRequirement("top_k", 1)
    with pytest.raises(VisualIntegrityError, match="must be unique"):
        evaluate_visual_benchmark_acceptance(
            pytest.importorskip("types").SimpleNamespace(),  # type: ignore[arg-type]
            VisualBenchmarkAcceptancePolicy(
                "fixture",
                "1",
                "test",
                operating_points=(duplicate, duplicate),
            ),
        )
    with pytest.raises(VisualIntegrityError, match="between 0 and 1"):
        evaluate_visual_benchmark_acceptance(
            pytest.importorskip("types").SimpleNamespace(),  # type: ignore[arg-type]
            VisualBenchmarkAcceptancePolicy("fixture", "1", "test", min_auroc=1.1),
        )


def _acceptance_policy(
    *,
    max_selected_fraction: float = 0.5,
) -> VisualBenchmarkAcceptancePolicy:
    return VisualBenchmarkAcceptancePolicy(
        dataset_name="controlled-reference-fixture",
        dataset_version="1",
        split_name="test",
        min_auroc=0.9,
        min_average_precision=0.9,
        operating_points=(
            VisualBenchmarkOperatingPointRequirement(
                "top_k",
                2,
                min_precision=0.9,
                min_recall=0.9,
                max_selected_fraction=max_selected_fraction,
            ),
        ),
    )


def test_acceptance_policy_round_trip_derives_required_run_config(
    tmp_path: Path,
) -> None:
    policy = _acceptance_policy()
    payload = serialize_visual_benchmark_acceptance_policy(policy)
    policy_path = tmp_path / "policy.json"
    policy_path.write_text(payload, encoding="utf-8")

    assert deserialize_visual_benchmark_acceptance_policy(payload) == policy
    assert load_visual_benchmark_acceptance_policy(policy_path) == policy
    assert benchmark_run_config_from_policy(policy) == VisualBenchmarkRunConfig(
        "test",
        top_k=(2,),
    )


def test_acceptance_policy_rejects_strategy_specific_invalid_values() -> None:
    with pytest.raises(VisualIntegrityError, match="positive integers"):
        serialize_visual_benchmark_acceptance_policy(
            VisualBenchmarkAcceptancePolicy(
                "fixture",
                "1",
                "test",
                operating_points=(
                    VisualBenchmarkOperatingPointRequirement("top_k", 1.5),
                ),
            )
        )


def test_reference_baseline_publishes_idempotent_validated_evidence(
    tmp_path: Path,
) -> None:
    manifest_path, config_path = _benchmark(tmp_path)
    policy = _acceptance_policy()
    execution = run_reference_benchmark(
        manifest_path,
        config_path=config_path,
        run_config=benchmark_run_config_from_policy(policy),
        generated_at="2026-01-01T00:00:00+00:00",
    )
    baseline = build_reference_benchmark_baseline(execution, policy)

    artifact_path = publish_reference_benchmark_baseline(
        baseline,
        tmp_path / "baselines",
    )

    assert baseline.acceptance_result.passed is True
    assert validate_reference_benchmark_baseline(artifact_path) == baseline
    assert publish_reference_benchmark_baseline(
        baseline,
        tmp_path / "baselines",
    ) == artifact_path


def test_reference_baseline_detects_content_tampering(tmp_path: Path) -> None:
    manifest_path, config_path = _benchmark(tmp_path)
    policy = _acceptance_policy()
    execution = run_reference_benchmark(
        manifest_path,
        config_path=config_path,
        run_config=benchmark_run_config_from_policy(policy),
    )
    artifact_path = publish_reference_benchmark_baseline(
        build_reference_benchmark_baseline(execution, policy),
        tmp_path / "baselines",
    )
    (artifact_path / "baseline.json").write_text("{}\n", encoding="utf-8")

    with pytest.raises(VisualIntegrityError, match="does not match its manifest"):
        validate_reference_benchmark_baseline(artifact_path)


def test_failed_acceptance_remains_publishable_evidence(tmp_path: Path) -> None:
    manifest_path, config_path = _benchmark(tmp_path)
    policy = _acceptance_policy(max_selected_fraction=0.25)
    execution = run_reference_benchmark(
        manifest_path,
        config_path=config_path,
        run_config=benchmark_run_config_from_policy(policy),
    )
    baseline = build_reference_benchmark_baseline(execution, policy)

    artifact_path = publish_reference_benchmark_baseline(
        baseline,
        tmp_path / "baselines",
    )
    validated = validate_reference_benchmark_baseline(artifact_path)

    assert validated.acceptance_result.passed is False
    assert "above required maximum" in validated.acceptance_result.failures[0]

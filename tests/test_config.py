from pathlib import Path

import pytest

from ade.config import DEFAULT_CONFIG, load_config


def test_default_config_loads_expected_sections() -> None:
    config = load_config()

    assert {
        "project",
        "preprocessing",
        "discovery",
        "reporting",
        "validation",
        "demo_data",
        "memory",
        "feedback",
        "tabular",
        "timeseries",
    }.issubset(config)
    assert config["project"]["name"] == "ADE"
    assert config["preprocessing"]["patch_size"] == 64
    assert config["preprocessing"]["patch_sizes"] == [64]
    assert config["preprocessing"]["patch_strides"] == [64]
    assert config["discovery"]["novelty_strategy"] == "hybrid"
    assert config["discovery"]["memory_aware_scoring"]["enabled"] is True
    assert config["discovery"]["diversity"]["enabled"] is True
    assert config["discovery"]["scoring_backend"] == "centroid_distance"
    assert config["discovery"]["clustering_backend"] == "threshold_candidate_grouping"
    assert config["discovery"]["top_k"] is None
    assert config["feedback"]["store_path"] == "data/feedback/feedback.jsonl"
    assert config["tabular"]["max_categorical_cardinality"] == 50
    assert config["timeseries"]["window_size"] == 3
    assert ".png" in config["validation"]["supported_image_extensions"]


def test_config_loader_uses_defaults_for_missing_optional_fields(tmp_path: Path) -> None:
    config_path = tmp_path / "partial.yaml"
    config_path.write_text(
        """
project:
  name: "Custom ADE"
discovery:
  max_candidate_anomalies: 2
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config["project"]["name"] == "Custom ADE"
    assert config["project"]["pipeline_version"] == DEFAULT_CONFIG["project"][
        "pipeline_version"
    ]
    assert config["discovery"]["max_candidate_anomalies"] == 2
    assert config["preprocessing"]["patch_size"] == 64


def test_config_loader_preserves_legacy_single_scale_settings(tmp_path: Path) -> None:
    config_path = tmp_path / "legacy.yaml"
    config_path.write_text(
        """
preprocessing:
  patch_size: 128
  patch_stride: 32
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config["preprocessing"]["patch_sizes"] == [128]
    assert config["preprocessing"]["patch_strides"] == [32]


def test_config_loader_defaults_missing_patch_strides_to_sizes(tmp_path: Path) -> None:
    config_path = tmp_path / "multiscale.yaml"
    config_path.write_text(
        """
preprocessing:
  patch_sizes:
    - 32
    - 64
""".strip(),
        encoding="utf-8",
    )

    config = load_config(config_path)

    assert config["preprocessing"]["patch_sizes"] == [32, 64]
    assert config["preprocessing"]["patch_strides"] == [32, 64]


def test_config_loader_rejects_missing_explicit_config(tmp_path: Path) -> None:
    missing_config = tmp_path / "missing.yaml"

    with pytest.raises(FileNotFoundError, match="Config file does not exist"):
        load_config(missing_config)


def test_config_loader_rejects_invalid_yaml(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid.yaml"
    config_path.write_text("project: [", encoding="utf-8")

    with pytest.raises(ValueError, match="not valid YAML"):
        load_config(config_path)


def test_config_loader_rejects_invalid_novelty_strategy(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_strategy.yaml"
    config_path.write_text(
        """
discovery:
  novelty_strategy: "unknown"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="novelty_strategy"):
        load_config(config_path)


def test_config_loader_rejects_unknown_discovery_backend(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_backend.yaml"
    config_path.write_text(
        """
discovery:
  scoring_backend: "unknown"
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="Unsupported discovery.scoring_backend"):
        load_config(config_path)


def test_config_loader_rejects_invalid_top_k(tmp_path: Path) -> None:
    config_path = tmp_path / "bad_top_k.yaml"
    config_path.write_text(
        """
discovery:
  top_k: 0
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="discovery.top_k"):
        load_config(config_path)


def test_config_loader_rejects_invalid_memory_scoring_weights(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_weights.yaml"
    config_path.write_text(
        """
discovery:
  novelty_strategy: "hybrid"
  memory_aware_scoring:
    weight_global_distance: 0
    weight_neighbor_distance: 0
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="weights"):
        load_config(config_path)


def test_config_loader_rejects_invalid_neighbor_top_k(tmp_path: Path) -> None:
    config_path = tmp_path / "invalid_top_k.yaml"
    config_path.write_text(
        """
discovery:
  memory_aware_scoring:
    neighbor_top_k: 0
""".strip(),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="neighbor_top_k"):
        load_config(config_path)

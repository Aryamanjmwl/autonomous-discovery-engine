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
    }.issubset(config)
    assert config["project"]["name"] == "ADE"
    assert config["preprocessing"]["patch_size"] == 64
    assert config["preprocessing"]["patch_sizes"] == [64]
    assert config["preprocessing"]["patch_strides"] == [64]
    assert config["discovery"]["diversity"]["enabled"] is True
    assert config["reporting"]["human_review_required"] is True
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

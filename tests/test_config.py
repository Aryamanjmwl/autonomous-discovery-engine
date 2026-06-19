from pathlib import Path

from ade.config import DEFAULT_CONFIG, load_config


def test_default_config_loads_expected_sections() -> None:
    config = load_config()

    assert {"project", "preprocessing", "discovery", "reporting", "demo_data"}.issubset(
        config
    )
    assert config["project"]["name"] == "ADE"
    assert config["preprocessing"]["patch_size"] == 64
    assert config["reporting"]["human_review_required"] is True


def test_config_loader_uses_defaults_for_missing_optional_fields() -> None:
    output_dir = Path("tests/.tmp_config_outputs")
    output_dir.mkdir(parents=True, exist_ok=True)
    config_path = output_dir / "partial.yaml"
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

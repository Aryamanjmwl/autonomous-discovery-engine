"""Configuration loading for ADE."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml


DEFAULT_CONFIG_PATH = Path("configs/default.yaml")

DEFAULT_CONFIG: dict[str, Any] = {
    "project": {
        "name": "ADE",
        "pipeline_version": "0.1.0",
    },
    "preprocessing": {
        "patch_size": 64,
        "patch_stride": 64,
    },
    "discovery": {
        "max_candidate_anomalies": 10,
        "max_concepts": 5,
        "novelty_metric": "euclidean",
        "cluster_distance_threshold": 0.35,
    },
    "reporting": {
        "report_version": "1.0",
        "human_review_required": True,
        "save_patch_previews": True,
        "assets_dir_name": "assets",
        "runs_dir_name": "runs",
    },
    "demo_data": {
        "output_dir": "data/raw/demo_images",
        "image_count": 6,
        "image_size": 256,
        "seed": 42,
    },
}


def load_config(config_path: Path | str | None = None) -> dict[str, Any]:
    """Load ADE configuration with defaults for missing optional fields."""

    path = Path(config_path) if config_path is not None else DEFAULT_CONFIG_PATH
    config = deepcopy(DEFAULT_CONFIG)
    if not path.exists():
        return config

    loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(loaded, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")

    return _deep_merge(config, loaded)


def _deep_merge(
    base: dict[str, Any],
    override: dict[str, Any],
) -> dict[str, Any]:
    """Merge nested dictionaries without mutating inputs."""

    merged = deepcopy(base)
    for key, value in override.items():
        if (
            key in merged
            and isinstance(merged[key], dict)
            and isinstance(value, dict)
        ):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged

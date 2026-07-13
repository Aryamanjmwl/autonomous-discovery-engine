"""Configuration loading for ADE."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import yaml

from ade.discovery.registry import (
    available_clustering_backends,
    available_scoring_backends,
)

DEFAULT_CONFIG_PATH = Path("configs/default.yaml")

DEFAULT_CONFIG: dict[str, Any] = {
    "project": {
        "name": "ADE",
        "pipeline_version": "0.1.0",
    },
    "preprocessing": {
        "patch_size": 64,
        "patch_stride": 64,
        "patch_sizes": [64],
        "patch_strides": [64],
    },
    "discovery": {
        "max_candidate_anomalies": 10,
        "top_k": None,
        "max_concepts": 5,
        "novelty_metric": "euclidean",
        "novelty_strategy": "hybrid",
        "scoring_backend": "centroid_distance",
        "clustering_backend": "threshold_candidate_grouping",
        "cluster_distance_threshold": 0.35,
        "random_seed": 42,
        "memory_aware_scoring": {
            "enabled": True,
            "neighbor_top_k": 5,
            "exclude_same_source": False,
            "weight_global_distance": 0.5,
            "weight_neighbor_distance": 0.5,
        },
        "diversity": {
            "enabled": True,
            "min_spatial_distance": 32,
            "max_per_image": 3,
            "prefer_multiple_scales": True,
        },
        "concepts": {
            "min_supporting_examples": 2,
            "max_supporting_examples": 5,
            "min_confidence_to_highlight": 0.5,
        },
    },
    "memory": {
        "enabled": True,
        "metric": "euclidean",
        "top_k_neighbors": 5,
        "include_neighbors_in_report": True,
    },
    "feedback": {
        "enabled": True,
        "store_path": "data/feedback/feedback.jsonl",
    },
    "review_memory": {
        "enabled": True,
        "feedback_store_path": "data/feedback/feedback.jsonl",
        "positive_labels": ["interesting", "important"],
        "negative_labels": ["false_positive", "not_useful"],
        "neutral_labels": ["known_pattern", "duplicate", "needs_more_data"],
    },
    "tabular": {
        "id_column": None,
        "max_categorical_cardinality": 50,
        "missing_value_tokens": ["", "na", "n/a", "nan", "null", "none"],
    },
    "timeseries": {
        "timestamp_column": None,
        "entity_column": None,
        "window_size": 3,
        "missing_value_tokens": ["", "na", "n/a", "nan", "null", "none"],
    },
    "reporting": {
        "report_version": "1.0",
        "human_review_required": True,
        "save_patch_previews": True,
        "assets_dir_name": "assets",
        "runs_dir_name": "runs",
    },
    "validation": {
        "supported_image_extensions": [".jpg", ".jpeg", ".png", ".bmp", ".webp"],
        "min_images": 1,
        "warn_if_images_below": 3,
        "warn_if_estimated_patches_above": 50_000,
        "min_image_width": 32,
        "min_image_height": 32,
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

    explicit_path = config_path is not None
    path = Path(config_path) if explicit_path else DEFAULT_CONFIG_PATH
    config = deepcopy(DEFAULT_CONFIG)
    if not path.exists():
        if explicit_path:
            raise FileNotFoundError(f"Config file does not exist: {path}")
        _validate_config(config)
        return config
    if not path.is_file():
        raise ValueError(f"Config path is not a file: {path}")

    try:
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except yaml.YAMLError as error:
        raise ValueError(f"Config file is not valid YAML: {path}") from error
    if not isinstance(loaded, dict):
        raise ValueError(f"Config file must contain a mapping: {path}")

    merged = _deep_merge(config, loaded)
    _normalize_preprocessing_config(merged, loaded)
    _validate_config(merged)
    return merged


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


def _normalize_preprocessing_config(
    config: dict[str, Any],
    loaded: dict[str, Any],
) -> dict[str, Any]:
    """Preserve legacy patch_size/patch_stride behavior with multi-scale defaults."""

    loaded_preprocessing = loaded.get("preprocessing")
    if not isinstance(loaded_preprocessing, dict):
        return config

    preprocessing = config["preprocessing"]
    if "patch_sizes" not in loaded_preprocessing and "patch_size" in loaded_preprocessing:
        preprocessing["patch_sizes"] = [int(preprocessing["patch_size"])]
    if "patch_strides" not in loaded_preprocessing:
        if "patch_sizes" in loaded_preprocessing:
            preprocessing["patch_strides"] = [
                int(value) for value in preprocessing["patch_sizes"]
            ]
        elif "patch_stride" in loaded_preprocessing:
            preprocessing["patch_strides"] = [int(preprocessing["patch_stride"])]
        elif "patch_sizes" not in loaded_preprocessing and "patch_size" in loaded_preprocessing:
            preprocessing["patch_strides"] = [int(preprocessing["patch_size"])]
    return config


def _validate_config(config: dict[str, Any]) -> None:
    """Validate config values with clear errors for user-editable settings."""

    discovery = config.get("discovery", {})
    if not isinstance(discovery, dict):
        raise ValueError("Config section 'discovery' must be a mapping.")

    top_k = discovery.get("top_k")
    if top_k is not None and int(top_k) <= 0:
        raise ValueError("discovery.top_k must be greater than zero.")

    max_candidates = discovery.get("max_candidate_anomalies")
    if max_candidates is not None and int(max_candidates) <= 0:
        raise ValueError("discovery.max_candidate_anomalies must be greater than zero.")

    strategy = str(discovery.get("novelty_strategy", "global_distance"))
    valid_strategies = {"global_distance", "memory_neighbor_distance", "hybrid"}
    if strategy not in valid_strategies:
        expected = ", ".join(sorted(valid_strategies))
        raise ValueError(f"discovery.novelty_strategy must be one of: {expected}")

    scoring_backend = str(discovery.get("scoring_backend", "centroid_distance"))
    if scoring_backend not in available_scoring_backends():
        supported = ", ".join(available_scoring_backends())
        raise ValueError(
            f"Unsupported discovery.scoring_backend: {scoring_backend}. "
            f"Supported backends: {supported}."
        )

    clustering_backend = str(
        discovery.get("clustering_backend", "threshold_candidate_grouping")
    )
    if clustering_backend not in available_clustering_backends():
        supported = ", ".join(available_clustering_backends())
        raise ValueError(
            f"Unsupported discovery.clustering_backend: {clustering_backend}. "
            f"Supported backends: {supported}."
        )

    scoring = discovery.get("memory_aware_scoring", {})
    if not isinstance(scoring, dict):
        raise ValueError("discovery.memory_aware_scoring must be a mapping.")
    neighbor_top_k = int(scoring.get("neighbor_top_k", 5))
    if neighbor_top_k <= 0:
        raise ValueError("discovery.memory_aware_scoring.neighbor_top_k must be positive")

    global_weight = float(scoring.get("weight_global_distance", 0.5))
    neighbor_weight = float(scoring.get("weight_neighbor_distance", 0.5))
    if global_weight < 0 or neighbor_weight < 0:
        raise ValueError("memory-aware scoring weights must be non-negative")
    if strategy == "hybrid" and global_weight + neighbor_weight == 0:
        raise ValueError("hybrid novelty scoring weights must not sum to zero")

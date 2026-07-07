from pathlib import Path

import numpy as np
import pytest

from ade.discovery.novelty_scorer import (
    DistanceToCenterScorer,
    NearestNeighborScorer,
    RobustZScoreScorer,
)
from ade.discovery.registry import create_clustering_backend, create_scoring_backend
from ade.preprocessing.patch_extractor import Patch
from ade.representation.embedding_engine import PatchEmbedding


def _embedding(values: list[float], patch_id: str) -> PatchEmbedding:
    patch = Patch(
        source_path=Path(f"{patch_id}.png"),
        array=np.zeros((2, 2, 3), dtype=np.uint8),
        x=0,
        y=0,
        width=2,
        height=2,
        patch_id=patch_id,
    )
    return PatchEmbedding(
        patch=patch,
        vector=np.array(values, dtype=np.float32),
        metadata={"feature_names": [f"feature_{index}" for index in range(len(values))]},
    )


def test_scoring_registry_returns_known_backends() -> None:
    assert isinstance(create_scoring_backend("centroid_distance"), DistanceToCenterScorer)
    assert isinstance(
        create_scoring_backend("nearest_neighbor_distance"),
        NearestNeighborScorer,
    )
    assert isinstance(create_scoring_backend("robust_z_score"), RobustZScoreScorer)


def test_registry_rejects_unknown_backend_names() -> None:
    with pytest.raises(ValueError, match="Unsupported scoring backend"):
        create_scoring_backend("missing")

    with pytest.raises(ValueError, match="Unsupported clustering backend"):
        create_clustering_backend("missing")


def test_scoring_backends_return_finite_deterministic_scores() -> None:
    embeddings = [
        _embedding([0.0, 0.0], "a"),
        _embedding([0.1, 0.0], "b"),
        _embedding([10.0, 10.0], "c"),
    ]

    first = create_scoring_backend("centroid_distance").score(embeddings)
    second = create_scoring_backend("centroid_distance").score(embeddings)

    assert [candidate.novelty_score for candidate in first] == [
        candidate.novelty_score for candidate in second
    ]
    assert all(np.isfinite(candidate.novelty_score) for candidate in first)
    assert first[0].embedding.patch.patch_id == "c"
    assert first[0].metadata["rank"] == 1
    assert first[0].metadata["scoring_backend"] == "centroid_distance"
    assert first[0].metadata["normalized_score"] == 1.0


def test_nearest_neighbor_backend_ranks_isolated_record_first() -> None:
    embeddings = [
        _embedding([0.0, 0.0], "a"),
        _embedding([0.1, 0.0], "b"),
        _embedding([8.0, 8.0], "c"),
    ]

    candidates = create_scoring_backend("nearest_neighbor_distance").score(embeddings)

    assert candidates[0].embedding.patch.patch_id == "c"
    assert candidates[0].metadata["nearest_neighbor_id"] in {"a", "b"}
    assert candidates[0].metadata["reason"].startswith("Nearest-neighbor distance")


def test_robust_backend_handles_constant_feature_columns() -> None:
    embeddings = [
        _embedding([1.0, 5.0], "a"),
        _embedding([1.0, 5.0], "b"),
        _embedding([1.0, 5.0], "c"),
    ]

    candidates = create_scoring_backend("robust_z_score").score(embeddings)

    assert len(candidates) == 3
    assert all(candidate.novelty_score == 0.0 for candidate in candidates)
    assert all(np.isfinite(candidate.novelty_score) for candidate in candidates)

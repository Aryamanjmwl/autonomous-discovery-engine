from pathlib import Path

import numpy as np
import pytest

from ade.discovery.novelty_scorer import NoveltyScorer
from ade.memory.vector_memory import VectorMemory
from ade.preprocessing.patch_extractor import Patch
from ade.representation.embedding_engine import PatchEmbedding


def _embedding(values: list[float], patch_id: str = "") -> PatchEmbedding:
    patch = Patch(
        source_path=Path("sample.png"),
        array=np.zeros((2, 2, 3), dtype=np.uint8),
        x=0,
        y=0,
        width=2,
        height=2,
        patch_id=patch_id,
    )
    return PatchEmbedding(patch=patch, vector=np.array(values, dtype=np.float32))


def test_novelty_scorer_ranks_far_embedding_first() -> None:
    embeddings = [
        _embedding([0.0, 0.0]),
        _embedding([0.1, 0.0]),
        _embedding([10.0, 10.0]),
    ]

    candidates = NoveltyScorer().score(embeddings)

    assert candidates[0].embedding.vector.tolist() == [10.0, 10.0]
    assert candidates[0].novelty_score > candidates[-1].novelty_score
    assert candidates[0].metadata["score_breakdown"]["strategy"] == "global_distance"


def test_novelty_scorer_handles_empty_input() -> None:
    assert NoveltyScorer().score([]) == []


def test_memory_neighbor_distance_scores_are_deterministic() -> None:
    embeddings = [
        _embedding([0.0, 0.0], patch_id="a"),
        _embedding([1.0, 0.0], patch_id="b"),
        _embedding([5.0, 0.0], patch_id="c"),
    ]
    memory = VectorMemory()
    for embedding in embeddings:
        memory.add(embedding.patch.patch_id, embedding.vector)

    candidates = NoveltyScorer(strategy="memory_neighbor_distance").score(
        embeddings,
        memory=memory,
    )

    assert candidates[0].embedding.patch.patch_id == "c"
    assert candidates[0].novelty_score == 1.0
    assert candidates[0].metadata["score_breakdown"]["nearest_neighbor_count"] == 2
    assert candidates[0].metadata["score_breakdown"]["strategy"] == "memory_neighbor_distance"


def test_hybrid_scoring_combines_global_and_neighbor_scores() -> None:
    embeddings = [
        _embedding([0.0, 0.0], patch_id="a"),
        _embedding([2.0, 0.0], patch_id="b"),
        _embedding([8.0, 0.0], patch_id="c"),
    ]
    memory = VectorMemory()
    for embedding in embeddings:
        memory.add(embedding.patch.patch_id, embedding.vector)

    candidates = NoveltyScorer(
        strategy="hybrid",
        weight_global_distance=0.25,
        weight_neighbor_distance=0.75,
    ).score(embeddings, memory=memory)

    breakdown = candidates[0].metadata["score_breakdown"]
    assert candidates[0].novelty_score == pytest.approx(breakdown["hybrid_score"])
    assert breakdown["strategy"] == "hybrid"
    assert 0.0 <= candidates[0].novelty_score <= 1.0


def test_normalization_handles_equal_distances_safely() -> None:
    embeddings = [
        _embedding([1.0, 1.0], patch_id="a"),
        _embedding([1.0, 1.0], patch_id="b"),
    ]

    candidates = NoveltyScorer(strategy="hybrid").score(embeddings, memory=VectorMemory())

    assert [candidate.novelty_score for candidate in candidates] == [0.0, 0.0]
    assert all(
        np.isfinite(candidate.novelty_score)
        for candidate in candidates
    )


def test_memory_strategy_falls_back_to_global_when_memory_is_empty() -> None:
    embeddings = [
        _embedding([0.0, 0.0], patch_id="a"),
        _embedding([10.0, 0.0], patch_id="b"),
    ]
    scorer = NoveltyScorer(strategy="memory_neighbor_distance")

    candidates = scorer.score(embeddings, memory=VectorMemory())

    assert scorer.last_metadata.fallback_used is True
    assert scorer.last_metadata.strategy == "global_distance"
    assert candidates[0].metadata["score_breakdown"]["strategy"] == "global_distance"


def test_novelty_scorer_rejects_invalid_strategy_and_weights() -> None:
    with pytest.raises(ValueError, match="Unsupported novelty strategy"):
        NoveltyScorer(strategy="unknown")
    with pytest.raises(ValueError, match="non-negative"):
        NoveltyScorer(weight_global_distance=-1)
    with pytest.raises(ValueError, match="must not sum to zero"):
        NoveltyScorer(
            strategy="hybrid",
            weight_global_distance=0,
            weight_neighbor_distance=0,
        )

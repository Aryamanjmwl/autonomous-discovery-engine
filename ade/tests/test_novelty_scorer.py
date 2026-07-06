from pathlib import Path

import numpy as np

from ade.discovery.novelty_scorer import NoveltyScorer
from ade.preprocessing.patch_extractor import Patch
from ade.representation.embedding_engine import PatchEmbedding


def _embedding(values: list[float]) -> PatchEmbedding:
    patch = Patch(
        source_path=Path("sample.png"),
        array=np.zeros((2, 2, 3), dtype=np.uint8),
        x=0,
        y=0,
        width=2,
        height=2,
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


def test_novelty_scorer_handles_empty_input() -> None:
    assert NoveltyScorer().score([]) == []

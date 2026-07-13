from pathlib import Path

import numpy as np

from ade.preprocessing.patch_extractor import Patch
from ade.representation.embedding_engine import EmbeddingEngine


def _patch(array: np.ndarray) -> Patch:
    return Patch(
        source_path=Path("sample.png"),
        array=array,
        x=0,
        y=0,
        width=array.shape[1],
        height=array.shape[0],
        patch_id="sample_0_0",
    )


def test_embedding_engine_emits_richer_deterministic_features() -> None:
    array = np.zeros((8, 8, 3), dtype=np.uint8)
    array[:, :4, 0] = 255
    array[4:, :, 1] = 128
    engine = EmbeddingEngine()

    first = engine.embed_patch(_patch(array))
    second = engine.embed_patch(_patch(array))

    assert first.vector.shape == second.vector.shape
    assert first.vector.size > 8
    assert np.array_equal(first.vector, second.vector)
    assert np.isfinite(first.vector).all()
    assert first.metadata["backend_name"] == "statistical_visual_v2"
    assert first.metadata["feature_count"] == first.vector.size
    assert len(first.metadata["feature_names"]) == first.vector.size


def test_embedding_engine_distinguishes_simple_visual_patterns() -> None:
    dark = np.zeros((8, 8, 3), dtype=np.uint8)
    bright = np.full((8, 8, 3), 240, dtype=np.uint8)

    engine = EmbeddingEngine()
    dark_embedding = engine.embed_patch(_patch(dark))
    bright_embedding = engine.embed_patch(_patch(bright))

    assert not np.array_equal(dark_embedding.vector, bright_embedding.vector)

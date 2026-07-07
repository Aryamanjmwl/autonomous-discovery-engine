import numpy as np
import pytest

from ade.memory.vector_memory import VectorMemory
from ade.models import NeighborResult


def test_vector_memory_queries_euclidean_neighbors_in_stable_order() -> None:
    memory = VectorMemory(metric="euclidean")
    memory.add("b", [1.0, 0.0], {"source_path": "b.png"})
    memory.add("a", [1.0, 0.0], {"source_path": "a.png"})
    memory.add("c", [3.0, 0.0], {"source_path": "c.png"})

    results = memory.query([0.0, 0.0], top_k=2)

    assert [result.item_id for result in results] == ["a", "b"]
    assert [result.rank for result in results] == [1, 2]
    assert results[0].distance == 1.0
    assert results[0].similarity == 0.5


def test_vector_memory_queries_cosine_neighbors() -> None:
    memory = VectorMemory(metric="cosine")
    memory.add("same", [1.0, 0.0])
    memory.add("orthogonal", [0.0, 1.0])

    results = memory.query(np.array([1.0, 0.0], dtype=np.float32), top_k=2)

    assert [result.item_id for result in results] == ["same", "orthogonal"]
    assert results[0].distance == 0.0
    assert results[0].similarity == 1.0


def test_vector_memory_excludes_ids_and_filters_source_paths() -> None:
    memory = VectorMemory()
    memory.add("same-source", [0.0, 0.0], {"source_path": "a.png"})
    memory.add("other-source", [0.1, 0.0], {"source_path": "b.png"})

    results = memory.query(
        [0.0, 0.0],
        top_k=5,
        exclude_ids={"same-source"},
        exclude_source_path="a.png",
    )

    assert [result.item_id for result in results] == ["other-source"]


def test_vector_memory_empty_query_returns_empty_list() -> None:
    assert VectorMemory().query([1.0, 2.0], top_k=5) == []


def test_vector_memory_rejects_invalid_metric() -> None:
    with pytest.raises(ValueError, match="Unsupported memory metric"):
        VectorMemory(metric="manhattan")


def test_neighbor_result_serialization_is_json_safe() -> None:
    result = NeighborResult(
        item_id="patch-1",
        distance=np.float32(0.25),
        similarity=np.float64(0.8),
        rank=np.int64(1),
        metadata={
            "source_path": "image.png",
            "score": np.float32(0.7),
            "flags": [np.bool_(True)],
        },
    )

    data = result.to_dict()

    assert data["item_id"] == "patch-1"
    assert data["distance"] == 0.25
    assert data["similarity"] == 0.8
    assert data["rank"] == 1
    assert data["metadata"]["source_path"] == "image.png"
    assert data["metadata"]["score"] == pytest.approx(0.7)
    assert data["metadata"]["flags"] == [True]

"""Conformance tests for the exact NumPy reference search oracle."""

from __future__ import annotations

import numpy as np
import pytest

from ade.visual import ExactNumpySearch, VisualConfigurationError, VisualIntegrityError


def _references() -> tuple[np.ndarray, tuple[str, ...]]:
    return (
        np.array([[0.0, 0.0], [1.0, 0.0], [0.0, 2.0]], dtype=np.float32),
        ("zero", "x", "y"),
    )


def test_exact_euclidean_matches_brute_force_oracle() -> None:
    references, identifiers = _references()
    queries = np.array([[0.5, 0.0], [0.0, 1.5]], dtype=np.float32)
    results = ExactNumpySearch(references, identifiers).search(queries, top_k=3)
    for query_index, result in enumerate(results):
        expected = sorted(
            range(len(references)),
            key=lambda index: (
                float(
                    np.linalg.norm(
                        queries[query_index].astype(np.float64) - references[index]
                    )
                ),
                identifiers[index],
                index,
            ),
        )
        assert [neighbor.row_index for neighbor in result.neighbors] == expected


def test_exact_cosine_matches_brute_force_oracle() -> None:
    references = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    identifiers = ("x", "y", "xy")
    query = np.array([[1.0, 0.25]], dtype=np.float32)
    result = ExactNumpySearch(references, identifiers, metric="cosine").search(
        query, top_k=3
    )[0]
    distances = [
        1.0
        - float(
            np.dot(query[0].astype(np.float64), row)
            / (np.linalg.norm(query[0]) * np.linalg.norm(row))
        )
        for row in references
    ]
    expected = sorted(
        range(3), key=lambda index: (distances[index], identifiers[index], index)
    )
    assert [neighbor.row_index for neighbor in result.neighbors] == expected


def test_equal_distances_use_vector_id_then_row_tie_breaking() -> None:
    references = np.array([[1.0], [-1.0], [1.0]], dtype=np.float32)
    result = ExactNumpySearch(references, ("z", "b", "a")).search(
        np.array([0.0], dtype=np.float32), top_k=3
    )[0]
    assert [neighbor.vector_id for neighbor in result.neighbors] == ["a", "b", "z"]
    assert [neighbor.row_index for neighbor in result.neighbors] == [2, 1, 0]


def test_batched_and_unbatched_search_are_equivalent() -> None:
    references, identifiers = _references()
    queries = np.arange(20, dtype=np.float32).reshape(10, 2) / 10.0
    batched = ExactNumpySearch(references, identifiers, query_batch_size=2).search(
        queries, top_k=10
    )
    unbatched = ExactNumpySearch(references, identifiers, query_batch_size=100).search(
        queries, top_k=10
    )
    assert batched == unbatched
    assert all(len(result.neighbors) == len(references) for result in batched)


def test_empty_query_returns_empty_and_empty_reference_is_rejected() -> None:
    references, identifiers = _references()
    search = ExactNumpySearch(references, identifiers)
    assert search.search(np.empty((0, 2), dtype=np.float32), top_k=1) == ()
    with pytest.raises(VisualIntegrityError, match="non-empty"):
        ExactNumpySearch(np.empty((0, 2), dtype=np.float32), ())


@pytest.mark.parametrize("top_k", [0, -1])
def test_search_rejects_invalid_top_k(top_k: int) -> None:
    references, identifiers = _references()
    with pytest.raises(VisualConfigurationError):
        ExactNumpySearch(references, identifiers).search(references[:1], top_k=top_k)


def test_search_rejects_dimensions_dtype_nan_and_infinity() -> None:
    references, identifiers = _references()
    search = ExactNumpySearch(references, identifiers)
    invalid = (
        np.ones((1, 3), dtype=np.float32),
        np.ones((1, 2), dtype=np.float64),
        np.array([[np.nan, 0.0]], dtype=np.float32),
        np.array([[np.inf, 0.0]], dtype=np.float32),
    )
    for query in invalid:
        with pytest.raises(VisualIntegrityError):
            search.search(query, top_k=1)


def test_search_rejects_invalid_reference_rows_and_batch_bounds() -> None:
    references, identifiers = _references()
    with pytest.raises(VisualIntegrityError):
        ExactNumpySearch(references.astype(np.float64), identifiers)
    with pytest.raises(VisualIntegrityError):
        ExactNumpySearch(references, ("duplicate", "duplicate", "other"))
    with pytest.raises(VisualConfigurationError):
        ExactNumpySearch(references, identifiers, query_batch_size=0)

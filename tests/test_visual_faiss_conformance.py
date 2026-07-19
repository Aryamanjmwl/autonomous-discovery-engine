from __future__ import annotations

import importlib
import sys
from unittest.mock import patch

import numpy as np
import pytest

from ade.visual import (
    ExactNumpySearch,
    ExactNumpySearchBackend,
    FaissBackendConfig,
    FaissSearchBackend,
    SearchBackendConfig,
    VisualIntegrityError,
    VisualProvisioningError,
    create_search_backend,
)


class FakeFaissAdapter:
    version = "fake-faiss-1"

    def __init__(self, references: np.ndarray, metric: str) -> None:
        self.references = references.astype(np.float64)
        self.metric = metric

    def search(self, queries: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        distances: list[list[float]] = []
        indices: list[list[int]] = []
        for query in queries.astype(np.float64):
            if self.metric == "euclidean":
                row = np.linalg.norm(self.references - query, axis=1)
            else:
                query_norm = np.linalg.norm(query)
                reference_norms = np.linalg.norm(self.references, axis=1)
                denominator = reference_norms * query_norm
                similarities = np.zeros(len(self.references), dtype=np.float64)
                np.divide(
                    self.references @ query,
                    denominator,
                    out=similarities,
                    where=denominator != 0,
                )
                row = 1.0 - np.clip(similarities, -1, 1)
                row[denominator == 0] = 1.0
            # Deliberately reverse row order to emulate unspecified FAISS tie order.
            order = sorted(range(len(row)), key=lambda index: (row[index], -index))[:top_k]
            distances.append([float(row[index]) for index in order])
            indices.append(order)
        return np.asarray(distances, dtype=np.float64), np.asarray(indices, dtype=np.int64)


def references() -> tuple[np.ndarray, tuple[str, ...]]:
    return (
        np.array([[1, 0], [-1, 0], [0, 1], [0, -1]], dtype=np.float32),
        ("z", "a", "m", "b"),
    )


def test_default_factory_is_exact_and_does_not_import_faiss() -> None:
    vectors, ids = references()
    before = "faiss" in sys.modules
    real_import = importlib.import_module

    def guarded(name: str, package: str | None = None):
        if name == "faiss":
            raise AssertionError("FAISS imported for default backend")
        return real_import(name, package)

    with patch("ade.visual.search_backends.importlib.import_module", side_effect=guarded):
        backend = create_search_backend(vectors, ids)
    assert isinstance(backend, ExactNumpySearchBackend)
    assert backend.metadata.backend == "exact_numpy"
    assert before == ("faiss" in sys.modules)


def test_missing_faiss_raises_structured_provisioning_error() -> None:
    vectors, ids = references()
    with (
        patch(
            "ade.visual.search_backends.importlib.import_module",
            side_effect=ImportError("missing"),
        ),
        pytest.raises(VisualProvisioningError) as captured,
    ):
        create_search_backend(vectors, ids, FaissBackendConfig())
    assert captured.value.context["backend"] == "faiss"
    assert captured.value.context["missing_package"] == "faiss-cpu"
    assert "ExactNumpySearch" in captured.value.context["default_fallback"]


@pytest.mark.parametrize("metric", ["euclidean", "cosine"])
def test_fake_faiss_matches_exact_oracle(metric: str) -> None:
    vectors, ids = references()
    queries = np.array([[0, 0], [1, 0.5]], dtype=np.float32)
    exact = ExactNumpySearch(vectors, ids, metric=metric).search(queries, top_k=4)
    faiss = FaissSearchBackend(
        vectors,
        ids,
        FaissBackendConfig(metric=metric),
        adapter=FakeFaissAdapter(vectors, metric),
    ).search(queries, top_k=4)
    for expected, actual in zip(exact, faiss, strict=True):
        assert [item.vector_id for item in actual.neighbors] == [
            item.vector_id for item in expected.neighbors
        ]
        assert [item.row_index for item in actual.neighbors] == [
            item.row_index for item in expected.neighbors
        ]
        assert [item.distance for item in actual.neighbors] == pytest.approx(
            [item.distance for item in expected.neighbors], abs=1e-6
        )


def test_top_k_clamping_and_tie_normalization() -> None:
    vectors, ids = references()
    backend = FaissSearchBackend(
        vectors,
        ids,
        FaissBackendConfig(),
        adapter=FakeFaissAdapter(vectors, "euclidean"),
    )
    result = backend.search(np.array([[0, 0]], dtype=np.float32), top_k=99)[0]
    assert [item.vector_id for item in result.neighbors] == ["a", "b", "m", "z"]
    assert len(result.neighbors) == len(vectors)


def test_faiss_query_validation_and_float32_contract() -> None:
    vectors, ids = references()
    backend = FaissSearchBackend(
        vectors,
        ids,
        FaissBackendConfig(),
        adapter=FakeFaissAdapter(vectors, "euclidean"),
    )
    invalid = (
        np.ones((1, 3), dtype=np.float32),
        np.ones((1, 2), dtype=np.float64),
        np.array([[np.nan, 0]], dtype=np.float32),
        np.array([[np.inf, 0]], dtype=np.float32),
    )
    for query in invalid:
        with pytest.raises(VisualIntegrityError):
            backend.search(query, top_k=1)


def test_faiss_provenance_is_complete_and_uncalibrated() -> None:
    vectors, ids = references()
    backend = FaissSearchBackend(
        vectors,
        ids,
        FaissBackendConfig(metric="cosine", query_batch_size=3),
        adapter=FakeFaissAdapter(vectors, "cosine"),
    )
    metadata = backend.metadata
    assert metadata.backend == "faiss"
    assert metadata.backend_version == "fake-faiss-1"
    assert metadata.metric == "cosine"
    assert metadata.dimension == 2
    assert metadata.dtype == "float32"
    assert metadata.device == "cpu"
    assert metadata.deterministic is True
    assert len(metadata.configuration_fingerprint) == 64
    assert metadata.calibrated is False


def test_faiss_config_validates_without_importing_package() -> None:
    FaissBackendConfig(metric="euclidean").validate()
    SearchBackendConfig().validate()

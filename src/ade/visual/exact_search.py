"""Exact batched NumPy similarity search for reference-memory conformance."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

import numpy as np

from ade.visual.errors import VisualConfigurationError, VisualIntegrityError
from ade.visual.reference_contracts import ReferenceNeighbor, ReferenceSearchResult


@runtime_checkable
class ReferenceSimilaritySearch(Protocol):
    """Typed search boundary that future accelerated backends must satisfy."""

    metric: str

    def search(self, queries: np.ndarray, *, top_k: int) -> tuple[ReferenceSearchResult, ...]:
        """Return deterministic nearest reference neighbors for each query row."""


class ExactNumpySearch:
    """Correctness-oracle exact search with bounded query batches."""

    def __init__(
        self,
        reference_vectors: np.ndarray,
        vector_ids: tuple[str, ...],
        *,
        metric: str = "euclidean",
        query_batch_size: int = 128,
    ) -> None:
        if metric not in {"euclidean", "cosine"}:
            raise VisualConfigurationError("Exact search metric must be euclidean or cosine")
        if query_batch_size <= 0 or query_batch_size > 65_536:
            raise VisualConfigurationError("query_batch_size must be between 1 and 65536")
        vectors = np.asarray(reference_vectors)
        if vectors.dtype != np.float32 or vectors.ndim != 2:
            raise VisualIntegrityError("Reference search vectors must be a float32 matrix")
        if vectors.shape[0] == 0 or vectors.shape[1] == 0:
            raise VisualIntegrityError("Exact search requires a non-empty reference matrix")
        if not np.all(np.isfinite(vectors)):
            raise VisualIntegrityError("Reference search vectors must be finite")
        if len(vector_ids) != vectors.shape[0] or len(set(vector_ids)) != len(vector_ids):
            raise VisualIntegrityError("Reference vector IDs must be unique and match row count")
        if any(not vector_id for vector_id in vector_ids):
            raise VisualIntegrityError("Reference vector IDs must be non-empty")
        self.reference_vectors = np.ascontiguousarray(vectors, dtype=np.float32)
        self.vector_ids = vector_ids
        self.metric = metric
        self.query_batch_size = query_batch_size
        self._reference64 = self.reference_vectors.astype(np.float64)
        self._reference_norm_squared = np.einsum(
            "ij,ij->i", self._reference64, self._reference64, dtype=np.float64
        )
        self._reference_norms = np.sqrt(self._reference_norm_squared)

    def search(
        self,
        queries: np.ndarray,
        *,
        top_k: int,
    ) -> tuple[ReferenceSearchResult, ...]:
        """Search exactly; top-k above reference count is explicitly clamped."""

        if top_k <= 0:
            raise VisualConfigurationError("top_k must be positive")
        query_array = np.asarray(queries)
        if query_array.dtype != np.float32:
            raise VisualIntegrityError("Query vectors must use float32 dtype")
        if query_array.ndim == 1:
            query_array = query_array.reshape(1, -1)
        if query_array.ndim != 2:
            raise VisualIntegrityError("Queries must be a one- or two-dimensional float32 array")
        if query_array.shape[1] != self.reference_vectors.shape[1]:
            raise VisualIntegrityError(
                "Query and reference embedding dimensions must match",
                context={
                    "query_dimension": query_array.shape[1],
                    "reference_dimension": self.reference_vectors.shape[1],
                },
            )
        if not np.all(np.isfinite(query_array)):
            raise VisualIntegrityError("Query vectors must contain only finite values")
        if query_array.shape[0] == 0:
            return ()
        limit = min(top_k, self.reference_vectors.shape[0])
        results: list[ReferenceSearchResult] = []
        for start in range(0, query_array.shape[0], self.query_batch_size):
            batch = query_array[start : start + self.query_batch_size]
            distances = self._distance_batch(batch)
            for offset, row in enumerate(distances):
                order = sorted(
                    range(len(self.vector_ids)),
                    key=lambda index: (float(row[index]), self.vector_ids[index], index),
                )[:limit]
                neighbors = tuple(
                    ReferenceNeighbor(
                        vector_id=self.vector_ids[index],
                        row_index=index,
                        distance=float(row[index]),
                    )
                    for index in order
                )
                results.append(ReferenceSearchResult(start + offset, neighbors))
        return tuple(results)

    def _distance_batch(self, queries: np.ndarray) -> np.ndarray:
        query64 = queries.astype(np.float64, copy=False)
        dots = query64 @ self._reference64.T
        if self.metric == "euclidean":
            query_norm_squared = np.einsum(
                "ij,ij->i", query64, query64, dtype=np.float64
            )
            squared = (
                query_norm_squared[:, None]
                + self._reference_norm_squared[None, :]
                - 2.0 * dots
            )
            return np.sqrt(np.maximum(squared, 0.0))
        query_norms = np.linalg.norm(query64, axis=1)
        denominators = query_norms[:, None] * self._reference_norms[None, :]
        similarities = np.zeros_like(dots, dtype=np.float64)
        np.divide(dots, denominators, out=similarities, where=denominators != 0.0)
        np.clip(similarities, -1.0, 1.0, out=similarities)
        distances = 1.0 - similarities
        distances[denominators == 0.0] = 1.0
        return distances

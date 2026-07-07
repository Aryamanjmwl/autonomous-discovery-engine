"""Small NumPy-backed vector memory for ADE retrieval."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import numpy as np

from ade.models import NeighborResult

SUPPORTED_METRICS = {"euclidean", "cosine"}


class VectorMemory:
    """Store vectors and return deterministic nearest-neighbor results.

    This class is intentionally small. It provides the local retrieval behavior
    needed by the current visual pipeline and leaves room for future normal
    memory banks, nearest-neighbor anomaly scoring, coreset selection, or a
    FAISS/vector database backend without adding those dependencies now.
    """

    def __init__(self, metric: str = "euclidean") -> None:
        if metric not in SUPPORTED_METRICS:
            supported = ", ".join(sorted(SUPPORTED_METRICS))
            raise ValueError(f"Unsupported memory metric: {metric}. Expected one of: {supported}")
        self.metric = metric
        self._items: dict[str, tuple[np.ndarray, dict[str, Any]]] = {}

    def add(
        self,
        item_id: str,
        vector: Sequence[float] | np.ndarray,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Add or replace one vector and its metadata."""

        if not item_id:
            raise ValueError("item_id must be non-empty")
        array = np.asarray(vector, dtype=np.float32).reshape(-1)
        if array.size == 0:
            raise ValueError("vector must contain at least one value")
        if not np.all(np.isfinite(array)):
            raise ValueError("vector must contain only finite values")
        self._items[item_id] = (array, dict(metadata or {}))

    def add_many(
        self,
        items: Iterable[tuple[str, Sequence[float] | np.ndarray, dict[str, Any] | None]],
    ) -> None:
        """Add multiple vectors."""

        for item_id, vector, metadata in items:
            self.add(item_id=item_id, vector=vector, metadata=metadata)

    def query(
        self,
        vector: Sequence[float] | np.ndarray,
        top_k: int = 5,
        exclude_ids: set[str] | None = None,
        include_source_path: str | None = None,
        exclude_source_path: str | None = None,
    ) -> list[NeighborResult]:
        """Return nearest neighbors sorted by distance and stable item id."""

        if top_k <= 0:
            return []
        if not self._items:
            return []

        query_vector = np.asarray(vector, dtype=np.float32).reshape(-1)
        if query_vector.size == 0:
            raise ValueError("query vector must contain at least one value")
        if not np.all(np.isfinite(query_vector)):
            raise ValueError("query vector must contain only finite values")

        excluded = exclude_ids or set()
        scored: list[tuple[float, str, dict[str, Any]]] = []
        for item_id, (stored_vector, metadata) in self._items.items():
            if item_id in excluded:
                continue
            if stored_vector.shape != query_vector.shape:
                continue
            source_path = str(metadata.get("source_path", ""))
            if include_source_path is not None and source_path != include_source_path:
                continue
            if exclude_source_path is not None and source_path == exclude_source_path:
                continue
            scored.append((self._distance(query_vector, stored_vector), item_id, metadata))

        scored.sort(key=lambda item: (item[0], item[1]))
        return [
            NeighborResult(
                item_id=item_id,
                distance=distance,
                similarity=self._similarity(distance),
                rank=index,
                metadata=metadata,
            )
            for index, (distance, item_id, metadata) in enumerate(scored[:top_k], start=1)
        ]

    def __len__(self) -> int:
        """Return the number of indexed vectors."""

        return len(self._items)

    def _distance(self, left: np.ndarray, right: np.ndarray) -> float:
        """Return configured distance between two vectors."""

        if self.metric == "euclidean":
            return float(np.linalg.norm(left - right))
        left_norm = float(np.linalg.norm(left))
        right_norm = float(np.linalg.norm(right))
        if left_norm == 0.0 or right_norm == 0.0:
            return 1.0
        cosine_similarity = float(np.dot(left, right) / (left_norm * right_norm))
        return float(1.0 - max(-1.0, min(1.0, cosine_similarity)))

    def _similarity(self, distance: float) -> float:
        """Return a bounded similarity value for report readability."""

        if self.metric == "cosine":
            return float(max(-1.0, min(1.0, 1.0 - distance)))
        return float(1.0 / (1.0 + max(distance, 0.0)))

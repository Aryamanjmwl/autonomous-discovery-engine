"""Optional search backends conforming to ADE's exact NumPy oracle."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
from dataclasses import dataclass
from typing import Any, Protocol, runtime_checkable

import numpy as np

from ade.visual.errors import (
    VisualConfigurationError,
    VisualIntegrityError,
    VisualProvisioningError,
)
from ade.visual.exact_search import ExactNumpySearch, ReferenceSimilaritySearch
from ade.visual.reference_contracts import ReferenceNeighbor, ReferenceSearchResult


@dataclass(frozen=True)
class SearchBackendConfig:
    """Strict, JSON-stable selection of an exact or optional FAISS backend."""

    backend: str = "exact_numpy"
    metric: str = "euclidean"
    query_batch_size: int = 128
    device: str = "cpu"

    def validate(self) -> None:
        if self.backend not in {"exact_numpy", "faiss"}:
            raise VisualConfigurationError("search backend must be exact_numpy or faiss")
        if self.metric not in {"euclidean", "cosine"}:
            raise VisualConfigurationError("search metric must be euclidean or cosine")
        if self.query_batch_size <= 0 or self.query_batch_size > 65_536:
            raise VisualConfigurationError("search query_batch_size must be between 1 and 65536")
        if self.device != "cpu":
            raise VisualConfigurationError(
                "Only CPU visual search backends are currently supported"
            )

    def fingerprint(self) -> str:
        self.validate()
        payload = {
            "backend": self.backend,
            "metric": self.metric,
            "query_batch_size": self.query_batch_size,
            "device": self.device,
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        ).hexdigest()


@dataclass(frozen=True)
class FaissBackendConfig(SearchBackendConfig):
    """Convenience configuration selecting the optional CPU FAISS backend."""

    backend: str = "faiss"


@dataclass(frozen=True)
class SearchBackendMetadata:
    """Portable search identity for scoring provenance."""

    backend: str
    backend_version: str
    metric: str
    dimension: int
    dtype: str
    device: str
    deterministic: bool
    configuration_fingerprint: str
    calibrated: bool = False


@runtime_checkable
class VisualSearchBackend(ReferenceSimilaritySearch, Protocol):
    @property
    def metadata(self) -> SearchBackendMetadata: ...


class ExactNumpySearchBackend:
    """Metadata adapter over the unchanged exact NumPy implementation."""

    def __init__(
        self,
        reference_vectors: np.ndarray,
        vector_ids: tuple[str, ...],
        config: SearchBackendConfig,
    ) -> None:
        config.validate()
        if config.backend != "exact_numpy":
            raise VisualConfigurationError("Exact backend requires backend=exact_numpy")
        self._search = ExactNumpySearch(
            reference_vectors,
            vector_ids,
            metric=config.metric,
            query_batch_size=config.query_batch_size,
        )
        self.metric = config.metric
        self.metadata = SearchBackendMetadata(
            "exact_numpy",
            np.__version__,
            config.metric,
            int(self._search.reference_vectors.shape[1]),
            "float32",
            "cpu",
            True,
            config.fingerprint(),
        )

    def search(self, queries: np.ndarray, *, top_k: int) -> tuple[ReferenceSearchResult, ...]:
        return self._search.search(queries, top_k=top_k)


@runtime_checkable
class FaissIndexAdapter(Protocol):
    """Injectable FAISS-like index boundary used by dependency-free tests."""

    @property
    def version(self) -> str: ...

    def search(self, queries: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]: ...


class FaissSearchBackend:
    """CPU FAISS search normalized to ExactNumpySearch result semantics."""

    def __init__(
        self,
        reference_vectors: np.ndarray,
        vector_ids: tuple[str, ...],
        config: SearchBackendConfig,
        *,
        adapter: FaissIndexAdapter | None = None,
    ) -> None:
        config.validate()
        if config.backend != "faiss":
            raise VisualConfigurationError("FAISS backend requires backend=faiss")
        vectors = np.asarray(reference_vectors)
        if vectors.dtype != np.float32 or vectors.ndim != 2:
            raise VisualIntegrityError("FAISS reference vectors must be a float32 matrix")
        if vectors.shape[0] == 0 or vectors.shape[1] == 0 or not np.all(np.isfinite(vectors)):
            raise VisualIntegrityError("FAISS reference vectors must be non-empty and finite")
        if len(vector_ids) != vectors.shape[0] or len(set(vector_ids)) != len(vector_ids):
            raise VisualIntegrityError("FAISS vector IDs must be unique and match row count")
        if any(not vector_id for vector_id in vector_ids):
            raise VisualIntegrityError("FAISS vector IDs must be non-empty")
        self.reference_vectors = np.ascontiguousarray(vectors)
        self.vector_ids = vector_ids
        self.metric = config.metric
        self.query_batch_size = config.query_batch_size
        self._adapter = adapter or _load_faiss_adapter(self.reference_vectors, config.metric)
        self.metadata = SearchBackendMetadata(
            "faiss",
            self._adapter.version,
            config.metric,
            int(vectors.shape[1]),
            "float32",
            "cpu",
            True,
            config.fingerprint(),
        )

    def search(self, queries: np.ndarray, *, top_k: int) -> tuple[ReferenceSearchResult, ...]:
        if top_k <= 0:
            raise VisualConfigurationError("top_k must be positive")
        query_array = np.asarray(queries)
        if query_array.dtype != np.float32:
            raise VisualIntegrityError("Query vectors must use float32 dtype")
        if query_array.ndim == 1:
            query_array = query_array.reshape(1, -1)
        if query_array.ndim != 2 or query_array.shape[1] != self.metadata.dimension:
            raise VisualIntegrityError("Query and FAISS reference dimensions must match")
        if not np.all(np.isfinite(query_array)):
            raise VisualIntegrityError("FAISS query vectors must be finite")
        if query_array.shape[0] == 0:
            return ()
        limit = min(top_k, len(self.vector_ids))
        results: list[ReferenceSearchResult] = []
        for start in range(0, len(query_array), self.query_batch_size):
            batch = np.ascontiguousarray(query_array[start : start + self.query_batch_size])
            distances, indices = self._adapter.search(batch, len(self.vector_ids))
            if distances.shape != indices.shape or distances.shape != (
                len(batch),
                len(self.vector_ids),
            ):
                raise VisualIntegrityError("FAISS adapter returned an invalid result shape")
            for offset, (distance_row, index_row) in enumerate(
                zip(distances, indices, strict=True)
            ):
                candidates: list[tuple[float, str, int]] = []
                for raw_distance, raw_index in zip(distance_row, index_row, strict=True):
                    index = int(raw_index)
                    distance = float(raw_distance)
                    if index < 0 or index >= len(self.vector_ids) or not np.isfinite(distance):
                        raise VisualIntegrityError("FAISS adapter returned an invalid neighbor")
                    candidates.append((distance, self.vector_ids[index], index))
                candidates.sort()
                neighbors = tuple(
                    ReferenceNeighbor(vector_id, row_index, distance)
                    for distance, vector_id, row_index in candidates[:limit]
                )
                results.append(ReferenceSearchResult(start + offset, neighbors))
        return tuple(results)


class _FaissCpuAdapter:
    def __init__(self, vectors: np.ndarray, metric: str, module: Any) -> None:
        self._metric = metric
        self._module = module
        prepared = vectors.copy()
        if metric == "cosine":
            module.normalize_L2(prepared)
            self._index = module.IndexFlatIP(prepared.shape[1])
        else:
            self._index = module.IndexFlatL2(prepared.shape[1])
        self._index.add(prepared)

    @property
    def version(self) -> str:
        try:
            return importlib.metadata.version("faiss-cpu")
        except importlib.metadata.PackageNotFoundError:
            return str(getattr(self._module, "__version__", "unknown"))

    def search(self, queries: np.ndarray, top_k: int) -> tuple[np.ndarray, np.ndarray]:
        prepared = queries.copy()
        if self._metric == "cosine":
            self._module.normalize_L2(prepared)
        raw, indices = self._index.search(prepared, top_k)
        if self._metric == "euclidean":
            raw = np.sqrt(np.maximum(raw, 0.0))
        else:
            raw = 1.0 - raw
        return raw.astype(np.float64), indices


def _load_faiss_adapter(vectors: np.ndarray, metric: str) -> FaissIndexAdapter:
    try:
        module = importlib.import_module("faiss")
    except ImportError as error:
        raise VisualProvisioningError(
            "Optional FAISS package is unavailable for the selected search backend",
            context={
                "backend": "faiss",
                "missing_package": "faiss-cpu",
                "suggested_installation": "Install faiss-cpu in an optional search environment",
                "default_fallback": "ExactNumpySearch is the default and requires no FAISS",
            },
        ) from error
    return _FaissCpuAdapter(vectors, metric, module)


def create_search_backend(
    reference_vectors: np.ndarray,
    vector_ids: tuple[str, ...],
    config: SearchBackendConfig | None = None,
) -> VisualSearchBackend:
    """Create the explicitly selected backend; exact NumPy remains the default."""

    selected = config or SearchBackendConfig()
    selected.validate()
    if selected.backend == "exact_numpy":
        return ExactNumpySearchBackend(reference_vectors, vector_ids, selected)
    return FaissSearchBackend(reference_vectors, vector_ids, selected)

"""Typed contracts for immutable visual reference memory."""

from __future__ import annotations

import json
import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ade.visual.contracts import VisualArtifactManifest
from ade.visual.errors import VisualIntegrityError

REFERENCE_MEMORY_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ReferenceVectorRecord:
    """One finite reference vector with traceable source and patch provenance."""

    vector_id: str
    source_identity: str
    vector: np.ndarray
    x: int | None = None
    y: int | None = None
    width: int | None = None
    height: int | None = None
    scale_id: str | None = None
    scale_label: str | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.vector_id.strip() or not self.source_identity.strip():
            raise VisualIntegrityError("Reference vector identity fields must be non-empty")
        array = np.asarray(self.vector)
        if array.ndim != 1 or array.size == 0:
            raise VisualIntegrityError("Reference vectors must be non-empty and one-dimensional")
        array = np.ascontiguousarray(array, dtype=np.float32)
        if not np.all(np.isfinite(array)):
            raise VisualIntegrityError("Reference vectors must contain only finite values")
        coordinates = (self.x, self.y, self.width, self.height)
        if any(value is not None for value in coordinates):
            if any(value is None for value in coordinates):
                raise VisualIntegrityError("Patch coordinates must be provided together")
            if self.x is None or self.y is None or self.width is None or self.height is None:
                raise VisualIntegrityError("Patch coordinates are incomplete")
            if self.x < 0 or self.y < 0 or self.width <= 0 or self.height <= 0:
                raise VisualIntegrityError(
                    "Patch coordinates must be non-negative with positive size"
                )
        metadata = dict(self.metadata)
        _validate_json_safe(metadata, "metadata")
        object.__setattr__(self, "vector", array)
        object.__setattr__(self, "metadata", metadata)

    def metadata_dict(self) -> dict[str, Any]:
        """Return canonical payload metadata without the vector values."""

        return {
            "vector_id": self.vector_id,
            "source_identity": self.source_identity,
            "x": self.x,
            "y": self.y,
            "width": self.width,
            "height": self.height,
            "scale_id": self.scale_id,
            "scale_label": self.scale_label,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class ReferenceMemoryManifest:
    """Immutable identity, provenance, and payload integrity for reference memory."""

    schema_version: int
    memory_id: str
    created_at: str
    reference_dataset_fingerprint: str
    configuration_fingerprint: str
    backend_id: str
    backend_version: str
    vector_count: int
    embedding_dimension: int
    dtype: str
    distance_metric: str
    coreset_strategy: str
    coreset_parameters: Mapping[str, Any]
    random_seed: int
    vector_artifact: VisualArtifactManifest
    metadata_artifact: VisualArtifactManifest
    ade_version: str
    python_version: str
    completion_state: str


@dataclass(frozen=True)
class LoadedReferenceMemory:
    """Validated loaded reference vectors, records, and immutable manifest."""

    root: Path
    manifest: ReferenceMemoryManifest
    vectors: np.ndarray
    records: tuple[ReferenceVectorRecord, ...]


@dataclass(frozen=True)
class ReferenceNeighbor:
    """One exact-search neighbor result."""

    vector_id: str
    row_index: int
    distance: float


@dataclass(frozen=True)
class ReferenceSearchResult:
    """Ordered exact neighbors for one query row."""

    query_index: int
    neighbors: tuple[ReferenceNeighbor, ...]


def validate_reference_records(records: tuple[ReferenceVectorRecord, ...]) -> int:
    """Validate unique IDs and consistent dimensions; return embedding dimension."""

    if not records:
        raise VisualIntegrityError("Reference memory requires at least one vector")
    identifiers = [record.vector_id for record in records]
    if len(set(identifiers)) != len(identifiers):
        raise VisualIntegrityError("Reference vector IDs must be unique")
    dimensions = {int(record.vector.size) for record in records}
    if len(dimensions) != 1:
        raise VisualIntegrityError("Reference vectors must have one consistent dimension")
    return dimensions.pop()


def _validate_json_safe(value: object, path: str) -> None:
    if value is None or isinstance(value, str | bool | int):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise VisualIntegrityError(f"{path} contains a non-finite number")
        return
    if isinstance(value, list | tuple):
        for index, item in enumerate(value):
            _validate_json_safe(item, f"{path}[{index}]")
        return
    if isinstance(value, Mapping):
        for key, item in value.items():
            if not isinstance(key, str):
                raise VisualIntegrityError(f"{path} keys must be strings")
            _validate_json_safe(item, f"{path}.{key}")
        return
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise VisualIntegrityError(f"{path} is not JSON-safe") from error
    raise VisualIntegrityError(f"{path} contains an unsupported metadata type")

"""Typed contracts for uncalibrated visual reference scoring."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ade.models import EmbeddingRecord
from ade.visual.contracts import VisualArtifactManifest
from ade.visual.errors import VisualIntegrityError


def _json_safe(value: object, name: str) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (TypeError, ValueError) as error:
        raise VisualIntegrityError(f"{name} must contain only finite JSON-safe values") from error


@dataclass(frozen=True)
class QueryPatchRecord:
    """One query embedding with complete spatial traceability."""

    patch_id: str
    image_id: str
    image_width: int
    image_height: int
    x: int
    y: int
    width: int
    height: int
    vector: np.ndarray
    scale_id: str = "default"
    patch_stride: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        vector = np.asarray(self.vector)
        context = {"patch_id": self.patch_id, "image_id": self.image_id}
        if not self.patch_id or not self.image_id:
            raise VisualIntegrityError(
                "Query patch and image IDs must be non-empty", context=context
            )
        if vector.dtype != np.float32 or vector.ndim != 1 or vector.size == 0:
            raise VisualIntegrityError(
                "Query patch vector must be non-empty 1D float32", context=context
            )
        if not np.all(np.isfinite(vector)):
            raise VisualIntegrityError("Query patch vector must be finite", context=context)
        values = (self.image_width, self.image_height, self.width, self.height)
        if any(
            not isinstance(value, int) or isinstance(value, bool) or value <= 0 for value in values
        ):
            raise VisualIntegrityError(
                "Image and patch dimensions must be positive integers", context=context
            )
        if (
            self.x < 0
            or self.y < 0
            or self.x + self.width > self.image_width
            or self.y + self.height > self.image_height
        ):
            raise VisualIntegrityError(
                "Query patch coordinates are outside the source image", context=context
            )
        if self.patch_stride is not None and self.patch_stride <= 0:
            raise VisualIntegrityError(
                "patch_stride must be positive when provided", context=context
            )
        if not self.scale_id:
            raise VisualIntegrityError("scale_id must be non-empty", context=context)
        _json_safe(self.metadata, "Query patch metadata")
        object.__setattr__(self, "vector", np.ascontiguousarray(vector))

    @classmethod
    def from_embedding_record(
        cls, record: EmbeddingRecord, *, image_width: int, image_height: int
    ) -> QueryPatchRecord:
        """Adapt ADE's existing patch embedding without creating a parallel representation."""

        patch = record.patch
        return cls(
            patch_id=record.patch_id or patch.patch_id,
            image_id=patch.image_id,
            image_width=image_width,
            image_height=image_height,
            x=patch.x,
            y=patch.y,
            width=patch.width,
            height=patch.height,
            vector=np.asarray(record.vector, dtype=np.float32),
            scale_id=patch.scale_id or "default",
            patch_stride=patch.patch_stride,
            metadata=dict(record.metadata),
        )


@dataclass(frozen=True)
class ReferenceEvidence:
    vector_ids: tuple[str, ...]
    row_indices: tuple[int, ...]
    distances: tuple[float, ...]


@dataclass(frozen=True)
class PatchAnomalyScore:
    patch_id: str
    image_id: str
    raw_score: float
    metric: str
    strategy: str
    aggregate_distance: float
    evidence: ReferenceEvidence
    backend_id: str
    backend_version: str
    reference_memory_id: str


@dataclass(frozen=True)
class ImageAnomalyScore:
    image_id: str
    raw_score: float
    strategy: str
    top_fraction: float
    selected_patch_ids: tuple[str, ...]
    patch_scores: tuple[PatchAnomalyScore, ...]


@dataclass(frozen=True)
class SpatialAnomalyMap:
    image_id: str
    width: int
    height: int
    raw_map: np.ndarray
    coverage_counts: np.ndarray
    coverage_fraction: float
    projection: str
    fusion: str
    smoothing_sigma: float
    uncovered_policy: str = "nan_masked"
    display_map: np.ndarray | None = None


@dataclass(frozen=True)
class ReferenceScoringProvenance:
    query_dataset_fingerprint: str
    reference_dataset_fingerprint: str
    configuration_fingerprint: str
    backend_id: str
    backend_version: str
    deterministic: bool = True
    device: str = "cpu"
    validation_dataset_fingerprint: str | None = None


@dataclass(frozen=True)
class ReferenceScoringSummary:
    scoring_id: str
    calibrated: bool
    metric: str
    patch_strategy: str
    neighbor_count: int
    image_aggregation: str
    top_fraction: float
    map_projection: str
    multi_scale_fusion: str
    smoothing_sigma: float
    query_dataset_fingerprint: str
    reference_dataset_fingerprint: str
    reference_memory_id: str
    configuration_fingerprint: str
    backend_id: str
    backend_version: str
    deterministic: bool
    device: str


@dataclass(frozen=True)
class ReferenceScoringResult:
    summary: ReferenceScoringSummary
    patch_scores: tuple[PatchAnomalyScore, ...]
    image_scores: tuple[ImageAnomalyScore, ...]
    anomaly_maps: tuple[SpatialAnomalyMap, ...]
    artifacts: tuple[VisualArtifactManifest, ...] = ()
    artifact_root: Path | None = None

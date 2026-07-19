"""PatchCore-style uncalibrated reference anomaly scoring orchestration."""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from ade.visual.config import VisualReferenceScoringConfig
from ade.visual.errors import VisualDatasetRoleError, VisualIntegrityError
from ade.visual.reference_contracts import LoadedReferenceMemory
from ade.visual.scoring_artifacts import publish_scoring_artifacts
from ade.visual.scoring_contracts import (
    ImageAnomalyScore,
    PatchAnomalyScore,
    QueryPatchRecord,
    ReferenceEvidence,
    ReferenceScoringProvenance,
    ReferenceScoringResult,
    ReferenceScoringSummary,
)
from ade.visual.search_backends import SearchBackendConfig, create_search_backend
from ade.visual.spatial_maps import build_spatial_maps


def score_reference_anomalies(
    query_records: tuple[QueryPatchRecord, ...],
    loaded_reference_memory: LoadedReferenceMemory,
    config: VisualReferenceScoringConfig,
    provenance: ReferenceScoringProvenance,
    output_directory: Path | None = None,
) -> ReferenceScoringResult:
    """Score query patches exactly and optionally publish portable map artifacts."""

    config.validate()
    _validate(query_records, loaded_reference_memory, provenance, config)
    matrix = np.ascontiguousarray(
        np.stack([record.vector for record in query_records]), dtype=np.float32
    )
    search = create_search_backend(
        loaded_reference_memory.vectors,
        tuple(record.vector_id for record in loaded_reference_memory.records),
        SearchBackendConfig(
            backend=config.search_backend,
            metric=loaded_reference_memory.manifest.distance_metric,
            query_batch_size=config.query_batch_size,
        ),
    )
    results = search.search(matrix, top_k=config.neighbor_count)
    patch_scores: list[PatchAnomalyScore] = []
    for record, search_result in zip(query_records, results, strict=True):
        distances = tuple(neighbor.distance for neighbor in search_result.neighbors)
        aggregate = (
            distances[0]
            if config.patch_strategy == "nearest_neighbor"
            else float(np.mean(np.asarray(distances, dtype=np.float64)))
        )
        patch_scores.append(
            PatchAnomalyScore(
                record.patch_id,
                record.image_id,
                aggregate,
                search.metric,
                config.patch_strategy,
                aggregate,
                ReferenceEvidence(
                    tuple(n.vector_id for n in search_result.neighbors),
                    tuple(n.row_index for n in search_result.neighbors),
                    distances,
                ),
                loaded_reference_memory.manifest.backend_id,
                loaded_reference_memory.manifest.backend_version,
                loaded_reference_memory.manifest.memory_id,
            )
        )
    patches = tuple(patch_scores)
    images = _aggregate_images(patches, config.image_aggregation, config.top_fraction)
    maps = build_spatial_maps(
        query_records,
        patches,
        projection=config.map_projection,
        fusion=config.multi_scale_fusion,
        smoothing_sigma=config.smoothing_sigma,
        maximum_image_pixels=config.maximum_image_pixels,
        display_normalization=config.display_normalization,
    )
    identity = {
        "query": provenance.query_dataset_fingerprint,
        "reference_memory": loaded_reference_memory.manifest.memory_id,
        "configuration": provenance.configuration_fingerprint,
        "patch_scores": [(p.patch_id, p.raw_score) for p in patches],
    }
    scoring_id = hashlib.sha256(
        json.dumps(identity, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    summary = ReferenceScoringSummary(
        scoring_id,
        False,
        search.metric,
        config.patch_strategy,
        min(config.neighbor_count, len(loaded_reference_memory.records)),
        config.image_aggregation,
        config.top_fraction,
        config.map_projection,
        config.multi_scale_fusion,
        config.smoothing_sigma,
        provenance.query_dataset_fingerprint,
        provenance.reference_dataset_fingerprint,
        loaded_reference_memory.manifest.memory_id,
        provenance.configuration_fingerprint,
        provenance.backend_id,
        provenance.backend_version,
        provenance.deterministic,
        provenance.device,
        search_backend=search.metadata.backend,
        search_backend_version=search.metadata.backend_version,
        search_dimension=search.metadata.dimension,
        search_dtype=search.metadata.dtype,
        search_device=search.metadata.device,
        search_deterministic=search.metadata.deterministic,
        search_configuration_fingerprint=search.metadata.configuration_fingerprint,
    )
    result = ReferenceScoringResult(summary, patches, images, maps)
    if output_directory is not None:
        artifacts, root = publish_scoring_artifacts(result, output_directory, config)
        result = ReferenceScoringResult(summary, patches, images, maps, artifacts, root)
    return result


def _validate(
    records: tuple[QueryPatchRecord, ...],
    memory: LoadedReferenceMemory,
    provenance: ReferenceScoringProvenance,
    config: VisualReferenceScoringConfig,
) -> None:
    if not records:
        raise VisualIntegrityError("Reference scoring requires at least one query patch")
    ids = [record.patch_id for record in records]
    if len(ids) != len(set(ids)):
        raise VisualIntegrityError("Query patch IDs must be unique")
    dimensions = {record.vector.size for record in records}
    if dimensions != {memory.manifest.embedding_dimension}:
        raise VisualIntegrityError(
            "Query embedding dimension is incompatible with reference memory",
            context={
                "query_dimensions": sorted(dimensions),
                "reference_dimension": memory.manifest.embedding_dimension,
            },
        )
    image_dimensions: dict[str, tuple[int, int]] = {}
    for record in records:
        prior = image_dimensions.setdefault(
            record.image_id, (record.image_width, record.image_height)
        )
        if prior != (record.image_width, record.image_height):
            raise VisualIntegrityError(
                "Source image dimensions are inconsistent", context={"image_id": record.image_id}
            )
    fingerprints = [provenance.query_dataset_fingerprint, provenance.reference_dataset_fingerprint]
    if provenance.validation_dataset_fingerprint is not None:
        fingerprints.append(provenance.validation_dataset_fingerprint)
    if len(fingerprints) != len(set(fingerprints)):
        raise VisualDatasetRoleError(
            "Query, reference, and validation fingerprints must be distinct"
        )
    manifest = memory.manifest
    mismatches = {}
    for name, expected, actual in (
        (
            "reference_fingerprint",
            provenance.reference_dataset_fingerprint,
            manifest.reference_dataset_fingerprint,
        ),
        (
            "configuration_fingerprint",
            provenance.configuration_fingerprint,
            manifest.configuration_fingerprint,
        ),
        ("backend_id", provenance.backend_id, manifest.backend_id),
        ("backend_version", provenance.backend_version, manifest.backend_version),
        ("metric", config.metric, manifest.distance_metric),
    ):
        if expected != actual:
            mismatches[name] = {"expected": expected, "actual": actual}
    if mismatches:
        raise VisualIntegrityError(
            "Scoring provenance is incompatible with reference memory", context=mismatches
        )


def _aggregate_images(
    scores: tuple[PatchAnomalyScore, ...], strategy: str, top_fraction: float
) -> tuple[ImageAnomalyScore, ...]:
    grouped: dict[str, list[PatchAnomalyScore]] = defaultdict(list)
    for score in scores:
        grouped[score.image_id].append(score)
    results = []
    for image_id in sorted(grouped):
        patches = tuple(grouped[image_id])
        ordered = sorted(patches, key=lambda item: (-item.raw_score, item.patch_id))
        count = 1 if strategy == "max_patch" else max(1, int(np.ceil(len(ordered) * top_fraction)))
        selected = ordered[:count]
        raw = (
            selected[0].raw_score
            if strategy == "max_patch"
            else float(np.mean(np.asarray([item.raw_score for item in selected], dtype=np.float64)))
        )
        results.append(
            ImageAnomalyScore(
                image_id,
                raw,
                strategy,
                top_fraction,
                tuple(item.patch_id for item in selected),
                patches,
            )
        )
    return tuple(results)

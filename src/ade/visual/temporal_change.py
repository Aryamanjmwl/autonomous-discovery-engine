"""Deterministic, local temporal visual change scoring."""

from __future__ import annotations

import hashlib
import math
from dataclasses import replace
from datetime import datetime
from pathlib import Path
from typing import TypeAlias

import numpy as np
from ade.cancellation import CancellationToken
from ade.preprocessing.patch_extractor import PatchExtractor
from ade.representation.embedding_engine import EmbeddingEngine
from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.temporal_contracts import (
    TemporalAlignmentSummary,
    TemporalChangeEvent,
    TemporalChangeProvenance,
    TemporalChangeResult,
    TemporalChangeScore,
    TemporalChangeStrategy,
    TemporalChangeSummary,
    TemporalObservation,
    TemporalObservationSequence,
    TemporalPatchEvidence,
)
from ade.visual.temporal_manifests import (
    resolve_temporal_dataset_root,
    serialize_temporal_manifest,
    validate_temporal_manifest,
)

TemporalSortKey: TypeAlias = tuple[int, datetime | int, str]


def analyze_temporal_change(
    sequence: TemporalObservationSequence,
    *,
    manifest_path: Path | None = None,
    strategy: TemporalChangeStrategy = "adjacent_difference",
    patch_size: int | None = None,
    top_k: int = 10,
    patch_top_k: int = 5,
    cancellation_token: CancellationToken | None = None,
) -> TemporalChangeResult:
    """Rank candidate changes in one explicitly ordered observation sequence."""
    from PIL import Image

    validate_temporal_manifest(sequence, manifest_path=manifest_path, strict=True)
    if strategy not in ("adjacent_difference", "baseline_difference"):
        raise ValueError("Unsupported temporal change strategy")
    if top_k <= 0 or patch_top_k <= 0 or patch_size is not None and patch_size <= 0:
        raise ValueError("top_k, patch_top_k, and patch_size must be positive")
    root = resolve_temporal_dataset_root(sequence, manifest_path)
    ordered = _ordered(sequence)
    engine = EmbeddingEngine()
    vectors: dict[str, np.ndarray] = {}
    dimensions: dict[str, tuple[int, int]] = {}
    paths: dict[str, Path] = {}
    enriched: list[TemporalObservation] = []
    for observation in ordered.observations:
        if cancellation_token is not None:
            cancellation_token.checkpoint()
        path = (root / observation.source_path).resolve()
        paths[observation.observation_id] = path
        with Image.open(path) as image:
            rgb = image.convert("RGB")
            width, height = rgb.size
            array = np.asarray(rgb, dtype=np.uint8)
        patch = PatchExtractor(patch_size=max(width, height)).extract_from_array(array, path)[0]
        vectors[observation.observation_id] = engine.embed_patch(patch).vector
        dimensions[observation.observation_id] = (width, height)
        enriched.append(replace(observation, width=width, height=height))
    ordered = replace(ordered, observations=tuple(enriched))
    if cancellation_token is not None:
        cancellation_token.checkpoint()
    pairs = _pairs(ordered.observations, strategy)
    scores = tuple(
        TemporalChangeScore(
            a.observation_id,
            b.observation_id,
            strategy,
            _distance(vectors[a.observation_id], vectors[b.observation_id]),
        )
        for a, b in pairs
    )
    events_unranked = [
        TemporalChangeEvent(
            _event_id(ordered.sequence_id, score),
            0,
            score,
            patch_evidence=_patch_evidence(
                paths[score.source_observation_id],
                paths[score.target_observation_id],
                score.source_observation_id,
                score.target_observation_id,
                patch_size,
                patch_top_k,
                engine,
                cancellation_token,
            )
            if patch_size
            else (),
        )
        for score in scores
    ]
    if cancellation_token is not None:
        cancellation_token.checkpoint()
    ranked = sorted(
        events_unranked, key=lambda item: (-item.score.global_feature_distance, item.event_id)
    )
    events = tuple(replace(item, rank=index) for index, item in enumerate(ranked[:top_k], 1))
    dimension_consistent = len(set(dimensions.values())) == 1
    warnings = [
        "No geospatial or feature registration is applied; viewpoint, lighting, and "
        "alignment changes may affect scores."
    ]
    if not dimension_consistent:
        warnings.append(
            "Observation dimensions differ; patch evidence is unavailable for mismatched grids."
        )
    adjacent_pairs = _pairs(ordered.observations, "adjacent_difference")
    adjacent = [
        _distance(vectors[a.observation_id], vectors[b.observation_id]) for a, b in adjacent_pairs
    ]
    strongest = max(
        scores, key=lambda item: (item.global_feature_distance, item.target_observation_id)
    )
    summary = TemporalChangeSummary(
        len(ordered.observations),
        _order_label(ordered.observations[0]),
        _order_label(ordered.observations[-1]),
        max(x.global_feature_distance for x in scores),
        float(np.mean(adjacent)),
        (strongest.source_observation_id, strongest.target_observation_id),
        tuple(item.event_id for item in events),
        tuple(warnings),
    )
    fingerprint = hashlib.sha256(serialize_temporal_manifest(ordered).encode()).hexdigest()
    return TemporalChangeResult(
        VISUAL_ENGINE_SCHEMA_VERSION,
        ordered,
        TemporalAlignmentSummary(
            "none",
            dimension_consistent,
            dimension_consistent and patch_size is not None,
            tuple(warnings),
        ),
        scores,
        events,
        summary,
        TemporalChangeProvenance(
            ordered.sequence_id,
            fingerprint,
            strategy,
            engine.backend_name,
            "2",
            patch_size,
            limitations=tuple(warnings),
        ),
    )


def _ordered(sequence: TemporalObservationSequence) -> TemporalObservationSequence:
    return replace(
        sequence,
        observations=tuple(sorted(sequence.observations, key=_temporal_sort_key)),
    )


def _temporal_sort_key(observation: TemporalObservation) -> TemporalSortKey:
    if observation.timestamp is not None:
        timestamp = datetime.fromisoformat(observation.timestamp.replace("Z", "+00:00"))
        return (0, timestamp, observation.observation_id)
    assert observation.sequence_index is not None
    return (1, observation.sequence_index, observation.observation_id)


def _pairs(
    items: tuple[TemporalObservation, ...], strategy: TemporalChangeStrategy
) -> list[tuple[TemporalObservation, TemporalObservation]]:
    return [
        (items[index - 1] if strategy == "adjacent_difference" else items[0], items[index])
        for index in range(1, len(items))
    ]


def _distance(first: np.ndarray, second: np.ndarray) -> float:
    return float(
        np.linalg.norm(first.astype(np.float64) - second.astype(np.float64)) / math.sqrt(first.size)
    )


def _event_id(sequence_id: str, score: TemporalChangeScore) -> str:
    value = "\0".join(
        (
            sequence_id,
            score.strategy,
            score.source_observation_id,
            score.target_observation_id,
        )
    )
    return "change-" + hashlib.sha256(value.encode()).hexdigest()[:16]


def _order_label(item: TemporalObservation) -> str:
    return item.timestamp if item.timestamp is not None else str(item.sequence_index)


def _patch_evidence(
    first: Path,
    second: Path,
    first_id: str,
    second_id: str,
    patch_size: int,
    top_k: int,
    engine: EmbeddingEngine,
    cancellation_token: CancellationToken | None,
) -> tuple[TemporalPatchEvidence, ...]:
    extractor = PatchExtractor(patch_size=patch_size)
    left, right = extractor.extract_from_path(first), extractor.extract_from_path(second)
    left_by_key = {(p.x, p.y, p.width, p.height): p for p in left}
    evidence: list[TemporalPatchEvidence] = []
    for patch in right:
        if cancellation_token is not None:
            cancellation_token.checkpoint()
        key = (patch.x, patch.y, patch.width, patch.height)
        if key not in left_by_key:
            continue
        score = _distance(
            engine.embed_patch(left_by_key[key]).vector, engine.embed_patch(patch).vector
        )
        evidence.append(TemporalPatchEvidence(first_id, second_id, *key, f"s{patch_size}", score))
    return tuple(sorted(evidence, key=lambda x: (-x.change_score, x.y, x.x))[:top_k])

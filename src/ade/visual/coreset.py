"""Deterministic bounded coreset selection for visual reference vectors."""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np

from ade.visual.errors import VisualConfigurationError, VisualIntegrityError
from ade.visual.reference_contracts import ReferenceVectorRecord, validate_reference_records


@dataclass(frozen=True)
class CoresetSelection:
    """Selected records and provenance for a deterministic coreset operation."""

    records: tuple[ReferenceVectorRecord, ...]
    source_indices: tuple[int, ...]
    parameters: dict[str, int | float | str | None]


def select_reference_coreset(
    records: tuple[ReferenceVectorRecord, ...],
    *,
    strategy: str = "none",
    maximum_vectors: int = 10_000,
    selection_ratio: float | None = None,
    seed: int = 42,
    distance_metric: str = "euclidean",
) -> CoresetSelection:
    """Select reference vectors without allocating a full pairwise distance matrix."""

    validate_reference_records(records)
    if strategy not in {"none", "deterministic_farthest_first"}:
        raise VisualConfigurationError(f"Unsupported coreset strategy: {strategy}")
    if maximum_vectors <= 0 or maximum_vectors > 10_000_000:
        raise VisualConfigurationError("maximum_vectors must be between 1 and 10000000")
    if selection_ratio is not None and not 0.0 < selection_ratio <= 1.0:
        raise VisualConfigurationError("selection_ratio must be greater than 0 and at most 1")
    if seed < 0 or seed > 2**32 - 1:
        raise VisualConfigurationError("coreset seed is outside the supported range")
    if distance_metric not in {"euclidean", "cosine"}:
        raise VisualConfigurationError("coreset distance metric must be euclidean or cosine")

    count = len(records)
    if strategy == "none":
        if count > maximum_vectors:
            raise VisualIntegrityError(
                "Reference vector count exceeds maximum_vectors with coreset strategy none",
                context={"vector_count": count, "maximum_vectors": maximum_vectors},
            )
        indices = tuple(range(count))
    else:
        ratio_count = (
            count if selection_ratio is None else max(1, math.ceil(count * selection_ratio))
        )
        requested = min(maximum_vectors, ratio_count)
        target = min(count, requested)
        indices = _farthest_first_indices(records, target, seed, distance_metric)
    selected = tuple(records[index] for index in indices)
    return CoresetSelection(
        records=selected,
        source_indices=indices,
        parameters={
            "strategy": strategy,
            "maximum_vectors": maximum_vectors,
            "selection_ratio": selection_ratio,
            "seed": seed,
            "distance_metric": distance_metric,
            "input_vector_count": count,
            "selected_vector_count": len(selected),
        },
    )


def _farthest_first_indices(
    records: tuple[ReferenceVectorRecord, ...],
    target: int,
    seed: int,
    metric: str,
) -> tuple[int, ...]:
    if target >= len(records):
        return tuple(range(len(records)))
    vectors = np.ascontiguousarray(
        np.stack([record.vector for record in records]), dtype=np.float32
    )
    first = seed % len(records)
    selected = [first]
    selected_set = {first}
    minimum_distances = _distances(vectors, vectors[first], metric)
    minimum_distances[first] = -np.inf
    while len(selected) < target:
        available = [index for index in range(len(records)) if index not in selected_set]
        next_index = min(
            available,
            key=lambda index: (
                -float(minimum_distances[index]),
                records[index].vector_id,
                index,
            ),
        )
        selected.append(next_index)
        selected_set.add(next_index)
        distances = _distances(vectors, vectors[next_index], metric)
        minimum_distances = np.minimum(minimum_distances, distances)
        for index in selected:
            minimum_distances[index] = -np.inf
    return tuple(selected)


def _distances(vectors: np.ndarray, selected: np.ndarray, metric: str) -> np.ndarray:
    left = vectors.astype(np.float64, copy=False)
    right = selected.astype(np.float64, copy=False)
    if metric == "euclidean":
        difference = left - right
        return np.sqrt(np.einsum("ij,ij->i", difference, difference, dtype=np.float64))
    left_norms = np.linalg.norm(left, axis=1)
    right_norm = float(np.linalg.norm(right))
    dots = left @ right
    denominators = left_norms * right_norm
    similarities = np.zeros(len(vectors), dtype=np.float64)
    np.divide(dots, denominators, out=similarities, where=denominators != 0.0)
    similarities = np.clip(similarities, -1.0, 1.0)
    distances = 1.0 - similarities
    distances[denominators == 0.0] = 1.0
    return distances

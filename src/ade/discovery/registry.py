"""Small discovery backend registry."""

from __future__ import annotations

from collections.abc import Callable

from ade.discovery.concept_clusterer import ConceptClusterer
from ade.discovery.novelty_scorer import (
    DistanceToCenterScorer,
    NearestNeighborScorer,
    RobustZScoreScorer,
)

ScoringFactory = Callable[[], object]
ClusteringFactory = Callable[..., object]

SCORING_BACKENDS: dict[str, ScoringFactory] = {
    DistanceToCenterScorer.name: DistanceToCenterScorer,
    "distance_to_center": DistanceToCenterScorer,
    NearestNeighborScorer.name: NearestNeighborScorer,
    RobustZScoreScorer.name: RobustZScoreScorer,
}

CLUSTERING_BACKENDS: dict[str, ClusteringFactory] = {
    ConceptClusterer.name: ConceptClusterer,
    "threshold": ConceptClusterer,
}


def available_scoring_backends() -> tuple[str, ...]:
    """Return supported scoring backend names."""

    return tuple(sorted(SCORING_BACKENDS))


def available_clustering_backends() -> tuple[str, ...]:
    """Return supported clustering backend names."""

    return tuple(sorted(CLUSTERING_BACKENDS))


def create_scoring_backend(name: str) -> object:
    """Create a scoring backend by name."""

    try:
        return SCORING_BACKENDS[name]()
    except KeyError as error:
        supported = ", ".join(available_scoring_backends())
        raise ValueError(
            f"Unsupported scoring backend: {name}. Supported backends: {supported}."
        ) from error


def create_clustering_backend(name: str, **kwargs: object) -> object:
    """Create a clustering backend by name."""

    try:
        return CLUSTERING_BACKENDS[name](**kwargs)
    except KeyError as error:
        supported = ", ".join(available_clustering_backends())
        raise ValueError(
            f"Unsupported clustering backend: {name}. Supported backends: {supported}."
        ) from error

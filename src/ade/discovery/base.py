"""Discovery backend interfaces for ADE extension points."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

EmbeddingT = TypeVar("EmbeddingT")
ScoreT = TypeVar("ScoreT")
ClusterT = TypeVar("ClusterT")
RecordT = TypeVar("RecordT")
EvidenceT = TypeVar("EvidenceT")


@runtime_checkable
class ScoringBackend(Protocol[EmbeddingT, ScoreT]):
    """Rank embeddings as candidate anomalies or candidate patterns."""

    name: str

    def score(
        self,
        embeddings: list[EmbeddingT],
        max_candidates: int | None = None,
    ) -> list[ScoreT]:
        """Return ranked candidate findings."""


@runtime_checkable
class ClusteringBackend(Protocol[EmbeddingT, ScoreT, ClusterT]):
    """Group related items into candidate concepts."""

    name: str

    def cluster(
        self,
        embeddings: list[EmbeddingT],
        scores: list[ScoreT] | None = None,
    ) -> list[ClusterT]:
        """Return candidate concept groups."""


@runtime_checkable
class EvidenceRanker(Protocol[RecordT, ScoreT, ClusterT, EmbeddingT, EvidenceT]):
    """Select or summarize evidence for reviewable findings."""

    name: str

    def rank(
        self,
        records: list[RecordT],
        scores: list[ScoreT],
        clusters: list[ClusterT] | None = None,
        embeddings: list[EmbeddingT] | None = None,
    ) -> list[EvidenceT]:
        """Return ranked or grouped evidence records."""

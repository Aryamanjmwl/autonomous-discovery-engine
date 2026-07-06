"""Discovery backend interfaces for ADE extension points."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

EmbeddingT = TypeVar("EmbeddingT")
CandidateT = TypeVar("CandidateT")
ConceptT = TypeVar("ConceptT")
EvidenceT = TypeVar("EvidenceT")


@runtime_checkable
class ScoringBackend(Protocol[EmbeddingT, CandidateT]):
    """Rank representations as candidate anomalies or candidate patterns."""

    def score(
        self,
        embeddings: list[EmbeddingT],
        max_candidates: int | None = None,
    ) -> list[CandidateT]:
        """Return ranked candidate findings."""


@runtime_checkable
class ClusteringBackend(Protocol[CandidateT, ConceptT]):
    """Group related candidate findings into candidate concepts."""

    def cluster(self, candidates: list[CandidateT]) -> list[ConceptT]:
        """Return candidate concept groups."""


@runtime_checkable
class EvidenceRanker(Protocol[ConceptT, EvidenceT]):
    """Collect or rank evidence for candidate concepts."""

    def collect(self, concepts: list[ConceptT]) -> list[EvidenceT]:
        """Return evidence summaries for candidate concepts."""

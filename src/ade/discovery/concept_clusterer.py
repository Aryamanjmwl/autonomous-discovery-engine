"""Grouping for ADE candidate unknown concepts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ade.discovery.novelty_scorer import CandidateAnomaly


@dataclass(frozen=True)
class CandidateConcept:
    """A cautious grouping of similar candidate anomalies."""

    concept_id: str
    candidates: list[CandidateAnomaly]
    centroid: np.ndarray
    consistency: float
    representative_anomaly_id: str | None = None
    average_score: float = 0.0
    item_count: int = 0
    summary: str = ""


class ConceptClusterer:
    """Group candidate anomalies with a small dependency-light algorithm."""

    name = "threshold_candidate_grouping"

    def __init__(
        self,
        distance_threshold: float = 0.35,
        max_concepts: int | None = None,
    ) -> None:
        if distance_threshold <= 0:
            raise ValueError("distance_threshold must be positive")
        if max_concepts is not None and max_concepts < 1:
            raise ValueError("max_concepts must be positive")
        self.distance_threshold = distance_threshold
        self.max_concepts = max_concepts

    def cluster(
        self,
        candidates: list[CandidateAnomaly],
        scores: list[CandidateAnomaly] | None = None,
    ) -> list[CandidateConcept]:
        """Return candidate unknown concepts grouped by embedding distance."""

        if scores is not None:
            candidates = scores

        concepts: list[CandidateConcept] = []
        for candidate in candidates:
            assigned_index = self._nearest_concept_index(candidate, concepts)
            if assigned_index is None:
                concepts.append(
                    CandidateConcept(
                        concept_id=f"concept-{len(concepts) + 1:03d}",
                        candidates=[candidate],
                        centroid=candidate.embedding.vector.copy(),
                        consistency=1.0,
                        representative_anomaly_id=candidate.anomaly_id,
                        average_score=float(candidate.novelty_score),
                        item_count=1,
                        summary="Single candidate anomaly in this concept group.",
                    )
                )
            else:
                existing = concepts[assigned_index]
                updated_candidates = [*existing.candidates, candidate]
                updated_centroid = np.vstack(
                    [item.embedding.vector for item in updated_candidates]
                ).mean(axis=0)
                concepts[assigned_index] = CandidateConcept(
                    concept_id=existing.concept_id,
                    candidates=updated_candidates,
                    centroid=updated_centroid,
                    consistency=self._consistency(updated_candidates, updated_centroid),
                    representative_anomaly_id=self._representative_id(updated_candidates),
                    average_score=self._average_score(updated_candidates),
                    item_count=len(updated_candidates),
                    summary=(
                        f"{len(updated_candidates)} candidate anomalies grouped by "
                        "similar feature vectors."
                    ),
                )
        if self.max_concepts is not None:
            return concepts[: self.max_concepts]
        return concepts

    def _nearest_concept_index(
        self,
        candidate: CandidateAnomaly,
        concepts: list[CandidateConcept],
    ) -> int | None:
        """Return the nearest concept index when it falls within threshold."""

        if not concepts:
            return None

        distances = [
            float(np.linalg.norm(candidate.embedding.vector - concept.centroid))
            for concept in concepts
        ]
        nearest_index = int(np.argmin(distances))
        if distances[nearest_index] <= self.distance_threshold:
            return nearest_index
        return None

    @staticmethod
    def _consistency(candidates: list[CandidateAnomaly], centroid: np.ndarray) -> float:
        """Estimate cluster consistency on a bounded 0 to 1 scale."""

        if len(candidates) <= 1:
            return 1.0
        distances = np.array(
            [np.linalg.norm(candidate.embedding.vector - centroid) for candidate in candidates],
            dtype=np.float32,
        )
        return float(1.0 / (1.0 + distances.mean()))

    @staticmethod
    def _representative_id(candidates: list[CandidateAnomaly]) -> str | None:
        """Return the highest-scoring candidate id for a concept."""

        if not candidates:
            return None
        representative = max(candidates, key=lambda candidate: candidate.novelty_score)
        return representative.anomaly_id

    @staticmethod
    def _average_score(candidates: list[CandidateAnomaly]) -> float:
        """Return average candidate novelty score."""

        if not candidates:
            return 0.0
        return float(sum(candidate.novelty_score for candidate in candidates) / len(candidates))

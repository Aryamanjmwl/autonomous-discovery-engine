"""Grouping for ADE candidate unknown concepts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ade.discovery.concept_scorer import ConceptScorer
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
    average_novelty: float = 0.0
    item_count: int = 0
    diversity_score: float = 0.0
    confidence_breakdown: dict[str, float] | None = None
    confidence_score: float = 0.0
    summary: str = ""


class ConceptClusterer:
    """Group candidate anomalies with a small dependency-light algorithm."""

    name = "threshold_candidate_grouping"

    def __init__(
        self,
        distance_threshold: float = 2.5,
        max_concepts: int | None = None,
        min_supporting_examples: int = 2,
        max_supporting_examples: int = 5,
    ) -> None:
        if distance_threshold <= 0:
            raise ValueError("distance_threshold must be positive")
        if max_concepts is not None and max_concepts < 1:
            raise ValueError("max_concepts must be positive")
        self.distance_threshold = distance_threshold
        self.max_concepts = max_concepts
        self.scorer = ConceptScorer(
            min_supporting_examples=min_supporting_examples,
            max_supporting_examples=max_supporting_examples,
        )

    def cluster(
        self,
        candidates: list[CandidateAnomaly],
        scores: list[CandidateAnomaly] | None = None,
    ) -> list[CandidateConcept]:
        """Return candidate unknown concepts grouped by embedding distance."""

        if scores is not None:
            candidates = scores
        if not candidates:
            return []

        normalized_vectors = self._normalized_candidate_vectors(candidates)
        concepts: list[CandidateConcept] = []
        vectors_by_id = {
            id(candidate): normalized_vectors[index]
            for index, candidate in enumerate(candidates)
        }
        for index, candidate in enumerate(candidates):
            vector = normalized_vectors[index]
            assigned_index = self._nearest_concept_index(vector, concepts)
            if assigned_index is None:
                concepts.append(
                    self._build_concept(
                        concept_id=f"concept-{len(concepts) + 1:03d}",
                        candidates=[candidate],
                        vectors_by_id=vectors_by_id,
                    )
                )
            else:
                existing = concepts[assigned_index]
                updated_candidates = [*existing.candidates, candidate]
                concepts[assigned_index] = self._build_concept(
                    concept_id=existing.concept_id,
                    candidates=updated_candidates,
                    vectors_by_id=vectors_by_id,
                )
        concepts.sort(key=lambda concept: (-concept.average_score, concept.concept_id))
        if self.max_concepts is not None:
            return concepts[: self.max_concepts]
        return concepts

    def _build_concept(
        self,
        concept_id: str,
        candidates: list[CandidateAnomaly],
        vectors_by_id: dict[int, np.ndarray],
    ) -> CandidateConcept:
        """Build a scored candidate concept."""

        centroid = np.vstack([vectors_by_id[id(item)] for item in candidates]).mean(axis=0)
        concept_score = self.scorer.score(candidates)
        average_score = self._average_score(candidates)
        return CandidateConcept(
            concept_id=concept_id,
            candidates=candidates,
            centroid=centroid,
            consistency=concept_score.consistency_score,
            representative_anomaly_id=self._representative_id(candidates),
            average_score=average_score,
            average_novelty=average_score,
            item_count=len(candidates),
            diversity_score=concept_score.diversity_score,
            confidence_breakdown=concept_score.confidence_breakdown,
            confidence_score=concept_score.confidence_score,
            summary=self._summary(candidates),
        )

    def _nearest_concept_index(
        self,
        candidate_vector: np.ndarray,
        concepts: list[CandidateConcept],
    ) -> int | None:
        """Return the nearest concept index when it falls within threshold."""

        if not concepts:
            return None

        distances = [
            float(np.linalg.norm(candidate_vector - concept.centroid))
            for concept in concepts
        ]
        nearest_index = int(np.argmin(distances))
        if distances[nearest_index] <= self.distance_threshold:
            return nearest_index
        return None

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

    @staticmethod
    def _summary(candidates: list[CandidateAnomaly]) -> str:
        """Return a cautious concept summary."""

        if len(candidates) == 1:
            return "Single candidate anomaly retained for human review."
        return (
            f"{len(candidates)} candidate anomalies grouped as a possible shared "
            "visual structure."
        )

    @staticmethod
    def _normalized_candidate_vectors(
        candidates: list[CandidateAnomaly],
    ) -> list[np.ndarray]:
        """Return finite unit-scale vectors for deterministic grouping."""

        vectors: list[np.ndarray] = []
        for candidate in candidates:
            vector = np.nan_to_num(
                candidate.embedding.vector.astype(np.float32),
                nan=0.0,
                posinf=0.0,
                neginf=0.0,
            )
            norm = float(np.linalg.norm(vector))
            if norm > 0:
                vector = vector / norm
            vectors.append(vector)
        return vectors

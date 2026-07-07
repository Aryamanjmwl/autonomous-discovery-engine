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
    average_novelty: float = 0.0
    summary: str = ""


class ConceptClusterer:
    """Group candidate anomalies with a small dependency-light algorithm."""

    def __init__(
        self,
        distance_threshold: float = 2.5,
        max_concepts: int | None = None,
    ) -> None:
        if distance_threshold <= 0:
            raise ValueError("distance_threshold must be positive")
        if max_concepts is not None and max_concepts < 1:
            raise ValueError("max_concepts must be positive")
        self.distance_threshold = distance_threshold
        self.max_concepts = max_concepts

    def cluster(self, candidates: list[CandidateAnomaly]) -> list[CandidateConcept]:
        """Return candidate unknown concepts grouped by embedding distance."""

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
        concepts.sort(key=lambda concept: (-concept.average_novelty, concept.concept_id))
        if self.max_concepts is not None:
            return concepts[: self.max_concepts]
        return concepts

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
    def _consistency(vectors: np.ndarray, centroid: np.ndarray) -> float:
        """Estimate cluster consistency on a bounded 0 to 1 scale."""

        if vectors.shape[0] <= 1:
            return 1.0
        distances = np.linalg.norm(vectors - centroid, axis=1).astype(np.float32)
        return float(1.0 / (1.0 + distances.mean()))

    @staticmethod
    def _normalized_candidate_vectors(candidates: list[CandidateAnomaly]) -> np.ndarray:
        """Return normalized candidate vectors for dependency-light clustering."""

        matrix = np.vstack(
            [candidate.embedding.vector for candidate in candidates]
        ).astype(np.float32)
        means = matrix.mean(axis=0)
        stds = matrix.std(axis=0)
        safe_stds = np.where(stds > 1e-8, stds, 1.0)
        normalized = (matrix - means) / safe_stds
        normalized[:, stds <= 1e-8] = 0.0
        return np.nan_to_num(
            normalized,
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        ).astype(np.float32)

    def _build_concept(
        self,
        concept_id: str,
        candidates: list[CandidateAnomaly],
        vectors_by_id: dict[int, np.ndarray],
    ) -> CandidateConcept:
        """Build a concept summary from candidates and normalized vectors."""

        vectors = np.vstack([vectors_by_id[id(candidate)] for candidate in candidates])
        centroid = vectors.mean(axis=0)
        representative = max(
            candidates,
            key=lambda candidate: (
                candidate.novelty_score,
                candidate.embedding.patch.patch_id,
            ),
        )
        average_novelty = sum(
            candidate.novelty_score for candidate in candidates
        ) / len(candidates)
        return CandidateConcept(
            concept_id=concept_id,
            candidates=candidates,
            centroid=centroid,
            consistency=self._consistency(vectors, centroid),
            representative_anomaly_id=representative.anomaly_id,
            average_novelty=float(average_novelty),
            summary=self._summary(candidates),
        )

    @staticmethod
    def _summary(candidates: list[CandidateAnomaly]) -> str:
        """Return a short cautious summary for a candidate concept."""

        if len(candidates) == 1:
            return "Single candidate anomaly with limited supporting evidence."
        return (
            f"{len(candidates)} candidate anomalies with similar normalized "
            "visual feature profiles."
        )

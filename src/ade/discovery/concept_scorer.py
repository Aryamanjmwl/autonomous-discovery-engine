"""Deterministic scoring helpers for candidate unknown concepts."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ade.discovery.novelty_scorer import CandidateAnomaly


@dataclass(frozen=True)
class ConceptScore:
    """Explainable scoring signals for a candidate concept."""

    consistency_score: float
    diversity_score: float
    confidence_breakdown: dict[str, float]

    @property
    def confidence_score(self) -> float:
        """Return the final review-worthiness confidence score."""

        return self.confidence_breakdown["final_confidence"]


class ConceptScorer:
    """Score candidate concepts with simple bounded review-readiness signals."""

    def __init__(
        self,
        min_supporting_examples: int = 2,
        max_supporting_examples: int = 5,
    ) -> None:
        self.min_supporting_examples = max(1, min_supporting_examples)
        self.max_supporting_examples = max(
            self.min_supporting_examples,
            max_supporting_examples,
        )

    def score(self, candidates: list[CandidateAnomaly]) -> ConceptScore:
        """Return deterministic consistency, diversity, and confidence signals."""

        if not candidates:
            return ConceptScore(
                consistency_score=0.0,
                diversity_score=0.0,
                confidence_breakdown={
                    "novelty_strength": 0.0,
                    "support_count": 0.0,
                    "consistency": 0.0,
                    "source_diversity": 0.0,
                    "data_quality": 0.0,
                    "final_confidence": 0.0,
                },
            )

        consistency = self._embedding_consistency(candidates)
        diversity = self._source_diversity(candidates)
        novelty_strength = self._novelty_strength(candidates)
        support_count = min(len(candidates) / self.max_supporting_examples, 1.0)
        data_quality = self._data_quality(candidates)
        final_confidence = _bounded(
            0.30 * novelty_strength
            + 0.20 * support_count
            + 0.25 * consistency
            + 0.15 * diversity
            + 0.10 * data_quality
        )
        return ConceptScore(
            consistency_score=consistency,
            diversity_score=diversity,
            confidence_breakdown={
                "novelty_strength": novelty_strength,
                "support_count": support_count,
                "consistency": consistency,
                "source_diversity": diversity,
                "data_quality": data_quality,
                "final_confidence": final_confidence,
            },
        )

    @staticmethod
    def _embedding_consistency(candidates: list[CandidateAnomaly]) -> float:
        """Return inverse average distance from the concept centroid."""

        if len(candidates) <= 1:
            return 1.0
        matrix = np.vstack([candidate.embedding.vector for candidate in candidates]).astype(
            np.float32
        )
        centroid = matrix.mean(axis=0)
        distances = np.linalg.norm(matrix - centroid, axis=1)
        return _bounded(1.0 / (1.0 + float(distances.mean())))

    @staticmethod
    def _source_diversity(candidates: list[CandidateAnomaly]) -> float:
        """Return a bounded signal for the number of source images represented."""

        source_count = len(
            {candidate.embedding.patch.source_path.as_posix() for candidate in candidates}
        )
        return _bounded(source_count / max(len(candidates), 1))

    @staticmethod
    def _novelty_strength(candidates: list[CandidateAnomaly]) -> float:
        """Return normalized average novelty within a concept."""

        scores = [candidate.novelty_score for candidate in candidates]
        if not scores:
            return 0.0
        scale = max(max(scores), 1.0)
        return _bounded(float(sum(scores) / len(scores)) / scale)

    @staticmethod
    def _data_quality(candidates: list[CandidateAnomaly]) -> float:
        """Return a small signal for valid patch metadata."""

        valid = 0
        for candidate in candidates:
            patch = candidate.embedding.patch
            if patch.width > 0 and patch.height > 0 and patch.array.size > 0:
                valid += 1
        return _bounded(valid / max(len(candidates), 1))


def _bounded(value: float) -> float:
    """Clamp a score to the 0..1 range."""

    if not np.isfinite(value):
        return 0.0
    return float(max(0.0, min(1.0, value)))

"""Confidence scoring for ADE candidate concepts."""

from __future__ import annotations

from dataclasses import dataclass

from ade.discovery.evidence_collector import ConceptEvidence


@dataclass(frozen=True)
class ConceptConfidence:
    """Confidence score for a candidate unknown concept."""

    concept_id: str
    score: float


class ConfidenceScorer:
    """Estimate cautious confidence from novelty, evidence count, and consistency."""

    def score(self, evidence_items: list[ConceptEvidence]) -> list[ConceptConfidence]:
        """Return bounded confidence scores for concept evidence."""

        if not evidence_items:
            return []

        max_novelty = max(item.average_novelty for item in evidence_items) or 1.0
        confidences: list[ConceptConfidence] = []
        for item in evidence_items:
            novelty_component = item.average_novelty / max_novelty
            count_component = min(item.example_count / 5.0, 1.0)
            score = 0.5 * novelty_component + 0.3 * count_component + 0.2 * item.consistency
            confidences.append(ConceptConfidence(concept_id=item.concept_id, score=float(min(score, 1.0))))
        return confidences

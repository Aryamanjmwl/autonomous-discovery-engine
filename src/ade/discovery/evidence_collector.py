"""Evidence collection for ADE candidate concepts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ade.discovery.concept_clusterer import CandidateConcept


@dataclass(frozen=True)
class EvidenceItem:
    """Traceable evidence for one supporting patch."""

    source_path: Path
    coordinates: tuple[int, int, int, int]
    novelty_score: float


@dataclass(frozen=True)
class ConceptEvidence:
    """Evidence summary for a candidate unknown concept."""

    concept_id: str
    examples: list[EvidenceItem]
    example_count: int
    average_novelty: float
    consistency: float


class EvidenceCollector:
    """Collect supporting patches and simple statistics for concepts."""

    name = "concept_evidence_collector"

    def rank(
        self,
        records: list[object],
        scores: list[object],
        clusters: list[CandidateConcept] | None = None,
        embeddings: list[object] | None = None,
    ) -> list[ConceptEvidence]:
        """Return evidence for candidate concepts.

        The current visual implementation ranks evidence after concept grouping,
        so ``clusters`` is the meaningful input. The broader signature keeps the
        backend boundary ready for future evidence rankers.
        """

        del records, scores, embeddings
        return self.collect(clusters or [])

    def collect(self, concepts: list[CandidateConcept]) -> list[ConceptEvidence]:
        """Return evidence summaries for candidate concepts."""

        evidence: list[ConceptEvidence] = []
        for concept in concepts:
            examples = [
                EvidenceItem(
                    source_path=candidate.embedding.patch.source_path,
                    coordinates=candidate.embedding.patch.coordinates,
                    novelty_score=candidate.novelty_score,
                )
                for candidate in concept.candidates
            ]
            average_novelty = (
                sum(item.novelty_score for item in examples) / len(examples)
                if examples
                else 0.0
            )
            evidence.append(
                ConceptEvidence(
                    concept_id=concept.concept_id,
                    examples=examples,
                    example_count=len(examples),
                    average_novelty=average_novelty,
                    consistency=concept.consistency,
                )
            )
        return evidence

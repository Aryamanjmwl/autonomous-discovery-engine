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
    anomaly_id: str = ""
    rank: int | None = None
    scoring_backend: str | None = None
    normalized_score: float | None = None
    concept_id: str | None = None
    nearest_neighbor_id: str | None = None
    feature_deviations: list[dict[str, float | str]] | None = None
    reason: str = ""
    preview_path: str | None = None


@dataclass(frozen=True)
class ConceptEvidence:
    """Evidence summary for a candidate unknown concept."""

    concept_id: str
    examples: list[EvidenceItem]
    example_count: int
    average_novelty: float
    consistency: float
    representative_anomaly_id: str | None = None
    item_count: int = 0
    summary: str = ""


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
                    anomaly_id=candidate.anomaly_id,
                    rank=self._int_metadata(candidate.metadata.get("rank")),
                    scoring_backend=self._str_metadata(
                        candidate.metadata.get("scoring_backend")
                    ),
                    normalized_score=self._float_metadata(
                        candidate.metadata.get("normalized_score")
                    ),
                    concept_id=concept.concept_id,
                    nearest_neighbor_id=self._str_metadata(
                        candidate.metadata.get("nearest_neighbor_id")
                    ),
                    feature_deviations=self._feature_deviations(
                        candidate.metadata.get("feature_deviations")
                    ),
                    reason=str(candidate.metadata.get("reason", "")),
                    preview_path=candidate.preview_path,
                )
                for candidate in sorted(
                    concept.candidates,
                    key=lambda item: (-item.novelty_score, item.anomaly_id),
                )
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
                    representative_anomaly_id=concept.representative_anomaly_id,
                    item_count=concept.item_count or len(examples),
                    summary=concept.summary,
                )
            )
        return evidence

    @staticmethod
    def _int_metadata(value: object) -> int | None:
        """Return integer metadata when available."""

        if isinstance(value, int):
            return value
        return None

    @staticmethod
    def _str_metadata(value: object) -> str | None:
        """Return string metadata when available."""

        if value is None:
            return None
        return str(value)

    @staticmethod
    def _float_metadata(value: object) -> float | None:
        """Return float metadata when available."""

        if isinstance(value, int | float):
            return float(value)
        return None

    @staticmethod
    def _feature_deviations(value: object) -> list[dict[str, float | str]]:
        """Return JSON-safe feature deviation metadata."""

        if not isinstance(value, list):
            return []
        deviations: list[dict[str, float | str]] = []
        for item in value:
            if not isinstance(item, dict):
                continue
            feature = item.get("feature")
            deviation = item.get("deviation")
            if feature is None or not isinstance(deviation, int | float):
                continue
            deviations.append({"feature": str(feature), "deviation": float(deviation)})
        return deviations

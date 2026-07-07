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
    nearest_neighbor_patch_id: str | None = None
    feature_deviations: list[dict[str, float | str]] | None = None
    reason: str = ""
    preview_path: str | None = None
    concept_id: str | None = None


@dataclass(frozen=True)
class ConceptEvidence:
    """Evidence summary for a candidate unknown concept."""

    concept_id: str
    examples: list[EvidenceItem]
    example_count: int
    average_novelty: float
    consistency: float
    representative_anomaly_id: str | None = None
    summary: str = ""


class EvidenceCollector:
    """Collect supporting patches and simple statistics for concepts."""

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
                    rank=self._metadata_int(candidate.metadata.get("rank")),
                    nearest_neighbor_patch_id=self._metadata_str_or_none(
                        candidate.metadata.get("nearest_neighbor_patch_id")
                    ),
                    feature_deviations=self._feature_deviations(
                        candidate.metadata.get("feature_deviations")
                    ),
                    reason=str(candidate.metadata.get("reason", "")),
                    preview_path=candidate.preview_path,
                    concept_id=concept.concept_id,
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
                    summary=concept.summary,
                )
            )
        return evidence

    @staticmethod
    def _metadata_int(value: object) -> int | None:
        """Return an integer metadata value when available."""

        if isinstance(value, int):
            return value
        return None

    @staticmethod
    def _metadata_str_or_none(value: object) -> str | None:
        """Return a string metadata value when available."""

        if value is None:
            return None
        return str(value)

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
            z_deviation = item.get("z_deviation")
            if feature is None or not isinstance(z_deviation, int | float):
                continue
            deviations.append(
                {
                    "feature": str(feature),
                    "z_deviation": float(z_deviation),
                }
            )
        return deviations

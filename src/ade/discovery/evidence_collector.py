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
    concept_id: str | None = None
    preview_path: str | None = None

    @property
    def patch_size(self) -> int:
        """Return the patch width for compact reporting."""

        return int(self.coordinates[2])

    def to_dict(self) -> dict[str, object]:
        """Return JSON-safe evidence metadata."""

        return {
            "anomaly_id": self.anomaly_id,
            "source_path": self.source_path.as_posix(),
            "x": int(self.coordinates[0]),
            "y": int(self.coordinates[1]),
            "width": int(self.coordinates[2]),
            "height": int(self.coordinates[3]),
            "patch_size": self.patch_size,
            "novelty_score": float(self.novelty_score),
            "rank": self.rank,
            "concept_id": self.concept_id,
            "preview_path": self.preview_path,
        }


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
    source_image_count: int = 0
    diversity_score: float = 0.0
    confidence_breakdown: dict[str, float] | None = None
    confidence_score: float = 0.0
    evidence_summary: dict[str, object] | None = None
    summary: str = ""


class EvidenceCollector:
    """Collect supporting patches and simple statistics for concepts."""

    def __init__(self, max_supporting_examples: int = 5) -> None:
        self.max_supporting_examples = max(1, max_supporting_examples)

    def collect(self, concepts: list[CandidateConcept]) -> list[ConceptEvidence]:
        """Return evidence summaries for candidate concepts."""

        evidence: list[ConceptEvidence] = []
        for concept in concepts:
            sorted_candidates = sorted(
                concept.candidates,
                key=lambda candidate: (-candidate.novelty_score, candidate.anomaly_id),
            )
            examples = [
                EvidenceItem(
                    source_path=candidate.embedding.patch.source_path,
                    coordinates=candidate.embedding.patch.coordinates,
                    novelty_score=candidate.novelty_score,
                    anomaly_id=candidate.anomaly_id,
                    rank=index,
                    concept_id=concept.concept_id,
                )
                for index, candidate in enumerate(sorted_candidates, start=1)
            ]
            average_novelty = (
                sum(item.novelty_score for item in examples) / len(examples)
                if examples
                else 0.0
            )
            source_image_count = len({item.source_path.as_posix() for item in examples})
            representative_examples = examples[:1]
            supporting_examples = examples[: self.max_supporting_examples]
            evidence.append(
                ConceptEvidence(
                    concept_id=concept.concept_id,
                    examples=examples,
                    example_count=len(examples),
                    average_novelty=average_novelty,
                    consistency=concept.consistency,
                    representative_anomaly_id=concept.representative_anomaly_id,
                    item_count=concept.item_count or len(examples),
                    source_image_count=source_image_count,
                    diversity_score=concept.diversity_score,
                    confidence_breakdown=concept.confidence_breakdown or {},
                    confidence_score=concept.confidence_score,
                    evidence_summary={
                        "supporting_examples": [
                            item.to_dict() for item in supporting_examples
                        ],
                        "representative_examples": [
                            item.to_dict() for item in representative_examples
                        ],
                        "near_matches": [],
                        "normal_comparisons": [],
                        "notes": [
                            "Candidate concept is based on similar anomaly embeddings.",
                            "Confidence indicates review priority, not proof of truth.",
                        ],
                        "warnings": [],
                    },
                    summary=concept.summary,
                )
            )
        return evidence

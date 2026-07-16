"""Evidence collection for ADE candidate concepts."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ade.discovery.concept_clusterer import CandidateConcept
from ade.memory.vector_memory import VectorMemory


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
    nearest_neighbor_patch_id: str | None = None
    feature_deviations: list[dict[str, float | str]] | None = None
    reason: str = ""
    preview_path: str | None = None
    patch_stride: int | None = None
    scale_id: str | None = None
    scale_label: str | None = None

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
            "patch_stride": self.patch_stride,
            "scale_id": self.scale_id,
            "scale_label": self.scale_label,
            "novelty_score": float(self.novelty_score),
            "rank": self.rank,
            "scoring_backend": self.scoring_backend,
            "normalized_score": self.normalized_score,
            "concept_id": self.concept_id,
            "nearest_neighbor_id": self.nearest_neighbor_id,
            "nearest_neighbor_patch_id": self.nearest_neighbor_patch_id,
            "feature_deviations": self.feature_deviations or [],
            "reason": self.reason,
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

    name = "concept_evidence_collector"

    def __init__(
        self,
        max_supporting_examples: int = 5,
        memory: VectorMemory | None = None,
        top_k_neighbors: int = 5,
        include_neighbors: bool = True,
    ) -> None:
        self.max_supporting_examples = max(1, max_supporting_examples)
        self.memory = memory
        self.top_k_neighbors = max(0, top_k_neighbors)
        self.include_neighbors = include_neighbors

    def rank(
        self,
        records: list[object],
        scores: list[object],
        clusters: list[CandidateConcept] | None = None,
        embeddings: list[object] | None = None,
    ) -> list[ConceptEvidence]:
        """Return evidence for candidate concepts."""

        del records, scores, embeddings
        return self.collect(clusters or [])

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
                    rank=self._int_metadata(candidate.metadata.get("rank")) or index,
                    scoring_backend=self._str_metadata(
                        candidate.metadata.get("scoring_backend")
                    ),
                    normalized_score=self._float_metadata(
                        candidate.metadata.get("normalized_score")
                    ),
                    concept_id=concept.concept_id,
                    nearest_neighbor_id=self._str_metadata(
                        candidate.metadata.get("nearest_neighbor_id")
                        or candidate.metadata.get("nearest_neighbor_patch_id")
                    ),
                    nearest_neighbor_patch_id=self._str_metadata(
                        candidate.metadata.get("nearest_neighbor_patch_id")
                        or candidate.metadata.get("nearest_neighbor_id")
                    ),
                    feature_deviations=self._feature_deviations(
                        candidate.metadata.get("feature_deviations")
                    ),
                    reason=str(candidate.metadata.get("reason", "")),
                    preview_path=candidate.preview_path,
                    patch_stride=getattr(candidate.embedding.patch, "patch_stride", None),
                    scale_id=getattr(candidate.embedding.patch, "scale_id", None),
                    scale_label=getattr(candidate.embedding.patch, "scale_label", None),
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
            nearest_neighbors = self._nearest_neighbors(
                concept=concept,
                supporting_count=len(supporting_examples),
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
                        "near_matches": nearest_neighbors,
                        "nearest_neighbors": nearest_neighbors,
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

    def _nearest_neighbors(
        self,
        concept: CandidateConcept,
        supporting_count: int,
    ) -> list[dict[str, object]]:
        """Return JSON-safe nearest-neighbor evidence for a concept."""

        if (
            self.memory is None
            or not self.include_neighbors
            or self.top_k_neighbors <= 0
            or len(self.memory) == 0
        ):
            return []

        concept_patch_ids = {
            candidate.embedding.patch.patch_id
            for candidate in concept.candidates
            if candidate.embedding.patch.patch_id
        }
        neighbor_rows: list[dict[str, object]] = []
        for candidate in concept.candidates[: max(1, supporting_count)]:
            patch_id = candidate.embedding.patch.patch_id
            neighbors = self.memory.query(
                vector=candidate.embedding.vector,
                top_k=self.top_k_neighbors,
                exclude_ids=concept_patch_ids or ({patch_id} if patch_id else set()),
            )
            for neighbor in neighbors:
                row = neighbor.to_dict()
                row["query_anomaly_id"] = candidate.anomaly_id
                row["query_patch_id"] = patch_id
                neighbor_rows.append(row)

        neighbor_rows.sort(
            key=lambda row: (
                _numeric_value(row.get("distance")),
                str(row["item_id"]),
                str(row.get("query_patch_id", "")),
            )
        )
        return neighbor_rows[: self.top_k_neighbors]

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
            deviation_key = "deviation"
            if not isinstance(deviation, int | float):
                deviation = item.get("z_deviation")
                deviation_key = "z_deviation"
            if feature is None or not isinstance(deviation, int | float):
                continue
            deviations.append({"feature": str(feature), deviation_key: float(deviation)})
        return deviations

def _numeric_value(value: object) -> float:
    """Return a sortable numeric value for JSON-like metadata."""

    return float(value) if isinstance(value, int | float) else float("inf")

"""Row-level discovery helpers for lightweight tabular ADE runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ade.representation.tabular_engine import TabularEmbeddingRecord


@dataclass(frozen=True)
class TabularFinding:
    """A row ranked as a candidate anomaly."""

    record_id: str
    row_index: int
    source_path: str
    novelty_score: float
    rank: int
    reason: str
    feature_deviations: list[dict[str, float | str]]
    missing_columns: list[str]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe candidate anomaly record."""

        return {
            "anomaly_id": self.record_id,
            "record_id": self.record_id,
            "row_index": int(self.row_index),
            "source_path": self.source_path,
            "novelty_score": float(self.novelty_score),
            "rank": int(self.rank),
            "reason": self.reason,
            "feature_deviations": list(self.feature_deviations),
            "missing_columns": list(self.missing_columns),
            "preview_path": None,
            "label": "candidate tabular row anomaly",
            "requires_human_review": True,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class TabularConcept:
    """A cautious grouping of similar row-level findings."""

    concept_id: str
    findings: list[TabularFinding]
    summary: str
    average_novelty: float
    confidence_score: float

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe candidate concept record."""

        representative = self.findings[0] if self.findings else None
        return {
            "concept_id": self.concept_id,
            "label": "candidate tabular concept",
            "example_count": len(self.findings),
            "average_novelty": float(self.average_novelty),
            "cluster_consistency": 1.0 / (1.0 + _score_std(self.findings)),
            "representative_anomaly_id": representative.record_id if representative else None,
            "item_count": len(self.findings),
            "summary": self.summary,
            "confidence_score": float(self.confidence_score),
            "possible_pattern": (
                "Rows in this group may share a candidate tabular pattern. "
                "This hypothesis requires human review."
            ),
            "examples": [finding.to_dict() for finding in self.findings],
            "requires_human_review": True,
        }


class TabularNoveltyScorer:
    """Score tabular rows by distance from the dataset feature center."""

    name = "tabular_centroid_distance"

    def score(
        self,
        embeddings: list[TabularEmbeddingRecord],
        max_candidates: int | None = None,
    ) -> list[TabularFinding]:
        """Return stable row-level candidate anomalies."""

        if not embeddings:
            return []
        matrix = np.vstack([embedding.vector for embedding in embeddings]).astype(np.float32)
        matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
        centroid = matrix.mean(axis=0)
        scores = np.linalg.norm(matrix - centroid, axis=1).astype(np.float32)
        scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
        findings = [
            self._finding(
                embedding=embedding,
                score=float(score),
                centroid=centroid,
                source_index=index,
            )
            for index, (embedding, score) in enumerate(zip(embeddings, scores, strict=True))
        ]
        findings.sort(key=lambda item: (-item.novelty_score, item.row_index, item.record_id))
        ranked = [
            TabularFinding(
                record_id=finding.record_id,
                row_index=finding.row_index,
                source_path=finding.source_path,
                novelty_score=finding.novelty_score,
                rank=rank,
                reason=finding.reason,
                feature_deviations=finding.feature_deviations,
                missing_columns=finding.missing_columns,
                metadata={**finding.metadata, "rank": rank},
            )
            for rank, finding in enumerate(findings, start=1)
        ]
        return ranked[:max_candidates] if max_candidates is not None else ranked

    def _finding(
        self,
        embedding: TabularEmbeddingRecord,
        score: float,
        centroid: np.ndarray,
        source_index: int,
    ) -> TabularFinding:
        """Build one row finding."""

        deviations = _feature_deviations(embedding, centroid)
        missing_columns = [
            str(column) for column in embedding.metadata.get("missing_columns", [])
        ]
        return TabularFinding(
            record_id=embedding.record.record_id,
            row_index=embedding.record.row_index,
            source_path=embedding.record.source_path.as_posix(),
            novelty_score=score,
            rank=0,
            reason=_reason(deviations, missing_columns),
            feature_deviations=deviations,
            missing_columns=missing_columns,
            metadata={
                "scoring_backend": self.name,
                "source_index": source_index,
                "completeness_ratio": embedding.metadata.get("completeness_ratio"),
            },
        )


class TabularConceptGrouper:
    """Group tabular findings into small reason-based candidate concepts."""

    name = "tabular_reason_grouping"

    def __init__(self, max_concepts: int = 5) -> None:
        self.max_concepts = max(1, max_concepts)

    def group(self, findings: list[TabularFinding]) -> list[TabularConcept]:
        """Return cautious concept groups for row-level findings."""

        groups: dict[str, list[TabularFinding]] = {}
        for finding in findings:
            groups.setdefault(_group_key(finding), []).append(finding)

        concepts: list[TabularConcept] = []
        for index, (key, items) in enumerate(groups.items(), start=1):
            if index > self.max_concepts:
                break
            average = sum(item.novelty_score for item in items) / len(items)
            concepts.append(
                TabularConcept(
                    concept_id=f"tabular-concept-{index:03d}",
                    findings=items,
                    summary=_concept_summary(key, items),
                    average_novelty=float(average),
                    confidence_score=_confidence(items),
                )
            )
        return concepts


def _feature_deviations(
    embedding: TabularEmbeddingRecord,
    centroid: np.ndarray,
    limit: int = 5,
) -> list[dict[str, float | str]]:
    """Return the largest feature deviations from the tabular center."""

    deltas = embedding.vector.astype(np.float32) - centroid.astype(np.float32)
    indexes = np.argsort(np.abs(deltas))[::-1][:limit]
    return [
        {
            "feature": embedding.feature_names[int(index)],
            "deviation": float(deltas[int(index)]),
        }
        for index in indexes
    ]


def _reason(
    deviations: list[dict[str, float | str]],
    missing_columns: list[str],
) -> str:
    """Return a conservative reason string for a tabular finding."""

    if missing_columns:
        return "Several fields are missing compared with the dataset baseline."
    if any("categorical_rarity" in str(item["feature"]) for item in deviations[:2]):
        return "Categorical values are uncommon in this dataset."
    return "Row has numeric values farther from the dataset center than most rows."


def _group_key(finding: TabularFinding) -> str:
    """Return a compact reason key for grouping findings."""

    if finding.missing_columns:
        return "missing_values"
    if any("categorical_rarity" in str(item["feature"]) for item in finding.feature_deviations[:2]):
        return "categorical_rarity"
    return "numeric_deviation"


def _concept_summary(key: str, findings: list[TabularFinding]) -> str:
    """Return a short factual concept summary."""

    if key == "missing_values":
        return f"{len(findings)} candidate rows grouped by missing-value signals."
    if key == "categorical_rarity":
        return f"{len(findings)} candidate rows grouped by uncommon categorical values."
    return f"{len(findings)} candidate rows grouped by numeric deviation signals."


def _confidence(findings: list[TabularFinding]) -> float:
    """Return a simple bounded confidence signal for a tabular concept."""

    if not findings:
        return 0.0
    example_factor = min(1.0, len(findings) / 5.0)
    score_factor = min(1.0, sum(item.novelty_score for item in findings) / len(findings))
    consistency = 1.0 / (1.0 + _score_std(findings))
    return float(max(0.0, min(1.0, 0.4 * score_factor + 0.3 * example_factor + 0.3 * consistency)))


def _score_std(findings: list[TabularFinding]) -> float:
    """Return standard deviation of finding scores."""

    if len(findings) <= 1:
        return 0.0
    return float(np.std([finding.novelty_score for finding in findings]))

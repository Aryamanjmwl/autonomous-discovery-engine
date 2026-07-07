"""Point-level discovery helpers for lightweight time-series ADE runs."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from ade.representation.timeseries_engine import TimeSeriesEmbeddingRecord


@dataclass(frozen=True)
class TimeSeriesFinding:
    """A timestamped point ranked as a candidate anomaly."""

    record_id: str
    row_index: int
    timestamp: str
    source_path: str
    novelty_score: float
    rank: int
    reason: str
    feature_deviations: list[dict[str, float | str]]
    signal_deltas: dict[str, float]
    spike_signals: list[str]
    missing_signals: list[str]
    gap_seconds: float
    time_gap_indicator: float
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe candidate anomaly record."""

        return {
            "anomaly_id": self.record_id,
            "record_id": self.record_id,
            "row_index": int(self.row_index),
            "timestamp": self.timestamp,
            "source_path": self.source_path,
            "novelty_score": float(self.novelty_score),
            "rank": int(self.rank),
            "reason": self.reason,
            "feature_deviations": list(self.feature_deviations),
            "signal_deltas": dict(self.signal_deltas),
            "spike_signals": list(self.spike_signals),
            "missing_signals": list(self.missing_signals),
            "gap_seconds": float(self.gap_seconds),
            "time_gap_indicator": float(self.time_gap_indicator),
            "preview_path": None,
            "label": "candidate time-series point anomaly",
            "requires_human_review": True,
            "metadata": dict(self.metadata),
        }


@dataclass(frozen=True)
class TimeSeriesConcept:
    """A cautious grouping of related time-series findings."""

    concept_id: str
    findings: list[TimeSeriesFinding]
    summary: str
    average_novelty: float
    confidence_score: float

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe candidate concept record."""

        representative = self.findings[0] if self.findings else None
        return {
            "concept_id": self.concept_id,
            "label": "candidate time-series concept",
            "example_count": len(self.findings),
            "average_novelty": float(self.average_novelty),
            "cluster_consistency": 1.0 / (1.0 + _score_std(self.findings)),
            "representative_anomaly_id": representative.record_id if representative else None,
            "item_count": len(self.findings),
            "summary": self.summary,
            "confidence_score": float(self.confidence_score),
            "possible_pattern": (
                "Points in this group may share a candidate time-series pattern. "
                "This hypothesis requires human review."
            ),
            "examples": [finding.to_dict() for finding in self.findings],
            "requires_human_review": True,
        }


class TimeSeriesNoveltyScorer:
    """Score time-series points by distance from the feature center."""

    name = "timeseries_centroid_distance"

    def score(
        self,
        embeddings: list[TimeSeriesEmbeddingRecord],
        max_candidates: int | None = None,
    ) -> list[TimeSeriesFinding]:
        """Return stable point-level candidate anomalies."""

        if not embeddings:
            return []
        matrix = np.vstack([embedding.vector for embedding in embeddings]).astype(np.float32)
        matrix = np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)
        centroid = matrix.mean(axis=0)
        scores = np.linalg.norm(matrix - centroid, axis=1).astype(np.float32)
        scores = np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0)
        findings = [
            self._finding(embedding, float(score), centroid, index)
            for index, (embedding, score) in enumerate(zip(embeddings, scores, strict=True))
        ]
        findings.sort(key=lambda item: (-item.novelty_score, item.timestamp, item.row_index))
        ranked = [
            TimeSeriesFinding(
                record_id=finding.record_id,
                row_index=finding.row_index,
                timestamp=finding.timestamp,
                source_path=finding.source_path,
                novelty_score=finding.novelty_score,
                rank=rank,
                reason=finding.reason,
                feature_deviations=finding.feature_deviations,
                signal_deltas=finding.signal_deltas,
                spike_signals=finding.spike_signals,
                missing_signals=finding.missing_signals,
                gap_seconds=finding.gap_seconds,
                time_gap_indicator=finding.time_gap_indicator,
                metadata={**finding.metadata, "rank": rank},
            )
            for rank, finding in enumerate(findings, start=1)
        ]
        return ranked[:max_candidates] if max_candidates is not None else ranked

    def _finding(
        self,
        embedding: TimeSeriesEmbeddingRecord,
        score: float,
        centroid: np.ndarray,
        source_index: int,
    ) -> TimeSeriesFinding:
        """Build one time-series finding."""

        deviations = _feature_deviations(embedding, centroid)
        spike_signals = [str(item) for item in embedding.metadata.get("spike_signals", [])]
        missing_signals = [str(item) for item in embedding.metadata.get("missing_signals", [])]
        signal_deltas = {
            str(key): float(value)
            for key, value in dict(embedding.metadata.get("signal_deltas", {})).items()
        }
        gap_seconds = float(embedding.metadata.get("gap_seconds", 0.0))
        time_gap_indicator = float(embedding.metadata.get("time_gap_indicator", 0.0))
        return TimeSeriesFinding(
            record_id=embedding.record.record_id,
            row_index=embedding.record.row_index,
            timestamp=embedding.record.timestamp,
            source_path=embedding.record.source_path.as_posix(),
            novelty_score=score,
            rank=0,
            reason=_reason(spike_signals, missing_signals, time_gap_indicator),
            feature_deviations=deviations,
            signal_deltas=signal_deltas,
            spike_signals=spike_signals,
            missing_signals=missing_signals,
            gap_seconds=gap_seconds,
            time_gap_indicator=time_gap_indicator,
            metadata={
                "scoring_backend": self.name,
                "source_index": source_index,
                "entity_id": embedding.record.entity_id,
                "completeness_ratio": embedding.metadata.get("completeness_ratio"),
            },
        )


class TimeSeriesConceptGrouper:
    """Group time-series findings into small reason-based candidate concepts."""

    name = "timeseries_reason_grouping"

    def __init__(self, max_concepts: int = 5) -> None:
        self.max_concepts = max(1, max_concepts)

    def group(self, findings: list[TimeSeriesFinding]) -> list[TimeSeriesConcept]:
        """Return cautious concept groups for time-series findings."""

        groups: dict[str, list[TimeSeriesFinding]] = {}
        for finding in findings:
            groups.setdefault(_group_key(finding), []).append(finding)
        concepts: list[TimeSeriesConcept] = []
        for index, (key, items) in enumerate(groups.items(), start=1):
            if index > self.max_concepts:
                break
            average = sum(item.novelty_score for item in items) / len(items)
            concepts.append(
                TimeSeriesConcept(
                    concept_id=f"timeseries-concept-{index:03d}",
                    findings=items,
                    summary=_concept_summary(key, items),
                    average_novelty=float(average),
                    confidence_score=_confidence(items),
                )
            )
        return concepts


def _feature_deviations(
    embedding: TimeSeriesEmbeddingRecord,
    centroid: np.ndarray,
    limit: int = 5,
) -> list[dict[str, float | str]]:
    """Return the largest feature deviations from the time-series center."""

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
    spike_signals: list[str],
    missing_signals: list[str],
    time_gap_indicator: float,
) -> str:
    """Return a conservative reason string."""

    if time_gap_indicator > 0:
        return "Timestamp gap is larger than the dataset baseline."
    if spike_signals:
        return "Signal value changed more sharply than nearby points."
    if missing_signals:
        return "One or more signal values are missing at this timestamp."
    return "Window-level feature profile is farther from the dataset center than most windows."


def _group_key(finding: TimeSeriesFinding) -> str:
    """Return a compact reason key for grouping findings."""

    if finding.time_gap_indicator > 0:
        return "time_gap"
    if finding.spike_signals:
        return "signal_change"
    if finding.missing_signals:
        return "missing_signal"
    return "feature_profile"


def _concept_summary(key: str, findings: list[TimeSeriesFinding]) -> str:
    """Return a short factual concept summary."""

    if key == "time_gap":
        return f"{len(findings)} candidate points grouped by timestamp gap signals."
    if key == "signal_change":
        return f"{len(findings)} candidate points grouped by sharp signal changes."
    if key == "missing_signal":
        return f"{len(findings)} candidate points grouped by missing signal values."
    return f"{len(findings)} candidate points grouped by time-series feature profile."


def _confidence(findings: list[TimeSeriesFinding]) -> float:
    """Return a simple bounded confidence signal."""

    if not findings:
        return 0.0
    example_factor = min(1.0, len(findings) / 5.0)
    score_factor = min(1.0, sum(item.novelty_score for item in findings) / len(findings))
    consistency = 1.0 / (1.0 + _score_std(findings))
    return float(max(0.0, min(1.0, 0.4 * score_factor + 0.3 * example_factor + 0.3 * consistency)))


def _score_std(findings: list[TimeSeriesFinding]) -> float:
    """Return standard deviation of finding scores."""

    if len(findings) <= 1:
        return 0.0
    return float(np.std([finding.novelty_score for finding in findings]))

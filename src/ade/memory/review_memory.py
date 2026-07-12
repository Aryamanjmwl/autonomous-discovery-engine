"""Review-memory helpers for local feedback-informed ranking signals."""

from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any, Iterable

from ade.feedback.models import ReviewFeedback

DEFAULT_POSITIVE_LABELS = frozenset({"interesting", "important"})
DEFAULT_NEGATIVE_LABELS = frozenset({"false_positive", "not_useful"})
DEFAULT_NEUTRAL_LABELS = frozenset({"known_pattern", "duplicate", "needs_more_data"})


@dataclass(frozen=True)
class ReviewMemorySignal:
    """Transparent review-memory signal for one candidate target."""

    priority_delta: float
    matched_feedback_count: int
    positive_feedback_count: int
    negative_feedback_count: int
    known_pattern_count: int
    duplicate_count: int
    needs_more_data_count: int
    notes: list[str] = field(default_factory=list)
    explanation: str = "No prior feedback matched this candidate target."

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe signal representation."""

        return {
            "priority_delta": float(self.priority_delta),
            "matched_feedback_count": int(self.matched_feedback_count),
            "positive_feedback_count": int(self.positive_feedback_count),
            "negative_feedback_count": int(self.negative_feedback_count),
            "known_pattern_count": int(self.known_pattern_count),
            "duplicate_count": int(self.duplicate_count),
            "needs_more_data_count": int(self.needs_more_data_count),
            "notes": list(self.notes),
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class ReviewMemorySummary:
    """Aggregated local review feedback used for ranking hints."""

    total_feedback_count: int
    label_counts: dict[str, int]
    label_counts_by_target_type: dict[str, dict[str, int]]
    target_counts: dict[str, dict[str, dict[str, int]]]
    positive_labels: list[str]
    negative_labels: list[str]
    neutral_labels: list[str]

    @property
    def has_feedback(self) -> bool:
        """Return whether any feedback was available."""

        return self.total_feedback_count > 0

    def to_dict(self) -> dict[str, object]:
        """Return a JSON-safe summary representation."""

        return {
            "total_feedback_count": int(self.total_feedback_count),
            "label_counts": dict(sorted(self.label_counts.items())),
            "label_counts_by_target_type": {
                target_type: dict(sorted(counts.items()))
                for target_type, counts in sorted(self.label_counts_by_target_type.items())
            },
            "positive_labels": list(self.positive_labels),
            "negative_labels": list(self.negative_labels),
            "neutral_labels": list(self.neutral_labels),
            "explanation": (
                "Review-memory signals summarize local human-review feedback as "
                "ranking hints. They do not establish automated truth."
            ),
        }

    def counts_for(self, target_type: str, target_id: str) -> dict[str, int]:
        """Return label counts for one target."""

        return dict(self.target_counts.get(target_type, {}).get(target_id, {}))


def build_review_memory_summary(
    feedback_records: Iterable[ReviewFeedback],
    *,
    positive_labels: Iterable[str] = DEFAULT_POSITIVE_LABELS,
    negative_labels: Iterable[str] = DEFAULT_NEGATIVE_LABELS,
    neutral_labels: Iterable[str] = DEFAULT_NEUTRAL_LABELS,
) -> ReviewMemorySummary:
    """Build deterministic review-memory counts from local feedback records."""

    positive = sorted({str(label) for label in positive_labels})
    negative = sorted({str(label) for label in negative_labels})
    neutral = sorted({str(label) for label in neutral_labels})

    label_counts: Counter[str] = Counter()
    label_counts_by_type: dict[str, Counter[str]] = defaultdict(Counter)
    target_counts: dict[str, dict[str, Counter[str]]] = defaultdict(
        lambda: defaultdict(Counter)
    )

    total = 0
    for record in feedback_records:
        total += 1
        label = str(record.label)
        target_type = str(record.target_type)
        target_id = str(record.target_id)
        label_counts[label] += 1
        label_counts_by_type[target_type][label] += 1
        target_counts[target_type][target_id][label] += 1

    return ReviewMemorySummary(
        total_feedback_count=total,
        label_counts=dict(label_counts),
        label_counts_by_target_type={
            target_type: dict(counts) for target_type, counts in label_counts_by_type.items()
        },
        target_counts={
            target_type: {
                target_id: dict(counts)
                for target_id, counts in sorted(targets.items())
            }
            for target_type, targets in sorted(target_counts.items())
        },
        positive_labels=positive,
        negative_labels=negative,
        neutral_labels=neutral,
    )


def score_candidate_with_review_memory(
    candidate: object,
    target_type: str,
    memory_summary: ReviewMemorySummary,
) -> ReviewMemorySignal:
    """Return a transparent ranking signal for one candidate target."""

    target_id = _candidate_target_id(candidate, target_type)
    if not target_id:
        return ReviewMemorySignal(
            priority_delta=0.0,
            matched_feedback_count=0,
            positive_feedback_count=0,
            negative_feedback_count=0,
            known_pattern_count=0,
            duplicate_count=0,
            needs_more_data_count=0,
            explanation="No stable target identifier was available for review-memory matching.",
        )

    counts = memory_summary.counts_for(target_type, target_id)
    positive_count = sum(counts.get(label, 0) for label in memory_summary.positive_labels)
    negative_count = sum(counts.get(label, 0) for label in memory_summary.negative_labels)
    known_count = counts.get("known_pattern", 0)
    duplicate_count = counts.get("duplicate", 0)
    needs_more_data_count = counts.get("needs_more_data", 0)
    matched_count = sum(counts.values())
    priority_delta = (
        float(positive_count)
        - float(negative_count)
        + (0.25 * float(needs_more_data_count))
        - (0.25 * float(known_count))
        - (0.5 * float(duplicate_count))
    )

    notes = _signal_notes(
        positive_count=positive_count,
        negative_count=negative_count,
        known_count=known_count,
        duplicate_count=duplicate_count,
        needs_more_data_count=needs_more_data_count,
    )
    explanation = (
        "No prior feedback matched this candidate target."
        if matched_count == 0
        else (
            "Priority delta is computed from local feedback label counts: "
            "positive labels increase review priority, negative labels reduce it, "
            "needs_more_data is slightly elevated, and known_pattern or duplicate "
            "labels mark possible repeated review context."
        )
    )

    return ReviewMemorySignal(
        priority_delta=priority_delta,
        matched_feedback_count=matched_count,
        positive_feedback_count=positive_count,
        negative_feedback_count=negative_count,
        known_pattern_count=known_count,
        duplicate_count=duplicate_count,
        needs_more_data_count=needs_more_data_count,
        notes=notes,
        explanation=explanation,
    )


def _candidate_target_id(candidate: object, target_type: str) -> str | None:
    if isinstance(candidate, dict):
        if target_type == "anomaly":
            value = candidate.get("anomaly_id") or candidate.get("target_id") or candidate.get("id")
        else:
            value = candidate.get("concept_id") or candidate.get("target_id") or candidate.get("id")
        return str(value) if value else None

    if target_type == "anomaly":
        value = getattr(candidate, "anomaly_id", None)
        if value:
            return str(value)
    if target_type == "concept":
        value = getattr(candidate, "concept_id", None)
        if value:
            return str(value)

    metadata = getattr(candidate, "metadata", None)
    if isinstance(metadata, dict):
        value = metadata.get("target_id")
        return str(value) if value else None
    return None


def _signal_notes(
    *,
    positive_count: int,
    negative_count: int,
    known_count: int,
    duplicate_count: int,
    needs_more_data_count: int,
) -> list[str]:
    notes: list[str] = []
    if positive_count:
        notes.append("Prior feedback marked this target as interesting or important.")
    if negative_count:
        notes.append("Prior feedback marked this target as false positive or not useful.")
    if needs_more_data_count:
        notes.append("Prior feedback requested more data before interpretation.")
    if known_count:
        notes.append("Prior feedback marked this target as a possibly known pattern.")
    if duplicate_count:
        notes.append("Prior feedback marked this target as a possible duplicate.")
    return notes

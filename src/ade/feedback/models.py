"""Typed records for local ADE human-review feedback."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

ALLOWED_TARGET_TYPES = frozenset({"anomaly", "concept", "temporal"})
ALLOWED_FEEDBACK_LABELS = frozenset(
    {
        "interesting",
        "known_pattern",
        "false_positive",
        "duplicate",
        "important",
        "not_useful",
        "needs_more_data",
    }
)


@dataclass(frozen=True)
class ReviewFeedback:
    """One local reviewer label attached to a report target."""

    feedback_id: str
    run_id: str
    report_path: Path
    target_type: str
    target_id: str
    label: str
    notes: str = ""
    reviewer: str = "local"
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate fields that define the local feedback contract."""

        if not self.feedback_id:
            raise ValueError("feedback_id must not be empty.")
        if not self.run_id:
            raise ValueError("run_id must not be empty.")
        if not self.target_id:
            raise ValueError("target_id must not be empty.")
        if self.target_type not in ALLOWED_TARGET_TYPES:
            allowed = ", ".join(sorted(ALLOWED_TARGET_TYPES))
            raise ValueError(
                f"Unsupported feedback target_type: {self.target_type}. Allowed: {allowed}."
            )
        if self.label not in ALLOWED_FEEDBACK_LABELS:
            allowed = ", ".join(sorted(ALLOWED_FEEDBACK_LABELS))
            raise ValueError(f"Unsupported feedback label: {self.label}. Allowed: {allowed}.")

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        report_path: Path,
        target_type: str,
        target_id: str,
        label: str,
        notes: str = "",
        reviewer: str = "local",
        metadata: dict[str, Any] | None = None,
    ) -> ReviewFeedback:
        """Create a feedback record with a timestamped local identifier."""

        created_at = datetime.now(UTC)
        feedback_id = f"feedback_{created_at.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
        return cls(
            feedback_id=feedback_id,
            run_id=run_id,
            report_path=report_path,
            target_type=target_type,
            target_id=target_id,
            label=label,
            notes=notes,
            reviewer=reviewer,
            created_at=created_at.isoformat(),
            metadata=metadata or {},
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dictionary representation."""

        return {
            "feedback_id": self.feedback_id,
            "run_id": self.run_id,
            "report_path": self.report_path.as_posix(),
            "target_type": self.target_type,
            "target_id": self.target_id,
            "label": self.label,
            "notes": self.notes,
            "reviewer": self.reviewer,
            "created_at": self.created_at,
            "metadata": _json_safe(self.metadata),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ReviewFeedback:
        """Build and validate feedback from JSON data."""

        metadata = data.get("metadata") or {}
        if not isinstance(metadata, dict):
            raise ValueError("metadata must be a JSON object.")
        return cls(
            feedback_id=str(data.get("feedback_id", "")),
            run_id=str(data.get("run_id", "")),
            report_path=Path(str(data.get("report_path", ""))),
            target_type=str(data.get("target_type", "")),
            target_id=str(data.get("target_id", "")),
            label=str(data.get("label", "")),
            notes=str(data.get("notes", "")),
            reviewer=str(data.get("reviewer", "local")),
            created_at=str(data.get("created_at", "")),
            metadata=metadata,
        )


@dataclass(frozen=True)
class ReviewSummary:
    """Label counts for a local feedback query."""

    run_id: str | None
    total_feedback: int
    label_counts: dict[str, int]

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe summary."""

        return {
            "run_id": self.run_id,
            "total_feedback": int(self.total_feedback),
            "label_counts": dict(sorted(self.label_counts.items())),
        }


def _json_safe(value: Any) -> Any:
    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe(item) for item in value]
    return value

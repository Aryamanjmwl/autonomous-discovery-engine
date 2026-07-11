"""Append-only JSONL store for local ADE review feedback."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

from ade.feedback.models import ReviewFeedback, ReviewSummary


class FeedbackStore:
    """File-backed local feedback store."""

    def __init__(self, store_path: Path = Path("data/feedback/feedback.jsonl")) -> None:
        self.store_path = Path(store_path)

    def append(self, feedback: ReviewFeedback) -> None:
        """Append one feedback record, creating the parent directory if needed."""

        self.store_path.parent.mkdir(parents=True, exist_ok=True)
        with self.store_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(feedback.to_dict(), sort_keys=True))
            handle.write("\n")

    def read_all(self) -> list[ReviewFeedback]:
        """Read all feedback records, returning an empty list when absent."""

        if not self.store_path.exists():
            return []

        records: list[ReviewFeedback] = []
        with self.store_path.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    loaded = json.loads(stripped)
                except json.JSONDecodeError as error:
                    raise ValueError(
                        f"Malformed feedback JSONL entry at {self.store_path}:{line_number}"
                    ) from error
                if not isinstance(loaded, dict):
                    raise ValueError(
                        f"Feedback JSONL entry must be an object at {self.store_path}:{line_number}"
                    )
                try:
                    records.append(ReviewFeedback.from_dict(loaded))
                except ValueError as error:
                    raise ValueError(
                        f"Invalid feedback record at {self.store_path}:{line_number}: {error}"
                    ) from error
        return records

    def filter_by_run_id(self, run_id: str) -> list[ReviewFeedback]:
        """Return feedback for one run ID."""

        return [record for record in self.read_all() if record.run_id == run_id]

    def filter_by_target_type(self, target_type: str) -> list[ReviewFeedback]:
        """Return feedback for one target type."""

        return [record for record in self.read_all() if record.target_type == target_type]

    def summarize_labels_by_run_id(self, run_id: str | None = None) -> ReviewSummary:
        """Return label counts for all feedback or one run."""

        records = self.filter_by_run_id(run_id) if run_id else self.read_all()
        counts = Counter(record.label for record in records)
        return ReviewSummary(
            run_id=run_id,
            total_feedback=len(records),
            label_counts=dict(counts),
        )

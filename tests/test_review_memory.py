from __future__ import annotations

from pathlib import Path

from ade.feedback import ReviewFeedback
from ade.memory.review_memory import (
    build_review_memory_summary,
    score_candidate_with_review_memory,
)


def _feedback(
    tmp_path: Path,
    *,
    target_type: str = "anomaly",
    target_id: str = "anomaly-0001",
    label: str = "interesting",
) -> ReviewFeedback:
    return ReviewFeedback.create(
        run_id="ade_20260709_120000_abcdef",
        report_path=tmp_path / "report.json",
        target_type=target_type,
        target_id=target_id,
        label=label,
    )


def test_review_memory_summary_with_no_feedback() -> None:
    summary = build_review_memory_summary([])

    assert summary.total_feedback_count == 0
    assert summary.label_counts == {}
    assert summary.label_counts_by_target_type == {}
    assert summary.to_dict()["total_feedback_count"] == 0


def test_review_memory_summary_counts_positive_labels(tmp_path: Path) -> None:
    summary = build_review_memory_summary(
        [
            _feedback(tmp_path, label="interesting"),
            _feedback(tmp_path, label="important"),
        ]
    )

    assert summary.total_feedback_count == 2
    assert summary.label_counts == {"interesting": 1, "important": 1}
    signal = score_candidate_with_review_memory(
        {"anomaly_id": "anomaly-0001"},
        "anomaly",
        summary,
    )
    assert signal.priority_delta == 2.0
    assert signal.positive_feedback_count == 2


def test_review_memory_summary_counts_negative_labels(tmp_path: Path) -> None:
    summary = build_review_memory_summary(
        [
            _feedback(tmp_path, label="false_positive"),
            _feedback(tmp_path, label="not_useful"),
        ]
    )

    signal = score_candidate_with_review_memory(
        {"anomaly_id": "anomaly-0001"},
        "anomaly",
        summary,
    )
    assert signal.priority_delta == -2.0
    assert signal.negative_feedback_count == 2


def test_review_memory_known_pattern_duplicate_and_needs_more_data(
    tmp_path: Path,
) -> None:
    summary = build_review_memory_summary(
        [
            _feedback(
                tmp_path,
                target_type="concept",
                target_id="concept-001",
                label="known_pattern",
            ),
            _feedback(tmp_path, target_type="concept", target_id="concept-001", label="duplicate"),
            _feedback(
                tmp_path,
                target_type="concept",
                target_id="concept-001",
                label="needs_more_data",
            ),
        ]
    )

    signal = score_candidate_with_review_memory(
        {"concept_id": "concept-001"},
        "concept",
        summary,
    )
    assert signal.known_pattern_count == 1
    assert signal.duplicate_count == 1
    assert signal.needs_more_data_count == 1
    assert signal.priority_delta == -0.5
    assert any("known pattern" in note for note in signal.notes)


def test_review_memory_candidate_scoring_is_deterministic(tmp_path: Path) -> None:
    summary = build_review_memory_summary(
        [
            _feedback(tmp_path, label="important"),
            _feedback(tmp_path, label="needs_more_data"),
            _feedback(tmp_path, target_id="anomaly-0002", label="not_useful"),
        ]
    )

    first = score_candidate_with_review_memory(
        {"anomaly_id": "anomaly-0001"},
        "anomaly",
        summary,
    ).to_dict()
    second = score_candidate_with_review_memory(
        {"anomaly_id": "anomaly-0001"},
        "anomaly",
        summary,
    ).to_dict()

    assert first == second
    assert first["priority_delta"] == 1.25

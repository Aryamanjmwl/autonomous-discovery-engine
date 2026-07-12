from __future__ import annotations

import json
from pathlib import Path

import pytest

from ade.cli import (
    add_feedback_from_report,
    format_feedback_summary,
    format_review_memory_summary,
    main,
)
from ade.feedback import FeedbackStore, ReviewFeedback


def _valid_report() -> dict[str, object]:
    return {
        "project_name": "ADE",
        "run_id": "ade_20260709_120000_abcdef",
        "run_metadata": {"run_id": "ade_20260709_120000_abcdef"},
        "candidate_anomalies": [
            {
                "anomaly_id": "anomaly-0001",
                "source_path": "image.png",
                "novelty_score": 0.42,
            }
        ],
        "candidate_unknown_concepts": [
            {
                "concept_id": "concept-001",
                "example_count": 1,
            }
        ],
        "candidate_concepts": [
            {
                "concept_id": "concept-001",
                "example_count": 1,
            }
        ],
        "human_review_required": True,
        "report_version": "1.0",
    }


def _write_report(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(_valid_report()), encoding="utf-8")


def test_review_feedback_serialization_round_trip(tmp_path: Path) -> None:
    feedback = ReviewFeedback.create(
        run_id="ade_20260709_120000_abcdef",
        report_path=tmp_path / "report.json",
        target_type="anomaly",
        target_id="anomaly-0001",
        label="interesting",
        notes="Worth reviewing",
        reviewer="local",
        metadata={"asset": tmp_path / "asset.png"},
    )

    restored = ReviewFeedback.from_dict(feedback.to_dict())

    assert restored.feedback_id == feedback.feedback_id
    assert restored.created_at.endswith("+00:00")
    assert restored.report_path.as_posix().endswith("report.json")
    assert restored.metadata["asset"].endswith("asset.png")


def test_review_feedback_rejects_invalid_label_and_target_type(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="Unsupported feedback label"):
        ReviewFeedback.create(
            run_id="run",
            report_path=tmp_path / "report.json",
            target_type="anomaly",
            target_id="anomaly-0001",
            label="bad_label",
        )

    with pytest.raises(ValueError, match="Unsupported feedback target_type"):
        ReviewFeedback.create(
            run_id="run",
            report_path=tmp_path / "report.json",
            target_type="finding",
            target_id="anomaly-0001",
            label="interesting",
        )


def test_feedback_store_append_read_filter_and_summarize(tmp_path: Path) -> None:
    store = FeedbackStore(tmp_path / "feedback.jsonl")
    first = ReviewFeedback.create(
        run_id="run-1",
        report_path=tmp_path / "report.json",
        target_type="anomaly",
        target_id="anomaly-0001",
        label="interesting",
    )
    second = ReviewFeedback.create(
        run_id="run-2",
        report_path=tmp_path / "report.json",
        target_type="concept",
        target_id="concept-001",
        label="known_pattern",
    )

    store.append(first)
    store.append(second)

    assert store.read_all() == [first, second]
    assert store.filter_by_run_id("run-1") == [first]
    assert store.filter_by_target_type("concept") == [second]
    assert store.summarize_labels_by_run_id("run-1").to_dict()["label_counts"] == {
        "interesting": 1
    }


def test_feedback_store_missing_file_and_malformed_jsonl(tmp_path: Path) -> None:
    assert FeedbackStore(tmp_path / "missing.jsonl").read_all() == []

    malformed = tmp_path / "feedback.jsonl"
    malformed.write_text("{not-json}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Malformed feedback JSONL entry"):
        FeedbackStore(malformed).read_all()


def test_add_feedback_from_report_accepts_anomaly_and_concept_ids(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    store_path = tmp_path / "feedback.jsonl"
    _write_report(report_path)

    anomaly_feedback = add_feedback_from_report(
        report_path=report_path,
        target_type="anomaly",
        target_id="anomaly-0001",
        label="interesting",
        notes="Local review",
        reviewer="local",
        store_path=store_path,
    )
    concept_feedback = add_feedback_from_report(
        report_path=report_path,
        target_type="concept",
        target_id="concept-001",
        label="known_pattern",
        notes="Known recurring pattern",
        reviewer="local",
        store_path=store_path,
    )

    assert FeedbackStore(store_path).read_all() == [anomaly_feedback, concept_feedback]


def test_add_feedback_rejects_missing_report_and_unknown_target(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Report JSON does not exist"):
        add_feedback_from_report(
            report_path=tmp_path / "missing.json",
            target_type="anomaly",
            target_id="anomaly-0001",
            label="interesting",
            notes="",
            reviewer="local",
            store_path=tmp_path / "feedback.jsonl",
        )

    report_path = tmp_path / "report.json"
    _write_report(report_path)
    with pytest.raises(ValueError, match="Target ID was not found"):
        add_feedback_from_report(
            report_path=report_path,
            target_type="anomaly",
            target_id="anomaly-9999",
            label="interesting",
            notes="",
            reviewer="local",
            store_path=tmp_path / "feedback.jsonl",
        )


def test_cli_add_feedback_and_list_feedback_use_configured_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    report_path = tmp_path / "report.json"
    store_path = tmp_path / "feedback.jsonl"
    config_path = tmp_path / "config.yaml"
    _write_report(report_path)
    config_path.write_text(
        f"feedback:\n  enabled: true\n  store_path: \"{store_path.as_posix()}\"\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "ade",
            "--config",
            str(config_path),
            "--add-feedback",
            str(report_path),
            "--target-type",
            "anomaly",
            "--target-id",
            "anomaly-0001",
            "--label",
            "interesting",
            "--notes",
            "Local review",
            "--reviewer",
            "local",
        ],
    )
    main()

    assert "ADE feedback recorded" in capsys.readouterr().out
    assert len(FeedbackStore(store_path).read_all()) == 1

    summary = format_feedback_summary(store_path)
    assert "Total feedback: 1" in summary
    assert "interesting: 1" in summary

    memory_summary = format_review_memory_summary(store_path)
    assert "ADE Review Memory Summary" in memory_summary
    assert "Feedback records: 1" in memory_summary
    assert "interesting: 1" in memory_summary


def test_cli_add_feedback_rejects_invalid_label(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    report_path = tmp_path / "report.json"
    _write_report(report_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "ade",
            "--add-feedback",
            str(report_path),
            "--target-type",
            "anomaly",
            "--target-id",
            "anomaly-0001",
            "--label",
            "bad_label",
        ],
    )

    with pytest.raises(SystemExit):
        main()


def test_cli_summarize_feedback_memory_tolerates_missing_store(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    config_path = tmp_path / "config.yaml"
    config_path.write_text(
        "review_memory:\n"
        "  enabled: true\n"
        f"  feedback_store_path: \"{(tmp_path / 'missing.jsonl').as_posix()}\"\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        ["ade", "--config", str(config_path), "--summarize-feedback-memory"],
    )

    main()

    output = capsys.readouterr().out
    assert "ADE Review Memory Summary" in output
    assert "Feedback records: 0" in output

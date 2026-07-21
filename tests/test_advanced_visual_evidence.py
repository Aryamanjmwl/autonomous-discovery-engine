import json
from pathlib import Path

from ade.reporting.html_report import render_html_report
from ade.reporting.report_generator import DatasetSummary, ReportGenerator
from ade.reporting.report_validator import validate_report_dict
from ade.studio.service import StudioPaths, build_summary, load_report

FINGERPRINT = "a" * 64


def _base_report() -> dict[str, object]:
    return {
        "project_name": "ADE",
        "run_id": "run-1",
        "run_metadata": {},
        "candidate_anomalies": [],
        "candidate_unknown_concepts": [],
        "human_review_required": True,
    }


def _summary(**values: object) -> dict[str, object]:
    return {
        "artifact_path": "artifacts/evidence.json",
        "artifact_fingerprint": FINGERPRINT,
        "requires_human_review": True,
        **values,
    }


def test_default_report_omits_advanced_evidence_and_optional_markdown() -> None:
    generator = ReportGenerator()
    arguments = {
        "dataset_summary": DatasetSummary(Path("data/raw"), 0, 0),
        "candidates": [],
        "evidence_items": [],
        "confidences": [],
        "hypotheses": [],
    }

    markdown = generator.generate(**arguments)
    report = generator.generate_json(**arguments)

    assert validate_report_dict(report).is_valid
    assert not any(key.endswith("_summary") and "advanced" in key for key in report)
    assert "Optional Reference Scoring Evidence" not in markdown
    assert "Optional Benchmark Validation Artifact" not in markdown


def test_optional_evidence_validates_and_renders_cautious_markdown_and_html() -> None:
    evidence = {
        "reference_scoring_summary": _summary(calibrated=False, candidate_count=3),
        "calibration_summary": _summary(
            calibrated=True, labels_available=True, sample_count=20
        ),
        "benchmark_validation_summary": _summary(
            dataset_name="local-validation", labels_available=True, sample_count=20,
            metrics={"precision_at_5": 0.6},
        ),
    }
    generator = ReportGenerator()
    arguments = {
        "dataset_summary": DatasetSummary(Path("data/raw"), 0, 0),
        "candidates": [],
        "evidence_items": [],
        "confidences": [],
        "hypotheses": [],
        "advanced_evidence": evidence,
    }

    markdown = generator.generate(**arguments)
    report = generator.generate_json(**arguments)
    html = render_html_report(report)

    assert validate_report_dict(report).is_valid
    assert "Optional Reference Scoring Evidence" in markdown
    assert "Optional Calibration and Threshold Evaluation" in markdown
    assert "Optional Benchmark Validation Artifact" in markdown
    assert "requires human review" in markdown.lower()
    assert "universal anomaly probability" in markdown
    assert "product guarantee" not in markdown
    assert "guaranteed detection" not in markdown.lower()
    assert "Optional Reference Scoring Evidence" in html
    assert "not a universal anomaly probability" in html


def test_malformed_advanced_evidence_is_rejected() -> None:
    report = _base_report()
    report["calibration_summary"] = {
        "artifact_path": "artifact.json",
        "artifact_fingerprint": "invalid",
        "calibrated": "yes",
        "labels_available": True,
        "requires_human_review": False,
    }

    result = validate_report_dict(report)

    assert not result.is_valid
    assert any("calibration_summary.artifact_fingerprint" in error for error in result.errors)
    assert any("calibration_summary.calibrated" in error for error in result.errors)


def test_studio_exposes_only_valid_report_backed_advanced_evidence(tmp_path: Path) -> None:
    reports = tmp_path / "reports"
    reports.mkdir()
    report = _base_report()
    report["reference_scoring_summary"] = _summary(calibrated=False, candidate_count=2)
    report["calibration_summary"] = {"artifact_path": "broken.json"}
    (reports / "report.json").write_text(json.dumps(report), encoding="utf-8")
    paths = StudioPaths(
        reports_dir=reports,
        run_index_path=reports / "runs" / "index.json",
        dashboard_dir=tmp_path / "dashboard",
        feedback_path=tmp_path / "feedback.jsonl",
    )

    detail = load_report("report.json", paths)
    summary = build_summary(paths)

    assert set(detail["advanced_evidence"]) == {"reference_scoring_summary"}
    assert detail["advanced_evidence_available"]["reference_scoring_summary"] is True
    assert detail["advanced_evidence_available"]["calibration_summary"] is False
    assert summary["advanced_evidence_available"]["reference_scoring_summary"] is True

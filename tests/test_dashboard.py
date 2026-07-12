import json
from pathlib import Path

from ade.cli import main
from ade.dashboard.local_dashboard import (
    collect_dashboard_data,
    export_local_dashboard,
    render_dashboard_html,
)
from ade.dashboard.service import generate_dashboard


def _run_summary(run_id: str, report_path: Path) -> dict[str, object]:
    return {
        "run_id": run_id,
        "generated_at": "2026-07-07T12:00:00+00:00",
        "input_path": "data/raw/demo_images",
        "markdown_report_path": report_path.with_suffix(".md").as_posix(),
        "json_report_path": report_path.as_posix(),
        "run_metadata_path": f"data/reports/runs/{run_id}.json",
        "number_of_images": 3,
        "number_of_patches": 12,
        "number_of_candidate_anomalies": 1,
        "number_of_candidate_unknown_concepts": 1,
        "human_review_required": True,
    }


def _write_index(index_path: Path, runs: list[dict[str, object]]) -> None:
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "index_version": "1.0",
                "updated_at": "2026-07-07T12:01:00+00:00",
                "runs": runs,
            }
        ),
        encoding="utf-8",
    )


def _write_report(report_path: Path) -> None:
    asset_path = report_path.parent / "assets" / "anomaly_0001.png"
    asset_path.parent.mkdir(parents=True, exist_ok=True)
    asset_path.write_bytes(b"not a real png but enough for a local link test")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(
        json.dumps(
            {
                "run_id": "ade_20260707_120000_abcdef",
                "input_summary": {"input_dir": "data/raw/demo_images"},
                "dataset_profile": {
                    "input_type": "image_folder",
                    "valid_images": 3,
                    "unsupported_file_count": 0,
                    "unreadable_file_count": 0,
                    "estimated_patch_count": 12,
                    "warnings": [],
                },
                "backend_metadata": {
                    "scoring_backend": "centroid_distance",
                    "clustering_backend": "threshold_candidate_grouping",
                },
                "number_of_images": 3,
                "number_of_patches": 12,
                "candidate_anomalies": [
                    {
                        "rank": 1,
                        "source_path": "data/raw/demo_images/demo_image_01.png",
                        "novelty_score": 0.91,
                        "reason": "Feature profile differs from nearby examples.",
                        "nearest_neighbor_id": "patch-002",
                        "preview_path": "assets/anomaly_0001.png",
                    }
                ],
                "candidate_unknown_concepts": [
                    {
                        "concept_id": "concept-001",
                        "example_count": 1,
                        "average_novelty": 0.91,
                        "confidence_score": 0.63,
                        "representative_anomaly_id": "anomaly-0001",
                        "summary": "One candidate visual pattern grouped for review.",
                        "possible_pattern": "This may indicate a candidate visual pattern.",
                        "examples": [
                            {
                                "source_path": "data/raw/demo_images/demo_image_01.png",
                                "novelty_score": 0.91,
                                "rank": 1,
                                "preview_path": "assets/anomaly_0001.png",
                            }
                        ],
                    }
                ],
                "limitations": [
                    "Candidate findings require human review.",
                ],
                "run_metadata": {
                    "pipeline_version": "0.1.0",
                    "human_review_required": True,
                },
            }
        ),
        encoding="utf-8",
    )


def _write_local_dashboard_report(report_path: Path) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    html_path = report_path.with_suffix(".html")
    html_path.write_text("<!doctype html><title>Report</title>", encoding="utf-8")
    report_path.write_text(
        json.dumps(
            {
                "project_name": "ADE",
                "report_version": "1.0",
                "run_id": "ade_20260707_120000_abcdef",
                "generated_at": "2026-07-07T12:00:00+00:00",
                "modality": "tabular",
                "run_metadata": {"run_id": "ade_20260707_120000_abcdef"},
                "number_of_candidate_anomalies": 2,
                "number_of_candidate_unknown_concepts": 1,
                "candidate_anomalies": [{"anomaly_id": "row-000001"}],
                "candidate_unknown_concepts": [{"concept_id": "concept-001"}],
                "human_review_required": True,
            }
        ),
        encoding="utf-8",
    )


def _write_benchmark(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "benchmark_id": "bench_20260707_120000_abcdef",
                "generated_at": "2026-07-07T12:05:00+00:00",
                "duration_seconds": 1.25,
                "report_valid": True,
                "input_path": "data/raw/demo_images",
                "config_path": "configs/default.yaml",
            }
        ),
        encoding="utf-8",
    )


def _write_feedback(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "feedback_id": "feedback-1",
                "run_id": "ade_20260707_120000_abcdef",
                "report_path": "data/reports/demo_report.json",
                "target_type": "anomaly",
                "target_id": "row-000001",
                "label": "interesting",
                "reviewer": "local",
                "created_at": "2026-07-07T12:10:00+00:00",
            }
        )
        + "\n",
        encoding="utf-8",
    )


def test_dashboard_handles_empty_run_history(tmp_path: Path) -> None:
    result = generate_dashboard(
        index_path=tmp_path / "reports" / "runs" / "index.json",
        output_dir=tmp_path / "dashboard",
    )

    index_html = result.index_path.read_text(encoding="utf-8")
    runs_html = result.runs_path.read_text(encoding="utf-8")

    assert result.run_count == 0
    assert "No ADE runs found yet." in index_html
    assert "Run an analysis before generating the dashboard" in runs_html


def test_local_dashboard_exporter_handles_missing_artifacts(tmp_path: Path) -> None:
    result = export_local_dashboard(
        output_dir=tmp_path / "dashboard",
        run_index_path=tmp_path / "missing" / "index.json",
        reports_dir=tmp_path / "missing_reports",
        benchmarks_dir=tmp_path / "missing_benchmarks",
        feedback_path=tmp_path / "missing_feedback.jsonl",
    )
    data = json.loads(result.data_path.read_text(encoding="utf-8"))
    html = result.index_path.read_text(encoding="utf-8")

    assert result.run_count == 0
    assert result.report_count == 0
    assert result.benchmark_count == 0
    assert result.feedback_count == 0
    assert data["summary"]["total_runs"] == 0
    assert "ADE Local Dashboard" in html
    assert "No run history found." in html


def test_local_dashboard_data_includes_artifact_summaries(tmp_path: Path) -> None:
    report_path = tmp_path / "reports" / "demo_report.json"
    index_path = tmp_path / "reports" / "runs" / "index.json"
    benchmark_path = tmp_path / "benchmarks" / "demo_benchmark.json"
    feedback_path = tmp_path / "feedback" / "feedback.jsonl"
    _write_local_dashboard_report(report_path)
    _write_index(index_path, [_run_summary("ade_20260707_120000_abcdef", report_path)])
    _write_benchmark(benchmark_path)
    _write_feedback(feedback_path)

    data = collect_dashboard_data(
        run_index_path=index_path,
        reports_dir=report_path.parent,
        benchmarks_dir=benchmark_path.parent,
        feedback_path=feedback_path,
    )

    assert data["summary"]["total_runs"] == 1
    assert data["summary"]["total_candidate_anomalies"] == 1
    assert data["summary"]["total_candidate_concepts"] == 1
    assert data["summary"]["benchmark_count"] == 1
    assert data["summary"]["feedback_count"] == 1
    assert data["reports"][0]["validation_status"] == "valid"
    assert data["reports"][0]["html_report_path"].endswith("demo_report.html")
    assert data["benchmarks"][0]["benchmark_id"] == "bench_20260707_120000_abcdef"
    assert data["feedback"]["label_counts"] == {"interesting": 1}


def test_local_dashboard_html_escapes_unsafe_strings() -> None:
    html = render_dashboard_html(
        {
            "summary": {
                "total_runs": 1,
                "total_candidate_anomalies": 0,
                "total_candidate_concepts": 0,
                "latest_run_timestamp": "<script>alert(1)</script>",
                "benchmark_count": 0,
                "feedback_count": 0,
            },
            "runs": [
                {
                    "run_id": "<img src=x onerror=alert(1)>",
                    "generated_at": "now",
                    "input_path": "<script>alert(2)</script>",
                }
            ],
            "reports": [],
            "benchmarks": [],
            "feedback": {"total_feedback_records": 0, "label_counts": {}, "recent_records": []},
            "limitations": ["Findings require human review."],
        }
    )

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "<img src=x onerror=alert(1)>" not in html


def test_dashboard_handles_malformed_report_json(tmp_path: Path) -> None:
    report_path = tmp_path / "reports" / "demo_report.json"
    report_path.parent.mkdir(parents=True)
    report_path.write_text("{not valid json", encoding="utf-8")
    run_id = "ade_20260707_120000_abcdef"
    index_path = tmp_path / "reports" / "runs" / "index.json"
    _write_index(index_path, [_run_summary(run_id, report_path)])

    result = generate_dashboard(index_path=index_path, output_dir=tmp_path / "dashboard")
    detail_path = result.output_dir / "runs" / f"{run_id}.html"
    detail_html = detail_path.read_text(encoding="utf-8")

    assert result.run_count == 1
    assert "JSON report file is malformed" in detail_html


def test_dashboard_renders_run_detail_with_findings_and_evidence(tmp_path: Path) -> None:
    report_path = tmp_path / "reports" / "demo_report.json"
    _write_report(report_path)
    run_id = "ade_20260707_120000_abcdef"
    index_path = tmp_path / "reports" / "runs" / "index.json"
    _write_index(index_path, [_run_summary(run_id, report_path)])

    result = generate_dashboard(index_path=index_path, output_dir=tmp_path / "dashboard")
    runs_html = result.runs_path.read_text(encoding="utf-8")
    detail_html = (result.output_dir / "runs" / f"{run_id}.html").read_text(
        encoding="utf-8"
    )

    assert "ADE Runs" in runs_html
    assert run_id in runs_html
    assert "Dataset Summary" in detail_html
    assert "Discovery Configuration" in detail_html
    assert "Top Findings" in detail_html
    assert "Concept Groups" in detail_html
    assert "Feature profile differs from nearby examples." in detail_html
    assert "candidate evidence preview" in detail_html
    assert "Limitations and Reproducibility" in detail_html


def test_cli_dashboard_generates_static_files(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["ade", "dashboard", "--dashboard-output", str(tmp_path / "dashboard")],
    )

    main()

    output = capsys.readouterr().out
    assert "ADE dashboard written to" in output
    assert "Open locally:" in output
    assert (tmp_path / "dashboard" / "index.html").is_file()
    assert (tmp_path / "dashboard" / "runs.html").is_file()


def test_cli_export_local_dashboard_generates_static_files(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "sys.argv",
        ["ade", "--export-local-dashboard", "--output", str(tmp_path / "local_dashboard")],
    )

    main()

    output = capsys.readouterr().out
    assert "ADE local dashboard written to" in output
    assert "Dashboard data written to" in output
    assert (tmp_path / "local_dashboard" / "index.html").is_file()
    assert (tmp_path / "local_dashboard" / "dashboard_data.json").is_file()


def test_cli_export_html_report_still_generates_static_file(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    report_path = tmp_path / "reports" / "demo_report.json"
    output_path = tmp_path / "reports" / "demo_report.html"
    _write_local_dashboard_report(report_path)
    monkeypatch.setattr(
        "sys.argv",
        [
            "ade",
            "--export-html-report",
            str(report_path),
            "--output",
            str(output_path),
        ],
    )

    main()

    output = capsys.readouterr().out
    assert "HTML report written to" in output
    assert output_path.is_file()

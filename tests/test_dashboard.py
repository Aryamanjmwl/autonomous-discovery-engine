import json
from pathlib import Path

from ade.cli import main
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

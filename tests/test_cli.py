import importlib.util
import json
from pathlib import Path

import pytest

from ade.cli import format_run_history, main, run_pipeline


def _sample_run(run_id: str) -> dict[str, object]:
    return {
        "run_id": run_id,
        "generated_at": "2026-06-18T14:30:22+00:00",
        "input_path": "data/raw/demo_images",
        "markdown_report_path": "data/reports/demo_report.md",
        "json_report_path": "data/reports/demo_report.json",
        "run_metadata_path": f"data/reports/runs/{run_id}.json",
        "number_of_images": 6,
        "number_of_patches": 96,
        "number_of_candidate_anomalies": 10,
        "number_of_candidate_unknown_concepts": 3,
        "human_review_required": True,
    }


def _load_demo_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "create_demo_data.py"
    spec = importlib.util.spec_from_file_location("create_demo_data", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_format_run_history_handles_missing_index(tmp_path: Path) -> None:
    result = format_run_history(index_path=tmp_path / "runs" / "index.json")

    assert result == "No ADE run history found yet. Run an analysis first."


def test_format_run_history_lists_runs_and_applies_limit(tmp_path: Path) -> None:
    index_path = tmp_path / "runs" / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "index_version": "1.0",
                "updated_at": "2026-06-18T14:31:00+00:00",
                "runs": [
                    _sample_run("ade_20260618_143000_a11111"),
                    _sample_run("ade_20260618_143100_b22222"),
                ],
            }
        ),
        encoding="utf-8",
    )

    result = format_run_history(index_path=index_path, limit=1)

    assert "## ADE Run History" in result
    assert "Total runs: 1" in result
    assert "ade_20260618_143000_a11111" not in result
    assert "ade_20260618_143100_b22222" in result
    assert "Human review required: True" in result


def test_cli_list_runs_reads_default_index(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    index_path = tmp_path / "data" / "reports" / "runs" / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "index_version": "1.0",
                "updated_at": "2026-06-18T14:31:00+00:00",
                "runs": [_sample_run("ade_20260618_143100_b22222")],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("sys.argv", ["ade", "--list-runs", "--limit", "5"])

    main()

    output = capsys.readouterr().out
    assert "## ADE Run History" in output
    assert "ade_20260618_143100_b22222" in output


def test_format_run_history_rejects_invalid_limit(tmp_path: Path) -> None:
    index_path = tmp_path / "runs" / "index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(
            {
                "index_version": "1.0",
                "updated_at": "2026-06-18T14:31:00+00:00",
                "runs": [_sample_run("ade_20260618_143100_b22222")],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="--limit"):
        format_run_history(index_path=index_path, limit=0)


def test_run_pipeline_rejects_empty_input_directory(tmp_path: Path) -> None:
    input_dir = tmp_path / "empty_images"
    input_dir.mkdir()

    with pytest.raises(ValueError, match="No supported image files"):
        run_pipeline(
            input_dir=input_dir,
            output_path=tmp_path / "report.md",
        )


def test_run_pipeline_rejects_missing_input_path(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Input directory does not exist"):
        run_pipeline(
            input_dir=tmp_path / "missing",
            output_path=tmp_path / "report.md",
        )


def test_run_pipeline_rejects_missing_explicit_config(tmp_path: Path) -> None:
    input_dir = tmp_path / "images"
    input_dir.mkdir()

    with pytest.raises(FileNotFoundError, match="Config file does not exist"):
        run_pipeline(
            input_dir=input_dir,
            output_path=tmp_path / "report.md",
            config_path=tmp_path / "missing.yaml",
        )


def test_cli_analysis_uses_explicit_config(tmp_path: Path, monkeypatch) -> None:
    pytest.importorskip("PIL.Image")
    image_dir = tmp_path / "images"
    report_path = tmp_path / "report.md"
    config_path = tmp_path / "config.yaml"
    _load_demo_module().generate_demo_images(output_dir=image_dir)
    config_path.write_text(
        """
project:
  name: "ADE Test"
  pipeline_version: "test-version"
preprocessing:
  patch_size: 128
  patch_stride: 128
discovery:
  max_candidate_anomalies: 2
  max_concepts: 2
  novelty_metric: "euclidean"
  cluster_distance_threshold: 0.35
reporting:
  report_version: "test-report"
  human_review_required: true
  save_patch_previews: true
  assets_dir_name: "preview_assets"
  runs_dir_name: "run_records"
demo_data:
  output_dir: "data/raw/demo_images"
  image_count: 6
  image_size: 256
  seed: 42
""".strip(),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        "sys.argv",
        [
            "ade",
            "--input",
            str(image_dir),
            "--output",
            str(report_path),
            "--config",
            str(config_path),
        ],
    )

    main()

    report_data = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert report_path.is_file()
    assert report_path.with_suffix(".json").is_file()
    assert report_data["project_name"] == "ADE Test"
    assert report_data["report_version"] == "test-report"
    assert report_data["number_of_candidate_anomalies"] == 2
    assert report_data["backend_metadata"]["scoring_backend"] == "centroid_distance"
    assert report_data["backend_metadata"]["clustering_backend"] == (
        "threshold_candidate_grouping"
    )
    assert report_data["backend_metadata"]["top_k"] == 2
    assert report_data["run_metadata"]["pipeline_version"] == "test-version"
    assert report_data["run_index_path"].endswith("run_records/index.json")
    assert (tmp_path / "preview_assets").is_dir()
    assert (tmp_path / "run_records" / "index.json").is_file()

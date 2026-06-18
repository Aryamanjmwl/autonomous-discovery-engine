import json
from pathlib import Path

import pytest

from ade.cli import format_run_history, main


def _cli_output_dir(name: str) -> Path:
    output_dir = Path("tests/.tmp_cli_outputs") / name
    if output_dir.exists():
        for path in sorted(output_dir.rglob("*"), reverse=True):
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                path.rmdir()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


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


def test_format_run_history_handles_missing_index() -> None:
    output_dir = _cli_output_dir("missing_index")

    result = format_run_history(index_path=output_dir / "runs" / "index.json")

    assert result == "No ADE run history found yet. Run an analysis first."


def test_format_run_history_lists_runs_and_applies_limit() -> None:
    output_dir = _cli_output_dir("list_runs")
    index_path = output_dir / "runs" / "index.json"
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


def test_cli_list_runs_reads_default_index(monkeypatch, capsys) -> None:
    output_dir = _cli_output_dir("cli_default_index")
    index_path = output_dir / "data" / "reports" / "runs" / "index.json"
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
    monkeypatch.chdir(output_dir)
    monkeypatch.setattr("sys.argv", ["ade", "--list-runs", "--limit", "5"])

    main()

    output = capsys.readouterr().out
    assert "## ADE Run History" in output
    assert "ade_20260618_143100_b22222" in output


def test_format_run_history_rejects_invalid_limit() -> None:
    output_dir = _cli_output_dir("invalid_limit")
    index_path = output_dir / "runs" / "index.json"
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

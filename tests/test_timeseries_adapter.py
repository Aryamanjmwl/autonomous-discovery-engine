import json
from pathlib import Path

import numpy as np
import pytest

from ade.adapters.base import DataAdapter
from ade.adapters.timeseries_adapter import TimeSeriesAdapter
from ade.cli import main, run_pipeline
from ade.dashboard.service import generate_dashboard
from ade.discovery.timeseries import TimeSeriesConceptGrouper, TimeSeriesNoveltyScorer
from ade.representation.timeseries_engine import TimeSeriesFeatureEngine


def _write_timeseries_csv(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "timestamp,machine,temp,pressure",
                "2026-07-07T00:00:00,A,20,100",
                "2026-07-07T00:01:00,A,21,101",
                "2026-07-07T00:02:00,A,85,140",
                "2026-07-07T00:08:00,A,22,102",
                "2026-07-07T00:08:00,A,23,103",
                ",A,24,104",
                "bad-ts,A,25,105",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_timeseries_adapter_profiles_timestamped_csv(tmp_path: Path) -> None:
    csv_path = _write_timeseries_csv(tmp_path / "series.csv")
    adapter = TimeSeriesAdapter(csv_path, entity_column="machine")

    profile = adapter.profile()
    records = adapter.load()

    assert isinstance(adapter, DataAdapter)
    assert profile.is_valid is True
    assert profile.timestamp_column == "timestamp"
    assert profile.entity_column == "machine"
    assert profile.row_count == 5
    assert profile.signal_columns == ["temp", "pressure"]
    assert profile.missing_timestamp_count == 1
    assert profile.malformed_timestamp_count == 1
    assert profile.duplicate_timestamp_count == 1
    assert profile.sampling_interval_summary["irregular"] is True
    assert records[0].to_ade_record().media_type == "timeseries_point"
    assert records[0].timestamp == "2026-07-07T00:00:00"


def test_timeseries_adapter_rejects_missing_timestamp_column(tmp_path: Path) -> None:
    csv_path = tmp_path / "series.csv"
    csv_path.write_text("time,value\n2026-07-07T00:00:00,1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Timestamp column 'timestamp'"):
        TimeSeriesAdapter(csv_path, timestamp_column="timestamp").profile()


def test_timeseries_adapter_rejects_missing_detectable_timestamp(tmp_path: Path) -> None:
    csv_path = tmp_path / "series.csv"
    csv_path.write_text("when,value\n2026-07-07T00:00:00,1\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Could not detect"):
        TimeSeriesAdapter(csv_path).profile()


def test_timeseries_feature_extraction_is_deterministic_and_finite(tmp_path: Path) -> None:
    csv_path = _write_timeseries_csv(tmp_path / "series.csv")
    adapter = TimeSeriesAdapter(csv_path, entity_column="machine")
    profile = adapter.profile()
    records = adapter.load()
    engine = TimeSeriesFeatureEngine(window_size=3)

    first = engine.embed(records, profile)
    second = engine.embed(records, profile)

    assert len(first) == 5
    assert first[0].feature_names == second[0].feature_names
    assert np.allclose(first[2].vector, second[2].vector)
    assert all(np.isfinite(embedding.vector).all() for embedding in first)
    assert "temp:delta_z" in first[0].feature_names
    assert "time:gap_indicator" in first[0].feature_names
    assert first[3].metadata["time_gap_indicator"] == 1.0


def test_timeseries_scoring_ranks_unusual_points_without_nan(tmp_path: Path) -> None:
    csv_path = _write_timeseries_csv(tmp_path / "series.csv")
    adapter = TimeSeriesAdapter(csv_path, entity_column="machine")
    profile = adapter.profile()
    embeddings = TimeSeriesFeatureEngine(window_size=3).embed(adapter.load(), profile)

    findings = TimeSeriesNoveltyScorer().score(embeddings, max_candidates=3)
    concepts = TimeSeriesConceptGrouper(max_concepts=3).group(findings)

    assert len(findings) == 3
    assert findings[0].rank == 1
    assert np.isfinite([finding.novelty_score for finding in findings]).all()
    assert findings[0].reason
    assert findings[0].feature_deviations
    assert any(finding.time_gap_indicator > 0 for finding in findings)
    assert concepts
    assert concepts[0].to_dict()["requires_human_review"] is True


def test_run_pipeline_writes_timeseries_reports(tmp_path: Path) -> None:
    csv_path = _write_timeseries_csv(tmp_path / "series.csv")
    report_path = tmp_path / "timeseries_report.md"

    run_pipeline(
        input_dir=csv_path,
        output_path=report_path,
        max_candidates=3,
        modality="timeseries",
        entity_column="machine",
    )

    markdown = report_path.read_text(encoding="utf-8")
    report_data = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))

    assert "# ADE Time-Series Discovery Report" in markdown
    assert "Modality: `timeseries`" in markdown
    assert "Top Time-Series Findings" in markdown
    assert report_data["modality"] == "timeseries"
    assert report_data["number_of_rows"] == 5
    assert report_data["timeseries_profile"]["signal_column_count"] == 2
    assert report_data["timeseries_profile"]["duplicate_timestamp_count"] == 1
    assert report_data["number_of_candidate_anomalies"] == 3
    assert report_data["candidate_anomalies"][0]["timestamp"]
    assert report_data["candidate_anomalies"][0]["reason"]
    assert report_data["candidate_unknown_concepts"]
    assert report_data["run_metadata"]["modality"] == "timeseries"
    assert (tmp_path / "runs" / "index.json").is_file()


def test_plain_csv_still_defaults_to_tabular(tmp_path: Path) -> None:
    csv_path = _write_timeseries_csv(tmp_path / "series.csv")
    report_path = tmp_path / "tabular_report.md"

    run_pipeline(input_dir=csv_path, output_path=report_path, max_candidates=2)

    report_data = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert report_data["modality"] == "tabular"


def test_cli_runs_timeseries_csv(tmp_path: Path, monkeypatch, capsys) -> None:
    csv_path = _write_timeseries_csv(tmp_path / "series.csv")
    report_path = tmp_path / "timeseries_report.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ade",
            "--input",
            str(csv_path),
            "--output",
            str(report_path),
            "--modality",
            "timeseries",
            "--entity-column",
            "machine",
            "--max-candidates",
            "2",
        ],
    )

    main()

    output = capsys.readouterr().out
    assert "ADE report written to" in output
    report_data = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert report_data["modality"] == "timeseries"
    assert report_data["number_of_candidate_anomalies"] == 2


def test_dashboard_renders_timeseries_run_metadata(tmp_path: Path) -> None:
    csv_path = _write_timeseries_csv(tmp_path / "series.csv")
    report_path = tmp_path / "reports" / "timeseries_report.md"
    run_pipeline(
        input_dir=csv_path,
        output_path=report_path,
        max_candidates=2,
        modality="timeseries",
        entity_column="machine",
    )

    result = generate_dashboard(
        index_path=tmp_path / "reports" / "runs" / "index.json",
        output_dir=tmp_path / "dashboard",
    )
    run_files = list((result.output_dir / "runs").glob("*.html"))
    detail_html = run_files[0].read_text(encoding="utf-8")

    assert result.run_count == 1
    assert "timeseries" in detail_html
    assert "Timestamp column" in detail_html
    assert "Top Findings" in detail_html

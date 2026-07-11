import json
from pathlib import Path

import numpy as np
import pytest

from ade.adapters.base import DataAdapter
from ade.adapters.tabular_adapter import TabularAdapter
from ade.cli import main, run_pipeline
from ade.discovery.tabular import TabularConceptGrouper, TabularNoveltyScorer
from ade.representation.tabular_engine import TabularFeatureEngine


def _write_csv(path: Path) -> Path:
    path.write_text(
        "\n".join(
            [
                "id,amount,status,region,notes",
                "1,10,ok,north,complete",
                "2,11,ok,north,complete",
                "3,1000,review,south,",
                "4,9,ok,north,complete",
            ]
        ),
        encoding="utf-8",
    )
    return path


def test_tabular_adapter_profiles_mixed_csv(tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path / "sample.csv")
    adapter = TabularAdapter(csv_path)

    profile = adapter.profile()
    records = adapter.load()

    assert isinstance(adapter, DataAdapter)
    assert profile.is_valid is True
    assert profile.row_count == 4
    assert profile.column_count == 5
    assert profile.numeric_columns == ["id", "amount"]
    assert profile.categorical_columns == ["status", "region", "notes"]
    assert profile.missing_value_summary["notes"] == 1
    assert records[2].row_index == 3
    assert records[2].values["amount"] == "1000"
    assert records[2].to_ade_record().media_type == "tabular_row"


def test_tabular_adapter_rejects_empty_csv(tmp_path: Path) -> None:
    csv_path = tmp_path / "empty.csv"
    csv_path.write_text("", encoding="utf-8")

    with pytest.raises(ValueError, match="empty"):
        TabularAdapter(csv_path).profile()


def test_tabular_adapter_records_malformed_row_warning(tmp_path: Path) -> None:
    csv_path = tmp_path / "malformed.csv"
    csv_path.write_text("a,b\n1,2,3\n4,5\n", encoding="utf-8")

    profile = TabularAdapter(csv_path).profile()

    assert profile.is_valid is True
    assert any("more fields than the header" in warning for warning in profile.warnings)


def test_tabular_feature_extraction_is_deterministic_and_finite(tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path / "sample.csv")
    adapter = TabularAdapter(csv_path)
    records = adapter.load()
    profile = adapter.profile()
    engine = TabularFeatureEngine()

    first = engine.embed(records, profile)
    second = engine.embed(records, profile)

    assert len(first) == 4
    assert first[0].feature_names == second[0].feature_names
    assert first[0].vector.shape == second[0].vector.shape
    assert np.allclose(first[0].vector, second[0].vector)
    assert all(np.isfinite(embedding.vector).all() for embedding in first)
    assert "amount:numeric_z" in first[0].feature_names
    assert "notes:missing" in first[0].feature_names


def test_tabular_scoring_ranks_unusual_rows_without_nan(tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path / "sample.csv")
    adapter = TabularAdapter(csv_path)
    profile = adapter.profile()
    embeddings = TabularFeatureEngine().embed(adapter.load(), profile)

    findings = TabularNoveltyScorer().score(embeddings, max_candidates=2)
    concepts = TabularConceptGrouper(max_concepts=3).group(findings)

    assert len(findings) == 2
    assert findings[0].rank == 1
    assert findings[0].row_index == 3
    assert np.isfinite([finding.novelty_score for finding in findings]).all()
    assert findings[0].reason
    assert findings[0].feature_deviations
    assert concepts
    assert concepts[0].to_dict()["requires_human_review"] is True


def test_run_pipeline_writes_tabular_reports(tmp_path: Path) -> None:
    csv_path = _write_csv(tmp_path / "sample.csv")
    report_path = tmp_path / "tabular_report.md"

    run_pipeline(input_dir=csv_path, output_path=report_path, max_candidates=3)

    markdown = report_path.read_text(encoding="utf-8")
    report_data = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))

    assert "# ADE Tabular Discovery Report" in markdown
    assert "Modality: `tabular`" in markdown
    assert "Top Row-Level Findings" in markdown
    assert report_data["modality"] == "tabular"
    assert report_data["number_of_rows"] == 4
    assert report_data["number_of_columns"] == 5
    assert report_data["tabular_profile"]["numeric_column_count"] == 2
    assert report_data["number_of_candidate_anomalies"] == 3
    assert report_data["candidate_anomalies"][0]["row_index"] == 3
    assert report_data["candidate_anomalies"][0]["reason"]
    assert report_data["candidate_unknown_concepts"]
    assert report_data["run_metadata"]["modality"] == "tabular"
    assert (tmp_path / "runs" / "index.json").is_file()


def test_cli_runs_tabular_csv(tmp_path: Path, monkeypatch, capsys) -> None:
    csv_path = _write_csv(tmp_path / "sample.csv")
    report_path = tmp_path / "tabular_report.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ade",
            "--input",
            str(csv_path),
            "--output",
            str(report_path),
            "--max-candidates",
            "2",
        ],
    )

    main()

    output = capsys.readouterr().out
    assert "ADE report written to" in output
    assert report_path.is_file()
    report_data = json.loads(report_path.with_suffix(".json").read_text(encoding="utf-8"))
    assert report_data["modality"] == "tabular"
    assert report_data["number_of_candidate_anomalies"] == 2

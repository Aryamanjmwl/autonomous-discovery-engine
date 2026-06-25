import json
from pathlib import Path
import re

import numpy as np

from ade.discovery.confidence_scorer import ConceptConfidence
from ade.discovery.evidence_collector import ConceptEvidence, EvidenceItem
from ade.discovery.novelty_scorer import CandidateAnomaly
from ade.models import DatasetProfile
from ade.preprocessing.patch_extractor import Patch
from ade.reasoning.hypothesis_generator import Hypothesis
from ade.reporting.report_generator import DatasetSummary, ReportGenerator
from ade.reporting.run_index import build_run_summary, update_run_index
from ade.representation.embedding_engine import PatchEmbedding


def _candidate_patch() -> tuple[Patch, CandidateAnomaly]:
    patch = Patch(
        source_path=Path("image.png"),
        array=np.full((4, 4, 3), 128, dtype=np.uint8),
        x=1,
        y=2,
        width=4,
        height=4,
    )
    candidate = CandidateAnomaly(
        embedding=PatchEmbedding(patch=patch, vector=np.zeros(8, dtype=np.float32)),
        novelty_score=0.42,
    )
    return patch, candidate


def _concept_evidence() -> ConceptEvidence:
    return ConceptEvidence(
        concept_id="concept-001",
        examples=[EvidenceItem(source_path=Path("image.png"), coordinates=(1, 2, 4, 4), novelty_score=0.42)],
        example_count=1,
        average_novelty=0.42,
        consistency=1.0,
    )


def _dataset_profile() -> DatasetProfile:
    return DatasetProfile(
        input_path=Path("data/raw"),
        input_type="image_folder",
        total_files=2,
        supported_image_files=1,
        unsupported_files=[Path("data/raw/notes.txt")],
        unreadable_files=[],
        valid_images=1,
        image_width_min=4,
        image_width_max=4,
        image_height_min=4,
        image_height_max=4,
        unique_image_sizes=[(4, 4)],
        estimated_patch_count=1,
        warnings=["Unsupported files found: 1"],
        is_valid=True,
    )


def _write_sample_report(output_path: Path) -> None:
    _, candidate = _candidate_patch()
    evidence = _concept_evidence()
    ReportGenerator().write(
        output_path=output_path,
        dataset_summary=DatasetSummary(input_dir=Path("data/raw"), image_count=1, patch_count=1),
        candidates=[candidate],
        evidence_items=[evidence],
        confidences=[ConceptConfidence(concept_id="concept-001", score=0.7)],
        hypotheses=[Hypothesis(concept_id="concept-001", text="A cautious hypothesis.")],
        dataset_profile=_dataset_profile(),
    )


def test_report_generator_includes_required_sections() -> None:
    _, candidate = _candidate_patch()
    evidence = _concept_evidence()

    report = ReportGenerator().generate(
        dataset_summary=DatasetSummary(input_dir=Path("data/raw"), image_count=1, patch_count=1),
        candidates=[candidate],
        evidence_items=[evidence],
        confidences=[ConceptConfidence(concept_id="concept-001", score=0.7)],
        hypotheses=[Hypothesis(concept_id="concept-001", text="A cautious hypothesis.")],
        dataset_profile=_dataset_profile(),
    )

    assert "# ADE Discovery Report" in report
    assert "Number of input images: 1" in report
    assert "Number of extracted patches: 1" in report
    assert "Number of candidate anomalies: 1" in report
    assert "Number of candidate unknown concepts: 1" in report
    assert "Top Candidate Anomalies" in report
    assert "Input Dataset Profile" in report
    assert "Unsupported files found: 1" in report
    assert "Candidate Unknown Concepts" in report
    assert "Human Expert Review Required" in report
    assert "A cautious hypothesis." in report


def test_report_generator_includes_image_links_when_assets_are_saved(tmp_path: Path) -> None:
    output_path = tmp_path / "demo_report.md"

    _write_sample_report(output_path)

    report = output_path.read_text(encoding="utf-8")
    assert "![candidate anomaly 1](assets/anomaly_0001.png)" in report
    assert "![concept-001 example 1](assets/concept_001_example_001.png)" in report
    assert output_path.with_suffix(".json").is_file()


def test_report_generator_writes_structured_json_report(tmp_path: Path) -> None:
    output_path = tmp_path / "demo_report.md"

    _write_sample_report(output_path)

    json_path = output_path.with_suffix(".json")
    report_data = json.loads(json_path.read_text(encoding="utf-8"))

    expected_keys = {
        "project_name",
        "report_version",
        "run_id",
        "run_metadata",
        "run_index_path",
        "generated_at",
        "input_summary",
        "dataset_profile",
        "number_of_images",
        "number_of_patches",
        "number_of_candidate_anomalies",
        "number_of_candidate_unknown_concepts",
        "candidate_anomalies",
        "candidate_unknown_concepts",
        "evidence_summary",
        "confidence_scores",
        "hypotheses",
        "human_review_required",
        "limitations",
    }
    assert expected_keys.issubset(report_data)
    assert report_data["number_of_images"] == 1
    assert report_data["number_of_patches"] == 1
    assert report_data["number_of_candidate_anomalies"] == 1
    assert report_data["number_of_candidate_unknown_concepts"] == 1
    assert report_data["human_review_required"] is True
    assert report_data["dataset_profile"]["input_type"] == "image_folder"
    assert report_data["dataset_profile"]["unsupported_file_count"] == 1
    assert report_data["candidate_anomalies"][0]["preview_path"] == "assets/anomaly_0001.png"
    assert report_data["candidate_unknown_concepts"][0]["confidence_score"] == 0.7


def test_report_generator_tracks_run_metadata(tmp_path: Path) -> None:
    output_path = tmp_path / "demo_report.md"

    _write_sample_report(output_path)

    markdown = output_path.read_text(encoding="utf-8")
    json_report = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    run_id = json_report["run_id"]
    run_metadata = json_report["run_metadata"]
    metadata_path = tmp_path / "runs" / f"{run_id}.json"
    index_path = tmp_path / "runs" / "index.json"
    saved_metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
    run_index = json.loads(index_path.read_text(encoding="utf-8"))

    assert re.fullmatch(r"ade_\d{8}_\d{6}_[a-f0-9]{6}", run_id)
    assert f"**Run ID:** `{run_id}`" in markdown
    assert metadata_path.is_file()
    assert index_path.is_file()
    assert saved_metadata == run_metadata
    assert run_metadata["run_id"] == run_id
    assert run_metadata["input_path"] == "data/raw"
    assert run_metadata["markdown_report_path"] == output_path.as_posix()
    assert run_metadata["json_report_path"] == output_path.with_suffix(".json").as_posix()
    assert run_metadata["run_index_path"] == index_path.as_posix()
    assert run_metadata["number_of_images"] == 1
    assert run_metadata["number_of_patches"] == 1
    assert run_metadata["number_of_candidate_anomalies"] == 1
    assert run_metadata["number_of_candidate_unknown_concepts"] == 1
    assert run_metadata["number_of_input_files"] == 2
    assert run_metadata["number_of_valid_images"] == 1
    assert run_metadata["number_of_unsupported_files"] == 1
    assert run_metadata["number_of_unreadable_files"] == 0
    assert run_metadata["estimated_patch_count"] == 1
    assert run_metadata["input_warnings"] == ["Unsupported files found: 1"]
    assert run_metadata["pipeline_version"]
    assert run_metadata["human_review_required"] is True
    assert json_report["human_review_required"] is True
    assert json_report["run_index_path"] == index_path.as_posix()
    assert run_index["index_version"] == "1.0"
    assert isinstance(run_index["runs"], list)
    assert run_index["runs"][-1]["run_id"] == run_id
    assert run_index["runs"][-1]["human_review_required"] is True


def test_report_generator_generates_run_id() -> None:
    run_id = ReportGenerator.generate_run_id()

    assert re.fullmatch(r"ade_\d{8}_\d{6}_[a-f0-9]{6}", run_id)


def test_run_index_appends_and_avoids_duplicate_run_ids(tmp_path: Path) -> None:
    index_path = tmp_path / "runs" / "index.json"
    first_metadata = {
        "run_id": "ade_20260618_143022_a7f3c9",
        "generated_at": "2026-06-18T14:30:22+00:00",
        "input_path": "data/raw/demo_images",
        "markdown_report_path": "data/reports/demo_report.md",
        "json_report_path": "data/reports/demo_report.json",
        "run_index_path": index_path.as_posix(),
        "number_of_images": 6,
        "number_of_patches": 96,
        "number_of_candidate_anomalies": 10,
        "number_of_candidate_unknown_concepts": 3,
        "pipeline_version": "0.1.0",
        "human_review_required": True,
    }
    second_metadata = {
        **first_metadata,
        "run_id": "ade_20260618_143123_b8e4d1",
        "generated_at": "2026-06-18T14:31:23+00:00",
    }

    first_summary = build_run_summary(
        first_metadata,
        tmp_path / "runs" / f"{first_metadata['run_id']}.json",
    )
    second_summary = build_run_summary(
        second_metadata,
        tmp_path / "runs" / f"{second_metadata['run_id']}.json",
    )

    update_run_index(index_path, first_summary)
    update_run_index(index_path, second_summary)
    update_run_index(index_path, first_summary)

    run_index = json.loads(index_path.read_text(encoding="utf-8"))
    run_ids = [run["run_id"] for run in run_index["runs"]]

    assert run_index["index_version"] == "1.0"
    assert len(run_index["runs"]) == 2
    assert run_ids == [
        "ade_20260618_143123_b8e4d1",
        "ade_20260618_143022_a7f3c9",
    ]
    assert run_index["runs"][-1]["human_review_required"] is True
    assert run_index["runs"][-1]["run_metadata_path"].endswith(
        "ade_20260618_143022_a7f3c9.json"
    )


def test_report_generator_creates_assets_and_saves_patch_images(tmp_path: Path) -> None:
    _, candidate = _candidate_patch()
    evidence = _concept_evidence()
    output_path = tmp_path / "demo_report.md"

    assets = ReportGenerator().save_assets(
        output_path=output_path,
        candidates=[candidate],
        evidence_items=[evidence],
    )

    assert (tmp_path / "assets").is_dir()
    assert (tmp_path / "assets" / "anomaly_0001.png").is_file()
    assert (tmp_path / "assets" / "concept_001_example_001.png").is_file()
    assert assets.anomaly_previews[1] == "assets/anomaly_0001.png"
    assert assets.concept_previews[("concept-001", 1)] == "assets/concept_001_example_001.png"

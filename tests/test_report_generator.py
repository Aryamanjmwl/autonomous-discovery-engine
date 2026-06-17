import json
from pathlib import Path

import numpy as np

from ade.discovery.confidence_scorer import ConceptConfidence
from ade.discovery.evidence_collector import ConceptEvidence, EvidenceItem
from ade.discovery.novelty_scorer import CandidateAnomaly
from ade.preprocessing.patch_extractor import Patch
from ade.reasoning.hypothesis_generator import Hypothesis
from ade.reporting.report_generator import DatasetSummary, ReportGenerator
from ade.representation.embedding_engine import PatchEmbedding


def _test_output_dir() -> Path:
    output_dir = Path("tests/.tmp_report_assets")
    output_dir.mkdir(parents=True, exist_ok=True)
    for path in output_dir.rglob("*"):
        if path.is_file():
            path.unlink()
    return output_dir


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


def test_report_generator_includes_required_sections() -> None:
    _, candidate = _candidate_patch()
    evidence = ConceptEvidence(
        concept_id="concept-001",
        examples=[EvidenceItem(source_path=Path("image.png"), coordinates=(1, 2, 4, 4), novelty_score=0.42)],
        example_count=1,
        average_novelty=0.42,
        consistency=1.0,
    )

    report = ReportGenerator().generate(
        dataset_summary=DatasetSummary(input_dir=Path("data/raw"), image_count=1, patch_count=1),
        candidates=[candidate],
        evidence_items=[evidence],
        confidences=[ConceptConfidence(concept_id="concept-001", score=0.7)],
        hypotheses=[Hypothesis(concept_id="concept-001", text="A cautious hypothesis.")],
    )

    assert "# ADE Discovery Report" in report
    assert "Number of input images: 1" in report
    assert "Number of extracted patches: 1" in report
    assert "Number of candidate anomalies: 1" in report
    assert "Number of candidate unknown concepts: 1" in report
    assert "Top Candidate Anomalies" in report
    assert "Candidate Unknown Concepts" in report
    assert "Human Expert Review Required" in report
    assert "A cautious hypothesis." in report


def test_report_generator_includes_image_links_when_assets_are_saved() -> None:
    _, candidate = _candidate_patch()
    evidence = ConceptEvidence(
        concept_id="concept-001",
        examples=[EvidenceItem(source_path=Path("image.png"), coordinates=(1, 2, 4, 4), novelty_score=0.42)],
        example_count=1,
        average_novelty=0.42,
        consistency=1.0,
    )
    output_path = _test_output_dir() / "demo_report.md"

    ReportGenerator().write(
        output_path=output_path,
        dataset_summary=DatasetSummary(input_dir=Path("data/raw"), image_count=1, patch_count=1),
        candidates=[candidate],
        evidence_items=[evidence],
        confidences=[ConceptConfidence(concept_id="concept-001", score=0.7)],
        hypotheses=[Hypothesis(concept_id="concept-001", text="A cautious hypothesis.")],
    )

    report = output_path.read_text(encoding="utf-8")
    assert "![candidate anomaly 1](assets/anomaly_0001.png)" in report
    assert "![concept-001 example 1](assets/concept_001_example_001.png)" in report
    assert output_path.with_suffix(".json").is_file()


def test_report_generator_writes_structured_json_report() -> None:
    _, candidate = _candidate_patch()
    evidence = ConceptEvidence(
        concept_id="concept-001",
        examples=[EvidenceItem(source_path=Path("image.png"), coordinates=(1, 2, 4, 4), novelty_score=0.42)],
        example_count=1,
        average_novelty=0.42,
        consistency=1.0,
    )
    output_path = _test_output_dir() / "demo_report.md"

    ReportGenerator().write(
        output_path=output_path,
        dataset_summary=DatasetSummary(input_dir=Path("data/raw"), image_count=1, patch_count=1),
        candidates=[candidate],
        evidence_items=[evidence],
        confidences=[ConceptConfidence(concept_id="concept-001", score=0.7)],
        hypotheses=[Hypothesis(concept_id="concept-001", text="A cautious hypothesis.")],
    )

    json_path = output_path.with_suffix(".json")
    report_data = json.loads(json_path.read_text(encoding="utf-8"))

    expected_keys = {
        "project_name",
        "report_version",
        "generated_at",
        "input_summary",
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
    assert report_data["candidate_anomalies"][0]["preview_path"] == "assets/anomaly_0001.png"
    assert report_data["candidate_unknown_concepts"][0]["confidence_score"] == 0.7


def test_report_generator_creates_assets_and_saves_patch_images() -> None:
    _, candidate = _candidate_patch()
    evidence = ConceptEvidence(
        concept_id="concept-001",
        examples=[EvidenceItem(source_path=Path("image.png"), coordinates=(1, 2, 4, 4), novelty_score=0.42)],
        example_count=1,
        average_novelty=0.42,
        consistency=1.0,
    )
    output_dir = _test_output_dir()
    output_path = output_dir / "demo_report.md"

    assets = ReportGenerator().save_assets(
        output_path=output_path,
        candidates=[candidate],
        evidence_items=[evidence],
    )

    assert (output_dir / "assets").is_dir()
    assert (output_dir / "assets" / "anomaly_0001.png").is_file()
    assert (output_dir / "assets" / "concept_001_example_001.png").is_file()
    assert assets.anomaly_previews[1] == "assets/anomaly_0001.png"
    assert assets.concept_previews[("concept-001", 1)] == "assets/concept_001_example_001.png"

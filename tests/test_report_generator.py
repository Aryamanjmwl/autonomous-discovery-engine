import json
import re
from pathlib import Path

import numpy as np

from ade.discovery.confidence_scorer import ConceptConfidence
from ade.discovery.evidence_collector import ConceptEvidence, EvidenceItem
from ade.discovery.novelty_scorer import CandidateAnomaly
from ade.feedback import ReviewFeedback
from ade.memory.review_memory import build_review_memory_summary
from ade.models import DatasetProfile
from ade.preprocessing.patch_extractor import Patch
from ade.reasoning.hypothesis_generator import Hypothesis
from ade.reporting.html_report import render_html_report
from ade.reporting.report_generator import DatasetSummary, ReportGenerator
from ade.reporting.report_validator import validate_report_file
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
        patch_id="image_s4_stride4_x1_y2",
        metadata={
            "patch_size": 4,
            "patch_stride": 4,
            "scale_id": "scale-1",
            "scale_label": "s4",
        },
    )
    candidate = CandidateAnomaly(
        embedding=PatchEmbedding(
            patch=patch,
            vector=np.zeros(8, dtype=np.float32),
            metadata={
                "backend_name": "statistical_visual_v2",
                "feature_count": 8,
                "feature_names": [f"feature_{index}" for index in range(8)],
            },
        ),
        novelty_score=0.42,
        metadata={
            "selection_reason": "diversity selected",
            "selection_rank": 1,
            "score_breakdown": {
                "global_distance_score": 0.3,
                "neighbor_distance_score": 0.5,
                "hybrid_score": 0.4,
                "strategy": "hybrid",
                "nearest_neighbor_count": 2,
            },
        },
    )
    return patch, candidate


def _concept_evidence() -> ConceptEvidence:
    return ConceptEvidence(
        concept_id="concept-001",
        examples=[
            EvidenceItem(
                source_path=Path("image.png"),
                coordinates=(1, 2, 4, 4),
                novelty_score=0.42,
                anomaly_id="anomaly-0001",
                rank=1,
                concept_id="concept-001",
                patch_stride=4,
                scale_id="scale-1",
                scale_label="s4",
            )
        ],
        example_count=1,
        average_novelty=0.42,
        consistency=1.0,
        representative_anomaly_id="anomaly-0001",
        item_count=1,
        source_image_count=1,
        diversity_score=1.0,
        confidence_breakdown={
            "novelty_strength": 0.42,
            "support_count": 0.2,
            "consistency": 1.0,
            "source_diversity": 1.0,
            "data_quality": 1.0,
            "final_confidence": 0.68,
        },
        confidence_score=0.68,
        evidence_summary={
            "supporting_examples": [
                {
                    "anomaly_id": "anomaly-0001",
                    "source_path": "image.png",
                    "x": 1,
                    "y": 2,
                    "width": 4,
                    "height": 4,
                    "patch_size": 4,
                    "patch_stride": 4,
                    "scale_id": "scale-1",
                    "scale_label": "s4",
                    "novelty_score": 0.42,
                    "rank": 1,
                    "concept_id": "concept-001",
                    "preview_path": None,
                }
            ],
            "representative_examples": [
                {
                    "anomaly_id": "anomaly-0001",
                    "source_path": "image.png",
                    "x": 1,
                    "y": 2,
                    "width": 4,
                    "height": 4,
                    "patch_size": 4,
                    "patch_stride": 4,
                    "scale_id": "scale-1",
                    "scale_label": "s4",
                    "novelty_score": 0.42,
                    "rank": 1,
                    "concept_id": "concept-001",
                    "preview_path": None,
                }
            ],
            "near_matches": [],
            "nearest_neighbors": [
                {
                    "item_id": "image_0_0_4_4",
                    "distance": 0.1,
                    "similarity": 0.9,
                    "rank": 1,
                    "metadata": {
                        "source_path": "image.png",
                        "x": 0,
                        "y": 0,
                        "width": 4,
                        "height": 4,
                    },
                    "query_anomaly_id": "anomaly-0001",
                    "query_patch_id": "image_1_2_4_4",
                }
            ],
            "normal_comparisons": [],
            "notes": ["Candidate concept is based on similar anomaly embeddings."],
            "warnings": [],
        },
        summary="Single candidate anomaly retained for human review.",
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
        memory_metadata={
            "enabled": True,
            "metric": "euclidean",
            "items_indexed": 3,
        },
        analysis_metadata={
            "total_patches": 1,
            "patch_scales_used": ["s4"],
            "anomaly_selection_strategy": "diversity-aware",
            "novelty_strategy": "hybrid",
            "memory_aware_scoring_enabled": True,
            "neighbor_top_k": 5,
            "scoring_fallback_used": False,
            "scoring_fallback_reason": None,
        },
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
        analysis_metadata={
            "total_patches": 1,
            "patch_scales_used": ["s4"],
            "anomaly_selection_strategy": "diversity-aware",
            "novelty_strategy": "hybrid",
            "memory_aware_scoring_enabled": True,
            "neighbor_top_k": 5,
            "scoring_fallback_used": False,
            "scoring_fallback_reason": None,
        },
    )

    assert "# ADE Discovery Report" in report
    assert "Number of input images: 1" in report
    assert "Number of extracted patches: 1" in report
    assert "Number of candidate anomalies: 1" in report
    assert "Number of candidate unknown concepts: 1" in report
    assert "Novelty scoring strategy: `hybrid`" in report
    assert "Top Candidate Anomalies" in report
    assert "Patch scale" in report
    assert "`s4` / 4px" in report
    assert "Input Dataset Profile" in report
    assert "Scoring Metadata" in report
    assert "Novelty strategy: `hybrid`" in report
    assert "Unsupported files found: 1" in report
    assert "Candidate Unknown Concepts" in report
    assert "Representative anomaly: anomaly-0001" in report
    assert "Consistency score: 1.0000" in report
    assert "Confidence breakdown:" in report
    assert "Evidence bundle for this candidate concept" in report
    assert "Nearest visual matches:" in report
    assert "`image_0_0_4_4`" in report
    assert "Human Review Feedback" in report
    assert "--add-feedback" in report
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
        "scoring_metadata",
        "review_memory_summary",
        "number_of_images",
        "number_of_patches",
        "number_of_candidate_anomalies",
        "number_of_candidate_unknown_concepts",
        "top_discoveries",
        "candidate_anomalies",
        "candidate_unknown_concepts",
        "candidate_concepts",
        "evidence_summary",
        "confidence_scores",
        "hypotheses",
        "human_review_required",
        "feedback_supported",
        "supported_feedback_labels",
        "feedback_store_path",
        "limitations",
    }
    assert expected_keys.issubset(report_data)
    assert report_data["number_of_images"] == 1
    assert report_data["number_of_patches"] == 1
    assert report_data["number_of_candidate_anomalies"] == 1
    assert report_data["number_of_candidate_unknown_concepts"] == 1
    assert report_data["human_review_required"] is True
    assert report_data["feedback_supported"] is True
    assert "interesting" in report_data["supported_feedback_labels"]
    assert report_data["feedback_store_path"] == "data/feedback/feedback.jsonl"
    assert report_data["review_memory_summary"] is None
    assert report_data["candidate_concepts"] == report_data["candidate_unknown_concepts"]
    assert report_data["dataset_profile"]["input_type"] == "image_folder"
    assert report_data["dataset_profile"]["unsupported_file_count"] == 1
    assert report_data["scoring_metadata"]["novelty_strategy"] == "hybrid"
    assert report_data["scoring_metadata"]["neighbor_top_k"] == 5
    assert report_data["candidate_anomalies"][0]["preview_path"] == "assets/anomaly_0001.png"
    assert report_data["candidate_anomalies"][0]["patch_size"] == 4
    assert report_data["candidate_anomalies"][0]["patch_stride"] == 4
    assert report_data["candidate_anomalies"][0]["scale_label"] == "s4"
    assert report_data["candidate_anomalies"][0]["selection_reason"] == "diversity selected"
    assert report_data["candidate_anomalies"][0]["score_breakdown"]["strategy"] == "hybrid"
    assert report_data["candidate_anomalies"][0]["score_breakdown"]["hybrid_score"] == 0.4
    concept = report_data["candidate_unknown_concepts"][0]
    assert concept["confidence_score"] == 0.7
    assert concept["representative_anomaly_id"] == "anomaly-0001"
    assert concept["consistency_score"] == 1.0
    assert concept["confidence_breakdown"]["final_confidence"] == 0.68
    assert concept["evidence_summary"]["supporting_examples"][0]["anomaly_id"] == "anomaly-0001"
    assert concept["evidence_summary"]["representative_examples"][0]["patch_size"] == 4
    assert concept["evidence_summary"]["nearest_neighbors"][0]["item_id"] == "image_0_0_4_4"
    assert report_data["evidence_summary"][0]["confidence_breakdown"]["final_confidence"] == 0.68


def test_report_generator_validates_with_no_review_memory_feedback(tmp_path: Path) -> None:
    output_path = tmp_path / "demo_report.md"

    _write_sample_report(output_path)

    result = validate_report_file(output_path.with_suffix(".json"))

    assert result.is_valid is True
    assert result.errors == []


def test_report_generator_includes_review_memory_when_feedback_exists(
    tmp_path: Path,
) -> None:
    _, candidate = _candidate_patch()
    evidence = _concept_evidence()
    summary = build_review_memory_summary(
        [
            ReviewFeedback.create(
                run_id="ade_20260709_120000_abcdef",
                report_path=tmp_path / "report.json",
                target_type="anomaly",
                target_id="anomaly-0001",
                label="important",
            ),
            ReviewFeedback.create(
                run_id="ade_20260709_120000_abcdef",
                report_path=tmp_path / "report.json",
                target_type="concept",
                target_id="concept-001",
                label="known_pattern",
            ),
        ]
    )
    output_path = tmp_path / "demo_report.md"

    ReportGenerator().write(
        output_path=output_path,
        dataset_summary=DatasetSummary(input_dir=Path("data/raw"), image_count=1, patch_count=1),
        candidates=[candidate],
        evidence_items=[evidence],
        confidences=[ConceptConfidence(concept_id="concept-001", score=0.7)],
        hypotheses=[Hypothesis(concept_id="concept-001", text="A cautious hypothesis.")],
        dataset_profile=_dataset_profile(),
        review_memory_summary=summary,
    )

    markdown = output_path.read_text(encoding="utf-8")
    report_data = json.loads(output_path.with_suffix(".json").read_text(encoding="utf-8"))
    anomaly_signal = report_data["candidate_anomalies"][0]["review_memory_signal"]
    concept_signal = report_data["candidate_unknown_concepts"][0]["review_memory_signal"]

    assert "Review Memory" in markdown
    assert "Review-memory signals summarize local human-review feedback" in markdown
    assert report_data["review_memory_summary"]["total_feedback_count"] == 2
    assert anomaly_signal["priority_delta"] == 1.0
    assert anomaly_signal["positive_feedback_count"] == 1
    assert concept_signal["known_pattern_count"] == 1
    assert validate_report_file(output_path.with_suffix(".json")).is_valid is True


def test_html_report_renders_review_memory_signals(tmp_path: Path) -> None:
    summary = build_review_memory_summary(
        [
            ReviewFeedback.create(
                run_id="run",
                report_path=tmp_path / "report.json",
                target_type="anomaly",
                target_id="anomaly-0001",
                label="important",
            )
        ]
    )
    report = {
        "run_id": "run",
        "review_memory_summary": summary.to_dict(),
        "candidate_anomalies": [
            {
                "anomaly_id": "anomaly-0001",
                "novelty_score": 0.42,
                "source_path": "image.png",
                "review_memory_signal": {
                    "priority_delta": 1.0,
                    "matched_feedback_count": 1,
                    "positive_feedback_count": 1,
                    "negative_feedback_count": 0,
                    "known_pattern_count": 0,
                    "duplicate_count": 0,
                    "needs_more_data_count": 0,
                    "notes": ["Prior feedback marked this target as important."],
                    "explanation": "transparent",
                },
            }
        ],
        "candidate_unknown_concepts": [],
    }

    html = render_html_report(report)

    assert "Review Memory" in html
    assert "feedback-informed ranking support" in html
    assert "delta +1.00" in html


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
    assert run_metadata["average_concept_confidence"] == 0.68
    assert run_metadata["average_concept_consistency"] == 1.0
    assert run_metadata["memory_enabled"] is True
    assert run_metadata["memory_metric"] == "euclidean"
    assert run_metadata["memory_items_indexed"] == 3
    assert run_metadata["total_patches"] == 1
    assert run_metadata["patch_scales_used"] == ["s4"]
    assert run_metadata["anomaly_selection_strategy"] == "diversity-aware"
    assert run_metadata["novelty_strategy"] == "hybrid"
    assert run_metadata["memory_aware_scoring_enabled"] is True
    assert run_metadata["neighbor_top_k"] == 5
    assert run_metadata["scoring_fallback_used"] is False
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

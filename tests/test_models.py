from pathlib import Path

import numpy as np

from ade.models import (
    CandidateAnomaly,
    EmbeddingRecord,
    EvidenceSummary,
    ImageRecord,
    PatchRecord,
    RunMetadata,
    UnknownConcept,
)


def test_image_record_serializes_json_safe_metadata() -> None:
    record = ImageRecord(
        image_id="demo",
        path=Path("data/raw/demo_images/demo.png"),
        width=np.int64(256),
        height=np.int64(128),
        metadata={"mode": "RGB", "format": "PNG", "score": np.float32(0.5)},
    )

    data = record.to_dict()

    assert data["image_id"] == "demo"
    assert data["path"] == "data/raw/demo_images/demo.png"
    assert data["width"] == 256
    assert data["height"] == 128
    assert data["metadata"]["score"] == 0.5


def test_patch_and_embedding_serialization_do_not_dump_arrays() -> None:
    patch = PatchRecord(
        patch_id="patch-1",
        image_id="image-1",
        source_path=Path("data/raw/demo_images/image.png"),
        array=np.zeros((2, 2, 3), dtype=np.uint8),
        x=1,
        y=2,
        width=2,
        height=2,
    )
    embedding = EmbeddingRecord(
        patch=patch,
        vector=np.array([0.1, 0.2, 0.3], dtype=np.float32),
    )

    patch_data = patch.to_dict()
    embedding_data = embedding.to_dict()

    assert "array" not in patch_data
    assert patch_data["source_path"] == "data/raw/demo_images/image.png"
    assert patch_data["x"] == 1
    assert patch_data["y"] == 2
    assert embedding_data == {
        "patch_id": "patch-1",
        "vector_length": 3,
        "metadata": {},
    }


def test_candidate_anomaly_serialization_is_json_safe() -> None:
    patch = PatchRecord(
        patch_id="patch-1",
        source_path=Path("data/raw/demo_images/image.png"),
        array=np.zeros((2, 2, 3), dtype=np.uint8),
        x=0,
        y=0,
        width=2,
        height=2,
    )
    embedding = EmbeddingRecord(
        patch=patch,
        vector=np.array([1.0, 2.0], dtype=np.float32),
    )
    anomaly = CandidateAnomaly(
        anomaly_id="anomaly-0001",
        embedding=embedding,
        novelty_score=np.float64(1.25),
        preview_path="assets/anomaly_0001.png",
    )

    data = anomaly.to_dict()

    assert data["anomaly_id"] == "anomaly-0001"
    assert data["patch_id"] == "patch-1"
    assert data["source_path"] == "data/raw/demo_images/image.png"
    assert data["novelty_score"] == 1.25
    assert data["preview_path"] == "assets/anomaly_0001.png"
    assert "vector" not in data


def test_unknown_concept_serialization_is_json_safe() -> None:
    evidence = EvidenceSummary(
        supporting_examples=["anomaly-0001"],
        contradicting_examples=[],
        notes=["requires human review"],
    )
    concept = UnknownConcept(
        concept_id="concept-1",
        anomaly_ids=["anomaly-0001"],
        representative_anomaly_id="anomaly-0001",
        average_novelty_score=np.float64(2.5),
        confidence_score=np.float32(0.75),
        evidence=evidence,
    )

    data = concept.to_dict()

    assert data["concept_id"] == "concept-1"
    assert data["average_novelty_score"] == 2.5
    assert data["confidence_score"] == 0.75
    assert data["evidence"]["notes"] == ["requires human review"]


def test_run_metadata_round_trip_serialization() -> None:
    metadata = RunMetadata(
        run_id="ade_20260618_143022_a7f3c9",
        generated_at="2026-06-18T14:30:22+00:00",
        input_path=Path("data/raw/demo_images"),
        markdown_report_path=Path("data/reports/demo_report.md"),
        json_report_path=Path("data/reports/demo_report.json"),
        run_index_path=Path("data/reports/runs/index.json"),
        number_of_images=6,
        number_of_patches=96,
        number_of_candidate_anomalies=10,
        number_of_candidate_unknown_concepts=3,
        pipeline_version="0.1.0",
        human_review_required=True,
    )

    data = metadata.to_dict()
    restored = RunMetadata.from_dict(data)

    assert data["input_path"] == "data/raw/demo_images"
    assert data["run_index_path"] == "data/reports/runs/index.json"
    assert restored == metadata

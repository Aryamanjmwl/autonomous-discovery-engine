from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ade.models import EmbeddingRecord, ImageRecord, PatchRecord
from ade.visual import (
    ReferenceVectorRecord,
    VisualConfigurationError,
    VisualDatasetRole,
    VisualEngineConfig,
    build_reference_memory,
)
from ade.visual.reference_pipeline import (
    publish_reference_scoring_evidence,
    score_configured_reference_memory,
)
from ade.visual.representation import RepresentationProviderConfig


def _reference_config(manifest_path: Path) -> VisualEngineConfig:
    return VisualEngineConfig.from_mapping(
        {
            "execution_mode": "reference_anomaly",
            "dataset_roles": ["query", "reference"],
            "reference_memory": {
                "enabled": True,
                "manifest_path": str(manifest_path),
            },
            "reference_scoring": {"enabled": True},
        }
    )


def _build_memory(tmp_path: Path, dimension: int) -> Path:
    provider = RepresentationProviderConfig()
    loaded = build_reference_memory(
        (
            ReferenceVectorRecord(
                "reference-0",
                "reference/image.png",
                np.zeros(dimension, dtype=np.float32),
            ),
        ),
        storage_root=tmp_path / "memory",
        dataset_role=VisualDatasetRole.REFERENCE,
        reference_dataset_fingerprint="a" * 64,
        configuration_fingerprint=provider.fingerprint(),
        backend_id="statistical_visual_v2",
        backend_version="1",
    )
    root = loaded.root
    loaded.close()
    return root / "manifest.json"


def _query(tmp_path: Path) -> tuple[Path, list[ImageRecord], list[EmbeddingRecord]]:
    input_dir = tmp_path / "query"
    input_dir.mkdir()
    image_path = input_dir / "query.png"
    image_path.write_bytes(b"query-content")
    patch = PatchRecord(
        source_path=image_path,
        array=np.zeros((2, 2, 3), dtype=np.uint8),
        x=0,
        y=0,
        width=2,
        height=2,
        patch_id="query-patch",
        image_id="query",
        metadata={
            "patch_size": 2,
            "patch_stride": 2,
            "scale_id": "scale-1",
        },
    )
    embedding = EmbeddingRecord(
        patch=patch,
        vector=np.ones(47, dtype=np.float32),
        patch_id=patch.patch_id,
    )
    return (
        input_dir,
        [ImageRecord(image_path, width=4, height=4, image_id="query")],
        [embedding],
    )


def test_disabled_reference_scoring_leaves_default_pipeline_unchanged(
    tmp_path: Path,
) -> None:
    result = score_configured_reference_memory(
        input_dir=tmp_path,
        image_records=[],
        embeddings=[],
        visual_config=VisualEngineConfig(),
    )

    assert result is None


def test_configured_memory_scores_and_publishes_report_evidence(tmp_path: Path) -> None:
    input_dir, images, embeddings = _query(tmp_path)
    manifest_path = _build_memory(tmp_path, dimension=47)
    config = _reference_config(manifest_path)

    result = score_configured_reference_memory(
        input_dir=input_dir,
        image_records=images,
        embeddings=embeddings,
        visual_config=config,
    )
    evidence = publish_reference_scoring_evidence(
        result,
        output_path=tmp_path / "report.md",
        config=config.reference_scoring,
    )

    assert result is not None
    assert result.summary.calibrated is False
    assert result.summary.reference_dataset_fingerprint == "a" * 64
    assert evidence is not None
    reference = evidence["reference_scoring_summary"]
    spatial = evidence["spatial_anomaly_map_summary"]
    assert isinstance(reference, dict)
    assert isinstance(spatial, dict)
    assert reference["candidate_count"] == 1
    assert reference["calibrated"] is False
    assert Path(str(reference["artifact_path"])).is_file()
    assert spatial["map_count"] == 1


def test_reference_scoring_rejects_non_manifest_path(tmp_path: Path) -> None:
    input_dir, images, embeddings = _query(tmp_path)
    config = _reference_config(tmp_path / "memory")

    with pytest.raises(
        VisualConfigurationError,
        match="must identify an immutable manifest.json",
    ):
        score_configured_reference_memory(
            input_dir=input_dir,
            image_records=images,
            embeddings=embeddings,
            visual_config=config,
        )


def test_reference_scoring_requires_manifest_in_configuration() -> None:
    with pytest.raises(
        VisualConfigurationError,
        match="requires reference_memory.manifest_path",
    ):
        VisualEngineConfig.from_mapping(
            {
                "execution_mode": "reference_anomaly",
                "dataset_roles": ["query", "reference"],
                "reference_memory": {"enabled": True},
                "reference_scoring": {"enabled": True},
            }
        )

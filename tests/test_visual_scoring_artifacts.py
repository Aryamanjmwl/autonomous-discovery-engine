from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest

from ade.visual import (
    QueryPatchRecord,
    ReferenceScoringProvenance,
    ReferenceVectorRecord,
    VisualDatasetRole,
    VisualIntegrityError,
    VisualReferenceScoringConfig,
    build_reference_memory,
    score_reference_anomalies,
    validate_scoring_artifacts,
)


def test_artifact_round_trip_corruption_and_overwrite(tmp_path: Path) -> None:
    fingerprints = ("1" * 64, "2" * 64, "3" * 64)
    memory = build_reference_memory(
        (ReferenceVectorRecord("r", "normal", np.array([0], dtype=np.float32)),),
        storage_root=tmp_path / "memory",
        dataset_role=VisualDatasetRole.REFERENCE,
        reference_dataset_fingerprint=fingerprints[1],
        configuration_fingerprint=fingerprints[2],
        backend_id="backend",
        backend_version="1",
    )
    query = QueryPatchRecord("q", "image", 2, 2, 0, 0, 2, 2, np.array([1], dtype=np.float32))
    provenance = ReferenceScoringProvenance(*fingerprints, "backend", "1")
    config = VisualReferenceScoringConfig(display_normalization=True, save_preview=True)
    try:
        result = score_reference_anomalies(
            (query,), memory, config, provenance, tmp_path / "scores"
        )
        assert result.artifact_root is not None
        artifacts = validate_scoring_artifacts(
            result.artifact_root, expected_scoring_id=result.summary.scoring_id
        )
        raw_path = next(
            result.artifact_root / item.relative_path
            for item in artifacts
            if item.artifact_id.startswith("raw-map")
        )
        loaded = np.load(raw_path, allow_pickle=False)
        assert loaded.dtype == np.float32
        with pytest.raises(VisualIntegrityError):
            score_reference_anomalies((query,), memory, config, provenance, tmp_path / "scores")
        raw_path.write_bytes(b"truncated")
        with pytest.raises(VisualIntegrityError):
            validate_scoring_artifacts(result.artifact_root)
    finally:
        memory.close()


def test_atomic_publication_failure_cleans_temporary_directory(tmp_path: Path) -> None:
    fingerprints = ("1" * 64, "2" * 64, "3" * 64)
    memory = build_reference_memory(
        (ReferenceVectorRecord("r", "normal", np.array([0], dtype=np.float32)),),
        storage_root=tmp_path / "memory",
        dataset_role=VisualDatasetRole.REFERENCE,
        reference_dataset_fingerprint=fingerprints[1],
        configuration_fingerprint=fingerprints[2],
        backend_id="backend",
        backend_version="1",
    )
    query = QueryPatchRecord("q", "image", 2, 2, 0, 0, 2, 2, np.array([1], dtype=np.float32))
    output = tmp_path / "scores"
    try:
        with (
            patch("ade.visual.scoring_artifacts.os.rename", side_effect=OSError("failure")),
            pytest.raises(VisualIntegrityError),
        ):
            score_reference_anomalies(
                (query,),
                memory,
                VisualReferenceScoringConfig(),
                ReferenceScoringProvenance(*fingerprints, "backend", "1"),
                output,
            )
        assert not list(output.iterdir())
    finally:
        memory.close()


def test_manifest_path_traversal_rejected(tmp_path: Path) -> None:
    root = tmp_path / "artifacts"
    root.mkdir()
    (root / "manifest.json").write_text(
        '{"schema_version":1,"scoring_id":"x","artifacts":[{"schema_version":1,"artifact_id":"x","artifact_type":"numpy-array","relative_path":"../x.npy","sha256":"'
        + "0" * 64
        + '","size_bytes":0,"media_type":"application/x-npy"}]}\n',
        encoding="utf-8",
    )
    with pytest.raises(ValueError):
        validate_scoring_artifacts(root)

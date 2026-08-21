"""Regression tests for cooperative workflow cancellation boundaries."""

from __future__ import annotations

from pathlib import Path

import pytest

from ade.cancellation import CancellationRequested, CancellationToken
from ade.cli import run_pipeline, run_temporal_pipeline
from ade.studio.provenance import capture_image_folder_provenance
from ade.studio.service import StudioPaths
from ade.visual import (
    VISUAL_ENGINE_SCHEMA_VERSION,
    TemporalObservation,
    TemporalObservationSequence,
    serialize_temporal_manifest,
)


def _requested_token() -> CancellationToken:
    return CancellationToken(lambda: True, lambda: False)


def test_image_pipeline_stops_before_publishing_report(tmp_path: Path) -> None:
    image_module = pytest.importorskip("PIL.Image")
    numpy = pytest.importorskip("numpy")
    images = tmp_path / "images"
    images.mkdir()
    pixels = numpy.zeros((32, 32, 3), dtype=numpy.uint8)
    image_module.fromarray(pixels).save(images / "sample.png")
    output = tmp_path / "reports" / "cancelled.md"

    with pytest.raises(CancellationRequested):
        run_pipeline(
            images,
            output,
            modality="image",
            cancellation_token=_requested_token(),
        )

    assert not output.exists()
    assert not output.with_suffix(".json").exists()


def test_temporal_pipeline_stops_before_publishing_artifacts(tmp_path: Path) -> None:
    sequence = TemporalObservationSequence(
        VISUAL_ENGINE_SCHEMA_VERSION,
        "cancel-test",
        "1",
        ".",
        "sequence-cancel",
        (
            TemporalObservation("o1", "first.png", sequence_index=0),
            TemporalObservation("o2", "second.png", sequence_index=1),
        ),
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(serialize_temporal_manifest(sequence), encoding="utf-8")
    output = tmp_path / "reports" / "cancelled.md"
    artifact_root = tmp_path / "artifacts"

    with pytest.raises(CancellationRequested):
        run_temporal_pipeline(
            manifest,
            output,
            artifact_root=artifact_root,
            cancellation_token=_requested_token(),
        )

    assert not output.exists()
    assert not output.with_suffix(".json").exists()
    assert not artifact_root.exists()


def test_provenance_hashing_observes_cancellation(tmp_path: Path) -> None:
    images = tmp_path / "images"
    images.mkdir()
    (images / "sample.png").write_bytes(b"image-content")

    with pytest.raises(CancellationRequested):
        capture_image_folder_provenance(
            "images",
            None,
            paths=StudioPaths(project_root=tmp_path),
            cancellation_token=_requested_token(),
        )

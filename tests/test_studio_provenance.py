"""Run-provenance tests for ADE Studio workflows."""

from __future__ import annotations

from pathlib import Path

from ade.studio.provenance import (
    capture_image_folder_provenance,
    capture_temporal_provenance,
)
from ade.studio.service import StudioPaths
from ade.visual import (
    VISUAL_ENGINE_SCHEMA_VERSION,
    TemporalObservation,
    TemporalObservationSequence,
    serialize_temporal_manifest,
)


def test_image_provenance_tracks_supported_content_and_effective_config(
    tmp_path: Path,
) -> None:
    images = tmp_path / "images"
    images.mkdir()
    image = images / "sample.png"
    image.write_bytes(b"first-image")
    (images / "ignored.txt").write_text("not an image", encoding="utf-8")
    config = tmp_path / "config.yaml"
    config.write_text(
        "validation:\n  supported_image_extensions: ['.png']\n",
        encoding="utf-8",
    )
    paths = StudioPaths(project_root=tmp_path)

    first = capture_image_folder_provenance("images", "config.yaml", paths=paths)
    repeated = capture_image_folder_provenance("images", "config.yaml", paths=paths)

    assert first == repeated
    assert first.input_fingerprint["kind"] == "image_folder"
    assert first.input_fingerprint["algorithm"] == "sha256"
    assert first.input_fingerprint["file_count"] == 1
    values = first.effective_configuration["values"]
    assert isinstance(values, dict)
    validation = values["validation"]
    assert isinstance(validation, dict)
    assert validation["supported_image_extensions"] == [".png"]

    image.write_bytes(b"changed-image")
    changed = capture_image_folder_provenance("images", "config.yaml", paths=paths)

    assert changed.input_fingerprint["digest"] != first.input_fingerprint["digest"]
    assert (
        changed.effective_configuration["fingerprint"]
        == first.effective_configuration["fingerprint"]
    )


def test_temporal_provenance_tracks_manifest_sources_and_applied_parameters(
    tmp_path: Path,
) -> None:
    first_image = tmp_path / "first.png"
    second_image = tmp_path / "second.png"
    first_image.write_bytes(b"first")
    second_image.write_bytes(b"second")
    sequence = TemporalObservationSequence(
        VISUAL_ENGINE_SCHEMA_VERSION,
        "provenance-test",
        "1",
        ".",
        "sequence-1",
        (
            TemporalObservation("o1", "first.png", sequence_index=0),
            TemporalObservation("o2", "second.png", sequence_index=1),
        ),
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(serialize_temporal_manifest(sequence), encoding="utf-8")
    paths = StudioPaths(project_root=tmp_path)

    first = capture_temporal_provenance(
        "manifest.json",
        strategy="baseline_difference",
        patch_size=16,
        top_k=7,
        patch_top_k=3,
        paths=paths,
    )

    assert first.input_fingerprint["kind"] == "temporal_sequence"
    assert first.input_fingerprint["file_count"] == 3
    assert first.effective_configuration["values"] == {
        "strategy": "baseline_difference",
        "patch_size": 16,
        "top_k": 7,
        "patch_top_k": 3,
    }

    second_image.write_bytes(b"changed-second")
    changed = capture_temporal_provenance(
        "manifest.json",
        strategy="baseline_difference",
        patch_size=16,
        top_k=7,
        patch_top_k=3,
        paths=paths,
    )

    assert changed.input_fingerprint["digest"] != first.input_fingerprint["digest"]

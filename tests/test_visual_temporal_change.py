from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ade.visual import (
    VISUAL_ENGINE_SCHEMA_VERSION,
    TemporalObservation,
    TemporalObservationSequence,
    VisualIntegrityError,
    VisualManifestError,
    analyze_temporal_change,
    deserialize_temporal_manifest,
    load_temporal_manifest,
    publish_temporal_change_artifact,
    serialize_temporal_manifest,
    validate_temporal_change_artifact,
    validate_temporal_manifest,
)


def _image(path: Path, value: int, changed: bool = False) -> None:
    image_module = pytest.importorskip("PIL.Image")
    array = np.full((16, 16, 3), value, dtype=np.uint8)
    if changed:
        array[:8, :8] = 255
    path.parent.mkdir(parents=True, exist_ok=True)
    image_module.fromarray(array).save(path)


def _sequence(
    root: Path, observations: tuple[TemporalObservation, ...] | None = None
) -> TemporalObservationSequence:
    return TemporalObservationSequence(
        VISUAL_ENGINE_SCHEMA_VERSION,
        "revisits",
        "1",
        str(root),
        "scene-1",
        observations
        or (
            TemporalObservation("o2", "images/2.png", sequence_index=2),
            TemporalObservation("o0", "images/0.png", sequence_index=0),
            TemporalObservation("o1", "images/1.png", sequence_index=1),
        ),
    )


def test_manifest_success_and_deterministic_order(tmp_path: Path) -> None:
    payload = serialize_temporal_manifest(_sequence(tmp_path))
    loaded = deserialize_temporal_manifest(payload)
    assert [x.observation_id for x in loaded.observations] == ["o0", "o1", "o2"]
    assert serialize_temporal_manifest(loaded) == payload


def test_manifest_rejects_traversal_duplicates_invalid_order_and_short_sequence(
    tmp_path: Path,
) -> None:
    with pytest.raises(VisualIntegrityError):
        validate_temporal_manifest(
            _sequence(
                tmp_path,
                (
                    TemporalObservation("a", "../a.png", sequence_index=0),
                    TemporalObservation("b", "b.png", sequence_index=1),
                ),
            )
        )
    with pytest.raises(VisualIntegrityError):
        validate_temporal_manifest(
            _sequence(
                tmp_path,
                (
                    TemporalObservation("a", "a.png", sequence_index=0),
                    TemporalObservation("a", "b.png", sequence_index=1),
                ),
            )
        )
    with pytest.raises(VisualManifestError):
        validate_temporal_manifest(
            _sequence(
                tmp_path,
                (
                    TemporalObservation("a", "a.png", timestamp="bad"),
                    TemporalObservation("b", "b.png", timestamp="2026-01-01T00:00:00Z"),
                ),
            )
        )
    with pytest.raises(VisualManifestError):
        validate_temporal_manifest(
            _sequence(
                tmp_path,
                (
                    TemporalObservation("a", "a.png", sequence_index=-1),
                    TemporalObservation("b", "b.png", sequence_index=1),
                ),
            )
        )
    with pytest.raises(VisualIntegrityError):
        validate_temporal_manifest(
            _sequence(tmp_path, (TemporalObservation("a", "a.png", sequence_index=0),))
        )


def test_strict_missing_file_behavior(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(serialize_temporal_manifest(_sequence(tmp_path)), encoding="utf-8")
    with pytest.raises(VisualIntegrityError):
        load_temporal_manifest(path, strict=True)


def test_adjacent_baseline_ranking_patch_evidence_and_artifact(tmp_path: Path) -> None:
    _image(tmp_path / "images/0.png", 0)
    _image(tmp_path / "images/1.png", 10)
    _image(tmp_path / "images/2.png", 10, True)
    sequence = _sequence(tmp_path)
    adjacent = analyze_temporal_change(sequence, strategy="adjacent_difference", patch_size=8)
    baseline = analyze_temporal_change(sequence, strategy="baseline_difference")
    assert [(x.source_observation_id, x.target_observation_id) for x in adjacent.scores] == [
        ("o0", "o1"),
        ("o1", "o2"),
    ]
    assert [(x.source_observation_id, x.target_observation_id) for x in baseline.scores] == [
        ("o0", "o1"),
        ("o0", "o2"),
    ]
    assert (
        adjacent.events[0].score.global_feature_distance
        >= adjacent.events[1].score.global_feature_distance
    )
    assert adjacent.events[0].requires_human_review and adjacent.events[0].patch_evidence
    root = publish_temporal_change_artifact(adjacent, tmp_path / "results")
    assert validate_temporal_change_artifact(root)["summary"]["observation_count"] == 3
    (root / "temporal_change_result.json").write_text("{}\n", encoding="utf-8")
    with pytest.raises(VisualIntegrityError):
        validate_temporal_change_artifact(root)


def test_default_pipeline_and_dependencies_unchanged() -> None:
    from ade.visual import VisualReferenceScoringConfig

    assert VisualReferenceScoringConfig().enabled is False
    project = Path("pyproject.toml").read_text(encoding="utf-8")
    assert '"numpy>=1.24"' in project and "opencv" not in project

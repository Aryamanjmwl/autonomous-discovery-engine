from __future__ import annotations

from dataclasses import replace
from pathlib import Path

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
)

FINGERPRINTS = ("1" * 64, "2" * 64, "3" * 64)


def reference_memory(tmp_path: Path, *, metric: str = "euclidean"):
    records = (
        ReferenceVectorRecord("r0", "normal-a", np.array([0, 0], dtype=np.float32)),
        ReferenceVectorRecord("r1", "normal-b", np.array([2, 0], dtype=np.float32)),
        ReferenceVectorRecord("r2", "normal-c", np.array([0, 2], dtype=np.float32)),
    )
    return build_reference_memory(
        records,
        storage_root=tmp_path / "memory",
        dataset_role=VisualDatasetRole.REFERENCE,
        reference_dataset_fingerprint=FINGERPRINTS[1],
        configuration_fingerprint=FINGERPRINTS[2],
        backend_id="statistical_visual_v2",
        backend_version="1",
        distance_metric=metric,
    )


def patch(
    patch_id: str,
    vector: tuple[float, float],
    *,
    image_id: str = "image-a",
    x: int = 0,
    y: int = 0,
    width: int = 2,
    height: int = 2,
    image_width: int = 4,
    image_height: int = 4,
    scale_id: str = "s1",
) -> QueryPatchRecord:
    return QueryPatchRecord(
        patch_id,
        image_id,
        image_width,
        image_height,
        x,
        y,
        width,
        height,
        np.array(vector, dtype=np.float32),
        scale_id,
        1,
    )


def provenance() -> ReferenceScoringProvenance:
    return ReferenceScoringProvenance(
        FINGERPRINTS[0],
        FINGERPRINTS[1],
        FINGERPRINTS[2],
        "statistical_visual_v2",
        "1",
    )


def test_known_nearest_neighbor_and_alignment(tmp_path: Path) -> None:
    with reference_memory(tmp_path) as memory:
        records = (patch("q-b", (1, 0)), patch("q-a", (0, 1), x=2))
        result = score_reference_anomalies(
            records, memory, VisualReferenceScoringConfig(), provenance()
        )
    assert [item.patch_id for item in result.patch_scores] == ["q-b", "q-a"]
    assert [item.raw_score for item in result.patch_scores] == pytest.approx([1, 1])
    assert result.patch_scores[0].evidence.vector_ids == ("r0",)
    assert result.summary.calibrated is False


def test_knn_mean_and_top_k_clamping(tmp_path: Path) -> None:
    config = VisualReferenceScoringConfig(patch_strategy="knn_mean", neighbor_count=10)
    with reference_memory(tmp_path) as memory:
        result = score_reference_anomalies((patch("q", (0, 0)),), memory, config, provenance())
    assert result.patch_scores[0].raw_score == pytest.approx(4 / 3)
    assert result.summary.neighbor_count == 3


def test_cosine_and_zero_norm_semantics(tmp_path: Path) -> None:
    config = VisualReferenceScoringConfig(metric="cosine")
    with reference_memory(tmp_path, metric="cosine") as memory:
        result = score_reference_anomalies((patch("q", (0, 0)),), memory, config, provenance())
    assert result.patch_scores[0].raw_score == pytest.approx(1.0)


def test_equal_distance_order_and_batch_equivalence(tmp_path: Path) -> None:
    records = (patch("q1", (1, 1)), patch("q2", (0.5, 0.5), x=2))
    config = VisualReferenceScoringConfig(patch_strategy="knn_mean", neighbor_count=3)
    with reference_memory(tmp_path) as memory:
        first = score_reference_anomalies(
            records, memory, replace(config, query_batch_size=1), provenance()
        )
        second = score_reference_anomalies(
            records, memory, replace(config, query_batch_size=20), provenance()
        )
    assert first.patch_scores == second.patch_scores
    assert first.patch_scores[0].evidence.vector_ids == ("r0", "r1", "r2")


@pytest.mark.parametrize(
    "records",
    [
        (patch("same", (0, 0)), patch("same", (1, 1), x=2)),
        (patch("a", (0, 0)), patch("b", (1, 1), image_width=5, x=2)),
    ],
)
def test_duplicate_ids_and_inconsistent_image_dimensions(tmp_path: Path, records) -> None:
    with reference_memory(tmp_path) as memory, pytest.raises(VisualIntegrityError):
        score_reference_anomalies(records, memory, VisualReferenceScoringConfig(), provenance())


def test_query_contract_rejects_coordinates_and_nonfinite() -> None:
    with pytest.raises(VisualIntegrityError):
        patch("q", (0, 0), x=3)
    with pytest.raises(VisualIntegrityError):
        patch("q", (float("nan"), 0))
    with pytest.raises(VisualIntegrityError):
        patch("q", (float("inf"), 0))


@pytest.mark.parametrize(
    "change",
    [
        {"reference_dataset_fingerprint": FINGERPRINTS[0]},
        {"configuration_fingerprint": "4" * 64},
        {"backend_id": "other"},
    ],
)
def test_provenance_incompatibility(tmp_path: Path, change: dict[str, str]) -> None:
    with reference_memory(tmp_path) as memory, pytest.raises(ValueError):
        score_reference_anomalies(
            (patch("q", (0, 0)),),
            memory,
            VisualReferenceScoringConfig(),
            replace(provenance(), **change),
        )


def test_dimension_and_metric_incompatibility(tmp_path: Path) -> None:
    with reference_memory(tmp_path) as memory:
        with pytest.raises(VisualIntegrityError):
            bad = replace(patch("q", (0, 0)), vector=np.array([1], dtype=np.float32))
            score_reference_anomalies((bad,), memory, VisualReferenceScoringConfig(), provenance())
        with pytest.raises(VisualIntegrityError):
            score_reference_anomalies(
                (patch("q", (0, 0)),),
                memory,
                VisualReferenceScoringConfig(metric="cosine"),
                provenance(),
            )


def test_image_aggregation_isolated_and_deterministic(tmp_path: Path) -> None:
    records = (
        patch("b", (1, 0)),
        patch("a", (1, 0), x=2),
        patch("c", (0, 0), image_id="image-b"),
    )
    config = VisualReferenceScoringConfig(image_aggregation="top_fraction_mean", top_fraction=0.5)
    with reference_memory(tmp_path) as memory:
        result = score_reference_anomalies(records, memory, config, provenance())
    assert [item.image_id for item in result.image_scores] == ["image-a", "image-b"]
    assert result.image_scores[0].selected_patch_ids == ("a",)
    assert result.image_scores[1].patch_scores[0].patch_id == "c"


@pytest.mark.parametrize("fraction", [0, -0.1, 1.1])
def test_top_fraction_boundaries(fraction: float) -> None:
    with pytest.raises(ValueError):
        VisualReferenceScoringConfig(top_fraction=fraction).validate()


def test_default_configuration_is_disabled() -> None:
    config = VisualReferenceScoringConfig()
    assert config.enabled is False
    config.validate()

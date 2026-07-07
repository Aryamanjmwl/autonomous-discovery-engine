from pathlib import Path

import numpy as np

from ade.discovery.anomaly_selector import AnomalySelector
from ade.models import CandidateAnomaly
from ade.preprocessing.patch_extractor import Patch
from ade.representation.embedding_engine import PatchEmbedding


def _candidate(
    anomaly_id: str,
    source_path: str,
    x: int,
    y: int,
    score: float,
    scale_label: str = "s64",
    vector: list[float] | None = None,
) -> CandidateAnomaly:
    patch = Patch(
        source_path=Path(source_path),
        array=np.zeros((64, 64, 3), dtype=np.uint8),
        x=x,
        y=y,
        width=64,
        height=64,
        patch_id=f"{Path(source_path).stem}_{scale_label}_x{x}_y{y}",
        image_id=Path(source_path).stem,
        metadata={
            "patch_size": 64,
            "patch_stride": 64,
            "scale_id": f"scale-{scale_label}",
            "scale_label": scale_label,
        },
    )
    return CandidateAnomaly(
        embedding=PatchEmbedding(
            patch=patch,
            vector=np.asarray(vector or [score, 0.0], dtype=np.float32),
        ),
        novelty_score=score,
        anomaly_id=anomaly_id,
    )


def test_anomaly_selector_preserves_top_n_when_disabled() -> None:
    candidates = [
        _candidate("a1", "a.png", 0, 0, 0.8),
        _candidate("a2", "a.png", 10, 0, 0.7),
        _candidate("b1", "b.png", 0, 0, 0.6),
    ]

    selected = AnomalySelector(enabled=False).select(candidates, max_candidates=2)

    assert [candidate.anomaly_id for candidate in selected] == ["a1", "a2"]
    assert selected[0].metadata["selection_reason"] == "high novelty"


def test_anomaly_selector_limits_repeated_image_regions() -> None:
    candidates = [
        _candidate("a1", "a.png", 0, 0, 0.9),
        _candidate("a2", "a.png", 8, 8, 0.85),
        _candidate("a3", "a.png", 96, 96, 0.8),
        _candidate("b1", "b.png", 0, 0, 0.7),
    ]

    selected = AnomalySelector(
        enabled=True,
        min_spatial_distance=32,
        max_per_image=1,
    ).select(candidates, max_candidates=3)

    assert [candidate.anomaly_id for candidate in selected] == ["a1", "b1"]
    assert all(
        candidate.metadata["selection_reason"] == "diversity selected"
        for candidate in selected
    )


def test_anomaly_selector_prefers_multiple_scales_deterministically() -> None:
    candidates = [
        _candidate("s64-a", "a.png", 0, 0, 0.9, scale_label="s64"),
        _candidate("s64-b", "b.png", 0, 0, 0.8, scale_label="s64"),
        _candidate("s128-a", "c.png", 0, 0, 0.7, scale_label="s128"),
    ]

    selected = AnomalySelector(
        enabled=True,
        prefer_multiple_scales=True,
    ).select(candidates, max_candidates=2)

    assert [candidate.anomaly_id for candidate in selected] == ["s64-a", "s128-a"]
    assert [candidate.metadata["selection_rank"] for candidate in selected] == [1, 2]

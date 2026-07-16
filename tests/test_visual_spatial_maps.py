from __future__ import annotations

import numpy as np
import pytest

from ade.visual import PatchAnomalyScore, QueryPatchRecord, ReferenceEvidence, build_spatial_maps
from ade.visual.errors import VisualIntegrityError


def record(
    name: str,
    score: float,
    x: int,
    y: int,
    w: int,
    h: int,
    *,
    scale: str = "s1",
    iw: int = 4,
    ih: int = 3,
):
    query = QueryPatchRecord(
        name, "image", iw, ih, x, y, w, h, np.array([score], dtype=np.float32), scale
    )
    scored = PatchAnomalyScore(
        name,
        "image",
        score,
        "euclidean",
        "nearest_neighbor",
        score,
        ReferenceEvidence(("r",), (0,), (score,)),
        "b",
        "1",
        "m",
    )
    return query, scored


def maps(items, **kwargs):
    records, scores = zip(*items, strict=True)
    options = dict(
        projection="overlap_mean",
        fusion="max",
        smoothing_sigma=0,
        maximum_image_pixels=100,
        display_normalization=False,
    )
    options.update(kwargs)
    return build_spatial_maps(tuple(records), tuple(scores), **options)[0]


def test_complete_patch_and_float32() -> None:
    result = maps([record("a", 2, 0, 0, 4, 3)])
    assert result.raw_map.dtype == np.float32
    assert np.all(result.raw_map == 2)
    assert result.coverage_fraction == 1


def test_overlap_mean_and_uncovered_nan() -> None:
    result = maps([record("a", 2, 0, 0, 2, 2), record("b", 4, 1, 0, 2, 2)])
    assert result.raw_map[0, :3].tolist() == [2, 3, 4]
    assert np.isnan(result.raw_map[2, 3])
    assert result.uncovered_policy == "nan_masked"
    assert result.coverage_fraction == pytest.approx(6 / 12)


def test_overlap_max_non_square_edge_aligned() -> None:
    result = maps(
        [record("a", 2, 0, 0, 3, 3), record("b", 4, 2, 1, 2, 2)], projection="overlap_max"
    )
    assert result.raw_map[1, 2] == 4
    assert result.raw_map[2, 3] == 4


@pytest.mark.parametrize("fusion,expected", [("max", 4), ("mean", 3)])
def test_multiscale_fusion(fusion: str, expected: float) -> None:
    result = maps(
        [record("a", 2, 0, 0, 4, 3, scale="small"), record("b", 4, 0, 0, 4, 3, scale="large")],
        fusion=fusion,
    )
    assert np.all(result.raw_map == expected)


def test_smoothing_deterministic_and_display_does_not_change_raw() -> None:
    items = [record("a", 0, 0, 0, 2, 3), record("b", 4, 2, 0, 2, 3)]
    first = maps(items, smoothing_sigma=1, display_normalization=True)
    second = maps(items, smoothing_sigma=1, display_normalization=False)
    np.testing.assert_array_equal(first.raw_map, second.raw_map)
    assert first.display_map is not None
    assert np.nanmin(first.display_map) == 0
    assert np.nanmax(first.display_map) == 1


def test_pixel_bound() -> None:
    with pytest.raises(VisualIntegrityError):
        maps([record("a", 1, 0, 0, 4, 3)], maximum_image_pixels=11)

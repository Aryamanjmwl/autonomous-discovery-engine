"""Deterministic projection of raw patch scores into image space."""

from __future__ import annotations

import math
from collections import defaultdict

import numpy as np

from ade.visual.errors import VisualConfigurationError, VisualIntegrityError
from ade.visual.scoring_contracts import PatchAnomalyScore, QueryPatchRecord, SpatialAnomalyMap


def build_spatial_maps(
    records: tuple[QueryPatchRecord, ...],
    scores: tuple[PatchAnomalyScore, ...],
    *,
    projection: str,
    fusion: str,
    smoothing_sigma: float,
    maximum_image_pixels: int,
    display_normalization: bool,
) -> tuple[SpatialAnomalyMap, ...]:
    """Project per-patch scores, retaining NaN for pixels without evidence."""

    if projection not in {"overlap_mean", "overlap_max"} or fusion not in {"mean", "max"}:
        raise VisualConfigurationError("Unsupported map projection or multi-scale fusion")
    if smoothing_sigma < 0 or not math.isfinite(smoothing_sigma):
        raise VisualConfigurationError("smoothing_sigma must be finite and non-negative")
    score_by_id = {score.patch_id: score for score in scores}
    grouped: dict[str, list[QueryPatchRecord]] = defaultdict(list)
    for record in records:
        grouped[record.image_id].append(record)
    maps: list[SpatialAnomalyMap] = []
    for image_id in sorted(grouped):
        patches = grouped[image_id]
        width, height = patches[0].image_width, patches[0].image_height
        if width * height > maximum_image_pixels:
            raise VisualIntegrityError(
                "Image exceeds configured anomaly-map pixel bound",
                context={
                    "image_id": image_id,
                    "pixels": width * height,
                    "maximum": maximum_image_pixels,
                },
            )
        scale_maps: list[np.ndarray] = []
        scale_counts: list[np.ndarray] = []
        for scale in sorted({patch.scale_id for patch in patches}):
            selected = [patch for patch in patches if patch.scale_id == scale]
            counts = np.zeros((height, width), dtype=np.uint32)
            if projection == "overlap_mean":
                values = np.zeros((height, width), dtype=np.float64)
                for patch in selected:
                    area = np.s_[patch.y : patch.y + patch.height, patch.x : patch.x + patch.width]
                    values[area] += score_by_id[patch.patch_id].raw_score
                    counts[area] += 1
                projected = np.full((height, width), np.nan, dtype=np.float64)
                np.divide(values, counts, out=projected, where=counts > 0)
            else:
                projected = np.full((height, width), -np.inf, dtype=np.float64)
                for patch in selected:
                    area = np.s_[patch.y : patch.y + patch.height, patch.x : patch.x + patch.width]
                    np.maximum(
                        projected[area], score_by_id[patch.patch_id].raw_score, out=projected[area]
                    )
                    counts[area] += 1
                projected[counts == 0] = np.nan
            scale_maps.append(projected)
            scale_counts.append(counts)
        stack = np.stack(scale_maps)
        valid = np.isfinite(stack)
        coverage = np.asarray(
            np.sum(np.stack(scale_counts), axis=0, dtype=np.uint32), dtype=np.uint32
        )
        if fusion == "mean":
            total = np.nansum(stack, axis=0)
            contributors = valid.sum(axis=0)
            raw = np.full((height, width), np.nan, dtype=np.float64)
            np.divide(total, contributors, out=raw, where=contributors > 0)
        else:
            raw = np.max(np.where(valid, stack, -np.inf), axis=0)
            raw[~np.any(valid, axis=0)] = np.nan
        if smoothing_sigma > 0:
            raw = _masked_gaussian(raw, smoothing_sigma)
        raw32 = raw.astype(np.float32)
        display = _display_normalize(raw32) if display_normalization else None
        maps.append(
            SpatialAnomalyMap(
                image_id,
                width,
                height,
                raw32,
                coverage,
                float(np.count_nonzero(coverage) / coverage.size),
                projection,
                fusion,
                smoothing_sigma,
                display_map=display,
            )
        )
    return tuple(maps)


def _gaussian_kernel(sigma: float) -> np.ndarray:
    radius = max(1, int(math.ceil(3.0 * sigma)))
    x = np.arange(-radius, radius + 1, dtype=np.float64)
    kernel = np.exp(-(x * x) / (2.0 * sigma * sigma))
    return kernel / kernel.sum()


def _convolve_axis(values: np.ndarray, kernel: np.ndarray, axis: int) -> np.ndarray:
    radius = len(kernel) // 2
    padded = np.pad(values, [(radius, radius) if index == axis else (0, 0) for index in range(2)], mode="edge")
    return np.apply_along_axis(lambda row: np.convolve(row, kernel, mode="valid"), axis, padded)


def _masked_gaussian(values: np.ndarray, sigma: float) -> np.ndarray:
    kernel = _gaussian_kernel(sigma)
    valid = np.isfinite(values)
    numerator = np.where(valid, values, 0.0)
    weights = valid.astype(np.float64)
    for axis in (1, 0):
        numerator = _convolve_axis(numerator, kernel, axis)
        weights = _convolve_axis(weights, kernel, axis)
    result = np.full(values.shape, np.nan, dtype=np.float64)
    np.divide(numerator, weights, out=result, where=weights > 0)
    result[~valid] = np.nan
    return result


def _display_normalize(raw: np.ndarray) -> np.ndarray:
    display = np.zeros(raw.shape, dtype=np.float32)
    valid = np.isfinite(raw)
    if not np.any(valid):
        return display
    low, high = float(np.min(raw[valid])), float(np.max(raw[valid]))
    if high > low:
        display[valid] = (raw[valid] - low) / (high - low)
    return display

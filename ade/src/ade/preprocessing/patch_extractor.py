"""Patch extraction utilities for ADE images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass(frozen=True)
class Patch:
    """A fixed-size image patch and its source coordinates."""

    source_path: Path
    array: np.ndarray
    x: int
    y: int
    width: int
    height: int

    @property
    def coordinates(self) -> tuple[int, int, int, int]:
        """Return coordinates as ``(x, y, width, height)``."""

        return (self.x, self.y, self.width, self.height)


class PatchExtractor:
    """Split images into deterministic fixed-size patches."""

    def __init__(self, patch_size: int = 64, stride: int | None = None) -> None:
        if patch_size <= 0:
            raise ValueError("patch_size must be positive")
        if stride is not None and stride <= 0:
            raise ValueError("stride must be positive")

        self.patch_size = patch_size
        self.stride = stride or patch_size

    def extract_from_path(self, image_path: Path | str) -> list[Patch]:
        """Load an image and return RGB patch arrays with coordinates."""

        from PIL import Image

        path = Path(image_path)
        with Image.open(path) as image:
            rgb_image = image.convert("RGB")
            array = np.asarray(rgb_image, dtype=np.uint8)
        return self.extract_from_array(array=array, source_path=path)

    def extract_from_array(self, array: np.ndarray, source_path: Path | str) -> list[Patch]:
        """Return fixed-size patches from an RGB image array."""

        if array.ndim != 3 or array.shape[2] != 3:
            raise ValueError("array must have shape (height, width, 3)")

        source = Path(source_path)
        image_height, image_width, _ = array.shape
        patches: list[Patch] = []

        for y in range(0, max(image_height - self.patch_size + 1, 0), self.stride):
            for x in range(0, max(image_width - self.patch_size + 1, 0), self.stride):
                patch_array = array[y : y + self.patch_size, x : x + self.patch_size].copy()
                patches.append(
                    Patch(
                        source_path=source,
                        array=patch_array,
                        x=x,
                        y=y,
                        width=self.patch_size,
                        height=self.patch_size,
                    )
                )

        if not patches and image_height > 0 and image_width > 0:
            cropped_height = min(self.patch_size, image_height)
            cropped_width = min(self.patch_size, image_width)
            patches.append(
                Patch(
                    source_path=source,
                    array=array[:cropped_height, :cropped_width].copy(),
                    x=0,
                    y=0,
                    width=cropped_width,
                    height=cropped_height,
                )
            )

        return patches

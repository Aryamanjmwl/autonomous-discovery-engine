"""Patch extraction utilities for ADE images."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from ade.models import PatchRecord as Patch


@dataclass(frozen=True)
class PatchSpec:
    """One deterministic patch extraction scale."""

    size: int
    stride: int
    scale_id: str
    scale_label: str


class PatchExtractor:
    """Split images into deterministic fixed-size patches."""

    def __init__(
        self,
        patch_size: int = 64,
        stride: int | None = None,
        patch_sizes: list[int] | tuple[int, ...] | None = None,
        patch_strides: list[int] | tuple[int, ...] | None = None,
    ) -> None:
        if patch_size <= 0:
            raise ValueError("patch_size must be positive")
        if stride is not None and stride <= 0:
            raise ValueError("stride must be positive")
        if patch_sizes is None:
            patch_sizes = [patch_size]
        if patch_strides is None:
            patch_strides = [stride or size for size in patch_sizes]
        if len(patch_sizes) != len(patch_strides):
            raise ValueError("patch_sizes and patch_strides must have matching lengths")
        if not patch_sizes:
            raise ValueError("at least one patch size is required")

        self.patch_specs = self._build_patch_specs(
            patch_sizes=patch_sizes,
            patch_strides=patch_strides,
        )
        self.patch_size = self.patch_specs[0].size
        self.stride = self.patch_specs[0].stride

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

        for spec in self.patch_specs:
            patches.extend(
                self._extract_scale(
                    array=array,
                    source=source,
                    spec=spec,
                    image_height=image_height,
                    image_width=image_width,
                )
            )

        return patches

    @staticmethod
    def _build_patch_specs(
        patch_sizes: list[int] | tuple[int, ...],
        patch_strides: list[int] | tuple[int, ...],
    ) -> list[PatchSpec]:
        """Return validated patch extraction specs."""

        specs: list[PatchSpec] = []
        seen_labels: dict[str, int] = {}
        for index, (size, stride) in enumerate(
            zip(patch_sizes, patch_strides, strict=True),
            start=1,
        ):
            if size <= 0:
                raise ValueError("patch sizes must be positive")
            if stride <= 0:
                raise ValueError("patch strides must be positive")
            base_label = f"s{int(size)}"
            seen_labels[base_label] = seen_labels.get(base_label, 0) + 1
            scale_label = (
                base_label
                if seen_labels[base_label] == 1
                else f"{base_label}_{seen_labels[base_label]}"
            )
            specs.append(
                PatchSpec(
                    size=int(size),
                    stride=int(stride),
                    scale_id=f"scale-{index}",
                    scale_label=scale_label,
                )
            )
        return specs

    def _extract_scale(
        self,
        array: np.ndarray,
        source: Path,
        spec: PatchSpec,
        image_height: int,
        image_width: int,
    ) -> list[Patch]:
        """Extract patches for one scale."""

        patches: list[Patch] = []
        for y in range(0, max(image_height - spec.size + 1, 0), spec.stride):
            for x in range(0, max(image_width - spec.size + 1, 0), spec.stride):
                patch_array = array[y : y + spec.size, x : x + spec.size].copy()
                patches.append(
                    self._build_patch(
                        source=source,
                        array=patch_array,
                        x=x,
                        y=y,
                        width=spec.size,
                        height=spec.size,
                        spec=spec,
                    )
                )
        if not patches and image_height > 0 and image_width > 0:
            cropped_height = min(spec.size, image_height)
            cropped_width = min(spec.size, image_width)
            patches.append(
                self._build_patch(
                    source=source,
                    array=array[:cropped_height, :cropped_width].copy(),
                    x=0,
                    y=0,
                    width=cropped_width,
                    height=cropped_height,
                    spec=spec,
                )
            )
        return patches

    @staticmethod
    def _build_patch(
        source: Path,
        array: np.ndarray,
        x: int,
        y: int,
        width: int,
        height: int,
        spec: PatchSpec,
    ) -> Patch:
        """Build a traceable patch record."""

        return Patch(
            source_path=source,
            array=array,
            x=x,
            y=y,
            width=width,
            height=height,
            patch_id=(
                f"{source.stem}_{spec.scale_label}_stride{spec.stride}_x{x}_y{y}"
            ),
            image_id=source.stem,
            metadata={
                "patch_size": spec.size,
                "patch_stride": spec.stride,
                "scale_id": spec.scale_id,
                "scale_label": spec.scale_label,
            },
        )

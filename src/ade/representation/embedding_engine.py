"""Deterministic lightweight visual embeddings for ADE image patches."""

from __future__ import annotations

import numpy as np

from ade.models import EmbeddingRecord as PatchEmbedding
from ade.preprocessing.patch_extractor import Patch


class EmbeddingEngine:
    """Create replaceable patch embeddings from deterministic visual statistics.

    This class intentionally avoids deep learning. Future implementations can
    preserve this interface while replacing ``embed_patch`` with DINOv2, CLIP,
    satellite-specific encoders, or other validated representation models.
    """

    backend_name = "statistical_visual_v2"

    @property
    def feature_names(self) -> list[str]:
        """Return the ordered feature names emitted by this backend."""

        return [
            "patch_width_norm",
            "patch_height_norm",
            "patch_aspect_ratio",
            "brightness_mean",
            "brightness_std",
            "brightness_min",
            "brightness_max",
            "brightness_p10",
            "brightness_p90",
            "contrast_rms",
            "red_mean",
            "green_mean",
            "blue_mean",
            "red_std",
            "green_std",
            "blue_std",
            "red_min",
            "green_min",
            "blue_min",
            "red_max",
            "green_max",
            "blue_max",
            "saturation_mean",
            "saturation_std",
            "texture_local_std",
            "edge_density",
            "horizontal_gradient_mean",
            "vertical_gradient_mean",
            "grayscale_entropy",
            *[f"red_hist_{index}" for index in range(4)],
            *[f"green_hist_{index}" for index in range(4)],
            *[f"blue_hist_{index}" for index in range(4)],
            *[f"brightness_hist_{index}" for index in range(6)],
        ]

    def embed_patch(self, patch: Patch) -> PatchEmbedding:
        """Return a deterministic statistical embedding for one patch."""

        array = patch.array.astype(np.float32) / 255.0
        vector = self._extract_features(array=array, width=patch.width, height=patch.height)
        return PatchEmbedding(
            patch=patch,
            vector=vector,
            metadata={
                "backend_name": self.backend_name,
                "feature_names": self.feature_names,
                "feature_count": int(vector.size),
            },
        )

    def embed_patches(self, patches: list[Patch]) -> list[PatchEmbedding]:
        """Return embeddings for a list of patches."""

        return [self.embed_patch(patch) for patch in patches]

    @staticmethod
    def _edge_density(array: np.ndarray) -> float:
        """Estimate edge density from simple grayscale gradients."""

        gray = array.mean(axis=2)
        if gray.shape[0] < 2 or gray.shape[1] < 2:
            return 0.0

        gradient_x = np.abs(np.diff(gray, axis=1)).mean()
        gradient_y = np.abs(np.diff(gray, axis=0)).mean()
        return float((gradient_x + gradient_y) / 2.0)

    def _extract_features(
        self,
        array: np.ndarray,
        width: int,
        height: int,
    ) -> np.ndarray:
        """Return a stable visual feature vector for an RGB patch."""

        if array.ndim != 3 or array.shape[2] != 3:
            raise ValueError("array must have shape (height, width, 3)")

        gray = array.mean(axis=2)
        channel_mean = array.mean(axis=(0, 1))
        channel_std = array.std(axis=(0, 1))
        channel_min = array.min(axis=(0, 1))
        channel_max = array.max(axis=(0, 1))
        brightness_stats = np.array(
            [
                gray.mean(),
                gray.std(),
                gray.min(),
                gray.max(),
                np.percentile(gray, 10),
                np.percentile(gray, 90),
            ],
            dtype=np.float32,
        )
        size_features = np.array(
            [
                min(float(width) / 1024.0, 1.0),
                min(float(height) / 1024.0, 1.0),
                float(width) / float(height) if height else 0.0,
            ],
            dtype=np.float32,
        )
        contrast = np.array([gray.std()], dtype=np.float32)
        saturation = self._saturation_stats(array)
        texture = np.array([self._local_texture(gray)], dtype=np.float32)
        gradients = self._gradient_features(gray)
        entropy = np.array([self._entropy(gray, bins=16)], dtype=np.float32)
        color_histograms = np.concatenate(
            [self._histogram(array[:, :, channel], bins=4) for channel in range(3)]
        )
        brightness_histogram = self._histogram(gray, bins=6)

        vector = np.concatenate(
            [
                size_features,
                brightness_stats,
                contrast,
                channel_mean,
                channel_std,
                channel_min,
                channel_max,
                saturation,
                texture,
                gradients,
                entropy,
                color_histograms,
                brightness_histogram,
            ]
        ).astype(np.float32)
        return np.nan_to_num(vector, nan=0.0, posinf=0.0, neginf=0.0)

    @staticmethod
    def _histogram(values: np.ndarray, bins: int) -> np.ndarray:
        """Return a normalized histogram over values in the range 0 to 1."""

        histogram, _ = np.histogram(values, bins=bins, range=(0.0, 1.0))
        total = histogram.sum()
        if total == 0:
            return np.zeros(bins, dtype=np.float32)
        return (histogram.astype(np.float32) / float(total)).astype(np.float32)

    @staticmethod
    def _saturation_stats(array: np.ndarray) -> np.ndarray:
        """Return simple saturation statistics for an RGB image array."""

        channel_max = array.max(axis=2)
        channel_min = array.min(axis=2)
        saturation = channel_max - channel_min
        return np.array([saturation.mean(), saturation.std()], dtype=np.float32)

    @staticmethod
    def _local_texture(gray: np.ndarray) -> float:
        """Estimate local texture from neighboring brightness variation."""

        if gray.shape[0] < 3 or gray.shape[1] < 3:
            return 0.0
        center = gray[1:-1, 1:-1]
        neighbors = [
            gray[:-2, 1:-1],
            gray[2:, 1:-1],
            gray[1:-1, :-2],
            gray[1:-1, 2:],
        ]
        local_differences = [np.abs(center - neighbor) for neighbor in neighbors]
        return float(np.mean(local_differences))

    @staticmethod
    def _gradient_features(gray: np.ndarray) -> np.ndarray:
        """Return edge and directional gradient features."""

        if gray.shape[0] < 2 or gray.shape[1] < 2:
            return np.zeros(3, dtype=np.float32)
        horizontal = np.abs(np.diff(gray, axis=1))
        vertical = np.abs(np.diff(gray, axis=0))
        horizontal_mean = float(horizontal.mean())
        vertical_mean = float(vertical.mean())
        edge_density = (horizontal_mean + vertical_mean) / 2.0
        return np.array([edge_density, horizontal_mean, vertical_mean], dtype=np.float32)

    @staticmethod
    def _entropy(gray: np.ndarray, bins: int) -> float:
        """Return normalized grayscale entropy."""

        histogram = EmbeddingEngine._histogram(gray, bins=bins)
        nonzero = histogram[histogram > 0]
        if nonzero.size == 0:
            return 0.0
        entropy = -float(np.sum(nonzero * np.log2(nonzero)))
        return entropy / float(np.log2(bins))

"""Deterministic placeholder embeddings for ADE image patches."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ade.preprocessing.patch_extractor import Patch


@dataclass(frozen=True)
class PatchEmbedding:
    """Embedding and trace metadata for a patch."""

    patch: Patch
    vector: np.ndarray


class EmbeddingEngine:
    """Create replaceable patch embeddings from simple image statistics.

    This class intentionally avoids deep learning. Future implementations can
    preserve this interface while replacing ``embed_patch`` with DINOv2, CLIP,
    satellite-specific encoders, or other validated representation models.
    """

    def embed_patch(self, patch: Patch) -> PatchEmbedding:
        """Return a deterministic statistical embedding for one patch."""

        array = patch.array.astype(np.float32) / 255.0
        channel_mean = array.mean(axis=(0, 1))
        channel_std = array.std(axis=(0, 1))
        brightness = np.array([array.mean()], dtype=np.float32)
        edge_density = np.array([self._edge_density(array)], dtype=np.float32)
        vector = np.concatenate([channel_mean, channel_std, brightness, edge_density]).astype(np.float32)
        return PatchEmbedding(patch=patch, vector=vector)

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

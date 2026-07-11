"""Candidate anomaly selection with lightweight diversity constraints."""

from __future__ import annotations

from dataclasses import replace
from math import hypot

import numpy as np

from ade.models import CandidateAnomaly


class AnomalySelector:
    """Select candidate anomalies using novelty ranking plus simple diversity rules."""

    def __init__(
        self,
        enabled: bool = True,
        min_spatial_distance: float = 32.0,
        max_per_image: int = 3,
        prefer_multiple_scales: bool = True,
        min_embedding_distance: float | None = None,
    ) -> None:
        if min_spatial_distance < 0:
            raise ValueError("min_spatial_distance must be non-negative")
        if max_per_image < 1:
            raise ValueError("max_per_image must be positive")
        if min_embedding_distance is not None and min_embedding_distance < 0:
            raise ValueError("min_embedding_distance must be non-negative")

        self.enabled = enabled
        self.min_spatial_distance = float(min_spatial_distance)
        self.max_per_image = int(max_per_image)
        self.prefer_multiple_scales = prefer_multiple_scales
        self.min_embedding_distance = min_embedding_distance

    def select(
        self,
        candidates: list[CandidateAnomaly],
        max_candidates: int | None,
    ) -> list[CandidateAnomaly]:
        """Return selected candidates in deterministic review order."""

        ranked = sorted(
            candidates,
            key=lambda candidate: (
                -candidate.novelty_score,
                str(candidate.embedding.patch.source_path),
                candidate.embedding.patch.y,
                candidate.embedding.patch.x,
                candidate.embedding.patch.scale_label or "",
            ),
        )
        if max_candidates is None:
            max_candidates = len(ranked)
        if max_candidates <= 0:
            return []

        if not self.enabled:
            return [
                self._with_selection_metadata(candidate, index, "high novelty")
                for index, candidate in enumerate(ranked[:max_candidates], start=1)
            ]

        selected: list[CandidateAnomaly] = []
        image_counts: dict[str, int] = {}
        seen_scales: set[str] = set()
        all_scales = {
            candidate.embedding.patch.scale_label or "single-scale"
            for candidate in ranked
        }

        if self.prefer_multiple_scales and len(all_scales) > 1:
            self._select_pass(
                ranked=ranked,
                selected=selected,
                image_counts=image_counts,
                seen_scales=seen_scales,
                max_candidates=max_candidates,
                require_new_scale=True,
            )

        self._select_pass(
            ranked=ranked,
            selected=selected,
            image_counts=image_counts,
            seen_scales=seen_scales,
            max_candidates=max_candidates,
            require_new_scale=False,
        )

        return [
            self._with_selection_metadata(candidate, index, "diversity selected")
            for index, candidate in enumerate(selected[:max_candidates], start=1)
        ]

    def _select_pass(
        self,
        ranked: list[CandidateAnomaly],
        selected: list[CandidateAnomaly],
        image_counts: dict[str, int],
        seen_scales: set[str],
        max_candidates: int,
        require_new_scale: bool,
    ) -> None:
        """Select candidates for one deterministic pass."""

        selected_patch_ids = {
            candidate.embedding.patch.patch_id for candidate in selected
        }
        for candidate in ranked:
            if len(selected) >= max_candidates:
                return
            patch = candidate.embedding.patch
            if patch.patch_id in selected_patch_ids:
                continue
            scale = patch.scale_label or "single-scale"
            if require_new_scale and scale in seen_scales:
                continue
            source = patch.source_path.as_posix()
            if image_counts.get(source, 0) >= self.max_per_image:
                continue
            if not self._is_spatially_diverse(candidate, selected):
                continue
            if not self._is_embedding_diverse(candidate, selected):
                continue
            selected.append(candidate)
            selected_patch_ids.add(patch.patch_id)
            image_counts[source] = image_counts.get(source, 0) + 1
            seen_scales.add(scale)

    def _is_spatially_diverse(
        self,
        candidate: CandidateAnomaly,
        selected: list[CandidateAnomaly],
    ) -> bool:
        """Return whether a candidate is spatially separated from selected patches."""

        patch = candidate.embedding.patch
        center_x = patch.x + patch.width / 2
        center_y = patch.y + patch.height / 2
        for existing in selected:
            existing_patch = existing.embedding.patch
            if existing_patch.source_path != patch.source_path:
                continue
            existing_x = existing_patch.x + existing_patch.width / 2
            existing_y = existing_patch.y + existing_patch.height / 2
            if hypot(center_x - existing_x, center_y - existing_y) < self.min_spatial_distance:
                return False
        return True

    def _is_embedding_diverse(
        self,
        candidate: CandidateAnomaly,
        selected: list[CandidateAnomaly],
    ) -> bool:
        """Return whether a candidate is separated in embedding space."""

        if self.min_embedding_distance is None:
            return True
        for existing in selected:
            distance = float(
                np.linalg.norm(candidate.embedding.vector - existing.embedding.vector)
            )
            if distance < self.min_embedding_distance:
                return False
        return True

    @staticmethod
    def _with_selection_metadata(
        candidate: CandidateAnomaly,
        selection_rank: int,
        selection_reason: str,
    ) -> CandidateAnomaly:
        """Return a candidate with JSON-safe selection metadata."""

        metadata = {
            **candidate.metadata,
            "selection_rank": selection_rank,
            "selection_reason": selection_reason,
        }
        return replace(candidate, metadata=metadata)

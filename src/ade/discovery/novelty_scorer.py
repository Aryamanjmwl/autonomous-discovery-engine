"""Novelty scoring for ADE candidate anomalies."""

from __future__ import annotations

import numpy as np

from ade.models import CandidateAnomaly
from ade.representation.embedding_engine import PatchEmbedding


class NoveltyScorer:
    """Rank patches by distance from the average embedding."""

    def score(
        self,
        embeddings: list[PatchEmbedding],
        max_candidates: int | None = None,
    ) -> list[CandidateAnomaly]:
        """Return candidate anomalies sorted by descending novelty score."""

        if not embeddings:
            return []

        matrix = np.vstack([embedding.vector for embedding in embeddings])
        centroid = matrix.mean(axis=0)
        distances = np.linalg.norm(matrix - centroid, axis=1)

        candidates = [
            CandidateAnomaly(
                embedding=embedding,
                novelty_score=float(distance),
                anomaly_id=f"anomaly-{index + 1:04d}",
            )
            for index, (embedding, distance) in enumerate(
                zip(embeddings, distances, strict=True)
            )
        ]
        candidates.sort(key=lambda candidate: candidate.novelty_score, reverse=True)
        if max_candidates is not None:
            return candidates[:max_candidates]
        return candidates

"""Lightweight novelty scoring backends for ADE candidate anomalies."""

from __future__ import annotations

import numpy as np

from ade.models import CandidateAnomaly
from ade.representation.embedding_engine import PatchEmbedding


class DistanceToCenterScorer:
    """Rank patches by distance from the dataset center."""

    name = "centroid_distance"

    def score(
        self,
        embeddings: list[PatchEmbedding],
        max_candidates: int | None = None,
    ) -> list[CandidateAnomaly]:
        """Return candidate anomalies sorted by descending novelty score."""

        if not embeddings:
            return []

        matrix = _embedding_matrix(embeddings)
        centroid = matrix.mean(axis=0)
        distances = _safe_scores(np.linalg.norm(matrix - centroid, axis=1))

        return _rank_candidates(
            embeddings=embeddings,
            scores=distances,
            backend_name=self.name,
            reason="Feature profile is farther from the dataset center than most records.",
            max_candidates=max_candidates,
            reference_vector=centroid,
        )


class NearestNeighborScorer:
    """Rank patches by distance to their closest neighbor."""

    name = "nearest_neighbor_distance"

    def score(
        self,
        embeddings: list[PatchEmbedding],
        max_candidates: int | None = None,
    ) -> list[CandidateAnomaly]:
        """Return candidate anomalies sorted by nearest-neighbor distance."""

        if not embeddings:
            return []

        matrix = _embedding_matrix(embeddings)
        distances, neighbor_ids = _nearest_neighbor_distances(matrix, embeddings)
        candidates = _rank_candidates(
            embeddings=embeddings,
            scores=distances,
            backend_name=self.name,
            reason="Nearest-neighbor distance is high relative to the rest of the dataset.",
            max_candidates=max_candidates,
        )
        return [
            CandidateAnomaly(
                embedding=candidate.embedding,
                novelty_score=candidate.novelty_score,
                anomaly_id=candidate.anomaly_id,
                preview_path=candidate.preview_path,
                metadata={
                    **candidate.metadata,
                    "nearest_neighbor_id": neighbor_ids[
                        int(candidate.metadata["source_index"])
                    ],
                },
            )
            for candidate in candidates
        ]


class RobustZScoreScorer:
    """Rank patches by robust median absolute deviation distance."""

    name = "robust_z_score"

    def score(
        self,
        embeddings: list[PatchEmbedding],
        max_candidates: int | None = None,
    ) -> list[CandidateAnomaly]:
        """Return candidate anomalies sorted by robust z-score distance."""

        if not embeddings:
            return []

        matrix = _embedding_matrix(embeddings)
        median = np.median(matrix, axis=0)
        mad = np.median(np.abs(matrix - median), axis=0)
        scale = np.where(mad > 1e-12, 1.4826 * mad, 1.0)
        robust_z = (matrix - median) / scale
        robust_z[:, mad <= 1e-12] = 0.0
        scores = _safe_scores(np.linalg.norm(robust_z, axis=1))

        return _rank_candidates(
            embeddings=embeddings,
            scores=scores,
            backend_name=self.name,
            reason="Brightness and texture features differ from the dataset median.",
            max_candidates=max_candidates,
            reference_vector=median,
        )


class NoveltyScorer(DistanceToCenterScorer):
    """Backward-compatible default novelty scorer."""


def _embedding_matrix(embeddings: list[PatchEmbedding]) -> np.ndarray:
    """Return finite embedding matrix data."""

    matrix = np.vstack([embedding.vector for embedding in embeddings]).astype(np.float32)
    return np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)


def _safe_scores(scores: np.ndarray) -> np.ndarray:
    """Return finite float scores."""

    return np.nan_to_num(scores.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)


def _normalized_scores(scores: np.ndarray) -> np.ndarray:
    """Return scores normalized to 0..1 without changing rank order."""

    safe_scores = _safe_scores(scores)
    if safe_scores.size == 0:
        return safe_scores
    score_min = float(safe_scores.min())
    score_max = float(safe_scores.max())
    if score_max <= score_min:
        return np.zeros_like(safe_scores, dtype=np.float32)
    return ((safe_scores - score_min) / (score_max - score_min)).astype(np.float32)


def _rank_candidates(
    embeddings: list[PatchEmbedding],
    scores: np.ndarray,
    backend_name: str,
    reason: str,
    max_candidates: int | None,
    reference_vector: np.ndarray | None = None,
) -> list[CandidateAnomaly]:
    """Build stable ranked candidate anomalies."""

    normalized_scores = _normalized_scores(scores)
    candidates = [
        CandidateAnomaly(
            embedding=embedding,
            novelty_score=float(score),
            anomaly_id=f"anomaly-{index + 1:04d}",
            metadata={
                "scoring_backend": backend_name,
                "source_index": index,
                "normalized_score": float(normalized_scores[index]),
                "reason": reason,
                "feature_deviations": _feature_deviations(embedding, reference_vector),
            },
        )
        for index, (embedding, score) in enumerate(
            zip(embeddings, _safe_scores(scores), strict=True)
        )
    ]
    candidates.sort(
        key=lambda candidate: (
            -candidate.novelty_score,
            candidate.embedding.patch.source_path.as_posix(),
            candidate.embedding.patch.y,
            candidate.embedding.patch.x,
        )
    )
    ranked = [
        CandidateAnomaly(
            embedding=candidate.embedding,
            novelty_score=candidate.novelty_score,
            anomaly_id=candidate.anomaly_id,
            preview_path=candidate.preview_path,
            metadata={**candidate.metadata, "rank": rank},
        )
        for rank, candidate in enumerate(candidates, start=1)
    ]
    if max_candidates is not None:
        return ranked[:max_candidates]
    return ranked


def _nearest_neighbor_distances(
    matrix: np.ndarray,
    embeddings: list[PatchEmbedding],
) -> tuple[np.ndarray, list[str | None]]:
    """Return nearest-neighbor distance and patch ids for each row."""

    if len(embeddings) <= 1:
        return np.zeros(len(embeddings), dtype=np.float32), [None for _ in embeddings]

    distances = np.zeros(len(embeddings), dtype=np.float32)
    neighbor_ids: list[str | None] = []
    for index, row in enumerate(matrix):
        row_distances = np.linalg.norm(matrix - row, axis=1)
        row_distances[index] = np.inf
        nearest_index = int(np.argmin(row_distances))
        distances[index] = float(row_distances[nearest_index])
        neighbor_patch = embeddings[nearest_index].patch
        neighbor_ids.append(neighbor_patch.patch_id or neighbor_patch.source_path.as_posix())
    return _safe_scores(distances), neighbor_ids


def _feature_deviations(
    embedding: PatchEmbedding,
    reference_vector: np.ndarray | None,
    limit: int = 3,
) -> list[dict[str, float | str]]:
    """Return simple top feature deviations from a reference vector."""

    if reference_vector is None or reference_vector.size != embedding.vector.size:
        return []
    deltas = embedding.vector.astype(np.float32) - reference_vector.astype(np.float32)
    feature_names = embedding.metadata.get("feature_names", [])
    if not isinstance(feature_names, list) or len(feature_names) != deltas.size:
        feature_names = [f"feature_{index}" for index in range(deltas.size)]
    indexes = np.argsort(np.abs(deltas))[::-1][:limit]
    return [
        {
            "feature": str(feature_names[int(index)]),
            "deviation": float(deltas[int(index)]),
        }
        for index in indexes
    ]

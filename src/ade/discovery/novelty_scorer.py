"""Novelty scoring for ADE candidate anomalies."""

from __future__ import annotations

from dataclasses import replace

import numpy as np

from ade.models import CandidateAnomaly
from ade.representation.embedding_engine import PatchEmbedding


class NoveltyScorer:
    """Rank patches using normalized distance from the dataset center."""

    SUPPORTED_METRICS = {"euclidean", "cosine"}

    def __init__(self, metric: str = "euclidean") -> None:
        if metric not in self.SUPPORTED_METRICS:
            raise ValueError(
                f"Unsupported novelty metric: {metric}. "
                f"Expected one of: {', '.join(sorted(self.SUPPORTED_METRICS))}."
            )
        self.metric = metric

    def score(
        self,
        embeddings: list[PatchEmbedding],
        max_candidates: int | None = None,
    ) -> list[CandidateAnomaly]:
        """Return candidate anomalies sorted by descending novelty score."""

        if not embeddings:
            return []

        matrix = np.vstack([embedding.vector for embedding in embeddings]).astype(
            np.float32
        )
        normalized = self._normalize(matrix)
        centroid = normalized.mean(axis=0)
        centroid_distances = self._distance_to_vector(normalized, centroid)
        neighbor_distances, neighbor_indices = self._nearest_neighbor_distances(normalized)
        scores = self._combined_scores(centroid_distances, neighbor_distances)

        candidates = [
            CandidateAnomaly(
                embedding=embedding,
                novelty_score=float(score),
                anomaly_id=f"anomaly-{index + 1:04d}",
                metadata={
                    "novelty_metric": self.metric,
                    "centroid_distance": float(centroid_distances[index]),
                    "nearest_neighbor_distance": float(neighbor_distances[index]),
                    "nearest_neighbor_patch_id": self._neighbor_patch_id(
                        embeddings,
                        neighbor_indices[index],
                    ),
                    "feature_deviations": self._feature_deviations(
                        embedding=embedding,
                        z_scores=normalized[index],
                        centroid=centroid,
                    ),
                },
            )
            for index, (embedding, score) in enumerate(
                zip(embeddings, scores, strict=True)
            )
        ]
        candidates.sort(
            key=lambda candidate: (
                -candidate.novelty_score,
                str(candidate.embedding.patch.source_path),
                candidate.embedding.patch.y,
                candidate.embedding.patch.x,
            )
        )
        candidates = [
            replace(
                candidate,
                metadata={
                    **candidate.metadata,
                    "rank": rank,
                    "reason": self._reason(candidate.metadata),
                },
            )
            for rank, candidate in enumerate(candidates, start=1)
        ]
        if max_candidates is not None:
            return candidates[:max_candidates]
        return candidates

    def _distance_to_vector(self, matrix: np.ndarray, vector: np.ndarray) -> np.ndarray:
        """Return finite distances from each row to a reference vector."""

        if self.metric == "cosine":
            distances = np.array(
                [self._cosine_distance(row, vector) for row in matrix],
                dtype=np.float32,
            )
        else:
            distances = np.linalg.norm(matrix - vector, axis=1).astype(np.float32)
        return np.nan_to_num(distances, nan=0.0, posinf=0.0, neginf=0.0)

    def _nearest_neighbor_distances(
        self,
        matrix: np.ndarray,
    ) -> tuple[np.ndarray, list[int | None]]:
        """Return nearest-neighbor distances and row indexes for each embedding."""

        row_count = matrix.shape[0]
        if row_count <= 1:
            return np.zeros(row_count, dtype=np.float32), [None] * row_count

        distances = np.zeros(row_count, dtype=np.float32)
        neighbor_indices: list[int | None] = []
        for index, row in enumerate(matrix):
            row_distances = self._distance_to_vector(matrix, row)
            row_distances[index] = np.inf
            nearest_index = int(np.argmin(row_distances))
            distances[index] = float(row_distances[nearest_index])
            neighbor_indices.append(nearest_index)
        return (
            np.nan_to_num(distances, nan=0.0, posinf=0.0, neginf=0.0),
            neighbor_indices,
        )

    @staticmethod
    def _normalize(matrix: np.ndarray) -> np.ndarray:
        """Return z-scored features while preserving constant columns as zero."""

        if matrix.size == 0:
            return matrix
        means = matrix.mean(axis=0)
        stds = matrix.std(axis=0)
        safe_stds = np.where(stds > 1e-8, stds, 1.0)
        normalized = (matrix - means) / safe_stds
        normalized[:, stds <= 1e-8] = 0.0
        return np.nan_to_num(normalized, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

    @staticmethod
    def _combined_scores(
        centroid_distances: np.ndarray,
        neighbor_distances: np.ndarray,
    ) -> np.ndarray:
        """Combine global and local novelty signals into a finite score."""

        scores = (0.75 * centroid_distances) + (0.25 * neighbor_distances)
        return np.nan_to_num(scores, nan=0.0, posinf=0.0, neginf=0.0).astype(np.float32)

    @staticmethod
    def _cosine_distance(left: np.ndarray, right: np.ndarray) -> float:
        """Return cosine distance with safe handling for zero vectors."""

        denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
        if denominator <= 1e-12:
            return 0.0
        similarity = float(np.dot(left, right) / denominator)
        return 1.0 - max(min(similarity, 1.0), -1.0)

    @staticmethod
    def _neighbor_patch_id(
        embeddings: list[PatchEmbedding],
        neighbor_index: int | None,
    ) -> str | None:
        """Return the patch id for a nearest neighbor index."""

        if neighbor_index is None:
            return None
        neighbor = embeddings[neighbor_index]
        return neighbor.patch.patch_id or neighbor.patch.source_path.as_posix()

    @staticmethod
    def _feature_deviations(
        embedding: PatchEmbedding,
        z_scores: np.ndarray,
        centroid: np.ndarray,
        limit: int = 3,
    ) -> list[dict[str, float | str]]:
        """Return the largest normalized feature deviations from the dataset center."""

        feature_names = embedding.metadata.get("feature_names")
        if not isinstance(feature_names, list) or len(feature_names) != z_scores.size:
            feature_names = [f"feature_{index}" for index in range(z_scores.size)]

        deltas = z_scores - centroid
        ranked_indexes = np.argsort(np.abs(deltas))[::-1][:limit]
        deviations: list[dict[str, float | str]] = []
        for index in ranked_indexes:
            deviations.append(
                {
                    "feature": str(feature_names[int(index)]),
                    "z_deviation": float(deltas[int(index)]),
                }
            )
        return deviations

    @staticmethod
    def _reason(metadata: dict[str, object]) -> str:
        """Return a concise factual reason for a candidate ranking."""

        deviations = metadata.get("feature_deviations")
        if not isinstance(deviations, list) or not deviations:
            return "Patch summary is less similar to the dataset center."

        feature_labels = []
        for deviation in deviations[:2]:
            if not isinstance(deviation, dict):
                continue
            feature = str(deviation.get("feature", "feature")).replace("_", " ")
            direction = (
                "higher"
                if float(deviation.get("z_deviation", 0.0)) >= 0
                else "lower"
            )
            feature_labels.append(f"{direction} {feature}")
        if not feature_labels:
            return "Patch summary is less similar to the dataset center."
        return (
            f"{' and '.join(feature_labels).capitalize()} than most patches "
            "in this dataset."
        )

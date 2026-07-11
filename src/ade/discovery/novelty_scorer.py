"""Lightweight novelty scoring backends for ADE candidate anomalies."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from ade.memory.vector_memory import VectorMemory
from ade.models import CandidateAnomaly
from ade.representation.embedding_engine import PatchEmbedding

SUPPORTED_NOVELTY_STRATEGIES = {"global_distance", "memory_neighbor_distance", "hybrid"}


@dataclass(frozen=True)
class NoveltyScoringMetadata:
    """Run-level metadata for novelty scoring."""

    strategy: str
    memory_aware_enabled: bool
    neighbor_top_k: int
    fallback_used: bool = False
    fallback_reason: str | None = None

    def to_dict(self) -> dict[str, object]:
        """Return JSON-safe scoring metadata."""

        return {
            "novelty_strategy": self.strategy,
            "memory_aware_scoring_enabled": self.memory_aware_enabled,
            "neighbor_top_k": int(self.neighbor_top_k),
            "scoring_fallback_used": bool(self.fallback_used),
            "scoring_fallback_reason": self.fallback_reason,
        }


class NoveltyScorer:
    """Rank patches using configurable deterministic novelty strategies."""

    name = "memory_aware_novelty"

    def __init__(
        self,
        strategy: str = "global_distance",
        neighbor_top_k: int = 5,
        exclude_same_source: bool = False,
        weight_global_distance: float = 0.5,
        weight_neighbor_distance: float = 0.5,
    ) -> None:
        if strategy not in SUPPORTED_NOVELTY_STRATEGIES:
            expected = ", ".join(sorted(SUPPORTED_NOVELTY_STRATEGIES))
            raise ValueError(
                f"Unsupported novelty strategy: {strategy}. Expected one of: {expected}"
            )
        if neighbor_top_k <= 0:
            raise ValueError("neighbor_top_k must be positive")
        if weight_global_distance < 0 or weight_neighbor_distance < 0:
            raise ValueError("novelty scoring weights must be non-negative")
        if strategy == "hybrid" and weight_global_distance + weight_neighbor_distance == 0:
            raise ValueError("hybrid novelty scoring weights must not sum to zero")

        self.strategy = strategy
        self.neighbor_top_k = int(neighbor_top_k)
        self.exclude_same_source = exclude_same_source
        self.weight_global_distance = float(weight_global_distance)
        self.weight_neighbor_distance = float(weight_neighbor_distance)
        self.last_metadata = NoveltyScoringMetadata(
            strategy=strategy,
            memory_aware_enabled=strategy != "global_distance",
            neighbor_top_k=self.neighbor_top_k,
        )

    def score(
        self,
        embeddings: list[PatchEmbedding],
        max_candidates: int | None = None,
        memory: VectorMemory | None = None,
    ) -> list[CandidateAnomaly]:
        """Return candidate anomalies sorted by descending final novelty score."""

        if not embeddings:
            self.last_metadata = NoveltyScoringMetadata(
                strategy=self.strategy,
                memory_aware_enabled=self.strategy != "global_distance",
                neighbor_top_k=self.neighbor_top_k,
            )
            return []

        matrix = _embedding_matrix(embeddings)
        centroid = matrix.mean(axis=0)
        global_distances = np.linalg.norm(matrix - centroid, axis=1).astype(np.float32)
        global_scores = _min_max_normalize(global_distances)

        effective_strategy = self.strategy
        fallback_reason: str | None = None
        if self.strategy != "global_distance" and (memory is None or len(memory) == 0):
            effective_strategy = "global_distance"
            fallback_reason = "vector memory was not available"

        neighbor_distances, neighbor_counts = self._neighbor_distances(
            embeddings=embeddings,
            memory=memory,
        )
        if self.strategy != "global_distance" and np.all(neighbor_counts == 0):
            effective_strategy = "global_distance"
            fallback_reason = "no nearest neighbors were available"

        neighbor_scores = _min_max_normalize(neighbor_distances)
        final_scores = self._final_scores(
            strategy=effective_strategy,
            global_distances=global_distances,
            global_scores=global_scores,
            neighbor_scores=neighbor_scores,
        )

        self.last_metadata = NoveltyScoringMetadata(
            strategy=effective_strategy,
            memory_aware_enabled=self.strategy != "global_distance",
            neighbor_top_k=self.neighbor_top_k,
            fallback_used=effective_strategy != self.strategy,
            fallback_reason=fallback_reason,
        )
        candidates = [
            CandidateAnomaly(
                embedding=embedding,
                novelty_score=float(final_score),
                anomaly_id=f"anomaly-{index + 1:04d}",
                metadata={
                    "scoring_backend": self.name,
                    "source_index": index,
                    "normalized_score": float(_min_max_normalize(final_scores)[index]),
                    "reason": "Patch summary is less similar to the dataset center.",
                    "feature_deviations": _feature_deviations(embedding, centroid),
                    "score_breakdown": {
                        "global_distance_score": float(global_scores[index]),
                        "neighbor_distance_score": float(neighbor_scores[index]),
                        "hybrid_score": float(
                            self._hybrid_score(
                                global_score=float(global_scores[index]),
                                neighbor_score=float(neighbor_scores[index]),
                            )
                        ),
                        "strategy": effective_strategy,
                        "nearest_neighbor_count": int(neighbor_counts[index]),
                    },
                    "raw_global_distance": float(global_distances[index]),
                    "raw_neighbor_distance": float(neighbor_distances[index]),
                },
            )
            for index, (embedding, final_score) in enumerate(
                zip(embeddings, final_scores, strict=True)
            )
        ]
        candidates.sort(
            key=lambda candidate: (
                -candidate.novelty_score,
                str(candidate.embedding.patch.source_path),
                candidate.embedding.patch.y,
                candidate.embedding.patch.x,
                candidate.embedding.patch.scale_label or "",
            )
        )
        candidates = [
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
            return candidates[:max_candidates]
        return candidates

    def _neighbor_distances(
        self,
        embeddings: list[PatchEmbedding],
        memory: VectorMemory | None,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Return nearest-neighbor distances and counts for each embedding."""

        distances: list[float] = []
        counts: list[int] = []
        for embedding in embeddings:
            patch = embedding.patch
            neighbors = (
                memory.query(
                    vector=embedding.vector,
                    top_k=self.neighbor_top_k,
                    exclude_ids={patch.patch_id} if patch.patch_id else None,
                    exclude_source_path=(
                        patch.source_path.as_posix() if self.exclude_same_source else None
                    ),
                )
                if memory is not None
                else []
            )
            counts.append(len(neighbors))
            distances.append(float(neighbors[0].distance) if neighbors else 0.0)
        return np.asarray(distances, dtype=np.float32), np.asarray(counts, dtype=np.int32)

    def _final_scores(
        self,
        strategy: str,
        global_distances: np.ndarray,
        global_scores: np.ndarray,
        neighbor_scores: np.ndarray,
    ) -> np.ndarray:
        """Return final novelty scores for the effective strategy."""

        if strategy == "global_distance":
            return global_distances.astype(np.float32)
        if strategy == "memory_neighbor_distance":
            return neighbor_scores.astype(np.float32)
        return np.asarray(
            [
                self._hybrid_score(
                    global_score=float(global_score),
                    neighbor_score=float(neighbor_score),
                )
                for global_score, neighbor_score in zip(
                    global_scores,
                    neighbor_scores,
                    strict=True,
                )
            ],
            dtype=np.float32,
        )

    def _hybrid_score(self, global_score: float, neighbor_score: float) -> float:
        """Return weighted normalized hybrid score."""

        weight_sum = self.weight_global_distance + self.weight_neighbor_distance
        if weight_sum == 0:
            return 0.0
        return float(
            (
                self.weight_global_distance * global_score
                + self.weight_neighbor_distance * neighbor_score
            )
            / weight_sum
        )


class DistanceToCenterScorer(NoveltyScorer):
    """Registry-compatible scorer using distance from the dataset center."""

    name = "centroid_distance"

    def __init__(self) -> None:
        super().__init__(strategy="global_distance")


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
                    "nearest_neighbor_id": neighbor_ids[int(candidate.metadata["source_index"])],
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


def _embedding_matrix(embeddings: list[PatchEmbedding]) -> np.ndarray:
    """Return finite embedding matrix data."""

    matrix = np.vstack([embedding.vector for embedding in embeddings]).astype(np.float32)
    return np.nan_to_num(matrix, nan=0.0, posinf=0.0, neginf=0.0)


def _safe_scores(scores: np.ndarray) -> np.ndarray:
    """Return finite float scores."""

    return np.nan_to_num(scores.astype(np.float32), nan=0.0, posinf=0.0, neginf=0.0)


def _min_max_normalize(values: np.ndarray) -> np.ndarray:
    """Return deterministic 0..1 min-max normalized values."""

    if values.size == 0:
        return values.astype(np.float32)
    minimum = float(np.min(values))
    maximum = float(np.max(values))
    if not np.isfinite(minimum) or not np.isfinite(maximum) or maximum == minimum:
        return np.zeros_like(values, dtype=np.float32)
    normalized = (values.astype(np.float32) - minimum) / (maximum - minimum)
    return np.clip(normalized, 0.0, 1.0).astype(np.float32)


def _rank_candidates(
    embeddings: list[PatchEmbedding],
    scores: np.ndarray,
    backend_name: str,
    reason: str,
    max_candidates: int | None,
    reference_vector: np.ndarray | None = None,
) -> list[CandidateAnomaly]:
    """Build stable ranked candidate anomalies."""

    normalized_scores = _min_max_normalize(scores)
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
            candidate.embedding.patch.scale_label or "",
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

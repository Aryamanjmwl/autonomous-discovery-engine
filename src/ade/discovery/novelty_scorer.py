"""Novelty scoring for ADE candidate anomalies."""

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

        matrix = np.vstack([embedding.vector for embedding in embeddings])
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

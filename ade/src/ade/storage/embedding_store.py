"""Simple in-memory embedding store for ADE prototypes."""

from __future__ import annotations

from dataclasses import dataclass, field

from ade.representation.embedding_engine import PatchEmbedding


@dataclass
class EmbeddingStore:
    """Store patch embeddings during a pipeline run."""

    embeddings: list[PatchEmbedding] = field(default_factory=list)

    def add_many(self, embeddings: list[PatchEmbedding]) -> None:
        """Add embeddings to the store."""

        self.embeddings.extend(embeddings)

    def all(self) -> list[PatchEmbedding]:
        """Return all stored embeddings."""

        return list(self.embeddings)

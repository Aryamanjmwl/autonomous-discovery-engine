"""Representation backend interfaces for ADE."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

PatchT = TypeVar("PatchT")
EmbeddingT = TypeVar("EmbeddingT")


@runtime_checkable
class EmbeddingBackend(Protocol[PatchT, EmbeddingT]):
    """Convert analysis units into comparable representations."""

    def embed_patch(self, patch: PatchT) -> EmbeddingT:
        """Return one embedding record for one analysis unit."""

    def embed_patches(self, patches: list[PatchT]) -> list[EmbeddingT]:
        """Return embedding records for multiple analysis units."""

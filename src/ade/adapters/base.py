"""Adapter interfaces for ADE dataset inputs."""

from __future__ import annotations

from typing import Protocol, TypeVar, runtime_checkable

RecordT = TypeVar("RecordT")


@runtime_checkable
class DataAdapter(Protocol[RecordT]):
    """Load traceable records from one dataset source.

    ADE's current implementation ships an image-folder adapter. Future adapters
    should keep the same boundary: validate source access, collect metadata, and
    return records without running discovery logic.
    """

    def load(self) -> list[RecordT]:
        """Return source records in deterministic order."""

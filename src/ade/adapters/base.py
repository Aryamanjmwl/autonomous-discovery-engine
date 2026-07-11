"""Adapter interfaces for ADE dataset inputs."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol, TypeVar, runtime_checkable

from ade.models import DatasetSummary

RecordT = TypeVar("RecordT")


@runtime_checkable
class DataAdapter(Protocol[RecordT]):
    """Load traceable records from one dataset source."""

    name: str

    def validate(self) -> None:
        """Raise a clear exception if the input cannot be read."""

    def summarize(self) -> DatasetSummary:
        """Return a lightweight summary of the input source."""

    def iter_records(self) -> Iterator[RecordT]:
        """Yield source records in deterministic order."""

    def load(self) -> list[RecordT]:
        """Return source records in deterministic order."""

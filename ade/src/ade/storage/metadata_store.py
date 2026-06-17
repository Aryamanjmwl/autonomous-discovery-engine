"""Simple in-memory metadata store for ADE prototypes."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MetadataStore:
    """Store structured metadata records during a pipeline run."""

    records: list[dict[str, Any]] = field(default_factory=list)

    def add(self, record: dict[str, Any]) -> None:
        """Add one metadata record."""

        self.records.append(record)

    def all(self) -> list[dict[str, Any]]:
        """Return all metadata records."""

        return list(self.records)

"""Report rendering interfaces for ADE outputs."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ReportRenderer(Protocol):
    """Render discovery results into reviewable artifacts."""

    def generate(self, *args: Any, **kwargs: Any) -> str:
        """Return a human-readable report representation."""

    def generate_json(self, *args: Any, **kwargs: Any) -> dict[str, object]:
        """Return a machine-readable report representation."""

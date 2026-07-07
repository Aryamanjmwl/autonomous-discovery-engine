"""Report rendering interfaces for ADE outputs."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from ade.models import ReportArtifact


@runtime_checkable
class ReportRenderer(Protocol):
    """Render discovery results into reviewable artifacts."""

    name: str

    def render(
        self,
        run_result: Any,
        output_dir: Path | str,
    ) -> list[ReportArtifact]:
        """Render a discovery result into one or more report artifacts."""

    def generate(self, *args: Any, **kwargs: Any) -> str:
        """Return a human-readable report representation."""

    def generate_json(self, *args: Any, **kwargs: Any) -> dict[str, object]:
        """Return a machine-readable report representation."""

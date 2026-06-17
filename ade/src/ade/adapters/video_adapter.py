"""Video adapter placeholder for future ADE media support."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VideoRecord:
    """Metadata describing a video source for future processing."""

    path: Path
    frame_count: int | None = None
    frames_per_second: float | None = None


class VideoAdapter:
    """Placeholder video adapter.

    Future implementations can decode frames, sample temporal windows, and
    stream metadata into the same discovery pipeline.
    """

    def __init__(self, input_dir: Path | str) -> None:
        self.input_dir = Path(input_dir)

    def load(self) -> list[VideoRecord]:
        """Return no records until video support is implemented."""

        return []

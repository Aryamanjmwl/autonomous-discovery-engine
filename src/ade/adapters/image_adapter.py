"""Image loading adapter for local ADE datasets."""

from __future__ import annotations

from pathlib import Path
from collections.abc import Iterable

from ade.models import ImageRecord

SUPPORTED_IMAGE_EXTENSIONS = {".bmp", ".jpeg", ".jpg", ".png", ".tif", ".tiff", ".webp"}


class ImageAdapter:
    """Load image records from a folder without performing model inference."""

    def __init__(
        self,
        input_dir: Path | str,
        supported_image_extensions: Iterable[str] = SUPPORTED_IMAGE_EXTENSIONS,
    ) -> None:
        self.input_dir = Path(input_dir)
        self.supported_image_extensions = {
            extension.lower() for extension in supported_image_extensions
        }

    def load(self) -> list[ImageRecord]:
        """Return image paths and basic metadata for supported files."""

        if not self.input_dir.exists():
            raise FileNotFoundError(f"Input directory does not exist: {self.input_dir}")
        if not self.input_dir.is_dir():
            raise NotADirectoryError(f"Input path is not a directory: {self.input_dir}")

        records: list[ImageRecord] = []
        for path in self._iter_image_paths():
            from PIL import Image

            try:
                with Image.open(path) as image:
                    records.append(
                        ImageRecord(
                            path=path,
                            width=image.width,
                            height=image.height,
                            image_id=path.stem,
                            metadata={
                                "mode": image.mode,
                                "format": image.format,
                            },
                        )
                    )
            except OSError:
                continue
        return records

    def _iter_image_paths(self) -> Iterable[Path]:
        """Yield supported image paths in deterministic order."""

        return (
            path
            for path in sorted(self.input_dir.rglob("*"))
            if path.is_file() and path.suffix.lower() in self.supported_image_extensions
        )

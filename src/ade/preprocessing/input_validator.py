"""Input validation and profiling for ADE visual datasets."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from ade.models import DatasetProfile


def profile_image_folder(
    input_path: Path | str,
    config: dict[str, Any],
    supported_image_extensions: Iterable[str],
    patch_size: int,
    patch_stride: int,
    patch_sizes: list[int] | None = None,
    patch_strides: list[int] | None = None,
) -> DatasetProfile:
    """Inspect an image-folder input and return a structured dataset profile."""

    path = Path(input_path)
    validation = config.get("validation", {})
    min_images = int(validation.get("min_images", 1))
    warn_if_images_below = int(validation.get("warn_if_images_below", 3))
    warn_if_estimated_patches_above = int(
        validation.get("warn_if_estimated_patches_above", 50_000)
    )
    min_image_width = int(validation.get("min_image_width", 32))
    min_image_height = int(validation.get("min_image_height", 32))

    warnings: list[str] = []
    if not path.exists():
        return _invalid_profile(path, [f"Input path does not exist: {path}"])
    if not path.is_dir():
        return _invalid_profile(
            path,
            [f"Input path must be an image folder for the current implementation: {path}"],
        )

    supported_extensions = {extension.lower() for extension in supported_image_extensions}
    files = sorted(item for item in path.rglob("*") if item.is_file())
    supported_files = [
        item for item in files if item.suffix.lower() in supported_extensions
    ]
    unsupported_files = [
        item for item in files if item.suffix.lower() not in supported_extensions
    ]

    widths: list[int] = []
    heights: list[int] = []
    unreadable_files: list[Path] = []
    estimated_patch_count = 0
    for image_path in supported_files:
        try:
            width, height = _read_image_size(image_path)
        except OSError:
            unreadable_files.append(image_path)
            continue

        widths.append(width)
        heights.append(height)
        estimated_patch_count += _estimate_multiscale_patch_count(
            width=width,
            height=height,
            patch_sizes=patch_sizes or [patch_size],
            patch_strides=patch_strides or [patch_stride],
        )

    valid_images = len(widths)
    if unsupported_files:
        warnings.append(f"Unsupported files found: {len(unsupported_files)}")
    if unreadable_files:
        warnings.append(f"Unreadable or corrupt image files found: {len(unreadable_files)}")
    if not supported_files:
        warnings.append(f"No supported image files were found in: {path}")
    if valid_images < min_images:
        warnings.append(
            f"Valid image count is below the configured minimum: {valid_images} < {min_images}"
        )
    elif valid_images < warn_if_images_below:
        warnings.append(
            f"Small visual dataset: {valid_images} valid image(s); "
            "review candidate findings cautiously."
        )
    if widths and (min(widths) < min_image_width or min(heights) < min_image_height):
        warnings.append(
            "Very small images found; patch extraction may produce limited visual evidence."
        )
    if estimated_patch_count > warn_if_estimated_patches_above:
        warnings.append(
            f"Estimated patch count is high: {estimated_patch_count}. "
            "Consider increasing patch size or stride."
        )

    return DatasetProfile(
        input_path=path,
        input_type="image_folder",
        total_files=len(files),
        supported_image_files=len(supported_files),
        unsupported_files=unsupported_files,
        unreadable_files=unreadable_files,
        valid_images=valid_images,
        image_width_min=min(widths) if widths else None,
        image_width_max=max(widths) if widths else None,
        image_height_min=min(heights) if heights else None,
        image_height_max=max(heights) if heights else None,
        unique_image_sizes=sorted(set(zip(widths, heights, strict=True))),
        estimated_patch_count=estimated_patch_count,
        warnings=warnings,
        is_valid=valid_images >= min_images,
    )


def _invalid_profile(input_path: Path, warnings: list[str]) -> DatasetProfile:
    """Return an invalid profile for a path-level validation failure."""

    return DatasetProfile(
        input_path=input_path,
        input_type="image_folder",
        total_files=0,
        supported_image_files=0,
        warnings=warnings,
        is_valid=False,
    )


def _read_image_size(image_path: Path) -> tuple[int, int]:
    """Read an image size without loading full pixel data."""

    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(image_path) as image:
            image.verify()
        with Image.open(image_path) as image:
            return int(image.width), int(image.height)
    except (OSError, UnidentifiedImageError) as error:
        raise OSError(f"Unable to read image: {image_path}") from error


def _estimate_patch_count(
    width: int,
    height: int,
    patch_size: int,
    patch_stride: int,
) -> int:
    """Estimate patch count using the current extractor behavior."""

    if width <= 0 or height <= 0:
        return 0
    x_count = len(range(0, max(width - patch_size + 1, 0), patch_stride))
    y_count = len(range(0, max(height - patch_size + 1, 0), patch_stride))
    return max(x_count * y_count, 1)


def _estimate_multiscale_patch_count(
    width: int,
    height: int,
    patch_sizes: list[int],
    patch_strides: list[int],
) -> int:
    """Estimate total patch count across configured scales."""

    if len(patch_sizes) != len(patch_strides):
        raise ValueError("patch_sizes and patch_strides must have matching lengths")
    return sum(
        _estimate_patch_count(
            width=width,
            height=height,
            patch_size=patch_size,
            patch_stride=patch_stride,
        )
        for patch_size, patch_stride in zip(patch_sizes, patch_strides, strict=True)
    )

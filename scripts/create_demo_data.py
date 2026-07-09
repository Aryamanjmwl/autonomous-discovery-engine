"""Create synthetic ADE demo images without downloading external data."""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ade.config import load_config  # noqa: E402

_CONFIG = load_config()
_DEMO_CONFIG = _CONFIG["demo_data"]

DEFAULT_OUTPUT_DIR = Path(str(_DEMO_CONFIG["output_dir"]))
IMAGE_COUNT = int(_DEMO_CONFIG["image_count"])
IMAGE_SIZE = int(_DEMO_CONFIG["image_size"])
SEED = int(_DEMO_CONFIG["seed"])


def generate_demo_images(output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> list[Path]:
    """Generate synthetic PNG images with normal and unusual visual patches."""

    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    rng = np.random.default_rng(seed=SEED)
    created_paths: list[Path] = []
    for index in range(IMAGE_COUNT):
        image = _base_image(index=index, rng=rng)
        _add_repeated_shapes(image=image, index=index)
        _add_brightness_region(image=image, index=index)
        _add_texture_variation(image=image, index=index, rng=rng)
        _add_unusual_patch(image=image, index=index)

        image_path = output_path / f"demo_image_{index + 1:02d}.png"
        _save_png(image=image, output_path=image_path)
        created_paths.append(image_path)

    return created_paths


def _base_image(index: int, rng: np.random.Generator) -> np.ndarray:
    """Create a mostly plain RGB background with mild deterministic noise."""

    base_value = 96 + index * 8
    image = np.full((IMAGE_SIZE, IMAGE_SIZE, 3), base_value, dtype=np.float32)
    noise = rng.normal(loc=0.0, scale=4.0, size=image.shape)
    return np.clip(image + noise, 0, 255).astype(np.uint8)


def _add_repeated_shapes(image: np.ndarray, index: int) -> None:
    """Add recurring rectangles that should appear normal across images."""

    color = np.array([80 + index * 4, 135, 165], dtype=np.uint8)
    for y in (32, 112, 192):
        for x in (32, 112, 192):
            image[y : y + 24, x : x + 24] = color


def _add_brightness_region(image: np.ndarray, index: int) -> None:
    """Add a broad brightness region to create non-anomalous variation."""

    if index % 2 == 0:
        image[0:128, 128:256] = np.clip(
            image[0:128, 128:256].astype(np.int16) + 28,
            0,
            255,
        ).astype(np.uint8)
    else:
        image[128:256, 0:128] = np.clip(
            image[128:256, 0:128].astype(np.int16) - 22,
            0,
            255,
        ).astype(np.uint8)


def _add_texture_variation(image: np.ndarray, index: int, rng: np.random.Generator) -> None:
    """Add simple texture variation in a consistent patch-sized area."""

    texture = rng.integers(low=0, high=38 + index * 2, size=(64, 64, 1), dtype=np.uint8)
    image[64:128, 0:64] = np.clip(
        image[64:128, 0:64].astype(np.int16) + texture.astype(np.int16),
        0,
        255,
    ).astype(
        np.uint8,
    )


def _add_unusual_patch(image: np.ndarray, index: int) -> None:
    """Add a few intentionally unusual patches for novelty ranking."""

    if index == 2:
        image[128:192, 128:192] = np.array([230, 35, 35], dtype=np.uint8)
        image[144:176, 144:176] = np.array([255, 245, 35], dtype=np.uint8)
    elif index == 4:
        image[0:64, 192:256] = np.array([30, 220, 80], dtype=np.uint8)
        image[16:48, 208:240] = np.array([25, 35, 240], dtype=np.uint8)


def _save_png(image: np.ndarray, output_path: Path) -> None:
    """Save an RGB array as a PNG using Pillow."""

    from PIL import Image

    Image.fromarray(image).save(output_path)


def main() -> None:
    """Generate demo images and print the suggested ADE command."""

    try:
        created_paths = generate_demo_images()
    except ModuleNotFoundError as error:
        if error.name == "PIL":
            raise SystemExit(
                "Pillow is required to create demo PNG images. "
                "Install project dependencies first with: pip install -e .[dev]"
            ) from error
        raise
    print(f"Output folder: {DEFAULT_OUTPUT_DIR}")
    print(f"Images created: {len(created_paths)}")
    print("Suggested ADE demo command:")
    print("python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md")


if __name__ == "__main__":
    main()

"""Create deterministic local image sequences and temporal manifests for ADE demos."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from ade.visual import (  # noqa: E402
    VISUAL_ENGINE_SCHEMA_VERSION,
    TemporalObservation,
    TemporalObservationSequence,
    serialize_temporal_manifest,
)

DEFAULT_OUTPUT_DIR = Path("data/raw/temporal_demo")
IMAGE_SIZE = 64
OBSERVATION_COUNT = 3


def generate_temporal_demo(output_dir: Path | str = DEFAULT_OUTPUT_DIR) -> list[Path]:
    """Generate three small synthetic sequences and return their manifest paths."""

    root = Path(output_dir)
    manifests: list[Path] = []
    sequences = (
        ("scene_revisit_shift", _scene_revisit_shift),
        ("plant_growth_like", _plant_growth_like),
        ("inspection_damage_like", _inspection_damage_like),
    )
    for sequence_id, renderer in sequences:
        sequence_root = root / sequence_id
        images_dir = sequence_root / "images"
        images_dir.mkdir(parents=True, exist_ok=True)
        observations: list[TemporalObservation] = []
        for index in range(OBSERVATION_COUNT):
            image_path = images_dir / f"observation_{index:03d}.png"
            _save_png(renderer(index), image_path)
            observations.append(
                TemporalObservation(
                    observation_id=f"{sequence_id}-o{index:03d}",
                    source_path=f"images/{image_path.name}",
                    sequence_index=index,
                    entity_id=f"synthetic-{sequence_id}",
                    scene_id=f"synthetic-{sequence_id}",
                    metadata={"synthetic_generated_demo": True},
                    width=IMAGE_SIZE,
                    height=IMAGE_SIZE,
                )
            )
        sequence = TemporalObservationSequence(
            schema_version=VISUAL_ENGINE_SCHEMA_VERSION,
            dataset_name="ade-generated-temporal-demo",
            dataset_version="1",
            dataset_root=".",
            sequence_id=sequence_id,
            observations=tuple(observations),
            scene_id=f"synthetic-{sequence_id}",
            entity_id=f"synthetic-{sequence_id}",
            metadata={
                "synthetic_generated_demo": True,
                "description": (
                    "Generated local demo sequence for candidate temporal change review."
                ),
                "requires_human_review": True,
            },
        )
        manifest_path = sequence_root / "manifest.json"
        manifest_path.write_text(
            serialize_temporal_manifest(sequence) + "\n",
            encoding="utf-8",
            newline="\n",
        )
        manifests.append(manifest_path)
    return manifests


def _base_image() -> np.ndarray:
    y, x = np.indices((IMAGE_SIZE, IMAGE_SIZE))
    base = (42 + x // 4 + y // 8).astype(np.uint8)
    return np.stack((base, base + 8, base + 16), axis=2)


def _scene_revisit_shift(index: int) -> np.ndarray:
    image = _base_image()
    x = 12 + index * 5
    image[20:36, x : x + 16] = np.array([210, 150, 55], dtype=np.uint8)
    return image


def _plant_growth_like(index: int) -> np.ndarray:
    image = _base_image()
    y, x = np.indices((IMAGE_SIZE, IMAGE_SIZE))
    radius = 7 + index * 4
    mask = (x - 32) ** 2 + (y - 34) ** 2 <= radius**2
    image[mask] = np.array([55, 175, 85], dtype=np.uint8)
    return image


def _inspection_damage_like(index: int) -> np.ndarray:
    image = _base_image()
    image[12:52, 12:52] = np.array([105, 115, 125], dtype=np.uint8)
    if index >= 1:
        size = 4 + index * 3
        image[28 : 28 + size, 38 : 38 + size] = np.array([220, 65, 55], dtype=np.uint8)
    return image


def _save_png(image: np.ndarray, output_path: Path) -> None:
    from PIL import Image

    Image.fromarray(image, mode="RGB").save(output_path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    try:
        manifests = generate_temporal_demo(args.output_dir)
    except ModuleNotFoundError as error:
        if error.name == "PIL":
            raise SystemExit(
                "Pillow is required to create temporal demo PNG images. "
                "Install project dependencies first with: pip install -e .[dev]"
            ) from error
        raise
    print(f"Generated local demo sequence root: {args.output_dir}")
    print(f"Temporal manifests created: {len(manifests)}")
    for manifest in manifests:
        print(f"- {manifest.as_posix()}")
    print("Candidate temporal changes from this synthetic demo require human review.")


if __name__ == "__main__":
    main()

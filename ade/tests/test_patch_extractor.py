from pathlib import Path

import numpy as np

from ade.preprocessing.patch_extractor import PatchExtractor


def test_patch_extractor_returns_fixed_grid_patches() -> None:
    image = np.zeros((128, 128, 3), dtype=np.uint8)
    extractor = PatchExtractor(patch_size=64, stride=64)

    patches = extractor.extract_from_array(image, source_path=Path("sample.png"))

    assert len(patches) == 4
    assert patches[0].coordinates == (0, 0, 64, 64)
    assert patches[-1].coordinates == (64, 64, 64, 64)
    assert patches[0].array.shape == (64, 64, 3)


def test_patch_extractor_handles_small_images() -> None:
    image = np.zeros((16, 20, 3), dtype=np.uint8)
    extractor = PatchExtractor(patch_size=64)

    patches = extractor.extract_from_array(image, source_path=Path("small.png"))

    assert len(patches) == 1
    assert patches[0].coordinates == (0, 0, 20, 16)
    assert patches[0].array.shape == (16, 20, 3)

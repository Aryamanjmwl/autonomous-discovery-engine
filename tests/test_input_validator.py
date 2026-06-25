from pathlib import Path

import pytest

from ade.config import DEFAULT_CONFIG
from ade.preprocessing.input_validator import profile_image_folder


def _write_png(path: Path, size: tuple[int, int] = (64, 64)) -> None:
    Image = pytest.importorskip("PIL.Image")
    image = Image.new("RGB", size, color=(120, 130, 140))
    image.save(path)


def _profile(path: Path):
    return profile_image_folder(
        input_path=path,
        config=DEFAULT_CONFIG,
        supported_image_extensions=DEFAULT_CONFIG["validation"][
            "supported_image_extensions"
        ],
        patch_size=64,
        patch_stride=64,
    )


def test_profile_valid_image_folder(tmp_path: Path) -> None:
    _write_png(tmp_path / "image_01.png")
    _write_png(tmp_path / "image_02.png")
    _write_png(tmp_path / "image_03.png", size=(128, 64))

    profile = _profile(tmp_path)

    assert profile.is_valid is True
    assert profile.total_files == 3
    assert profile.supported_image_files == 3
    assert profile.valid_images == 3
    assert profile.image_width_min == 64
    assert profile.image_width_max == 128
    assert profile.image_height_min == 64
    assert profile.image_height_max == 64
    assert profile.estimated_patch_count == 4
    assert profile.warnings == []


def test_profile_empty_folder_is_invalid(tmp_path: Path) -> None:
    profile = _profile(tmp_path)

    assert profile.is_valid is False
    assert profile.valid_images == 0
    assert any("No supported image files" in warning for warning in profile.warnings)


def test_profile_reports_unsupported_files(tmp_path: Path) -> None:
    _write_png(tmp_path / "image.png")
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")

    profile = _profile(tmp_path)

    assert profile.is_valid is True
    assert len(profile.unsupported_files) == 1
    assert any("Unsupported files found" in warning for warning in profile.warnings)


def test_profile_reports_corrupt_supported_image(tmp_path: Path) -> None:
    _write_png(tmp_path / "image.png")
    (tmp_path / "corrupt.png").write_bytes(b"not a valid png")

    profile = _profile(tmp_path)

    assert profile.is_valid is True
    assert len(profile.unreadable_files) == 1
    assert profile.valid_images == 1
    assert any("Unreadable or corrupt" in warning for warning in profile.warnings)


def test_profile_warns_for_small_dataset(tmp_path: Path) -> None:
    _write_png(tmp_path / "image.png")

    profile = _profile(tmp_path)

    assert profile.is_valid is True
    assert any("Small visual dataset" in warning for warning in profile.warnings)


def test_profile_serializes_json_safe_paths(tmp_path: Path) -> None:
    _write_png(tmp_path / "image.png")
    (tmp_path / "notes.txt").write_text("not an image", encoding="utf-8")

    data = _profile(tmp_path).to_dict()

    assert data["input_path"] == tmp_path.as_posix()
    assert data["input_type"] == "image_folder"
    assert data["unsupported_file_count"] == 1
    assert data["unreadable_file_count"] == 0
    assert isinstance(data["unsupported_files"][0], str)

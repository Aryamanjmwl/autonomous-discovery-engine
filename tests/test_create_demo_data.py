from pathlib import Path
import importlib.util

import pytest


def _load_demo_module():
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "create_demo_data.py"
    spec = importlib.util.spec_from_file_location("create_demo_data", script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_generate_demo_images_creates_valid_png_files(tmp_path: Path) -> None:
    Image = pytest.importorskip("PIL.Image")
    demo_data = _load_demo_module()
    output_dir = tmp_path / "demo_images"

    created_paths = demo_data.generate_demo_images(output_dir=output_dir)

    assert output_dir.exists()
    assert len(created_paths) == demo_data.IMAGE_COUNT
    assert len(list(output_dir.glob("*.png"))) == demo_data.IMAGE_COUNT

    for path in created_paths:
        assert path.suffix == ".png"
        with Image.open(path) as image:
            assert image.format == "PNG"
            assert image.size == (256, 256)

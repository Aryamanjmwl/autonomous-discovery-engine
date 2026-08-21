from __future__ import annotations

from pathlib import Path

import pytest

from ade.cli import main, run_pipeline
from ade.visual import (
    VisualDatasetRoleError,
    VisualEngineConfig,
    build_reference_memory_from_images,
    load_reference_memory,
    validate_reference_memory,
)


def _write_image(path: Path, value: int = 32) -> None:
    image_module = pytest.importorskip("PIL.Image")
    path.parent.mkdir(parents=True, exist_ok=True)
    image_module.new("RGB", (8, 8), color=(value, value, value)).save(path)


def _build(
    reference_dir: Path,
    storage_root: Path,
    config: VisualEngineConfig | None = None,
):
    return build_reference_memory_from_images(
        reference_dir=reference_dir,
        storage_root=storage_root,
        visual_config=config or VisualEngineConfig(),
        patch_sizes=[4],
        patch_strides=[4],
        supported_extensions=[".png"],
    )


def test_builds_valid_traceable_reference_memory(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    _write_image(reference_dir / "nested" / "normal.png")

    summary = _build(reference_dir, tmp_path / "memory")

    manifest = validate_reference_memory(summary.root)
    with load_reference_memory(summary.root, memory_map=False) as memory:
        assert {record.source_identity for record in memory.records} == {
            "nested/normal.png"
        }
        assert all(record.vector_id.startswith("nested/normal.png::") for record in memory.records)
    assert summary.manifest_path.is_file()
    assert summary.image_count == 1
    assert summary.patch_count == 4
    assert summary.input_vector_count == 4
    assert summary.vector_count == 4
    assert summary.embedding_dimension == 47
    assert manifest.memory_id == summary.memory_id


def test_same_inputs_reuse_the_same_immutable_memory(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    storage_root = tmp_path / "memory"
    _write_image(reference_dir / "normal.png")

    first = _build(reference_dir, storage_root)
    second = _build(reference_dir, storage_root)

    assert second.memory_id == first.memory_id
    assert second.manifest_path == first.manifest_path
    assert [path for path in storage_root.iterdir() if path.is_dir()] == [first.root]


def test_builder_applies_configured_coreset_bound(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    _write_image(reference_dir / "normal.png")
    config = VisualEngineConfig.from_mapping(
        {
            "reference_memory": {
                "coreset_strategy": "deterministic_farthest_first",
                "maximum_vectors": 2,
                "selection_ratio": 1.0,
            }
        }
    )

    summary = _build(reference_dir, tmp_path / "memory", config)

    assert summary.input_vector_count == 4
    assert summary.vector_count == 2


def test_reference_scoring_rejects_the_reference_dataset_as_query(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    _write_image(reference_dir / "normal.png")
    summary = _build(reference_dir, tmp_path / "memory")
    config_path = tmp_path / "reference.yaml"
    config_path.write_text(
        (
            "visual_engine:\n"
            "  execution_mode: reference_anomaly\n"
            "  dataset_roles: [query, reference]\n"
            "  reference_memory:\n"
            "    enabled: true\n"
            f"    manifest_path: \"{summary.manifest_path.as_posix()}\"\n"
            "  reference_scoring:\n"
            "    enabled: true\n"
            "preprocessing:\n"
            "  patch_size: 4\n"
            "  patch_stride: 4\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(VisualDatasetRoleError, match="must be distinct"):
        run_pipeline(
            input_dir=reference_dir,
            output_path=tmp_path / "report.md",
            config_path=config_path,
        )

    assert not (tmp_path / "report.md").exists()


def test_cli_builds_reference_memory_without_analysis_output(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    reference_dir = tmp_path / "reference"
    storage_root = tmp_path / "memory"
    _write_image(reference_dir / "normal.png")
    monkeypatch.setattr(
        "sys.argv",
        [
            "ade",
            "--build-reference-memory",
            str(reference_dir),
            "--reference-memory-output",
            str(storage_root),
            "--patch-size",
            "4",
            "--stride",
            "4",
        ],
    )

    main()

    output = capsys.readouterr().out
    assert "ADE reference memory ready." in output
    assert "Reference images: 1" in output
    manifest_line = next(line for line in output.splitlines() if line.startswith("Manifest: "))
    assert Path(manifest_line.removeprefix("Manifest: ")).is_file()


def test_builder_rejects_empty_reference_folder(tmp_path: Path) -> None:
    reference_dir = tmp_path / "reference"
    reference_dir.mkdir()

    with pytest.raises(ValueError, match="no readable supported images"):
        _build(reference_dir, tmp_path / "memory")

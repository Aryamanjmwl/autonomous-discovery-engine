from __future__ import annotations

from pathlib import Path

import pytest

from ade.cli import main
from ade.visual import (
    MVTEC_AD_LICENSE,
    VisualBenchmarkLabel,
    VisualIntegrityError,
    load_visual_benchmark_manifest,
    qualify_mvtec_ad_category,
)


def _write_image(path: Path, value: int = 32) -> None:
    image_module = pytest.importorskip("PIL.Image")
    path.parent.mkdir(parents=True, exist_ok=True)
    image_module.new("RGB", (8, 8), color=(value, value, value)).save(path)


def _dataset(tmp_path: Path) -> Path:
    root = tmp_path / "mvtec_ad"
    category = root / "bottle"
    _write_image(category / "train" / "good" / "000.png")
    _write_image(category / "test" / "good" / "001.png", 36)
    _write_image(category / "test" / "broken_large" / "002.png", 220)
    _write_image(
        category / "ground_truth" / "broken_large" / "002_mask.png",
        255,
    )
    return root


def test_qualifies_category_and_publishes_canonical_manifest(tmp_path: Path) -> None:
    root = _dataset(tmp_path)
    output = tmp_path / "manifests" / "bottle.json"

    summary = qualify_mvtec_ad_category(
        root,
        category="bottle",
        benchmark_manifest_path=output,
        dataset_version="classic",
    )
    manifest = load_visual_benchmark_manifest(output, strict=True)
    samples = manifest.splits[0].samples

    assert summary.reference_directory == (root / "bottle" / "train" / "good").resolve()
    assert summary.reference_image_count == 1
    assert summary.test_normal_count == 1
    assert summary.test_anomaly_count == 1
    assert summary.anomaly_types == ("broken_large",)
    assert len(summary.dataset_sha256) == 64
    assert manifest.dataset_name == "mvtec-ad-bottle"
    assert manifest.dataset_version == "classic"
    assert manifest.dataset_sha256 == summary.dataset_sha256
    assert manifest.metadata["license"] == MVTEC_AD_LICENSE
    assert manifest.metadata["commercial_use_allowed"] is False
    assert {sample.label for sample in samples} == {
        VisualBenchmarkLabel.NORMAL,
        VisualBenchmarkLabel.ANOMALY,
    }
    anomaly = next(
        sample for sample in samples if sample.label == VisualBenchmarkLabel.ANOMALY
    )
    assert anomaly.anomaly_type == "broken_large"
    assert anomaly.mask_path == "ground_truth/broken_large/002_mask.png"
    assert len(anomaly.image_sha256 or "") == 64
    assert len(anomaly.mask_sha256 or "") == 64


def test_qualification_is_idempotent_but_refuses_manifest_replacement(
    tmp_path: Path,
) -> None:
    root = _dataset(tmp_path)
    output = tmp_path / "bottle.json"

    first = qualify_mvtec_ad_category(
        root,
        category="bottle",
        benchmark_manifest_path=output,
    )
    second = qualify_mvtec_ad_category(
        root,
        category="bottle",
        benchmark_manifest_path=output,
    )
    _write_image(root / "bottle" / "test" / "good" / "001.png", 64)

    assert second == first
    with pytest.raises(VisualIntegrityError, match="Refusing to overwrite"):
        qualify_mvtec_ad_category(
            root,
            category="bottle",
            benchmark_manifest_path=output,
        )


def test_qualification_requires_anomaly_masks(tmp_path: Path) -> None:
    root = _dataset(tmp_path)
    (root / "bottle" / "ground_truth" / "broken_large" / "002_mask.png").unlink()

    with pytest.raises(VisualIntegrityError, match="mask is missing"):
        qualify_mvtec_ad_category(
            root,
            category="bottle",
            benchmark_manifest_path=tmp_path / "bottle.json",
        )


@pytest.mark.parametrize(
    "category",
    ["../bottle", "objects/bottle", "/bottle", "not_an_official_category"],
)
def test_qualification_rejects_unsafe_category_paths(
    tmp_path: Path,
    category: str,
) -> None:
    root = _dataset(tmp_path)

    with pytest.raises(VisualIntegrityError):
        qualify_mvtec_ad_category(
            root,
            category=category,
            benchmark_manifest_path=tmp_path / "bottle.json",
        )


def test_cli_qualifies_category_without_analysis_inputs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    root = _dataset(tmp_path)
    output = tmp_path / "bottle.json"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ade",
            "--qualify-mvtec-ad",
            str(root),
            "--mvtec-category",
            "bottle",
            "--benchmark-manifest-output",
            str(output),
        ],
    )

    main()

    terminal = capsys.readouterr().out
    assert "ADE MVTec AD category qualified." in terminal
    assert "Reference images: 1" in terminal
    assert "Normal test images: 1" in terminal
    assert "Anomalous test images: 1" in terminal
    assert "commercial use is not allowed" in terminal
    assert output.is_file()


def test_qualification_rejects_reference_directory_outside_category(
    tmp_path: Path,
) -> None:
    root = _dataset(tmp_path)
    reference_directory = root / "bottle" / "train" / "good"
    (reference_directory / "000.png").unlink()
    reference_directory.rmdir()
    outside = tmp_path / "outside"
    _write_image(outside / "000.png")
    try:
        reference_directory.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Directory symlinks are unavailable on this platform")

    with pytest.raises(VisualIntegrityError, match="outside the category root"):
        qualify_mvtec_ad_category(
            root,
            category="bottle",
            benchmark_manifest_path=tmp_path / "bottle.json",
        )

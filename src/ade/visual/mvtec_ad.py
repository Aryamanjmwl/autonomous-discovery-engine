"""Strict local qualification for one MVTec AD category."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path

from ade.visual.benchmark_contracts import (
    VisualBenchmarkDatasetManifest,
    VisualBenchmarkLabel,
    VisualBenchmarkSample,
    VisualBenchmarkSplit,
)
from ade.visual.benchmark_manifests import (
    serialize_visual_benchmark_manifest,
    validate_visual_benchmark_manifest,
)
from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.errors import VisualIntegrityError
from ade.visual.fingerprints import normalize_relative_path, sha256_file

MVTEC_AD_SOURCE_URL = "https://www.mvtec.com/research-teaching/datasets/mvtec-ad"
MVTEC_AD_LICENSE = "CC BY-NC-SA 4.0"


@dataclass(frozen=True)
class MVTecADQualificationSummary:
    """Traceable local inputs produced for one qualified category."""

    category: str
    category_root: Path
    reference_directory: Path
    benchmark_manifest_path: Path
    dataset_sha256: str
    reference_image_count: int
    test_normal_count: int
    test_anomaly_count: int
    anomaly_types: tuple[str, ...]


def qualify_mvtec_ad_category(
    dataset_root: Path,
    *,
    category: str,
    benchmark_manifest_path: Path,
    dataset_version: str = "official-download",
) -> MVTecADQualificationSummary:
    """Validate an official local category layout and publish a canonical manifest."""

    normalized_category = normalize_relative_path(category)
    if normalized_category != category or "/" in normalized_category:
        raise VisualIntegrityError("MVTec AD category must be one canonical directory name")
    if not dataset_version.strip():
        raise VisualIntegrityError("MVTec AD dataset version must be non-empty")

    root = dataset_root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"MVTec AD dataset root is not a directory: {dataset_root}")
    category_root = (root / normalized_category).resolve()
    _require_contained_directory(root, category_root, "category")

    reference_directory = category_root / "train" / "good"
    test_directory = category_root / "test"
    ground_truth_directory = category_root / "ground_truth"
    _require_directory(reference_directory, "train/good")
    _require_directory(test_directory / "good", "test/good")
    _require_directory(ground_truth_directory, "ground_truth")

    reference_images = _png_files(reference_directory)
    normal_images = _png_files(test_directory / "good")
    defect_directories = tuple(
        path
        for path in sorted(test_directory.iterdir(), key=lambda item: item.name)
        if path.is_dir() and path.name != "good"
    )
    if not reference_images:
        raise VisualIntegrityError("MVTec AD train/good contains no PNG reference images")
    if not normal_images:
        raise VisualIntegrityError("MVTec AD test/good contains no PNG images")
    if not defect_directories:
        raise VisualIntegrityError("MVTec AD test contains no anomaly directories")

    samples: list[VisualBenchmarkSample] = []
    for image_path in normal_images:
        relative = _relative_file(category_root, image_path)
        samples.append(
            VisualBenchmarkSample(
                sample_id=f"{category}:good:{image_path.stem}",
                image_path=relative,
                label=VisualBenchmarkLabel.NORMAL,
                category=category,
                image_sha256=sha256_file(image_path),
            )
        )

    anomaly_types: list[str] = []
    anomaly_count = 0
    for defect_directory in defect_directories:
        defect_type = defect_directory.name
        defect_images = _png_files(defect_directory)
        if not defect_images:
            raise VisualIntegrityError(
                "MVTec AD anomaly directory contains no PNG images",
                context={"anomaly_type": defect_type},
            )
        mask_directory = ground_truth_directory / defect_type
        _require_directory(mask_directory, f"ground_truth/{defect_type}")
        anomaly_types.append(defect_type)
        for image_path in defect_images:
            mask_path = mask_directory / f"{image_path.stem}_mask.png"
            if not mask_path.is_file():
                raise VisualIntegrityError(
                    "MVTec AD anomaly mask is missing",
                    context={
                        "anomaly_type": defect_type,
                        "image": image_path.name,
                        "expected_mask": mask_path.name,
                    },
                )
            image_relative = _relative_file(category_root, image_path)
            mask_relative = _relative_file(category_root, mask_path)
            samples.append(
                VisualBenchmarkSample(
                    sample_id=f"{category}:{defect_type}:{image_path.stem}",
                    image_path=image_relative,
                    label=VisualBenchmarkLabel.ANOMALY,
                    mask_path=mask_relative,
                    anomaly_type=defect_type,
                    category=category,
                    image_sha256=sha256_file(image_path),
                    mask_sha256=sha256_file(mask_path),
                )
            )
            anomaly_count += 1

    dataset_sha256 = _sample_content_fingerprint(samples)
    manifest = VisualBenchmarkDatasetManifest(
        schema_version=VISUAL_ENGINE_SCHEMA_VERSION,
        dataset_name=f"mvtec-ad-{category}",
        dataset_version=dataset_version,
        dataset_root=str(category_root),
        splits=(
            VisualBenchmarkSplit(
                "test",
                tuple(sorted(samples, key=lambda item: item.sample_id)),
            ),
        ),
        dataset_sha256=dataset_sha256,
        metadata={
            "adapter": "mvtec_ad",
            "source_url": MVTEC_AD_SOURCE_URL,
            "license": MVTEC_AD_LICENSE,
            "commercial_use_allowed": False,
            "category": category,
            "reference_directory": str(reference_directory),
            "reference_image_count": len(reference_images),
        },
    )
    validate_visual_benchmark_manifest(
        manifest,
        manifest_path=benchmark_manifest_path,
        strict=True,
    )
    _write_immutable_manifest(benchmark_manifest_path, manifest)

    return MVTecADQualificationSummary(
        category=category,
        category_root=category_root,
        reference_directory=reference_directory,
        benchmark_manifest_path=benchmark_manifest_path.resolve(),
        dataset_sha256=dataset_sha256,
        reference_image_count=len(reference_images),
        test_normal_count=len(normal_images),
        test_anomaly_count=anomaly_count,
        anomaly_types=tuple(anomaly_types),
    )


def _png_files(directory: Path) -> tuple[Path, ...]:
    return tuple(
        path
        for path in sorted(directory.iterdir(), key=lambda item: item.name)
        if path.is_file() and path.suffix.lower() == ".png"
    )


def _require_directory(path: Path, label: str) -> None:
    if not path.is_dir():
        raise VisualIntegrityError(f"MVTec AD layout is missing required directory: {label}")


def _require_contained_directory(root: Path, path: Path, label: str) -> None:
    try:
        path.relative_to(root)
    except ValueError as error:
        raise VisualIntegrityError(
            f"MVTec AD {label} resolves outside the dataset root"
        ) from error
    _require_directory(path, label)


def _relative_file(root: Path, path: Path) -> str:
    resolved = path.resolve()
    try:
        relative = resolved.relative_to(root)
    except ValueError as error:
        raise VisualIntegrityError(
            "MVTec AD file resolves outside the category root",
            context={"path": str(path)},
        ) from error
    if not resolved.is_file():
        raise VisualIntegrityError(
            "MVTec AD input must be a regular file",
            context={"path": str(path)},
        )
    return normalize_relative_path(relative)


def _sample_content_fingerprint(samples: list[VisualBenchmarkSample]) -> str:
    records = [
        {
            "sample_id": sample.sample_id,
            "image_path": sample.image_path,
            "image_sha256": sample.image_sha256,
            "mask_path": sample.mask_path,
            "mask_sha256": sample.mask_sha256,
        }
        for sample in sorted(samples, key=lambda item: item.sample_id)
    ]
    payload = json.dumps(
        records,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _write_immutable_manifest(
    path: Path,
    manifest: VisualBenchmarkDatasetManifest,
) -> None:
    payload = serialize_visual_benchmark_manifest(manifest) + "\n"
    target = path.resolve()
    if target.exists():
        if not target.is_file() or target.read_text(encoding="utf-8") != payload:
            raise VisualIntegrityError(
                "Refusing to overwrite a different benchmark manifest",
                context={"path": str(target)},
            )
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{target.name}.",
        suffix=".tmp",
        dir=target.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(payload)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)

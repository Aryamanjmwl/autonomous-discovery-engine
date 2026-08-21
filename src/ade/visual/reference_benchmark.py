"""Execute ADE reference scoring against an explicit visual benchmark manifest."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

from ade.cancellation import CancellationToken
from ade.config import load_config
from ade.models import EmbeddingRecord, ImageRecord
from ade.preprocessing.patch_extractor import PatchExtractor
from ade.representation.embedding_engine import EmbeddingEngine
from ade.visual.benchmark_contracts import (
    VisualBenchmarkPrediction,
    VisualBenchmarkResult,
    VisualBenchmarkRunConfig,
)
from ade.visual.benchmark_evaluation import evaluate_visual_benchmark
from ade.visual.benchmark_manifests import (
    load_visual_benchmark_manifest,
    resolve_visual_benchmark_root,
)
from ade.visual.config import VisualEngineConfig
from ade.visual.errors import VisualConfigurationError, VisualIntegrityError
from ade.visual.fingerprints import fingerprint_visual_content
from ade.visual.reference_pipeline import score_configured_reference_memory


def run_reference_benchmark(
    manifest_path: Path,
    *,
    config_path: Path,
    run_config: VisualBenchmarkRunConfig,
    cancellation_token: CancellationToken | None = None,
    generated_at: str | None = None,
) -> VisualBenchmarkResult:
    """Score one labeled benchmark split with the configured reference memory."""

    config = load_config(config_path)
    visual_config = VisualEngineConfig.from_mapping(config["visual_engine"])
    if not visual_config.reference_scoring.enabled:
        raise VisualConfigurationError(
            "Reference benchmark execution requires reference_scoring.enabled=true"
        )

    manifest = load_visual_benchmark_manifest(manifest_path, strict=True)
    split = next(
        (item for item in manifest.splits if item.name == run_config.split_name),
        None,
    )
    if split is None:
        raise VisualIntegrityError(
            f"Benchmark split does not exist: {run_config.split_name}"
        )
    dataset_root = resolve_visual_benchmark_root(manifest, manifest_path)
    image_paths = tuple(dataset_root / sample.image_path for sample in split.samples)

    # Enforce configured file-count and file-size bounds before image decoding.
    fingerprint_visual_content(
        dataset_root,
        image_paths,
        visual_config,
    )
    if cancellation_token is not None:
        cancellation_token.checkpoint()

    preprocessing = config["preprocessing"]
    patch_sizes = [int(value) for value in preprocessing["patch_sizes"]]
    patch_strides = [int(value) for value in preprocessing["patch_strides"]]
    if not patch_sizes or len(patch_sizes) != len(patch_strides):
        raise VisualConfigurationError(
            "Benchmark patch sizes and strides must be non-empty and aligned"
        )
    extractor = PatchExtractor(
        patch_size=patch_sizes[0],
        stride=patch_strides[0],
        patch_sizes=patch_sizes,
        patch_strides=patch_strides,
    )
    embedding_engine = EmbeddingEngine()
    image_records: list[ImageRecord] = []
    embeddings: list[EmbeddingRecord] = []

    for sample, image_path in zip(split.samples, image_paths, strict=True):
        if cancellation_token is not None:
            cancellation_token.checkpoint()
        try:
            from PIL import Image

            with Image.open(image_path) as image:
                image_record = ImageRecord(
                    path=image_path,
                    width=image.width,
                    height=image.height,
                    image_id=sample.sample_id,
                    metadata={"mode": image.mode, "format": image.format},
                )
            patches = [
                replace(
                    patch,
                    patch_id=(
                        f"{sample.sample_id}::{patch.scale_id or 'default'}::"
                        f"{patch.x}:{patch.y}:{patch.width}:{patch.height}"
                    ),
                    image_id=sample.sample_id,
                )
                for patch in extractor.extract_from_path(image_path)
            ]
        except OSError as error:
            raise VisualIntegrityError(
                "Benchmark image could not be decoded",
                context={
                    "sample_id": sample.sample_id,
                    "image_path": sample.image_path,
                },
            ) from error
        image_records.append(image_record)
        embeddings.extend(embedding_engine.embed_patches(patches))

    scoring = score_configured_reference_memory(
        input_dir=dataset_root,
        image_records=image_records,
        embeddings=embeddings,
        visual_config=visual_config,
        cancellation_token=cancellation_token,
    )
    if scoring is None:
        raise VisualConfigurationError("Reference benchmark scoring was not executed")

    predictions = tuple(
        VisualBenchmarkPrediction(
            sample_id=item.image_id,
            score=item.raw_score,
            score_source=f"reference_scoring:{scoring.summary.scoring_id}",
        )
        for item in scoring.image_scores
    )
    return evaluate_visual_benchmark(
        manifest,
        predictions,
        run_config,
        benchmark_manifest_path=str(manifest_path.resolve()),
        generated_at=generated_at,
    )

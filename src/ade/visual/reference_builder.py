"""Build immutable visual reference memory from an explicit image dataset."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ade.adapters.image_adapter import ImageAdapter
from ade.cancellation import CancellationToken
from ade.preprocessing.patch_extractor import PatchExtractor
from ade.representation.embedding_engine import EmbeddingEngine
from ade.visual.config import VisualEngineConfig
from ade.visual.contracts import VisualDatasetRole
from ade.visual.errors import VisualConfigurationError, VisualIntegrityError
from ade.visual.fingerprints import (
    fingerprint_visual_content,
    normalize_relative_path,
)
from ade.visual.reference_contracts import ReferenceVectorRecord
from ade.visual.reference_memory import build_reference_memory
from ade.visual.representation import LightweightVisualRepresentationProvider


@dataclass(frozen=True)
class ReferenceMemoryBuildSummary:
    """Traceable result of one reference-memory build or immutable reuse."""

    root: Path
    manifest_path: Path
    memory_id: str
    reference_dataset_fingerprint: str
    image_count: int
    patch_count: int
    input_vector_count: int
    vector_count: int
    embedding_dimension: int


def build_reference_memory_from_images(
    *,
    reference_dir: Path,
    storage_root: Path,
    visual_config: VisualEngineConfig,
    patch_sizes: list[int],
    patch_strides: list[int],
    supported_extensions: list[str],
    cancellation_token: CancellationToken | None = None,
) -> ReferenceMemoryBuildSummary:
    """Build or resolve a compatible immutable memory from explicit reference images."""

    visual_config.validate()
    if not patch_sizes or len(patch_sizes) != len(patch_strides):
        raise VisualConfigurationError(
            "Patch sizes and strides must be non-empty and have matching lengths"
        )
    if visual_config.representation.provider != "lightweight":
        raise VisualConfigurationError(
            "Reference-memory CLI builds currently support only "
            "representation.provider=lightweight"
        )
    provider = LightweightVisualRepresentationProvider(visual_config.representation)
    metadata = provider.metadata
    if (
        visual_config.backend_id != metadata.provider_name
        or visual_config.backend_version != metadata.provider_version
    ):
        raise VisualConfigurationError(
            "visual_engine backend identity does not match the selected representation provider"
        )

    images = ImageAdapter(
        reference_dir,
        supported_image_extensions=supported_extensions,
    ).load()
    if not images:
        raise VisualIntegrityError(
            "Reference dataset contains no readable supported images",
            context={"reference_dir": str(reference_dir)},
        )
    if cancellation_token is not None:
        cancellation_token.checkpoint()

    extractor = PatchExtractor(
        patch_size=patch_sizes[0],
        stride=patch_strides[0],
        patch_sizes=patch_sizes,
        patch_strides=patch_strides,
    )
    embedding_engine = EmbeddingEngine()
    reference_root = reference_dir.resolve()
    records: list[ReferenceVectorRecord] = []
    patch_count = 0
    for image in images:
        if cancellation_token is not None:
            cancellation_token.checkpoint()
        patches = extractor.extract_from_path(image.path)
        patch_count += len(patches)
        for embedding in embedding_engine.embed_patches(patches):
            patch = embedding.patch
            source_identity = normalize_relative_path(
                patch.source_path.resolve().relative_to(reference_root)
            )
            vector_id = (
                f"{source_identity}::{patch.scale_id or 'default'}::"
                f"{patch.x}:{patch.y}:{patch.width}:{patch.height}"
            )
            records.append(
                ReferenceVectorRecord(
                    vector_id=vector_id,
                    source_identity=source_identity,
                    vector=embedding.vector,
                    x=patch.x,
                    y=patch.y,
                    width=patch.width,
                    height=patch.height,
                    scale_id=patch.scale_id,
                    scale_label=patch.scale_label,
                    metadata=dict(embedding.metadata),
                )
            )

    if cancellation_token is not None:
        cancellation_token.checkpoint()
    dataset_fingerprint = fingerprint_visual_content(
        reference_dir,
        (image.path for image in images),
        visual_config,
    )
    if cancellation_token is not None:
        cancellation_token.begin_finalization()

    memory_config = visual_config.reference_memory
    with build_reference_memory(
        records,
        storage_root=storage_root,
        dataset_role=VisualDatasetRole.REFERENCE,
        reference_dataset_fingerprint=dataset_fingerprint,
        configuration_fingerprint=metadata.configuration_fingerprint,
        backend_id=metadata.provider_name,
        backend_version=metadata.provider_version,
        distance_metric=memory_config.metric,
        coreset_strategy=memory_config.coreset_strategy,
        maximum_vectors=memory_config.maximum_vectors,
        selection_ratio=memory_config.selection_ratio,
        random_seed=memory_config.seed,
    ) as memory:
        manifest = memory.manifest
        root = memory.root
    return ReferenceMemoryBuildSummary(
        root=root,
        manifest_path=root / "manifest.json",
        memory_id=manifest.memory_id,
        reference_dataset_fingerprint=manifest.reference_dataset_fingerprint,
        image_count=len(images),
        patch_count=patch_count,
        input_vector_count=len(records),
        vector_count=manifest.vector_count,
        embedding_dimension=manifest.embedding_dimension,
    )

"""Opt-in orchestration for immutable visual reference scoring."""

from __future__ import annotations

from pathlib import Path

from ade.cancellation import CancellationToken
from ade.models import EmbeddingRecord, ImageRecord
from ade.visual.config import VisualEngineConfig, VisualReferenceScoringConfig
from ade.visual.errors import VisualConfigurationError
from ade.visual.fingerprints import fingerprint_visual_dataset
from ade.visual.reference_memory import load_reference_memory
from ade.visual.reference_scoring import score_reference_anomalies
from ade.visual.representation import LightweightVisualRepresentationProvider
from ade.visual.scoring_artifacts import publish_scoring_artifacts
from ade.visual.scoring_contracts import (
    QueryPatchRecord,
    ReferenceScoringProvenance,
    ReferenceScoringResult,
)


def score_configured_reference_memory(
    *,
    input_dir: Path,
    image_records: list[ImageRecord],
    embeddings: list[EmbeddingRecord],
    visual_config: VisualEngineConfig,
    cancellation_token: CancellationToken | None = None,
) -> ReferenceScoringResult | None:
    """Score query embeddings against an explicitly configured reference memory."""

    if not visual_config.reference_scoring.enabled:
        return None
    if visual_config.representation.provider != "lightweight":
        raise VisualConfigurationError(
            "The image-folder pipeline currently supports reference scoring only "
            "with representation.provider=lightweight"
        )

    manifest_value = visual_config.reference_memory.manifest_path
    if manifest_value is None:
        raise VisualConfigurationError(
            "Enabled reference scoring requires reference_memory.manifest_path"
        )
    manifest_path = Path(manifest_value).resolve()
    if manifest_path.name != "manifest.json":
        raise VisualConfigurationError(
            "reference_memory.manifest_path must identify an immutable manifest.json"
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

    if cancellation_token is not None:
        cancellation_token.checkpoint()
    query_fingerprint = fingerprint_visual_dataset(
        input_dir,
        (record.path for record in image_records),
        visual_config,
    )
    dimensions = {
        record.path.resolve(): (record.width, record.height) for record in image_records
    }
    query_records = tuple(
        QueryPatchRecord.from_embedding_record(
            embedding,
            image_width=dimensions[embedding.patch.source_path.resolve()][0],
            image_height=dimensions[embedding.patch.source_path.resolve()][1],
        )
        for embedding in embeddings
    )
    if cancellation_token is not None:
        cancellation_token.checkpoint()

    with load_reference_memory(
        manifest_path.parent,
        memory_map=visual_config.reference_memory.memory_map,
        expected_backend_id=metadata.provider_name,
        expected_backend_version=metadata.provider_version,
        expected_dimension=metadata.feature_dimension,
        expected_metric=visual_config.reference_scoring.metric,
        expected_configuration_fingerprint=metadata.configuration_fingerprint,
    ) as memory:
        provenance = ReferenceScoringProvenance(
            query_dataset_fingerprint=query_fingerprint.fingerprint,
            reference_dataset_fingerprint=memory.manifest.reference_dataset_fingerprint,
            configuration_fingerprint=metadata.configuration_fingerprint,
            backend_id=metadata.provider_name,
            backend_version=metadata.provider_version,
            deterministic=metadata.deterministic,
            device=metadata.device,
        )
        result = score_reference_anomalies(
            query_records,
            memory,
            visual_config.reference_scoring,
            provenance,
        )
    if cancellation_token is not None:
        cancellation_token.checkpoint()
    return result


def publish_reference_scoring_evidence(
    result: ReferenceScoringResult | None,
    *,
    output_path: Path,
    config: VisualReferenceScoringConfig,
) -> dict[str, object] | None:
    """Publish immutable scoring artifacts and return report-backed summaries."""

    if result is None:
        return None
    artifacts, root = publish_scoring_artifacts(
        result,
        output_path.parent / f"{output_path.stem}_reference_scoring",
        config,
    )
    summary = next(item for item in artifacts if item.artifact_id == "scoring-summary")
    artifact_path = root / summary.relative_path
    common = {
        "artifact_path": str(artifact_path),
        "artifact_fingerprint": summary.sha256,
        "requires_human_review": True,
    }
    previews = [
        str(root / item.relative_path)
        for item in artifacts
        if item.artifact_type == "preview"
    ]
    return {
        "reference_scoring_summary": {
            **common,
            "calibrated": False,
            "candidate_count": len(result.image_scores),
            "scoring_id": result.summary.scoring_id,
            "reference_memory_id": result.summary.reference_memory_id,
            "metric": result.summary.metric,
        },
        "spatial_anomaly_map_summary": {
            **common,
            "map_count": len(result.anomaly_maps),
            "preview_paths": previews,
        },
    }

"""Command-line entry point for the ADE prototype pipeline."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ade.adapters.image_adapter import ImageAdapter
from ade.adapters.tabular_adapter import TabularAdapter
from ade.adapters.timeseries_adapter import TimeSeriesAdapter
from ade.cancellation import CancellationToken
from ade.config import load_config
from ade.dashboard import export_local_dashboard, generate_dashboard
from ade.dashboard.service import DEFAULT_DASHBOARD_DIR
from ade.discovery.anomaly_selector import AnomalySelector
from ade.discovery.concept_clusterer import ConceptClusterer
from ade.discovery.confidence_scorer import ConfidenceScorer
from ade.discovery.evidence_collector import EvidenceCollector
from ade.discovery.novelty_scorer import NoveltyScorer
from ade.discovery.tabular import TabularConceptGrouper, TabularNoveltyScorer
from ade.discovery.timeseries import TimeSeriesConceptGrouper, TimeSeriesNoveltyScorer
from ade.feedback import (
    ALLOWED_FEEDBACK_LABELS,
    ALLOWED_TARGET_TYPES,
    FeedbackStore,
    ReviewFeedback,
)
from ade.memory.review_memory import build_review_memory_summary
from ade.memory.vector_memory import VectorMemory
from ade.models import CandidateAnomaly, DatasetProfile
from ade.preprocessing.input_validator import profile_image_folder
from ade.preprocessing.patch_extractor import PatchExtractor
from ade.reasoning.hypothesis_generator import HypothesisGenerator
from ade.reporting.html_report import write_html_report
from ade.reporting.report_generator import DatasetSummary, ReportGenerator
from ade.reporting.report_validator import validate_report_file
from ade.reporting.run_index import load_run_index
from ade.reporting.tabular_report_generator import TabularReportGenerator
from ade.reporting.temporal_report import (
    validate_temporal_report_file,
    write_temporal_html_report,
    write_temporal_report,
)
from ade.reporting.timeseries_report_generator import TimeSeriesReportGenerator
from ade.representation.embedding_engine import EmbeddingEngine, PatchEmbedding
from ade.representation.tabular_engine import TabularFeatureEngine
from ade.representation.timeseries_engine import TimeSeriesFeatureEngine
from ade.visual import (
    analyze_temporal_change,
    load_temporal_manifest,
    publish_temporal_change_artifact,
    validate_temporal_change_artifact,
)
from ade.visual.temporal_contracts import TemporalChangeStrategy

DEFAULT_RUN_INDEX_PATH = Path("data/reports/runs/index.json")


def build_parser() -> argparse.ArgumentParser:
    """Create the ADE command-line parser."""

    parser = argparse.ArgumentParser(description="Run the ADE prototype image pipeline.")
    parser.add_argument(
        "command",
        nargs="?",
        choices=["dashboard"],
        help="Optional command. Use `dashboard` to generate a local static dashboard.",
    )
    parser.add_argument(
        "--input",
        type=Path,
        help="Directory containing input images, or a CSV file for tabular discovery.",
    )
    parser.add_argument("--output", type=Path, help="Markdown report output path.")
    parser.add_argument(
        "--modality",
        choices=["image", "tabular", "timeseries"],
        default=None,
        help="Optional input modality. CSV defaults to tabular unless set to timeseries.",
    )
    parser.add_argument(
        "--timestamp-column",
        default=None,
        help="Timestamp column for --modality timeseries.",
    )
    parser.add_argument(
        "--entity-column",
        default=None,
        help="Optional entity/group column for --modality timeseries.",
    )
    parser.add_argument("--patch-size", default=None, type=int, help="Square patch size in pixels.")
    parser.add_argument(
        "--stride",
        default=None,
        type=int,
        help="Patch stride in pixels. Defaults to patch size.",
    )
    parser.add_argument(
        "--max-candidates",
        default=None,
        type=int,
        help="Maximum candidate anomalies to report.",
    )
    parser.add_argument(
        "--config",
        default=None,
        type=Path,
        help="ADE configuration path. Defaults to configs/default.yaml.",
    )
    parser.add_argument(
        "--list-runs",
        action="store_true",
        help="List previous ADE runs from data/reports/runs/index.json.",
    )
    parser.add_argument(
        "--validate-report",
        type=Path,
        help="Validate an ADE JSON report and exit.",
    )
    parser.add_argument(
        "--export-html-report",
        type=Path,
        metavar="REPORT_JSON",
        help="Export a local HTML review report from an ADE JSON report and exit.",
    )
    parser.add_argument(
        "--export-local-dashboard",
        action="store_true",
        help="Export a local static dashboard from existing ADE artifacts and exit.",
    )
    parser.add_argument(
        "--validate-temporal-manifest",
        type=Path,
        help="Strictly validate an explicit temporal observation manifest and exit.",
    )
    parser.add_argument(
        "--temporal-manifest",
        type=Path,
        help="Run opt-in temporal visual change analysis from this manifest.",
    )
    parser.add_argument(
        "--temporal-output",
        type=Path,
        help="Temporal Markdown report output, or HTML output for temporal export.",
    )
    parser.add_argument(
        "--temporal-strategy",
        choices=["adjacent_difference", "baseline_difference"],
        default="adjacent_difference",
        help="Explicit temporal comparison strategy.",
    )
    parser.add_argument(
        "--temporal-patch-size",
        type=int,
        default=None,
        help="Optional patch size for real local temporal patch evidence.",
    )
    parser.add_argument("--temporal-top-k", type=int, default=10)
    parser.add_argument("--temporal-patch-top-k", type=int, default=5)
    parser.add_argument(
        "--temporal-artifact-root",
        type=Path,
        default=None,
        help="Optional root for immutable temporal result artifacts.",
    )
    parser.add_argument(
        "--validate-temporal-artifact",
        type=Path,
        help="Validate an immutable temporal change artifact and exit.",
    )
    parser.add_argument(
        "--validate-temporal-report",
        type=Path,
        help="Validate a temporal JSON report and exit.",
    )
    parser.add_argument(
        "--export-temporal-html-report",
        type=Path,
        metavar="REPORT_JSON",
        help="Export a validated temporal JSON report to HTML and exit.",
    )
    parser.add_argument(
        "--add-feedback",
        type=Path,
        metavar="REPORT_JSON",
        help="Record local human-review feedback for an ADE JSON report and exit.",
    )
    parser.add_argument(
        "--target-type",
        choices=sorted(ALLOWED_TARGET_TYPES),
        help="Feedback target type.",
    )
    parser.add_argument("--target-id", help="Feedback target identifier from the report.")
    parser.add_argument(
        "--label",
        choices=sorted(ALLOWED_FEEDBACK_LABELS),
        help="Human-review feedback label.",
    )
    parser.add_argument("--notes", default="", help="Optional human-review notes.")
    parser.add_argument(
        "--reviewer",
        default="local",
        help="Reviewer identifier for local feedback.",
    )
    parser.add_argument(
        "--list-feedback",
        action="store_true",
        help="List local review feedback summary.",
    )
    parser.add_argument(
        "--summarize-feedback-memory",
        action="store_true",
        help="Summarize local review-memory signals from human-review feedback.",
    )
    parser.add_argument("--run-id", help="Optional run ID filter for feedback listing.")
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit run history output to the most recent N runs.",
    )
    parser.add_argument(
        "--dashboard-output",
        type=Path,
        default=DEFAULT_DASHBOARD_DIR,
        help="Output directory for `ade dashboard` static HTML files.",
    )
    return parser


def run_temporal_pipeline(
    manifest_path: Path,
    output_path: Path,
    *,
    strategy: TemporalChangeStrategy = "adjacent_difference",
    patch_size: int | None = None,
    top_k: int = 10,
    patch_top_k: int = 5,
    artifact_root: Path | None = None,
    cancellation_token: CancellationToken | None = None,
) -> tuple[Path, Path, Path]:
    """Run the explicit manifest-driven temporal workflow and publish reports."""

    sequence = load_temporal_manifest(manifest_path, strict=True)
    if cancellation_token is not None:
        cancellation_token.checkpoint()
    result = analyze_temporal_change(
        sequence,
        manifest_path=manifest_path,
        strategy=strategy,
        patch_size=patch_size,
        top_k=top_k,
        patch_top_k=patch_top_k,
        cancellation_token=cancellation_token,
    )
    if cancellation_token is not None:
        cancellation_token.checkpoint()
        cancellation_token.begin_finalization()
    root = artifact_root or output_path.parent / f"{output_path.stem}_artifacts"
    artifact_path = publish_temporal_change_artifact(result, root)
    artifact = validate_temporal_change_artifact(artifact_path)
    fingerprint = artifact_path.name
    if (
        artifact.get("provenance", {}).get("manifest_fingerprint")
        != result.provenance.manifest_fingerprint
    ):
        raise ValueError(
            "Published temporal artifact provenance does not match the analysis result"
        )
    markdown_path, json_path = write_temporal_report(
        result, output_path, artifact_path, fingerprint
    )
    errors = validate_temporal_report_file(json_path)
    if errors:
        raise ValueError("Generated temporal report failed validation: " + "; ".join(errors))
    return markdown_path, json_path, artifact_path


def run_pipeline(
    input_dir: Path,
    output_path: Path,
    patch_size: int | None = None,
    stride: int | None = None,
    max_candidates: int | None = None,
    config_path: Path | None = None,
    modality: str | None = None,
    timestamp_column: str | None = None,
    entity_column: str | None = None,
    cancellation_token: CancellationToken | None = None,
) -> Path:
    """Run an ADE discovery pipeline and write a Markdown report."""

    if modality == "timeseries":
        return run_timeseries_pipeline(
            input_path=input_dir,
            output_path=output_path,
            max_candidates=max_candidates,
            config_path=config_path,
            timestamp_column=timestamp_column,
            entity_column=entity_column,
        )

    if input_dir.suffix.lower() == ".csv" or modality == "tabular":
        return run_tabular_pipeline(
            input_path=input_dir,
            output_path=output_path,
            max_candidates=max_candidates,
            config_path=config_path,
        )

    _validate_analysis_inputs(
        input_dir=input_dir,
        patch_size=patch_size,
        stride=stride,
        max_candidates=max_candidates,
        config_path=config_path,
    )
    config = load_config(config_path)
    preprocessing = config["preprocessing"]
    discovery = config["discovery"]
    reporting = config["reporting"]
    project = config["project"]
    validation = config["validation"]
    memory_config = config["memory"]
    review_memory_config = config.get("review_memory", {})
    scoring_config = discovery["memory_aware_scoring"]
    review_memory_summary = None
    if isinstance(review_memory_config, dict) and bool(review_memory_config.get("enabled", True)):
        feedback_records = FeedbackStore(_review_memory_store_path(config)).read_all()
        review_memory_summary = build_review_memory_summary(
            feedback_records,
            positive_labels=_review_memory_labels(
                review_memory_config,
                "positive_labels",
                ["interesting", "important"],
            ),
            negative_labels=_review_memory_labels(
                review_memory_config,
                "negative_labels",
                ["false_positive", "not_useful"],
            ),
            neutral_labels=_review_memory_labels(
                review_memory_config,
                "neutral_labels",
                ["known_pattern", "duplicate", "needs_more_data"],
            ),
        )

    patch_sizes, patch_strides = _resolve_patch_scales(
        preprocessing=preprocessing,
        patch_size=patch_size,
        stride=stride,
    )
    effective_patch_size = patch_sizes[0]
    effective_stride = patch_strides[0]
    effective_max_candidates = (
        max_candidates
        if max_candidates is not None
        else int(discovery.get("top_k") or discovery["max_candidate_anomalies"])
    )
    supported_extensions = [
        str(extension) for extension in validation["supported_image_extensions"]
    ]
    if cancellation_token is not None:
        cancellation_token.checkpoint()
    dataset_profile = profile_image_folder(
        input_path=input_dir,
        config=config,
        supported_image_extensions=supported_extensions,
        patch_size=effective_patch_size,
        patch_stride=effective_stride,
        patch_sizes=patch_sizes,
        patch_strides=patch_strides,
    )
    _raise_for_invalid_profile(dataset_profile)
    if cancellation_token is not None:
        cancellation_token.checkpoint()

    image_records = ImageAdapter(
        input_dir,
        supported_image_extensions=supported_extensions,
    ).load()
    if not image_records:
        raise ValueError(
            f"No supported image files found in input directory: {input_dir}. "
            "Run `python scripts/create_demo_data.py` or provide a folder of PNG, JPEG, "
            "TIFF, BMP, or WebP images."
        )
    extractor = PatchExtractor(
        patch_size=effective_patch_size,
        stride=effective_stride,
        patch_sizes=patch_sizes,
        patch_strides=patch_strides,
    )
    patches = []
    for record in image_records:
        if cancellation_token is not None:
            cancellation_token.checkpoint()
        patches.extend(extractor.extract_from_path(record.path))

    if cancellation_token is not None:
        cancellation_token.checkpoint()
    embeddings = EmbeddingEngine().embed_patches(patches)
    if cancellation_token is not None:
        cancellation_token.checkpoint()
    memory = (
        _build_vector_memory(
            embeddings=embeddings,
            candidates=[],
            metric=str(memory_config["metric"]),
        )
        if bool(memory_config["enabled"])
        else None
    )
    novelty_scorer = NoveltyScorer(
        strategy=(
            str(discovery["novelty_strategy"])
            if bool(scoring_config["enabled"])
            else "global_distance"
        ),
        neighbor_top_k=int(scoring_config["neighbor_top_k"]),
        exclude_same_source=bool(scoring_config["exclude_same_source"]),
        weight_global_distance=float(scoring_config["weight_global_distance"]),
        weight_neighbor_distance=float(scoring_config["weight_neighbor_distance"]),
    )
    scored_candidates = novelty_scorer.score(embeddings, memory=memory)
    if cancellation_token is not None:
        cancellation_token.checkpoint()
    candidates = AnomalySelector(
        enabled=bool(discovery.get("diversity", {}).get("enabled", False)),
        min_spatial_distance=float(discovery.get("diversity", {}).get("min_spatial_distance", 32)),
        max_per_image=int(discovery.get("diversity", {}).get("max_per_image", 3)),
        prefer_multiple_scales=bool(
            discovery.get("diversity", {}).get("prefer_multiple_scales", True)
        ),
    ).select(
        candidates=scored_candidates,
        max_candidates=effective_max_candidates,
    )
    if cancellation_token is not None:
        cancellation_token.checkpoint()
    if memory is not None:
        memory = _build_vector_memory(
            embeddings=embeddings,
            candidates=candidates,
            metric=str(memory_config["metric"]),
        )
    concepts = ConceptClusterer(
        distance_threshold=float(discovery["cluster_distance_threshold"]),
        max_concepts=int(discovery["max_concepts"]),
        min_supporting_examples=int(
            discovery.get("concepts", {}).get("min_supporting_examples", 2)
        ),
        max_supporting_examples=int(
            discovery.get("concepts", {}).get("max_supporting_examples", 5)
        ),
    ).cluster(candidates)
    if cancellation_token is not None:
        cancellation_token.checkpoint()
    evidence_items = EvidenceCollector(
        max_supporting_examples=int(
            discovery.get("concepts", {}).get("max_supporting_examples", 5)
        ),
        memory=memory,
        top_k_neighbors=int(memory_config["top_k_neighbors"]),
        include_neighbors=bool(memory_config["include_neighbors_in_report"]),
    ).collect(concepts)
    if cancellation_token is not None:
        cancellation_token.checkpoint()
    confidences = ConfidenceScorer().score(evidence_items)
    hypotheses = HypothesisGenerator().generate(evidence_items)
    if cancellation_token is not None:
        cancellation_token.checkpoint()

    summary = DatasetSummary(
        input_dir=input_dir,
        image_count=len(image_records),
        patch_count=len(patches),
    )
    if cancellation_token is not None:
        cancellation_token.begin_finalization()
    return ReportGenerator(
        project_name=str(project["name"]),
        pipeline_version=str(project["pipeline_version"]),
        report_version=str(reporting["report_version"]),
        human_review_required=bool(reporting["human_review_required"]),
        save_patch_previews=bool(reporting["save_patch_previews"]),
        assets_dir_name=str(reporting["assets_dir_name"]),
        runs_dir_name=str(reporting["runs_dir_name"]),
    ).write(
        output_path=output_path,
        dataset_summary=summary,
        candidates=candidates,
        evidence_items=evidence_items,
        confidences=confidences,
        hypotheses=hypotheses,
        dataset_profile=dataset_profile,
        memory_metadata={
            "enabled": bool(memory_config["enabled"]),
            "metric": str(memory_config["metric"]),
            "items_indexed": len(memory) if memory is not None else 0,
        },
        analysis_metadata={
            "total_patches": len(patches),
            "patch_scales_used": _patch_scales_used(patches),
            "anomaly_selection_strategy": (
                "diversity-aware"
                if bool(discovery.get("diversity", {}).get("enabled", False))
                else "top-novelty"
            ),
            **novelty_scorer.last_metadata.to_dict(),
        },
        review_memory_summary=review_memory_summary,
    )


def run_timeseries_pipeline(
    input_path: Path,
    output_path: Path,
    max_candidates: int | None = None,
    config_path: Path | None = None,
    timestamp_column: str | None = None,
    entity_column: str | None = None,
) -> Path:
    """Run the lightweight ADE time-series CSV pipeline and write a report."""

    if config_path is not None and not config_path.exists():
        raise FileNotFoundError(f"Config file does not exist: {config_path}")
    if config_path is not None and not config_path.is_file():
        raise ValueError(f"Config path is not a file: {config_path}")
    if max_candidates is not None and max_candidates <= 0:
        raise ValueError("--max-candidates must be greater than zero.")

    config = load_config(config_path)
    discovery = config["discovery"]
    reporting = config["reporting"]
    project = config["project"]
    timeseries_config = config.get("timeseries", {})
    missing_tokens = {
        str(token)
        for token in timeseries_config.get(
            "missing_value_tokens",
            ["", "na", "n/a", "nan", "null", "none"],
        )
    }
    effective_timestamp_column = timestamp_column or timeseries_config.get("timestamp_column")
    effective_entity_column = entity_column or timeseries_config.get("entity_column")
    effective_max_candidates = (
        max_candidates
        if max_candidates is not None
        else int(discovery.get("top_k") or discovery["max_candidate_anomalies"])
    )
    window_size = int(timeseries_config.get("window_size", 3))
    adapter = TimeSeriesAdapter(
        input_path=input_path,
        timestamp_column=(str(effective_timestamp_column) if effective_timestamp_column else None),
        entity_column=str(effective_entity_column) if effective_entity_column else None,
        missing_value_tokens=missing_tokens,
    )
    profile = adapter.profile()
    if not profile.is_valid:
        raise ValueError(
            f"CSV input is not valid for time-series discovery: {input_path}. "
            f"Warnings: {'; '.join(profile.warnings)}"
        )
    records = adapter.load()
    embeddings = TimeSeriesFeatureEngine(
        window_size=window_size,
        missing_value_tokens=missing_tokens,
    ).embed(records=records, profile=profile)
    findings = TimeSeriesNoveltyScorer().score(
        embeddings,
        max_candidates=effective_max_candidates,
    )
    concepts = TimeSeriesConceptGrouper(max_concepts=int(discovery["max_concepts"])).group(findings)
    feature_vector_length = int(embeddings[0].vector.size) if embeddings else 0
    return TimeSeriesReportGenerator(
        project_name=str(project["name"]),
        pipeline_version=str(project["pipeline_version"]),
        report_version=str(reporting["report_version"]),
        human_review_required=bool(reporting["human_review_required"]),
        runs_dir_name=str(reporting["runs_dir_name"]),
    ).write(
        output_path=output_path,
        profile=profile,
        findings=findings,
        concepts=concepts,
        backend_metadata={
            "embedding_backend": TimeSeriesFeatureEngine.name,
            "scoring_backend": TimeSeriesNoveltyScorer.name,
            "clustering_backend": TimeSeriesConceptGrouper.name,
            "top_k": effective_max_candidates,
            "feature_vector_count": len(embeddings),
            "feature_vector_length": feature_vector_length,
            "window_size": window_size,
        },
    )


def run_tabular_pipeline(
    input_path: Path,
    output_path: Path,
    max_candidates: int | None = None,
    config_path: Path | None = None,
) -> Path:
    """Run the lightweight ADE CSV pipeline and write a Markdown report."""

    if config_path is not None and not config_path.exists():
        raise FileNotFoundError(f"Config file does not exist: {config_path}")
    if config_path is not None and not config_path.is_file():
        raise ValueError(f"Config path is not a file: {config_path}")
    if max_candidates is not None and max_candidates <= 0:
        raise ValueError("--max-candidates must be greater than zero.")

    config = load_config(config_path)
    discovery = config["discovery"]
    reporting = config["reporting"]
    project = config["project"]
    tabular_config = config.get("tabular", {})
    missing_tokens = {
        str(token)
        for token in tabular_config.get(
            "missing_value_tokens",
            ["", "na", "n/a", "nan", "null", "none"],
        )
    }
    effective_max_candidates = (
        max_candidates
        if max_candidates is not None
        else int(discovery.get("top_k") or discovery["max_candidate_anomalies"])
    )
    adapter = TabularAdapter(
        input_path=input_path,
        missing_value_tokens=missing_tokens,
        max_categorical_cardinality=int(tabular_config.get("max_categorical_cardinality", 50)),
    )
    profile = adapter.profile()
    if not profile.is_valid:
        raise ValueError(
            f"CSV input is not valid for tabular discovery: {input_path}. "
            f"Warnings: {'; '.join(profile.warnings)}"
        )
    records = adapter.load()
    embeddings = TabularFeatureEngine(missing_value_tokens=missing_tokens).embed(
        records=records,
        profile=profile,
    )
    findings = TabularNoveltyScorer().score(
        embeddings,
        max_candidates=effective_max_candidates,
    )
    concepts = TabularConceptGrouper(max_concepts=int(discovery["max_concepts"])).group(findings)
    feature_vector_length = int(embeddings[0].vector.size) if embeddings else 0
    return TabularReportGenerator(
        project_name=str(project["name"]),
        pipeline_version=str(project["pipeline_version"]),
        report_version=str(reporting["report_version"]),
        human_review_required=bool(reporting["human_review_required"]),
        runs_dir_name=str(reporting["runs_dir_name"]),
    ).write(
        output_path=output_path,
        profile=profile,
        findings=findings,
        concepts=concepts,
        backend_metadata={
            "embedding_backend": TabularFeatureEngine.name,
            "scoring_backend": TabularNoveltyScorer.name,
            "clustering_backend": TabularConceptGrouper.name,
            "top_k": effective_max_candidates,
            "feature_vector_count": len(embeddings),
            "feature_vector_length": feature_vector_length,
        },
    )


def _resolve_patch_scales(
    preprocessing: dict,
    patch_size: int | None,
    stride: int | None,
) -> tuple[list[int], list[int]]:
    """Resolve patch scale settings from CLI overrides and config."""

    if patch_size is not None or stride is not None:
        size = patch_size if patch_size is not None else int(preprocessing["patch_size"])
        return [int(size)], [int(stride if stride is not None else size)]

    raw_sizes = preprocessing.get("patch_sizes")
    raw_strides = preprocessing.get("patch_strides")
    if raw_sizes is None:
        raw_sizes = [int(preprocessing["patch_size"])]
    if raw_strides is None:
        raw_strides = [int(preprocessing.get("patch_stride", raw_sizes[0]))]

    patch_sizes = [int(value) for value in raw_sizes]
    patch_strides = [int(value) for value in raw_strides]
    if len(patch_sizes) != len(patch_strides):
        raise ValueError("preprocessing.patch_sizes and patch_strides must match")
    if not patch_sizes:
        raise ValueError("preprocessing.patch_sizes must contain at least one size")
    if any(value <= 0 for value in patch_sizes):
        raise ValueError("preprocessing.patch_sizes must contain positive values")
    if any(value <= 0 for value in patch_strides):
        raise ValueError("preprocessing.patch_strides must contain positive values")
    return patch_sizes, patch_strides


def _patch_scales_used(patches: list) -> list[str]:
    """Return stable patch scale labels used in this run."""

    scales = {str(patch.scale_label or f"s{patch.patch_size}") for patch in patches}
    return sorted(scales)


def _build_vector_memory(
    embeddings: list[PatchEmbedding],
    candidates: list[CandidateAnomaly],
    metric: str,
) -> VectorMemory:
    """Build a local vector memory from patch embeddings."""

    memory = VectorMemory(metric=metric)
    anomaly_by_patch_id = {
        candidate.embedding.patch.patch_id: candidate
        for candidate in candidates
        if candidate.embedding.patch.patch_id
    }
    for embedding in embeddings:
        patch = embedding.patch
        if not patch.patch_id:
            continue
        candidate = anomaly_by_patch_id.get(patch.patch_id)
        memory.add(
            item_id=patch.patch_id,
            vector=embedding.vector,
            metadata={
                "patch_id": patch.patch_id,
                "image_id": patch.image_id,
                "source_path": patch.source_path,
                "x": patch.x,
                "y": patch.y,
                "width": patch.width,
                "height": patch.height,
                "patch_size": patch.patch_size,
                "patch_stride": patch.patch_stride,
                "scale_id": patch.scale_id,
                "scale_label": patch.scale_label,
                "is_candidate_anomaly": candidate is not None,
                "anomaly_id": candidate.anomaly_id if candidate is not None else None,
                "novelty_score": (candidate.novelty_score if candidate is not None else None),
            },
        )
    return memory


def _raise_for_invalid_profile(dataset_profile: DatasetProfile) -> None:
    """Raise a clear error when a profiled input cannot be analyzed."""

    if dataset_profile.is_valid:
        return

    if not dataset_profile.input_path.exists():
        raise FileNotFoundError(f"Input path does not exist: {dataset_profile.input_path}")
    if not dataset_profile.input_path.is_dir():
        raise NotADirectoryError(
            "Input path must be an image folder for the current implementation: "
            f"{dataset_profile.input_path}"
        )
    if dataset_profile.supported_image_files == 0:
        raise ValueError(f"No supported image files were found in: {dataset_profile.input_path}")
    if dataset_profile.valid_images == 0 and dataset_profile.unreadable_files:
        raise ValueError(
            "Found unreadable image files and no valid images. See dataset profile warnings."
        )
    raise ValueError(
        f"Input dataset is not valid for analysis: {dataset_profile.input_path}. "
        f"Warnings: {'; '.join(dataset_profile.warnings)}"
    )


def _validate_analysis_inputs(
    input_dir: Path,
    patch_size: int | None,
    stride: int | None,
    max_candidates: int | None,
    config_path: Path | None,
) -> None:
    """Validate CLI analysis inputs before running the pipeline."""

    if not input_dir.exists():
        raise FileNotFoundError(f"Input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {input_dir}")
    if config_path is not None and not config_path.exists():
        raise FileNotFoundError(f"Config file does not exist: {config_path}")
    if config_path is not None and not config_path.is_file():
        raise ValueError(f"Config path is not a file: {config_path}")
    if patch_size is not None and patch_size <= 0:
        raise ValueError("--patch-size must be greater than zero.")
    if stride is not None and stride <= 0:
        raise ValueError("--stride must be greater than zero.")
    if max_candidates is not None and max_candidates <= 0:
        raise ValueError("--max-candidates must be greater than zero.")


def format_run_history(
    index_path: Path = DEFAULT_RUN_INDEX_PATH,
    limit: int | None = None,
) -> str:
    """Return a terminal-friendly ADE run history summary."""

    run_index = load_run_index(index_path)
    if run_index is None:
        return "No ADE run history found yet. Run an analysis first."

    run_values = run_index.get("runs")
    runs = (
        [run for run in run_values if isinstance(run, dict)] if isinstance(run_values, list) else []
    )
    if limit is not None:
        if limit < 1:
            raise ValueError("--limit must be greater than or equal to 1.")
        runs = runs[-limit:]

    lines = [
        "## ADE Run History",
        "",
        f"Total runs: {len(runs)}",
        "",
    ]
    for index, run in enumerate(runs, start=1):
        lines.extend(
            [
                f"{index}. {run.get('run_id')}",
                f"   Generated at: {run.get('generated_at')}",
                f"   Input: {run.get('input_path')}",
                f"   Markdown report: {run.get('markdown_report_path')}",
                f"   JSON report: {run.get('json_report_path')}",
                f"   Candidate anomalies: {run.get('number_of_candidate_anomalies')}",
                f"   Candidate unknown concepts: {run.get('number_of_candidate_unknown_concepts')}",
                f"   Human review required: {run.get('human_review_required')}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def add_feedback_from_report(
    report_path: Path,
    target_type: str | None,
    target_id: str | None,
    label: str | None,
    notes: str,
    reviewer: str,
    store_path: Path = Path("data/feedback/feedback.jsonl"),
) -> ReviewFeedback:
    """Validate a report target and append one feedback record."""

    if target_type is None:
        raise ValueError("--target-type is required with --add-feedback.")
    if target_id is None:
        raise ValueError("--target-id is required with --add-feedback.")
    if label is None:
        raise ValueError("--label is required with --add-feedback.")
    if not report_path.exists():
        raise FileNotFoundError(f"Report JSON does not exist: {report_path}")

    validation = validate_report_file(report_path)
    if not validation.is_valid:
        errors = "; ".join(validation.errors) or "report validation failed"
        raise ValueError(f"Cannot record feedback for invalid ADE report: {errors}")

    report_data = _read_json_object(report_path)
    run_id = str(report_data.get("run_id") or "")
    if not run_id:
        raise ValueError("Report JSON does not contain a run_id.")
    if not _target_exists(report_data, target_type=target_type, target_id=target_id):
        raise ValueError(
            f"Target ID was not found in report for target_type={target_type}: {target_id}"
        )

    feedback = ReviewFeedback.create(
        run_id=run_id,
        report_path=report_path,
        target_type=target_type,
        target_id=target_id,
        label=label,
        notes=notes,
        reviewer=reviewer,
        metadata={"report_version": report_data.get("report_version")},
    )
    FeedbackStore(store_path).append(feedback)
    return feedback


def format_feedback_summary(
    store_path: Path = Path("data/feedback/feedback.jsonl"),
    run_id: str | None = None,
) -> str:
    """Return a concise Markdown-style local feedback summary."""

    summary = FeedbackStore(store_path).summarize_labels_by_run_id(run_id=run_id)
    lines = ["## ADE Feedback Summary", ""]
    lines.append(f"Run ID: {run_id}" if run_id else "Run ID: all")
    lines.append(f"Total feedback: {summary.total_feedback}")
    if summary.label_counts:
        lines.extend(["", "Labels:"])
        for label, count in sorted(summary.label_counts.items()):
            lines.append(f"- {label}: {count}")
    return "\n".join(lines)


def format_review_memory_summary(
    store_path: Path = Path("data/feedback/feedback.jsonl"),
    run_id: str | None = None,
    *,
    positive_labels: list[str] | None = None,
    negative_labels: list[str] | None = None,
    neutral_labels: list[str] | None = None,
) -> str:
    """Return a concise Markdown-style review-memory summary."""

    store = FeedbackStore(store_path)
    records = store.filter_by_run_id(run_id) if run_id else store.read_all()
    summary = build_review_memory_summary(
        records,
        positive_labels=positive_labels or ["interesting", "important"],
        negative_labels=negative_labels or ["false_positive", "not_useful"],
        neutral_labels=neutral_labels or ["known_pattern", "duplicate", "needs_more_data"],
    )
    lines = [
        "## ADE Review Memory Summary",
        "",
        f"Run ID: {run_id}" if run_id else "Run ID: all",
        f"Feedback records: {summary.total_feedback_count}",
        "",
        "Review-memory signals are feedback-informed ranking support. "
        "They do not replace human review.",
    ]
    if summary.label_counts:
        lines.extend(["", "Labels:"])
        for label, count in sorted(summary.label_counts.items()):
            lines.append(f"- {label}: {count}")
    if summary.label_counts_by_target_type:
        lines.extend(["", "Target types:"])
        for target_type, counts in sorted(summary.label_counts_by_target_type.items()):
            count_text = ", ".join(f"{label}: {count}" for label, count in sorted(counts.items()))
            lines.append(f"- {target_type}: {count_text}")
    return "\n".join(lines)


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise ValueError(f"Report JSON is not valid JSON: {path}") from error
    if not isinstance(loaded, dict):
        raise ValueError(f"Report JSON root must be an object: {path}")
    return loaded


def _target_exists(report_data: dict[str, Any], target_type: str, target_id: str) -> bool:
    if target_type == "anomaly":
        return target_id in _ids_from_items(
            report_data.get("candidate_anomalies"),
            ["anomaly_id", "id"],
        )
    if target_type == "concept":
        concept_items = report_data.get("candidate_concepts")
        if not concept_items:
            concept_items = report_data.get("candidate_unknown_concepts")
        return target_id in _ids_from_items(concept_items, ["concept_id", "id"])
    return False


def _ids_from_items(value: object, field_names: list[str]) -> set[str]:
    if not isinstance(value, list):
        return set()
    ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        for field_name in field_names:
            item_id = item.get(field_name)
            if item_id:
                ids.add(str(item_id))
    return ids


def _feedback_store_path(config: dict[str, Any]) -> Path:
    feedback_config = config.get("feedback", {})
    if not isinstance(feedback_config, dict):
        feedback_config = {}
    return Path(str(feedback_config.get("store_path", "data/feedback/feedback.jsonl")))


def _review_memory_store_path(config: dict[str, Any]) -> Path:
    review_memory_config = config.get("review_memory", {})
    if isinstance(review_memory_config, dict) and review_memory_config.get("feedback_store_path"):
        return Path(str(review_memory_config["feedback_store_path"]))
    return _feedback_store_path(config)


def _review_memory_labels(
    review_memory_config: dict[str, Any],
    key: str,
    default: list[str],
) -> list[str]:
    labels = review_memory_config.get(key, default)
    if not isinstance(labels, list):
        return list(default)
    return [str(label) for label in labels]


def main() -> None:
    """Run ADE from command-line arguments."""

    parser = build_parser()
    args = parser.parse_args()
    if args.validate_temporal_manifest is not None:
        try:
            sequence = load_temporal_manifest(args.validate_temporal_manifest, strict=True)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(
            "ADE temporal manifest validation passed: "
            f"{args.validate_temporal_manifest} ({len(sequence.observations)} observations)"
        )
        return

    if args.validate_temporal_artifact is not None:
        try:
            artifact = validate_temporal_change_artifact(args.validate_temporal_artifact)
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(
            "ADE temporal artifact validation passed: "
            f"{args.validate_temporal_artifact} "
            f"({artifact['summary']['observation_count']} observations)"
        )
        return

    if args.validate_temporal_report is not None:
        errors = validate_temporal_report_file(args.validate_temporal_report)
        if errors:
            for validation_error in errors:
                print(f"ERROR: {validation_error}")
            raise SystemExit(1)
        print(f"ADE temporal report validation passed: {args.validate_temporal_report}")
        return

    if args.export_temporal_html_report is not None:
        if args.temporal_output is None:
            parser.error("--temporal-output is required with --export-temporal-html-report.")
        try:
            html_path = write_temporal_html_report(
                args.export_temporal_html_report, args.temporal_output
            )
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print(f"ADE temporal HTML report written to {html_path}")
        return

    if args.temporal_manifest is not None:
        if args.temporal_output is None:
            parser.error("--temporal-output is required with --temporal-manifest.")
        try:
            markdown_path, json_path, artifact_path = run_temporal_pipeline(
                args.temporal_manifest,
                args.temporal_output,
                strategy=args.temporal_strategy,
                patch_size=args.temporal_patch_size,
                top_k=args.temporal_top_k,
                patch_top_k=args.temporal_patch_top_k,
                artifact_root=args.temporal_artifact_root,
            )
        except (OSError, ValueError) as error:
            parser.error(str(error))
        print("ADE temporal analysis complete. Candidate temporal changes require human review.")
        print(f"Markdown report: {markdown_path}")
        print(f"JSON report: {json_path}")
        print(f"Temporal artifact: {artifact_path}")
        return

    if args.validate_report is not None:
        result = validate_report_file(args.validate_report)
        if not result.is_valid:
            for validation_error in result.errors:
                print(f"ERROR: {validation_error}")
            raise SystemExit(1)
        print(f"ADE report validation passed: {args.validate_report}")
        if result.warnings:
            print("Warnings:")
            for warning in result.warnings:
                print(f"* {warning}")
        return

    if args.export_html_report is not None:
        if args.output is None:
            parser.error("--output is required with --export-html-report.")
        try:
            output_path = write_html_report(args.export_html_report, args.output)
        except (FileNotFoundError, ValueError) as error:
            parser.error(str(error))
        print(f"ADE HTML report written to {output_path}")
        return

    if args.export_local_dashboard:
        if args.output is None:
            parser.error("--output is required with --export-local-dashboard.")
        try:
            dashboard_export = export_local_dashboard(output_dir=args.output)
        except OSError as error:
            parser.error(str(error))
        print(f"ADE local dashboard written to {dashboard_export.index_path}")
        print(f"Dashboard data written to {dashboard_export.data_path}")
        print(
            "Artifacts included: "
            f"{dashboard_export.run_count} runs, "
            f"{dashboard_export.report_count} reports, "
            f"{dashboard_export.benchmark_count} benchmarks, "
            f"{dashboard_export.feedback_count} feedback records"
        )
        return

    if args.add_feedback is not None:
        try:
            config = load_config(args.config)
            feedback = add_feedback_from_report(
                report_path=args.add_feedback,
                target_type=args.target_type,
                target_id=args.target_id,
                label=args.label,
                notes=args.notes,
                reviewer=args.reviewer,
                store_path=_feedback_store_path(config),
            )
        except (FileNotFoundError, ValueError) as error:
            parser.error(str(error))
        print(
            "ADE feedback recorded: "
            f"{feedback.feedback_id} "
            f"({feedback.target_type} {feedback.target_id}, {feedback.label})"
        )
        return

    if args.list_feedback:
        try:
            config = load_config(args.config)
            print(format_feedback_summary(_feedback_store_path(config), run_id=args.run_id))
        except (FileNotFoundError, ValueError) as error:
            parser.error(str(error))
        return

    if args.summarize_feedback_memory:
        try:
            config = load_config(args.config)
            review_memory_config = config.get("review_memory", {})
            if not isinstance(review_memory_config, dict):
                review_memory_config = {}
            print(
                format_review_memory_summary(
                    _review_memory_store_path(config),
                    run_id=args.run_id,
                    positive_labels=_review_memory_labels(
                        review_memory_config,
                        "positive_labels",
                        ["interesting", "important"],
                    ),
                    negative_labels=_review_memory_labels(
                        review_memory_config,
                        "negative_labels",
                        ["false_positive", "not_useful"],
                    ),
                    neutral_labels=_review_memory_labels(
                        review_memory_config,
                        "neutral_labels",
                        ["known_pattern", "duplicate", "needs_more_data"],
                    ),
                )
            )
        except (FileNotFoundError, ValueError) as error:
            parser.error(str(error))
        return

    if args.command == "dashboard":
        dashboard_build = generate_dashboard(output_dir=args.dashboard_output)
        print(f"ADE dashboard written to {dashboard_build.index_path}")
        print(f"Runs included: {dashboard_build.run_count}")
        print(f"Open locally: {dashboard_build.index_path.resolve().as_uri()}")
        return

    if args.list_runs:
        try:
            print(format_run_history(limit=args.limit))
        except ValueError as error:
            parser.error(str(error))
        return

    if args.input is None or args.output is None:
        parser.error(
            "--input and --output are required unless --list-runs, "
            "--validate-report, --export-html-report, --export-local-dashboard, "
            "--validate-temporal-manifest, --temporal-manifest, "
            "--validate-temporal-artifact, --validate-temporal-report, "
            "--export-temporal-html-report, "
            "--add-feedback, "
            "--list-feedback, or --summarize-feedback-memory is used."
        )

    try:
        report_path = run_pipeline(
            input_dir=args.input,
            output_path=args.output,
            patch_size=args.patch_size,
            stride=args.stride,
            max_candidates=args.max_candidates,
            config_path=args.config,
            modality=args.modality,
            timestamp_column=args.timestamp_column,
            entity_column=args.entity_column,
        )
    except ModuleNotFoundError as error:
        if error.name == "PIL":
            parser.error(
                "Pillow is required for image loading. "
                "Install dependencies with `pip install -e .[dev]`."
            )
        raise
    except (FileNotFoundError, NotADirectoryError, ValueError) as error:
        parser.error(str(error))
    print(_format_completed_run(report_path))


def _format_completed_run(report_path: Path) -> str:
    """Return concise terminal output for a completed analysis."""

    json_path = report_path.with_suffix(".json")
    if not json_path.exists():
        return f"ADE report written to {report_path}"

    import json

    report_data = json.loads(json_path.read_text(encoding="utf-8"))
    run_id = report_data.get("run_id", "unavailable")
    input_dir = report_data.get("input_summary", {}).get("input_dir", "unavailable")
    image_count = report_data.get("number_of_images", "unavailable")
    finding_count = report_data.get("number_of_candidate_anomalies", "unavailable")
    return "\n".join(
        [
            "ADE analysis complete.",
            f"Run ID: {run_id}",
            f"Dataset: {input_dir}",
            f"Images processed: {image_count}",
            f"Candidate anomalies: {finding_count}",
            f"ADE report written to {report_path}",
            f"Markdown report: {report_path}",
            f"JSON report: {json_path}",
        ]
    )


if __name__ == "__main__":
    main()

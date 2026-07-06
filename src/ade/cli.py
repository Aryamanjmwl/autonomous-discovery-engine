"""Command-line entry point for the ADE prototype pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from ade.adapters.image_adapter import ImageAdapter
from ade.config import load_config
from ade.discovery.concept_clusterer import ConceptClusterer
from ade.discovery.confidence_scorer import ConfidenceScorer
from ade.discovery.evidence_collector import EvidenceCollector
from ade.discovery.novelty_scorer import NoveltyScorer
from ade.models import DatasetProfile
from ade.preprocessing.input_validator import profile_image_folder
from ade.preprocessing.patch_extractor import PatchExtractor
from ade.reasoning.hypothesis_generator import HypothesisGenerator
from ade.reporting.report_generator import DatasetSummary, ReportGenerator
from ade.reporting.run_index import load_run_index
from ade.representation.embedding_engine import EmbeddingEngine

DEFAULT_RUN_INDEX_PATH = Path("data/reports/runs/index.json")


def build_parser() -> argparse.ArgumentParser:
    """Create the ADE command-line parser."""

    parser = argparse.ArgumentParser(description="Run the ADE prototype image pipeline.")
    parser.add_argument("--input", type=Path, help="Directory containing input images.")
    parser.add_argument("--output", type=Path, help="Markdown report output path.")
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
        "--limit",
        type=int,
        default=None,
        help="Limit run history output to the most recent N runs.",
    )
    return parser


def run_pipeline(
    input_dir: Path,
    output_path: Path,
    patch_size: int | None = None,
    stride: int | None = None,
    max_candidates: int | None = None,
    config_path: Path | None = None,
) -> Path:
    """Run the minimal ADE image pipeline and write a Markdown report."""

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

    effective_patch_size = (
        patch_size if patch_size is not None else int(preprocessing["patch_size"])
    )
    effective_stride = (
        stride if stride is not None else int(preprocessing["patch_stride"])
    )
    effective_max_candidates = (
        max_candidates
        if max_candidates is not None
        else int(discovery["max_candidate_anomalies"])
    )
    supported_extensions = [
        str(extension) for extension in validation["supported_image_extensions"]
    ]
    dataset_profile = profile_image_folder(
        input_path=input_dir,
        config=config,
        supported_image_extensions=supported_extensions,
        patch_size=effective_patch_size,
        patch_stride=effective_stride,
    )
    _raise_for_invalid_profile(dataset_profile)

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
    extractor = PatchExtractor(patch_size=effective_patch_size, stride=effective_stride)
    patches = [
        patch
        for record in image_records
        for patch in extractor.extract_from_path(record.path)
    ]

    embeddings = EmbeddingEngine().embed_patches(patches)
    candidates = NoveltyScorer().score(
        embeddings,
        max_candidates=effective_max_candidates,
    )
    concepts = ConceptClusterer(
        distance_threshold=float(discovery["cluster_distance_threshold"]),
        max_concepts=int(discovery["max_concepts"]),
    ).cluster(candidates)
    evidence_items = EvidenceCollector().collect(concepts)
    confidences = ConfidenceScorer().score(evidence_items)
    hypotheses = HypothesisGenerator().generate(evidence_items)

    summary = DatasetSummary(
        input_dir=input_dir,
        image_count=len(image_records),
        patch_count=len(patches),
    )
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
    )


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

    runs = [run for run in run_index.get("runs", []) if isinstance(run, dict)]
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
                "   Candidate unknown concepts: "
                f"{run.get('number_of_candidate_unknown_concepts')}",
                f"   Human review required: {run.get('human_review_required')}",
                "",
            ]
        )
    return "\n".join(lines).rstrip()


def main() -> None:
    """Run ADE from command-line arguments."""

    parser = build_parser()
    args = parser.parse_args()
    if args.list_runs:
        try:
            print(format_run_history(limit=args.limit))
        except ValueError as error:
            parser.error(str(error))
        return

    if args.input is None or args.output is None:
        parser.error("--input and --output are required unless --list-runs is used.")

    try:
        report_path = run_pipeline(
            input_dir=args.input,
            output_path=args.output,
            patch_size=args.patch_size,
            stride=args.stride,
            max_candidates=args.max_candidates,
            config_path=args.config,
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
    print(f"ADE report written to {report_path}")


if __name__ == "__main__":
    main()

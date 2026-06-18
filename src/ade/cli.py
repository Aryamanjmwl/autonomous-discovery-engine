"""Command-line entry point for the ADE prototype pipeline."""

from __future__ import annotations

import argparse
from pathlib import Path

from ade.adapters.image_adapter import ImageAdapter
from ade.discovery.concept_clusterer import ConceptClusterer
from ade.discovery.confidence_scorer import ConfidenceScorer
from ade.discovery.evidence_collector import EvidenceCollector
from ade.discovery.novelty_scorer import NoveltyScorer
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
    parser.add_argument("--patch-size", default=64, type=int, help="Square patch size in pixels.")
    parser.add_argument("--stride", default=None, type=int, help="Patch stride in pixels. Defaults to patch size.")
    parser.add_argument("--max-candidates", default=25, type=int, help="Maximum candidate anomalies to report.")
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
    patch_size: int = 64,
    stride: int | None = None,
    max_candidates: int = 25,
) -> Path:
    """Run the minimal ADE image pipeline and write a Markdown report."""

    image_records = ImageAdapter(input_dir).load()
    extractor = PatchExtractor(patch_size=patch_size, stride=stride)
    patches = [
        patch
        for record in image_records
        for patch in extractor.extract_from_path(record.path)
    ]

    embeddings = EmbeddingEngine().embed_patches(patches)
    candidates = NoveltyScorer().score(embeddings, max_candidates=max_candidates)
    concepts = ConceptClusterer().cluster(candidates)
    evidence_items = EvidenceCollector().collect(concepts)
    confidences = ConfidenceScorer().score(evidence_items)
    hypotheses = HypothesisGenerator().generate(evidence_items)

    summary = DatasetSummary(
        input_dir=input_dir,
        image_count=len(image_records),
        patch_count=len(patches),
    )
    return ReportGenerator().write(
        output_path=output_path,
        dataset_summary=summary,
        candidates=candidates,
        evidence_items=evidence_items,
        confidences=confidences,
        hypotheses=hypotheses,
    )


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
        print(format_run_history(limit=args.limit))
        return

    if args.input is None or args.output is None:
        parser.error("--input and --output are required unless --list-runs is used.")

    report_path = run_pipeline(
        input_dir=args.input,
        output_path=args.output,
        patch_size=args.patch_size,
        stride=args.stride,
        max_candidates=args.max_candidates,
    )
    print(f"ADE report written to {report_path}")


if __name__ == "__main__":
    main()

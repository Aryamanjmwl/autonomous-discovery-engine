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
from ade.representation.embedding_engine import EmbeddingEngine


def build_parser() -> argparse.ArgumentParser:
    """Create the ADE command-line parser."""

    parser = argparse.ArgumentParser(description="Run the ADE prototype image pipeline.")
    parser.add_argument("--input", required=True, type=Path, help="Directory containing input images.")
    parser.add_argument("--output", required=True, type=Path, help="Markdown report output path.")
    parser.add_argument("--patch-size", default=64, type=int, help="Square patch size in pixels.")
    parser.add_argument("--stride", default=None, type=int, help="Patch stride in pixels. Defaults to patch size.")
    parser.add_argument("--max-candidates", default=25, type=int, help="Maximum candidate anomalies to report.")
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


def main() -> None:
    """Run ADE from command-line arguments."""

    args = build_parser().parse_args()
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

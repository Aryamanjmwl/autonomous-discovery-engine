"""Markdown report generation for ADE discovery runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from ade.discovery.confidence_scorer import ConceptConfidence
from ade.discovery.evidence_collector import ConceptEvidence
from ade.discovery.novelty_scorer import CandidateAnomaly
from ade.reasoning.hypothesis_generator import Hypothesis


@dataclass(frozen=True)
class DatasetSummary:
    """High-level counts for an ADE run."""

    input_dir: Path
    image_count: int
    patch_count: int


class ReportGenerator:
    """Generate Markdown reports for human review."""

    def generate(
        self,
        dataset_summary: DatasetSummary,
        candidates: list[CandidateAnomaly],
        evidence_items: list[ConceptEvidence],
        confidences: list[ConceptConfidence],
        hypotheses: list[Hypothesis],
    ) -> str:
        """Return an ADE Discovery Report in Markdown format."""

        confidence_by_id = {confidence.concept_id: confidence for confidence in confidences}
        hypothesis_by_id = {hypothesis.concept_id: hypothesis for hypothesis in hypotheses}

        lines = [
            "# ADE Discovery Report",
            "",
            "## Dataset Summary",
            "",
            f"- Input directory: `{dataset_summary.input_dir}`",
            f"- Number of images: {dataset_summary.image_count}",
            f"- Number of patches: {dataset_summary.patch_count}",
            "",
            "## Candidate Anomalies",
            "",
        ]

        if candidates:
            for index, candidate in enumerate(candidates, start=1):
                patch = candidate.embedding.patch
                lines.append(
                    f"{index}. `{patch.source_path}` at {patch.coordinates} "
                    f"- novelty score: {candidate.novelty_score:.4f}"
                )
        else:
            lines.append("No candidate anomalies were identified by the placeholder scorer.")

        lines.extend(["", "## Candidate Unknown Concepts", ""])

        if evidence_items:
            for evidence in evidence_items:
                confidence = confidence_by_id.get(evidence.concept_id)
                hypothesis = hypothesis_by_id.get(evidence.concept_id)
                lines.extend(
                    [
                        f"### {evidence.concept_id}",
                        "",
                        f"- Supporting patches: {evidence.example_count}",
                        f"- Average novelty: {evidence.average_novelty:.4f}",
                        f"- Cluster consistency: {evidence.consistency:.4f}",
                        f"- Confidence score: {confidence.score:.4f}" if confidence else "- Confidence score: unavailable",
                        "",
                        "Evidence summary:",
                    ]
                )
                for item in evidence.examples:
                    lines.append(
                        f"- `{item.source_path}` at {item.coordinates}; "
                        f"novelty score {item.novelty_score:.4f}"
                    )
                lines.extend(
                    [
                        "",
                        "Cautious hypothesis:",
                        "",
                        hypothesis.text if hypothesis else "No hypothesis was generated.",
                        "",
                    ]
                )
        else:
            lines.append("No candidate unknown concepts were grouped by the placeholder clusterer.")

        lines.extend(
            [
                "",
                "## Human Expert Review Required",
                "",
                "All results are exploratory candidate findings. They require human expert review before any scientific, clinical, operational, or commercial interpretation.",
                "",
            ]
        )
        return "\n".join(lines)

    def write(
        self,
        output_path: Path | str,
        dataset_summary: DatasetSummary,
        candidates: list[CandidateAnomaly],
        evidence_items: list[ConceptEvidence],
        confidences: list[ConceptConfidence],
        hypotheses: list[Hypothesis],
    ) -> Path:
        """Write a Markdown report and return the output path."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        report = self.generate(
            dataset_summary=dataset_summary,
            candidates=candidates,
            evidence_items=evidence_items,
            confidences=confidences,
            hypotheses=hypotheses,
        )
        path.write_text(report, encoding="utf-8")
        return path

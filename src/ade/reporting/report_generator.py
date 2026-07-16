"""Markdown report generation for ADE discovery runs."""

from __future__ import annotations

import json
import re
import struct
import uuid
import zlib
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, TypedDict

from ade import __version__
from ade.discovery.confidence_scorer import ConceptConfidence
from ade.discovery.evidence_collector import ConceptEvidence
from ade.discovery.novelty_scorer import CandidateAnomaly
from ade.feedback import ALLOWED_FEEDBACK_LABELS
from ade.memory.review_memory import (
    ReviewMemorySignal,
    ReviewMemorySummary,
    score_candidate_with_review_memory,
)
from ade.models import (
    DatasetProfile,
    EvidenceSummary,
    ReportArtifact,
    RunMetadata,
    UnknownConcept,
)
from ade.reasoning.hypothesis_generator import Hypothesis
from ade.reporting.run_index import build_run_summary, update_run_index


class EvidenceSummaryJson(TypedDict):
    supporting_examples: list[Any]
    representative_examples: list[Any]
    near_matches: list[Any]
    nearest_neighbors: list[Any]
    normal_comparisons: list[Any]
    notes: list[str]
    warnings: list[str]


def _int_value(value: object, default: int = 0) -> int:
    return int(value) if isinstance(value, int | float | str) else default


def _list_value(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: object, default: list[str] | None = None) -> list[str]:
    items = _list_value(value)
    if not items and default is not None:
        return default
    return [str(item) for item in items]


@dataclass(frozen=True)
class DatasetSummary:
    """High-level counts for an ADE run."""

    input_dir: Path
    image_count: int
    patch_count: int


@dataclass(frozen=True)
class ReportAssets:
    """Relative Markdown image paths for saved report assets."""

    anomaly_previews: dict[int, str]
    concept_previews: dict[tuple[str, int], str]


class ReportGenerator:
    """Generate Markdown and JSON reports for human review."""

    name = "markdown_json_report"

    def __init__(
        self,
        project_name: str = "ADE",
        pipeline_version: str = __version__,
        report_version: str = "1.0",
        human_review_required: bool = True,
        save_patch_previews: bool = True,
        assets_dir_name: str = "assets",
        runs_dir_name: str = "runs",
    ) -> None:
        self.project_name = project_name
        self.pipeline_version = pipeline_version
        self.report_version = report_version
        self.human_review_required = human_review_required
        self.save_patch_previews = save_patch_previews
        self.assets_dir_name = assets_dir_name
        self.runs_dir_name = runs_dir_name

    def render(
        self,
        run_result: dict[str, Any],
        output_dir: Path | str,
    ) -> list[ReportArtifact]:
        """Render a structured run result into Markdown and JSON artifacts.

        ``write`` remains the main API for the current CLI. This method gives
        future orchestration code a small renderer contract without changing the
        established report format.
        """

        output_path = Path(output_dir) / str(run_result.get("filename", "ade_report.md"))
        markdown_path = self.write(
            output_path=output_path,
            dataset_summary=run_result["dataset_summary"],
            candidates=run_result.get("candidates", []),
            evidence_items=run_result.get("evidence_items", []),
            confidences=run_result.get("confidences", []),
            hypotheses=run_result.get("hypotheses", []),
            dataset_profile=run_result.get("dataset_profile"),
            analysis_metadata=run_result.get("analysis_metadata")
            or run_result.get("backend_metadata"),
        )
        return [
            ReportArtifact(artifact_type="markdown", path=markdown_path),
            ReportArtifact(artifact_type="json", path=markdown_path.with_suffix(".json")),
        ]

    def generate(
        self,
        dataset_summary: DatasetSummary,
        candidates: list[CandidateAnomaly],
        evidence_items: list[ConceptEvidence],
        confidences: list[ConceptConfidence],
        hypotheses: list[Hypothesis],
        assets: ReportAssets | None = None,
        run_id: str | None = None,
        dataset_profile: DatasetProfile | None = None,
        analysis_metadata: dict[str, object] | None = None,
        review_memory_summary: ReviewMemorySummary | None = None,
    ) -> str:
        """Return an ADE Discovery Report in Markdown format."""

        confidence_by_id = {confidence.concept_id: confidence for confidence in confidences}
        hypothesis_by_id = {hypothesis.concept_id: hypothesis for hypothesis in hypotheses}
        assets = assets or ReportAssets(anomaly_previews={}, concept_previews={})

        lines = [
            "# ADE Discovery Report",
            "",
            "ADE Discovery Report for exploratory review. Findings below are candidate "
            "patterns and require human review.",
            "",
            f"**Run ID:** `{run_id}`" if run_id else "**Run ID:** not assigned",
            "",
            "## Dataset Summary",
            "",
            f"- Input directory: `{dataset_summary.input_dir}`",
            f"- Number of input images: {dataset_summary.image_count}",
            f"- Number of extracted patches: {dataset_summary.patch_count}",
            f"- Number of candidate anomalies: {len(candidates)}",
            f"- Number of candidate unknown concepts: {len(evidence_items)}",
            "- Novelty scoring strategy: "
            f"`{self._scoring_strategy(analysis_metadata, candidates)}`",
            "",
            "## Input Dataset Profile",
            "",
            *self._dataset_profile_lines(dataset_profile),
            "",
            "## Scoring Metadata",
            "",
            *self._analysis_metadata_lines(analysis_metadata, candidates),
            "",
            "## Review Memory",
            "",
            *self._review_memory_lines(review_memory_summary),
            "",
            "## Top Candidate Anomalies",
            "",
        ]

        if candidates:
            lines.extend(
                [
                    "| Rank | Preview | Source | Coordinates | Patch scale | Novelty score | Review memory |",
                    "| --- | --- | --- | --- | --- | ---: | --- |",
                ]
            )
            for index, candidate in enumerate(candidates, start=1):
                patch = candidate.embedding.patch
                signal = (
                    score_candidate_with_review_memory(
                        candidate,
                        "anomaly",
                        review_memory_summary,
                    )
                    if review_memory_summary is not None
                    else None
                )
                preview = self._markdown_image(
                    alt_text=f"candidate anomaly {index}",
                    relative_path=assets.anomaly_previews.get(index),
                )
                lines.append(
                    f"| {index} | {preview} | `{patch.source_path}` | "
                    f"`{patch.coordinates}` | "
                    f"`{patch.scale_label or 'single-scale'}` / {patch.patch_size}px | "
                    f"{candidate.novelty_score:.4f} | "
                    f"{self._review_memory_signal_cell(signal)} |"
                )
        else:
            lines.append("No candidate anomalies were identified by the placeholder scorer.")

        lines.extend(["", "## Evidence Items", ""])
        if candidates:
            for index, candidate in enumerate(candidates, start=1):
                lines.extend(self._candidate_evidence_lines(index, candidate, assets))
        else:
            lines.append("No evidence items were available.")

        lines.extend(["", "## Candidate Unknown Concepts", ""])

        if evidence_items:
            for evidence in evidence_items:
                confidence = confidence_by_id.get(evidence.concept_id)
                hypothesis = hypothesis_by_id.get(evidence.concept_id)
                lines.extend(
                    [
                        f"### {evidence.concept_id}",
                        "",
                        "- Representative anomaly: "
                        f"{evidence.representative_anomaly_id or 'unavailable'}",
                        f"- Supporting patches: {evidence.example_count}",
                        f"- Source images represented: {evidence.source_image_count}",
                        f"- Average novelty: {evidence.average_novelty:.4f}",
                        f"- Consistency score: {evidence.consistency:.4f}",
                        f"- Diversity score: {evidence.diversity_score:.4f}",
                        (
                            f"- Confidence score: {confidence.score:.4f}"
                            if confidence
                            else "- Confidence score: unavailable"
                        ),
                        "- Review memory signal: "
                        + self._review_memory_signal_cell(
                            score_candidate_with_review_memory(
                                {"concept_id": evidence.concept_id},
                                "concept",
                                review_memory_summary,
                            )
                            if review_memory_summary is not None
                            else None
                        ),
                        "- Confidence breakdown:",
                        *self._confidence_breakdown_lines(
                            confidence.breakdown
                            if confidence and confidence.breakdown
                            else evidence.confidence_breakdown
                        ),
                        "",
                        "Evidence bundle for this candidate concept:",
                    ]
                )
                for example_index, item in enumerate(evidence.examples, start=1):
                    preview = self._markdown_image(
                        alt_text=f"{evidence.concept_id} example {example_index}",
                        relative_path=assets.concept_previews.get(
                            (evidence.concept_id, example_index)
                        ),
                    )
                    lines.append(
                        f"- {preview} `{item.source_path}` at {item.coordinates}; "
                        f"novelty score {item.novelty_score:.4f}; "
                        f"anomaly `{item.anomaly_id or 'unassigned'}`"
                    )
                near_match_lines = self._near_match_lines(evidence)
                if near_match_lines:
                    lines.extend(["", "Nearest visual matches:", *near_match_lines])
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
                "## Human Review Feedback",
                "",
                "Local reviewers can label candidate findings after inspecting the report.",
                "",
                "- Supported labels: "
                + ", ".join(f"`{label}`" for label in sorted(ALLOWED_FEEDBACK_LABELS)),
                "- Example anomaly feedback: "
                "`python -m ade.cli --add-feedback data/reports/demo_report.json "
                "--target-type anomaly --target-id <anomaly_id> --label interesting "
                '--notes "Local review note" --reviewer local`',
                "- Example concept feedback: "
                "`python -m ade.cli --add-feedback data/reports/demo_report.json "
                "--target-type concept --target-id <concept_id> --label known_pattern "
                '--notes "Known recurring pattern" --reviewer local`',
                "",
                "## Human Expert Review Required",
                "",
                "All results are exploratory candidate findings. Candidate anomalies, "
                "candidate unknown concepts, possible relationships, and hypotheses "
                "require human expert review before any scientific, clinical, "
                "operational, commercial, or financial interpretation.",
                "",
                "## Reproducibility Notes",
                "",
                "This report uses deterministic lightweight visual features and configured "
                "pipeline settings. Re-running with the same input files and configuration "
                "should produce stable rankings, apart from unique run identifiers and "
                "timestamps.",
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
        dataset_profile: DatasetProfile | None = None,
        memory_metadata: dict[str, object] | None = None,
        analysis_metadata: dict[str, object] | None = None,
        review_memory_summary: ReviewMemorySummary | None = None,
    ) -> Path:
        """Write a Markdown report and return the output path."""

        path = Path(output_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now(UTC)
        run_id = self.generate_run_id(generated_at)
        json_path = path.with_suffix(".json")
        runs_dir = path.parent / self.runs_dir_name
        run_metadata_path = runs_dir / f"{run_id}.json"
        run_index_path = runs_dir / "index.json"
        run_metadata = self.build_run_metadata(
            run_id=run_id,
            generated_at=generated_at,
            dataset_summary=dataset_summary,
            markdown_report_path=path,
            json_report_path=json_path,
            run_index_path=run_index_path,
            candidates=candidates,
            evidence_items=evidence_items,
            dataset_profile=dataset_profile,
            memory_metadata=memory_metadata,
            analysis_metadata=analysis_metadata,
        )
        assets = self.save_assets(path, candidates, evidence_items)
        report = self.generate(
            dataset_summary=dataset_summary,
            candidates=candidates,
            evidence_items=evidence_items,
            confidences=confidences,
            hypotheses=hypotheses,
            assets=assets,
            run_id=run_id,
            dataset_profile=dataset_profile,
            analysis_metadata=analysis_metadata,
            review_memory_summary=review_memory_summary,
        )
        path.write_text(report, encoding="utf-8")
        json_report = self.generate_json(
            dataset_summary=dataset_summary,
            candidates=candidates,
            evidence_items=evidence_items,
            confidences=confidences,
            hypotheses=hypotheses,
            assets=assets,
            run_id=run_id,
            run_metadata=run_metadata,
            dataset_profile=dataset_profile,
            analysis_metadata=analysis_metadata,
            review_memory_summary=review_memory_summary,
        )
        json_path.write_text(
            json.dumps(json_report, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        self.write_run_metadata(
            run_metadata_path=run_metadata_path,
            run_metadata=run_metadata,
        )
        update_run_index(
            index_path=run_index_path,
            run_summary=build_run_summary(run_metadata, run_metadata_path),
        )
        return path

    def generate_json(
        self,
        dataset_summary: DatasetSummary,
        candidates: list[CandidateAnomaly],
        evidence_items: list[ConceptEvidence],
        confidences: list[ConceptConfidence],
        hypotheses: list[Hypothesis],
        assets: ReportAssets | None = None,
        run_id: str | None = None,
        run_metadata: dict[str, object] | None = None,
        dataset_profile: DatasetProfile | None = None,
        analysis_metadata: dict[str, object] | None = None,
        review_memory_summary: ReviewMemorySummary | None = None,
    ) -> dict[str, object]:
        """Return a machine-readable ADE discovery report."""

        confidence_by_id = {confidence.concept_id: confidence for confidence in confidences}
        hypothesis_by_id = {hypothesis.concept_id: hypothesis for hypothesis in hypotheses}
        assets = assets or ReportAssets(anomaly_previews={}, concept_previews={})

        candidate_anomalies = [
            self._candidate_anomaly_json(index, candidate, assets, review_memory_summary)
            for index, candidate in enumerate(candidates, start=1)
        ]
        candidate_unknown_concepts = [
            self._concept_json(
                evidence=evidence,
                confidence=confidence_by_id.get(evidence.concept_id),
                hypothesis=hypothesis_by_id.get(evidence.concept_id),
                assets=assets,
                review_memory_summary=review_memory_summary,
            )
            for evidence in evidence_items
        ]

        return {
            "project_name": self.project_name,
            "report_version": self.report_version,
            "run_id": run_id,
            "run_metadata": run_metadata,
            "run_index_path": (
                str(run_metadata["run_index_path"])
                if run_metadata is not None
                else None
            ),
            "generated_at": (
                str(run_metadata["generated_at"])
                if run_metadata is not None
                else datetime.now(UTC).isoformat()
            ),
            "input_summary": {
                "input_dir": str(dataset_summary.input_dir),
                "image_count": int(dataset_summary.image_count),
                "patch_count": int(dataset_summary.patch_count),
            },
            "dataset_profile": (
                dataset_profile.to_dict() if dataset_profile is not None else None
            ),
            "scoring_metadata": self._scoring_metadata_json(
                analysis_metadata,
                candidates,
            ),
            "backend_metadata": self._backend_metadata_json(
                analysis_metadata,
                candidates,
            ),
            "review_memory_summary": (
                review_memory_summary.to_dict()
                if review_memory_summary is not None
                else None
            ),
            "number_of_images": int(dataset_summary.image_count),
            "number_of_patches": int(dataset_summary.patch_count),
            "number_of_candidate_anomalies": len(candidate_anomalies),
            "number_of_candidate_unknown_concepts": len(candidate_unknown_concepts),
            "top_discoveries": candidate_anomalies,
            "candidate_anomalies": candidate_anomalies,
            "candidate_unknown_concepts": candidate_unknown_concepts,
            "candidate_concepts": candidate_unknown_concepts,
            "evidence_summary": [
                {
                    "concept_id": evidence.concept_id,
                    "example_count": int(evidence.example_count),
                    "average_novelty": float(evidence.average_novelty),
                    "cluster_consistency": float(evidence.consistency),
                    "consistency_score": float(evidence.consistency),
                    "confidence_score": float(evidence.confidence_score),
                    "confidence_breakdown": self._json_confidence_breakdown(
                        evidence.confidence_breakdown
                    ),
                    "evidence_summary": self._evidence_summary_json(evidence, assets),
                }
                for evidence in evidence_items
            ],
            "confidence_scores": [
                {
                    "concept_id": confidence.concept_id,
                    "confidence_score": float(confidence.score),
                    "confidence_breakdown": self._json_confidence_breakdown(
                        confidence.breakdown
                    ),
                }
                for confidence in confidences
            ],
            "hypotheses": [
                {
                    "concept_id": hypothesis.concept_id,
                    "hypothesis": hypothesis.text,
                }
                for hypothesis in hypotheses
            ],
            "human_review_required": self.human_review_required,
            "feedback_supported": True,
            "supported_feedback_labels": sorted(ALLOWED_FEEDBACK_LABELS),
            "feedback_store_path": "data/feedback/feedback.jsonl",
            "limitations": [
                "All findings are exploratory candidate findings.",
                "Candidate anomalies and candidate unknown concepts require human review.",
                "The current MVP uses deterministic placeholder image statistics, "
                "not deep learning.",
                "Confidence scores are readiness signals, not proof of scientific "
                "or operational significance.",
            ],
        }

    def build_run_metadata(
        self,
        run_id: str,
        generated_at: datetime,
        dataset_summary: DatasetSummary,
        markdown_report_path: Path,
        json_report_path: Path,
        run_index_path: Path,
        candidates: list[CandidateAnomaly],
        evidence_items: list[ConceptEvidence],
        dataset_profile: DatasetProfile | None = None,
        memory_metadata: dict[str, object] | None = None,
        analysis_metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Build traceable metadata for one ADE analysis run."""

        return RunMetadata(
            run_id=run_id,
            generated_at=generated_at.isoformat(),
            input_path=dataset_summary.input_dir,
            markdown_report_path=markdown_report_path,
            json_report_path=json_report_path,
            run_index_path=run_index_path,
            number_of_images=dataset_summary.image_count,
            number_of_patches=dataset_summary.patch_count,
            number_of_candidate_anomalies=len(candidates),
            number_of_candidate_unknown_concepts=len(evidence_items),
            pipeline_version=self.pipeline_version,
            human_review_required=self.human_review_required,
            average_concept_confidence=self._average_concept_confidence(evidence_items),
            average_concept_consistency=self._average_concept_consistency(evidence_items),
            memory_enabled=(
                bool(memory_metadata.get("enabled"))
                if memory_metadata is not None
                else None
            ),
            memory_metric=(
                str(memory_metadata.get("metric"))
                if memory_metadata is not None
                and memory_metadata.get("metric") is not None
                else None
            ),
            memory_items_indexed=(
                _int_value(memory_metadata.get("items_indexed"))
                if memory_metadata is not None
                else None
            ),
            total_patches=(
                _int_value(analysis_metadata.get("total_patches"), dataset_summary.patch_count)
                if analysis_metadata is not None
                else None
            ),
            patch_scales_used=(
                [
                    str(item)
                    for item in _list_value(analysis_metadata.get("patch_scales_used"))
                ]
                if analysis_metadata is not None
                else []
            ),
            anomaly_selection_strategy=(
                str(analysis_metadata.get("anomaly_selection_strategy"))
                if analysis_metadata is not None
                and analysis_metadata.get("anomaly_selection_strategy") is not None
                else None
            ),
            novelty_strategy=(
                str(analysis_metadata.get("novelty_strategy"))
                if analysis_metadata is not None
                and analysis_metadata.get("novelty_strategy") is not None
                else None
            ),
            memory_aware_scoring_enabled=(
                bool(analysis_metadata.get("memory_aware_scoring_enabled"))
                if analysis_metadata is not None
                and analysis_metadata.get("memory_aware_scoring_enabled") is not None
                else None
            ),
            neighbor_top_k=(
                _int_value(analysis_metadata.get("neighbor_top_k"))
                if analysis_metadata is not None
                and analysis_metadata.get("neighbor_top_k") is not None
                else None
            ),
            scoring_fallback_used=(
                bool(analysis_metadata.get("scoring_fallback_used"))
                if analysis_metadata is not None
                and analysis_metadata.get("scoring_fallback_used") is not None
                else None
            ),
            scoring_fallback_reason=(
                str(analysis_metadata.get("scoring_fallback_reason"))
                if analysis_metadata is not None
                and analysis_metadata.get("scoring_fallback_reason") is not None
                else None
            ),
            number_of_input_files=(
                dataset_profile.total_files if dataset_profile is not None else None
            ),
            number_of_valid_images=(
                dataset_profile.valid_images if dataset_profile is not None else None
            ),
            number_of_unsupported_files=(
                len(dataset_profile.unsupported_files)
                if dataset_profile is not None
                else None
            ),
            number_of_unreadable_files=(
                len(dataset_profile.unreadable_files)
                if dataset_profile is not None
                else None
            ),
            estimated_patch_count=(
                dataset_profile.estimated_patch_count
                if dataset_profile is not None
                else None
            ),
            input_warnings=dataset_profile.warnings if dataset_profile is not None else [],
        ).to_dict()

    def write_run_metadata(
        self,
        run_metadata_path: Path,
        run_metadata: dict[str, object],
    ) -> Path:
        """Write run metadata JSON and return its path."""

        run_metadata_path.parent.mkdir(parents=True, exist_ok=True)
        run_metadata_path.write_text(
            json.dumps(run_metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        return run_metadata_path

    @staticmethod
    def generate_run_id(generated_at: datetime | None = None) -> str:
        """Return a unique ADE run identifier."""

        timestamp = (generated_at or datetime.now(UTC)).strftime("%Y%m%d_%H%M%S")
        short_uuid = uuid.uuid4().hex[:6]
        return f"ade_{timestamp}_{short_uuid}"

    def _candidate_anomaly_json(
        self,
        rank: int,
        candidate: CandidateAnomaly,
        assets: ReportAssets,
        review_memory_summary: ReviewMemorySummary | None = None,
    ) -> dict[str, object]:
        """Return one candidate anomaly as JSON-safe data."""

        patch = candidate.embedding.patch
        anomaly = CandidateAnomaly(
            embedding=candidate.embedding,
            novelty_score=candidate.novelty_score,
            anomaly_id=candidate.anomaly_id or f"anomaly-{rank:04d}",
            preview_path=assets.anomaly_previews.get(rank),
        ).to_dict()
        anomaly_data = {
            "rank": int(rank),
            "anomaly_id": candidate.anomaly_id or f"anomaly-{rank:04d}",
            "source_path": anomaly["source_path"],
            "coordinates": [int(value) for value in patch.coordinates],
            "patch_size": patch.patch_size,
            "patch_stride": patch.patch_stride,
            "scale_id": patch.scale_id,
            "scale_label": patch.scale_label,
            "novelty_score": anomaly["novelty_score"],
            "normalized_score": candidate.metadata.get("normalized_score"),
            "scoring_backend": candidate.metadata.get("scoring_backend"),
            "nearest_neighbor_id": candidate.metadata.get("nearest_neighbor_id"),
            "feature_deviations": candidate.metadata.get("feature_deviations", []),
            "reason": candidate.metadata.get("reason"),
            "preview_path": anomaly["preview_path"],
            "selection_reason": candidate.metadata.get("selection_reason"),
            "selection_rank": candidate.metadata.get("selection_rank"),
            "score_breakdown": candidate.metadata.get("score_breakdown", {}),
            "label": "candidate anomaly",
            "requires_human_review": self.human_review_required,
        }
        if review_memory_summary is not None:
            anomaly_data["review_memory_signal"] = score_candidate_with_review_memory(
                anomaly_data,
                "anomaly",
                review_memory_summary,
            ).to_dict()
        return anomaly_data

    def _concept_json(
        self,
        evidence: ConceptEvidence,
        confidence: ConceptConfidence | None,
        hypothesis: Hypothesis | None,
        assets: ReportAssets,
        review_memory_summary: ReviewMemorySummary | None = None,
    ) -> dict[str, object]:
        """Return one candidate unknown concept as JSON-safe data."""

        examples = []
        for example_index, item in enumerate(evidence.examples, start=1):
            preview_path = assets.concept_previews.get((evidence.concept_id, example_index))
            examples.append(
                {
                    "anomaly_id": item.anomaly_id,
                    "source_path": str(item.source_path),
                    "coordinates": [int(value) for value in item.coordinates],
                    "x": int(item.coordinates[0]),
                    "y": int(item.coordinates[1]),
                    "patch_size": int(item.patch_size),
                    "patch_stride": item.patch_stride,
                    "scale_id": item.scale_id,
                    "scale_label": item.scale_label,
                    "novelty_score": float(item.novelty_score),
                    "preview_path": preview_path,
                }
            )
        anomaly_ids = [str(example["anomaly_id"]) for example in examples if example["anomaly_id"]]
        evidence_summary = self._evidence_summary_json(evidence, assets)
        confidence_breakdown = self._json_confidence_breakdown(
            confidence.breakdown
            if confidence and confidence.breakdown
            else evidence.confidence_breakdown
        )

        concept_model = UnknownConcept(
            concept_id=evidence.concept_id,
            anomaly_ids=anomaly_ids,
            representative_anomaly_id=evidence.representative_anomaly_id,
            average_novelty_score=evidence.average_novelty,
            confidence_score=confidence.score if confidence else None,
            consistency_score=evidence.consistency,
            diversity_score=evidence.diversity_score,
            confidence_breakdown=confidence_breakdown,
            evidence=EvidenceSummary(
                supporting_examples=evidence_summary["supporting_examples"],
                representative_examples=evidence_summary["representative_examples"],
                near_matches=evidence_summary["near_matches"],
                nearest_neighbors=evidence_summary["nearest_neighbors"],
                normal_comparisons=evidence_summary["normal_comparisons"],
                notes=evidence_summary["notes"],
                warnings=evidence_summary["warnings"],
            ),
            notes=[
                "Candidate concept may indicate a recurring visual pattern.",
                "Requires human review before interpretation.",
            ],
        )
        concept_data = concept_model.to_dict()

        concept_data = {
            "concept_id": evidence.concept_id,
            "label": "candidate unknown concept",
            "anomaly_ids": concept_data["anomaly_ids"],
            "representative_anomaly_id": concept_data["representative_anomaly_id"],
            "example_count": int(evidence.example_count),
            "supporting_example_count": int(evidence.item_count or evidence.example_count),
            "source_image_count": int(evidence.source_image_count),
            "average_novelty": concept_data["average_novelty_score"],
            "average_novelty_score": concept_data["average_novelty_score"],
            "cluster_consistency": float(evidence.consistency),
            "consistency_score": concept_data["consistency_score"],
            "diversity_score": concept_data["diversity_score"],
            "confidence_score": concept_data["confidence_score"],
            "confidence_breakdown": concept_data["confidence_breakdown"],
            "evidence_summary": concept_data["evidence"],
            "summary": evidence.summary,
            "possible_pattern": hypothesis.text if hypothesis else None,
            "examples": examples,
            "requires_human_review": self.human_review_required,
        }
        if review_memory_summary is not None:
            concept_data["review_memory_signal"] = score_candidate_with_review_memory(
                concept_data,
                "concept",
                review_memory_summary,
            ).to_dict()
        return concept_data

    def save_assets(
        self,
        output_path: Path | str,
        candidates: list[CandidateAnomaly],
        evidence_items: list[ConceptEvidence],
    ) -> ReportAssets:
        """Save anomaly and concept patch previews next to the report."""

        path = Path(output_path)
        assets_dir = path.parent / self.assets_dir_name
        assets_dir.mkdir(parents=True, exist_ok=True)

        anomaly_previews: dict[int, str] = {}
        if not self.save_patch_previews:
            return ReportAssets(anomaly_previews={}, concept_previews={})

        for index, candidate in enumerate(candidates, start=1):
            asset_path = assets_dir / f"anomaly_{index:04d}.png"
            self._save_patch_image(candidate, asset_path)
            anomaly_previews[index] = self._relative_markdown_path(asset_path, path.parent)

        candidates_by_patch = {
            self._patch_key(candidate): candidate
            for candidate in candidates
        }
        concept_previews: dict[tuple[str, int], str] = {}
        for evidence in evidence_items:
            concept_slug = self._slugify(evidence.concept_id)
            for example_index, item in enumerate(evidence.examples, start=1):
                matched_candidate = candidates_by_patch.get((str(item.source_path), item.coordinates))
                if matched_candidate is None:
                    continue
                asset_path = assets_dir / f"{concept_slug}_example_{example_index:03d}.png"
                self._save_patch_image(matched_candidate, asset_path)
                concept_previews[
                    (evidence.concept_id, example_index)
                ] = self._relative_markdown_path(asset_path, path.parent)

        return ReportAssets(anomaly_previews=anomaly_previews, concept_previews=concept_previews)

    @staticmethod
    def _save_patch_image(candidate: CandidateAnomaly, output_path: Path) -> None:
        """Write a candidate patch array as a PNG preview."""

        import numpy as np

        array = candidate.embedding.patch.array
        if array.dtype != np.uint8:
            array = np.clip(array, 0, 255).astype(np.uint8)
        if array.ndim != 3 or array.shape[2] != 3:
            raise ValueError("patch image assets require RGB arrays with shape (height, width, 3)")

        height, width, _ = array.shape
        scanlines = b"".join(b"\x00" + array[row].tobytes() for row in range(height))
        png_bytes = b"".join(
            [
                b"\x89PNG\r\n\x1a\n",
                ReportGenerator._png_chunk(
                    b"IHDR",
                    struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0),
                ),
                ReportGenerator._png_chunk(b"IDAT", zlib.compress(scanlines)),
                ReportGenerator._png_chunk(b"IEND", b""),
            ]
        )
        output_path.write_bytes(png_bytes)

    @staticmethod
    def _png_chunk(chunk_type: bytes, data: bytes) -> bytes:
        """Return one PNG chunk with checksum."""

        checksum = zlib.crc32(chunk_type + data) & 0xFFFFFFFF
        return struct.pack(">I", len(data)) + chunk_type + data + struct.pack(">I", checksum)

    @staticmethod
    def _patch_key(candidate: CandidateAnomaly) -> tuple[str, tuple[int, int, int, int]]:
        """Return a stable key for matching evidence to candidate patches."""

        patch = candidate.embedding.patch
        return (str(patch.source_path), patch.coordinates)

    @staticmethod
    def _relative_markdown_path(asset_path: Path, report_dir: Path) -> str:
        """Return a Markdown-friendly path relative to the report file."""

        return asset_path.relative_to(report_dir).as_posix()

    @staticmethod
    def _markdown_image(alt_text: str, relative_path: str | None) -> str:
        """Return Markdown image syntax or a placeholder when no asset exists."""

        if relative_path is None:
            return "preview unavailable"
        return f"![{alt_text}]({relative_path})"

    @staticmethod
    def _dataset_profile_lines(dataset_profile: DatasetProfile | None) -> list[str]:
        """Return concise Markdown lines for a dataset profile."""

        if dataset_profile is None:
            return ["Dataset profile was not provided for this report."]

        width_range = (
            f"{dataset_profile.image_width_min}-{dataset_profile.image_width_max}"
            if dataset_profile.image_width_min is not None
            else "unavailable"
        )
        height_range = (
            f"{dataset_profile.image_height_min}-{dataset_profile.image_height_max}"
            if dataset_profile.image_height_min is not None
            else "unavailable"
        )
        lines = [
            f"- Input type: `{dataset_profile.input_type}`",
            f"- Valid image count: {dataset_profile.valid_images}",
            f"- Unsupported file count: {len(dataset_profile.unsupported_files)}",
            f"- Unreadable file count: {len(dataset_profile.unreadable_files)}",
            f"- Image width range: {width_range}",
            f"- Image height range: {height_range}",
            f"- Estimated patch count: {dataset_profile.estimated_patch_count}",
        ]
        if dataset_profile.warnings:
            lines.append("- Warnings:")
            lines.extend(f"  - {warning}" for warning in dataset_profile.warnings)
        else:
            lines.append("- Warnings: none")
        return lines

    @staticmethod
    def _scoring_strategy(
        analysis_metadata: dict[str, object] | None,
        candidates: list[CandidateAnomaly],
    ) -> str:
        """Return the effective scoring strategy for display."""

        if analysis_metadata and analysis_metadata.get("novelty_strategy") is not None:
            return str(analysis_metadata["novelty_strategy"])
        if candidates:
            breakdown = candidates[0].metadata.get("score_breakdown")
            if isinstance(breakdown, dict) and breakdown.get("strategy") is not None:
                return str(breakdown["strategy"])
        return "global_distance"

    def _candidate_evidence_lines(
        self,
        index: int,
        candidate: CandidateAnomaly,
        assets: ReportAssets,
    ) -> list[str]:
        """Return concise Markdown evidence for one candidate anomaly."""

        patch = candidate.embedding.patch
        preview = self._markdown_image(
            alt_text=f"candidate anomaly {index}",
            relative_path=assets.anomaly_previews.get(index),
        )
        lines = [
            f"### Candidate anomaly {index}: `{candidate.anomaly_id or f'anomaly-{index:04d}'}`",
            "",
            f"- Source: `{patch.source_path.as_posix()}`",
            f"- Coordinates: x={patch.x}, y={patch.y}, width={patch.width}, height={patch.height}",
            f"- Patch scale: `{patch.scale_label or 'single-scale'}` / {patch.patch_size}px",
            f"- Novelty score: {candidate.novelty_score:.4f}",
        ]
        if preview:
            lines.extend(["", preview, ""])

        reason = candidate.metadata.get("reason")
        if reason:
            lines.append(f"- Evidence note: {reason}")
        nearest_neighbor = candidate.metadata.get(
            "nearest_neighbor_id",
        ) or candidate.metadata.get("nearest_neighbor_patch_id")
        if nearest_neighbor:
            lines.append(f"- Nearest visual neighbor: `{nearest_neighbor}`")

        score_breakdown = candidate.metadata.get("score_breakdown")
        if isinstance(score_breakdown, dict) and score_breakdown:
            lines.append("- Score breakdown:")
            for key, value in sorted(score_breakdown.items()):
                if isinstance(value, int | float):
                    lines.append(f"  - `{key}`: {float(value):.4f}")
                else:
                    lines.append(f"  - `{key}`: `{value}`")

        deviations = candidate.metadata.get("feature_deviations")
        if isinstance(deviations, list) and deviations:
            lines.append("- Largest feature deviations:")
            for item in deviations[:3]:
                if not isinstance(item, dict):
                    continue
                feature = item.get("feature")
                deviation = item.get("deviation", item.get("z_deviation"))
                if feature is None or not isinstance(deviation, int | float):
                    continue
                lines.append(f"  - `{feature}`: {float(deviation):+.4f}")
        lines.append("")
        return lines

    @staticmethod
    def _scoring_metadata_json(
        analysis_metadata: dict[str, object] | None,
        candidates: list[CandidateAnomaly],
    ) -> dict[str, object]:
        """Return JSON-safe scoring metadata."""

        strategy = ReportGenerator._scoring_strategy(analysis_metadata, candidates)
        return {
            "novelty_strategy": strategy,
            "memory_aware_scoring_enabled": (
                bool(analysis_metadata.get("memory_aware_scoring_enabled"))
                if analysis_metadata is not None
                and analysis_metadata.get("memory_aware_scoring_enabled") is not None
                else strategy != "global_distance"
            ),
            "neighbor_top_k": (
                _int_value(analysis_metadata.get("neighbor_top_k"))
                if analysis_metadata is not None
                and analysis_metadata.get("neighbor_top_k") is not None
                else None
            ),
            "scoring_fallback_used": (
                bool(analysis_metadata.get("scoring_fallback_used"))
                if analysis_metadata is not None
                and analysis_metadata.get("scoring_fallback_used") is not None
                else False
            ),
            "scoring_fallback_reason": (
                str(analysis_metadata.get("scoring_fallback_reason"))
                if analysis_metadata is not None
                and analysis_metadata.get("scoring_fallback_reason") is not None
                else None
            ),
        }

    @staticmethod
    def _analysis_metadata_lines(
        analysis_metadata: dict[str, object] | None,
        candidates: list[CandidateAnomaly],
    ) -> list[str]:
        """Return compact Markdown lines for scoring and selection metadata."""

        metadata = ReportGenerator._scoring_metadata_json(analysis_metadata, candidates)
        lines = [
            f"- Novelty strategy: `{metadata['novelty_strategy']}`",
            "- Memory-aware scoring enabled: "
            f"{metadata['memory_aware_scoring_enabled']}",
            f"- Neighbor top-k: {metadata['neighbor_top_k'] or 'n/a'}",
            f"- Scoring fallback used: {metadata['scoring_fallback_used']}",
        ]
        if metadata["scoring_fallback_reason"]:
            lines.append(f"- Scoring fallback reason: {metadata['scoring_fallback_reason']}")
        if analysis_metadata:
            if analysis_metadata.get("anomaly_selection_strategy") is not None:
                lines.append(
                    "- Anomaly selection strategy: "
                    f"`{analysis_metadata['anomaly_selection_strategy']}`"
                )
            if analysis_metadata.get("patch_scales_used") is not None:
                lines.append(
                    "- Patch scales used: "
                    + ", ".join(
                        str(item)
                        for item in _list_value(analysis_metadata["patch_scales_used"])
                    )
                )
        return lines

    @staticmethod
    def _review_memory_lines(
        review_memory_summary: ReviewMemorySummary | None,
    ) -> list[str]:
        """Return Markdown lines for local review-memory context."""

        if review_memory_summary is None:
            return [
                "Review-memory ranking support was not enabled for this report.",
                "All candidate findings still require human review.",
            ]
        lines = [
            "Review-memory signals summarize local human-review feedback as "
            "ranking hints, not automated truth.",
            f"- Feedback records available: {review_memory_summary.total_feedback_count}",
        ]
        if not review_memory_summary.label_counts:
            lines.append("- Label counts: none")
            return lines

        lines.append("- Label counts:")
        for label, count in sorted(review_memory_summary.label_counts.items()):
            lines.append(f"  - `{label}`: {count}")
        return lines

    @staticmethod
    def _review_memory_signal_cell(signal: object | None) -> str:
        """Return a compact Markdown rendering for one review-memory signal."""

        if not isinstance(signal, ReviewMemorySignal):
            return "no signal"
        if signal.matched_feedback_count == 0:
            return "no matching feedback"
        notes = "; ".join(signal.notes) if signal.notes else signal.explanation
        return f"delta {signal.priority_delta:+.2f}; {notes}"

    @staticmethod
    def _backend_metadata_json(
        analysis_metadata: dict[str, object] | None,
        candidates: list[CandidateAnomaly],
    ) -> dict[str, object]:
        """Return backward-compatible backend metadata for report consumers."""

        first_metadata = candidates[0].metadata if candidates else {}
        scoring_backend = (
            analysis_metadata.get("scoring_backend")
            if analysis_metadata and analysis_metadata.get("scoring_backend") is not None
            else "centroid_distance"
        )
        clustering_backend = (
            analysis_metadata.get("clustering_backend")
            if analysis_metadata and analysis_metadata.get("clustering_backend") is not None
            else "threshold_candidate_grouping"
        )
        feature_vector_length = 0
        if candidates:
            feature_vector_length = int(candidates[0].embedding.vector.size)
        return {
            "scoring_backend": str(scoring_backend),
            "clustering_backend": str(clustering_backend),
            "top_k": (
                analysis_metadata.get("top_k")
                if analysis_metadata and analysis_metadata.get("top_k") is not None
                else len(candidates)
            ),
            "random_seed": (
                analysis_metadata.get("random_seed")
                if analysis_metadata and analysis_metadata.get("random_seed") is not None
                else None
            ),
            "feature_vector_count": len(candidates),
            "feature_vector_length": feature_vector_length,
        }

    @staticmethod
    def _confidence_breakdown_lines(
        breakdown: dict[str, float] | None,
    ) -> list[str]:
        """Return Markdown lines for a concept confidence breakdown."""

        if not breakdown:
            return ["  - unavailable"]
        labels = [
            ("novelty_strength", "Novelty strength"),
            ("support_count", "Support count"),
            ("consistency", "Consistency"),
            ("source_diversity", "Source diversity"),
            ("data_quality", "Data quality"),
            ("final_confidence", "Final confidence"),
        ]
        return [
            f"  - {label}: {float(breakdown.get(key, 0.0)):.4f}"
            for key, label in labels
        ]

    @staticmethod
    def _json_confidence_breakdown(
        breakdown: dict[str, float] | None,
    ) -> dict[str, float]:
        """Return JSON-safe confidence breakdown values."""

        if not breakdown:
            return {}
        return {str(key): float(value) for key, value in breakdown.items()}

    @staticmethod
    def _evidence_summary_json(
        evidence: ConceptEvidence,
        assets: ReportAssets,
    ) -> EvidenceSummaryJson:
        """Return a JSON-safe structured evidence bundle."""

        supporting_examples = []
        for example_index, item in enumerate(evidence.examples, start=1):
            example = item.to_dict()
            example["preview_path"] = assets.concept_previews.get(
                (evidence.concept_id, example_index)
            )
            supporting_examples.append(example)
        bundle = evidence.evidence_summary or {}
        return {
            "supporting_examples": supporting_examples,
            "representative_examples": supporting_examples[:1],
            "near_matches": _list_value(bundle.get("near_matches")),
            "nearest_neighbors": _list_value(bundle.get("nearest_neighbors")),
            "normal_comparisons": _list_value(bundle.get("normal_comparisons")),
            "notes": _string_list(
                bundle.get("notes"),
                [
                    "Candidate concept is based on visually similar candidate anomalies.",
                    "Requires human review.",
                ],
            ),
            "warnings": _string_list(bundle.get("warnings")),
        }

    @staticmethod
    def _near_match_lines(evidence: ConceptEvidence, max_rows: int = 5) -> list[str]:
        """Return concise Markdown lines for nearest-neighbor evidence."""

        bundle = evidence.evidence_summary or {}
        matches = bundle.get("nearest_neighbors") or bundle.get("near_matches") or []
        if not isinstance(matches, list):
            return []

        lines: list[str] = []
        for match in matches[:max_rows]:
            if not isinstance(match, dict):
                continue
            metadata = match.get("metadata", {})
            source_path = ""
            coordinates = ""
            if isinstance(metadata, dict):
                source_path = str(metadata.get("source_path", "unknown"))
                coordinates = (
                    f"({metadata.get('x', '?')}, {metadata.get('y', '?')}, "
                    f"{metadata.get('width', '?')}, {metadata.get('height', '?')})"
                )
            lines.append(
                "- "
                f"`{match.get('item_id', 'unknown')}` from `{source_path}` "
                f"at {coordinates}; distance {float(match.get('distance', 0.0)):.4f}"
            )
        return lines

    @staticmethod
    def _average_concept_confidence(
        evidence_items: list[ConceptEvidence],
    ) -> float | None:
        """Return average concept confidence for concise run metadata."""

        if not evidence_items:
            return None
        return float(
            sum(item.confidence_score for item in evidence_items) / len(evidence_items)
        )

    @staticmethod
    def _average_concept_consistency(
        evidence_items: list[ConceptEvidence],
    ) -> float | None:
        """Return average concept consistency for concise run metadata."""

        if not evidence_items:
            return None
        return float(sum(item.consistency for item in evidence_items) / len(evidence_items))

    @staticmethod
    def _slugify(value: str) -> str:
        """Return a filename-safe identifier for report assets."""

        slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
        return slug or "concept"

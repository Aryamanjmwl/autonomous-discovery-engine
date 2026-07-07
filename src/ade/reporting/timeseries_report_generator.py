"""Markdown and JSON reports for ADE time-series discovery runs."""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ade import __version__
from ade.discovery.timeseries import TimeSeriesConcept, TimeSeriesFinding
from ade.models import RunMetadata, TimeSeriesProfile
from ade.reporting.report_generator import ReportGenerator
from ade.reporting.run_index import build_run_summary, update_run_index


class TimeSeriesReportGenerator:
    """Generate reviewable reports for timestamped CSV discovery."""

    name = "timeseries_markdown_json_report"

    def __init__(
        self,
        project_name: str = "ADE",
        pipeline_version: str = __version__,
        report_version: str = "1.0",
        human_review_required: bool = True,
        runs_dir_name: str = "runs",
    ) -> None:
        self.project_name = project_name
        self.pipeline_version = pipeline_version
        self.report_version = report_version
        self.human_review_required = human_review_required
        self.runs_dir_name = runs_dir_name

    def write(
        self,
        output_path: Path,
        profile: TimeSeriesProfile,
        findings: list[TimeSeriesFinding],
        concepts: list[TimeSeriesConcept],
        backend_metadata: dict[str, object],
    ) -> Path:
        """Write Markdown, JSON, run metadata, and run index entries."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        generated_at = datetime.now(UTC)
        run_id = ReportGenerator.generate_run_id(generated_at)
        json_path = output_path.with_suffix(".json")
        runs_dir = output_path.parent / self.runs_dir_name
        run_metadata_path = runs_dir / f"{run_id}.json"
        run_index_path = runs_dir / "index.json"
        run_metadata = self._run_metadata(
            run_id=run_id,
            generated_at=generated_at,
            profile=profile,
            markdown_report_path=output_path,
            json_report_path=json_path,
            run_index_path=run_index_path,
            finding_count=len(findings),
            concept_count=len(concepts),
        )

        output_path.write_text(
            self.generate_markdown(
                run_id=run_id,
                profile=profile,
                findings=findings,
                concepts=concepts,
                backend_metadata=backend_metadata,
            ),
            encoding="utf-8",
        )
        json_path.write_text(
            json.dumps(
                self.generate_json(
                    run_id=run_id,
                    generated_at=generated_at.isoformat(),
                    profile=profile,
                    findings=findings,
                    concepts=concepts,
                    backend_metadata=backend_metadata,
                    run_metadata=run_metadata,
                ),
                indent=2,
                sort_keys=True,
            ),
            encoding="utf-8",
        )
        run_metadata_path.parent.mkdir(parents=True, exist_ok=True)
        run_metadata_path.write_text(
            json.dumps(run_metadata, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        update_run_index(
            index_path=run_index_path,
            run_summary=build_run_summary(run_metadata, run_metadata_path),
        )
        return output_path

    def generate_markdown(
        self,
        run_id: str,
        profile: TimeSeriesProfile,
        findings: list[TimeSeriesFinding],
        concepts: list[TimeSeriesConcept],
        backend_metadata: dict[str, object],
    ) -> str:
        """Return a Markdown time-series discovery report."""

        lines = [
            "# ADE Time-Series Discovery Report",
            "",
            "ADE Discovery Report for exploratory review. Findings below are candidate "
            "time-series patterns and require human review.",
            "",
            f"**Run ID:** `{run_id}`",
            "",
            "## Dataset Summary",
            "",
            "- Modality: `timeseries`",
            f"- Input CSV: `{profile.input_path}`",
            f"- Row count: {profile.row_count}",
            f"- Timestamp column: `{profile.timestamp_column}`",
            f"- Entity column: `{profile.entity_column or 'none'}`",
            f"- Time range: {profile.time_start or 'unavailable'} to {profile.time_end or 'unavailable'}",
            f"- Signal columns: {len(profile.signal_columns)}",
            f"- Candidate time-series findings: {len(findings)}",
            f"- Candidate time-series concepts: {len(concepts)}",
            "",
            "## Time-Series Profile",
            "",
            f"- Signal columns: {', '.join(profile.signal_columns) or 'none'}",
            f"- Missing timestamps: {profile.missing_timestamp_count}",
            f"- Malformed timestamps: {profile.malformed_timestamp_count}",
            f"- Duplicate timestamps: {profile.duplicate_timestamp_count}",
            "- Sampling interval summary:",
        ]
        for key, value in profile.sampling_interval_summary.items():
            lines.append(f"  - `{key}`: {value}")
        lines.append("- Missing values:")
        lines.extend(
            f"  - `{column}`: {count}"
            for column, count in profile.missing_value_summary.items()
        )
        if profile.warnings:
            lines.append("- Warnings:")
            lines.extend(f"  - {warning}" for warning in profile.warnings)
        else:
            lines.append("- Warnings: none")

        lines.extend(
            [
                "",
                "## Feature Extraction Summary",
                "",
                f"- Embedding backend: `{backend_metadata.get('embedding_backend')}`",
                f"- Scoring backend: `{backend_metadata.get('scoring_backend')}`",
                f"- Grouping backend: `{backend_metadata.get('clustering_backend')}`",
                f"- Feature vector count: {backend_metadata.get('feature_vector_count')}",
                f"- Feature vector length: {backend_metadata.get('feature_vector_length')}",
                f"- Window size: {backend_metadata.get('window_size')}",
                "",
                "## Top Time-Series Findings",
                "",
            ]
        )
        if findings:
            lines.extend(
                [
                    "| Rank | Timestamp | Row | Score | Reason | Top contributing signals |",
                    "| ---: | --- | ---: | ---: | --- | --- |",
                ]
            )
            for finding in findings:
                lines.append(
                    f"| {finding.rank} | `{finding.timestamp}` | {finding.row_index} | "
                    f"{finding.novelty_score:.4f} | {finding.reason} | "
                    f"{self._deviation_summary(finding)} |"
                )
        else:
            lines.append("No candidate time-series findings were identified.")

        lines.extend(["", "## Candidate Time-Series Concepts", ""])
        if concepts:
            for concept in concepts:
                lines.extend(
                    [
                        f"### {concept.concept_id}",
                        "",
                        f"- Example count: {len(concept.findings)}",
                        f"- Average novelty: {concept.average_novelty:.4f}",
                        f"- Confidence score: {concept.confidence_score:.4f}",
                        f"- Summary: {concept.summary}",
                        "",
                    ]
                )
        else:
            lines.append("No candidate time-series concepts were grouped.")

        lines.extend(
            [
                "## Human Expert Review Required",
                "",
                "All results are exploratory candidate findings. Candidate time-series "
                "findings, candidate concepts, possible relationships, and hypotheses "
                "require human expert review before scientific, operational, commercial, "
                "financial, or clinical interpretation.",
                "",
            ]
        )
        return "\n".join(lines)

    def generate_json(
        self,
        run_id: str,
        generated_at: str,
        profile: TimeSeriesProfile,
        findings: list[TimeSeriesFinding],
        concepts: list[TimeSeriesConcept],
        backend_metadata: dict[str, object],
        run_metadata: dict[str, object],
    ) -> dict[str, object]:
        """Return a machine-readable time-series report."""

        profile_data = profile.to_dict()
        return {
            "project_name": self.project_name,
            "report_version": self.report_version,
            "run_id": run_id,
            "generated_at": generated_at,
            "modality": "timeseries",
            "run_metadata": run_metadata,
            "run_index_path": run_metadata.get("run_index_path"),
            "input_summary": {
                "input_dir": profile.input_path.as_posix(),
                "input_path": profile.input_path.as_posix(),
                "modality": "timeseries",
                "row_count": profile.row_count,
                "timestamp_column": profile.timestamp_column,
                "entity_column": profile.entity_column,
                "time_start": profile.time_start,
                "time_end": profile.time_end,
                "signal_column_count": len(profile.signal_columns),
            },
            "dataset_profile": {
                **profile_data,
                "valid_images": 0,
                "estimated_patch_count": 0,
                "unsupported_file_count": 0,
                "unreadable_file_count": 0,
            },
            "timeseries_profile": profile_data,
            "backend_metadata": backend_metadata,
            "number_of_images": 0,
            "number_of_patches": profile.row_count,
            "number_of_rows": profile.row_count,
            "number_of_signal_columns": len(profile.signal_columns),
            "number_of_candidate_anomalies": len(findings),
            "number_of_candidate_unknown_concepts": len(concepts),
            "candidate_anomalies": [finding.to_dict() for finding in findings],
            "candidate_unknown_concepts": [concept.to_dict() for concept in concepts],
            "evidence_summary": [
                {
                    "concept_id": concept.concept_id,
                    "example_count": len(concept.findings),
                    "average_novelty": concept.average_novelty,
                    "summary": concept.summary,
                }
                for concept in concepts
            ],
            "confidence_scores": [
                {
                    "concept_id": concept.concept_id,
                    "confidence_score": concept.confidence_score,
                }
                for concept in concepts
            ],
            "hypotheses": [
                {
                    "concept_id": concept.concept_id,
                    "hypothesis": (
                        "Points in this group may share a candidate time-series pattern. "
                        "This hypothesis requires human review."
                    ),
                }
                for concept in concepts
            ],
            "human_review_required": self.human_review_required,
            "limitations": [
                "CSV time-series support is currently point/window-feature level only.",
                "No forecasting, streaming ingestion, or production alerting is applied.",
                "Scores are unsupervised ranking signals, not proof of significance.",
                "Candidate time-series patterns require human review.",
            ],
        }

    def _run_metadata(
        self,
        run_id: str,
        generated_at: datetime,
        profile: TimeSeriesProfile,
        markdown_report_path: Path,
        json_report_path: Path,
        run_index_path: Path,
        finding_count: int,
        concept_count: int,
    ) -> dict[str, object]:
        """Build run metadata compatible with the existing run index."""

        data = RunMetadata(
            run_id=run_id,
            generated_at=generated_at.isoformat(),
            input_path=profile.input_path,
            markdown_report_path=markdown_report_path,
            json_report_path=json_report_path,
            run_index_path=run_index_path,
            number_of_images=0,
            number_of_patches=profile.row_count,
            number_of_candidate_anomalies=finding_count,
            number_of_candidate_unknown_concepts=concept_count,
            pipeline_version=self.pipeline_version,
            human_review_required=self.human_review_required,
            number_of_input_files=1,
            number_of_valid_images=0,
            number_of_unsupported_files=0,
            number_of_unreadable_files=0,
            estimated_patch_count=0,
            input_warnings=profile.warnings,
        ).to_dict()
        data.update(
            {
                "modality": "timeseries",
                "number_of_rows": profile.row_count,
                "timestamp_column": profile.timestamp_column,
                "entity_column": profile.entity_column,
                "time_start": profile.time_start,
                "time_end": profile.time_end,
                "number_of_signal_columns": len(profile.signal_columns),
            }
        )
        return data

    @staticmethod
    def _deviation_summary(finding: TimeSeriesFinding) -> str:
        """Return a compact Markdown-safe deviation summary."""

        if finding.spike_signals:
            return "spike: " + ", ".join(f"`{signal}`" for signal in finding.spike_signals[:3])
        if finding.time_gap_indicator > 0:
            return f"time gap: {finding.gap_seconds:.1f}s"
        if finding.missing_signals:
            return "missing: " + ", ".join(f"`{signal}`" for signal in finding.missing_signals[:3])
        if not finding.feature_deviations:
            return "not available"
        return ", ".join(
            f"`{item['feature']}` ({float(item['deviation']):+.3f})"
            for item in finding.feature_deviations[:3]
        )

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
from typing import Any

from ade import __version__
from ade.discovery.confidence_scorer import ConceptConfidence
from ade.discovery.evidence_collector import ConceptEvidence
from ade.discovery.novelty_scorer import CandidateAnomaly
from ade.models import (
    DatasetProfile,
    EvidenceSummary,
    ReportArtifact,
    RunMetadata,
    UnknownConcept,
)
from ade.reasoning.hypothesis_generator import Hypothesis
from ade.reporting.run_index import build_run_summary, update_run_index


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
            backend_metadata=run_result.get("backend_metadata"),
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
        backend_metadata: dict[str, object] | None = None,
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
            "",
            "## Input Dataset Profile",
            "",
            *self._dataset_profile_lines(dataset_profile),
            "",
            "## Discovery Backend Metadata",
            "",
            *self._backend_metadata_lines(backend_metadata),
            "",
            "## Top Candidate Anomalies",
            "",
        ]

        if candidates:
            lines.extend(
                [
                    "| Rank | Preview | Source | Coordinates | Novelty score |",
                    "| --- | --- | --- | --- | ---: |",
                ]
            )
            for index, candidate in enumerate(candidates, start=1):
                patch = candidate.embedding.patch
                preview = self._markdown_image(
                    alt_text=f"candidate anomaly {index}",
                    relative_path=assets.anomaly_previews.get(index),
                )
                lines.append(
                    f"| {index} | {preview} | `{patch.source_path}` | "
                    f"`{patch.coordinates}` | {candidate.novelty_score:.4f} |"
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
                        f"- Representative anomaly: {evidence.representative_anomaly_id}",
                        f"- Concept item count: {evidence.item_count}",
                        f"- Concept summary: {evidence.summary or 'Not available'}",
                        (
                            f"- Confidence score: {confidence.score:.4f}"
                            if confidence
                            else "- Confidence score: unavailable"
                        ),
                        "",
                        "Evidence summary for this possible pattern:",
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
                        f"rank {item.rank or 'n/a'}; "
                        f"backend {item.scoring_backend or 'unknown'}; "
                        f"{item.reason or 'requires review'}"
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
                "All results are exploratory candidate findings. Candidate anomalies, "
                "candidate unknown concepts, possible relationships, and hypotheses "
                "require human expert review before any scientific, clinical, "
                "operational, commercial, or financial interpretation.",
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
        backend_metadata: dict[str, object] | None = None,
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
            backend_metadata=backend_metadata,
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
            backend_metadata=backend_metadata,
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
        backend_metadata: dict[str, object] | None = None,
    ) -> dict[str, object]:
        """Return a machine-readable ADE discovery report."""

        confidence_by_id = {confidence.concept_id: confidence for confidence in confidences}
        hypothesis_by_id = {hypothesis.concept_id: hypothesis for hypothesis in hypotheses}
        assets = assets or ReportAssets(anomaly_previews={}, concept_previews={})

        candidate_anomalies = [
            self._candidate_anomaly_json(index, candidate, assets)
            for index, candidate in enumerate(candidates, start=1)
        ]
        candidate_unknown_concepts = [
            self._concept_json(
                evidence=evidence,
                confidence=confidence_by_id.get(evidence.concept_id),
                hypothesis=hypothesis_by_id.get(evidence.concept_id),
                assets=assets,
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
            "backend_metadata": backend_metadata or {},
            "number_of_images": int(dataset_summary.image_count),
            "number_of_patches": int(dataset_summary.patch_count),
            "number_of_candidate_anomalies": len(candidate_anomalies),
            "number_of_candidate_unknown_concepts": len(candidate_unknown_concepts),
            "candidate_anomalies": candidate_anomalies,
            "candidate_unknown_concepts": candidate_unknown_concepts,
            "evidence_summary": [
                {
                    "concept_id": evidence.concept_id,
                    "example_count": int(evidence.example_count),
                    "average_novelty": float(evidence.average_novelty),
                    "cluster_consistency": float(evidence.consistency),
                    "representative_anomaly_id": evidence.representative_anomaly_id,
                    "item_count": int(evidence.item_count),
                    "summary": evidence.summary,
                }
                for evidence in evidence_items
            ],
            "confidence_scores": [
                {
                    "concept_id": confidence.concept_id,
                    "confidence_score": float(confidence.score),
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
            "limitations": [
                "All findings are exploratory candidate findings.",
                "Candidate anomalies and candidate unknown concepts require human review.",
                "The current MVP uses deterministic placeholder image statistics, "
                "not deep learning.",
                "Backend scores are ranking signals, not proof of significance.",
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
    ) -> dict[str, object]:
        """Return one candidate anomaly as JSON-safe data."""

        patch = candidate.embedding.patch
        anomaly = CandidateAnomaly(
            embedding=candidate.embedding,
            novelty_score=candidate.novelty_score,
            anomaly_id=candidate.anomaly_id or f"anomaly-{rank:04d}",
            preview_path=assets.anomaly_previews.get(rank),
        ).to_dict()
        return {
            "rank": int(rank),
            "anomaly_id": candidate.anomaly_id or f"anomaly-{rank:04d}",
            "source_path": anomaly["source_path"],
            "coordinates": [int(value) for value in patch.coordinates],
            "novelty_score": anomaly["novelty_score"],
            "normalized_score": candidate.metadata.get("normalized_score"),
            "scoring_backend": candidate.metadata.get("scoring_backend"),
            "nearest_neighbor_id": candidate.metadata.get("nearest_neighbor_id"),
            "feature_deviations": candidate.metadata.get("feature_deviations", []),
            "reason": candidate.metadata.get("reason"),
            "preview_path": anomaly["preview_path"],
            "label": "candidate anomaly",
            "requires_human_review": self.human_review_required,
        }

    def _concept_json(
        self,
        evidence: ConceptEvidence,
        confidence: ConceptConfidence | None,
        hypothesis: Hypothesis | None,
        assets: ReportAssets,
    ) -> dict[str, object]:
        """Return one candidate unknown concept as JSON-safe data."""

        examples = []
        for example_index, item in enumerate(evidence.examples, start=1):
            examples.append(
                {
                    "source_path": str(item.source_path),
                    "coordinates": [int(value) for value in item.coordinates],
                    "novelty_score": float(item.novelty_score),
                    "normalized_score": item.normalized_score,
                    "anomaly_id": item.anomaly_id,
                    "rank": item.rank,
                    "scoring_backend": item.scoring_backend,
                    "concept_id": item.concept_id,
                    "nearest_neighbor_id": item.nearest_neighbor_id,
                    "feature_deviations": item.feature_deviations or [],
                    "reason": item.reason,
                    "preview_path": assets.concept_previews.get(
                        (evidence.concept_id, example_index)
                    ),
                }
            )

        concept_model = UnknownConcept(
            concept_id=evidence.concept_id,
            anomaly_ids=[
                f"{Path(str(item.source_path)).stem}_{item.coordinates[0]}_"
                f"{item.coordinates[1]}_{item.coordinates[2]}_{item.coordinates[3]}"
                for item in evidence.examples
            ],
            representative_anomaly_id=(
                f"{Path(str(evidence.examples[0].source_path)).stem}_"
                f"{evidence.examples[0].coordinates[0]}_"
                f"{evidence.examples[0].coordinates[1]}_"
                f"{evidence.examples[0].coordinates[2]}_"
                f"{evidence.examples[0].coordinates[3]}"
                if evidence.examples
                else None
            ),
            average_novelty_score=evidence.average_novelty,
            confidence_score=confidence.score if confidence else None,
            evidence=EvidenceSummary(
                supporting_examples=[
                    str(item.source_path) for item in evidence.examples
                ],
                notes=["candidate unknown concept requires human review"],
            ),
        )
        concept_data = concept_model.to_dict()

        return {
            "concept_id": evidence.concept_id,
            "label": "candidate unknown concept",
            "example_count": int(evidence.example_count),
            "average_novelty": concept_data["average_novelty_score"],
            "cluster_consistency": float(evidence.consistency),
            "representative_anomaly_id": evidence.representative_anomaly_id,
            "item_count": int(evidence.item_count),
            "summary": evidence.summary,
            "confidence_score": concept_data["confidence_score"],
            "possible_pattern": hypothesis.text if hypothesis else None,
            "examples": examples,
            "requires_human_review": self.human_review_required,
        }

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
                candidate = candidates_by_patch.get((str(item.source_path), item.coordinates))
                if candidate is None:
                    continue
                asset_path = assets_dir / f"{concept_slug}_example_{example_index:03d}.png"
                self._save_patch_image(candidate, asset_path)
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
    def _backend_metadata_lines(backend_metadata: dict[str, object] | None) -> list[str]:
        """Return concise Markdown lines for selected discovery backends."""

        if not backend_metadata:
            return ["Backend metadata was not provided for this report."]
        return [
            f"- Scoring backend: `{backend_metadata.get('scoring_backend', 'unknown')}`",
            f"- Clustering backend: `{backend_metadata.get('clustering_backend', 'unknown')}`",
            f"- Top K: {backend_metadata.get('top_k', 'unknown')}",
            f"- Random seed: {backend_metadata.get('random_seed', 'not used')}",
            f"- Feature vector count: {backend_metadata.get('feature_vector_count', 'unknown')}",
            f"- Feature vector length: {backend_metadata.get('feature_vector_length', 'unknown')}",
        ]

    @staticmethod
    def _slugify(value: str) -> str:
        """Return a filename-safe identifier for report assets."""

        slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
        return slug or "concept"

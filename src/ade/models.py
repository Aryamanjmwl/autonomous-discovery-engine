"""Typed internal data models for ADE."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


def _json_safe_value(value: Any) -> Any:
    """Return a JSON-safe scalar or container value."""

    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return float(value)
    if isinstance(value, np.bool_):
        return bool(value)
    if isinstance(value, dict):
        return {str(key): _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_safe_value(item) for item in value]
    return value


def _json_safe_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
    """Return metadata with path and NumPy scalar values converted for JSON."""

    return {str(key): _json_safe_value(value) for key, value in metadata.items()}


def _json_safe_evidence_items(items: list[Any]) -> list[Any]:
    """Return JSON-safe evidence items while preserving legacy scalar IDs."""

    safe_items: list[Any] = []
    for item in items:
        if isinstance(item, dict):
            safe_items.append(_json_safe_metadata(item))
        else:
            safe_items.append(_json_safe_value(item))
    return safe_items


@dataclass(frozen=True)
class ImageRecord:
    """Metadata describing an image available for ADE processing."""

    path: Path
    width: int
    height: int
    image_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def mode(self) -> str | None:
        """Return the image mode when available."""

        value = self.metadata.get("mode")
        return str(value) if value is not None else None

    @property
    def format(self) -> str | None:
        """Return the image format when available."""

        value = self.metadata.get("format")
        return str(value) if value is not None else None

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe representation."""

        return {
            "image_id": self.image_id,
            "path": self.path.as_posix(),
            "width": int(self.width),
            "height": int(self.height),
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class ADERecord:
    """Generic source record for future non-visual adapters."""

    record_id: str
    source_path: Path | None = None
    media_type: str = "unknown"
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe source record."""

        return {
            "record_id": self.record_id,
            "source_path": self.source_path.as_posix() if self.source_path else None,
            "media_type": self.media_type,
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class DatasetProfile:
    """Profile and validation summary for one input dataset."""

    input_path: Path
    input_type: str
    total_files: int
    supported_image_files: int
    unsupported_files: list[Path] = field(default_factory=list)
    unreadable_files: list[Path] = field(default_factory=list)
    valid_images: int = 0
    image_width_min: int | None = None
    image_width_max: int | None = None
    image_height_min: int | None = None
    image_height_max: int | None = None
    unique_image_sizes: list[tuple[int, int]] = field(default_factory=list)
    estimated_patch_count: int = 0
    warnings: list[str] = field(default_factory=list)
    is_valid: bool = False

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dataset profile."""

        return {
            "input_path": self.input_path.as_posix(),
            "input_type": self.input_type,
            "total_files": int(self.total_files),
            "supported_image_files": int(self.supported_image_files),
            "unsupported_files": [path.as_posix() for path in self.unsupported_files],
            "unsupported_file_count": len(self.unsupported_files),
            "unreadable_files": [path.as_posix() for path in self.unreadable_files],
            "unreadable_file_count": len(self.unreadable_files),
            "valid_images": int(self.valid_images),
            "image_width_min": self.image_width_min,
            "image_width_max": self.image_width_max,
            "image_height_min": self.image_height_min,
            "image_height_max": self.image_height_max,
            "unique_image_sizes": [
                {"width": int(width), "height": int(height)}
                for width, height in self.unique_image_sizes
            ],
            "estimated_patch_count": int(self.estimated_patch_count),
            "warnings": list(self.warnings),
            "is_valid": bool(self.is_valid),
        }


@dataclass(frozen=True)
class DatasetSummary:
    """Stable summary of an input dataset for public interfaces."""

    input_path: Path
    input_type: str
    record_count: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe dataset summary."""

        return {
            "input_path": self.input_path.as_posix(),
            "input_type": self.input_type,
            "record_count": int(self.record_count),
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class PatchRecord:
    """A fixed-size image patch and its source coordinates."""

    source_path: Path
    array: np.ndarray
    x: int
    y: int
    width: int
    height: int
    patch_id: str = ""
    image_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def coordinates(self) -> tuple[int, int, int, int]:
        """Return coordinates as ``(x, y, width, height)``."""

        return (self.x, self.y, self.width, self.height)

    @property
    def patch_size(self) -> int:
        """Return the configured extraction patch size."""

        return int(self.metadata.get("patch_size", self.width))

    @property
    def patch_stride(self) -> int | None:
        """Return the configured patch stride when known."""

        value = self.metadata.get("patch_stride")
        return int(value) if value is not None else None

    @property
    def scale_id(self) -> str | None:
        """Return the extraction scale identifier when known."""

        value = self.metadata.get("scale_id")
        return str(value) if value is not None else None

    @property
    def scale_label(self) -> str | None:
        """Return the human-readable extraction scale label when known."""

        value = self.metadata.get("scale_label")
        return str(value) if value is not None else None

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe patch metadata without dumping the image array."""

        return {
            "patch_id": self.patch_id,
            "image_id": self.image_id,
            "source_path": self.source_path.as_posix(),
            "x": int(self.x),
            "y": int(self.y),
            "width": int(self.width),
            "height": int(self.height),
            "patch_size": self.patch_size,
            "patch_stride": self.patch_stride,
            "scale_id": self.scale_id,
            "scale_label": self.scale_label,
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class EmbeddingRecord:
    """Embedding and trace metadata for a patch."""

    patch: PatchRecord
    vector: np.ndarray
    patch_id: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe embedding metadata without dumping the full vector."""

        patch_id = self.patch_id or self.patch.patch_id
        return {
            "patch_id": patch_id,
            "vector_length": int(self.vector.size),
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class EmbeddingResult:
    """Backend-neutral embedding result metadata."""

    record_id: str
    vector_length: int
    backend_name: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe embedding result metadata."""

        return {
            "record_id": self.record_id,
            "vector_length": int(self.vector_length),
            "backend_name": self.backend_name,
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class NeighborResult:
    """Nearest-neighbor retrieval result from local vector memory."""

    item_id: str
    distance: float
    similarity: float
    rank: int
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe neighbor result."""

        return {
            "item_id": self.item_id,
            "distance": float(self.distance),
            "similarity": float(self.similarity),
            "rank": int(self.rank),
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class CandidateAnomaly:
    """A patch ranked as a candidate anomaly."""

    embedding: EmbeddingRecord
    novelty_score: float
    anomaly_id: str = ""
    preview_path: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe candidate anomaly representation."""

        patch = self.embedding.patch
        return {
            "anomaly_id": self.anomaly_id,
            "patch_id": patch.patch_id,
            "source_path": patch.source_path.as_posix(),
            "x": int(patch.x),
            "y": int(patch.y),
            "width": int(patch.width),
            "height": int(patch.height),
            "patch_size": patch.patch_size,
            "patch_stride": patch.patch_stride,
            "scale_id": patch.scale_id,
            "scale_label": patch.scale_label,
            "novelty_score": float(self.novelty_score),
            "preview_path": self.preview_path,
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class EvidenceItem:
    """One traceable evidence item attached to a finding."""

    evidence_id: str
    source_path: Path | None
    description: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe evidence item."""

        return {
            "evidence_id": self.evidence_id,
            "source_path": self.source_path.as_posix() if self.source_path else None,
            "description": self.description,
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class Finding:
    """Evidence-backed candidate finding produced by a discovery run."""

    finding_id: str
    finding_type: str
    score: float
    summary: str
    evidence: list[EvidenceItem] = field(default_factory=list)
    requires_human_review: bool = True
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe finding."""

        return {
            "finding_id": self.finding_id,
            "finding_type": self.finding_type,
            "score": float(self.score),
            "summary": self.summary,
            "evidence": [item.to_dict() for item in self.evidence],
            "requires_human_review": bool(self.requires_human_review),
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class EvidenceSummary:
    """Structured evidence attached to a candidate unknown concept."""

    supporting_examples: list[Any] = field(default_factory=list)
    representative_examples: list[Any] = field(default_factory=list)
    near_matches: list[Any] = field(default_factory=list)
    nearest_neighbors: list[Any] = field(default_factory=list)
    normal_comparisons: list[Any] = field(default_factory=list)
    contradicting_examples: list[Any] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe evidence summary."""

        return {
            "supporting_examples": _json_safe_evidence_items(self.supporting_examples),
            "representative_examples": _json_safe_evidence_items(
                self.representative_examples
            ),
            "near_matches": _json_safe_evidence_items(self.near_matches),
            "nearest_neighbors": _json_safe_evidence_items(self.nearest_neighbors),
            "normal_comparisons": _json_safe_evidence_items(
                self.normal_comparisons
            ),
            "contradicting_examples": _json_safe_evidence_items(
                self.contradicting_examples
            ),
            "notes": list(self.notes),
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class UnknownConcept:
    """A cautious grouping of related candidate anomalies."""

    concept_id: str
    anomaly_ids: list[str]
    representative_anomaly_id: str | None
    average_novelty_score: float
    confidence_score: float | None
    evidence: EvidenceSummary
    consistency_score: float | None = None
    diversity_score: float | None = None
    confidence_breakdown: dict[str, float] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe candidate unknown concept representation."""

        return {
            "concept_id": self.concept_id,
            "anomaly_ids": list(self.anomaly_ids),
            "representative_anomaly_id": self.representative_anomaly_id,
            "average_novelty_score": float(self.average_novelty_score),
            "consistency_score": (
                float(self.consistency_score)
                if self.consistency_score is not None
                else None
            ),
            "diversity_score": (
                float(self.diversity_score)
                if self.diversity_score is not None
                else None
            ),
            "confidence_score": (
                float(self.confidence_score)
                if self.confidence_score is not None
                else None
            ),
            "confidence_breakdown": {
                str(key): float(value)
                for key, value in self.confidence_breakdown.items()
            },
            "evidence": self.evidence.to_dict(),
            "notes": list(self.notes),
        }


@dataclass(frozen=True)
class RunMetadata:
    """Traceable metadata for one ADE analysis run."""

    run_id: str
    generated_at: str
    input_path: Path
    markdown_report_path: Path
    json_report_path: Path
    number_of_images: int
    number_of_patches: int
    number_of_candidate_anomalies: int
    number_of_candidate_unknown_concepts: int
    pipeline_version: str
    human_review_required: bool
    run_index_path: Path | None = None
    number_of_input_files: int | None = None
    number_of_valid_images: int | None = None
    number_of_unsupported_files: int | None = None
    number_of_unreadable_files: int | None = None
    estimated_patch_count: int | None = None
    average_concept_confidence: float | None = None
    average_concept_consistency: float | None = None
    memory_enabled: bool | None = None
    memory_metric: str | None = None
    memory_items_indexed: int | None = None
    total_patches: int | None = None
    patch_scales_used: list[str] = field(default_factory=list)
    anomaly_selection_strategy: str | None = None
    input_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe run metadata dictionary."""

        data: dict[str, Any] = {
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "input_path": self.input_path.as_posix(),
            "markdown_report_path": self.markdown_report_path.as_posix(),
            "json_report_path": self.json_report_path.as_posix(),
            "number_of_images": int(self.number_of_images),
            "number_of_patches": int(self.number_of_patches),
            "number_of_candidate_anomalies": int(
                self.number_of_candidate_anomalies
            ),
            "number_of_candidate_unknown_concepts": int(
                self.number_of_candidate_unknown_concepts
            ),
            "pipeline_version": self.pipeline_version,
            "human_review_required": bool(self.human_review_required),
        }
        if self.run_index_path is not None:
            data["run_index_path"] = self.run_index_path.as_posix()
        if self.number_of_input_files is not None:
            data["number_of_input_files"] = int(self.number_of_input_files)
        if self.number_of_valid_images is not None:
            data["number_of_valid_images"] = int(self.number_of_valid_images)
        if self.number_of_unsupported_files is not None:
            data["number_of_unsupported_files"] = int(self.number_of_unsupported_files)
        if self.number_of_unreadable_files is not None:
            data["number_of_unreadable_files"] = int(self.number_of_unreadable_files)
        if self.estimated_patch_count is not None:
            data["estimated_patch_count"] = int(self.estimated_patch_count)
        if self.average_concept_confidence is not None:
            data["average_concept_confidence"] = float(self.average_concept_confidence)
        if self.average_concept_consistency is not None:
            data["average_concept_consistency"] = float(self.average_concept_consistency)
        if self.memory_enabled is not None:
            data["memory_enabled"] = bool(self.memory_enabled)
        if self.memory_metric is not None:
            data["memory_metric"] = self.memory_metric
        if self.memory_items_indexed is not None:
            data["memory_items_indexed"] = int(self.memory_items_indexed)
        if self.total_patches is not None:
            data["total_patches"] = int(self.total_patches)
        if self.patch_scales_used:
            data["patch_scales_used"] = list(self.patch_scales_used)
        if self.anomaly_selection_strategy is not None:
            data["anomaly_selection_strategy"] = self.anomaly_selection_strategy
        if self.input_warnings:
            data["input_warnings"] = list(self.input_warnings)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunMetadata:
        """Build run metadata from a dictionary."""

        return cls(
            run_id=str(data["run_id"]),
            generated_at=str(data["generated_at"]),
            input_path=Path(str(data["input_path"])),
            markdown_report_path=Path(str(data["markdown_report_path"])),
            json_report_path=Path(str(data["json_report_path"])),
            run_index_path=(
                Path(str(data["run_index_path"]))
                if data.get("run_index_path") is not None
                else None
            ),
            number_of_images=int(data["number_of_images"]),
            number_of_patches=int(data["number_of_patches"]),
            number_of_candidate_anomalies=int(
                data["number_of_candidate_anomalies"]
            ),
            number_of_candidate_unknown_concepts=int(
                data["number_of_candidate_unknown_concepts"]
            ),
            pipeline_version=str(data["pipeline_version"]),
            human_review_required=bool(data["human_review_required"]),
            number_of_input_files=(
                int(data["number_of_input_files"])
                if data.get("number_of_input_files") is not None
                else None
            ),
            number_of_valid_images=(
                int(data["number_of_valid_images"])
                if data.get("number_of_valid_images") is not None
                else None
            ),
            number_of_unsupported_files=(
                int(data["number_of_unsupported_files"])
                if data.get("number_of_unsupported_files") is not None
                else None
            ),
            number_of_unreadable_files=(
                int(data["number_of_unreadable_files"])
                if data.get("number_of_unreadable_files") is not None
                else None
            ),
            estimated_patch_count=(
                int(data["estimated_patch_count"])
                if data.get("estimated_patch_count") is not None
                else None
            ),
            average_concept_confidence=(
                float(data["average_concept_confidence"])
                if data.get("average_concept_confidence") is not None
                else None
            ),
            average_concept_consistency=(
                float(data["average_concept_consistency"])
                if data.get("average_concept_consistency") is not None
                else None
            ),
            memory_enabled=(
                bool(data["memory_enabled"])
                if data.get("memory_enabled") is not None
                else None
            ),
            memory_metric=(
                str(data["memory_metric"])
                if data.get("memory_metric") is not None
                else None
            ),
            memory_items_indexed=(
                int(data["memory_items_indexed"])
                if data.get("memory_items_indexed") is not None
                else None
            ),
            total_patches=(
                int(data["total_patches"])
                if data.get("total_patches") is not None
                else None
            ),
            patch_scales_used=[
                str(item) for item in data.get("patch_scales_used", [])
            ],
            anomaly_selection_strategy=(
                str(data["anomaly_selection_strategy"])
                if data.get("anomaly_selection_strategy") is not None
                else None
            ),
            input_warnings=[str(item) for item in data.get("input_warnings", [])],
        )


@dataclass(frozen=True)
class DiscoveryRun:
    """Public run-level summary for future APIs and report artifacts."""

    run_id: str
    dataset: DatasetSummary
    findings: list[Finding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe discovery run summary."""

        return {
            "run_id": self.run_id,
            "dataset": self.dataset.to_dict(),
            "findings": [finding.to_dict() for finding in self.findings],
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class ReportArtifact:
    """Reference to a generated report or export artifact."""

    artifact_type: str
    path: Path
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe report artifact reference."""

        return {
            "artifact_type": self.artifact_type,
            "path": self.path.as_posix(),
            "metadata": _json_safe_metadata(self.metadata),
        }


@dataclass(frozen=True)
class RunIndexEntry:
    """Compact summary of one run for the run history index."""

    run_id: str
    generated_at: str
    input_path: Path
    markdown_report_path: Path
    json_report_path: Path
    run_metadata_path: Path
    number_of_images: int
    number_of_patches: int
    number_of_candidate_anomalies: int
    number_of_candidate_unknown_concepts: int
    human_review_required: bool

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-safe run index entry."""

        return {
            "run_id": self.run_id,
            "generated_at": self.generated_at,
            "input_path": self.input_path.as_posix(),
            "markdown_report_path": self.markdown_report_path.as_posix(),
            "json_report_path": self.json_report_path.as_posix(),
            "run_metadata_path": self.run_metadata_path.as_posix(),
            "number_of_images": int(self.number_of_images),
            "number_of_patches": int(self.number_of_patches),
            "number_of_candidate_anomalies": int(
                self.number_of_candidate_anomalies
            ),
            "number_of_candidate_unknown_concepts": int(
                self.number_of_candidate_unknown_concepts
            ),
            "human_review_required": bool(self.human_review_required),
        }

    @classmethod
    def from_run_metadata(
        cls,
        run_metadata: dict[str, Any],
        run_metadata_path: Path,
    ) -> RunIndexEntry:
        """Build an index entry from run metadata."""

        return cls(
            run_id=str(run_metadata["run_id"]),
            generated_at=str(run_metadata["generated_at"]),
            input_path=Path(str(run_metadata["input_path"])),
            markdown_report_path=Path(str(run_metadata["markdown_report_path"])),
            json_report_path=Path(str(run_metadata["json_report_path"])),
            run_metadata_path=run_metadata_path,
            number_of_images=int(run_metadata["number_of_images"]),
            number_of_patches=int(run_metadata["number_of_patches"]),
            number_of_candidate_anomalies=int(
                run_metadata["number_of_candidate_anomalies"]
            ),
            number_of_candidate_unknown_concepts=int(
                run_metadata["number_of_candidate_unknown_concepts"]
            ),
            human_review_required=bool(run_metadata["human_review_required"]),
        )

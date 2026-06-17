"""Markdown report generation for ADE discovery runs."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import struct
import zlib

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


@dataclass(frozen=True)
class ReportAssets:
    """Relative Markdown image paths for saved report assets."""

    anomaly_previews: dict[int, str]
    concept_previews: dict[tuple[str, int], str]


class ReportGenerator:
    """Generate Markdown reports for human review."""

    def generate(
        self,
        dataset_summary: DatasetSummary,
        candidates: list[CandidateAnomaly],
        evidence_items: list[ConceptEvidence],
        confidences: list[ConceptConfidence],
        hypotheses: list[Hypothesis],
        assets: ReportAssets | None = None,
    ) -> str:
        """Return an ADE Discovery Report in Markdown format."""

        confidence_by_id = {confidence.concept_id: confidence for confidence in confidences}
        hypothesis_by_id = {hypothesis.concept_id: hypothesis for hypothesis in hypotheses}
        assets = assets or ReportAssets(anomaly_previews={}, concept_previews={})

        lines = [
            "# ADE Discovery Report",
            "",
            "ADE Discovery Report for exploratory review. Findings below are candidate patterns and require human review.",
            "",
            "## Dataset Summary",
            "",
            f"- Input directory: `{dataset_summary.input_dir}`",
            f"- Number of input images: {dataset_summary.image_count}",
            f"- Number of extracted patches: {dataset_summary.patch_count}",
            f"- Number of candidate anomalies: {len(candidates)}",
            f"- Number of candidate unknown concepts: {len(evidence_items)}",
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
                        f"- Confidence score: {confidence.score:.4f}" if confidence else "- Confidence score: unavailable",
                        "",
                        "Evidence summary for this possible pattern:",
                    ]
                )
                for example_index, item in enumerate(evidence.examples, start=1):
                    preview = self._markdown_image(
                        alt_text=f"{evidence.concept_id} example {example_index}",
                        relative_path=assets.concept_previews.get((evidence.concept_id, example_index)),
                    )
                    lines.append(
                        f"- {preview} `{item.source_path}` at {item.coordinates}; "
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
                "All results are exploratory candidate findings. Candidate anomalies, candidate unknown concepts, possible relationships, and hypotheses require human expert review before any scientific, clinical, operational, commercial, or financial interpretation.",
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
        assets = self.save_assets(path, candidates, evidence_items)
        report = self.generate(
            dataset_summary=dataset_summary,
            candidates=candidates,
            evidence_items=evidence_items,
            confidences=confidences,
            hypotheses=hypotheses,
            assets=assets,
        )
        path.write_text(report, encoding="utf-8")
        return path

    def save_assets(
        self,
        output_path: Path | str,
        candidates: list[CandidateAnomaly],
        evidence_items: list[ConceptEvidence],
    ) -> ReportAssets:
        """Save anomaly and concept patch previews next to the report."""

        path = Path(output_path)
        assets_dir = path.parent / "assets"
        assets_dir.mkdir(parents=True, exist_ok=True)

        anomaly_previews: dict[int, str] = {}
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
                concept_previews[(evidence.concept_id, example_index)] = self._relative_markdown_path(
                    asset_path,
                    path.parent,
                )

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
                ReportGenerator._png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)),
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
    def _slugify(value: str) -> str:
        """Return a filename-safe identifier for report assets."""

        slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
        return slug or "concept"

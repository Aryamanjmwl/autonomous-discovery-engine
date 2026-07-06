from pathlib import Path

from ade.adapters.base import DataAdapter
from ade.discovery.backends import ClusteringBackend, EvidenceRanker, ScoringBackend
from ade.models import (
    ADERecord,
    DatasetSummary,
    DiscoveryRun,
    EmbeddingResult,
    EvidenceItem,
    Finding,
    ReportArtifact,
)
from ade.reporting.base import ReportRenderer
from ade.representation.base import EmbeddingBackend


class DemoAdapter:
    def load(self) -> list[ADERecord]:
        return [ADERecord(record_id="record-1", source_path=Path("data/raw/item.png"))]


class DemoEmbeddingBackend:
    def embed_patch(self, patch: ADERecord) -> EmbeddingResult:
        return EmbeddingResult(record_id=patch.record_id, vector_length=4, backend_name="demo")

    def embed_patches(self, patches: list[ADERecord]) -> list[EmbeddingResult]:
        return [self.embed_patch(patch) for patch in patches]


class DemoScorer:
    def score(
        self,
        embeddings: list[EmbeddingResult],
        max_candidates: int | None = None,
    ) -> list[Finding]:
        return [
            Finding(
                finding_id="finding-1",
                finding_type="candidate anomaly",
                score=0.5,
                summary="Candidate finding for contract tests.",
            )
        ][:max_candidates]


class DemoClusterer:
    def cluster(self, candidates: list[Finding]) -> list[list[Finding]]:
        return [candidates]


class DemoEvidenceRanker:
    def collect(self, concepts: list[list[Finding]]) -> list[list[Finding]]:
        return concepts


class DemoRenderer:
    def generate(self) -> str:
        return "report"

    def generate_json(self) -> dict[str, object]:
        return {"report": "ok"}


def test_public_protocols_are_structural() -> None:
    assert isinstance(DemoAdapter(), DataAdapter)
    assert isinstance(DemoEmbeddingBackend(), EmbeddingBackend)
    assert isinstance(DemoScorer(), ScoringBackend)
    assert isinstance(DemoClusterer(), ClusteringBackend)
    assert isinstance(DemoEvidenceRanker(), EvidenceRanker)
    assert isinstance(DemoRenderer(), ReportRenderer)


def test_public_discovery_models_serialize_without_arrays() -> None:
    evidence = EvidenceItem(
        evidence_id="evidence-1",
        source_path=Path("data/raw/image.png"),
        description="Patch preview supporting a candidate finding.",
    )
    finding = Finding(
        finding_id="finding-1",
        finding_type="candidate concept",
        score=0.75,
        summary="Evidence-backed candidate concept.",
        evidence=[evidence],
    )
    run = DiscoveryRun(
        run_id="ade_20260703_120000_abcdef",
        dataset=DatasetSummary(
            input_path=Path("data/raw/demo_images"),
            input_type="image_folder",
            record_count=6,
        ),
        findings=[finding],
    )
    artifact = ReportArtifact(
        artifact_type="markdown",
        path=Path("data/reports/demo_report.md"),
    )

    run_data = run.to_dict()
    artifact_data = artifact.to_dict()

    assert run_data["dataset"]["input_type"] == "image_folder"
    assert run_data["findings"][0]["requires_human_review"] is True
    assert run_data["findings"][0]["evidence"][0]["source_path"] == "data/raw/image.png"
    assert artifact_data["path"] == "data/reports/demo_report.md"

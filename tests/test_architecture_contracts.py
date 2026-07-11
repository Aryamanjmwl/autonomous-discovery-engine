from pathlib import Path

import numpy as np
import pytest

from ade.adapters.base import DataAdapter
from ade.adapters.image_adapter import ImageAdapter
from ade.discovery.base import ClusteringBackend, EvidenceRanker, ScoringBackend
from ade.discovery.concept_clusterer import ConceptClusterer
from ade.discovery.evidence_collector import EvidenceCollector
from ade.discovery.novelty_scorer import NoveltyScorer
from ade.models import (
    ADERecord,
    ConceptGroup,
    DatasetSummary,
    DiscoveryRun,
    EmbeddingResult,
    EvidenceItem,
    Finding,
    ReportArtifact,
)
from ade.preprocessing.patch_extractor import Patch
from ade.reporting.base import ReportRenderer
from ade.reporting.report_generator import ReportGenerator
from ade.representation.base import EmbeddingBackend
from ade.representation.embedding_engine import EmbeddingEngine


class DemoAdapter:
    name = "demo"

    def validate(self) -> None:
        return None

    def summarize(self) -> DatasetSummary:
        return DatasetSummary(input_path=Path("data/raw"), input_type="demo", record_count=1)

    def iter_records(self):
        yield from self.load()

    def load(self) -> list[ADERecord]:
        return [ADERecord(record_id="record-1", source_path=Path("data/raw/item.png"))]


class DemoEmbeddingBackend:
    name = "demo"

    def embed(self, records: list[ADERecord]) -> list[EmbeddingResult]:
        return [
            EmbeddingResult(record_id=record.record_id, vector_length=4, backend_name="demo")
            for record in records
        ]

    def embed_patch(self, patch: ADERecord) -> EmbeddingResult:
        return EmbeddingResult(record_id=patch.record_id, vector_length=4, backend_name="demo")

    def embed_patches(self, patches: list[ADERecord]) -> list[EmbeddingResult]:
        return self.embed(patches)


class DemoScorer:
    name = "demo"

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
    name = "demo"

    def cluster(
        self,
        embeddings: list[EmbeddingResult],
        scores: list[Finding] | None = None,
    ) -> list[list[Finding]]:
        del embeddings
        return [scores or []]


class DemoEvidenceRanker:
    name = "demo"

    def rank(
        self,
        records: list[ADERecord],
        scores: list[Finding],
        clusters: list[list[Finding]] | None = None,
        embeddings: list[EmbeddingResult] | None = None,
    ) -> list[list[Finding]]:
        del records, embeddings
        return clusters or [scores]


class DemoRenderer:
    name = "demo"

    def render(self, run_result: object, output_dir: Path | str) -> list[ReportArtifact]:
        del run_result
        return [ReportArtifact(artifact_type="markdown", path=Path(output_dir) / "report.md")]

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


def test_current_visual_pipeline_components_satisfy_contracts(tmp_path: Path) -> None:
    Image = pytest.importorskip("PIL.Image")
    image_path = tmp_path / "image.png"
    Image.new("RGB", (8, 8), color=(128, 64, 32)).save(image_path)

    adapter = ImageAdapter(tmp_path)
    patch = Patch(
        source_path=image_path,
        array=np.zeros((4, 4, 3), dtype=np.uint8),
        x=0,
        y=0,
        width=4,
        height=4,
    )

    assert isinstance(adapter, DataAdapter)
    assert isinstance(EmbeddingEngine(), EmbeddingBackend)
    assert isinstance(NoveltyScorer(), ScoringBackend)
    assert isinstance(ConceptClusterer(), ClusteringBackend)
    assert isinstance(EvidenceCollector(), EvidenceRanker)
    assert isinstance(ReportGenerator(), ReportRenderer)
    assert adapter.summarize().record_count == 1
    assert len(EmbeddingEngine().embed([patch])) == 1


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
    concept = ConceptGroup(
        concept_id="concept-1",
        finding_ids=["finding-1"],
        representative_finding_id="finding-1",
        score=0.75,
        summary="Related candidate finding group.",
        evidence=[evidence],
    )
    artifact = ReportArtifact(
        artifact_type="markdown",
        path=Path("data/reports/demo_report.md"),
    )
    run = DiscoveryRun(
        run_id="ade_20260703_120000_abcdef",
        dataset=DatasetSummary(
            input_path=Path("data/raw/demo_images"),
            input_type="image_folder",
            record_count=6,
        ),
        findings=[finding],
        concept_groups=[concept],
        artifacts=[artifact],
    )

    run_data = run.to_dict()
    artifact_data = artifact.to_dict()

    assert run_data["dataset"]["input_type"] == "image_folder"
    assert run_data["findings"][0]["requires_human_review"] is True
    assert run_data["findings"][0]["evidence"][0]["source_path"] == "data/raw/image.png"
    assert run_data["concept_groups"][0]["representative_finding_id"] == "finding-1"
    assert run_data["artifacts"][0]["artifact_type"] == "markdown"
    assert run_data["generated_at"]
    assert artifact_data["path"] == "data/reports/demo_report.md"

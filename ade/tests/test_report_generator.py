from pathlib import Path

import numpy as np

from ade.discovery.confidence_scorer import ConceptConfidence
from ade.discovery.evidence_collector import ConceptEvidence, EvidenceItem
from ade.discovery.novelty_scorer import CandidateAnomaly
from ade.preprocessing.patch_extractor import Patch
from ade.reasoning.hypothesis_generator import Hypothesis
from ade.reporting.report_generator import DatasetSummary, ReportGenerator
from ade.representation.embedding_engine import PatchEmbedding


def test_report_generator_includes_required_sections() -> None:
    patch = Patch(
        source_path=Path("image.png"),
        array=np.zeros((4, 4, 3), dtype=np.uint8),
        x=1,
        y=2,
        width=4,
        height=4,
    )
    candidate = CandidateAnomaly(
        embedding=PatchEmbedding(patch=patch, vector=np.zeros(8, dtype=np.float32)),
        novelty_score=0.42,
    )
    evidence = ConceptEvidence(
        concept_id="concept-001",
        examples=[EvidenceItem(source_path=Path("image.png"), coordinates=(1, 2, 4, 4), novelty_score=0.42)],
        example_count=1,
        average_novelty=0.42,
        consistency=1.0,
    )

    report = ReportGenerator().generate(
        dataset_summary=DatasetSummary(input_dir=Path("data/raw"), image_count=1, patch_count=1),
        candidates=[candidate],
        evidence_items=[evidence],
        confidences=[ConceptConfidence(concept_id="concept-001", score=0.7)],
        hypotheses=[Hypothesis(concept_id="concept-001", text="A cautious hypothesis.")],
    )

    assert "# ADE Discovery Report" in report
    assert "Number of images: 1" in report
    assert "Candidate Anomalies" in report
    assert "Candidate Unknown Concepts" in report
    assert "Human Expert Review Required" in report
    assert "A cautious hypothesis." in report

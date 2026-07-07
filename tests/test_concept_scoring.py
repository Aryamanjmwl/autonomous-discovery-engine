from pathlib import Path

import numpy as np

from ade.discovery.concept_clusterer import CandidateConcept, ConceptClusterer
from ade.discovery.concept_scorer import ConceptScorer
from ade.discovery.confidence_scorer import ConfidenceScorer
from ade.discovery.evidence_collector import EvidenceCollector
from ade.discovery.novelty_scorer import CandidateAnomaly
from ade.preprocessing.patch_extractor import Patch
from ade.representation.embedding_engine import PatchEmbedding


def _candidate(
    anomaly_id: str,
    source_path: str,
    vector: list[float],
    novelty_score: float,
    x: int = 0,
) -> CandidateAnomaly:
    patch = Patch(
        source_path=Path(source_path),
        array=np.full((4, 4, 3), 128, dtype=np.uint8),
        x=x,
        y=0,
        width=4,
        height=4,
    )
    return CandidateAnomaly(
        embedding=PatchEmbedding(
            patch=patch,
            vector=np.asarray(vector, dtype=np.float32),
        ),
        novelty_score=novelty_score,
        anomaly_id=anomaly_id,
    )


def test_concept_scorer_is_deterministic_and_bounded() -> None:
    candidates = [
        _candidate("anomaly-0001", "image-a.png", [1.0, 1.0], 0.9),
        _candidate("anomaly-0002", "image-b.png", [1.1, 1.0], 0.8),
    ]
    scorer = ConceptScorer(min_supporting_examples=2, max_supporting_examples=5)

    first = scorer.score(candidates)
    second = scorer.score(candidates)

    assert first == second
    assert 0.0 <= first.consistency_score <= 1.0
    assert 0.0 <= first.diversity_score <= 1.0
    assert set(first.confidence_breakdown) == {
        "novelty_strength",
        "support_count",
        "consistency",
        "source_diversity",
        "data_quality",
        "final_confidence",
    }
    assert first.confidence_score == first.confidence_breakdown["final_confidence"]


def test_evidence_collector_returns_json_safe_bundle() -> None:
    candidates = [
        _candidate("anomaly-0001", "image-a.png", [1.0, 1.0], 0.9),
        _candidate("anomaly-0002", "image-b.png", [1.1, 1.0], 0.8, x=4),
    ]
    concept = ConceptClusterer(distance_threshold=0.5).cluster(candidates)[0]

    evidence = EvidenceCollector(max_supporting_examples=2).collect([concept])[0]

    assert evidence.representative_anomaly_id == "anomaly-0001"
    assert evidence.source_image_count == 2
    assert evidence.diversity_score > 0.0
    assert evidence.confidence_breakdown
    assert evidence.evidence_summary is not None
    assert evidence.evidence_summary["supporting_examples"][0]["anomaly_id"] == "anomaly-0001"
    assert evidence.evidence_summary["supporting_examples"][0]["source_path"] == "image-a.png"
    assert evidence.evidence_summary["representative_examples"][0]["patch_size"] == 4
    assert "proof of truth" in evidence.evidence_summary["notes"][1]


def test_confidence_scorer_uses_breakdown_from_evidence() -> None:
    candidates = [
        _candidate("anomaly-0001", "image-a.png", [1.0, 1.0], 0.9),
        _candidate("anomaly-0002", "image-b.png", [1.1, 1.0], 0.8),
    ]
    evidence = EvidenceCollector().collect(
        [ConceptClusterer(distance_threshold=0.5).cluster(candidates)[0]]
    )

    confidence = ConfidenceScorer().score(evidence)[0]

    assert confidence.breakdown is not None
    assert confidence.score == confidence.breakdown["final_confidence"]
    assert 0.0 <= confidence.score <= 1.0


def test_empty_candidate_concept_does_not_crash() -> None:
    concept = CandidateConcept(
        concept_id="concept-empty",
        candidates=[],
        centroid=np.zeros(2, dtype=np.float32),
        consistency=0.0,
    )

    evidence = EvidenceCollector().collect([concept])[0]
    confidence = ConfidenceScorer().score([evidence])[0]

    assert evidence.example_count == 0
    assert evidence.evidence_summary is not None
    assert confidence.score == 0.0

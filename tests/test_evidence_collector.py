from pathlib import Path

import numpy as np

from ade.discovery.concept_clusterer import CandidateConcept
from ade.discovery.evidence_collector import EvidenceCollector
from ade.models import CandidateAnomaly
from ade.preprocessing.patch_extractor import Patch
from ade.representation.embedding_engine import PatchEmbedding


def _candidate(anomaly_id: str, score: float, rank: int) -> CandidateAnomaly:
    patch = Patch(
        source_path=Path(f"{anomaly_id}.png"),
        array=np.zeros((4, 4, 3), dtype=np.uint8),
        x=0,
        y=0,
        width=4,
        height=4,
        patch_id=anomaly_id,
    )
    return CandidateAnomaly(
        embedding=PatchEmbedding(patch=patch, vector=np.array([score], dtype=np.float32)),
        novelty_score=score,
        anomaly_id=anomaly_id,
        metadata={
            "rank": rank,
            "nearest_neighbor_patch_id": "nearby-patch",
            "feature_deviations": [{"feature": "brightness_mean", "z_deviation": 1.5}],
            "reason": "Higher brightness than most patches in this dataset.",
        },
    )


def test_evidence_collector_orders_examples_and_preserves_context() -> None:
    lower = _candidate("anomaly-0002", 0.3, 2)
    higher = _candidate("anomaly-0001", 0.9, 1)
    concept = CandidateConcept(
        concept_id="concept-001",
        candidates=[lower, higher],
        centroid=np.zeros(1, dtype=np.float32),
        consistency=0.8,
        representative_anomaly_id="anomaly-0001",
        average_novelty=0.6,
        summary="Two candidate anomalies with similar normalized visual feature profiles.",
    )

    evidence = EvidenceCollector().collect([concept])[0]

    assert evidence.representative_anomaly_id == "anomaly-0001"
    assert evidence.summary.startswith("Two candidate anomalies")
    assert [item.anomaly_id for item in evidence.examples] == ["anomaly-0001", "anomaly-0002"]
    assert evidence.examples[0].rank == 1
    assert evidence.examples[0].nearest_neighbor_patch_id == "nearby-patch"
    assert evidence.examples[0].feature_deviations == [
        {"feature": "brightness_mean", "z_deviation": 1.5}
    ]
    assert evidence.examples[0].reason.startswith("Higher brightness")

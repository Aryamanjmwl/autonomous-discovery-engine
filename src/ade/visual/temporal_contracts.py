"""Typed contracts for explicit temporal visual change analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

TemporalChangeStrategy = Literal["adjacent_difference", "baseline_difference"]


@dataclass(frozen=True)
class TemporalObservation:
    observation_id: str
    source_path: str
    timestamp: str | None = None
    sequence_index: int | None = None
    entity_id: str | None = None
    scene_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)
    width: int | None = None
    height: int | None = None
    image_sha256: str | None = None
    mask_path: str | None = None


@dataclass(frozen=True)
class TemporalObservationSequence:
    schema_version: int
    dataset_name: str
    dataset_version: str
    dataset_root: str
    sequence_id: str
    observations: tuple[TemporalObservation, ...]
    scene_id: str | None = None
    entity_id: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class TemporalAlignmentSummary:
    method: str
    dimensions_consistent: bool
    comparable_patch_grid: bool
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TemporalChangeScore:
    source_observation_id: str
    target_observation_id: str
    strategy: TemporalChangeStrategy
    global_feature_distance: float


@dataclass(frozen=True)
class TemporalPatchEvidence:
    source_observation_id: str
    target_observation_id: str
    x: int
    y: int
    width: int
    height: int
    patch_scale: str
    change_score: float
    evidence_note: str = "Local feature difference; requires human review."


@dataclass(frozen=True)
class TemporalChangeEvent:
    event_id: str
    rank: int
    score: TemporalChangeScore
    candidate_label: str = "candidate temporal change"
    possible_interpretation: str = "possible movement/growth/damage/change"
    requires_human_review: bool = True
    patch_evidence: tuple[TemporalPatchEvidence, ...] = ()


@dataclass(frozen=True)
class TemporalChangeSummary:
    observation_count: int
    range_start: str
    range_end: str
    max_change_score: float
    mean_adjacent_change_score: float
    strongest_observation_pair: tuple[str, str]
    top_candidate_change_event_ids: tuple[str, ...]
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class TemporalChangeProvenance:
    sequence_id: str
    manifest_fingerprint: str
    strategy: TemporalChangeStrategy
    feature_backend: str
    feature_backend_version: str
    patch_size: int | None
    deterministic: bool = True
    local_offline: bool = True
    human_review_required: bool = True
    limitations: tuple[str, ...] = ()


@dataclass(frozen=True)
class TemporalChangeResult:
    schema_version: int
    sequence: TemporalObservationSequence
    alignment: TemporalAlignmentSummary
    scores: tuple[TemporalChangeScore, ...]
    events: tuple[TemporalChangeEvent, ...]
    summary: TemporalChangeSummary
    provenance: TemporalChangeProvenance

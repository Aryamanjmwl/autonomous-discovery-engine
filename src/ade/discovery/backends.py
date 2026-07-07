"""Backward-compatible imports for discovery backend protocols."""

from __future__ import annotations

from ade.discovery.base import ClusteringBackend, EvidenceRanker, ScoringBackend

__all__ = ["ClusteringBackend", "EvidenceRanker", "ScoringBackend"]

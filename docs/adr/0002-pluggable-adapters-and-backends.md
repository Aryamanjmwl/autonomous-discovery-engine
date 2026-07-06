# ADR 0002: Pluggable Adapters and Backends

## Status

Accepted

## Context

ADE is a general autonomous discovery platform. The current implementation is visual-data-first, but future work may add tabular, time-series, logs, video, audio, and multimodal adapters.

## Decision

Define small protocol-style interfaces for adapters and backends:

- `DataAdapter`
- `EmbeddingBackend`
- `ScoringBackend`
- `ClusteringBackend`
- `EvidenceRanker`
- `ReportRenderer`

## Consequences

This keeps extension points explicit without introducing a plugin framework too early. Advanced backends can remain optional and outside the default dependency set.

# ADE Architecture

ADE is a general autonomous discovery platform. The current implementation is visual-data-first; it supports image-folder profiling, patch extraction, statistical embeddings, novelty scoring, candidate concept grouping, and Markdown/JSON reports.

The long-term architecture is layered so discovery logic does not depend on a single dataset type or a single model backend.

## Product Principle

Discovery with evidence, not only anomaly scores.

ADE should produce candidate findings with traceable evidence and reviewable outputs. Scores help rank findings, but evidence makes findings useful.

## Layers

1. Data Adapter Layer
2. Representation / Embedding Layer
3. Discovery Layer
4. Evidence and Explanation Layer
5. Report and Output Layer
6. API and Product Layer
7. Enterprise Operations Layer

## Core Interfaces

- `DataAdapter`: loads traceable source records.
- `EmbeddingBackend`: converts records or patches into comparable representations.
- `ScoringBackend`: ranks candidate anomalies or candidate patterns.
- `ClusteringBackend`: groups related candidates into candidate concepts.
- `EvidenceRanker`: collects and ranks evidence for candidate concepts.
- `ReportRenderer`: exports human-readable and machine-readable reports.

## Core Models

- `ADERecord`
- `DatasetSummary`
- `EmbeddingResult`
- `DiscoveryRun`
- `Finding`
- `EvidenceItem`
- `ReportArtifact`

## Current Visual Pipeline

1. Profile image-folder input.
2. Load valid image metadata.
3. Extract fixed-size image patches.
4. Compute deterministic lightweight visual embeddings.
5. Score candidate anomalies with normalized global and nearest-neighbor distance signals.
6. Group candidate visual concepts with dependency-light normalized vector clustering.
7. Collect evidence, feature deviations, nearest-neighbor context, and confidence summaries.
8. Generate cautious hypotheses.
9. Export Markdown, JSON, preview assets, run metadata, and run index entries.

## Current Visual Feature Strategy

The current visual representation backend is intentionally lightweight and deterministic. It combines patch size and aspect ratio, brightness and contrast statistics, RGB channel summaries, normalized color and brightness histograms, simple texture estimates, and gradient-based edge features.

This is not a replacement for CLIP, DINOv2, domain-specific encoders, or validated scientific models. It gives the current image adapter a more useful baseline while keeping the default install small and making future embedding backends easier to compare against.

## Current Boundaries

The current implementation does not include non-visual adapters, deep learning backends, a service API, a dashboard, or enterprise storage. Those are planned extension points, not current capabilities.

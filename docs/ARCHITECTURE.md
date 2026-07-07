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

- `DataAdapter`: validates an input source, summarizes it, and yields traceable records.
- `EmbeddingBackend`: converts records or patches into comparable representations.
- `ScoringBackend`: ranks embeddings as candidate anomalies or candidate patterns.
- `ClusteringBackend`: groups related candidates into candidate concepts.
- `EvidenceRanker`: selects or summarizes evidence for reviewable findings.
- `ReportRenderer`: exports human-readable and machine-readable report artifacts.

The interfaces are implemented as small structural protocols. They are intended
to protect module boundaries without requiring a large plugin framework.

## Core Models

- `ADERecord`
- `DatasetSummary`
- `EmbeddingResult`
- `DiscoveryRun`
- `Finding`
- `EvidenceItem`
- `ConceptGroup`
- `ReportArtifact`

## Current Visual Pipeline

1. Profile image-folder input.
2. Load valid image metadata.
3. Extract fixed-size image patches.
4. Compute deterministic statistical embeddings.
5. Score candidate anomalies.
6. Group candidate visual concepts.
7. Collect evidence and confidence summaries.
8. Generate cautious hypotheses.
9. Export Markdown, JSON, preview assets, run metadata, and run index entries.

## Extension Points

Future adapters should implement `DataAdapter` and keep data loading separate
from discovery logic. A tabular adapter, for example, should validate and yield
records; it should not run anomaly scoring itself.

Future embedding backends should implement `EmbeddingBackend` behind the same
boundary used by the current deterministic visual backend. CLIP, DINOv2, custom
satellite encoders, or medical research encoders can be added later as optional
backends without making them default dependencies.

Scoring, clustering, evidence ranking, and report rendering are separate
contracts so candidate ranking can evolve independently from evidence
presentation. ADE should continue to produce candidate findings with traceable
evidence rather than only returning anomaly scores.

## Backend Selection

The current discovery registry supports lightweight scoring backends selected
by `discovery.scoring_backend`: centroid distance, nearest-neighbor distance,
and robust z-score distance. The default remains centroid distance for backward
compatibility.

The current clustering backend is a threshold-based concept grouper selected by
`discovery.clustering_backend`. Backend names are validated when configuration
is loaded, so unsupported names fail before the pipeline starts processing data.

## Current Boundaries

The current implementation does not include non-visual adapters, deep learning backends, a service API, a dashboard, or enterprise storage. Those are planned extension points, not current capabilities.

Heavy model dependencies are intentionally delayed until the lightweight
pipeline, report schema, and backend contracts are stable.

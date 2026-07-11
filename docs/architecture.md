# ADE Architecture

ADE is a general autonomous discovery platform. The current implementation
supports a visual-data-first image pipeline and a lightweight CSV/tabular
foundation plus explicit CSV time-series support. Image folders remain the most
complete adapter; CSV support adds row-level profiling, deterministic tabular
or time-series features, novelty ranking, concept grouping, and Markdown/JSON
reports.

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

## Current Tabular Pipeline

1. Validate a local `.csv` file.
2. Profile rows, columns, numeric fields, categorical fields, and missing values.
3. Yield stable row-level records.
4. Compute deterministic row-level features from numeric scaling, missing-value
   indicators, categorical rarity, and completeness.
5. Score candidate row anomalies by distance from the tabular feature center.
6. Group candidate rows into simple reason-based candidate concepts.
7. Export Markdown, JSON, run metadata, and run index entries.

The tabular path is intentionally row-level only. It does not apply
time-series semantics, supervised learning, relational joins, or database
ingestion.

## Current Time-Series Pipeline

1. Validate a local `.csv` file in explicit time-series mode.
2. Detect or use a configured timestamp column.
3. Profile rows, time range, numeric signal columns, missing timestamps,
   malformed timestamps, duplicate timestamps, and sampling intervals.
4. Yield stable timestamped records.
5. Compute deterministic point/window-style features from normalized signal
   values, missing indicators, deltas, rolling summaries, spike indicators,
   time-gap indicators, and completeness.
6. Score candidate unusual points by distance from the time-series feature
   center.
7. Group candidate points into simple reason-based candidate concepts.
8. Export Markdown, JSON, run metadata, and run index entries.

The time-series path is intentionally lightweight. It does not include
forecasting, streaming ingestion, production alerting, supervised learning, or
database ingestion.

## Extension Points

Future adapters should implement `DataAdapter` and keep data loading separate
from discovery logic. The current image, tabular CSV, and time-series CSV
adapters follow that boundary: they validate inputs and yield records without
running anomaly scoring inside the adapter.

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

The current implementation includes image-folder inputs, plain CSV tabular
inputs, and explicit timestamped CSV time-series inputs. It does not include
video, audio, document, log, database, live-stream, forecasting, or production
monitoring adapters. Deep learning backends and enterprise storage are planned
extension points, not current capabilities.

Heavy model dependencies are intentionally delayed until the lightweight
pipeline, report schema, and backend contracts are stable.

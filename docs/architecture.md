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
4. Compute deterministic statistical embeddings.
5. Score candidate anomalies.
6. Group candidate visual concepts.
7. Score concept consistency, source diversity, and confidence components.
8. Collect structured evidence bundles with anomaly IDs, patch coordinates, ranks, and preview paths.
9. Generate cautious hypotheses.
10. Export Markdown, JSON, preview assets, run metadata, and run index entries.

## Current Concept and Evidence Layer

The visual MVP keeps concept scoring deterministic and dependency-light. Candidate anomalies are grouped by embedding distance, then each candidate concept receives bounded review signals:

- consistency: how tightly supporting embeddings sit around the concept center
- source diversity: how many source images are represented
- support count: whether there are enough supporting patches to justify review
- novelty strength: average candidate anomaly strength within the group
- data quality: whether patch metadata is usable

These signals are combined into a confidence score for review prioritization. The score is not a claim that a pattern is real or important. Reports include the component breakdown so reviewers can see why a candidate concept was highlighted.

Evidence bundles currently include supporting examples, representative examples, empty placeholders for near matches and normal comparisons, notes, and warnings. Near-match and normal-comparison selection should be added only after the baseline/reference strategy is designed.

## Current Boundaries

The current implementation does not include non-visual adapters, deep learning backends, a service API, a dashboard, or enterprise storage. Those are planned extension points, not current capabilities.

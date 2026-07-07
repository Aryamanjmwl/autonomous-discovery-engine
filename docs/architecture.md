# ADE Architecture

ADE is a general autonomous discovery platform. The current implementation is visual-data-first; it supports image-folder profiling, single-scale or configured multi-scale patch extraction, statistical embeddings, local visual memory, strategy-based novelty scoring, diversity-aware candidate anomaly selection, candidate concept grouping, and Markdown/JSON reports.

The long-term architecture is layered so discovery logic does not depend on a single dataset type or a single model backend.

## Product Principle

Discovery with evidence, not only anomaly scores.

ADE should produce candidate findings with traceable evidence and reviewable outputs. Scores help rank findings, but evidence makes findings useful.

## Layers

1. Data Adapter Layer
2. Representation / Embedding Layer
3. Discovery Layer
4. Memory and Retrieval Layer
5. Evidence and Explanation Layer
6. Report and Output Layer
7. API and Product Layer
8. Enterprise Operations Layer

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
3. Extract fixed-size image patches across one or more configured scales.
4. Compute deterministic statistical embeddings.
5. Build an optional local vector memory for patch retrieval.
6. Score candidate anomalies with global, memory-neighbor, or hybrid scoring.
7. Select a diverse candidate anomaly set across source images, spatial regions, and patch scales.
8. Group candidate visual concepts.
9. Score concept consistency, source diversity, and confidence components.
10. Collect structured evidence bundles with anomaly IDs, patch coordinates, ranks, preview paths, scale metadata, and nearest visual matches.
11. Generate cautious hypotheses.
12. Export Markdown, JSON, preview assets, run metadata, and run index entries.

## Current Patch Extraction and Selection

The default visual pipeline uses one conservative patch scale. Configured multi-scale extraction is available through matching `patch_sizes` and `patch_strides` lists. Patch IDs include source image, scale, stride, and coordinates so records remain deterministic across runs.

After novelty scoring, the diversity selector can limit repeated candidates from the same image or nearby region and can prefer multiple scales when more than one scale is configured. This is a simple review-quality improvement, not a claim that selected anomalies are more important or true.

## Current Memory Layer

`VectorMemory` is a small NumPy-backed in-process index for embedding retrieval. It supports Euclidean and cosine nearest-neighbor queries, deterministic top-k ordering, metadata storage, and exclusion filters for known item IDs or source paths.

The current pipeline indexes patch embeddings during a run and uses the memory layer to add near-match evidence to candidate concept bundles. This supports review and debugging today while keeping the path open for future normal memory banks, PatchCore-style nearest-neighbor anomaly scoring, coreset selection, FAISS, or a vector database backend.

The current memory is not persistent and does not replace the run metadata, JSON report, or future storage layers.

## Current Novelty Scoring

`NoveltyScorer` supports three deterministic strategies:

- `global_distance`: distance from the dataset average embedding
- `memory_neighbor_distance`: nearest-neighbor distance from local vector memory
- `hybrid`: weighted normalized combination of global and neighbor-distance scores

The scorer records a per-candidate score breakdown and concise run metadata,
including whether memory-aware scoring fell back to global distance. The fallback
path is intentional: if no memory or no neighbors are available, ADE still
produces candidate findings rather than failing a run.

These scores prioritize review. They are not proof that a candidate anomaly is
scientifically, operationally, or commercially significant.

## Current Concept and Evidence Layer

The visual MVP keeps concept scoring deterministic and dependency-light. Candidate anomalies are grouped by embedding distance, then each candidate concept receives bounded review signals:

- consistency: how tightly supporting embeddings sit around the concept center
- source diversity: how many source images are represented
- support count: whether there are enough supporting patches to justify review
- novelty strength: average candidate anomaly strength within the group
- data quality: whether patch metadata is usable

These signals are combined into a confidence score for review prioritization. The score is not a claim that a pattern is real or important. Reports include the component breakdown so reviewers can see why a candidate concept was highlighted.

Evidence bundles currently include supporting examples, representative examples, nearest-neighbor matches when memory is enabled, empty placeholders for normal comparisons, notes, and warnings. Normal-comparison selection should be added only after the baseline/reference strategy is designed.

## Current Boundaries

The current implementation does not include non-visual adapters, deep learning backends, a service API, a dashboard, or enterprise storage. Those are planned extension points, not current capabilities.

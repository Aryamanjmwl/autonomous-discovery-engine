# Adapter and Backend Guide

ADE separates dataset access from representation, discovery, evidence, and reporting.

## DataAdapter

A data adapter loads source records and metadata. It should not run discovery logic.

Required behavior:

- `validate()` checks whether the input can be read.
- `summarize()` returns a lightweight dataset summary.
- `iter_records()` yields records in deterministic order.
- `load()` may be kept as a convenience wrapper for existing code.

Current adapter:

- Image folder adapter

Future adapters:

- Tabular
- Time-series
- Logs
- Video
- Audio/spectrogram
- Multimodal

## EmbeddingBackend

An embedding backend converts records or patches into comparable representations. The default visual implementation uses deterministic statistical features.

Future backends should be optional and should not add heavy dependencies to the default install.

Required behavior:

- `name` identifies the backend in logs or reports.
- `embed(records)` returns embedding records for the provided analysis units.
- Compatibility helpers such as `embed_patch()` can remain on visual backends.

Deep-learning backends such as CLIP, DINOv2, or custom domain encoders should
plug in here later. They are intentionally not default dependencies while the
baseline pipeline and evidence reporting are still being stabilized.

## ScoringBackend

A scoring backend ranks candidate anomalies or candidate patterns. Scores should be treated as ranking signals, not final conclusions.

Scoring backends should be deterministic where practical and should avoid
returning NaN or infinite scores.

## ClusteringBackend

A clustering backend groups related candidates into candidate concepts.

The current implementation uses a simple threshold-based method. More advanced
clustering can be added later behind the same contract if it is justified by
tests and data.

## EvidenceRanker

An evidence ranker selects examples that make a finding reviewable.

Evidence should include enough context for review: source records, coordinates
when available, scores, cluster membership, and conservative reason text.

## ReportRenderer

A report renderer exports review artifacts. Markdown and JSON exist today; HTML is a planned format.

Report renderers should return artifact references and preserve human-review
language. They should not convert candidate findings into unsupported claims.

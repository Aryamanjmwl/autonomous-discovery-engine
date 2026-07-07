# Adapter and Backend Guide

ADE separates dataset access from representation, discovery, evidence, and reporting.

## DataAdapter

A data adapter loads source records and metadata. It should not run discovery logic.

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

An embedding backend converts records or patches into comparable representations. The default visual implementation uses deterministic lightweight statistics: patch geometry, brightness and contrast summaries, color channel statistics, histograms, simple texture estimates, and gradient features.

Future backends should be optional and should not add heavy dependencies to the default install.

Deep-learning backends such as CLIP, DINOv2, or custom domain encoders are intentionally delayed until the baseline pipeline, evidence reporting, and backend contracts are stable. A future backend should emit traceable metadata, preserve deterministic evaluation where practical, and remain replaceable behind the representation interface.

## ScoringBackend

A scoring backend ranks candidate anomalies or candidate patterns. Scores should be treated as ranking signals, not final conclusions.

## ClusteringBackend

A clustering backend groups related candidates into candidate concepts.

## EvidenceRanker

An evidence ranker selects examples that make a finding reviewable.

Current evidence records include rank, anomaly score, source path, coordinates, nearest-neighbor context, feature deviations, preview asset paths when available, and conservative reason text.

## ReportRenderer

A report renderer exports review artifacts. Markdown and JSON exist today; HTML is a planned format.

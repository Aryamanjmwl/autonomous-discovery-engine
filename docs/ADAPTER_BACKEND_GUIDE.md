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

An embedding backend converts records or patches into comparable representations. The default visual implementation uses deterministic statistical features.

Future backends should be optional and should not add heavy dependencies to the default install.

## ScoringBackend

A scoring backend ranks candidate anomalies or candidate patterns. Scores should be treated as ranking signals, not final conclusions.

## ClusteringBackend

A clustering backend groups related candidates into candidate concepts.

## EvidenceRanker

An evidence ranker selects examples that make a finding reviewable.

## ReportRenderer

A report renderer exports review artifacts. Markdown and JSON exist today; HTML is a planned format.

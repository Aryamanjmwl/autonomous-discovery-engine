# ADE Architecture

ADE is a general autonomous discovery platform. The current implementation focuses on visual data. Computer vision is the first supported adapter, not the final scope of the product.

ADE is organized as a modular discovery pipeline. Each stage has a narrow responsibility and uses simple data structures so future research components can be introduced without rewriting the whole system.

## Pipeline

1. Adapters load raw data and produce source records with metadata.
2. Preprocessing converts source records into patches or other analysis units.
3. Representation produces embeddings or other comparable feature records.
4. Discovery ranks candidate anomalies and groups candidate unknown concepts.
5. Evidence collection summarizes supporting examples.
6. Reasoning drafts cautious hypotheses from structured evidence.
7. Reporting creates human-readable and machine-readable review artifacts.

## Current Visual Adapter Pipeline

The current computer vision adapter supports image folders. It profiles the input folder, loads image metadata, extracts fixed-size patches, computes deterministic statistical embeddings, ranks candidate anomalies, groups candidate visual concepts, collects evidence, scores confidence, generates cautious hypotheses, and writes Markdown and JSON reports.

This visual pipeline is intentionally simple. It is a first adapter and a baseline for future stronger visual discovery work.

## Input Validation and Dataset Profiling

Before analysis, ADE inspects the image folder and creates a dataset profile. The profile records total files, supported image files, unsupported files, unreadable files, valid image counts, image size ranges, unique image sizes, estimated patch count, warnings, and validity.

Invalid inputs fail before analysis. Valid inputs with warnings continue, and those warnings are included in the reports and run metadata.

## Future Adapter Interface Concept

Future adapters should follow the same pattern:

- Load a dataset type and emit traceable source records.
- Convert source records into analysis units.
- Produce comparable representations through a replaceable backend.
- Preserve enough metadata to trace every candidate finding back to source data.
- Feed discovery, evidence, reasoning, reporting, and run tracking without changing the overall platform flow.

Future adapters may cover videos, tabular data, time-series data, logs, audio, documents, multimodal datasets, and live streams.

## Reporting and Run Tracking

Each run writes a Markdown report, structured JSON report, dataset profile, patch preview assets when enabled, one run metadata JSON file, and an updated run history index.

Run tracking records the run ID, timestamp, input path, report paths, result counts, pipeline version, and human-review requirement. This supports future dashboards, APIs, audits, subscription workspaces, and experiment comparison.

## Extension Points

- `adapters`: image folders today; future video, tabular, time-series, log, audio, document, multimodal, and live-stream sources.
- `representation`: future encoders such as DINOv2, CLIP, domain-specific satellite encoders, or medical image encoders.
- `discovery`: alternative novelty scoring, clustering, uncertainty estimation, and evidence ranking.
- `reasoning`: stricter hypothesis templates, literature-aware context, or human-in-the-loop review.

## Design Principles

- Prefer explicit dataclasses and type hints.
- Keep advanced models behind replaceable interfaces.
- Avoid overstating results.
- Preserve traceability from report findings back to source image paths and patch coordinates.

## Internal Data Models

ADE uses typed dataclasses in `src/ade/models.py` for image records, patches,
embeddings, candidate anomalies, candidate unknown concepts, evidence summaries,
and run metadata. These models keep internal objects explicit while ensuring
JSON reports and run metadata serialize paths, counts, scores, and references
without dumping raw NumPy arrays.

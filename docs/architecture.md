# ADE Architecture

ADE is organized as a modular discovery pipeline. Each stage has a narrow responsibility and uses simple data structures so future research components can be introduced without rewriting the whole system.

## Pipeline

1. Adapters load raw data and produce source records with metadata.
2. Preprocessing converts source records into patches or other analysis units.
3. Representation produces embeddings from patches.
4. Discovery ranks candidate anomalies and groups candidate unknown concepts.
5. Evidence collection summarizes supporting examples.
6. Reasoning drafts cautious hypotheses from structured evidence.
7. Reporting creates human-readable review artifacts.

## Extension Points

- `adapters`: satellite imagery, planetary imagery, video, medical imaging, streams, and time-series sources.
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

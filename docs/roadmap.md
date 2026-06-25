# Roadmap

ADE is being developed as a general autonomous discovery platform with a visual-data-first implementation.

## Phase 0: Current Foundation

- Maintain the current image folder adapter.
- Preserve synthetic demo data generation.
- Keep patch extraction, statistical embeddings, novelty scoring, concept grouping, evidence summaries, confidence scores, cautious hypotheses, Markdown reports, JSON reports, run metadata, run history index, config loading, and CLI run listing stable.
- Continue using careful language: candidate anomaly, candidate pattern, candidate concept, possible relationship, and requires human review.

## Phase 1: Repo Cleanup and Internal Models

- Harden typed internal models and serialization boundaries.
- Improve test coverage around CLI behavior, config overrides, report outputs, and run history.
- Keep generated artifacts out of version control.
- Expand documentation for private research workflow and product boundaries.

## Phase 2: Stronger Visual Discovery Engine

- Improve visual feature extraction while preserving the replaceable representation interface.
- Add better concept grouping, evidence ranking, and uncertainty summaries.
- Add review annotations for confirming, rejecting, or refining candidate findings.

## Phase 3: Video Adapter

- Add video metadata loading and frame sampling.
- Introduce temporal patch or clip extraction.
- Keep video outputs framed as candidate visual patterns requiring review.

## Phase 4: Deep Visual Embedding Backend

- Add optional deep visual embedding backends behind the existing representation interface.
- Evaluate domain-specific encoders without making unvalidated discovery claims.
- Preserve deterministic baselines for comparison.

## Phase 5: Dashboard

- Build a local review dashboard for runs, candidate anomalies, candidate concepts, previews, JSON metadata, and human notes.
- Keep dashboard work separate from the core pipeline.

## Phase 6: Non-Visual Dataset Adapters

- Add future adapters for tabular data, time-series data, logs, audio, documents, multimodal datasets, and other structured sources.
- Define adapter contracts that can produce analysis units, metadata, embeddings, and evidence links.

## Phase 7: Subscription/Cloud Platform

- Add secure upload, workspace isolation, authentication, billing, team workflows, audit logs, and hosted run history.
- Keep customer-facing claims careful and evidence-backed.

# Implementation Plan

This plan turns ADE from a visual-first prototype into a public-ready discovery engine foundation without adding premature SaaS complexity.

## Near-Term Work

1. Keep the CLI stable and well tested.
2. Keep reports reproducible and evidence-backed.
3. Stabilize public interfaces for adapters, embeddings, scoring, clustering, evidence, and reporting.
4. Improve visual feature quality with classical, lightweight methods before optional deep backends.
5. Keep generated artifacts out of source control.

## Engineering Priorities

- Correctness before feature breadth.
- Small interfaces before plugin systems.
- Deterministic demos before benchmarks.
- Evidence-backed reports before dashboards.
- Optional advanced backends before heavy default installs.

## Current Implementation Baseline

- YAML configuration
- Synthetic demo images
- Image-folder validation and profiling
- Image folder adapter
- Patch extraction
- Statistical embedding backend
- Novelty scoring
- Candidate concept grouping
- Evidence and confidence scoring
- Markdown and JSON reports
- Run metadata and run index
- CLI run listing

## Next Practical Milestones

- Add HTML report rendering.
- Add richer visual feature extraction.
- Add near-duplicate detection.
- Add explicit backend selection in config.
- Add an adapter contract document with examples.
- Add CI for tests and linting.

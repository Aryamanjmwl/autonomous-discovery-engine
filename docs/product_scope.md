# Product Scope

ADE is a general autonomous discovery platform. The long-term vision is to help users investigate hidden patterns, candidate anomalies, recurring behaviors, possible relationships, and predictive signals across many kinds of data.

The current implementation focuses on visual data. Computer vision is the first supported adapter, not the final scope of the product.

## Long-Term Vision

ADE is intended to become a secure discovery platform where users can upload datasets, run configurable discovery pipelines, review candidate findings, and receive evidence-backed reports. The platform should support human-in-the-loop review, run comparison, auditability, and eventually subscription-based workspaces.

Future adapter families may include:

- Images
- Videos
- Tabular data
- Time-series data
- Logs
- Audio
- Documents
- Multimodal datasets
- Live streams

## Current Implementation Scope

The current implementation supports a visual-data-first pipeline:

- Synthetic demo image generation
- Image-folder validation and dataset profiling
- Image folder loading
- Fixed-size patch extraction
- Deterministic statistical embeddings
- Novelty scoring
- Candidate anomaly selection
- Candidate concept grouping
- Evidence and confidence summaries
- Cautious hypothesis generation
- Markdown and JSON reports
- Run metadata and run history index
- CLI run listing
- Configuration via `configs/default.yaml`

## Not Supported Yet

ADE does not yet implement video processing, non-visual adapters, deep visual embedding models, hosted uploads, dashboards, user accounts, billing, live streams, or production security controls.

ADE does not guarantee discoveries, replace experts, or make scientific, medical, legal, operational, or financial conclusions. All outputs are candidate findings that require human review.

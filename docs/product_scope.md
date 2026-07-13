# Product Scope

ADE is an adapter-based autonomous discovery platform. The long-term vision is
to help users investigate hidden patterns, candidate anomalies, recurring
behaviors, possible relationships, and predictive signals across many kinds of
data.

The current private-alpha implementation includes a mature visual/image-folder
workflow plus lightweight CSV tabular and CSV time-series adapter foundations
where implemented. Other modalities are planned adapter targets unless the
repository contains working code, tests, and report contracts for them.

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

The current implementation supports an adapter-based local pipeline:

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
- Markdown, JSON, and static HTML reports
- Run metadata and run history index
- CLI run listing
- Local human-review feedback records
- Tabular CSV adapter foundation for row-level candidate findings
- Time-series CSV adapter foundation for explicit timestamped CSV workflows
- Video adapter placeholder without decoded frame processing
- Configuration via `configs/default.yaml`

## Not Supported Yet

ADE does not yet implement production video processing, sensor streams, live
satellite feeds, audio input, log/event adapters, scientific instrument
adapters, deep visual embedding models, hosted uploads, production dashboards,
user accounts, billing, live streams, or production security controls.

ADE does not guarantee discoveries, replace experts, or make scientific, medical, legal, operational, or financial conclusions. All outputs are candidate findings that require human review.

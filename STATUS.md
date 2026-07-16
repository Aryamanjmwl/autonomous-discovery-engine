# ADE Status

**Last verified:** 2026-07-16
**Verified revision:** `be84dedf23fdaf6658a6beb5fb32d0ca21a185f2`
**Stage:** Local Technical Preview progressing toward Local Beta

ADE is an adapter-based, local-first autonomous discovery platform. It surfaces
candidate anomalies, candidate concepts, and possible patterns with evidence for
human review. It does not produce automated truth or validated domain conclusions.

## Current State

| Area | State | Evidence |
| --- | --- | --- |
| Visual discovery | Implemented Technical Preview workflow | Validation, profiling, patch extraction, deterministic representations, novelty scoring, grouping, evidence, reports, tests |
| Tabular CSV | Lightweight local foundation | Row-level features, discovery, reports, demo workflow |
| Time-series CSV | Lightweight local foundation | Timestamp profiling, point/window features, discovery, reports, demo workflow |
| ADE Studio | Connected local visual workflow | Next.js frontend, localhost FastAPI service, run/report browsing, analysis, preview assets |
| Human review | Partial end-to-end workflow | CLI JSONL feedback and review-memory exist; Studio write/history workflow is incomplete |
| Evaluation | Foundation | Benchmark and verification scripts exist; governed datasets and comparative scorecards are incomplete |
| Security | Local-first foundation | Loopback service and asset traversal tests exist; approved dataset roots and broader negative testing remain |
| Advanced ML | Not implemented | No PyTorch/TensorFlow dependency, deep encoder, LSTM, or xLSTM backend |
| Hosted enterprise platform | Not implemented | No accounts, RBAC, database, object storage, queue, billing, SSO, or multi-tenancy |

## Completed Capabilities

- Typed configuration and adapter/backend extension contracts.
- Image-folder, tabular CSV, and time-series CSV local workflows.
- Multi-scale visual patches and deterministic statistical representations.
- Multiple deterministic novelty strategies and diversity-aware selection.
- Evidence bundles, confidence breakdowns, nearest-neighbor support, and cautious
  hypothesis templates.
- Markdown, JSON, and HTML reports; validation; run history; benchmark and local
  verification scripts.
- Local JSONL review records and deterministic review-memory summaries.
- ADE Studio frontend connected to a local Python API for visual analysis and
  local report artifacts.
- CI, release-readiness documentation, demo workflows, and claim-integrity tests.

## Material Gaps

- No canonical reproducibility manifest or governed dataset registry.
- No complete Studio feedback create/list/history path.
- No run comparison workflow or controlled model-comparison scorecard.
- Studio does not yet execute tabular or time-series workflows.
- Artifact storage and memory remain local filesystem/in-process implementations.
- No production video, logs, audio, document, sensor, satellite, or streaming
  adapters.
- No production authentication, authorization, tenancy, audit, retention, or
  infrastructure controls.

## Next Step

The next release slice is **Local Beta provenance and reviewer-loop hardening**:

1. Add a canonical run manifest and dataset fingerprint (`ADE-031`).
2. Version report and local API contracts (`ADE-032`).
3. Implement feedback list/create APIs and the complete Studio workflow
   (`ADE-034`, `ADE-035`).
4. Add governed benchmark datasets and comparative scorecards (`ADE-041`,
   `ADE-042`).
5. Enforce approved dataset roots and resource limits (`ADE-047`, `ADE-048`).

Advanced sequence models, including xLSTM, remain a research ticket after the
time-series benchmark and sequence-backend contract exist. The default install
remains lightweight and deterministic.

See [`docs/project/`](docs/project/README.md) for the controlled product,
architecture, security, frontend, and ticket baseline.

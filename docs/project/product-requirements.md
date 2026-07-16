# Product Requirements Document

**Product:** Autonomous Discovery Engine (ADE)
**Version:** 1.0
**Status:** Approved planning baseline
**Owner:** ADE Research and Engineering
**Last revised:** 2026-07-16

## 1. Product Definition

ADE is a local-first, adapter-based discovery system that helps researchers and
technical reviewers surface candidate anomalies, recurring structures, and
candidate concepts in datasets they may not yet know how to query. ADE produces
evidence-backed review artifacts; it does not assert scientific truth or replace
domain experts.

The current Technical Preview is strongest for image folders. Lightweight CSV
tabular and timestamped CSV workflows exist as foundations. ADE Studio provides
a connected local review interface for visual analysis through a localhost API.

## 2. Problem Statement

Exploratory data review is commonly fragmented across notebooks, one-off scripts,
and opaque anomaly scores. Reviewers need a reproducible way to inspect unusual
examples, understand why they were surfaced, group related evidence, record
decisions, and compare runs without uploading sensitive data.

## 3. Target Users

- Research engineers evaluating unfamiliar datasets.
- Domain researchers performing hypothesis-generating analysis.
- Quality and reliability engineers reviewing visual or operational data.
- ML engineers comparing discovery backends under controlled evaluation.
- Technical reviewers auditing evidence and reviewer decisions.

## 4. Product Principles

1. Evidence before claims.
2. Human review is explicit and preserved.
3. Reproducibility is a product feature.
4. Local-first operation is the default trust posture.
5. Implemented, experimental, and planned capabilities are never conflated.
6. Heavy ML dependencies remain optional and benchmark-gated.

## 5. Current Baseline

### Implemented

- Image-folder validation, profiling, multi-scale patch extraction, statistical
  representations, novelty scoring, diversity selection, grouping, evidence,
  confidence breakdowns, and cautious reports.
- Markdown, JSON, and static HTML reports; schema validation; run metadata and
  history; benchmark and local verification scripts.
- Local JSONL reviewer feedback and deterministic review-memory summaries.
- Lightweight tabular and time-series CSV CLI workflows.
- Local ADE Studio frontend plus localhost Python API for visual analysis, run
  and report browsing, and preview assets.

### Partial

- Studio reads feedback counts but does not provide a complete feedback write and
  history workflow.
- Tabular and time-series workflows are not fully wired into Studio.
- Memory is in-process and is not a validated reference memory bank.
- Evaluation tooling exists, but does not yet provide a governed dataset registry,
  repeated trials, or model-comparison scorecards.

### Not implemented

- Production video, logs, audio, documents, sensor streams, or live ingestion.
- Persistent database, object storage, job queue, workspaces, RBAC, SSO, billing,
  hosted uploads, or multi-tenant deployment.
- Deep encoders or sequence models in the default runtime.
- Validated forecasting, alerting, causal inference, or automated conclusions.

## 6. Goals for Local Beta

- Provide one reliable end-to-end visual discovery and review workflow.
- Make every run reproducible from a manifest and configuration snapshot.
- Complete reviewer feedback capture and display in ADE Studio.
- Establish controlled benchmark datasets and model-evaluation scorecards.
- Define stable versioned report and local API contracts.
- Maintain a local-only security boundary with automated negative tests.

## 7. Functional Requirements

| ID | Requirement | Local Beta acceptance |
| --- | --- | --- |
| PRD-FR-001 | Ingest supported local datasets through explicit adapters. | Visual, tabular, and time-series inputs validate consistently and unsupported inputs fail clearly. |
| PRD-FR-002 | Execute a deterministic discovery run from versioned configuration. | Identical input, version, seed, and config produce equivalent ranked outputs within documented tolerances. |
| PRD-FR-003 | Preserve provenance for every surfaced candidate. | Each candidate links to source, coordinates/row/time, score components, backend version, and run ID. |
| PRD-FR-004 | Produce human- and machine-readable reports. | Markdown, JSON, and HTML outputs validate against a versioned contract. |
| PRD-FR-005 | Support explicit human-review decisions. | Studio and CLI can create, list, and display append-only review records with reviewer, timestamp, label, and notes. |
| PRD-FR-006 | Compare runs and backend configurations. | A reviewer can compare metadata, candidate overlap, ranking changes, runtime, and resource use. |
| PRD-FR-007 | Provide evidence-oriented candidate review. | Studio exposes source context, preview/evidence, score breakdown, limitations, and review status. |
| PRD-FR-008 | Export a reproducibility manifest. | Each run records code version, config digest, dataset fingerprint, environment, seed, and artifact checksums. |
| PRD-FR-009 | Keep advanced ML backends optional. | Default install remains lightweight; optional backends register through documented interfaces. |
| PRD-FR-010 | Fail safely. | Invalid paths, malformed files, contract mismatches, and backend failures produce bounded errors without partial claims. |

## 8. Non-Functional Requirements

| ID | Requirement | Target |
| --- | --- | --- |
| PRD-NFR-001 | Reproducibility | 100% of benchmark runs emit a complete manifest. |
| PRD-NFR-002 | Test quality | Changed core behavior has unit and integration coverage; release gate passes on Python 3.11 and 3.12. |
| PRD-NFR-003 | Performance transparency | Runtime, item count, and peak memory are recorded for governed benchmarks. |
| PRD-NFR-004 | Accessibility | Core Studio workflows meet WCAG 2.2 AA interaction and contrast expectations. |
| PRD-NFR-005 | Security | Local API binds to loopback by default; path traversal and unsafe file access are covered by negative tests. |
| PRD-NFR-006 | Compatibility | Report and API schemas are versioned with documented compatibility policy. |
| PRD-NFR-007 | Observability | Structured local logs use correlation/run IDs and exclude dataset payloads by default. |
| PRD-NFR-008 | Documentation integrity | Status claims are checked against tests or explicit evidence before release. |

## 9. Success Metrics

- Reviewer yield: proportion of top-ranked candidates marked useful or requiring
  further investigation.
- False-positive burden: candidates marked false positive per reviewed run.
- Evidence completeness: candidates with valid provenance and preview/context.
- Reproducibility rate: governed runs reproducible from their manifests.
- Stability: ranking overlap across repeated deterministic runs.
- Performance: wall time and peak memory per dataset size and backend.
- Review throughput: median time from candidate open to recorded decision.

These metrics are evaluation signals, not claims of scientific validity.

## 10. Local Beta Release Gates

1. Python lint, type, unit, integration, and local verification checks pass.
2. Frontend lint, typecheck, build, accessibility smoke tests, and API contract
   tests pass.
3. Reproducibility manifests and versioned report contracts are implemented.
4. Studio feedback create/list/display workflow is complete.
5. Governed visual benchmark and at least one non-visual benchmark produce a
   checked scorecard with limitations.
6. Security negative tests and dependency scans have no unresolved critical
   findings.
7. Documentation accurately distinguishes current, experimental, and planned
   capabilities.

## 11. Explicit Non-Goals for Local Beta

- Multi-tenant hosting, subscriptions, SSO, or regulatory certification.
- Autonomous scientific conclusions or production alerting.
- Supporting every modality.
- Adding xLSTM, transformers, or deep encoders without controlled benchmark
  evidence and an optional dependency boundary.

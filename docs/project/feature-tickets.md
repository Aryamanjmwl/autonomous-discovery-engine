# Feature Ticket List

**Baseline:** 2026-07-16
**Delivery strategy:** Stabilize Local Beta before expanding modalities or models

Status values: `Done`, `In progress`, `Ready`, `Blocked`, `Research`. Priorities:
`P0` release blocker, `P1` next milestone, `P2` planned, `P3` exploratory.

## Milestone M0 — Baseline Reconciliation

| ID | Priority | Status | Ticket | Acceptance summary |
| --- | --- | --- | --- | --- |
| ADE-030 | P0 | Ready | Introduce canonical pipeline factory | CLI and Studio select adapters/backends through one tested composition root; modality branching is not duplicated. |
| ADE-031 | P0 | Ready | Add `RunManifest` and dataset fingerprint | Every run records revision, config digest, dataset fingerprint, backend versions, seed, environment, and artifact checksums. |
| ADE-032 | P0 | Ready | Version report and Studio API contracts | Responses and reports carry schema versions; compatibility and error-envelope tests pass. |
| ADE-033 | P0 | Ready | Reconcile status and release documentation | Current Studio integration and partial areas are accurately represented; automated claim checks pass. |

## Milestone M1 — Local Beta Review Loop

| ID | Priority | Status | Depends on | Ticket | Acceptance summary |
| --- | --- | --- | --- | --- | --- |
| ADE-034 | P0 | Ready | ADE-032 | Add feedback list/create API | Append-only validation, stable IDs, correction semantics, and negative tests. |
| ADE-035 | P0 | Ready | ADE-034 | Complete Studio feedback workflow | Reviewer can create and inspect decisions; history persists across restart; errors are recoverable. |
| ADE-036 | P1 | Ready | ADE-031, ADE-032 | Add run-detail and comparison APIs | Compare provenance, configuration, resources, candidate overlap, and incompatibilities. |
| ADE-037 | P1 | Ready | ADE-036 | Build Studio run comparison | Two compatible runs can be compared and exported with provenance. |
| ADE-038 | P1 | Ready | ADE-030 | Wire tabular workflow into Studio | Input validation, execution, report browsing, and modality-specific evidence are tested. |
| ADE-039 | P1 | Ready | ADE-030 | Wire time-series workflow into Studio | Timestamp/entity configuration and point/window evidence are tested. |
| ADE-040 | P1 | Ready | ADE-032 | Add Studio critical-path E2E suite | Connected, empty, invalid input, failed run, report, and feedback journeys run in CI. |

## Milestone M2 — Evaluation and Research Rigor

| ID | Priority | Status | Depends on | Ticket | Acceptance summary |
| --- | --- | --- | --- | --- | --- |
| ADE-041 | P0 | Ready | ADE-031 | Create governed benchmark registry | Dataset cards, versions, licenses, fingerprints, splits, and limitations are machine-readable. |
| ADE-042 | P0 | Ready | ADE-041 | Build experiment runner and scorecard | Repeated trials record quality, stability, runtime, peak memory, environment, and failures. |
| ADE-043 | P1 | Ready | ADE-042 | Define reviewer-yield evaluation protocol | Label guide, sampling plan, inter-reviewer handling, and uncertainty reporting are documented. |
| ADE-044 | P1 | Ready | ADE-042 | Establish visual baseline suite | Statistical backend is compared with at least one optional learned encoder on governed data. |
| ADE-045 | P1 | Ready | ADE-042 | Establish time-series baseline suite | Robust statistics, change-point, window features, and at least one learned baseline are compared. |
| ADE-046 | P2 | Research | ADE-045, ADE-050 | Evaluate xLSTM sequence backend | Optional PyTorch extra; comparison against simpler baselines; ablation, latency, memory, training cost, stability, and failure analysis. No default promotion without a decision record. |

## Milestone M3 — Security and Reliability

| ID | Priority | Status | Depends on | Ticket | Acceptance summary |
| --- | --- | --- | --- | --- | --- |
| ADE-047 | P0 | Ready | ADE-032 | Enforce approved dataset roots | Canonical path, symlink, traversal, and cross-platform negative tests pass. |
| ADE-048 | P0 | Ready | — | Add resource and parser limits | File size/count, image dimensions, patch count, CSV rows, and execution bounds fail safely. |
| ADE-049 | P1 | Ready | ADE-031 | Add structured local observability | Correlation/run IDs, bounded events, redaction tests, and no raw payload logging. |
| ADE-050 | P1 | Ready | ADE-042 | Add CI research-quality gates | Python/frontend checks, contract tests, security scans, benchmark smoke test, and artifact validation. |
| ADE-051 | P1 | Ready | ADE-031 | Add reproducible release provenance | Clean-tree verification, dependency inventory, checksums, and release evidence bundle. |

## Milestone M4 — Temporal and Multimodal Expansion

| ID | Priority | Status | Depends on | Ticket | Acceptance summary |
| --- | --- | --- | --- | --- | --- |
| ADE-052 | P1 | Ready | ADE-045 | Add time-series drift/change baseline | Seasonal normalization, change points, missingness, and drift evidence with controlled tests. |
| ADE-053 | P1 | Ready | ADE-031, ADE-052 | Add entity alignment and tracking contract | Stable entity identity and observation alignment support temporal comparison without claiming causality. |
| ADE-054 | P2 | Ready | ADE-030, ADE-041 | Implement logs/events adapter | Parser policy, event/session representation, evidence, reports, and benchmark fixture. |
| ADE-055 | P2 | Blocked | ADE-053 | Implement video frame workflow | Bounded decoding, sampling, temporal provenance, evidence, and resource tests. |
| ADE-056 | P3 | Research | ADE-042 | Assess domain-specific satellite pipeline | Geospatial alignment, cloud/season controls, domain benchmark, and cautious interpretation. |

## Delivery Order

The immediate next slice is `ADE-031` + `ADE-032`, followed by `ADE-034` and
`ADE-035`. This creates trustworthy provenance and completes the reviewer loop.
`ADE-041` and `ADE-042` then establish the evidence required for model work.
xLSTM evaluation (`ADE-046`) stays downstream of the sequence contract and
time-series baseline; it is not on the production critical path.

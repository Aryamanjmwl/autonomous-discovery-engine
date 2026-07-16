# ADE Roadmap

**Revised:** 2026-07-16
**Planning horizon:** Technical Preview to enterprise-ready research platform

ADE is a modular discovery platform for surfacing candidate anomalies and
patterns with traceable evidence and explicit human review. Roadmap status is
defined by merged code, tests, contracts, and reproducible evidence—not by UI
mockups or research intent.

## Phase 0 — Technical Preview Baseline (substantially complete)

- Visual image-folder pipeline and evidence-oriented reports.
- Lightweight tabular and time-series CSV foundations.
- Adapter/backend extension contracts.
- Run history, benchmark and verification scripts, local feedback, and static
  artifacts.
- ADE Studio frontend connected to a localhost API for visual analysis.

Remaining baseline work: reconcile documentation claims and consolidate pipeline
composition shared by CLI and Studio.

## Phase 1 — Local Beta: Provenance and Review (next)

- Canonical run manifest, dataset fingerprint, config digest, and artifact checksums.
- Versioned report and local API contracts with stable error envelopes.
- Complete Studio feedback create/list/history workflow.
- Run details and reproducible comparison.
- Tabular and time-series Studio integration.
- Approved local dataset roots, resource limits, and expanded security tests.
- Critical-path frontend end-to-end and accessibility checks.

Exit gate: the PRD Local Beta release gates pass with evidence.

## Phase 2 — Research Evaluation Platform

- Governed benchmark registry and dataset cards.
- Repeated experiment runner, scorecards, ablations, and failure analysis.
- Reviewer-yield protocol and uncertainty reporting.
- Strong visual and time-series baseline suites.
- Optional learned encoders behind stable interfaces.
- Structured runtime, peak-memory, and reproducibility measurements.

Exit gate: backend promotion decisions are evidence-based and reproducible.

## Phase 3 — Temporal and Operational Discovery

- Time-series drift and change-point baselines.
- Stable entity alignment and temporal provenance.
- Logs/events adapter with session evidence.
- Bounded video frame workflow.
- Optional sequence backend contract.
- xLSTM research evaluation only after statistical, recurrent, convolutional,
  and transformer/state-space baselines exist.

Exit gate: at least two temporal modalities have governed benchmarks and useful
review evidence without production-alerting claims.

## Phase 4 — Team Deployment Foundation

- Artifact-store and job-execution abstractions.
- PostgreSQL metadata, object storage, and worker queue.
- Identity integration, projects, roles, API credentials, and immutable audit.
- Retention, backup/restore, observability, and deployment documentation.
- Threat-model update and external security review before internet exposure.

Exit gate: single-organization deployment with tested isolation and recovery.

## Phase 5 — Enterprise and Domain Packages

- Organization/workspace isolation, SSO/OIDC, policy controls, and usage limits.
- Deployment automation based on demonstrated operational need.
- Domain packages beginning with manufacturing/quality, scientific datasets,
  and logs/security—each with domain-specific evaluation and limitations.
- Compliance work only for explicitly scoped deployments with auditable evidence.

## Deliberately Deferred

- No heavy ML dependency in the default install.
- No xLSTM or other model promoted from paper claims alone.
- No Kubernetes-first architecture.
- No mobile-app priority.
- No production streaming or alerting before offline evaluation is credible.
- No medical, scientific, financial, security, or operational truth claims.
- No SOC 2, HIPAA, ISO, or similar certification claims without formal scope and
  assessment.

Detailed requirements and dependency-ordered tickets are maintained in
[`docs/project/`](project/README.md).

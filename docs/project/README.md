# ADE Project Baseline

**Baseline date:** 2026-07-16
**Repository baseline:** `main` at `be84dedf23fdaf6658a6beb5fb32d0ca21a185f2`
**Product stage:** Local Technical Preview progressing toward Local Beta

This directory is the controlled product and engineering baseline for the
Autonomous Discovery Engine (ADE). It separates implemented behavior from
approved next work and research hypotheses. Repository code, tests, and
generated evidence remain authoritative when a document and implementation
disagree.

## Controlled Documents

| Document | Purpose |
| --- | --- |
| [Product requirements](product-requirements.md) | Product outcomes, scope, requirements, metrics, and release gates |
| [Technical architecture](technical-architecture.md) | Current architecture, target boundaries, data flow, and quality attributes |
| [Security and access](security-and-access.md) | Threat model, trust boundaries, controls, roles, and security backlog |
| [Frontend specification](frontend-specification.md) | ADE Studio workflows, states, API contracts, and UX acceptance criteria |
| [Feature tickets](feature-tickets.md) | Dependency-ordered delivery backlog with acceptance criteria |

## Governance

- Requirement IDs use `PRD-FR-*`, `PRD-NFR-*`, and `SEC-*` prefixes.
- Delivery tickets use `ADE-*` identifiers and reference their governing
  requirements.
- Architecture changes that affect public contracts, persistence, security, or
  model evaluation require an Architecture Decision Record.
- A capability is **implemented** only when code, automated tests, documentation,
  and reproducible verification exist on the default branch.
- Experimental results must record dataset version, configuration, random seed,
  environment, metrics, and limitations.
- Candidate findings remain decision-support outputs requiring human review.

# Dashboard Release Plan

This plan describes a staged path from the current static report outputs toward
a dashboard review experience. Future phases are not implemented unless a branch
adds code, tests, and documentation for them.

## Phase 0: Current Static Reports and Local Dashboard Export

Scope:

- Use existing Markdown, JSON, and static HTML reports.
- Export a local static dashboard-style artifact summary from existing files.
- Keep analysis and review file-based.
- Require human review for candidate findings.

Deliverables:

- JSON report validation.
- Static HTML export.
- Local static dashboard export with `index.html` and `dashboard_data.json`.
- Stable `anomaly_id` and `concept_id` fields.
- Local feedback JSONL foundation.
- Dashboard product spec and frontend contract.

Acceptance criteria:

- `python scripts/verify_local.py` passes.
- HTML export renders a local review artifact.
- `python -m ade.cli --export-local-dashboard --output data/dashboard` writes a
  local static demo viewer without running analysis.
- Report validation passes for generated reports.
- Documentation states that no dashboard app, server, authentication, database,
  or hosted deployment is implemented.

Risks:

- Static exports do not support interactive filtering.
- Feedback is local and not a production audit trail.
- Generated artifacts must remain out of version control.

## Phase 1: Local Read-Only Dashboard

Scope:

- Build a local read-only review interface over existing report JSON files.
- No server, authentication, database, billing, or cloud deployment.

Deliverables:

- Run list from local run index.
- Report detail view.
- Dataset profile panel.
- Candidate anomaly and candidate concept tables.
- Evidence preview panel.

Acceptance criteria:

- Dashboard reads current report JSON without changing report generation.
- Missing files and invalid reports show clear error states.
- UI text uses candidate anomaly, candidate concept, and requires human review.

Risks:

- Local file paths may differ across machines.
- Preview assets may be missing or moved.
- Large reports may need pagination or virtualization.

## Phase 2: Local Review Workflow Using Feedback JSONL

Scope:

- Add local feedback submission and filtering using the existing JSONL store.
- Keep feedback append-only and local.

Deliverables:

- Feedback controls for anomaly and concept targets.
- Feedback state joined onto report findings by `anomaly_id` and `concept_id`.
- Feedback list and simple filters.

Acceptance criteria:

- Feedback writes valid JSONL records.
- Invalid target IDs fail clearly.
- Existing CLI feedback commands remain compatible.

Risks:

- No user accounts or access controls.
- JSONL files can be edited outside the app.
- This is not a production audit trail.

## Phase 3: Benchmark and Run Comparison

Scope:

- Compare local runs and benchmark metadata.
- Surface changes in counts, validation status, and runtime metadata.

Deliverables:

- Benchmark list from `data/benchmarks/*.json`.
- Run comparison table.
- Links to generated reports and assets.
- Warning summaries.

Acceptance criteria:

- Benchmark files validate as JSON.
- Comparisons avoid benchmark marketing claims.
- Missing benchmark outputs show an empty state.

Risks:

- Local timing varies by machine.
- Small demo datasets are not representative.
- Cross-run concept matching requires careful design.

## Phase 4: Adapter-Aware Review Views

Scope:

- Prepare review views for future dataset adapters without claiming support
  before implementation.

Deliverables:

- Adapter metadata display.
- Dataset-profile renderer selection.
- Evidence renderer interface for visual and future non-visual records.
- Clear unsupported-adapter states.

Acceptance criteria:

- Existing visual reports still render correctly.
- Unsupported adapter reports fail gracefully.
- Documentation distinguishes current fields from planned fields.

Risks:

- Premature abstraction can obscure current visual review needs.
- Non-visual evidence may need different interaction patterns.

## Phase 5: Enterprise Deployment Path

Scope:

- Define, then later implement, a hosted review architecture only after local
  workflows are stable.

Deliverables:

- Service boundary proposal.
- Persistence and audit requirements.
- Access-control requirements.
- Deployment and security review plan.

Acceptance criteria:

- No enterprise claims are made before implementation and review.
- Hosted design preserves report IDs, evidence traceability, and human-review
  requirements.
- Security and privacy requirements are documented before user data is hosted.

Risks:

- Cloud storage, authentication, billing, and audit logs add significant scope.
- Compliance requirements vary by domain and require professional review.
- Hosted workflows can expose sensitive source data if not designed carefully.

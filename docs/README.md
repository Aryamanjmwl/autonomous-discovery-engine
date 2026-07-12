# ADE Documentation

ADE is an adapter-based autonomous discovery platform. The current
implementation includes a mature visual/image-folder workflow plus lightweight
CSV adapter foundations where implemented. It profiles inputs, builds
deterministic representations, ranks candidate anomalies, groups candidate
concepts, and writes reviewable reports.

All findings are candidate findings and require human review.

## Start Here

- [Product scope](product_scope.md): current scope, future adapters, and non-goals.
- [Modality capability matrix](modality_capability_matrix.md): implemented, foundation, and planned modality status.
- [Architecture](ARCHITECTURE.md): ADE layers, extension points, visual pipeline, and feedback flow.
- [Development workflow](development_workflow.md): install, test, demo, config, benchmark, and local verification commands.
- [CLI reference](cli_reference.md): PowerShell-friendly command examples.
- [Report schema](report_schema.md): JSON report fields, stable IDs, feedback metadata, and compatibility notes.
- [Engineering quality](engineering_quality.md): coding, testing, artifact, review, and release standards.
- [Dashboard product spec](dashboard/dashboard_product_spec.md): planned review UX without an implemented dashboard app.
- [Dashboard frontend contract](dashboard/dashboard_frontend_contract.md): report, feedback, benchmark, and run-history payloads for future UI work.
- [Roadmap](ROADMAP.md): staged product and engineering direction.
- [Release checklist](release_checklist.md): private-alpha verification checklist.
- [Versioning policy](versioning_policy.md): pre-1.0 version and schema expectations.
- [Private-alpha readiness audit](releases/private_alpha_readiness_audit.md): current release-readiness assessment.

## Architecture and Extension Points

- [Adapter/backend guide](ADAPTER_BACKEND_GUIDE.md)
- [Technical decisions](technical_decisions.md)
- [Research and IP notes](research_and_ip_notes.md)
- [Security model](SECURITY_MODEL.md)
- [Enterprise readiness notes](ENTERPRISE_READINESS.md)

## Examples

- [Demo workflow](../examples/demo_workflow.md): generate synthetic images, run analysis, validate reports, export HTML, record feedback, benchmark locally, and run the full local verification script.

## Dashboard Planning

- [Dashboard release plan](dashboard/dashboard_release_plan.md)
- [Dashboard design tokens](dashboard/design_tokens.json)

These files define a future dashboard review experience and frontend data
contract. They do not add a deployed dashboard app.

Generated demo images, reports, benchmark files, feedback logs, caches, and run
metadata are local artifacts and should stay out of version control.


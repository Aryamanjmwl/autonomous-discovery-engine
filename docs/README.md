# ADE Documentation

ADE is a general autonomous discovery platform. The current implementation is
visual-data-first: it profiles image folders, extracts image patches, computes
lightweight statistical representations, ranks candidate anomalies, groups
candidate concepts, and writes reviewable reports.

All findings are candidate findings and require human review.

## Start Here

- [Product scope](product_scope.md): current scope, future adapters, and non-goals.
- [Architecture](architecture.md): ADE layers, extension points, visual pipeline, and feedback flow.
- [Development workflow](development_workflow.md): install, test, demo, config, benchmark, and local verification commands.
- [CLI reference](cli_reference.md): PowerShell-friendly command examples.
- [Report schema](report_schema.md): JSON report fields, stable IDs, feedback metadata, and compatibility notes.
- [Engineering quality](engineering_quality.md): coding, testing, artifact, review, and release standards.
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

Generated demo images, reports, benchmark files, feedback logs, caches, and run
metadata are local artifacts and should stay out of version control.

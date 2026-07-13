# ADE Documentation

ADE is a general autonomous discovery platform. The current implementation is
visual-data-first: it profiles image folders, extracts image patches, computes
lightweight statistical representations, ranks candidate anomalies, groups
candidate concepts, and writes reviewable reports.

All findings are candidate findings and require human review.

## Start Here

- [Product scope](product_scope.md): current scope, future adapters, and non-goals.
- [Architecture](ARCHITECTURE.md): ADE layers, extension points, visual pipeline, and feedback flow.
- [Development workflow](development_workflow.md): install, test, demo, config, benchmark, and local verification commands.
- [CLI reference](cli_reference.md): PowerShell-friendly command examples.
- [Report schema](report_schema.md): JSON report fields, stable IDs, feedback metadata, and compatibility notes.
- [Modality capability matrix](modality_capability_matrix.md): implemented, foundation, and planned modality status.
- [Portfolio case study](portfolio_case_study.md): project summary, design choices, current capabilities, limitations, and interview talking points.
- [Sample outputs](sample_outputs.md): generated report, benchmark, dashboard, run-history, and feedback artifacts.
- [ADE Studio](ade_studio.md): local UI foundation, mock data scope, and future integration path.
- [CV project description](cv_project_description.md): concise project wording for resumes, portfolios, and interviews.
- [Engineering quality](engineering_quality.md): coding, testing, artifact, review, and release standards.
- [Roadmap](ROADMAP.md): staged product and engineering direction.
- [Release checklist](release_checklist.md): technical preview verification checklist.
- [Versioning policy](versioning_policy.md): pre-1.0 version and schema expectations.
- [Technical Preview readiness audit](releases/technical_preview_readiness_audit.md): current release-readiness assessment.
- [v0.1.0 Technical Preview release notes](releases/v0.1.0-preview.md): release scope, verification, limitations, and compatibility notes.
- [GitHub release body draft](releases/github_release_body_v0.1.0-preview.md): copy-paste release text for GitHub Releases.
- [Demo asset guidance](demo_assets.md): manual screenshot plan and safe release attachment guidance.

## Architecture and Extension Points

- [Adapter/backend guide](ADAPTER_BACKEND_GUIDE.md)
- [Technical decisions](technical_decisions.md)
- [Research and IP notes](research_and_ip_notes.md)
- [Security model](SECURITY_MODEL.md)
- [Enterprise readiness notes](ENTERPRISE_READINESS.md)

## Examples

- [Interview demo script](../examples/demo_script.md): short PowerShell walkthrough for demos and technical interviews.
- [Demo workflow](../examples/demo_workflow.md): generate synthetic images, run analysis, validate reports, export HTML, record feedback, benchmark locally, and run the full local verification script.
- [Tabular workflow](../examples/modalities/tabular_workflow.md): lightweight CSV tabular example.
- [Time-series workflow](../examples/modalities/timeseries_workflow.md): lightweight timestamped CSV example.

## Dashboard Planning

- [ADE Studio local UI foundation](ade_studio.md)
- [Dashboard product spec](dashboard/dashboard_product_spec.md)
- [Dashboard frontend contract](dashboard/dashboard_frontend_contract.md)
- [Dashboard release plan](dashboard/dashboard_release_plan.md)
- [Dashboard design tokens](dashboard/design_tokens.json)

These files define the local static dashboard export and future dashboard review
experience. They do not add a deployed dashboard app, server, auth, or database.

Generated demo images, reports, benchmark files, feedback logs, caches, and run
metadata are local artifacts and should stay out of version control.


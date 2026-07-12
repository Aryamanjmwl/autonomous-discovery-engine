# Versioning Policy

ADE is currently pre-1.0. Versioning should communicate compatibility intent
without implying production maturity.

## Pre-1.0 Versions

- Patch versions are for fixes, documentation corrections, and compatible test improvements.
- Minor versions are for additive capabilities, new CLI options, new report fields, and new adapter foundations.
- Breaking CLI or report-schema changes should be called out clearly in the changelog.

## Schema Compatibility

Reports should evolve through additive fields where practical. Consumers should
ignore unknown fields and prefer stable identifiers such as `anomaly_id`,
`concept_id`, and `run_id`.

Newly generated reports should include stable target IDs for feedback workflows.
Legacy reports may validate with warnings if they predate those fields.

## Technical Preview Limits

Technical preview versions do not claim production readiness, scientific validity,
medical or financial usefulness, hosted security controls, compliance status, or
enterprise deployment support.

## Tag Naming

Suggested technical preview tag forms:

- `v0.1.0-preview`
- `v0.1.1-preview`
- `preview-YYYYMMDD`

Use one convention consistently once releases begin.

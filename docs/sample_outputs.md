# ADE Sample Outputs

ADE generated artifacts are local demo and review files. They are ignored by
Git so the repository stays source-focused and does not commit generated data.
All candidate findings require human review.

## `data/reports/demo_report.md`

The Markdown discovery report is the human-readable review artifact. It
summarizes the run, dataset profile, candidate anomalies, candidate concepts,
evidence, limitations, and review notes.

## `data/reports/demo_report.json`

The JSON sidecar is the structured report payload. It is intended for validators,
local dashboard exports, future review tools, and compatibility checks. It
contains stable target IDs such as `anomaly_id` and `concept_id` where generated
reports support feedback.

## `data/reports/demo_report.html`

The static HTML report is a local browser-friendly export of the report. It does
not start a server or dashboard app.

## `data/reports/runs/index.json`

The run index records compact local run history. It allows commands and local
review tools to list recent runs without scanning every report manually.

## `data/benchmarks/demo_benchmark.json`

The benchmark JSON records local repeatability metadata such as command inputs,
duration, generated report path, and validation status. It is not a public
performance claim.

## `data/dashboard/index.html`

The local dashboard export is a static demo viewer built from existing local
artifacts. It can summarize run history, reports, benchmark files, static HTML
reports, and feedback JSONL when those files exist.

## `data/feedback/feedback.jsonl`

The feedback store is local JSONL for human-review labels on candidate anomalies
and candidate concepts. It can support review-informed ranking signals in later
reports, but it is not a production audit log or supervised learning system.

## Version Control

Generated demo images, reports, preview assets, run history, benchmarks,
dashboard exports, and feedback logs are ignored by Git. Recreate them locally
with the commands in `examples/demo_script.md` or `examples/demo_workflow.md`.

# Dashboard Product Spec

ADE is a general autonomous discovery platform. The current implementation is
visual-data-first and produces local reports for candidate anomalies, candidate
concepts, evidence, and reviewer feedback. This document defines the intended
dashboard user experience and the current local static export MVP; it does not
describe an implemented dashboard app or hosted service.

All dashboard surfaces must make clear that findings are candidate findings and
require human review.

## Purpose

The dashboard should help reviewers inspect ADE runs, compare candidate
findings, review supporting evidence, and record feedback without treating scores
as final conclusions.

The product principle is discovery with evidence, not only anomaly scores.

## Primary Users

- Individual researchers reviewing exploratory runs
- ML or data engineers evaluating discovery quality
- Product teams triaging possible patterns in private datasets
- Domain reviewers who need evidence-backed candidate findings
- Future operations teams comparing runs and benchmark outputs

## Current Scope

Current source data for a dashboard is file-based:

- ADE JSON report files
- generated preview assets referenced by the report
- run metadata and run-index files
- local feedback JSONL records
- benchmark JSON files
- static HTML report exports

The current local static dashboard export is:

```powershell
python -m ade.cli --export-local-dashboard --output data/dashboard
```

It writes `data/dashboard/index.html` and
`data/dashboard/dashboard_data.json`. It reads existing local artifacts where
present and shows empty states when folders or files are missing. It does not
run analysis.

The current repository does not implement a dashboard app, dashboard server,
user accounts, database, cloud upload flow, or collaborative review queue.

## Non-Goals

- No hosted dashboard in this branch
- No React, Vite, Next.js, Streamlit, FastAPI, database, auth, billing, or cloud deployment
- No medical, scientific, financial, legal, or operational conclusions
- No claim that a candidate anomaly or candidate concept is true
- No replacement for domain expert review

## Data Sources

The initial dashboard should read local artifacts:

- `data/reports/*.json` for report payloads
- `data/reports/assets/` for image previews
- `data/reports/runs/index.json` for run history
- `data/feedback/feedback.jsonl` for local review feedback
- `data/benchmarks/*.json` for benchmark metadata

Future implementations may replace local files with a service API, but the data
contract should remain close to the report and feedback schemas.

## Run Overview Workflow

The run overview should show:

- run ID and timestamp
- input path
- report paths
- number of images and patches
- number of candidate anomalies
- number of candidate concepts
- human-review-required status
- validation state and warnings

The reviewer should be able to open a run, inspect findings, and export or share
static report artifacts.

## Dataset Profile Review

The dataset profile view should show:

- input type and input path
- valid image count
- unsupported and unreadable file counts
- image size range
- estimated patch count
- warnings from input validation

Warnings should be visible without implying that a run is unusable unless the
profile marks the input invalid.

## Candidate Anomaly Review

Candidate anomaly cards or rows should show:

- `anomaly_id`
- rank
- score and score breakdown when available
- source image or item path
- patch coordinates and scale metadata when available
- preview asset
- concise reason text
- feedback state

The UI should support sorting and filtering, but should avoid presenting the
highest score as a guaranteed finding.

## Candidate Concept Review

Candidate concept views should show:

- `concept_id`
- item count or support count
- representative item
- average anomaly score or confidence summary
- concept summary
- supporting evidence items
- near visual matches when available
- feedback state

Concept language should use candidate concept or possible pattern, not final
discovery claims.

## Evidence Inspection

Evidence inspection should make source traceability easy:

- preview image
- source path
- patch ID
- coordinates
- anomaly score
- nearest visual matches
- confidence components
- warnings and limitations

Evidence should stay bounded so review remains usable.

## Feedback Submission

Feedback should attach to stable report IDs:

- `anomaly_id` for anomaly targets
- `concept_id` for concept targets

Feedback labels should match the local feedback module and be stored as JSONL
until a stronger persistence layer is designed.

## Benchmark Comparison

Benchmark comparison should show:

- benchmark ID and timestamp
- input path and config path
- generated report path
- validation result
- duration
- warnings and metadata

This is useful for local regressions and repeatability checks, not performance
claims.

## Export and Report Sharing

The dashboard should link or export:

- Markdown report
- JSON report
- static HTML report
- preview assets
- benchmark metadata

Private data handling must remain explicit. Sharing a report may expose source
paths, patches, reviewer notes, and generated assets.

## Audit and Reviewer History

Current reviewer history is local JSONL feedback. A future dashboard may show:

- reviewer name
- label
- notes
- target type and target ID
- timestamp
- source report path

This is not yet a production audit trail.

## Known Limitations

- Current mature analysis is visual-first, with lightweight tabular and
  time-series CSV workflows.
- Current dashboard support is local static export only.
- Feedback is local JSONL and has no access controls.
- Run history is local file metadata.
- Candidate findings require human review.
- No deployed dashboard app exists in this branch.

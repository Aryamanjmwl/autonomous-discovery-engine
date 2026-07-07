# ADE Local Dashboard

ADE includes a small static dashboard generator for local review of existing
run history and report artifacts. It is intended for development and private
analysis workflows where the user wants a quick way to inspect prior runs,
candidate findings, concept groups, evidence previews, and report paths.

The dashboard does not create a server, database, upload system, or hosted
application. It reads the existing run index and JSON reports from the local
filesystem.

## Generate the Dashboard

Run an analysis first:

```bash
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md
```

Then generate the local dashboard:

```bash
ade dashboard
```

The default output is:

```text
data/reports/dashboard/index.html
```

The command prints a local `file://` URL that can be opened in a browser.

Use a custom output directory when needed:

```bash
ade dashboard --dashboard-output data/reports/dashboard
```

## What It Shows

- Dashboard home page with a local-use note
- Run history loaded from `data/reports/runs/index.json`
- Run id, timestamp, dataset path, report paths, and result counts
- Run detail pages generated from the structured JSON report when available
- Dataset summary and input profile
- Backend/scoring metadata when present
- Top candidate anomalies and factual reason text
- Candidate concept groups and evidence examples
- Preview thumbnails when referenced assets exist
- Limitations and reproducibility notes from the report

## Failure Handling

The dashboard is intentionally tolerant of partial local state:

- Missing run history renders an empty dashboard.
- Missing report JSON renders a run detail page with a warning.
- Malformed report JSON renders a warning instead of crashing.
- Missing preview assets are shown as unavailable.
- Empty findings or concept lists are rendered as explicit empty states.

## Limitations

- Local static files only.
- No authentication.
- No database.
- No uploads.
- No multi-user support.
- No production hosting assumptions.

For a reviewable workflow, regenerate the dashboard after creating new ADE
runs so the static HTML reflects the latest run index and report artifacts.

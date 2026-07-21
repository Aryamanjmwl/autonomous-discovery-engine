# ADE Studio Local Engine Integration

ADE Studio is the local-first interactive app layer for ADE v0.1.0 Technical
Preview. It lives in `apps/studio/frontend` and connects to a small local Python
API under `ade.studio`.

The current connected workflow supports visual/image-folder analysis through
the local ADE engine. ADE Studio can read local run/report artifacts and submit
a local path for synchronous visual analysis. If the backend is unavailable,
the frontend falls back to mock preview data for demos. It does not add cloud
hosting, auth, database storage, billing, production streaming, browser upload,
or hosted product behavior.

## What It Shows

- Local run telemetry from ADE artifacts when connected
- Candidate anomaly and candidate concept review surfaces
- Possible pattern summaries
- Evidence previews
- Review status controls
- Novelty score and confidence score readouts
- Local reports, benchmark, feedback, and settings screens

All findings are candidate findings and require human review. The UI supports
review-oriented presentation; it does not claim automated truth.

## How To Run Locally

Terminal 1, from the repository root:

```powershell
pip install -e ".[studio]"
python -m ade.studio.api --host 127.0.0.1 --port 8765
```

Alternative:

```powershell
uvicorn ade.studio.api:app --host 127.0.0.1 --port 8765 --reload
```

Terminal 2:

```powershell
cd apps/studio/frontend
npm install
npm run typecheck
npm run build
npm run dev
```

The frontend calls `NEXT_PUBLIC_ADE_API_URL` and defaults to
`http://127.0.0.1:8765`.

The local API accepts JSON at `POST /api/studio/analysis`. Use an absolute local
path or a repository-relative path for visual/image-folder analysis:

```json
{
  "input_path": "data/raw/demo_images",
  "workflow": "visual",
  "output_name": "studio_report.md"
}
```

Generated report preview assets are served locally through
`GET /api/studio/report-assets/{asset_name}` from `data/reports/assets/`. The
route accepts asset filenames only, blocks path traversal, and is intended for
localhost Technical Preview use.

Generated HTML reports are served through
`GET /api/studio/reports/{report_name}/html`. The route accepts a local JSON
report filename and serves only the matching sibling HTML report from
`data/reports`.

## Connected Mode Contract

Connected ADE Studio views should show only real local backend state or an
explicit Technical Preview empty state. Current connected surfaces include:

- backend health and refresh
- local visual/image-folder analysis from an absolute or repo-relative path
- backend run and report lists
- selected report details, candidate anomalies, candidate concepts, and preview
  assets when available
- HTML report opening and copy-path actions for local artifacts
- explicit empty states for Studio feedback editing, project management, and
  benchmark browsing when those endpoints are not implemented

The Studio UI must not turn planned adapters, hosted dashboards, production
streaming, or reviewer workflows into active controls until backend support and
tests exist. Findings remain candidate findings and require human review.

If frontend dependencies are not available locally, the rest of ADE still works
through the existing Python CLI, report validation, HTML export, benchmark, and
verification workflows.

## Relationship To Existing ADE Workflows

The mature ADE workflow remains the local visual/image-folder flow with
Markdown, JSON, and HTML reports. CSV tabular and CSV time-series workflows are
lightweight local foundations with CLI reports. ADE Studio now reads local
artifacts such as:

- `data/reports/*.json`
- `data/reports/runs/index.json`
- `data/benchmarks/*.json`
- `data/feedback/feedback.jsonl`
- `data/dashboard/index.html`

Generated frontend artifacts are ignored by Git and should not be committed.

## Current Limits And Future Steps

- Browser file upload is not implemented; use a local path input.
- Visual/image-folder analysis is the connected workflow for this milestone.
- Tabular and time-series workflows remain lightweight foundations for future
  Studio wiring.
- Render feedback-informed review status from the JSONL feedback store.
- Keep reviewer decisions explicit and transparent
- Preserve the local workflow before considering hosted deployment paths




## Optional Advanced Visual Evidence

Connected ADE Studio report details expose advanced evidence only when a local report contains a
valid artifact-backed summary. Reference-score evidence, spatial anomaly maps, fitted calibration,
candidate operating points, and benchmark validation artifacts are optional and are not generated
by the default analysis workflow. Malformed summaries are omitted without breaking report browsing.

These values are review-prioritization signals in a Technical Preview. Calibrated scores are not
universal probabilities, benchmark validation artifacts are not guarantees, and candidate findings
require human review.

## Temporal Reports in Connected Mode

ADE Studio discovers Stage 5B temporal JSON reports only after they exist in the local
reports directory. It validates both the report and its referenced immutable temporal
artifact before exposing sequence metadata or candidate change events. Malformed reports
are ignored with local summary warnings. This Technical Preview provides report review,
not continuous observation, geospatial registration, or scientific confirmation.

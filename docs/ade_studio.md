# ADE Studio Local Engine Integration

ADE Studio is the local-first interactive app layer for ADE v0.1.0 Technical
Preview. It lives in `apps/studio/frontend` and connects to a small local Python
API under `ade.studio`.

The current connected workflow supports visual/image-folder and manifest-driven
temporal analysis through the local ADE engine. ADE Studio can read local
run/report artifacts and the Stage 7A backend can accept synchronous local runs.
Stage 7B connects those endpoints to the browser Run screen. If the backend is unavailable,
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

Stage 7A also exposes a job-oriented local run API:

- `POST /api/studio/runs/image-folder`
- `POST /api/studio/runs/temporal`
- `GET /api/studio/runs`
- `GET /api/studio/runs/{job_id}`

Jobs are stored in memory for the lifetime of the backend process and move
through `queued`, `running`, `succeeded`, or `failed`. Execution is synchronous
in this stage. Image-folder requests accept `input_path`, optional `output_name`,
optional `config_path`, and optional `run_label`. Temporal requests accept
`manifest_path`, `strategy` (`adjacent_difference` or `baseline_difference`),
optional existing patch/evidence limits, optional `output_name`, and optional
`run_label`.

All inputs must exist inside the configured local workspace. External URLs and
path traversal are rejected. Report outputs remain inside the configured report
root, and temporal artifacts remain inside the configured artifact root. The API
does not download inputs, browse the filesystem, or execute arbitrary commands.
Failed jobs expose no report or artifact path as valid evidence.

## Stage 7B Browser Run Screen

The Run screen can submit an image-folder path or temporal manifest path to the
local backend. Image-folder runs accept an optional label and config path.
Temporal runs select `adjacent_difference` or `baseline_difference` and may
provide an optional label and patch size. Submit controls are disabled while the
synchronous request is active, and validation or workflow failures show the real
backend error.

The Runs screen lists exact process-local job records with status, timestamps,
input summary, warnings, errors, report paths, artifact paths, and the
human-review requirement. Successful jobs can refresh report discovery and open
the generated JSON report through the existing report detail route when the job
returns one.

Paths refer to the machine running the ADE backend. There is no browser upload,
server filesystem picker, drag-and-drop transfer, or remote download. Restarting
the backend clears its in-memory Studio job history.

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
- Browser local run controls cover image-folder and temporal workflows.
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

ADE Studio discovers Stage 5B temporal JSON reports after they exist in the local
reports directory, including reports produced by the Stage 7A local run API. It
validates both the report and its referenced immutable temporal
artifact before exposing sequence metadata or candidate change events. Malformed reports
are ignored with local summary warnings. This Technical Preview provides report review,
not continuous observation, geographic registration, or domain verification.

The [Temporal Visual Demo Evidence](demo_temporal_visual_evidence.md) guide provides the
exact local commands needed to create a real temporal report before opening Studio. Studio
does not populate temporal panels from examples or mock report values. Candidate
temporal changes are review-prioritization signals and require human review.

Stage 7A is local-only Technical Preview infrastructure. It does not provide a
cloud or SaaS backend, accounts, uploads, continuous monitoring, satellite integration,
or geospatial registration.

## Stage 7C Local Review Feedback

Studio Findings now records real local reviewer actions for candidate anomalies,
candidate concepts, and candidate temporal changes. Reviewers can mark a
candidate useful, not useful, or needing review and may attach a short note.
The backend validates the report and stable target ID before appending to ADE's
existing `data/feedback/feedback.jsonl` pattern. No second feedback store or
database is introduced.

Studio actions map onto the existing feedback labels: useful uses `interesting`,
not useful uses `not_useful`, and needs review uses `needs_more_data`. Temporal
events use the same record fields with the additive `temporal` target type.
Saved state appears only after the local API confirms the append; validation and
storage errors remain visible to the reviewer.

Feedback is local review state and may inform later review-prioritization
signals. A reviewer action does not scientifically confirm a candidate finding.
Run history remains in memory for the lifetime of the Studio backend session,
while feedback is append-only local JSONL. Stage 7C adds no cloud/SaaS service,
account system, browser upload, continuous monitoring, or remote data transfer.

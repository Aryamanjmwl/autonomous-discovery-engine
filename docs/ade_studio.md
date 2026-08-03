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

## New-User Local App Quickstart

Use PowerShell from the repository root. Install the existing backend
development and Studio extras:

```powershell
pip install -e ".[dev,studio]"
```

Verify the local backend workflows and generate deterministic demo inputs:

```powershell
python scripts/verify_local.py
python scripts/create_temporal_demo_data.py
python scripts/verify_temporal_demo.py
```

Install frontend packages once:

```powershell
Set-Location apps/studio/frontend
npm install
Set-Location ../../..
```

Start the backend in terminal 1:

```powershell
.\scripts\start_studio_backend.ps1
```

Start the frontend in terminal 2:

```powershell
.\scripts\start_studio_frontend.ps1
```

Open `http://localhost:3000`. The backend health endpoint is
`http://127.0.0.1:8765/health`; it reports the service status, ADE version,
local-only mode, Technical Preview label, supported workflows, and the
human-review requirement. It does not report invented uptime, runtime metrics,
or monitoring state.

The startup helpers resolve the project root automatically, check prerequisites,
and run the existing commands. They do not install dependencies. The manual
equivalents are:

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

### Complete a local review loop

1. Open Run and enter `data/raw/demo_images` as the local image folder path.
2. Submit the image-folder local run, then follow its exact queued or running
   state on the Runs screen.
3. Choose Open in Reports, then inspect its candidate anomalies and candidate
   concepts on Reports and Findings.
4. On Findings, mark a candidate useful, not useful, or needing review and
   optionally save a reviewer note.
5. For a temporal local run, enter
   `data/raw/temporal_demo/scene_revisit_shift/manifest.json`, select
   `adjacent_difference`, submit, and open the generated report.
6. Review candidate temporal changes and save local reviewer feedback where
   appropriate.

Input paths must exist on the machine running the ADE backend. Browser upload,
drag-and-drop import, and server filesystem browsing are not implemented. Studio
job history is stored locally in `data/reports/studio_jobs.json` using atomic
file replacement. Feedback is append-only local JSONL at the configured feedback
path. Outputs are
review-prioritization signals and require human review.

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
- `POST /api/studio/runs/{job_id}/cancel`

Jobs move through `queued`, `running`, `succeeded`, `failed`, or `cancelled`,
and their state is persisted after every transition. Submission returns HTTP 202
without holding the request handler open; a bounded two-thread local executor
runs accepted work. Queued jobs cancel before execution. Running jobs record a
cooperative cancellation request and become cancelled when the current workflow
call returns. A queued or running job found when the backend restarts is retained
and marked failed with an interruption message. ADE never presents interrupted
or cancelled work as completed evidence.

Every new job also records a versioned run manifest containing the ADE version
and the complete normalized request after API defaults are applied. Existing
v1.0 and v1.1 job files migrate automatically. These fields record request
provenance; they do not claim to fingerprint dataset contents or snapshot the
resolved configuration file. Image-folder requests accept `input_path`, optional
`output_name`, optional `config_path`, and optional `run_label`. Temporal requests accept
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
provide an optional label and patch size. Accepted jobs are polled while active;
queued and running jobs expose a cancellation control. Validation or workflow
failures show the real backend error.

The Runs screen lists exact local job records with status, timestamps, manifest
version, ADE version, normalized request parameters, warnings, errors, report
paths, artifact paths, and the human-review requirement. Successful jobs can refresh report discovery and open
the generated JSON report through the existing report detail route when the job
returns one. Completed and failed records remain available after a backend restart.

Paths refer to the machine running the ADE backend. There is no browser upload,
server filesystem picker, drag-and-drop transfer, or remote download. The local
job store survives a normal backend restart; it is not a shared or remote store.

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
Run history and feedback are durable local files; feedback remains append-only
JSONL. This does not provide a worker queue or distributed execution. Stage 7C
adds no cloud/SaaS service, account system, browser upload, continuous
monitoring, or remote data transfer.

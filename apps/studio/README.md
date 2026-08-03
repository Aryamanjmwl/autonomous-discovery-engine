# ADE Studio

ADE Studio is the local-first interactive app layer for ADE. It combines a
Next.js frontend under `apps/studio/frontend` with a small local Python API
under `ade.studio` so reviewers can inspect local runs, candidate anomalies,
candidate concepts, possible patterns, evidence, review status, novelty scores,
and confidence scores.

The current connected Technical Preview supports the local visual/image-folder
workflow first. It can call the local ADE engine, generate Markdown/JSON
reports, validate reports, and export HTML. If the backend is unavailable, the
frontend falls back to mock preview data. Findings shown in either mode are
candidate findings and require human review.

## Local App Quickstart

Run these commands from the repository root in PowerShell:

```powershell
pip install -e ".[dev,studio]"
python scripts/verify_local.py
python scripts/create_temporal_demo_data.py
python scripts/verify_temporal_demo.py
Set-Location apps/studio/frontend
npm install
Set-Location ../../..
```

Start two terminals:

```powershell
.\scripts\start_studio_backend.ps1
```

```powershell
.\scripts\start_studio_frontend.ps1
```

Open `http://localhost:3000`. Check
`http://127.0.0.1:8765/health` if connected mode is unavailable. The health
response contains real service identity and capability fields only; it does not
claim uptime or monitoring state.

The helper scripts do not install dependencies. Their manual equivalents are:

Terminal 1, from the repository root:

```powershell
pip install -e ".[studio]"
python -m ade.studio.api --host 127.0.0.1 --port 8765
```

Alternative when `uvicorn` is installed:

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

The frontend uses `NEXT_PUBLIC_ADE_API_URL` and defaults to
`http://127.0.0.1:8765`.

## First Local Run and Review

- On Run, submit `data/raw/demo_images` as an image-folder path.
- For temporal analysis, first generate the demo data, then submit
  `data/raw/temporal_demo/scene_revisit_shift/manifest.json` with
  `adjacent_difference`.
- After success, use Open in Reports and inspect only the real generated report.
- Open Findings to mark a candidate useful, not useful, or needing review and
  optionally add a local reviewer note.

Paths refer to the backend machine. There is no browser upload or filesystem
picker. Run history is persisted in `data/reports/studio_jobs.json`. Feedback
uses the configured append-only local JSONL store. Candidate anomalies,
candidate concepts, and candidate temporal changes require human review.

The existing frontend posts JSON to `POST /api/studio/analysis`. The `input_path` value
can be an absolute Windows path such as `D:\ADE\ade\data\raw\demo_images` or a
repo-relative path such as `data/raw/demo_images`:

```json
{
  "input_path": "data/raw/demo_images",
  "workflow": "visual",
  "output_name": "studio_report.md"
}
```

## Stage 7A Local Run API

The local backend now provides synchronous job endpoints for existing ADE
workflows:

- `POST /api/studio/runs/image-folder`
- `POST /api/studio/runs/temporal`
- `GET /api/studio/runs`
- `GET /api/studio/runs/{job_id}`\n- `POST /api/studio/runs/{job_id}/cancel`

Job history is a durable local, versioned JSON file. Each record includes its
job type, status and timestamps, input summary, validated report/artifact paths,
warnings, safe failure text, and `human_review_required`. Interrupted queued or
running jobs are marked failed on restart and retain no output evidence paths.

Input folders, config files, and temporal manifests must already exist inside
the configured local workspace. External URLs, traversal, missing inputs, and
outputs outside the configured report/artifact roots are rejected. There are no
downloads, filesystem browsing endpoints, shell commands, cloud services, or
continuous monitoring. Outputs remain candidate findings and review-prioritization
signals that require human review.

## Stage 7B Browser Run UI

The Run navigation screen now calls the Stage 7A endpoints directly. It provides
separate forms for image-folder paths and temporal manifest paths, including the
two supported temporal strategies and only backend-supported optional settings.
Paths must exist on the machine running the local ADE backend; they are not
browser uploads.

Submission returns immediately, and the Runs screen refreshes active jobs. The UI
shows backend validation failures without invented percentages or stages. The
Runs screen displays exact persisted job metadata, warnings, errors, and
validated output paths. A successful job refreshes report discovery and can open
its returned JSON report through the existing Reports screen. Completed and
failed records remain available after a backend restart.

This remains a local-only Technical Preview without cloud/SaaS services,
accounts, browser upload, continuous monitoring, satellite integration, or
geospatial registration. Candidate anomalies, candidate concepts, and candidate
temporal changes are review-prioritization signals that require human review.

## Stage 7C Local Review Feedback

The Findings screen now submits reviewer actions to
`POST /api/studio/feedback`. Each request identifies a discovered local report,
stable candidate ID, visual or temporal candidate type, action, and optional
note. The backend validates the report and candidate before appending ADE's
existing local JSONL feedback record.

Available actions are Mark useful, Mark not useful, and Needs review. The UI
shows reviewer-marked useful or reviewer-marked not useful state only after a
successful response; backend errors are displayed without pretending the action
was saved. The Feedback screen reports the configured local store and directs
reviewers to real candidate controls instead of displaying example entries.

Successful run jobs use a returned JSON report path to offer Open in Reports.
When no JSON reference exists, Studio directs the reviewer to the Reports screen
without inventing a URL or report name. Failed jobs remain visually separate and
show their recorded safe error.

Feedback is review-oriented and does not scientifically confirm candidate
findings. Job history and feedback remain separate durable local files; feedback
uses the existing append-only local JSONL store.

Generated report preview assets are served locally through
`GET /api/studio/report-assets/{asset_name}` from `data/reports/assets/`. The
route accepts asset filenames only, blocks path traversal, and is intended for
localhost Technical Preview use.

Generated HTML reports can be opened through
`GET /api/studio/reports/{report_name}/html`. The route accepts local JSON
report filenames such as `demo_report.json` and serves only the sibling HTML
file from `data/reports`.

## Connected UI Contract

When ADE Studio is connected to the local backend, visible controls should be
backed by local ADE data or clearly disabled/reframed. The connected Technical
Preview currently supports:

- refreshing local backend summary, runs, reports, and the selected report
- running local visual/image-folder analysis from a local path
- reading backend runs and reports
- opening generated HTML reports
- copying local report and source paths
- showing honest empty states for feedback editing, benchmarks, and project
  management that are not implemented in Studio yet

Candidate findings remain candidate anomalies or candidate concepts and require
human review.

The package name is `ade-studio`, version `0.1.0`, and the app is private. The
scripts are `dev`, `build`, `start`, `lint`, and `typecheck`.

## Artifact Policy

Do not commit generated frontend artifacts. The root `.gitignore` excludes:

- `apps/studio/frontend/node_modules/`
- `apps/studio/frontend/.next/`
- `apps/studio/frontend/out/`
- `apps/studio/frontend/dist/`
- `apps/studio/frontend/.turbo/`
- `apps/studio/frontend/tsconfig.tsbuildinfo`

## Current Scope

Implemented here:

- Local Studio shell and navigation
- Local backend connection status
- Local visual/image-folder analysis through the ADE engine
- Recent runs and reports from local ADE artifacts
- Mock preview fallback when the backend is unavailable
- ADE v0.1.0 Technical Preview wording
- Candidate-finding review language

Not implemented here:

- Browser file upload
- Remote execution
- Live streaming or hosted dashboard
- Auth, users, database, billing, cloud deployment, or hosted product behavior
- Automated truth claims

Future work may consider browser import and asynchronous job execution while
preserving local execution and explicit human review.




## Optional Advanced Evidence

In connected mode, the Reports screen shows advanced-evidence panels only for valid summaries in a
real ADE JSON report. The default and mock views do not fabricate reference scoring, calibration,
threshold, map, or benchmark values. This Technical Preview treats every such value as optional
review support; candidate findings require human review.

## Connected Temporal Reports

The Reports and Findings screens can display validated temporal reports already generated
by the ADE CLI. Sequence ranges, candidate temporal changes, real patch coordinates, and
artifact fingerprints come directly from local report data. Temporal local runs use explicit
manifest paths; no continuous ingestion, playback, map, or synthetic chart is provided.
Candidate change events require human review.

## Stage 8B Bounded Asynchronous Execution

Studio runs execute outside HTTP request handlers on a local thread pool capped
at two workers. Submission returns an accepted job record immediately. Queued
jobs can be cancelled before execution; running jobs record a cancellation
request and transition to cancelled at the next workflow boundary. Python worker
threads are not force-killed, and cancelled jobs expose no report or artifact
paths as successful evidence. This is a single-process local worker, not a
distributed queue.

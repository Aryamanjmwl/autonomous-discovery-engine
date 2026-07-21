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

## Local Connected Workflow

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

The frontend posts JSON to `POST /api/studio/analysis`. The `input_path` value
can be an absolute Windows path such as `D:\ADE\ade\data\raw\demo_images` or a
repo-relative path such as `data/raw/demo_images`:

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

Next integration work is richer feedback editing, broader adapter workflows,
and deeper report browsing while preserving local execution.




## Optional Advanced Evidence

In connected mode, the Reports screen shows advanced-evidence panels only for valid summaries in a
real ADE JSON report. The default and mock views do not fabricate reference scoring, calibration,
threshold, map, or benchmark values. This Technical Preview treats every such value as optional
review support; candidate findings require human review.

## Connected Temporal Reports

The Reports and Findings screens can display validated temporal reports already generated
by the ADE CLI. Sequence ranges, candidate temporal changes, real patch coordinates, and
artifact fingerprints come directly from local report data. No temporal run form, live
feed, playback, map, or synthetic chart is provided. Candidate change events require
human review.

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


Generated report preview assets are served locally through `GET /api/studio/report-assets/{asset_name}` from `data/reports/assets/`. The route accepts asset filenames only, blocks path traversal, and is intended for localhost Technical Preview use. Findings remain candidate findings and require human review.```json
{
  "input_path": "data/raw/demo_images",
  "workflow": "visual",
  "output_name": "studio_report.md"
}
```

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





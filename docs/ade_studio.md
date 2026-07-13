# ADE Studio Local UI Foundation

ADE Studio is a local UI foundation for ADE v0.1.0 Technical Preview. It lives
in `apps/studio/frontend` and packages the imported prototype as a clean,
private Next.js app named `ade-studio`.

The current Studio UI uses mock data only. It is useful for recruiter demos,
technical discussion, and future reviewer workflow design, but it is not wired
to the ADE CLI or a backend service yet. It does not add cloud hosting, auth,
database storage, billing, production streaming, or hosted product behavior.

## What It Shows

- Local run telemetry
- Candidate anomaly and candidate concept review surfaces
- Possible pattern summaries
- Evidence previews
- Review status controls
- Novelty score and confidence score readouts
- Local reports, benchmark, feedback, and settings screens

All findings are candidate findings and require human review. The UI supports
review-oriented presentation; it does not claim automated truth.

## How To Run Locally

```powershell
cd apps/studio/frontend
npm install
npm run typecheck
npm run build
npm run dev
```

If frontend dependencies are not available locally, the rest of ADE still works
through the existing Python CLI, report validation, HTML export, benchmark, and
verification workflows.

## Relationship To Existing ADE Workflows

The mature ADE workflow remains the local visual/image-folder CLI flow with
Markdown, JSON, and HTML reports. CSV tabular and CSV time-series workflows are
lightweight local foundations with CLI reports. ADE Studio is a presentation
layer foundation that can later read generated local artifacts such as:

- `data/reports/*.json`
- `data/reports/runs/index.json`
- `data/benchmarks/*.json`
- `data/feedback/feedback.jsonl`
- `data/dashboard/index.html`

Generated frontend artifacts are ignored by Git and should not be committed.

## Future Integration Steps

- Load report JSON and run-history files from local ADE outputs
- Render feedback-informed review status from the JSONL feedback store
- Add a local adapter between Studio mock data and ADE report schemas
- Keep reviewer decisions explicit and transparent
- Preserve the local workflow before considering hosted deployment paths

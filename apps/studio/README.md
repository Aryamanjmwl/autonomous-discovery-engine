# ADE Studio

ADE Studio is the first local UI foundation for ADE. It is a Next.js frontend
prototype under `apps/studio/frontend` that demonstrates how reviewers might
inspect local runs, candidate anomalies, candidate concepts, possible patterns,
evidence, review status, novelty scores, and confidence scores.

This package is presentation-only in the current repository. It uses mock data
from `apps/studio/frontend/lib/ade-data.ts`; it does not run ADE analysis,
start a backend service, call a database, or send data to a hosted dashboard.
Findings shown in the UI are candidate findings and require human review.

## Local Commands

From `apps/studio/frontend`:

```powershell
npm install
npm run typecheck
npm run build
npm run dev
```

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
- Mock run telemetry, reports, feedback, benchmarks, and settings screens
- ADE v0.1.0 Technical Preview wording
- Candidate-finding review language

Not implemented here:

- Backend integration with `ade.cli`
- Live streaming or hosted dashboard
- Auth, users, database, billing, cloud deployment, or hosted product behavior
- Automated truth claims

Next integration work is to connect the UI to local ADE report JSON, run
history, feedback JSONL, and dashboard export contracts.

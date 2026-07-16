# Frontend Specification Document

**Application:** ADE Studio
**Version:** 1.0
**Target:** Local Beta
**Last revised:** 2026-07-16

## 1. Purpose

ADE Studio is a research review workspace, not an autonomous monitoring console.
It helps a reviewer start a local run, inspect evidence, understand scoring and
limitations, record a decision, and compare results. Connected data must never
be mixed visually with mock preview content without a persistent mode label.

## 2. Information Architecture

| Area | Primary purpose | Local Beta state |
| --- | --- | --- |
| Overview | Engine state, latest run, candidate counts, limitations | Connected |
| New analysis | Select approved local input, modality, config, and output | Visual connected; expand tabular/time-series |
| Runs | Browse status, provenance, configuration, and artifacts | Connected; add comparison |
| Findings | Review candidate evidence and score breakdown | Connected visual workflow |
| Reports | Browse and export validated report artifacts | Connected |
| Feedback | Create and inspect reviewer decisions | Partial; next critical workflow |
| Benchmarks | Display governed scorecards and resource measurements | Artifact integration required |
| Settings | Local roots, safe limits, API state, and appearance | Mostly presentation |

## 3. Critical User Journeys

### Run and review

1. Confirm **Local Engine Connected** state.
2. Select a supported modality and an input under an approved root.
3. Review the effective configuration and estimated workload.
4. Start analysis and receive a stable run ID.
5. Observe explicit queued/running/succeeded/failed state.
6. Open a candidate and inspect source context, evidence, score components,
   backend identity, warnings, and limitations.
7. Record a structured reviewer decision and optional note.
8. Verify that the decision appears in history without mutating the run result.

### Compare experiments

1. Select two compatible runs.
2. Compare dataset fingerprint, revision, config, backend, runtime, memory, and
   candidate overlap.
3. Display incompatibilities before displaying metric deltas.
4. Export the comparison with its provenance.

## 4. Application States

Every data surface must implement:

- loading skeleton;
- empty state with the exact next action;
- connected state;
- mock preview state with persistent labeling;
- recoverable error with correlation ID;
- stale/incompatible contract state;
- partial-artifact state;
- offline/backend unavailable state.

The UI must not invent connected-mode metrics. Missing values are shown as
“Not available” with context.

## 5. Finding Detail Contract

A finding view includes:

- stable candidate and run identifiers;
- source identifier and spatial/row/time location;
- source context and preview where safe;
- novelty score plus component breakdown and backend version;
- related candidate concept and nearest evidence where available;
- data quality warnings and known limitations;
- human-review-required indicator;
- review history and create-review control;
- links to the versioned report and run manifest.

Confidence is a prioritization signal, not probability of truth. The interface
must not use language such as “confirmed anomaly” unless a human reviewer has
explicitly applied an appropriate domain-defined label.

## 6. Local API Expectations

All JSON responses expose `schema_version`. Errors use a stable envelope:

```json
{
  "schema_version": "1.0",
  "error": {
    "code": "INPUT_PATH_NOT_ALLOWED",
    "message": "The selected path is outside configured dataset roots.",
    "correlation_id": "...",
    "retryable": false
  }
}
```

Required Local Beta endpoints:

- `GET /health`
- `GET /api/studio/summary`
- `GET /api/studio/runs`
- `GET /api/studio/runs/{run_id}`
- `POST /api/studio/analysis`
- `GET /api/studio/reports`
- `GET /api/studio/reports/{report_name}`
- `GET /api/studio/report-assets/{asset_name}`
- `GET /api/studio/feedback`
- `POST /api/studio/feedback`
- `GET /api/studio/benchmarks`

Mutation requests validate content type, origin policy, schema, allowed roots,
and bounded field sizes. API client types are generated from or tested against
the backend contract.

## 7. Design and Accessibility

- Dense technical information uses progressive disclosure rather than tiny text.
- Keyboard navigation and visible focus work for all primary journeys.
- Semantic landmarks, headings, tables, buttons, and form labels are required.
- Color is never the only carrier of run state, severity, or review status.
- Charts and score breakdowns have textual alternatives.
- Motion respects `prefers-reduced-motion`.
- Core workflows target WCAG 2.2 AA and 200% zoom without loss of function.
- Layout supports 1280px desktop as the primary research workspace and remains
  usable at tablet widths; mobile is not a Local Beta priority.

## 8. Frontend Engineering Standards

- TypeScript strict mode; no unchecked API payload assumptions.
- Server data access centralized in a typed client with runtime validation.
- Components separate data loading, state transitions, and presentation.
- Mock preview data is isolated from production paths.
- Stable fixtures cover empty, error, partial, connected, and mock states.
- Unit tests cover transforms and interaction logic; integration tests cover API
  contracts; end-to-end tests cover run, review, and compare journeys.
- Accessibility checks run in CI for critical screens.
- Performance budgets are measured and documented rather than asserted.

## 9. Local Beta Acceptance Criteria

1. Visual analysis can be initiated and reviewed without CLI intervention.
2. Feedback can be created, listed, and tied to stable candidate/run IDs.
3. No hard-coded demonstration values appear in connected mode.
4. API failures and contract mismatches are explicit and recoverable.
5. Run provenance and human-review status are visible on every finding.
6. Typecheck, lint, production build, contract tests, accessibility smoke tests,
   and critical end-to-end tests pass.

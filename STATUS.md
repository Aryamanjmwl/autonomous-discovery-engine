# ADE Status

ADE is a general autonomous discovery platform. The current implementation focuses on visual data. Computer vision is the first supported adapter, not the final scope of the product.

## Done

- Python package scaffold with `src/` layout
- Config system using `configs/default.yaml`
- Synthetic image demo data generator
- Image folder adapter
- Visual input validation and dataset profiling
- Patch extraction
- Deterministic statistical embedding backend
- Novelty scoring
- Candidate anomaly selection
- Candidate concept grouping with bounded consistency and diversity signals
- Structured evidence collection for supporting patches
- Confidence scoring with component breakdowns for review prioritization
- Cautious hypothesis generation
- Markdown discovery report with patch previews
- Structured JSON report with concept evidence bundles and confidence breakdowns
- Dataset profile included in reports and concise run metadata
- Run metadata files
- Run history index
- CLI run listing with optional limit
- Basic tests for config, models, patch extraction, novelty scoring, reports, demo data, and CLI behavior
- Engineering quality checklist covering coding, testing, documentation, artifact, configuration, review, and release standards

## Partially Done

- Internal dataclasses exist, but adapter contracts are still visual-data-oriented.
- Dataset profiling currently covers image folders only.
- Reporting is useful for the visual MVP, but review annotations, user feedback, and richer export formats are not implemented.
- Config supports current pipeline parameters, but broader adapter configuration is not designed yet.
- Run history exists locally, but there is no dashboard, database, user account model, or hosted audit system.

## Not Done

- Video adapter implementation
- Tabular, time-series, log, audio, document, multimodal, or live stream adapters
- Deep visual embedding backend
- Production dashboard
- Subscription platform
- User authentication, hosted storage, billing, or workspace isolation
- Validated scientific, medical, legal, financial, or operational conclusions

## Next Recommended Engineering Steps

1. Keep generated artifacts out of version control.
2. Add explicit adapter interfaces before adding non-visual data types.
3. Add stronger visual feature backends behind the existing representation interface.
4. Add near-match and normal-comparison evidence once baseline/reference selection is designed.
5. Improve report review workflows with human annotations.
6. Add run comparison tools for candidate anomalies and candidate concepts across experiments.
7. Continue documenting original decisions and experiments before public disclosure.
8. Run linting and type checking before a tagged internal release once the development environment includes those optional tools.

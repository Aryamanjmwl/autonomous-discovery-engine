# ADE Status

ADE is a general autonomous discovery platform. The current implementation focuses on visual data. Computer vision is the first supported adapter, not the final scope of the product.

## Done

- Python package scaffold with `src/` layout
- Config system using `configs/default.yaml`
- Synthetic image demo data generator
- Image folder adapter
- Visual input validation and dataset profiling
- Single-scale and configured multi-scale patch extraction
- Deterministic statistical embedding backend
- Strategy-based novelty scoring with global, memory-neighbor, and hybrid modes
- Diversity-aware candidate anomaly selection
- Candidate concept grouping with bounded consistency and diversity signals
- Structured evidence collection for supporting patches
- Lightweight visual memory with NumPy nearest-neighbor retrieval
- Confidence scoring with component breakdowns for review prioritization
- Cautious hypothesis generation
- Markdown discovery report with patch previews
- Structured JSON report with concept evidence bundles, near matches, and confidence breakdowns
- Dataset profile included in reports and concise run metadata
- Run metadata files
- Run history index
- CLI run listing with optional limit
- Local JSONL human-review feedback records for report targets
- Report validation, static HTML export, benchmark, and local verification scripts
- Private-alpha documentation package with CLI, schema, versioning, release checklist, audit, and examples
- Dashboard UX documentation, frontend data contract, design tokens, and phased release plan
- Basic tests for config, models, patch extraction, novelty scoring, reports, demo data, and CLI behavior
- Engineering quality checklist covering coding, testing, documentation, artifact, configuration, review, and release standards

## Partially Done

- Internal dataclasses exist, but adapter contracts are still visual-data-oriented.
- Dataset profiling currently covers image folders only.
- Multi-scale extraction is supported, but the default config intentionally uses one conservative scale.
- Memory is in-process only; persistent memory banks, coreset selection, and vector database backends are not implemented.
- Memory-aware scoring uses the current run's local patch memory, not a validated normal-reference memory bank.
- Reporting is useful for the visual MVP, and local feedback capture exists, but dashboard review queues and richer collaborative review workflows are not implemented.
- Dashboard documentation exists, but no dashboard app is implemented.
- Config supports current pipeline parameters, but broader adapter configuration is not designed yet.
- Run history exists locally, but there is no dashboard, database, user account model, or hosted audit system.
- Private-alpha docs are prepared for technical review, but they are not a production release certification.

## Not Done

- Video adapter implementation
- Tabular, time-series, log, audio, document, multimodal, or live stream adapters
- Deep visual embedding backend
- Persistent vector memory, FAISS integration, or vector database storage
- PatchCore-style normal memory bank scoring
- Production dashboard
- Database-backed review queues or user-specific feedback workflows
- Subscription platform
- User authentication, hosted storage, billing, or workspace isolation
- Validated scientific, medical, legal, financial, or operational conclusions

## Next Recommended Engineering Steps

1. Keep generated artifacts out of version control.
2. Add explicit adapter interfaces before adding non-visual data types.
3. Add stronger visual feature backends behind the existing representation interface.
4. Evaluate useful multi-scale presets on controlled demo and private datasets.
5. Design normal-reference memory banks before adding PatchCore-style anomaly scoring.
6. Add normal-comparison evidence once baseline/reference selection is designed.
7. Improve report review workflows with human annotations.
8. Add run comparison tools for candidate anomalies and candidate concepts across experiments.
9. Continue documenting original decisions and experiments before public disclosure.
10. Run linting and type checking before a tagged internal release once the development environment includes those optional tools.

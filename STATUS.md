# ADE Status

ADE is an adapter-based autonomous discovery platform. The current
private-alpha foundation includes a mature visual/image-folder workflow plus
lightweight adapter foundations where implemented. Findings are candidate
anomalies, candidate concepts, or possible patterns that require human review.

## Current Status

- Private-alpha foundation for local, adapter-based discovery workflows
- Mature visual workflow for local image folders
- Tabular CSV foundation for row-level candidate anomaly and concept review
- Time-series CSV foundation for explicit timestamped CSV workflows
- Video adapter placeholder; no decoded frame workflow yet
- Local human-review feedback through JSONL records
- Dashboard UX docs and frontend contracts; no production dashboard app
- Not production SaaS: no hosted uploads, auth, billing, database, or cloud deployment

## Done

- Python package scaffold with `src/` layout
- Config system using `configs/default.yaml`
- Synthetic image demo data generator
- Synthetic tabular and time-series CSV demo data generators
- Image folder adapter
- Tabular CSV adapter foundation
- Time-series CSV adapter foundation
- Video adapter placeholder
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
- Local review-memory summary and report annotations from human-review feedback
- Report validation, static HTML export, benchmark, local dashboard export, and
  local verification scripts
- Private-alpha documentation package with CLI, schema, versioning, release checklist, audit, and examples
- Local static dashboard export plus dashboard UX documentation, frontend data
  contract, design tokens, and phased release plan
- Basic tests for config, models, patch extraction, novelty scoring, reports, demo data, and CLI behavior
- Engineering quality checklist covering coding, testing, documentation, artifact, configuration, review, and release standards

## Partially Done

- Internal dataclasses exist, but adapter contracts still need more hardening before broader external plugin use.
- Dataset profiling is implemented for image folders, tabular CSV, and time-series CSV; other modalities remain planned.
- Multi-scale extraction is supported, but the default config intentionally uses one conservative scale.
- Memory is in-process only; persistent memory banks, coreset selection, and vector database backends are not implemented.
- Memory-aware scoring uses the current run's local patch memory, not a validated normal-reference memory bank.
- Reporting is useful for the visual MVP, and local feedback capture can inform
  future ranking annotations, but dashboard review queues and richer
  collaborative review workflows are not implemented.
- Local static dashboard export exists, but no dashboard app, dashboard server,
  database-backed review queue, authentication, billing, or hosted deployment is
  implemented.
- Config supports current visual, tabular, and time-series pipeline parameters, but broader adapter configuration is not designed yet.
- Run history exists locally, but there is no database, user account model, or
  hosted audit system.
- Private-alpha docs are prepared for technical review, but they are not a production release certification.

## Not Done

- Video adapter implementation
- Log, audio, document, multimodal, or live stream adapters
- Production tabular database ingestion, joins, or personalization
- Production time-series forecasting, live sensors, streaming, or alerting
- Deep visual embedding backend
- Persistent vector memory, FAISS integration, or vector database storage
- PatchCore-style normal memory bank scoring
- Production dashboard
- Database-backed review queues or user-specific feedback workflows
- Supervised learning or production personalization from feedback
- Subscription platform
- User authentication, hosted storage, billing, or workspace isolation
- Validated scientific, medical, legal, financial, or operational conclusions

## Next Recommended Engineering Steps

1. Keep generated artifacts out of version control.
2. Keep hardening adapter interfaces before adding more non-visual data types.
3. Add stronger visual feature backends behind the existing representation interface.
4. Evaluate useful multi-scale presets on controlled demo and private datasets.
5. Design normal-reference memory banks before adding PatchCore-style anomaly scoring.
6. Add normal-comparison evidence once baseline/reference selection is designed.
7. Improve report review workflows with human annotations.
8. Design reviewer dashboard and concept-memory flows around the local feedback JSONL contract.
9. Add run comparison tools for candidate anomalies and candidate concepts across experiments.
10. Continue documenting original decisions and experiments before public disclosure.
11. Run linting and type checking before a tagged internal release once the development environment includes those optional tools.

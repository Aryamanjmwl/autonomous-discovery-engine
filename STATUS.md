# ADE Status

ADE is an adapter-based autonomous discovery platform. The current
Technical Preview foundation includes a mature visual/image-folder workflow plus
lightweight adapter foundations where implemented. Findings are candidate
anomalies, candidate concepts, or possible patterns that require human review.

## Current Status

- Technical Preview foundation for local, adapter-based discovery workflows
- Mature visual workflow for local image folders
- ADE Studio localhost API integration for synchronous visual/image-folder and
  temporal local runs, in-memory job status, local report reads, and constrained
  report asset/HTML serving
- Schema-versioned visual-engine contracts, strict configuration validation,
  deterministic dataset fingerprints, and integrity-checked manifest codecs
- Immutable, content-addressed visual reference memory with validated NumPy
  vector payloads, canonical JSONL provenance, deterministic coreset selection,
  and exact batched NumPy Euclidean/cosine search
- Deterministic PatchCore-style reference scoring, raw image aggregation,
  spatial maps, coverage evidence, and immutable map artifacts. Scores remain
  uncalibrated review-prioritization signals that require human review.
- Backend-neutral visual representation provider contracts and an exact-output
  compatibility adapter for the existing lightweight deterministic features.
  Deep providers remain optional and disabled; CLIP/custom execution is
  unimplemented.
- An explicitly selected DINOv2 provider foundation with lazy optional imports,
  offline local-model provisioning, bounded float32 encoding, optional L2
  normalization, and stable model provenance. It remains disabled by default
  and is not integrated into CLI reports or Studio.
- Optional CPU FAISS reference search with lazy provisioning, exact-NumPy
  Euclidean/cosine conformance, deterministic tie normalization, and typed
  provenance. Exact NumPy remains the dependency-free default.
- Optional dependency-free fitted calibration and threshold-evaluation APIs
  with identity, empirical-percentile, and minmax methods; explicit,
  percentile, and top-fraction threshold candidates; labeled held-out metrics;
  unlabeled review-workload estimates; and integrity-checked JSON artifacts.
  They remain disabled and outside the default pipeline, Studio, and reports.
- Reproducible visual benchmark validation harness for externally provisioned
  manifests and explicit predictions, including dependency-free AUROC, average
  precision, precision/recall at k, candidate operating points, unlabeled
  workload evaluation, and immutable integrity-checked evaluation artifacts.
  No public datasets are downloaded and no benchmark performance is claimed.
- Tabular CSV foundation for row-level candidate anomaly and concept review
- Time-series CSV foundation for explicit timestamped CSV workflows
- Video adapter placeholder; no decoded frame workflow yet
- Local human-review feedback through JSONL records
- Dashboard UX docs and frontend contracts; no production dashboard app
- Not a hosted product deployment: no hosted uploads, auth, billing, database, or cloud deployment

## Stage 7A Studio Local Run API

The local Studio backend can trigger the existing image-folder and temporal
workflows through job-oriented endpoints. Jobs are synchronous and stored only
in process memory. Successful jobs reference validated reports and immutable
temporal artifacts already compatible with Studio discovery; failed jobs retain
safe error text and no valid output references.

Paths are confined to the configured local workspace, report root, and artifact
root. External URLs, traversal, missing inputs, malformed manifests, downloads,
and arbitrary command execution are rejected or fail cleanly. This remains a
local-only Technical Preview: no
cloud/SaaS backend, accounts, continuous monitoring, satellite integration, or
geospatial registration. All candidate findings are review-prioritization
signals and require human review.

## Stage 7B Studio Browser Run UI

ADE Studio can now start image-folder and temporal local runs from the browser
through the Stage 7A endpoints. Users enter paths that exist on the ADE backend
machine; no browser upload or filesystem picker is presented. Temporal controls
match the supported adjacent and baseline difference strategies.

The Runs screen reads exact backend job records and displays their status,
timestamps, input summary, warnings, errors, validated report/artifact paths,
and human-review requirement. Synchronous submissions use submitting,
completed, and failed presentation without estimated progress. Successful jobs
refresh existing report discovery and open returned JSON reports through the
Reports screen.

Stage 7B adds no cloud/SaaS backend, accounts, continuous monitoring, satellite
integration, or geospatial registration. Outputs remain candidate anomalies,
candidate concepts, or candidate temporal changes that require human review.

## Stage 7C Studio Review Feedback and Run-Result Polish

Studio now records real local review actions for candidate anomalies, candidate
concepts, and candidate temporal changes. The localhost feedback endpoint
validates each report and stable target ID, maps Studio actions to ADE's existing
feedback labels, and appends the established `ReviewFeedback` record to the
configured JSONL store.

Findings exposes Mark useful, Mark not useful, Needs review, and an optional
note. Saved labels appear only after backend confirmation. The Feedback screen
uses real store counts and paths rather than example feedback entries.
Reviewer-marked useful and reviewer-marked not useful are local review state;
they do not scientifically confirm findings.

Successful jobs offer Open in Reports only when a returned JSON output provides
a real report name. Failed jobs retain their safe error and do not present
successful outputs. Job history remains newest-first and process-local to the
backend session, while feedback remains append-only local JSONL. No cloud/SaaS
backend, accounts, uploads, continuous monitoring, satellite integration, or
geospatial registration were added.

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
- Technical Preview documentation package with CLI, schema, versioning, release checklist, audit, and examples
- Local static dashboard export plus dashboard UX documentation, frontend data
  contract, design tokens, and phased release plan
- Basic tests for config, models, patch extraction, novelty scoring, reports, demo data, and CLI behavior
- Engineering quality checklist covering coding, testing, documentation, artifact, configuration, review, and release standards

## Partially Done

- Internal dataclasses exist, but adapter contracts still need more hardening before broader external plugin use.
- Dataset profiling is implemented for image folders, tabular CSV, and time-series CSV; other modalities remain planned.
- Multi-scale extraction is supported, but the default config intentionally uses one conservative scale.
- The exploratory pipeline still uses its existing in-process memory. Persistent
  reference memory and scoring are separate typed APIs and are not wired into
  the legacy exploratory execution path.
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
- Technical Preview docs are prepared for technical review, but they are not a production release certification.

## Not Done

- Video adapter implementation
- Log, audio, document, multimodal, or live stream adapters
- Production tabular database ingestion, joins, or personalization
- Production time-series forecasting, live sensors, streaming, or alerting
- Deep visual embedding backend
- Persistent vector memory, FAISS integration, or vector database storage
- Pipeline/Studio/report integration for optional fitted calibration and
  threshold candidate evaluation
- Public benchmark dataset provisioning, qualification, and performance claims
- Production dashboard
- Database-backed review queues or user-specific feedback workflows
- Supervised learning or production personalization from feedback
- Hosted commercial platform
- User authentication, hosted storage, billing, or workspace isolation
- Validated scientific, medical, legal, financial, or operational conclusions

## Next Recommended Engineering Steps

1. Keep generated artifacts out of version control.
2. Keep hardening adapter interfaces before adding more non-visual data types.
3. Integrate Stage 1 visual requests and reproducibility manifests around the
   existing statistical pipeline without changing its scoring behavior.
4. Add explicit, offline-provisioned deep representation backends only after
   capability and reproducibility conformance tests are defined.
5. Evaluate useful multi-scale presets on controlled demo and private datasets.
6. Connect explicitly provisioned representation backends only after
   reproducibility conformance tests.
7. Fit calibration from held-out validation data and establish public
   benchmark/evaluation gates.
8. Improve report review workflows with human annotations.
9. Design reviewer dashboard and concept-memory flows around the local feedback JSONL contract.
10. Add run comparison tools for candidate anomalies and candidate concepts across experiments.
11. Continue documenting original decisions and experiments before public disclosure.

## Stage 5A temporal visual foundation

- Typed observation-sequence, alignment, score, event, summary, provenance,
  patch-evidence, and result contracts are implemented.
- Strict canonical manifests provide deterministic timestamp/index ordering, root
  containment, traversal rejection, and optional strict file checks.
- Local adjacent and baseline feature comparison can include computed patch evidence
  and ranks candidate change events that require human review.
- Immutable canonical JSON results have SHA-256 corruption detection.
- Default image-folder analysis, Studio, reports, and dependencies remain unchanged.

## Stage 5B Temporal CLI and Reports

- Strict temporal manifest, artifact, and temporal report validation commands
- Explicit adjacent or baseline temporal analysis with optional computed patch evidence
- Immutable artifact publication followed by deterministic Markdown/JSON reporting
- Static HTML review export without fake charts or heatmaps
- Candidate temporal changes and candidate change events require human review
## Stage 4F Status

Optional artifact-backed visual evidence is integrated into report JSON, Markdown, HTML, and ADE
Studio connected report details. Default runs still omit advanced sections. Reference scoring,
spatial maps, fitted calibration, candidate operating points, and benchmark validation remain
opt-in Technical Preview capabilities, and candidate findings require human review. Temporal change
workflow integration uses the separate explicit Stage 5B CLI and report path.

## Stage 5C Temporal Studio Integration

Connected ADE Studio now discovers valid local temporal reports, verifies their referenced
immutable artifacts, and exposes sequence summaries and candidate change events through the
existing report APIs and UI. Invalid temporal files are omitted with warnings. No temporal
run controls, continuous monitoring, geospatial maps, or fake charts were added; findings remain
review-prioritization signals that require human review.

## Stage 5D Deterministic Temporal Demo

ADE includes a generated local demo with three synthetic observation sequences and canonical
manifests. A separate verifier exercises one complete temporal evidence package without
expanding the normal verifier. Generated images, reports, HTML, and immutable artifacts stay
ignored; no external data, continuous ingestion, registration, or domain-verification claim is introduced.

## Stage 5E Temporal Demo Evidence Documentation

The public temporal evidence guide now connects deterministic local sequence generation,
manifest validation, analysis, immutable artifact validation, JSON/Markdown/HTML reporting,
and connected Studio review. It uses supported commands only, requires real local outputs,
and retains Technical Preview and human-review limitations.

## Stage 6A Visual Technical Preview Release Hardening

Public documentation, CLI help, and Studio copy have been audited against the local-first
Technical Preview boundary. The practical release checklist now covers backend and frontend
verification, the deterministic temporal demo, generated artifact hygiene, public claims,
known limitations, and explicitly excluded v0.1.0 capabilities. Analysis behavior and optional
provider defaults remain unchanged.

## Stage 6B v0.1.0 Technical Preview Preparation

ADE's Python package, runtime package constants, Studio API, and frontend package metadata
are aligned at version `0.1.0`. The canonical release note and changelog describe the current
local-first, review-oriented scope, verification workflow, and known limitations. This stage
prepares release materials only; hosted commercial capabilities remain future work and no
release tag is created by the preparation workflow.

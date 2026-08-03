# ADE Architecture

ADE is an adapter-based autonomous discovery platform. The current
implementation supports a mature visual/image-folder pipeline, a lightweight
CSV tabular foundation, and explicit CSV time-series support. Image folders
remain the most complete adapter; CSV support adds row-level or timestamped
profiling, deterministic features, novelty ranking, concept grouping, and
Markdown/JSON reports.

The long-term architecture is layered so discovery logic does not depend on a single dataset type or a single model backend.

## Product Principle

Discovery with evidence, not only anomaly scores.

ADE should produce candidate findings with traceable evidence and reviewable outputs. Scores help rank findings, but evidence makes findings useful.

## Layers

1. Input Adapter Layer
2. Validation and Profile Layer
3. Representation / Embedding Layer
4. Novelty and Scoring Layer
5. Concept Grouping Layer
6. Evidence and Reporting Layer
7. Human Review Feedback Layer
8. Future Memory / Re-ranking Loop
9. API and Product Layer
10. Enterprise Operations Layer

Current flow:

```text
input adapters
-> validation/profile
-> representation
-> novelty/scoring
-> concept grouping
-> evidence/reporting
-> human review feedback
-> future memory/re-ranking loop
```

## Core Interfaces

- `DataAdapter`: validates an input source, summarizes it, and yields traceable records.
- `EmbeddingBackend`: converts records or patches into comparable representations.
- `ScoringBackend`: ranks embeddings as candidate anomalies or candidate patterns.
- `ClusteringBackend`: groups related candidates into candidate concepts.
- `EvidenceRanker`: selects or summarizes evidence for reviewable findings.
- `ReportRenderer`: exports human-readable and machine-readable report artifacts.

The interfaces are implemented as small structural protocols. They are intended
to protect module boundaries without requiring a large plugin framework.

## Core Models

- `ADERecord`
- `DatasetSummary`
- `EmbeddingResult`
- `DiscoveryRun`
- `Finding`
- `EvidenceItem`
- `ConceptGroup`
- `ReportArtifact`

## Current Visual Pipeline

1. Profile image-folder input.
2. Load valid image metadata.
3. Extract fixed-size image patches.
4. Compute deterministic statistical embeddings.
5. Score candidate anomalies.
6. Group candidate visual concepts.
7. Collect evidence and confidence summaries.
8. Summarize local review feedback as optional review-memory ranking signals.
9. Generate cautious hypotheses.
10. Export Markdown, JSON, preview assets, run metadata, and run index entries.

## Visual Engine Contract Boundary

`ade.visual` now defines schema-versioned request, result, backend capability,
artifact, reproducibility, configuration, dataset-role, error, fingerprint, and
manifest interfaces. This boundary is additive: the existing CLI and Studio
continue to use the current visual pipeline while later stages integrate these
contracts deliberately.

The current contract supports describing exploratory execution. It validates
the prerequisites for reference-based anomaly intent but does not execute that
mode. Dataset fingerprints use canonical relative paths, stable ordering, and
streaming SHA-256 content hashes, with effective configuration and backend
identity included. Strict manifest codecs reject unknown fields and unsupported
schema versions.

See `visual_engine_completion_spec.md` and ADRs 0004 through 0008 for the full
completion gates and deferred scope.

## Immutable Visual Reference Memory

`ade.visual` now provides a persistent normal-reference memory boundary without
changing the exploratory pipeline. A memory version is content-addressed from
the reference dataset/configuration/backend identity, selected record metadata,
float32 vector bytes, coreset provenance, metric, and seed. Creation timestamps
are recorded but excluded from the memory ID.

Each completed version contains `manifest.json`, `vectors.npy`, and
`records.jsonl`. Builds occur in a sibling temporary directory, flush and fsync
payloads, validate hashes/schema/shape/metadata, and atomically publish the
directory. NumPy payloads prohibit pickle and support read-only memory mapping.
Completed versions are immutable and unexpected files or path traversal are
rejected.

The `none` coreset retains every vector within the configured bound.
`deterministic_farthest_first` keeps a bounded subset using incremental minimum
distances and stable ID tie-breaking; it does not allocate a full pairwise
matrix. Exact NumPy Euclidean and cosine search batches queries and provides the
correctness oracle for future accelerated implementations.

The reference scoring layer consumes this memory through exact search. It
supports nearest-neighbour and k-neighbour mean patch distance, maximum and
top-fraction image aggregation, overlap mean/maximum maps, multiscale
mean/maximum fusion, explicit coverage, and deterministic mask-aware Gaussian
smoothing. Uncovered pixels remain `NaN`. Raw float32 maps and coverage are the
authoritative artifacts; normalized PNG previews are presentation evidence.

Scores remain uncalibrated and require human review. DINOv2, FAISS, fitted
calibration, public benchmark validation, and Studio integration remain deferred.

## Visual representation provider boundary

Stage 4A adds `VisualRepresentationProvider`, typed batch/record contracts, and
stable provider metadata without changing the exploratory pipeline. The
lightweight provider delegates to the existing deterministic `EmbeddingEngine`
and preserves its vectors exactly. Future DINOv2, CLIP-like, and domain-model
adapters plug into the same bounded batch boundary and must declare dimension,
dtype, normalization, device, determinism, version, capabilities, and effective
configuration fingerprint. Stage 4B adds an optional DINOv2 runtime adapter
with lazy `torch`/`transformers` loading, explicit local model provisioning,
offline-safe defaults, and an injectable model boundary for framework-free
tests. It is not wired into reports or Studio and never replaces the lightweight
default. See `visual_representation_providers.md`.

## Visual search backend boundary

Stage 4C adds `VisualSearchBackend`, metadata, and `create_search_backend`.
The default wraps unchanged `ExactNumpySearch`; optional CPU FAISS loads only
when selected. FAISS L2/cosine output is normalized to ADE semantics and sorted
by distance, vector ID, and row. Provenance flows into scoring summaries. See
`visual_search_backends.md`.

## Review Memory

The current review-memory loop is local and deterministic. It reads the existing
JSONL feedback store, counts human-review labels by target type and target ID,
and attaches transparent ranking hints to future image reports when enabled.
Positive labels such as `interesting` and `important` can raise review priority;
negative labels such as `false_positive` and `not_useful` can lower it; labels
such as `known_pattern`, `duplicate`, and `needs_more_data` add review context.

This is feedback-informed ranking support, not automated truth, supervised
learning, or production personalization. Candidate anomalies and candidate
concepts still require human review. Future reviewer dashboards and concept
memory should build on this local contract rather than replacing it with hidden
state.

## Current Tabular Pipeline

1. Validate a local `.csv` file.
2. Profile rows, columns, numeric fields, categorical fields, and missing values.
3. Yield stable row-level records.
4. Compute deterministic row-level features from numeric scaling, missing-value
   indicators, categorical rarity, and completeness.
5. Score candidate row anomalies by distance from the tabular feature center.
6. Group candidate rows into simple reason-based candidate concepts.
7. Export Markdown, JSON, run metadata, and run index entries.

The tabular path is intentionally row-level only. It does not apply
time-series semantics, supervised learning, relational joins, or database
ingestion.

## Current Time-Series Pipeline

1. Validate a local `.csv` file in explicit time-series mode.
2. Detect or use a configured timestamp column.
3. Profile rows, time range, numeric signal columns, missing timestamps,
   malformed timestamps, duplicate timestamps, and sampling intervals.
4. Yield stable timestamped records.
5. Compute deterministic point/window-style features from normalized signal
   values, missing indicators, deltas, rolling summaries, spike indicators,
   time-gap indicators, and completeness.
6. Score candidate unusual points by distance from the time-series feature
   center.
7. Group candidate points into simple reason-based candidate concepts.
8. Export Markdown, JSON, run metadata, and run index entries.

The time-series path is intentionally lightweight. It does not include
forecasting, streaming ingestion, production alerting, supervised learning, or
database ingestion.

## Extension Points

Future adapters should implement `DataAdapter` and keep data loading separate
from discovery logic. The current image, tabular CSV, and time-series CSV
adapters follow that boundary: they validate inputs and yield records without
running anomaly scoring inside the adapter.

Adapters are the planned expansion route for sensor streams, audio, satellite
imagery, logs/events, scientific instrument data, tabular data, time-series
data, and future streaming pipelines. A modality should be described as
implemented only after it has an adapter, validation/profile behavior,
representation strategy, discovery/report contract, and tests.

Future embedding backends should implement `EmbeddingBackend` behind the same
boundary used by the current deterministic visual backend. CLIP, DINOv2, custom
satellite encoders, or medical research encoders can be added later as optional
backends without making them default dependencies.

Scoring, clustering, evidence ranking, and report rendering are separate
contracts so candidate ranking can evolve independently from evidence
presentation. ADE should continue to produce candidate findings with traceable
evidence rather than only returning anomaly scores.

## Backend Selection

The current discovery registry supports lightweight scoring backends selected
by `discovery.scoring_backend`: centroid distance, nearest-neighbor distance,
and robust z-score distance. The default remains centroid distance for backward
compatibility.

The current clustering backend is a threshold-based concept grouper selected by
`discovery.clustering_backend`. Backend names are validated when configuration
is loaded, so unsupported names fail before the pipeline starts processing data.

## Current Boundaries

The current implementation includes image-folder inputs, plain CSV tabular
inputs, and explicit timestamped CSV time-series inputs. Video has a placeholder
adapter only. ADE does not currently include production video processing, audio,
document, log/event, sensor stream, live satellite feed, database, live-stream,
forecasting, or operational monitoring adapters. Deep learning backends and
enterprise storage are planned extension points, not current capabilities.

Heavy model dependencies remain deferred. DINOv2, FAISS, PatchCore, persistent
reference-vector payloads, calibration fitting, anomaly maps, and reference-
mode scoring are not implemented by the Stage 1 contract foundation.

## Optional Calibration and Threshold Evaluation

Stage 4D adds a library-only boundary after raw/reference scoring. Identity,
fitted empirical-percentile, and fitted minmax transforms are dependency-free;
none changes the default pipeline. Threshold candidates support explicit,
percentile, and top-fraction strategies. Complete labeled held-out data enables
confusion counts and denominator-safe precision, recall, and F1. Unlabeled or
partially labeled inputs produce review-workload metrics only. Canonical JSON
artifacts carry SHA-256 validation and full calibration/evaluation provenance.
Every operating point remains a review-prioritization signal that requires
human review.

## Visual Benchmark Validation Harness

Stage 4E evaluates explicit sample-level predictions against a versioned
benchmark manifest for an externally provisioned dataset. Canonical manifests
declare deterministic splits, normal/anomaly/unknown labels, relative image and
optional mask paths, metadata, and optional checksums. The dependency-free
metric layer provides labeled held-out AUROC, average precision, precision@k,
recall@k, and candidate operating-point metrics where valid. Unknown-only data
produces review-workload metrics instead. Integrity-checked evaluation artifacts
retain prediction, manifest, configuration, and dataset provenance. No dataset
download, pipeline execution, or default backend selection occurs here.

## Temporal Visual Change Foundation

Stage 5A adds an optional library boundary for manifest-driven observation sequences.
It compares adjacent observations or each observation with the first using existing
deterministic statistical features, with optional computed patch evidence. Canonical
result artifacts are content-addressed and SHA-256 validated. This local, offline path
is separate from default image-folder execution; candidate change events require
human review. It provides no registration, continuous feed, cloud, or monitoring subsystem.

Stage 5B adds an explicit CLI and a separate temporal report boundary. The CLI strictly
loads a manifest, computes adjacent or baseline candidate change events, publishes and
validates the immutable Stage 5A artifact, then emits Markdown and deterministic JSON.
Temporal HTML contains review metadata and patch coordinates only when computed evidence
exists. Normal image-folder dispatch is unchanged.

## Optional Report Evidence Integration

The report layer may carry artifact-backed summaries for reference scoring, spatial anomaly maps,
fitted calibration, candidate operating points, and benchmark validation. These keys are additive
and optional, so the default pipeline and existing reports remain unchanged. The validator checks
present summaries before ADE Studio exposes them. Benchmark summaries describe local validation
artifacts rather than guarantees, and calibrated scores are not universal probabilities.

## Temporal Studio Integration

Stage 5C reuses the existing report list and detail endpoints. Discovery classifies a JSON
document as temporal only by its Stage 5B report type, validates the report, resolves its
artifact within configured local workspace roots, and revalidates artifact integrity.
Invalid reports are omitted with diagnostics. Connected UI projections are derived from
those validated fields and do not create monitoring, timeline, chart, or map state.

Stage 5D adds only a deterministic local fixture generator and an isolated smoke verifier.
It exercises the same manifest, CLI, artifact, report, and HTML boundaries as user-provided
sequences without changing runtime defaults or introducing external data.

## Studio Local Run Boundary

Stage 7A adds a synchronous, local job boundary around the existing image-folder
and temporal workflow functions. A thread-safe registry persists queued,
running, succeeded, and failed states through atomic local file replacement.
Interrupted jobs are marked failed on restart. This is not a background queue or worker
system.

Request validation has two layers. Schemas reject external URLs, traversal,
unknown fields, invalid strategies, and invalid evidence limits. Canonical path
resolution then confines inputs/config/manifests to the configured local
workspace, reports to the report root, and temporal artifacts to the artifact
root. The service calls internal Python workflows directly and validates their
reports/artifacts before attaching paths to a successful job. A failed job has
empty output lists.

The existing CLI dispatch and report discovery formats are unchanged. Studio
can discover reports produced by these runs through the same validated report
endpoints. This Technical Preview boundary has no cloud/SaaS services, accounts,
downloads, arbitrary command execution, continuous monitoring, satellite integration,
or geospatial registration. Candidate anomalies, candidate concepts, and
candidate temporal changes require human review.

Stage 7B adds only a browser client for this boundary. Typed client functions
submit the two supported job requests and read job lists/details through the
configured localhost base URL. The Run screen sends local path strings; it does
not read files in the browser or offer a filesystem picker. Because Stage 7A is
synchronous, the UI represents request submission and the returned terminal job
state without estimating progress.

The Runs screen renders job fields returned by the backend. A JSON report name
is derived only from an actual validated output report path before the existing
report detail flow is used. Report discovery remains the source of report and
finding content, so the browser does not synthesize candidate findings.

## Studio Review Feedback Boundary

Stage 7C exposes one localhost feedback endpoint over the established
`ReviewFeedback` and `FeedbackStore` contracts. Visual candidates reuse the same
report validation and target lookup as the CLI. Temporal candidates first pass
the existing temporal report and artifact validation boundary, then match a real
candidate event ID. Records remain append-only JSONL at the configured Studio
feedback path.

The API accepts Studio-oriented actions and maps them to established labels:
`useful` to `interesting`, `not_useful` to `not_useful`, and `needs_review` to
`needs_more_data`. The existing record fields remain unchanged; `temporal` is an
additive target type for candidate temporal changes. The reviewer identity is
the explicit local value `studio-local`.

The browser keeps saved actions only after a successful append response. It
does not infer prior feedback records because no feedback-history endpoint is
introduced. Feedback is local review state, not evidence that a candidate is correct.
In-memory Studio job history and persistent local JSONL feedback have separate,
explicit lifetimes.

## Studio Local App Onboarding

Stage 7D adds no runtime service or analysis boundary. Two PowerShell helpers
resolve the repository root, validate already-installed prerequisites, and start
the existing localhost backend or Next.js development frontend. Dependency
installation remains an explicit user step.

The established `/health` endpoint is the onboarding status contract. It
returns service identity, ADE version, local-only Technical Preview mode,
supported workflows, and the human-review requirement. It intentionally omits
uptime, load, progress, and monitoring fields.

The documented local app loop is: verify the backend, generate local demo
inputs, start both services, submit a local run using a backend-machine path,
open its validated report, inspect candidate findings, and append local review
feedback. Browser import, asynchronous execution, hosted identity, and managed
service operation remain future boundaries.

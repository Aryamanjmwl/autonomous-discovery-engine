# ADE: Autonomous Discovery Engine

[![CI workflow](https://img.shields.io/badge/CI-GitHub%20Actions-informational)](.github/workflows/ci.yml)
[![Python](https://img.shields.io/badge/Python-%3E%3D3.11-blue)](pyproject.toml)
[![Status](https://img.shields.io/badge/Status-Technical%20Preview-yellow)](docs/releases/v0.1.0-preview.md)
[![License](https://img.shields.io/badge/License-see%20LICENSE.md-lightgrey)](LICENSE.md)

Most AI tools answer known questions. ADE helps surface candidate patterns,
anomalies, and concepts you may not know to ask for yet.

ADE is an adapter-based autonomous discovery platform for local exploratory
data review. It is designed to surface candidate anomalies, candidate concepts,
and possible patterns with evidence so a human reviewer can decide what is
worth deeper investigation.

Core principle: discovery with evidence, not only anomaly scores.

## What ADE Does Today

The current local Technical Preview is strongest on the visual/image-folder
workflow. It also includes lightweight CSV tabular and CSV time-series
workflows with local CLI reports, local JSON/Markdown/HTML report artifacts,
run history, benchmark support, human-review feedback, review-informed ranking
signals, and a static local dashboard export. Outputs are review aids, not
automated truth.

ADE Studio is a local-first interactive app layer under `apps/studio/frontend`
with a small local Python API under `ade.studio`. It connects to the local ADE
engine for the visual/image-folder workflow and falls back to mock preview data
when the backend is unavailable.

All candidate anomalies, candidate concepts, and possible patterns require
human review.

## Try It Locally

Run the full local verification workflow:

```bash
python scripts/verify_local.py
```

Run the visual demo workflow:

```bash
python scripts/create_demo_data.py
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md
python -m ade.cli --validate-report data/reports/demo_report.json
python -m ade.cli --export-html-report data/reports/demo_report.json --output data/reports/demo_report.html
python -m ade.cli --export-local-dashboard --output data/dashboard
```

Temporal visual change analysis is a separate, explicit manifest-driven workflow:

```powershell
python -m ade.cli --validate-temporal-manifest data/temporal/manifest.json
python -m ade.cli --temporal-manifest data/temporal/manifest.json `
  --temporal-output data/reports/temporal_report.md `
  --temporal-strategy adjacent_difference
python -m ade.cli --validate-temporal-report data/reports/temporal_report.json
```

It produces candidate temporal changes for human review and does not alter default
image-folder analysis. See `docs/visual_temporal_change_detection.md` for manifest,
artifact-validation, optional patch-evidence, and HTML-export details.

Run ADE Studio in two terminals:

```bash
pip install -e ".[studio]"
python -m ade.studio.api --host 127.0.0.1 --port 8765
cd apps/studio/frontend
npm run dev
```

## Demo Outputs

Generated demo artifacts stay local and are ignored by Git:

- Markdown report: `data/reports/demo_report.md`
- JSON report: `data/reports/demo_report.json`
- HTML report: `data/reports/demo_report.html`
- Run history: `data/reports/runs/index.json`
- Benchmark output: `data/benchmarks/demo_benchmark.json`
- Local dashboard export: `data/dashboard/index.html`

Helpful docs:

- [Sample outputs](docs/sample_outputs.md)
- [Local dashboard export docs](docs/dashboard/dashboard_product_spec.md)
- [ADE Studio local UI foundation](docs/ade_studio.md)
- [Demo script](examples/demo_script.md)
- [Demo asset guidance](docs/demo_assets.md)

## Implemented vs Planned

| Status | Capabilities |
| --- | --- |
| Implemented | Visual/image-folder local workflow; Markdown, JSON, and HTML reports; report validation; run history; benchmark script; local dashboard export; human-review feedback; review-informed memory signals; local verification and CI |
| Foundation | CSV tabular workflow; CSV time-series workflow; adapter interfaces; dashboard contracts |
| Planned | Audio; live satellite feeds; sensor streams; production streaming; hosted dashboard; auth/users; database/backend service; enterprise deployment |

Current limitations: ADE does not process audio, live satellite feeds, sensor
streams, or production streams; it does not provide cloud hosting, auth,
database-backed review queues, billing, production personalization, or
enterprise deployment. All candidate findings require human review.

## Release Status

ADE v0.1.0 Technical Preview is prepared for local demo review and manual
release tagging. It is not a hosted product release.

- [v0.1.0 Technical Preview release notes](docs/releases/v0.1.0-preview.md)
- [Portfolio case study](docs/portfolio_case_study.md)
- [CV/project wording](docs/cv_project_description.md)
- [Modality capability matrix](docs/modality_capability_matrix.md)
- [License notice](LICENSE.md): currently all rights reserved; choose a public
  license before promoting the repository as open source.

## What Problem ADE Solves

Most AI tools are built around known questions: classify this image, summarize this text, forecast this metric, or answer this prompt. Many real-world datasets contain useful signals that users do not yet know to ask about.

ADE is designed for exploratory discovery workflows where the user may not know the exact target in advance. It helps scan data, surface unusual examples, group recurring patterns, collect evidence, and generate cautious reports that can guide deeper expert investigation.

## Why ADE Is Different

ADE is intended to be a discovery assistant, not a single-purpose prediction model. Its architecture separates data adapters, preprocessing, representation, novelty scoring, concept grouping, evidence collection, reasoning, reporting, and run tracking.

This modular design allows ADE to grow across domains and data types without being locked to one model, one industry, or one question format. Future implementations can add new dataset adapters and replace the current placeholder visual embedding engine with stronger domain-specific models while keeping the review-oriented discovery workflow intact.

The codebase exposes small pluggable contracts for data adapters, embedding
backends, scoring backends, clustering backends, evidence ranking, and report
rendering. These contracts are intentionally lightweight: they prepare ADE for
future CLIP, DINOv2, custom visual models, and non-visual adapters without
adding those heavy dependencies to the current prototype.

## Current Prototype Status

This version is a local technical preview MVP. It demonstrates a visual-first
end-to-end workflow and lightweight CSV tabular/time-series foundations without
using advanced AI, proprietary models, or deep learning.

Implemented / working inputs:

- Image folders

Foundation / partial inputs:

- CSV files for lightweight row-level tabular discovery
- CSV files with explicit time-series mode for timestamped point/window discovery
- Video adapter placeholder with no decoded frame workflow yet

Planned future adapter targets:

- Videos
- Logs
- Audio
- Sensor streams
- Live satellite feeds
- Scientific instrument data
- Documents
- Multimodal datasets
- Live streams

## Implemented vs Planned

- Implemented / working: visual image-folder workflow, report generation,
  report validation, static HTML export, local human-review feedback,
  benchmark script, and local verification script.
- Foundation / partial: tabular CSV adapter, time-series CSV adapter, and video
  adapter placeholder where present.
- Planned: sensor streams, live satellite feeds, audio input, logs/events,
  scientific instrument data, documents, multimodal datasets, and production
  streaming pipelines.

See `docs/modality_capability_matrix.md` for the current modality status.

## Current MVP Pipeline

The current pipeline performs:

1. Image-folder input validation and dataset profiling
2. Image loading from a local folder
3. Single-scale or configured multi-scale patch extraction
4. Deterministic statistical embeddings
5. Strategy-based novelty ranking
6. Diversity-aware candidate anomaly selection
7. Simple candidate concept grouping
8. Evidence bundle collection
9. Concept consistency and confidence scoring
10. Lightweight visual memory indexing and nearest-neighbor retrieval
11. Local review-memory summarization from human feedback JSONL
12. Cautious hypothesis generation
13. Markdown and JSON discovery report generation

For CSV files, ADE uses a separate lightweight tabular path: CSV validation,
numeric/categorical profiling, deterministic row-level feature extraction,
row-level novelty ranking, simple candidate concept grouping, and Markdown/JSON
reports with tabular metadata.

For timestamped CSV files, ADE supports an explicit lightweight time-series
path with timestamp profiling, numeric signal detection, deterministic
point/window-style features, point-level novelty ranking, simple candidate
concept grouping, and Markdown/JSON reports with time-series metadata.

The embedding system currently uses deterministic lightweight visual statistics: size and aspect ratio features, brightness and contrast summaries, color channel statistics, color histograms, simple texture estimates, and gradient-based edge features. This is intentionally dependency-light so the architecture can later support stronger encoders such as CLIP, DINOv2, or custom domain models behind the same representation boundary.

Discovery backends are selected through configuration. The current lightweight
scoring options are centroid distance, nearest-neighbor distance, and robust
z-score distance. These are deterministic baselines; deep-learning and advanced
indexing backends are intentionally deferred until they can be added as optional
extensions.

## Example Use Cases

ADE is designed to grow into a cross-industry discovery platform. Example future use cases include:

- Individual researchers exploring image or tabular datasets for candidate unknown patterns
- Students learning how anomaly discovery workflows are structured
- Companies scanning operational data for recurring behaviors or unusual events
- Startups testing data-driven product or research hypotheses
- Factories reviewing visual inspection data or industrial sensor streams
- Robotics teams analyzing robot logs, camera feeds, or failure patterns
- Healthcare research teams exploring medical research images for candidate patterns requiring expert review
- Finance and data teams investigating unusual activity, correlations, or predictive signals without treating outputs as financial advice
- Climate and satellite analysts reviewing Earth observation imagery
- Logistics companies searching for recurring delays, routing anomalies, or operational bottlenecks
- Security and monitoring teams reviewing candidate anomalies in monitored data
- Agriculture companies studying crop, field, or sensor patterns
- Space and aerospace organizations exploring satellite, rover, telescope, or simulation data

## What This Version Can Do

- Load images from a folder through the first visual data adapter
- Load CSV files through the first non-visual adapter
- Run explicit time-series discovery on timestamped CSV files
- Profile visual input folders before analysis
- Profile CSV files for row count, column count, numeric/categorical columns, and missing values
- Profile timestamped CSV files for time range, signal columns, duplicate timestamps, missing timestamps, and sampling intervals
- Warn about unsupported files, unreadable images, small datasets, small images, and high estimated patch counts
- Return image path and metadata
- Split images into fixed-size or configured multi-scale patches
- Create deterministic placeholder embeddings from image statistics
- Rank candidate anomalies with global-distance, memory-neighbor, or hybrid scoring
- Select a diverse candidate anomaly set across images, regions, and scales
- Group similar candidate anomalies into candidate unknown concepts
- Collect structured supporting evidence with anomaly IDs, coordinates, ranks, and preview paths
- Retrieve nearest visual matches from a local NumPy-backed embedding memory
- Produce bounded consistency, diversity, and confidence signals for review prioritization
- Generate cautious template-based hypotheses
- Write a Markdown ADE Discovery Report and a structured JSON sidecar report
- Record local human-review feedback for candidate anomalies and candidate concepts
- Summarize prior local feedback as review-informed ranking support in future reports

Current supported image formats are configured in `configs/default.yaml` and include `.jpg`, `.jpeg`, `.png`, `.bmp`, and `.webp`.

## What This Version Cannot Do Yet

- Process videos, live streams, robot logs, audio, documents, multimodal datasets, or industrial sensor data
- Provide production-grade tabular or time-series semantics such as database
  joins, forecasting, live sensors, or streaming alerts
- Use deep learning encoders such as CLIP, DINOv2, medical imaging models, or satellite-specific encoders
- Guarantee that a candidate anomaly is meaningful
- Learn production personalization or supervised truth labels from feedback
- Prove scientific, clinical, operational, or financial conclusions
- Provide medical diagnosis or financial advice
- Replace human experts or domain review
- Securely host user uploads as a subscription platform

## Installation

Use Python 3.11 or newer.

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .[dev]
```

Alternatively:

```bash
pip install -r requirements.txt
pip install -e .
```

## Documentation

Start with `docs/README.md` for architecture, CLI reference, report schema,
dashboard planning docs, release checklist, versioning policy, and technical preview
readiness notes.

The current implementation is adapter-based. Visual discovery is the mature
workflow; CSV tabular and CSV time-series are lightweight foundations where
implemented. Hosted workflows, production dashboards, cloud services, and deep
model backends remain future work unless a specific branch documents and
implements them.

## Demo

Place images in `data/raw`, then run:

```bash
python -m ade.cli --input data/raw --output data/reports/demo_report.md
```

The report will be written to `data/reports/demo_report.md`.

ADE also writes a machine-readable JSON report beside the Markdown report.
For example, this command creates both:

- `data/reports/demo_report.md`
- `data/reports/demo_report.json`

The Markdown report is for human review. The JSON report stores structured
candidate anomalies, candidate unknown concepts, evidence bundles,
nearest-neighbor evidence, confidence breakdowns, optional review-memory
signals, hypotheses, limitations, and the human-review requirement so future
dashboards, APIs, databases, subscription workflows, or comparison tools can
consume the same discovery results.

## Review Memory

ADE stores reviewer labels in a local JSONL feedback store. When review memory
is enabled, future image reports can include a `review_memory_summary` and
candidate-level `review_memory_signal` objects. These signals are simple,
deterministic counts from labels such as `important`, `interesting`,
`false_positive`, `known_pattern`, and `duplicate`.

Review memory is feedback-informed ranking support. It does not replace human
review, does not prove that a candidate anomaly is meaningful, and does not
implement supervised learning or production personalization. Future work may add
a reviewer dashboard and concept memory, with the local JSONL store remaining
the preview source of feedback state for now.

## Generate Demo Data

ADE includes a small synthetic data generator for local testing. It creates simple PNG images with repeated geometric patterns, brightness variation, mild texture, and a few intentionally unusual regions so the prototype has candidate anomalies to rank.

The generated images are programmatic test data only. They are not external datasets and should not be treated as scientific evidence.

```bash
python scripts/create_demo_data.py
```

Then run ADE on the generated image folder:

```bash
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md
```

## CSV Demo Commands

Generate a deterministic tabular CSV:

```bash
python scripts/create_tabular_demo_data.py
```

Run ADE on a CSV file by passing the file path as `--input`:

```bash
python -m ade.cli --input data/raw/demo_tabular/operations.csv --output data/reports/tabular_demo_report.md --modality tabular
```

The current tabular implementation performs row-level discovery only. Findings
are candidate row anomalies and candidate tabular concepts that require human
review.

Generate a deterministic timestamped CSV:

```bash
python scripts/create_timeseries_demo_data.py
```

Run ADE on a timestamped CSV file by explicitly selecting time-series mode:

```bash
python -m ade.cli --input data/raw/demo_timeseries/machine_metrics.csv --output data/reports/timeseries_demo_report.md --modality timeseries --timestamp-column timestamp --entity-column machine
```

See `docs/modality_capability_matrix.md` and `examples/modalities/` for the
current modality status.

The current time-series implementation performs point/window-feature discovery
only. It does not perform forecasting, streaming ingestion, or production
monitoring.

## Python Usage

```python
from pathlib import Path

from ade.cli import run_pipeline

run_pipeline(
    input_dir=Path("data/raw/demo_images"),
    output_path=Path("data/reports/demo_report.md"),
)
```

## Configuration

ADE loads default pipeline settings from:

```text
configs/default.yaml
```

You can also pass the config path explicitly:

```bash
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md --config configs/default.yaml
```

The current config covers settings such as patch size, patch stride, optional
multi-scale patch sizes and strides, maximum candidate anomaly count,
diversity-aware selection settings, concept limits, concept evidence
thresholds, visual memory settings, report version, human-review requirement,
report asset folders, run metadata folders, input validation thresholds,
supported image extensions, and synthetic demo data settings.
These settings are intended to make ADE runs easier to
reproduce and compare as the project grows.

### Multi-Scale Patch Extraction

ADE defaults to one conservative patch scale to keep runtime predictable:

```yaml
preprocessing:
  patch_size: 64
  patch_stride: 64
  patch_sizes:
    - 64
  patch_strides:
    - 64
```

To inspect more than one visual scale, set matching `patch_sizes` and
`patch_strides` lists. Each generated patch receives deterministic scale
metadata such as `patch_size`, `patch_stride`, and `scale_label`.

### Diversity-Aware Candidate Selection

The visual pipeline can avoid filling reports with near-duplicate candidate
anomalies from the same image or region:

```yaml
discovery:
  diversity:
    enabled: true
    min_spatial_distance: 32
    max_per_image: 3
    prefer_multiple_scales: true
```

The selector still starts from novelty ranking. Diversity settings only affect
which candidate anomalies are surfaced for review.

### Novelty Scoring Strategies

ADE supports configurable novelty scoring strategies for the current visual
pipeline:

- `global_distance`: distance from the dataset average embedding
- `memory_neighbor_distance`: distance from nearest neighbors in local visual memory
- `hybrid`: weighted combination of global and neighbor-distance scores

The default uses the lightweight local memory index with a hybrid score:

```yaml
discovery:
  novelty_strategy: "hybrid"
  memory_aware_scoring:
    enabled: true
    neighbor_top_k: 5
    exclude_same_source: false
    weight_global_distance: 0.5
    weight_neighbor_distance: 0.5
```

Each candidate anomaly keeps a JSON-safe score breakdown. These scores are
review-prioritization signals only; they do not prove that a candidate anomaly
is meaningful.

## Visual Memory

The current visual implementation can build a local in-memory index of patch
embeddings during a run. The index uses NumPy and supports Euclidean or cosine
nearest-neighbor retrieval. Reports can include concise nearest visual matches
for candidate concepts when memory is enabled.

This is a lightweight foundation for evidence retrieval, near-match lookup,
future normal comparison retrieval, PatchCore-style memory-bank scoring, and
eventual FAISS or vector database backends. It is not a persistent vector
database and does not use deep learning.

## Input Validation

Before analysis, the current visual implementation profiles the input image folder. The profile records file counts, valid image counts, unsupported files, unreadable files, image size ranges, estimated patch count, and warnings.

Invalid inputs fail with clear CLI errors. Valid inputs with warnings continue, and the warnings are included in the Markdown report, JSON report, and concise run metadata.

## Run Tracking

Each ADE analysis run receives a unique run ID and a small metadata record for traceability. The run metadata includes the input path, Markdown and JSON report paths, basic result counts, pipeline version, timestamp, and the human-review requirement.

Individual run metadata is stored alongside reports:

```text
data/reports/runs/ade_YYYYMMDD_HHMMSS_xxxxxx.json
```

ADE also maintains a lightweight run history index:

```text
data/reports/runs/index.json
```

The index lists compact summaries of previous runs so future review workflows, dashboards, APIs, audits, subscription workspaces, and experiment comparison tools can discover run history without scanning every metadata file manually.

List previous runs from the terminal:

```bash
python -m ade.cli --list-runs
```

Show only the most recent runs:

```bash
python -m ade.cli --list-runs --limit 5
```

## Human Review Feedback

ADE findings are candidate findings that require human review. Local reviewers
can attach structured labels to candidate anomalies and candidate concepts in a
generated JSON report.

```bash
python -m ade.cli --add-feedback data/reports/demo_report.json --target-type anomaly --target-id anomaly-0001 --label interesting --notes "Local review note" --reviewer local
python -m ade.cli --add-feedback data/reports/demo_report.json --target-type concept --target-id concept-001 --label known_pattern --notes "Known recurring pattern" --reviewer local
python -m ade.cli --list-feedback
```

Supported feedback labels are `interesting`, `known_pattern`,
`false_positive`, `duplicate`, `important`, `not_useful`, and
`needs_more_data`. Feedback is stored locally at
`data/feedback/feedback.jsonl` by default and is ignored by Git. This is a
foundation for future review queues, concept memory, and false-positive review;
those systems are not implemented yet.

## Local Dashboard

ADE can generate a lightweight static dashboard from existing local run history
and JSON reports:

```bash
ade dashboard
```

The dashboard is written to `data/reports/dashboard/index.html` by default and
the command prints a local `file://` URL. It shows run history, report paths,
dataset summaries, top candidate findings, candidate concept groups, evidence
items, and available preview assets.

ADE can also export a broader local dashboard-style artifact summary without
running analysis:

```bash
python -m ade.cli --export-local-dashboard --output data/dashboard
```

This writes `data/dashboard/index.html` and `data/dashboard/dashboard_data.json`
from existing local reports, run history, benchmark JSON, static HTML reports,
and feedback JSONL when those files are present. Missing folders are handled as
empty states. Generated dashboard output is ignored by Git.

This is a local review tool only. It does not add authentication, uploads,
multi-user support, a database, or production hosting assumptions.

## Repository Structure

```text
ade/
├── configs/                 # Default pipeline configuration
├── data/                    # Local raw, processed, embedding, and report folders
├── docs/                    # Architecture, invention, decision, and experiment notes
├── scripts/                 # Demo helpers
├── src/ade/                 # ADE Python package
│   ├── adapters/            # Data input interfaces
│   ├── preprocessing/       # Patch extraction and future transforms
│   ├── representation/      # Placeholder embeddings and future encoders
│   ├── memory/              # Local vector memory and nearest-neighbor retrieval
│   ├── feedback/            # Local JSONL human-review feedback records
│   ├── storage/             # Metadata and embedding stores
│   ├── discovery/           # Novelty, concepts, evidence, and confidence
│   ├── reasoning/           # Cautious hypothesis generation
│   ├── reporting/           # Markdown and JSON report generation
│   └── cli.py               # Command-line pipeline
└── tests/                   # Basic regression tests
```

Additional project docs:

- `docs/ARCHITECTURE.md`
- `docs/ROADMAP.md`
- `docs/IMPLEMENTATION_PLAN.md`
- `docs/ADAPTER_BACKEND_GUIDE.md`
- `docs/DASHBOARD.md`
- `docs/TABULAR.md`
- `docs/TIME_SERIES.md`
- `docs/ENTERPRISE_READINESS.md`
- `docs/SECURITY_MODEL.md`
- `docs/release_checklist.md`
- `docs/development_workflow.md`
- `docs/research_and_ip_notes.md`
- `docs/engineering_quality.md`
- `CHANGELOG.md`
- `CONTRIBUTING.md`
- `SECURITY.md`
- `STATUS.md`

## Artifact Policy

Generated demo images, reports, report assets, run metadata, run indexes, local feedback records, test temp folders, cache folders, bytecode, and package build metadata should not be committed. The repository keeps `.gitkeep` files only to preserve the intended empty data directories.

## Patent/IP-Aware Development

ADE is original, self-made scaffold code. It uses common open-source Python libraries as normal dependencies and keeps advanced discovery methods behind replaceable interfaces.

Development notes, experiment records, and technical decisions should be documented in `docs/` so future work has a clear invention trail. Proprietary future methods should be added carefully, documented privately, and reviewed before disclosure.

## Subscription Platform Vision

In the long term, ADE is intended to become a secure subscription-based discovery platform where users can upload different kinds of data, run autonomous discovery pipelines, review candidate discoveries, and receive evidence-backed reports.

The platform vision includes private workspaces, dataset management, configurable discovery pipelines, future visual and non-visual adapters, evidence review tools, exportable reports, and human-in-the-loop workflows for teams and organizations.

## Future Roadmap

- Add robust dataset manifests and richer run comparison
- Add video frame sampling and temporal patch extraction
- Add CSV and time-series adapters
- Add support for industrial sensor data and robot logs
- Add stronger embedding backends behind the existing representation interface
- Add persistent memory backends and normal-reference memory banks
- Add PatchCore-style normal-memory scoring experiments
- Add richer concept clustering and evidence ranking
- Add report exports with review annotations
- Add secure upload, storage, and workspace isolation for a hosted product
- Add human feedback loops for confirming, rejecting, or refining candidate findings

## Human Expert Review Required

All ADE outputs are exploratory candidate findings. Candidate anomalies, candidate unknown concepts, possible relationships, and hypotheses require human expert review before any scientific, clinical, operational, commercial, or financial interpretation.


# ADE: Autonomous Discovery Engine

ADE is an Autonomous Discovery Engine designed to help users discover hidden patterns, anomalies, recurring behaviors, and predictive signals inside their data. Instead of only answering predefined questions, ADE helps users find questions worth asking.

ADE is not only a computer vision tool, not only for NASA, and not only for scientific or aerospace datasets. The long-term goal is a general discovery assistant for individuals, companies, researchers, students, startups, factories, robotics teams, healthcare research teams, finance and data teams, climate and satellite analysts, logistics companies, security and monitoring teams, agriculture companies, space and aerospace organizations, and any user who has data and wants to investigate unknown patterns.

The current repository is an early private research prototype. It produces candidate anomalies, candidate unknown concepts, possible relationships, and hypotheses that require human expert review. ADE is not a final truth machine and does not replace domain experts.

## What Problem ADE Solves

Most AI tools are built around known questions: classify this image, summarize this text, forecast this metric, or answer this prompt. Many real-world datasets contain useful signals that users do not yet know to ask about.

ADE is designed for exploratory discovery workflows where the user may not know the exact target in advance. It helps scan data, surface unusual examples, group recurring patterns, collect evidence, and generate cautious reports that can guide deeper expert investigation.

## Why ADE Is Different

ADE is intended to be a discovery assistant, not a single-purpose prediction model. Its architecture separates data adapters, preprocessing, representation, novelty scoring, concept grouping, evidence collection, reasoning, and reporting.

This modular design allows ADE to grow across domains and data types without being locked to one model, one industry, or one question format. Future implementations can replace the current placeholder embedding engine with stronger domain-specific models while keeping the review-oriented discovery workflow intact.

## Current Prototype Status

This version is a minimal working MVP for image-folder input. It demonstrates the end-to-end discovery pipeline without using advanced AI, proprietary models, or deep learning.

Current supported inputs:

- Image folders

Planned future supported data types:

- Videos
- Satellite images
- Medical research images
- Industrial sensor data
- CSV and time-series data
- Robot logs
- Business datasets
- Live streams

## Current MVP Pipeline

The current pipeline performs:

1. Image loading from a local folder
2. Fixed-size patch extraction
3. Deterministic statistical embeddings
4. Novelty ranking
5. Simple candidate concept grouping
6. Evidence collection
7. Confidence scoring
8. Cautious hypothesis generation
9. Markdown and JSON discovery report generation

The embedding system currently uses simple image statistics such as color means, standard deviations, brightness, and edge density. This is intentionally basic so the architecture can later support stronger encoders for specific domains.

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

- Load images from a folder
- Return image path and metadata
- Split images into fixed-size patches
- Create deterministic placeholder embeddings from image statistics
- Rank candidate anomalies by distance from the dataset average
- Group similar candidate anomalies into candidate unknown concepts
- Collect supporting patches and basic statistics
- Produce a simple confidence score from novelty strength, example count, and cluster consistency
- Generate cautious template-based hypotheses
- Write a Markdown ADE Discovery Report and a structured JSON sidecar report

## What This Version Cannot Do Yet

- Process videos, live streams, CSV files, robot logs, or industrial sensor data
- Use deep learning encoders such as CLIP, DINOv2, medical imaging models, or satellite-specific encoders
- Guarantee that a candidate anomaly is meaningful
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
candidate anomalies, candidate unknown concepts, confidence scores,
hypotheses, evidence summaries, limitations, and the human-review requirement
so future dashboards, APIs, databases, subscription workflows, or comparison
tools can consume the same discovery results.

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
│   ├── storage/             # Metadata and embedding stores
│   ├── discovery/           # Novelty, concepts, evidence, and confidence
│   ├── reasoning/           # Cautious hypothesis generation
│   ├── reporting/           # Markdown and JSON report generation
│   └── cli.py               # Command-line pipeline
└── tests/                   # Basic regression tests
```

## Patent/IP-Aware Development

ADE is original, self-made scaffold code. It uses common open-source Python libraries as normal dependencies and keeps advanced discovery methods behind replaceable interfaces.

Development notes, experiment records, and technical decisions should be documented in `docs/` so future work has a clear invention trail. Proprietary future methods should be added carefully, documented privately, and reviewed before disclosure.

## Subscription Platform Vision

In the long term, ADE is intended to become a secure subscription-based discovery platform where users can upload different kinds of data, run autonomous discovery pipelines, review candidate discoveries, and receive evidence-backed reports.

The platform vision includes private workspaces, dataset management, configurable discovery pipelines, evidence review tools, exportable reports, and human-in-the-loop workflows for teams and organizations.

## Future Roadmap

- Add robust dataset manifests and richer run comparison
- Add video frame sampling and temporal patch extraction
- Add CSV and time-series adapters
- Add support for industrial sensor data and robot logs
- Add stronger embedding backends behind the existing representation interface
- Add richer concept clustering and evidence ranking
- Add report exports with review annotations
- Add secure upload, storage, and workspace isolation for a hosted product
- Add human feedback loops for confirming, rejecting, or refining candidate findings

## Human Expert Review Required

All ADE outputs are exploratory candidate findings. Candidate anomalies, candidate unknown concepts, possible relationships, and hypotheses require human expert review before any scientific, clinical, operational, commercial, or financial interpretation.

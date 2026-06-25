# Development Workflow

This document describes the current ADE development workflow. ADE is a general autonomous discovery platform; the current implementation focuses on visual data.

## Install

Use Python 3.11 or newer.

```bash
pip install -e .[dev]
```

## Run Tests

```bash
pytest
```

## Generate Demo Data

The demo data generator creates synthetic images locally. It does not download external datasets.

```bash
python scripts/create_demo_data.py
```

## Run an Analysis

```bash
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md
```

With an explicit config:

```bash
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md --config configs/default.yaml
```

## List Runs

```bash
python -m ade.cli --list-runs
python -m ade.cli --list-runs --limit 5
```

Run history is read from `data/reports/runs/index.json`.

## Use Config

Default settings live in `configs/default.yaml`. Current settings cover project metadata, patch extraction, discovery limits, reporting behavior, asset folders, run metadata folders, and demo data generation.

CLI arguments can override selected config values such as patch size, stride, and maximum candidate anomalies.

## Git Workflow Guidance

Review generated files before staging changes. Generated artifacts such as demo images, report Markdown, report JSON, report assets, run metadata, caches, and bytecode should stay out of commits.

Recommended manual review steps:

```bash
git status --short
git diff
```

Stage only source, tests, config, and docs that you intentionally changed.

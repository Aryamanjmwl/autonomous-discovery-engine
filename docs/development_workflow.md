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

The current implementation expects an image folder. Before processing, ADE profiles the folder and reports unsupported files, unreadable images, small datasets, small images, and high estimated patch counts as warnings.

With an explicit config:

```bash
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md --config configs/default.yaml
```

The generated Markdown and JSON reports include candidate anomalies, candidate concepts, supporting evidence bundles, concept consistency, confidence breakdowns, cautious hypotheses, and human-review disclaimers. These fields support review and comparison; they are not validated conclusions.

## List Runs

```bash
python -m ade.cli --list-runs
python -m ade.cli --list-runs --limit 5
```

Run history is read from `data/reports/runs/index.json`.

## Use Config

Default settings live in `configs/default.yaml`. Current settings cover project metadata, patch extraction, discovery limits, concept evidence thresholds, reporting behavior, asset folders, run metadata folders, and demo data generation.

CLI arguments can override selected config values such as patch size, stride, and maximum candidate anomalies. Validation settings include supported image extensions, minimum image count, small dataset warning threshold, high patch-count warning threshold, and minimum image dimensions.

## Git Workflow Guidance

Review generated files before staging changes. Generated artifacts such as demo images, report Markdown, report JSON, report assets, run metadata, caches, and bytecode should stay out of commits.

Recommended manual review steps:

```bash
git status --short
git diff
```

Stage only source, tests, config, and docs that you intentionally changed.

## Engineering Quality

Use `docs/engineering_quality.md` as the working checklist for code review, test expectations, documentation quality, artifact policy, configuration changes, and release readiness.

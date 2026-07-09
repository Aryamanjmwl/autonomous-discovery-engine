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

The generated Markdown and JSON reports include candidate anomalies, patch scale metadata, novelty score breakdowns, candidate concepts, supporting evidence bundles, nearest visual matches when memory is enabled, concept consistency, confidence breakdowns, cautious hypotheses, and human-review disclaimers. These fields support review and comparison; they are not validated conclusions.

## List Runs

```bash
python -m ade.cli --list-runs
python -m ade.cli --list-runs --limit 5
```

Run history is read from `data/reports/runs/index.json`.

## Record Human Review Feedback

Feedback labels are local JSONL records for candidate findings that require
human review. Use a real `anomaly_id` or `concept_id` from the generated JSON
report:

```bash
python -m ade.cli --add-feedback data/reports/demo_report.json --target-type anomaly --target-id anomaly_001 --label interesting --notes "Local review note" --reviewer local
python -m ade.cli --add-feedback data/reports/demo_report.json --target-type concept --target-id concept_001 --label known_pattern --notes "Known recurring pattern" --reviewer local
python -m ade.cli --list-feedback
```

Supported labels are `interesting`, `known_pattern`, `false_positive`,
`duplicate`, `important`, `not_useful`, and `needs_more_data`. Feedback is
stored at `data/feedback/feedback.jsonl` by default and should remain ignored.

## Use Config

Default settings live in `configs/default.yaml`. Current settings cover project metadata, patch extraction, optional multi-scale patch sizes and strides, discovery limits, novelty scoring strategy, memory-aware scoring weights, diversity-aware anomaly selection, concept evidence thresholds, visual memory retrieval, reporting behavior, asset folders, run metadata folders, and demo data generation.

CLI arguments can override selected config values such as patch size, stride, and maximum candidate anomalies. Validation settings include supported image extensions, minimum image count, small dataset warning threshold, high patch-count warning threshold, and minimum image dimensions.

Memory settings control whether the current run builds an in-process vector index, which metric it uses, and how many nearest visual matches are included in reports. Feedback settings control the local JSONL feedback store path. The current implementation uses NumPy only; persistent memory banks and FAISS/vector database backends are future work.

Novelty scoring settings live under `discovery.novelty_strategy` and
`discovery.memory_aware_scoring`. Supported strategies are `global_distance`,
`memory_neighbor_distance`, and `hybrid`. If memory-aware scoring cannot use
neighbors, ADE falls back to global distance and records that fallback in run
metadata.

Multi-scale extraction is configured with matching `preprocessing.patch_sizes`
and `preprocessing.patch_strides` lists. The default remains a single scale to
keep local runs fast. Diversity settings live under `discovery.diversity` and
control how many candidate anomalies can come from the same image or nearby
regions.

## Git Workflow Guidance

Review generated files before staging changes. Generated artifacts such as demo images, report Markdown, report JSON, report assets, run metadata, local feedback JSONL files, caches, and bytecode should stay out of commits.

Recommended manual review steps:

```bash
git status --short
git diff
```

Stage only source, tests, config, and docs that you intentionally changed.

## Engineering Quality

Use `docs/engineering_quality.md` as the working checklist for code review, test expectations, documentation quality, artifact policy, configuration changes, and release readiness.

## Private-Alpha Verification

For a full local smoke test, run:

```bash
python scripts/verify_local.py
```

For command details and report-schema notes, see `docs/cli_reference.md` and
`docs/report_schema.md`.

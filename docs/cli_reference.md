# ADE CLI Reference

These examples are written for PowerShell from the repository root. ADE is a
general autonomous discovery platform; the current CLI implementation is
visual-data-first and expects an image folder for analysis.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .[dev]
```

## Generate Demo Data

```powershell
python scripts/create_demo_data.py
```

This creates synthetic PNG files in `data/raw/demo_images/`. The images are
local test data only.

## Run Analysis

```powershell
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md
```

With an explicit config:

```powershell
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md --config configs/default.yaml
```

The command writes a Markdown report, a JSON sidecar report, preview assets, run
metadata, and a run-index entry. Candidate anomalies and candidate concepts are
review targets, not final conclusions.

## Validate a Report

```powershell
python -m ade.cli --validate-report data/reports/demo_report.json
```

Validation checks the JSON report shape, including stable `anomaly_id` and
`concept_id` fields on newly generated reports.

## Export HTML

```powershell
python -m ade.cli --export-html-report data/reports/demo_report.json --output data/reports/demo_report.html
```

The HTML export is a static local review artifact. It does not start a dashboard
or hosted service.

## Add Human Review Feedback

Use a real target ID from the JSON report:

```powershell
python -m ade.cli --add-feedback data/reports/demo_report.json --target-type anomaly --target-id anomaly_001 --label interesting --notes "Local review note" --reviewer local
python -m ade.cli --add-feedback data/reports/demo_report.json --target-type concept --target-id concept_001 --label known_pattern --notes "Known recurring pattern" --reviewer local
```

Supported labels are configured by the feedback module. Feedback is stored
locally as JSONL and is intended for review workflow experiments.

## List Feedback

```powershell
python -m ade.cli --list-feedback
python -m ade.cli --list-feedback --run-id <run_id>
```

## List Runs

```powershell
python -m ade.cli --list-runs
python -m ade.cli --list-runs --limit 5
```

## Run a Local Benchmark

```powershell
python scripts/run_benchmark.py --input data/raw/demo_images --config configs/default.yaml --output data/benchmarks/demo_benchmark.json
```

The benchmark script runs the ADE CLI, validates the generated JSON report, and
writes a small benchmark metadata file. It does not use internet access, GPUs,
or external datasets.

## Run Full Local Verification

```powershell
python scripts/verify_local.py
```

The verification script runs linting, tests, demo data generation, analysis,
report validation, HTML export, benchmarking, and run listing in sequence. It
fails fast on the first unsuccessful command.

## Dashboard Status

This branch may include dashboard UX documentation or static report exports, but
it does not implement a hosted dashboard application, authentication, billing,
or database-backed review workflow.

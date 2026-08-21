# ADE CLI Reference

These examples are written for PowerShell from the repository root. ADE is a
general autonomous discovery platform; the current CLI supports image-folder
analysis plus lightweight tabular CSV and explicit time-series CSV workflows.

## Install

```powershell
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .[dev]
```

## Generate Demo Data

```powershell
python scripts/create_demo_data.py
python scripts/create_tabular_demo_data.py
python scripts/create_timeseries_demo_data.py
```

These create synthetic local demo files under `data/raw/demo_images/`,
`data/raw/demo_tabular/`, and `data/raw/demo_timeseries/`. They are local test
data only.

## Build Visual Reference Memory

Build an immutable comparison memory from a folder containing expected or
normal reference images:

```powershell
python -m ade.cli --build-reference-memory data/reference/normal_images --reference-memory-output data/reference_memory
```

The command uses the configured patch scales, reference metric, coreset policy,
vector bound, and deterministic seed. It prints the content-addressed memory ID
and the exact `manifest.json` path. Repeating the command with identical files
and settings reuses the same validated immutable memory.

Use `--config` to supply non-default build settings and `--patch-size` or
`--stride` for explicit single-scale overrides:

```powershell
python -m ade.cli --build-reference-memory data/reference/normal_images `
  --reference-memory-output data/reference_memory `
  --config configs/reference_build.yaml
```

This command does not analyze a query dataset or produce candidate findings.
The reference folder must remain separate from query and validation data. See
[Opt-in visual reference scoring](reference_scoring_workflow.md) for the build,
configuration, scoring, and artifact workflow.

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

## Run Tabular Analysis

```powershell
python -m ade.cli --input data/raw/demo_tabular/operations.csv --output data/reports/tabular_demo_report.md --modality tabular
```

For `.csv` inputs, ADE defaults to the tabular path unless `--modality
timeseries` is supplied. The tabular workflow performs row-level candidate
anomaly ranking and simple candidate pattern grouping.

## Run Time-Series Analysis

```powershell
python -m ade.cli --input data/raw/demo_timeseries/machine_metrics.csv --output data/reports/timeseries_demo_report.md --modality timeseries --timestamp-column timestamp --entity-column machine
```

The time-series workflow is explicit. It performs timestamped point/window-style
candidate anomaly ranking and simple candidate pattern grouping. It does not
implement forecasting, production streaming, live sensors, or alerting.

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

## Export Local Dashboard

```powershell
python -m ade.cli --export-local-dashboard --output data/dashboard
```

This command does not run analysis. It reads existing local artifacts where
present, including `data/reports/runs/index.json`, report JSON files, static
HTML reports, benchmark JSON files, and `data/feedback/feedback.jsonl`. It
writes `index.html` and `dashboard_data.json` under the requested output
directory and treats missing folders as empty states.

The export is a local static demo viewer for review support. It is not a hosted
dashboard app, does not add authentication or a database, and does not turn
candidate findings into automated truth.

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

## Summarize Feedback Memory

```powershell
python -m ade.cli --summarize-feedback-memory
python -m ade.cli --summarize-feedback-memory --run-id <run_id>
```

This reads the configured local JSONL feedback store and prints a concise
Markdown-style summary. It does not run analysis. The summary is
feedback-informed ranking support and does not replace human review.

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
report validation, HTML export, benchmarking, local dashboard export, and run
listing in sequence. It fails fast on the first unsuccessful command.

## Dashboard Status

This branch includes local static dashboard exports and dashboard planning docs,
but it does not implement a hosted dashboard application, dashboard server,
authentication, billing, or database-backed review workflow.

## Qualify a local MVTec AD category

```powershell
python -m ade.cli `
  --qualify-mvtec-ad "D:\Datasets\mvtec_anomaly_detection" `
  --mvtec-category bottle `
  --mvtec-dataset-version classic `
  --benchmark-manifest-output "data\benchmarks\mvtec_ad\bottle.json"
```

This command validates a manually downloaded category, hashes declared test
images and masks, and writes an immutable canonical benchmark manifest. It does
not download or redistribute the dataset. MVTec AD is CC BY-NC-SA 4.0 and is not
permitted for commercial use. See
[`docs/mvtec_ad_benchmark.md`](mvtec_ad_benchmark.md) for the complete
reference-memory and benchmark workflow.

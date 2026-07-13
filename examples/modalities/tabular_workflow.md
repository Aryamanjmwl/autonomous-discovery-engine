# Tabular Workflow

This example demonstrates ADE's lightweight CSV tabular adapter foundation and
end-to-end CLI path. It generates a small deterministic operations-style CSV,
runs row-level candidate anomaly discovery, and writes Markdown/JSON reports for
human review.

## Generate Demo Data

```powershell
python scripts/create_tabular_demo_data.py
```

This writes:

- `data/raw/demo_tabular/operations.csv`

The generated rows include normal records plus a few rows with an
`anomaly_marker` value. The marker is present so reviewers can understand the
synthetic data; ADE still treats findings as candidate anomalies that require
human review.

## Run Tabular Discovery

```powershell
python -m ade.cli --input data/raw/demo_tabular/operations.csv --output data/reports/tabular_demo_report.md --modality tabular
```

For `.csv` inputs, ADE currently defaults to the tabular path unless
`--modality timeseries` is provided.

## Currently Implemented

- CSV validation and profiling
- Numeric/categorical column detection
- Deterministic row-level feature extraction
- Row-level candidate anomaly ranking
- Simple candidate pattern grouping
- Markdown and JSON report generation
- Local run metadata and run-index entries

## Planned

- Richer tabular feature backends
- Better schema-aware evidence summaries
- Relational and database adapters
- Reviewer workflows for comparing tabular candidate patterns across runs

## Interpretation

Findings are candidate row anomalies and possible tabular patterns. Scores help
prioritize review; they are not proof of operational, financial, scientific, or
clinical significance.

Generated demo data and reports under `data/` are ignored by Git.

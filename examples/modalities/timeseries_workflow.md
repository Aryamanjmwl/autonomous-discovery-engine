# Time-Series Workflow

This example demonstrates ADE's lightweight timestamped CSV adapter foundation
and explicit time-series CLI path. It generates a deterministic machine-metrics
CSV with trend/seasonality-like behavior and injected candidate anomaly points.

## Generate Demo Data

```powershell
python scripts/create_timeseries_demo_data.py
```

This writes:

- `data/raw/demo_timeseries/machine_metrics.csv`

The generated rows include normal timestamped points plus a few rows with an
`anomaly_marker` value. The marker is present for synthetic-data review only;
ADE still surfaces candidate anomalies that require human review.

## Run Time-Series Discovery

```powershell
python -m ade.cli --input data/raw/demo_timeseries/machine_metrics.csv --output data/reports/timeseries_demo_report.md --modality timeseries --timestamp-column timestamp --entity-column machine
```

The time-series path is explicit. Plain `.csv` inputs default to tabular
analysis unless `--modality timeseries` is provided.

## Currently Implemented

- Timestamped CSV validation and profiling
- Timestamp column detection or explicit `--timestamp-column`
- Optional entity column support
- Numeric signal detection
- Deterministic point/window-style feature extraction
- Point-level candidate anomaly ranking
- Simple candidate pattern grouping
- Markdown and JSON report generation
- Local run metadata and run-index entries

## Planned

- Stronger sequence-aware feature backends
- Baseline/reference memory for recurring time-series patterns
- Forecasting-oriented adapters, if added carefully later
- Production streaming and alerting remain future work and are not implemented

## Interpretation

Findings are candidate time-series anomalies and possible temporal patterns.
Scores are review-prioritization signals, not automated truth. Any operational,
financial, scientific, or clinical interpretation requires human review.

Generated demo data and reports under `data/` are ignored by Git.

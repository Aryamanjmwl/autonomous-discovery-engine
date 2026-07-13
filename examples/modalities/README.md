# Modality Examples

ADE is an adapter-based autonomous discovery platform. The examples here show
what can be run today and what is only planned.

All findings are candidate anomalies, candidate concepts, or possible patterns
that require human review.

## Implemented Visual Demo Workflow

```bash
python scripts/create_demo_data.py
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md
python -m ade.cli --validate-report data/reports/demo_report.json
python -m ade.cli --export-html-report data/reports/demo_report.json --output data/reports/demo_report.html
```

## Tabular CSV Foundation

Use this only with a local CSV file that has a header row:

```bash
python -m ade.cli --input data/raw/example.csv --output data/reports/tabular_report.md
```

This workflow produces candidate row anomalies and candidate tabular concepts.
It does not implement database ingestion, joins, supervised learning, or
financial advice.

## Time-Series CSV Foundation

Use this only with a local CSV file that has a timestamp column:

```bash
python -m ade.cli --input data/raw/series.csv --output data/reports/timeseries_report.md --modality timeseries --timestamp-column timestamp
```

This workflow produces candidate unusual points/windows and candidate
time-series concepts. It does not implement streaming ingestion, forecasting,
alerting, or production monitoring.

## Planned Adapter Targets

These modalities are planned or future adapter targets, not implemented
workflows in this branch:

- Sensor streams
- Live satellite feeds
- Audio input
- Logs/events
- Scientific instrument data
- Streaming pipelines

Do not invent commands for planned adapters. Add commands here only after the
adapter, validation/profile layer, representation strategy, report contract, and
tests exist.

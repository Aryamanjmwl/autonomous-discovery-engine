# ADE Time-Series CSV Support

ADE includes an initial CSV-based time-series adapter for timestamped datasets.
This foundation is intentionally lightweight: it profiles timestamped data,
extracts deterministic point/window-style features, ranks candidate unusual
points, groups evidence into candidate concepts, and writes reviewable
Markdown/JSON reports.

## Expected Input

Use a CSV file with a timestamp column and one or more numeric signal columns:

```text
timestamp,machine,temp,pressure
2026-07-07T00:00:00,A,20,100
2026-07-07T00:01:00,A,21,101
2026-07-07T00:02:00,A,85,140
```

Timestamp columns are detected from common names such as `timestamp`, `time`,
`datetime`, `date`, or `ts`. Passing an explicit timestamp column is safer for
real datasets.

## Run Time-Series Discovery

Time-series mode is explicit so plain CSV files continue to use the tabular
adapter:

```bash
python -m ade.cli --input data/raw/series.csv --output data/reports/timeseries_report.md --modality timeseries --timestamp-column timestamp
```

Optional entity/group column:

```bash
python -m ade.cli --input data/raw/series.csv --output data/reports/timeseries_report.md --modality timeseries --timestamp-column timestamp --entity-column machine
```

## What It Does

- Validates local `.csv` input
- Detects or uses a configured timestamp column
- Detects numeric signal columns
- Records row count, time range, missing values, malformed timestamps, duplicate timestamps, and sampling interval summary
- Builds deterministic features from normalized values, missing indicators, deltas, rolling mean/std signals, spike indicators, time-gap indicators, and completeness ratio
- Scores candidate unusual points by distance from the time-series feature center
- Groups candidate findings into simple reason-based candidate concepts
- Writes Markdown, JSON, run metadata, and run index entries

## Report Output

Time-series reports include:

- Modality: `timeseries`
- Row count
- Timestamp column
- Time range
- Signal column count
- Missing-value summary
- Sampling interval summary
- Feature extraction metadata
- Top candidate time-series findings
- Candidate time-series concepts
- Limitations and human-review disclaimer

## Limitations

- CSV only for now
- Point/window-feature discovery only
- No streaming ingestion
- No forecasting
- No supervised learning
- No database ingestion
- No production monitoring or alerting
- Scores are ranking signals, not proof of significance

All candidate time-series findings and candidate concepts require human review
before operational, scientific, commercial, financial, or clinical use.

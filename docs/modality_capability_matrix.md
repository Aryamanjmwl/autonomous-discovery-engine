# Modality Capability Matrix

ADE is an adapter-based autonomous discovery platform. The current private-alpha
implementation has a mature visual/image-folder workflow and lightweight
foundations for selected non-visual CSV modalities. Other modalities are planned
adapter targets and should not be described as implemented.

All outputs are candidate anomalies, candidate concepts, or possible patterns
that require human review.

| Modality | Current status | Current input format | Current output / evidence type | Limitations | Next engineering step |
| --- | --- | --- | --- | --- | --- |
| Visual image folders | Implemented / working mature workflow | Local folder of supported image files | Candidate visual anomalies, candidate visual concepts, patch previews, evidence bundles, Markdown/JSON/HTML reports | Lightweight deterministic visual features; no deep visual encoder; local files only | Evaluate stronger optional visual backends behind the representation interface |
| Report generation | Implemented / working | ADE run outputs | Markdown, JSON, static HTML, run metadata, run index | Local artifacts only; not a hosted review system | Keep schema compatibility while adding adapter-specific evidence renderers |
| Report validation | Implemented / working | ADE JSON report | Validation result with errors or warnings | Validates current report schema only | Extend validation as adapter schemas mature |
| Human-review feedback | Implemented / working local foundation | ADE JSON report plus `anomaly_id` or `concept_id` | Local JSONL feedback records | Local file store; no users, auth, database, or audit guarantees | Design review-state joins for future dashboard/API consumers |
| Benchmark/local verification | Implemented / working | Demo image workflow and config | Benchmark JSON, local verification result | Local smoke test only; not a performance claim | Add adapter-specific benchmark fixtures when workflows stabilize |
| Tabular CSV | Foundation / partial | Local `.csv` file | Candidate row anomalies, candidate tabular concepts, Markdown/JSON reports | Row-level only; no joins, database ingestion, supervised learning, or production analytics | Add representative CSV fixtures and clarify schema stability for tabular evidence |
| Time-series CSV | Foundation / partial | Local `.csv` file with timestamp column via explicit `--modality timeseries` | Candidate unusual points/windows, candidate time-series concepts, Markdown/JSON reports | CSV only; no streaming ingestion, forecasting, alerting, or monitoring | Add controlled time-series fixtures and refine window/evidence summaries |
| Video | Foundation / placeholder | Placeholder adapter object only | No decoded frame evidence yet | No frame extraction, temporal windows, reports, or CLI workflow | Implement frame sampling as a visual adapter extension before claiming video support |
| Logs/events | Planned modality | None in current implementation | Planned candidate event patterns | No parser, adapter, representation, or report renderer | Define a log/event record model and validation profile |
| Sensor streams | Planned modality | None in current implementation | Planned candidate sensor anomalies and possible patterns | No streaming or sensor adapter; no online scoring | Start with offline CSV sensor datasets before live ingestion |
| Live satellite feeds | Planned modality | None in current implementation | Planned candidate geospatial/temporal evidence | No live stream ingestion, geospatial tiling, or satellite-specific backend | Add offline satellite image-folder examples before live feeds |
| Audio input | Planned modality | None in current implementation | Planned candidate acoustic patterns | No audio decoder, spectrogram features, or report views | Prototype offline audio file profiling and spectrogram representation |
| Scientific instrument data | Planned modality | None in current implementation | Planned candidate instrument patterns | No instrument-specific adapter or calibration metadata | Define adapter requirements with domain experts and private datasets |
| Streaming pipelines | Planned platform capability | None in current implementation | Planned incremental discovery/review outputs | No queues, service runtime, database, cloud, or production monitoring | Design batch-first adapter contracts before adding streaming infrastructure |

## Current Working Commands

Visual demo:

```bash
python scripts/create_demo_data.py
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md
python -m ade.cli --validate-report data/reports/demo_report.json
python -m ade.cli --export-html-report data/reports/demo_report.json --output data/reports/demo_report.html
```

Tabular CSV foundation:

```bash
python -m ade.cli --input data/raw/example.csv --output data/reports/tabular_report.md
```

Time-series CSV foundation:

```bash
python -m ade.cli --input data/raw/series.csv --output data/reports/timeseries_report.md --modality timeseries --timestamp-column timestamp
```

Only use the CSV commands with local CSV files that match the documented
expectations. Planned modalities should remain documented as planned/future work
until implementation, tests, and report contracts exist.

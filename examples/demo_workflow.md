# Demo Workflow

This workflow exercises the current visual-data-first implementation from the
repository root. It uses synthetic images generated locally and does not require
internet access or a GPU.

## 1. Install

```powershell
pip install -e .[dev]
```

## 2. Generate Synthetic Images

```powershell
python scripts/create_demo_data.py
```

Images are written to `data/raw/demo_images/`.

## 3. Run ADE Analysis

```powershell
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md
```

With an explicit config:

```powershell
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md --config configs/default.yaml
```

The analysis writes `data/reports/demo_report.md` and
`data/reports/demo_report.json`.

## 4. Validate and Export

```powershell
python -m ade.cli --validate-report data/reports/demo_report.json
python -m ade.cli --export-html-report data/reports/demo_report.json --output data/reports/demo_report.html
```

## 5. Inspect Review Target IDs

```powershell
python -c "import json; r=json.load(open('data/reports/demo_report.json')); print(r.get('candidate_anomalies', [])[0].get('anomaly_id'))"
python -c "import json; r=json.load(open('data/reports/demo_report.json')); print(r.get('candidate_concepts', r.get('candidate_unknown_concepts', []))[0].get('concept_id'))"
```

Use real IDs from the report when recording feedback.

## 6. Record Local Feedback

```powershell
python -m ade.cli --add-feedback data/reports/demo_report.json --target-type anomaly --target-id anomaly_001 --label interesting --notes "Local review note" --reviewer local
python -m ade.cli --list-feedback
python -m ade.cli --summarize-feedback-memory
```

Feedback is local JSONL review data. It does not replace human review or
create a production audit trail. A later analysis can include review-memory
signals in Markdown, JSON, and HTML reports when the configured feedback store
contains prior feedback.

## 7. Export Local Dashboard

```powershell
python -m ade.cli --export-local-dashboard --output data/dashboard
```

This creates a local static demo viewer from existing run history, reports,
HTML exports, benchmarks, and feedback files where present. It does not run
analysis and does not replace human review.

## 8. Run a Benchmark

```powershell
python scripts/run_benchmark.py --input data/raw/demo_images --config configs/default.yaml --output data/benchmarks/demo_benchmark.json
```

## 9. Run Full Local Verification

```powershell
python scripts/verify_local.py
```

Generated demo images, reports, preview assets, benchmarks, dashboard exports,
feedback logs, and run metadata should remain untracked.

# ADE Interview Demo Script

This short PowerShell walkthrough exercises the local visual workflow and the
portfolio demo artifacts. It uses generated data and does not require internet
access or a GPU. Candidate findings require human review.

## 1. Generate Demo Images

```powershell
python scripts/create_demo_data.py
```

## 2. Run Visual Analysis

```powershell
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md
```

## 3. Validate the JSON Report

```powershell
python -m ade.cli --validate-report data/reports/demo_report.json
```

## 4. Export HTML

```powershell
python -m ade.cli --export-html-report data/reports/demo_report.json --output data/reports/demo_report.html
```

## 5. Run Benchmark

```powershell
python scripts/run_benchmark.py --input data/raw/demo_images --config configs/default.yaml --output data/benchmarks/demo_benchmark.json
```

## 6. Export Local Dashboard

```powershell
python -m ade.cli --export-local-dashboard --output data/dashboard
```

## 7. Add Human-Review Feedback

Inspect `data/reports/demo_report.json` for an `anomaly_id`, then use that ID:

```powershell
python -m ade.cli --add-feedback data/reports/demo_report.json --target-type anomaly --target-id anomaly_001 --label interesting --notes "Candidate anomaly to review in the demo" --reviewer local
```

Feedback is local JSONL review data. It can inform future ranking support, but
it does not prove that a candidate anomaly is meaningful.

## 8. Run Full Local Verification

```powershell
python scripts/verify_local.py
```

Generated demo images, reports, preview assets, benchmark files, dashboard
exports, feedback logs, and run metadata are ignored by Git.

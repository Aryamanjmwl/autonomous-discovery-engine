# ADE v0.1.0 Technical Preview

ADE v0.1.0 Technical Preview packages the current local workflow for recruiter
review, technical interviews, and early preview feedback.

ADE is an adapter-based autonomous discovery platform. The current release is a
local technical preview build: the visual/image-folder workflow is the most mature
path, while CSV tabular and CSV time-series workflows are lightweight
foundations with local CLI reports.

## Highlights

- Visual/image-folder local discovery workflow.
- Lightweight CSV tabular and CSV time-series workflows.
- Candidate anomaly and candidate concept reports.
- Markdown, JSON, and static HTML report outputs.
- Report validation and stable review target IDs.
- Local run history and benchmark script.
- Local dashboard export from generated artifacts.
- Local human-review feedback JSONL.
- Review-informed memory signals for future ranking support.
- Portfolio docs, demo script, and sample-output guide.

## Verification

Recommended verification before reviewing the release:

```powershell
ruff check
pytest
python scripts/verify_local.py
```

The demo workflow can also be refreshed locally:

```powershell
python scripts/create_demo_data.py
python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md
python -m ade.cli --validate-report data/reports/demo_report.json
python -m ade.cli --export-html-report data/reports/demo_report.json --output data/reports/demo_report.html
python scripts/run_benchmark.py --input data/raw/demo_images --config configs/default.yaml --output data/benchmarks/demo_benchmark.json
python -m ade.cli --export-local-dashboard --output data/dashboard
```

## Limitations

- Findings are candidate findings and require human review.
- This is not a production SaaS release.
- No hosted dashboard, auth/users, database service, billing, cloud deployment,
  production streaming, or enterprise deployment is included.
- Audio, live satellite feeds, and sensor streams remain planned/future adapter
  paths unless separately implemented.
- Local feedback supports review-informed ranking signals, not automated truth
  or supervised ground truth.

## Next Milestones

- Harden adapter and report contracts.
- Improve review workflows around local feedback JSONL.
- Expand concept memory and review-informed ranking support.
- Evaluate optional stronger representation backends behind existing
  interfaces.
- Keep production/hosted architecture design separate from the local technical
  preview workflow.

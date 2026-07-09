# Private-Alpha Release Checklist

Use this checklist before tagging or sharing a private-alpha build. It is a
review aid, not a production certification.

## Local Verification

- `ruff check` passes.
- `pytest` passes.
- `python scripts/create_demo_data.py` works from the repository root.
- `python -m ade.cli --input data/raw/demo_images --output data/reports/demo_report.md` writes Markdown and JSON reports.
- `python -m ade.cli --validate-report data/reports/demo_report.json` passes.
- `python -m ade.cli --export-html-report data/reports/demo_report.json --output data/reports/demo_report.html` passes.
- `python scripts/run_benchmark.py --input data/raw/demo_images --config configs/default.yaml --output data/benchmarks/demo_benchmark.json` passes.
- `python scripts/verify_local.py` passes.
- `python -m ade.cli --list-runs --limit 5` works.

## Documentation

- README describes ADE as a general autonomous discovery platform with a visual-data-first implementation.
- CLI reference includes analysis, validation, HTML export, feedback, benchmark, and local verification commands.
- Report schema documents `anomaly_id`, `concept_id`, dataset profile, evidence, confidence, and human-review requirements.
- Product scope, architecture, development workflow, and engineering quality docs match implemented behavior.
- Known limitations are stated without overclaiming production readiness.

## Generated Artifact Hygiene

- Demo images are ignored.
- Markdown, JSON, HTML reports, preview assets, run metadata, benchmarks, feedback logs, caches, and bytecode are ignored.
- `.gitkeep` files remain only where empty project directories are intentional.
- No generated report, benchmark, feedback, cache, or `__pycache__` file is staged.

## Known Limitations

- Current analysis support is image-folder based.
- Non-visual adapters are future work unless explicitly present in a branch.
- Deep visual embedding backends are not part of the lightweight default install.
- Local feedback is not a production audit system.
- Reports contain candidate findings that require human review.
- No hosted dashboard, authentication, billing, cloud storage, database, or compliance certification is included.

## Pull Request Review

- Scope is narrow and reviewable.
- Tests cover changed behavior.
- Docs and examples match the commands that actually work.
- No secrets, local paths, generated artifacts, or unrelated files are included.
- Changelog is updated for user-visible changes.

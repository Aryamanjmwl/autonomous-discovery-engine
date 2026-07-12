# Demo Asset Guidance

This guide lists screenshots and release assets to capture manually for a
portfolio page, GitHub release, or recruiter-facing walkthrough.
Do not commit generated private data. Do not commit generated reports,
generated dashboard output, or screenshots that reveal private datasets.

## Suggested Screenshots

- README top section:
  - Suggested filename: `ade-readme-top.png`
  - Capture the project title, technical preview positioning, and capability table.
- Terminal `verify_local.py` pass:
  - Suggested filename: `ade-verify-local-pass.png`
  - Capture the final `Local verification passed.` line.
- HTML report:
  - Suggested filename: `ade-html-report.png`
  - Capture a candidate anomaly or candidate concept section with the human
    review requirement visible.
- Local dashboard:
  - Suggested filename: `ade-local-dashboard.png`
  - Capture the static dashboard summary cards and artifact tables.
- Modality capability matrix:
  - Suggested filename: `ade-modality-matrix.png`
  - Capture implemented, foundation, and planned status rows.
- GitHub Actions passing:
  - Suggested filename: `ade-github-actions-passing.png`
  - Capture the workflow status after the release branch passes checks.

## Where To Store Screenshots

For local portfolio drafting, use a folder outside generated report data, such
as:

```text
docs/assets/demo/
```

Only commit screenshots if they contain synthetic/public data and are intended
for the repository. Keep preview customer data, local generated reports,
feedback logs, and dashboard exports out of Git.

## Portfolio Page Guidance

- Lead with ADE as an adapter-based autonomous discovery platform.
- Show the visual workflow as the most mature current path.
- Describe CSV tabular and CSV time-series support as lightweight local
  foundations.
- Include a screenshot of the local dashboard only as a static demo viewer, not
  as a hosted dashboard app.
- State that candidate anomalies, candidate concepts, and possible patterns
  require human review.

## GitHub Release Attachment Guidance

- Attach only screenshots that are safe for public or recruiter review.
- Prefer synthetic demo data screenshots generated from repository scripts.
- Do not attach generated JSONL feedback with private reviewer notes.
- Do not attach generated dashboard folders or private report archives.
- Link to `docs/releases/v0.1.0-preview.md` and
  `examples/demo_script.md` for reproducible local commands.

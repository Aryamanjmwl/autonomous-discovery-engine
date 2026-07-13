# Public Release Checklist

Use this checklist before presenting ADE as a public repository or open-source
project. ADE is currently a local Technical Preview; candidate findings require
human review.

## Repository First Impression

- README includes the discovery hook, local Technical Preview status, and a
  concise implemented/foundation/planned table.
- README screenshots or release attachments use synthetic/public data only.
- ADE Studio status is clear: local UI foundation with mock data, not backend
  integrated.
- Technical Preview limitations are documented without hosted deployment
  claims.

## Required Project Hygiene

- LICENSE is selected before promoting the repository as open source.
- SECURITY.md is present and describes the local-first posture.
- CI is green.
- Release notes are present.
- Demo assets guidance is present.
- No generated reports, generated dashboard output, feedback logs, private
  datasets, cache directories, or local run artifacts are committed.

## Release Presentation

- Screenshot plan is ready:
  - README top section
  - ADE Studio overview
  - Findings review
  - HTML report
  - Local dashboard
  - Terminal `verify_local.py` pass
  - GitHub Actions pass
- Optional demo video uses generated synthetic data only.
- Optional GitHub Discussions is configured only if the maintainer wants public
  support/discussion channels.
- Suggested GitHub topics: `python`, `data-science`, `anomaly-detection`,
  `human-in-the-loop`, `local-first`, `technical-preview`.

## Final Verification

```bash
ruff check
pytest
python scripts/verify_local.py
```

Do not create public release tags until the owner has reviewed the license,
security posture, generated artifacts, screenshots, and release notes.

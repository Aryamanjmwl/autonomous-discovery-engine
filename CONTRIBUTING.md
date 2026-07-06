# Contributing

ADE is a general autonomous discovery platform with a visual-data-first implementation. Contributions should improve correctness, maintainability, reproducibility, or documentation clarity.

## Development Setup

```bash
python -m venv .venv
.\.venv\Scripts\activate
pip install -e .[dev]
```

## Checks

```bash
pytest
ruff check .
```

## Contribution Standards

- Keep generated artifacts out of commits.
- Add tests for stable behavior.
- Keep public interfaces typed.
- Avoid heavy default dependencies.
- Do not describe future adapters or enterprise features as implemented.
- Keep findings framed as candidate anomalies, candidate patterns, candidate concepts, possible relationships, and hypotheses requiring human review.

## Pull Requests

Pull requests should include:

- Summary
- What changed
- Tests run
- Notes on limitations or intentionally delayed work

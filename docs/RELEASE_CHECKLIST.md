# Release Checklist

Use this checklist before creating an internal or public release.

## Code

- `pytest` passes.
- Linting passes if enabled.
- Type checks pass if enabled.
- Public interfaces are typed.
- Generated artifacts are not staged.

## Product Scope

- README describes current capabilities accurately.
- Future roadmap items are not described as implemented.
- Human review requirements are visible in reports and docs.
- Limitations are documented.

## Reports

- Markdown report renders cleanly.
- JSON report includes run metadata and dataset profile.
- Run metadata file is written.
- Run index is updated.

## Project Files

- `CHANGELOG.md` updated.
- `SECURITY.md` current.
- `CONTRIBUTING.md` current.
- CI workflow present.
- License unchanged unless intentionally reviewed.

## Release Decision

Do not release if generated artifacts, secrets, private datasets, or unreviewed proprietary methods are staged.

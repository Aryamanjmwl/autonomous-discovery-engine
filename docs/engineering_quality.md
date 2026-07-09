# Engineering Quality Checklist

ADE is a general autonomous discovery platform with a visual-data-first implementation. Engineering work should favor clear boundaries, reproducibility, testability, and careful product language.

## Coding Standards

- Keep modules focused on one responsibility.
- Use `pathlib.Path` for filesystem paths.
- Use dataclasses for stable internal records.
- Keep JSON serialization explicit and avoid dumping raw NumPy arrays.
- Keep retrieval metadata JSON-safe and avoid persisting runtime-only memory state by accident.
- Keep feedback records append-only, JSON-safe, and local until a database-backed review workflow is justified.
- Keep patch IDs deterministic and include enough scale/coordinate metadata to avoid collisions.
- Add type hints for public functions and dataclass fields.
- Prefer small functions over hidden control flow.
- Avoid broad exception handling unless the error is converted into a clear user-facing message.
- Do not add deep learning, dashboard, or adapter features before the relevant design boundary is documented.
- Treat scores as review-prioritization signals. Reports should expose supporting evidence and component breakdowns where practical.
- Keep novelty strategy fallbacks explicit in metadata rather than hiding them.

## Test Standards

- Tests should be deterministic.
- Use `tmp_path` for generated files whenever practical.
- Do not depend on internet access, GPUs, or user-local datasets.
- Test behavior and output contracts, not incidental implementation details.
- Cover CLI errors for invalid input paths, missing config files, empty datasets, and invalid limits.
- Cover input profiling for valid folders, empty folders, unsupported files, unreadable images, and warning behavior.
- Cover concept scoring, evidence ordering, JSON-safe evidence bundles, and report schema changes when discovery outputs change.
- Cover vector memory metrics, deterministic neighbor ordering, filters, and empty-index behavior when retrieval changes.
- Cover multi-scale patch counts, invalid scale config, and diversity selection behavior when patch extraction or anomaly selection changes.
- Cover novelty scoring strategies, normalization edge cases, invalid weights, and memory fallback behavior when scoring changes.
- Cover feedback serialization, store filtering, CLI target validation, and malformed JSONL handling when feedback behavior changes.

## Documentation Standards

- State that ADE is a general autonomous discovery platform.
- State that the current implementation focuses on visual data.
- Do not imply non-visual adapters are implemented before they exist.
- Use careful language: candidate anomaly, candidate pattern, candidate concept, possible relationship, hypothesis, and requires human review.
- Avoid hype, guaranteed outcomes, or claims that ADE replaces experts.

## Artifact Policy

Keep generated artifacts out of version control:

- Synthetic demo images
- Markdown and JSON reports
- Report preview assets
- Run metadata and run indexes
- Local feedback JSONL records
- Test temp folders
- Python bytecode and cache folders
- Build and package metadata

Keep `.gitkeep` files only where they preserve intended empty directory structure.

## Configuration Policy

- Defaults belong in `configs/default.yaml` and `src/ade/config.py`.
- CLI flags may override selected runtime settings.
- User-provided config paths should fail clearly when missing or invalid.
- Input validation thresholds and supported extensions belong in config.
- New configuration keys should have tests and documentation.
- Memory configuration should remain lightweight and should not imply persistent vector storage unless that storage exists.
- Memory-aware scoring weights and strategy names should be validated at config load time.
- Multi-scale defaults should remain conservative unless runtime and report quality are reviewed.

## Commit Discipline

- Review generated files before staging.
- Stage source, tests, configs, and docs intentionally.
- Keep unrelated refactors out of focused changes.
- Do not commit local report outputs, run history, caches, or demo images.

## Review Checklist

- Are product claims careful and accurate?
- Are candidate findings traceable to source data?
- Do concept findings include supporting evidence, consistency/confidence context, and cautious wording?
- If memory is enabled, are nearest-neighbor results bounded, deterministic, and traceable to source patches?
- Are reported candidate anomalies diverse enough to avoid obvious duplicate regions from one image?
- Do candidate anomalies include a JSON-safe score breakdown and effective scoring strategy?
- Are outputs marked as requiring human review?
- Are new paths ignored if they are generated?
- Do tests pass from a clean environment?
- Are new dependencies justified?

## Release Readiness Checklist

- `pytest` passes.
- Demo data generation works.
- Analysis command writes Markdown, JSON, assets, run metadata, and run index.
- `--list-runs` works with and without `--limit`.
- README and docs describe current scope accurately.
- Generated artifacts are not staged for release.

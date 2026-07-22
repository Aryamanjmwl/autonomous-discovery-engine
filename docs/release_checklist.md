# v0.1.0 Technical Preview Release Checklist

Use this checklist before sharing the local-first Technical Preview. It is a
release review aid, not an operational-readiness certification.

- [ ] Confirm `pyproject.toml`, `src/ade/__init__.py`, Studio metadata, and frontend
  package metadata identify version `0.1.0`.
- [ ] Review `docs/releases/v0.1.0-technical-preview.md` against the final release candidate.
- [ ] Confirm `CHANGELOG.md` links to the canonical release note.

## Local setup and backend verification

- [ ] Install the repository in an isolated environment with `pip install -e ".[dev,studio]"`.
- [ ] Run `ruff check`.
- [ ] Run `python -m mypy src`.
- [ ] Run `pytest`.
- [ ] Run `python scripts/verify_local.py`.
- [ ] Confirm a normal image-folder run still produces candidate findings that require human review.

## Frontend verification

From `apps/studio/frontend`:

- [ ] Run `npm --cache "D:\ADE\npm-cache" run typecheck`.
- [ ] Run `npm --cache "D:\ADE\npm-cache" run build`.
- [ ] Start the documented local backend and frontend, then confirm connected mode uses real local report data.
- [ ] Confirm missing, malformed, or unavailable reports produce an honest empty or warning state.
- [ ] Confirm every visible control performs a real action or is clearly disabled as Technical Preview functionality.

## Deterministic temporal demo

- [ ] Run `python scripts/verify_temporal_demo.py`.
- [ ] Confirm the generated sequence manifests validate.
- [ ] Confirm the temporal artifact and JSON report pass their CLI validators.
- [ ] Confirm Markdown and HTML describe candidate temporal changes as review-prioritization signals.
- [ ] Confirm Studio exposes the temporal report only after a real validated report exists.

## Generated artifact hygiene

- [ ] Generated demo images, reports, HTML, preview assets, run metadata, benchmark outputs, and caches remain ignored.
- [ ] No generated temporal images, reports, or immutable artifact directories are included in release source files.
- [ ] No secrets, private datasets, machine-specific paths, cache files, or bytecode are included.
- [ ] Tiny tracked fixtures, if any, are intentional and covered by tests.

## Documentation and claim audit

- [ ] README and public docs call ADE a local-first Technical Preview.
- [ ] Visual outputs use candidate anomaly or candidate concept language and require human review.
- [ ] Temporal outputs use candidate temporal change or candidate change event language and require human review.
- [ ] Optional DINOv2 and FAISS integrations are described as optional provider boundaries.
- [ ] Calibration is not described as a universal probability, and candidate operating points are not automated decisions.
- [ ] Benchmark outputs are described as validation artifacts, not general performance guarantees.
- [ ] Studio is described as reviewing real local reports, not as an operational monitoring service.
- [ ] Deterministic demo sequences are identified as synthetic generated local data.

## Known limitations

- Findings are review-prioritization signals, not autonomous conclusions.
- Default analysis is the local image-folder workflow; temporal analysis requires an explicit manifest and command.
- The lightweight default install does not enable optional DINOv2 or FAISS providers.
- Temporal comparison does not perform geographic alignment or continuous ingestion.
- Studio has no hosted accounts, authentication, billing, cloud storage, or multi-user review service.
- No clinical, scientific, safety-critical, or operational decision should rely on ADE output without appropriate independent review.

## Not included in v0.1.0 Technical Preview

- Hosted service operation, accounts, billing, or workspace tenancy.
- Continuous streams, remote-imagery services, or background monitoring.
- Geographic map registration or map-based review.
- Automatic decisions or domain-level verification of candidate findings.
- Operational support, service-level guarantees, or compliance certification.

Release only after every applicable item above has been checked and the actual
release contents have been manually inspected.

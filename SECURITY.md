# Security Policy

ADE is currently a local Technical Preview. The mature workflow runs on local
files and writes local artifacts such as reports, run metadata, feedback JSONL,
benchmarks, and dashboard exports.

## Local-First Posture

- No intentional cloud upload is part of the current local workflow. ADE does
  not intentionally upload input data, generated reports, feedback records, or
  dashboard exports to a cloud service.
- Users should still apply normal local-machine precautions before running ADE
  on files from untrusted sources.
- Generated artifacts may include source paths, reviewer notes, candidate
  anomaly details, and extracted preview images. Treat them as potentially
  sensitive.

## Reporting Security Issues

For now, report security concerns directly to the project owner through the
repository's preferred private contact channel. Do not publish exploit details
or private data in public issues.

## In Scope

- Local CLI workflows.
- Local report generation and validation.
- Local feedback JSONL handling.
- Local dashboard export.
- ADE Studio local UI foundation and mock-data surfaces.
- Documentation that could misstate security or privacy behavior.

## Out of Scope

- Hosted services, because ADE does not currently ship a hosted backend.
- Authentication, authorization, billing, and database security, because those
  systems are not implemented.
- Third-party infrastructure outside the repository.
- Private datasets or generated artifacts that users create locally.

## Security Review Status

ADE has not undergone a formal security audit. The current posture is a
local-first engineering constraint, not a certification.

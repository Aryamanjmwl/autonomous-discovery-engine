# ADR 0006: Offline and Explicit Model Provisioning

Status: Accepted

## Context

Implicit model downloads make runs non-reproducible, can disclose environment
information, and fail in restricted or air-gapped environments.

## Decision

ADE visual backends must not download models during execution. Optional model
artifacts are provisioned explicitly, addressed by local path and integrity
hash, and validated before dataset processing. Network provisioning, if ever
provided, must be a separate explicit user action.

## Consequences

Missing or mismatched model artifacts produce structured provisioning errors.
The default statistical backend requires no model artifact or network access.

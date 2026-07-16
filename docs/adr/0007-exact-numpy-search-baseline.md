# ADR 0007: Exact NumPy Search Baseline

Status: Accepted

## Context

Accelerated vector search can improve scale but introduces native dependencies,
index parameters, and approximation behavior that complicate correctness.

## Decision

Exact NumPy nearest-neighbor search is the correctness baseline. Accelerated
search such as FAISS may be added as an optional backend only after it is tested
against exact-search tolerances and records its index configuration in manifests.

## Consequences

The default remains lightweight and deterministic for bounded datasets.
Accelerated search is explicitly deferred and will never silently replace the
declared search backend.

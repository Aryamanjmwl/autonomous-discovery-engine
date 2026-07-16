# ADR 0007: Exact NumPy Search Baseline

Status: Implemented

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

The implementation batches query rows, accumulates distance calculations in
float64, clamps top-k to the reference count, and resolves equal distances by
stable vector ID and row index. Its memory boundary is one configured query
batch by the full bounded reference memory; it does not allocate an unbounded
full query-by-reference matrix.

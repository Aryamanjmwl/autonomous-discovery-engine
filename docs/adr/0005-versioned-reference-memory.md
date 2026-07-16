# ADR 0005: Persistent Versioned Reference Memory

Status: Implemented

## Context

Reference anomaly detection requires comparison state that is inspectable,
reproducible, and protected from query or validation leakage.

## Decision

Reference memory will be an immutable, persistent, schema-versioned artifact.
Its manifest binds the reference dataset fingerprint, effective configuration,
backend identity, search implementation, vector metadata, and integrity hashes.
Any source or configuration change produces a new memory identity.

## Consequences

Memory cannot be updated silently in place. Query and validation fingerprints
are rejected as memory sources. The implementation uses content-addressed
directories, pickle-free float32 NumPy arrays, canonical JSONL records, strict
artifact hashes, and atomic publication. Reference anomaly scoring remains a
separate future decision.

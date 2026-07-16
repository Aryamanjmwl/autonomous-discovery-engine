# ADR 0005: Persistent Versioned Reference Memory

Status: Accepted

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
are rejected as memory sources. Stage 1 supplies manifest boundaries only; it
does not persist vector payloads.

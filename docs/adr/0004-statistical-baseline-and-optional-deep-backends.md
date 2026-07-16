# ADR 0004: Statistical Baseline and Optional Deep Backends

Status: Accepted

## Context

ADE needs a reproducible default visual path while allowing stronger learned
representations later. Making a deep runtime mandatory would increase install,
provisioning, licensing, device, and offline-operation risk.

## Decision

Keep the deterministic statistical backend as the dependency-light baseline.
Deep backends will be optional implementations behind typed capability and
identity contracts. A request names a backend explicitly; unsupported or
unprovisioned backends fail before execution.

## Consequences

The baseline remains suitable for contract and pipeline tests but is not a
claim of deep visual quality. Later backends must declare model/version,
determinism, device support, representation shape, and provisioning state.

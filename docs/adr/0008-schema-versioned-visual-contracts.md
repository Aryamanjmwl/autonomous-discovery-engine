# ADR 0008: Schema-Versioned Visual Engine Contracts

Status: Accepted

## Context

Requests, results, reference memories, and reproducibility metadata cross
module and process boundaries. Unversioned dictionaries make compatibility and
validation ambiguous.

## Decision

Public visual-engine boundaries use typed Python contracts with an explicit
integer schema version. JSON manifests use canonical serialization and strict
field, enum, role, resource, and version validation. Unsupported schema
versions fail with structured errors rather than being guessed or upgraded.

## Consequences

Schema changes require an intentional versioning and migration decision.
Legacy CLI configuration remains supported through defaults while new visual
contracts are additive and initially separate from pipeline execution.

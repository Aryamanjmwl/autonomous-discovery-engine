# ADR 0001: Core Layered Architecture

## Status

Accepted

## Context

ADE needs to support discovery workflows without binding the engine to one dataset type, one model backend, or one report format.

## Decision

Use a layered architecture:

1. Data Adapter Layer
2. Representation / Embedding Layer
3. Discovery Layer
4. Evidence and Explanation Layer
5. Report and Output Layer
6. API and Product Layer
7. Enterprise Operations Layer

## Consequences

The current visual implementation remains simple, while future adapters and backends can be added behind stable boundaries. The tradeoff is that public interfaces must stay small and carefully documented.

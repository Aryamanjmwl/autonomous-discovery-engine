# Technical Decisions

## Python Package Layout

ADE uses a `src/` layout to keep import behavior explicit and testable.

## Placeholder Embeddings

The initial embedding engine uses deterministic image statistics. This keeps the pipeline working while avoiding premature claims about learned representation quality.

## Human Review

Reports include a human expert review note because current outputs are exploratory candidates, not validated scientific findings.

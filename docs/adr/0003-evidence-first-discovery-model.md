# ADR 0003: Evidence-First Discovery Model

## Status

Accepted

## Context

Anomaly scores alone are not enough for reviewable discovery workflows. Users need candidate findings connected to examples, metadata, and limitations.

## Decision

ADE will prioritize evidence-backed candidate findings. Reports should present candidate anomalies, candidate concepts, supporting evidence, confidence signals, limitations, and human review requirements.

## Consequences

Discovery outputs become more useful for review, but report generation and run metadata must preserve traceability. Scores remain ranking signals, not conclusions.

# ADR 0008: Uncalibrated reference scoring and spatial map semantics

## Status

Accepted

## Decision

ADE exposes PatchCore-style reference scoring as raw review-prioritization
distance, not probability or an automated normal/abnormal decision. Patch
scores use exact Euclidean or cosine search against one immutable reference
memory. `nearest_neighbor` returns the first distance; `knn_mean` returns the
float64 arithmetic mean of the nearest distances.

Image scores are either the maximum patch score or the mean of the largest
strictly configured fraction. Spatial maps project patch scores through
overlap mean or overlap max, then fuse scales through mean or max. Pixels with
no contributing patch remain `NaN` and are represented separately by coverage
counts; they are never interpreted as normal. Gaussian smoothing is
deterministic, mask-aware, and does not mutate patch scores. Per-image display
normalization is presentation-only and cannot be compared across images.

## Consequences

Results record dataset, configuration, backend, memory, metric, scoring,
aggregation, projection, fusion, smoothing, device, determinism and artifact
provenance with `calibrated=false`. Human review remains required. Fitted
calibration and benchmark thresholds require a later leakage-controlled stage.

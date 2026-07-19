# Visual Calibration and Threshold Candidates

Stage 4D provides an optional, library-first layer for fitted calibration and
held-out threshold evaluation. It is disabled by default and is not connected
to the ADE pipeline, Studio, or report UI.

## Fitted calibration

The dependency-free methods are `identity`, `empirical_percentile`, and
`minmax`. Identity preserves raw scores and records `calibrated=false`.
Empirical percentile uses a fitted held-out/reference score distribution and
returns its right-inclusive empirical percentile. Minmax uses the fitted score
range and clips to `[0, 1]` by default; a constant fitted range returns `0.0`
with a warning.

Only empirical-percentile and minmax outputs backed by fitted metadata may be
called calibrated scores. They are fitted transformations, not universal
anomaly probabilities or scientific truth. Metadata records the method, fit
time, score source and count, distribution statistics, configuration and data
fingerprints, fitted parameters, calibrated flag, and warnings.

## Threshold candidates and operating points

Candidates can be generated from explicit score thresholds, percentiles, or a
top fraction. Selection uses `score >= threshold`; top-fraction candidates use
the score at the requested ceiling-ranked position, so ties can increase the
selected workload. Every candidate is an operating point for evaluation, not
an automated decision threshold.

With complete valid binary labels, held-out evaluation reports confusion counts
and precision, recall, and F1 where their denominators are valid. Missing
positives, missing negatives, divide-by-zero cases, and class imbalance are
surfaced through unavailable metrics or warnings. Duplicate score IDs and
invalid labels are rejected.

Without complete labels, evaluation reports review-workload information only:
selected count and fraction, score threshold and quantile, and the selected
score range. It does not invent supervised performance quality.

## Artifacts and provenance

`publish_calibration_artifact` writes canonical JSON into an immutable,
content-addressed directory through a same-filesystem temporary directory. A
versioned manifest records the JSON size and SHA-256. Validation rejects schema
mismatches, corruption, missing or unexpected files, and path traversal. Pickle
is never used.

Provenance retains the source score artifact path or fingerprint, score type,
calibration method, threshold strategy, configuration and data fingerprints,
generation time, calibrated state, limitations, and
`human_review_required=true`.

All outputs are review-prioritization signals and require human review.

# Visual Benchmark Validation Harness

Stage 4E provides a reproducible, library-first benchmark validation harness
for explicit prediction records and externally provisioned visual datasets. It
does not run the ADE pipeline, download datasets, or change default analysis.

## Explicit provisioning and manifests

Benchmark datasets must be provisioned by the evaluator. ADE performs no
automatic public dataset downloads. A versioned canonical JSON benchmark
manifest declares the dataset name and version, dataset root, named splits,
sample IDs, relative image and optional mask paths, normal/anomaly/unknown
labels, optional categories and anomaly types, metadata, and optional SHA-256
fields.

Manifest validation rejects parent traversal, paths escaping the dataset root,
duplicate sample IDs, duplicate image paths, invalid labels or split names,
empty datasets, and non-canonical sample paths. Strict mode additionally checks
that every declared image and mask exists. Splits and samples are ordered
deterministically.

## Predictions and metrics

Evaluation accepts explicit sample-level predictions. Each record contains a
sample ID and raw score, plus optional fitted calibrated score, selection flag,
threshold ID, score source, and relative evidence path. Duplicate IDs, invalid
scores, NaN/infinity, unknown sample IDs, and unsafe evidence paths are
rejected. Calibrated-score evaluation must be explicitly selected and requires
the fitted score on every prediction.

For scored normal and anomaly labels, the dependency-free evaluator reports
score distribution statistics, AUROC, tie-grouped average precision/AUPRC,
precision@k, and recall@k where valid. Missing predictions and unknown labels
are counted and excluded from supervised metrics. No-positive and no-negative
cases produce unavailable metrics and warnings rather than invented quality.

Unknown-only or otherwise unlabeled evaluation reports review workload only:
scored and explicitly selected counts and fractions, score range and quantiles,
and configured top-k or top-fraction operating points. Labels are not required
for workload evaluation.

## Operating points and artifacts

Explicit thresholds, percentile thresholds, top-k, and top-fraction strategies
produce candidate operating points. Top-k selects an exact deterministic rank;
threshold strategies include score ties. These are candidate review settings
and review-prioritization signals, not automated decisions.

Evaluation artifacts use canonical JSON in an immutable content-addressed
directory. A versioned manifest records size and SHA-256. Publication uses a
same-filesystem temporary directory; validation detects corruption, traversal,
missing files, and unexpected files. Pickle is never used.

Benchmark results are validation artifacts, not product guarantees. Human
expert review remains required. DINOv2, FAISS, and fitted calibration remain
optional and must be selected and provisioned explicitly.

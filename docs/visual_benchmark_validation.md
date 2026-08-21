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

## Executing the reference scorer

The benchmark layer can now execute ADE's configured lightweight reference
scorer directly against one manifest split:

```python
from pathlib import Path

from ade.visual import VisualBenchmarkRunConfig, run_reference_benchmark

execution = run_reference_benchmark(
    Path("benchmarks/example/benchmark.json"),
    config_path=Path("configs/reference_scoring.yaml"),
    run_config=VisualBenchmarkRunConfig(
        split_name="test",
        precision_recall_k=(1, 5, 10),
        top_k=(10,),
    ),
)
result = execution.benchmark
```

The returned execution also retains the exact reference-memory ID, scoring
configuration fingerprint, backend identity, metric, and scoring ID through
`execution.reference_scoring`.

The manifest is loaded in strict mode. ADE validates declared paths and resource
bounds before image decoding, preserves manifest sample IDs through patch
scoring, and records the reference-scoring ID on every prediction. The
configured reference memory must already exist and remain compatible with the
patch extraction, representation, and metric settings.

This runner supports the deterministic lightweight representation only because
that is the only provider currently connected to image-folder reference
scoring. It does not download datasets, fit thresholds, or publish a performance
claim.

## Explicit acceptance policies

Acceptance criteria are declared separately from the measured result. This
prevents the evaluation code from selecting favorable thresholds after seeing
test labels:

```python
from ade.visual import (
    VisualBenchmarkAcceptancePolicy,
    VisualBenchmarkOperatingPointRequirement,
    evaluate_visual_benchmark_acceptance,
)

policy = VisualBenchmarkAcceptancePolicy(
    dataset_name="qualified-dataset",
    dataset_version="2026-08",
    split_name="test",
    min_auroc=0.85,
    min_average_precision=0.75,
    max_missing_predictions=0,
    operating_points=(
        VisualBenchmarkOperatingPointRequirement(
            strategy="top_k",
            value=10,
            min_precision=0.70,
            min_recall=0.50,
            max_selected_fraction=0.10,
        ),
    ),
)
acceptance = evaluate_visual_benchmark_acceptance(result, policy)
```

Required metrics that are unavailable fail closed. Required operating points
must exist exactly once, and workload limits are evaluated alongside precision
and recall. Thresholds shown above are illustrative only; a project must set
them before evaluating its held-out test split and justify them from the
intended review workload and error costs.

Repository tests use a controlled synthetic fixture solely to verify execution,
identity preservation, metric wiring, and failure behavior. They are not
evidence of real-world detection quality.


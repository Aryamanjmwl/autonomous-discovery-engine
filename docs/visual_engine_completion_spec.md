# Visual Engine Completion Specification

## Purpose

This specification defines the stable completion boundary for ADE's visual
engine. Stage 1 establishes contracts, validation, and reproducibility. It does
not claim that deep representations, persistent reference memory, calibrated
reference anomaly detection, or accelerated search are implemented.

## Execution Modes

### Exploratory discovery

Exploratory mode accepts a query dataset and ranks candidate anomalies and
candidate concepts within that dataset. It may use the current deterministic
statistical representation and in-run memory. Scores are relative discovery
signals, not calibrated probabilities or normal/abnormal classifications.

### Reference-based anomaly

Reference mode compares query representations with a separately provisioned
reference dataset representing expected variation. A validation dataset may be
used only to fit or assess calibration. Reference mode is complete only when
the reference memory, calibration record, leakage checks, and evaluation gates
defined here are implemented. Stage 1 defines this boundary but does not run it.

## Dataset Roles

- `query`: data to analyze and rank; required in every execution.
- `reference`: trusted comparison data used to build reference memory; required
  only for reference-based anomaly execution.
- `validation`: held-out data used for calibration and evaluation; optional,
  and forbidden from contributing representations to reference memory.

Each physical dataset identity may have only one role in a request. Reference
and validation data must never be inferred from query data. Fingerprints, not
machine-specific absolute paths, identify dataset content.

## Representations and Backends

A representation backend declares its identifier, version, determinism,
supported modes, device support, and whether it produces patch representations
or anomaly maps. The default remains the lightweight statistical visual
backend. Deep backends are optional, explicitly provisioned extensions and must
not add hidden downloads or network access.

## Reference Memory

Reference memory is a persistent, immutable, versioned artifact derived only
from a reference dataset. Its manifest records dataset and configuration
fingerprints, representation identity, vector shape and dtype, search backend,
creation parameters, and integrity hashes. Updating reference data creates a
new memory version; it never mutates an existing version in place.

Stage 2 implements this storage boundary with content-derived memory IDs,
pickle-free float32 NumPy payloads, canonical JSONL records, artifact hashes,
atomic directory publication, deterministic coreset provenance, and strict
load-time compatibility checks. It does not yet use the memory for anomaly
scoring.

## Scoring and Calibration

Exploratory scores are relative ranking signals. Reference-mode scores measure
distance from reference memory through a declared search backend. Calibration
must record its method, parameters, validation fingerprint, and fitted state.
Thresholds must not be presented as calibrated unless fitted exclusively from
the declared validation role. No Stage 1 interface performs scoring or fitting.

## Anomaly Maps

Backends that support spatial scoring may return an anomaly map aligned to the
source image through recorded preprocessing and resize metadata. Maps must
declare shape, dtype, normalization, coordinate convention, and artifact hash.
Image-level scores must identify the map aggregation method. Backends without
map capability must report that limitation rather than synthesize a map.

## Evidence

Every finding must retain source identity, region coordinates where relevant,
representation/backend identity, score breakdown, and links to integrity-
checked local artifacts. Reference-mode evidence should include nearest
reference neighbors without leaking validation examples into reference memory.
All findings remain candidates requiring human review.

## Evaluation

Reference-mode evaluation uses a declared, held-out validation dataset and
reports dataset fingerprints, metric definitions, thresholds, uncertainty, and
sample counts. At minimum, later implementation must support image-level and,
when annotations exist, localization evaluation. Evaluation artifacts must be
reproducible from manifests and must not silently tune on query data.

## Reproducibility

Every execution result records contract schema version, dataset fingerprints,
effective configuration fingerprint, backend identity, random seed,
deterministic policy, runtime versions, device selection, and artifact hashes.
Dataset fingerprints use normalized relative paths, stable ordering, and
streaming SHA-256 content hashes. Host-specific absolute paths are excluded.
The reproducibility boundary rejects one content/config fingerprint assigned to
multiple dataset roles, even when the copied datasets have different paths.
Manifest publication uses a same-directory temporary file, durable flush, and
atomic publication; existing immutable manifests are not replaced unless the
caller explicitly opts into replacement.

## Resource Controls

Requests require finite positive bounds for batch size, worker count, memory,
file count, and file size. Device policy is explicit (`cpu`, `auto`, or a
provisioned accelerator). Cache reads and writes follow an explicit policy.
Implementations must fail with structured errors when a bound cannot be met;
they must not silently use unbounded resources.

## Acceptance Gates

The complete visual engine must pass these gates before reference mode is
described as implemented:

1. Contract and manifest schemas round-trip and reject unknown versions.
2. Dataset-role validation prevents query/reference/validation leakage.
3. Identical inputs and effective configuration produce identical fingerprints.
4. Reference memory is versioned, integrity checked, and reproducible.
5. Offline model provisioning succeeds without implicit network access.
6. Exact NumPy search is a tested correctness baseline for optional acceleration.
7. Scores, calibration, maps, evidence, and evaluation retain provenance.
8. Deterministic runs meet documented tolerance on supported devices.
9. Resource limits fail safely and are covered by tests.
10. Existing CLI, reports, and Studio behavior remain backward compatible.

## Explicitly Deferred

Stage 3 implements deterministic PatchCore-style exact reference scoring,
image aggregation, spatial anomaly maps, coverage evidence, and immutable map
artifacts. Scores are raw, uncalibrated review-prioritization signals; uncovered
pixels remain `NaN`. DINOv2, CLIP, ResNet, FAISS, GPU execution, model
downloading, fitted calibration, benchmark claims, Studio integration, and
production dataset/model registries remain deferred.

Stage 4A defines provider metadata, bounded batch encoding, representation
records, capability declarations, and configuration fingerprints. The existing
lightweight statistical features are available through this boundary with
identical output, while the legacy pipeline remains unchanged. Deep provider
names are configuration schemas only: they perform no inference and raise a
clear provisioning error if selected. A future executable provider must declare
its exact preprocessing, normalization, model artifact, dimension, device, and
determinism semantics before it can satisfy the acceptance gates.

Stage 4B implements that execution boundary for explicitly provisioned DINOv2
models without making deep packages mandatory. Optional packages load lazily,
offline mode requires a local path, downloads require explicit opt-in, and an
injectable adapter permits dependency-free conformance tests. This establishes
representation mechanics and provenance only; it does not establish calibration,
scientific validity, benchmark quality, or automated truth.

Stage 4C implements optional CPU FAISS while retaining exact NumPy as the
default oracle. Conformance covers Euclidean/cosine distance, top-k clamping,
validation, neighbor identity, and canonical equal-distance ordering. Numeric
differences are accepted only within documented tolerance; this is not a speed,
quality, or detection benchmark claim.

Stage 4D implements the optional calibration and threshold-evaluation
foundation. Identity retains raw scores; empirical-percentile and minmax are
calibrated scores only when their fitted metadata exists. Explicit, percentile,
and top-fraction thresholds are candidate operating points. Complete labeled
held-out data enables supervised metrics; unlabeled or partially labeled data
supports review-workload estimates only. Versioned canonical JSON artifacts
retain fingerprints, limitations, integrity hashes, and human-review status.
This layer is not enabled by default and does not establish a universal anomaly
probability or remove the need for human expert review.

Stage 4E implements benchmark-manifest validation, explicit prediction input,
dependency-free AUROC and average-precision ranking metrics, precision/recall at
configured ranks, workload metrics, and explicit/percentile/top-k/top-fraction
operating points. Datasets are externally provisioned and strict mode validates
declared local files; ADE never downloads public benchmark data automatically.
Canonical evaluation artifacts preserve hashes and provenance. These results
are validation artifacts, not product guarantees or public benchmark claims,
and every operating point requires human expert review.

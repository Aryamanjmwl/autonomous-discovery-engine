# Opt-in visual reference scoring

ADE can compare query-image patches with a separately built immutable reference
memory and attach raw distance evidence plus spatial anomaly maps to the normal
image-folder report. The workflow is explicit and disabled by default. It does
not replace the existing exploratory novelty ranking.

Reference data should represent expected variation and must be physically
separate from query and validation data. ADE derives a content-only identity
from canonical relative paths, file sizes, and SHA-256 hashes, then rejects one
identity assigned to multiple roles. Execution configuration is recorded
separately for reproducibility.

Scores are uncalibrated distances for review prioritization, not probabilities
or automatic normal/abnormal decisions.

## 1. Configure the reference-memory build

The default lightweight representation and Euclidean metric need no custom
configuration. To control memory size or select a deterministic coreset, create
a build configuration such as `configs/reference_build.yaml`:

```yaml
visual_engine:
  execution_mode: reference_anomaly
  dataset_roles: [query, reference]
  reference_memory:
    enabled: true
    metric: euclidean
    exact_search_metric: euclidean
    storage_root: data/reference_memory
    coreset_strategy: deterministic_farthest_first
    maximum_vectors: 10000
    selection_ratio: 0.25
    seed: 42
```

Reference scoring stays disabled during this build step, so a manifest path is
not required yet. Omit the coreset settings to retain every vector up to the
configured maximum.

## 2. Build the immutable memory

```powershell
python -m ade.cli --build-reference-memory data/reference/normal_images `
  --reference-memory-output data/reference_memory `
  --config configs/reference_build.yaml
```

The command prints a result similar to:

```text
ADE reference memory ready.
Reference images: 24
Extracted patches: 384
Stored vectors: 96
Memory ID: <memory-id>
Manifest: .../data/reference_memory/<memory-id>/manifest.json
```

The directory is content-addressed and immutable. Do not edit
`manifest.json`, `vectors.npy`, or `records.jsonl` in place. Repeating the
same build resolves to the same validated memory; changed files or
representation settings create a new memory version.

## 3. Enable reference scoring explicitly

Create a separate scoring configuration and set `manifest_path` to the exact
path printed by the build:

```yaml
visual_engine:
  execution_mode: reference_anomaly
  dataset_roles: [query, reference]
  backend_id: statistical_visual_v2
  backend_version: "1"
  representation:
    provider: lightweight
    device: cpu
    batch_size: 16
    model_name: null
    model_path: null
    normalize: true
    allow_download: false
    options: {}
  reference_memory:
    enabled: true
    manifest_path: data/reference_memory/<memory-id>/manifest.json
    metric: euclidean
    exact_search_metric: euclidean
    memory_map: true
  reference_scoring:
    enabled: true
    search_backend: exact_numpy
    metric: euclidean
    patch_strategy: nearest_neighbor
    neighbor_count: 1
    image_aggregation: max_patch
    map_projection: overlap_mean
    multi_scale_fusion: max
    save_raw_maps: true
    save_coverage: true
    save_preview: false
```

The patch extraction and representation settings used for scoring must remain
compatible with those used to build the memory. A relative manifest path is
resolved from the process working directory.

## 4. Run and validate

```powershell
python -m ade.cli --input data/query/images `
  --output data/reports/reference_review.md `
  --config configs/reference_scoring.yaml
python -m ade.cli --validate-report data/reports/reference_review.json
```

The run produces the normal Markdown and JSON reports plus a content-addressed
artifact directory:

```text
data/reports/reference_review_reference_scoring/<scoring-id>/
  manifest.json
  summary.json
  maps/
```

The report exposes `reference_scoring_summary` and
`spatial_anomaly_map_summary` only after those artifacts have been published
and fingerprinted successfully.

## Compatibility and failure behavior

Before publication, ADE verifies:

- bounded, readable reference inputs and unique patch identities;
- reference-memory manifest and payload hashes;
- representation provider name, version, dimension, and configuration fingerprint;
- Euclidean or cosine metric compatibility;
- distinct content identities for query and reference datasets;
- configured vector and coreset limits.

The image-folder integration currently accepts only the deterministic
lightweight provider. DINOv2 remains an explicitly provisioned library
foundation and is not wired into this CLI path. Cancellation before finalization
prevents publication; after finalization begins, the atomic publication step is
allowed to finish consistently.

Reference evidence remains separate from exploratory candidate ranking. Review
both signals and do not interpret raw distance as calibrated probability.

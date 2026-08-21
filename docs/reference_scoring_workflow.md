# Opt-in visual reference scoring

ADE can attach raw reference-memory distance evidence and spatial anomaly maps
to a normal image-folder report. This path is explicit and disabled by default.
It does not replace the existing exploratory novelty ranking.

Use a reference dataset only when it represents expected variation and is
physically separate from the query data. ADE rejects identical query and
reference fingerprints. Scores are uncalibrated distances for review
prioritization, not probabilities or automatic normal/abnormal decisions.

## 1. Build an immutable reference memory

Reference-memory construction currently uses the typed Python API. The following
example uses the same deterministic lightweight representation as the
image-folder pipeline:

```python
from pathlib import Path

from ade.adapters.image_adapter import ImageAdapter
from ade.preprocessing.patch_extractor import PatchExtractor
from ade.representation.embedding_engine import EmbeddingEngine
from ade.visual import (
    ReferenceVectorRecord,
    VisualDatasetRole,
    VisualEngineConfig,
    build_reference_memory,
    fingerprint_visual_dataset,
)
from ade.visual.representation import LightweightVisualRepresentationProvider

reference_dir = Path("data/reference/normal_images")
visual_config = VisualEngineConfig()
images = ImageAdapter(reference_dir).load()
patches = [
    patch
    for image in images
    for patch in PatchExtractor(patch_size=64, stride=64).extract_from_path(image.path)
]
embeddings = EmbeddingEngine().embed_patches(patches)
provider = LightweightVisualRepresentationProvider(visual_config.representation)
dataset = fingerprint_visual_dataset(
    reference_dir,
    (image.path for image in images),
    visual_config,
)

records = tuple(
    ReferenceVectorRecord(
        vector_id=embedding.patch_id or embedding.patch.patch_id,
        source_identity=embedding.patch.source_path.relative_to(reference_dir).as_posix(),
        vector=embedding.vector,
        x=embedding.patch.x,
        y=embedding.patch.y,
        width=embedding.patch.width,
        height=embedding.patch.height,
        scale_id=embedding.patch.scale_id,
        scale_label=embedding.patch.scale_label,
        metadata=embedding.metadata,
    )
    for embedding in embeddings
)

with build_reference_memory(
    records,
    storage_root=Path("data/reference_memory"),
    dataset_role=VisualDatasetRole.REFERENCE,
    reference_dataset_fingerprint=dataset.fingerprint,
    configuration_fingerprint=provider.metadata.configuration_fingerprint,
    backend_id=provider.metadata.provider_name,
    backend_version=provider.metadata.provider_version,
    distance_metric="euclidean",
) as memory:
    print(memory.root / "manifest.json")
```

The printed directory is content-addressed and immutable. Do not edit
`manifest.json`, `vectors.npy`, or `records.jsonl` in place. Rebuilding
from changed data or settings produces a different memory ID.

## 2. Enable reference scoring explicitly

Create a separate configuration file. Keep the query input outside the reference
dataset and set `manifest_path` to the exact immutable manifest printed above:

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

Settings omitted from this file inherit ADE defaults. A relative manifest path is
resolved from the process working directory.

## 3. Run and validate

```powershell
python -m ade.cli --input data/query/images --output data/reports/reference_review.md --config configs/reference_review.yaml
python -m ade.cli --validate-report data/reports/reference_review.json
```

The run produces the normal Markdown and JSON reports plus a content-addressed
artifact directory beside the report:

```text
data/reports/reference_review_reference_scoring/<scoring-id>/
  manifest.json
  summary.json
  maps/
```

The report exposes `reference_scoring_summary` and
`spatial_anomaly_map_summary` only after those artifacts have been written and
fingerprinted successfully.

## Compatibility and failure behavior

Before scoring, ADE verifies:

- the query dataset content fingerprint;
- the reference-memory manifest and every declared payload hash;
- representation provider name, version, dimension, and configuration fingerprint;
- Euclidean or cosine metric compatibility;
- distinct query and reference dataset identities.

The image-folder integration currently accepts only the lightweight provider.
DINOv2 remains an explicitly provisioned library foundation and is not wired
into this CLI path. Cancellation before finalization prevents scoring artifacts
and the report from being published. Once finalization begins, publication
finishes consistently.

Reference evidence is deliberately separate from the exploratory candidate
ranking in this stage. Review both signals; do not interpret the raw distance as
a calibrated probability.

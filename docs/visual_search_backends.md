# Visual Search Backends

ADE treats `ExactNumpySearch` as the correctness oracle for reference-memory
and PatchCore-style scoring. Stage 4C adds a typed selection boundary and an
optional CPU FAISS implementation without changing that default.

## Backend contract and provenance

`VisualSearchBackend` returns existing `ReferenceSearchResult` and
`ReferenceNeighbor` records. `SearchBackendMetadata` records backend/version,
metric, dimension, float32 dtype, CPU device, determinism, configuration
fingerprint, and `calibrated=false`. Reference scoring records this metadata in
typed and artifact summaries while remaining disabled by default.

## Optional provisioning

ADE declares no mandatory FAISS dependency. The `faiss` module is imported
inside construction only after `backend: faiss` is selected. Missing
`faiss-cpu` raises `VisualProvisioningError` with installation guidance and the
dependency-free `ExactNumpySearch` fallback. GPU FAISS is unsupported. Loading
configuration alone does not import FAISS.

## Conformance

Euclidean search converts `IndexFlatL2` squared output to Euclidean distance.
Cosine search normalizes vectors, uses `IndexFlatIP`, and returns
`1 - similarity`; zero vectors retain ADE's distance-1 convention.

FAISS does not guarantee stable equal-distance order. ADE retrieves every
bounded reference row and sorts by `(distance, vector_id, reference_row)` before
top-k selection, including ties at the cutoff. Top-k above reference count is
clamped like the NumPy oracle. Small numeric differences across versions and
platforms are accepted within tolerance; this is not a performance or quality
claim. Outputs remain uncalibrated human-review signals.

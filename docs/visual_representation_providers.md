# Visual Representation Providers

ADE's visual representation boundary separates patch encoding from reference
memory, scoring, maps, reports, and Studio. It is backend-neutral and does not
make a particular model framework part of the visual-engine contract.

## Contracts

`VisualRepresentationProvider` declares stable metadata and implements one
bounded `encode_batch` operation. Inputs are existing ADE `Patch` records;
outputs are ordered `RepresentationRecord` values inside a validated
`RepresentationBatch`. `RepresentationProviderMetadata` records:

- provider name and version;
- feature dimension and float32 dtype;
- normalization semantics;
- device identity and deterministic status;
- effective representation-configuration fingerprint;
- patch/image and optional-dependency capabilities.

This payload supplies the representation provenance required by immutable
reference memories and scoring results. A consumer must continue validating
dimension, provider identity, configuration fingerprint, and metric
compatibility at its own boundary.

## Lightweight compatibility provider

`LightweightVisualRepresentationProvider` is an adapter over the existing
deterministic `EmbeddingEngine`. It delegates feature extraction unchanged, so
the default CLI, reports, embeddings, and scores retain their existing values.
The provider is CPU-only, deterministic, float32, and identifies normalization
as `provider_defined` because the statistical feature vector contains several
documented component ranges rather than one hidden vector normalization step.

The default configuration selects `lightweight`. Provider use remains optional;
the legacy exploratory pipeline is not rerouted in Stage 4A.

## Optional DINOv2 provider

`DINOv2VisualRepresentationProvider` implements the provider boundary while
keeping its runtime optional. Importing ADE or constructing the lightweight
provider does not import `torch`, `transformers`, or `timm`. Those packages are
resolved lazily only after `provider: dinov2` is explicitly selected. A missing
package raises `VisualProvisioningError` with the provider, missing package,
suggested optional environment, and reminder that lightweight needs no deep
dependency. ADE adds no mandatory or optional dependency metadata in Stage 4B.

DINOv2 configuration declares `model_name`, optional `model_path`, explicit
`cpu` or `cuda`, bounded `batch_size`, `normalize`, `allow_download`, and JSON
provider `options`. The offline-safe default is `allow_download: false`. In that
mode a local `model_path` is required and the Transformers loader receives
`local_files_only=true`. A remote `model_name` is considered only when the user
sets `allow_download: true`; this explicit choice may contact the configured
model repository. ADE never silently changes that setting.

The provider extracts the first token from the model's last hidden state,
returns finite float32 vectors, and optionally applies explicit L2
normalization. Feature dimension is discovered from the loaded model. Metadata
records the installed Transformers version where available, model identity,
device, normalization, determinism declaration, configuration fingerprint, and
`calibrated=false`. CPU is the default; CUDA is optional and must be requested.
Determinism is declared by the adapter and must be evaluated for the selected
runtime/device.

The injectable `DINOv2ModelAdapter` boundary allows contract tests and custom
local loaders without importing a deep framework. CLIP and custom provider
execution remain deferred.

Example offline configuration:

```yaml
visual_engine:
  representation:
    provider: dinov2
    model_name: dinov2-base
    model_path: models/dinov2-base
    device: cpu
    batch_size: 8
    normalize: true
    allow_download: false
    options: {}
```

## Interpretation limits

Representations and distances derived from them are review-prioritization
signals. They are not calibrated probabilities, scientific truth, or automated
normal/abnormal determinations. Provider integration does not establish model
fitness, benchmark quality, or domain validity; those require separate held-out
evaluation and human review.

Reference retrieval is separate. See `visual_search_backends.md` for the exact
NumPy default and optional FAISS conformance semantics.

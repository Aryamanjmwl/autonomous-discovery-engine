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

## Future deep providers

`dinov2`, `clip`, and `custom` are configuration identities, not executable
implementations. Selecting one explicitly raises `VisualProvisioningError`
until a separately tested adapter and locally provisioned model artifact exist.
Merely loading the default configuration imports no deep-learning package and
performs no network access.

A future DINOv2 adapter will implement the same bounded batch contract, declare
its exact model/version, preprocessing and normalization semantics, output
dimension, device, determinism limits, local artifact identity, and effective
configuration fingerprint. It must not download weights implicitly or alter the
lightweight default.

## Interpretation limits

Representations and distances derived from them are review-prioritization
signals. They are not calibrated probabilities, scientific truth, or automated
normal/abnormal determinations. Provider integration does not establish model
fitness, benchmark quality, or domain validity; those require separate held-out
evaluation and human review.

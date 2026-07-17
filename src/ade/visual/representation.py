"""Backend-neutral visual representation provider contracts and adapters."""

from __future__ import annotations

import json
import hashlib
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

import numpy as np

from ade.preprocessing.patch_extractor import Patch
from ade.representation.embedding_engine import EmbeddingEngine
from ade.visual.errors import (
    VisualConfigurationError,
    VisualIntegrityError,
    VisualProvisioningError,
)


@dataclass(frozen=True)
class RepresentationProviderConfig:
    """Configuration selecting one explicitly provisioned representation provider."""

    provider: str = "lightweight"
    device: str = "cpu"
    batch_size: int = 16
    model_path: str | None = None
    options: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.provider not in {"lightweight", "dinov2", "clip", "custom"}:
            raise VisualConfigurationError(
                "Unsupported visual representation provider",
                context={"provider": self.provider},
            )
        if self.device not in {"cpu", "auto", "accelerator"}:
            raise VisualConfigurationError(
                "representation.device must be cpu, auto, or accelerator"
            )
        if not isinstance(self.batch_size, int) or isinstance(self.batch_size, bool):
            raise VisualConfigurationError("representation.batch_size must be an integer")
        if self.batch_size <= 0 or self.batch_size > 4096:
            raise VisualConfigurationError("representation.batch_size must be between 1 and 4096")
        if self.model_path is not None and not self.model_path.strip():
            raise VisualConfigurationError("representation.model_path must be non-empty")
        try:
            json.dumps(dict(self.options), sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise VisualConfigurationError(
                "representation.options must be finite JSON data"
            ) from error
        if self.provider == "lightweight":
            if self.device != "cpu" or self.model_path is not None or self.options:
                raise VisualConfigurationError(
                    "lightweight representation requires cpu and accepts no model_path or options"
                )
        elif self.provider == "custom" and self.model_path is None:
            raise VisualConfigurationError("custom representation requires an explicit model_path")

    def fingerprint(self) -> str:
        """Return a stable identity for all representation-affecting configuration."""

        self.validate()
        payload = {
            "provider": self.provider,
            "device": self.device,
            "batch_size": self.batch_size,
            "model_path": self.model_path,
            "options": dict(self.options),
        }
        return hashlib.sha256(
            json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
                "utf-8"
            )
        ).hexdigest()


@dataclass(frozen=True)
class RepresentationProviderMetadata:
    """Stable capability and provenance metadata declared by a provider."""

    provider_name: str
    provider_version: str
    feature_dimension: int
    dtype: str
    normalization: str
    device: str
    deterministic: bool
    configuration_fingerprint: str
    supports_patch_encoding: bool = True
    supports_image_encoding: bool = False
    requires_optional_dependencies: bool = False

    def __post_init__(self) -> None:
        if not self.provider_name or not self.provider_version:
            raise VisualIntegrityError("Representation provider identity must be non-empty")
        if self.feature_dimension <= 0:
            raise VisualIntegrityError("Representation feature dimension must be positive")
        if self.dtype != "float32":
            raise VisualIntegrityError("Representation providers currently require float32")
        if self.normalization not in {"none", "provider_defined", "l2"}:
            raise VisualIntegrityError("Unsupported representation normalization semantics")
        if not self.device:
            raise VisualIntegrityError("Representation device identity must be non-empty")
        if len(self.configuration_fingerprint) != 64 or any(
            value not in "0123456789abcdef" for value in self.configuration_fingerprint
        ):
            raise VisualIntegrityError("Representation configuration fingerprint must be SHA-256")

    def provenance_payload(self) -> dict[str, Any]:
        return {
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "feature_dimension": self.feature_dimension,
            "dtype": self.dtype,
            "normalization": self.normalization,
            "device": self.device,
            "deterministic": self.deterministic,
            "configuration_fingerprint": self.configuration_fingerprint,
        }


@dataclass(frozen=True)
class RepresentationRecord:
    """One finite provider output aligned to a stable source record ID."""

    record_id: str
    vector: np.ndarray
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        vector = np.asarray(self.vector)
        if not self.record_id:
            raise VisualIntegrityError("Representation record ID must be non-empty")
        if vector.dtype != np.float32 or vector.ndim != 1 or vector.size == 0:
            raise VisualIntegrityError("Representation vector must be non-empty 1D float32")
        if not np.all(np.isfinite(vector)):
            raise VisualIntegrityError("Representation vector must be finite")
        try:
            json.dumps(dict(self.metadata), sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise VisualIntegrityError(
                "Representation metadata must be finite JSON data"
            ) from error
        object.__setattr__(self, "vector", np.ascontiguousarray(vector))


@dataclass(frozen=True)
class RepresentationBatch:
    """Validated ordered results from one provider batch call."""

    records: tuple[RepresentationRecord, ...]
    provider: RepresentationProviderMetadata

    def __post_init__(self) -> None:
        ids = [record.record_id for record in self.records]
        if len(ids) != len(set(ids)):
            raise VisualIntegrityError("Representation record IDs must be unique within a batch")
        dimensions = {record.vector.size for record in self.records}
        if dimensions and dimensions != {self.provider.feature_dimension}:
            raise VisualIntegrityError(
                "Representation vectors do not match provider feature dimension",
                context={
                    "dimensions": sorted(dimensions),
                    "expected": self.provider.feature_dimension,
                },
            )


@runtime_checkable
class VisualRepresentationProvider(Protocol):
    """Backend-neutral, bounded batch representation provider contract."""

    @property
    def metadata(self) -> RepresentationProviderMetadata: ...

    def encode_batch(self, patches: Sequence[Patch]) -> RepresentationBatch: ...


class LightweightVisualRepresentationProvider:
    """Compatibility adapter over ADE's unchanged statistical embedding engine."""

    def __init__(self, config: RepresentationProviderConfig | None = None) -> None:
        self.config = config or RepresentationProviderConfig()
        self.config.validate()
        if self.config.provider != "lightweight":
            raise VisualConfigurationError("Lightweight provider requires provider=lightweight")
        self._engine = EmbeddingEngine()
        self._metadata = RepresentationProviderMetadata(
            provider_name=self._engine.backend_name,
            provider_version="1",
            feature_dimension=len(self._engine.feature_names),
            dtype="float32",
            normalization="provider_defined",
            device="cpu",
            deterministic=True,
            configuration_fingerprint=self.config.fingerprint(),
        )

    @property
    def metadata(self) -> RepresentationProviderMetadata:
        return self._metadata

    def encode_batch(self, patches: Sequence[Patch]) -> RepresentationBatch:
        if len(patches) > self.config.batch_size:
            raise VisualIntegrityError(
                "Representation batch exceeds configured bound",
                context={"count": len(patches), "maximum": self.config.batch_size},
            )
        embeddings = self._engine.embed_patches(list(patches))
        records = tuple(
            RepresentationRecord(
                record_id=embedding.patch_id or embedding.patch.patch_id,
                vector=embedding.vector,
                metadata={"backend_name": self._engine.backend_name},
            )
            for embedding in embeddings
        )
        return RepresentationBatch(records, self.metadata)


def create_visual_representation_provider(
    config: RepresentationProviderConfig,
) -> VisualRepresentationProvider:
    """Resolve an executable provider; future/deep schemas fail only when selected."""

    config.validate()
    if config.provider == "lightweight":
        return LightweightVisualRepresentationProvider(config)
    raise VisualProvisioningError(
        "The selected visual representation provider is not implemented or provisioned",
        context={
            "provider": config.provider,
            "required_action": "Install and explicitly provision a future provider adapter",
        },
    )

"""Backend-neutral visual representation provider contracts and adapters."""

from __future__ import annotations

import hashlib
import importlib
import importlib.metadata
import json
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
    model_name: str | None = None
    model_path: str | None = None
    normalize: bool = True
    allow_download: bool = False
    options: Mapping[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.provider not in {"lightweight", "dinov2", "clip", "custom"}:
            raise VisualConfigurationError(
                "Unsupported visual representation provider",
                context={"provider": self.provider},
            )
        if self.device not in {"cpu", "cuda", "auto", "accelerator"}:
            raise VisualConfigurationError(
                "representation.device must be cpu, cuda, auto, or accelerator"
            )
        if not isinstance(self.batch_size, int) or isinstance(self.batch_size, bool):
            raise VisualConfigurationError("representation.batch_size must be an integer")
        if self.batch_size <= 0 or self.batch_size > 4096:
            raise VisualConfigurationError("representation.batch_size must be between 1 and 4096")
        if self.model_path is not None and not self.model_path.strip():
            raise VisualConfigurationError("representation.model_path must be non-empty")
        if self.model_name is not None and not self.model_name.strip():
            raise VisualConfigurationError("representation.model_name must be non-empty")
        if not isinstance(self.normalize, bool) or not isinstance(self.allow_download, bool):
            raise VisualConfigurationError(
                "representation.normalize and allow_download must be booleans"
            )
        try:
            json.dumps(dict(self.options), sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise VisualConfigurationError(
                "representation.options must be finite JSON data"
            ) from error
        if self.provider == "lightweight":
            if (
                self.device != "cpu"
                or self.model_name is not None
                or self.model_path is not None
                or not self.normalize
                or self.allow_download
                or self.options
            ):
                raise VisualConfigurationError(
                    "lightweight representation requires its default cpu configuration"
                )
        elif self.provider == "dinov2":
            if self.device not in {"cpu", "cuda"}:
                raise VisualConfigurationError(
                    "dinov2 representation requires an explicit cpu or cuda device"
                )
            if not self.model_path and not (self.allow_download and self.model_name):
                raise VisualConfigurationError(
                    "dinov2 requires model_path, or model_name with allow_download=true"
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
            "model_name": self.model_name,
            "model_path": self.model_path,
            "normalize": self.normalize,
            "allow_download": self.allow_download,
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
    provider_details: Mapping[str, Any] = field(default_factory=dict)

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
        try:
            json.dumps(dict(self.provider_details), sort_keys=True, allow_nan=False)
        except (TypeError, ValueError) as error:
            raise VisualIntegrityError("Provider details must be finite JSON data") from error

    def provenance_payload(self) -> dict[str, Any]:
        payload = {
            "provider_name": self.provider_name,
            "provider_version": self.provider_version,
            "feature_dimension": self.feature_dimension,
            "dtype": self.dtype,
            "normalization": self.normalization,
            "device": self.device,
            "deterministic": self.deterministic,
            "configuration_fingerprint": self.configuration_fingerprint,
        }
        if self.provider_details:
            payload["provider_details"] = dict(self.provider_details)
        return payload


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


@runtime_checkable
class DINOv2ModelAdapter(Protocol):
    """Minimal injectable runtime boundary for a provisioned DINOv2 model."""

    @property
    def model_id(self) -> str: ...

    @property
    def provider_version(self) -> str: ...

    @property
    def feature_dimension(self) -> int: ...

    @property
    def deterministic(self) -> bool: ...

    def encode(self, patches: Sequence[Patch]) -> np.ndarray: ...


class DINOv2VisualRepresentationProvider:
    """Optional DINOv2 provider with lazy imports and explicit provisioning."""

    def __init__(
        self,
        config: RepresentationProviderConfig,
        *,
        adapter: DINOv2ModelAdapter | None = None,
    ) -> None:
        config.validate()
        if config.provider != "dinov2":
            raise VisualConfigurationError("DINOv2 provider requires provider=dinov2")
        self.config = config
        self._adapter = adapter or _load_transformers_dinov2_adapter(config)
        self._metadata = RepresentationProviderMetadata(
            provider_name="dinov2",
            provider_version=self._adapter.provider_version,
            feature_dimension=self._adapter.feature_dimension,
            dtype="float32",
            normalization="l2" if config.normalize else "none",
            device=config.device,
            deterministic=self._adapter.deterministic,
            configuration_fingerprint=config.fingerprint(),
            supports_patch_encoding=True,
            supports_image_encoding=True,
            requires_optional_dependencies=True,
            provider_details={
                "model_id": self._adapter.model_id,
                "model_name": config.model_name,
                "model_path": config.model_path,
                "allow_download": config.allow_download,
                "calibrated": False,
            },
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
        ids = [patch.patch_id for patch in patches]
        if any(not record_id for record_id in ids) or len(ids) != len(set(ids)):
            raise VisualIntegrityError("DINOv2 input patch IDs must be non-empty and unique")
        vectors = np.asarray(self._adapter.encode(patches))
        if vectors.dtype != np.float32 or vectors.ndim != 2:
            raise VisualIntegrityError("DINOv2 adapter must return a float32 matrix")
        if vectors.shape != (len(patches), self.metadata.feature_dimension):
            raise VisualIntegrityError(
                "DINOv2 adapter output shape is incompatible with provider metadata",
                context={"shape": list(vectors.shape)},
            )
        if not np.all(np.isfinite(vectors)):
            raise VisualIntegrityError("DINOv2 adapter returned non-finite vectors")
        if self.config.normalize and vectors.size:
            norms = np.linalg.norm(vectors.astype(np.float64), axis=1, keepdims=True)
            normalized = np.zeros_like(vectors, dtype=np.float32)
            np.divide(vectors, norms, out=normalized, where=norms != 0.0)
            vectors = normalized
        records = tuple(
            RepresentationRecord(
                patch.patch_id,
                vectors[index],
                {"provider": "dinov2", "model_id": self._adapter.model_id},
            )
            for index, patch in enumerate(patches)
        )
        return RepresentationBatch(records, self.metadata)


class _TransformersDINOv2Adapter:
    """Private adapter receiving optional modules only after explicit selection."""

    def __init__(self, config: RepresentationProviderConfig, torch: Any, transformers: Any) -> None:
        from pathlib import Path

        source = config.model_path or config.model_name
        if source is None:
            raise VisualProvisioningError("DINOv2 model source was not configured")
        if config.model_path is not None and not Path(config.model_path).exists():
            raise VisualProvisioningError(
                "Configured local DINOv2 model path does not exist",
                context={"provider": "dinov2", "model_path": config.model_path},
            )
        try:
            self._processor = transformers.AutoImageProcessor.from_pretrained(
                source, local_files_only=not config.allow_download
            )
            self._model = transformers.AutoModel.from_pretrained(
                source, local_files_only=not config.allow_download
            ).to(config.device)
            self._model.eval()
        except Exception as error:
            raise VisualProvisioningError(
                "DINOv2 model could not be loaded from the configured source",
                context={
                    "provider": "dinov2",
                    "model_path": config.model_path,
                    "model_name": config.model_name,
                    "allow_download": config.allow_download,
                },
            ) from error
        self._torch = torch
        self._device = config.device
        self._model_id = str(source)
        self._dimension = int(self._model.config.hidden_size)

    @property
    def model_id(self) -> str:
        return self._model_id

    @property
    def provider_version(self) -> str:
        try:
            return importlib.metadata.version("transformers")
        except importlib.metadata.PackageNotFoundError:
            return "unknown"

    @property
    def feature_dimension(self) -> int:
        return self._dimension

    @property
    def deterministic(self) -> bool:
        return self._device == "cpu"

    def encode(self, patches: Sequence[Patch]) -> np.ndarray:
        inputs = self._processor(images=[patch.array for patch in patches], return_tensors="pt")
        inputs = {name: value.to(self._device) for name, value in inputs.items()}
        with self._torch.inference_mode():
            output = self._model(**inputs).last_hidden_state[:, 0, :]
        return output.detach().to("cpu").float().numpy().astype(np.float32, copy=False)


def _load_transformers_dinov2_adapter(
    config: RepresentationProviderConfig,
) -> DINOv2ModelAdapter:
    modules: dict[str, Any] = {}
    for package in ("torch", "transformers"):
        try:
            modules[package] = importlib.import_module(package)
        except ImportError as error:
            raise VisualProvisioningError(
                "Optional package required by the selected DINOv2 provider is missing",
                context={
                    "provider": "dinov2",
                    "missing_package": package,
                    "suggested_installation": (
                        "Install torch and transformers in an optional visual-deep environment"
                    ),
                    "lightweight_default": (
                        "The default lightweight provider requires no deep dependencies"
                    ),
                },
            ) from error
    return _TransformersDINOv2Adapter(config, modules["torch"], modules["transformers"])


def create_visual_representation_provider(
    config: RepresentationProviderConfig,
) -> VisualRepresentationProvider:
    """Resolve an executable provider; future/deep schemas fail only when selected."""

    config.validate()
    if config.provider == "lightweight":
        return LightweightVisualRepresentationProvider(config)
    if config.provider == "dinov2":
        return DINOv2VisualRepresentationProvider(config)
    raise VisualProvisioningError(
        "The selected visual representation provider is not implemented or provisioned",
        context={
            "provider": config.provider,
            "required_action": "Install and explicitly provision a future provider adapter",
        },
    )

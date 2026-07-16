"""Typed public boundaries for the ADE visual engine."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import StrEnum
from pathlib import Path
from typing import Any

from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION, VisualEngineConfig
from ade.visual.errors import VisualDatasetRoleError


class VisualDatasetRole(StrEnum):
    """The non-overlapping role assigned to a visual dataset."""

    QUERY = "query"
    REFERENCE = "reference"
    VALIDATION = "validation"


class VisualExecutionMode(StrEnum):
    """Supported visual-engine execution intents."""

    EXPLORATORY = "exploratory"
    REFERENCE_ANOMALY = "reference_anomaly"


@dataclass(frozen=True)
class VisualBackendCapabilities:
    """Capabilities declared by a visual representation/scoring backend."""

    backend_id: str
    backend_version: str
    execution_modes: tuple[VisualExecutionMode, ...]
    deterministic: bool
    supports_cpu: bool
    supports_accelerator: bool = False
    produces_patch_representations: bool = True
    produces_anomaly_maps: bool = False
    requires_model_artifact: bool = False


@dataclass(frozen=True)
class VisualArtifactManifest:
    """Integrity metadata for one local visual-engine artifact."""

    schema_version: int
    artifact_id: str
    artifact_type: str
    relative_path: str
    sha256: str
    size_bytes: int
    media_type: str | None = None


@dataclass(frozen=True)
class VisualReproducibilityManifest:
    """Provenance required to reproduce a visual-engine result."""

    schema_version: int
    dataset_fingerprints: Mapping[VisualDatasetRole, str]
    configuration_fingerprint: str
    backend_id: str
    backend_version: str
    random_seed: int
    deterministic: bool
    python_version: str
    ade_version: str
    device: str


@dataclass(frozen=True)
class VisualEngineRequest:
    """Validated request boundary; execution wiring is intentionally deferred."""

    datasets: Mapping[VisualDatasetRole, Path]
    config: VisualEngineConfig = field(default_factory=VisualEngineConfig)
    request_id: str | None = None

    def validate(self) -> None:
        """Validate role presence, uniqueness, and configuration compatibility."""

        self.config.validate()
        roles = set(self.datasets)
        expected = {VisualDatasetRole(role) for role in self.config.dataset_roles}
        if roles != expected:
            raise VisualDatasetRoleError(
                "Request dataset roles must exactly match configured dataset roles",
                context={
                    "configured": sorted(role.value for role in expected),
                    "provided": sorted(role.value for role in roles),
                },
            )
        resolved: dict[Path, VisualDatasetRole] = {}
        for role, path in self.datasets.items():
            normalized = path.expanduser().resolve()
            previous = resolved.get(normalized)
            if previous is not None:
                raise VisualDatasetRoleError(
                    "A physical dataset cannot be assigned to multiple roles",
                    context={"roles": sorted([previous.value, role.value])},
                )
            resolved[normalized] = role


@dataclass(frozen=True)
class VisualEngineResult:
    """Typed result envelope for future visual-engine execution adapters."""

    schema_version: int
    request_id: str
    execution_mode: VisualExecutionMode
    backend: VisualBackendCapabilities
    reproducibility: VisualReproducibilityManifest
    artifacts: tuple[VisualArtifactManifest, ...] = ()
    findings: tuple[Mapping[str, Any], ...] = ()
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.schema_version != VISUAL_ENGINE_SCHEMA_VERSION:
            raise ValueError(f"Unsupported visual result schema version: {self.schema_version}")

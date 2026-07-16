"""Typed, versioned configuration for visual-engine contract boundaries."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any

from ade.visual.errors import VisualConfigurationError, VisualContractVersionError

VISUAL_ENGINE_SCHEMA_VERSION = 1


class VisualDevicePolicy(StrEnum):
    """Allowed device-selection policies."""

    CPU = "cpu"
    AUTO = "auto"
    ACCELERATOR = "accelerator"


class VisualCachePolicy(StrEnum):
    """Allowed cache read/write policies."""

    DISABLED = "disabled"
    READ_ONLY = "read_only"
    READ_WRITE = "read_write"
    REFRESH = "refresh"


@dataclass(frozen=True)
class VisualResourceLimits:
    """Finite resource limits applied before visual execution."""

    batch_size: int = 16
    max_workers: int = 1
    max_memory_mb: int = 4096
    max_files: int = 100_000
    max_file_size_mb: int = 1024

    def validate(self) -> None:
        for name, value in asdict(self).items():
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise VisualConfigurationError(f"visual_engine.resources.{name} must be positive")
        if self.batch_size > 4096:
            raise VisualConfigurationError(
                "visual_engine.resources.batch_size must not exceed 4096"
            )
        if self.max_workers > 256:
            raise VisualConfigurationError(
                "visual_engine.resources.max_workers must not exceed 256"
            )
        if self.max_memory_mb > 1_048_576:
            raise VisualConfigurationError(
                "visual_engine.resources.max_memory_mb must not exceed 1048576"
            )


@dataclass(frozen=True)
class VisualReferenceMemoryConfig:
    """Configuration for a future persistent reference-memory artifact."""

    enabled: bool = False
    manifest_path: str | None = None
    search_backend: str = "numpy_exact"
    metric: str = "euclidean"
    storage_root: str = "data/reference_memory"
    coreset_strategy: str = "none"
    maximum_vectors: int = 10_000
    selection_ratio: float | None = None
    seed: int = 42
    search_batch_size: int = 128
    memory_map: bool = True
    exact_search_metric: str = "euclidean"

    def validate(self) -> None:
        if self.search_backend != "numpy_exact":
            raise VisualConfigurationError(
                "Only the numpy_exact reference-memory search backend is currently accepted"
            )
        if self.metric not in {"euclidean", "cosine"}:
            raise VisualConfigurationError(
                "visual_engine.reference_memory.metric must be euclidean or cosine"
            )
        if self.exact_search_metric not in {"euclidean", "cosine"}:
            raise VisualConfigurationError(
                "reference_memory.exact_search_metric must be euclidean or cosine"
            )
        if self.metric != self.exact_search_metric:
            raise VisualConfigurationError(
                "reference_memory.metric and exact_search_metric must match"
            )
        if self.coreset_strategy not in {"none", "deterministic_farthest_first"}:
            raise VisualConfigurationError("Unsupported reference-memory coreset strategy")
        if not self.storage_root.strip():
            raise VisualConfigurationError("reference_memory.storage_root must be non-empty")
        if self.maximum_vectors <= 0 or self.maximum_vectors > 10_000_000:
            raise VisualConfigurationError(
                "reference_memory.maximum_vectors must be between 1 and 10000000"
            )
        if self.selection_ratio is not None and not 0.0 < self.selection_ratio <= 1.0:
            raise VisualConfigurationError(
                "reference_memory.selection_ratio must be greater than 0 and at most 1"
            )
        if self.seed < 0 or self.seed > 2**32 - 1:
            raise VisualConfigurationError("reference_memory.seed is outside the supported range")
        if self.search_batch_size <= 0 or self.search_batch_size > 65_536:
            raise VisualConfigurationError(
                "reference_memory.search_batch_size must be between 1 and 65536"
            )
        if not isinstance(self.memory_map, bool):
            raise VisualConfigurationError("reference_memory.memory_map must be a boolean")
        if not self.enabled and self.manifest_path is not None:
            raise VisualConfigurationError(
                "reference_memory.manifest_path requires reference_memory.enabled"
            )


@dataclass(frozen=True)
class VisualReferenceScoringConfig:
    """Strict settings for optional uncalibrated reference scoring."""

    enabled: bool = False
    metric: str = "euclidean"
    patch_strategy: str = "nearest_neighbor"
    neighbor_count: int = 1
    query_batch_size: int = 128
    image_aggregation: str = "max_patch"
    top_fraction: float = 0.1
    map_projection: str = "overlap_mean"
    multi_scale_fusion: str = "max"
    smoothing_sigma: float = 0.0
    save_raw_maps: bool = True
    save_coverage: bool = True
    save_preview: bool = False
    maximum_image_pixels: int = 100_000_000
    display_normalization: bool = False

    def validate(self) -> None:
        if self.metric not in {"euclidean", "cosine"}:
            raise VisualConfigurationError("reference_scoring.metric must be euclidean or cosine")
        if self.patch_strategy not in {"nearest_neighbor", "knn_mean"}:
            raise VisualConfigurationError("Unsupported reference_scoring.patch_strategy")
        if self.neighbor_count <= 0 or self.neighbor_count > 65_536:
            raise VisualConfigurationError(
                "reference_scoring.neighbor_count must be between 1 and 65536"
            )
        if self.patch_strategy == "nearest_neighbor" and self.neighbor_count != 1:
            raise VisualConfigurationError("nearest_neighbor requires neighbor_count=1")
        if self.query_batch_size <= 0 or self.query_batch_size > 65_536:
            raise VisualConfigurationError(
                "reference_scoring.query_batch_size must be between 1 and 65536"
            )
        if self.image_aggregation not in {"max_patch", "top_fraction_mean"}:
            raise VisualConfigurationError("Unsupported reference_scoring.image_aggregation")
        if not 0.0 < self.top_fraction <= 1.0:
            raise VisualConfigurationError("reference_scoring.top_fraction must be in (0, 1]")
        if self.map_projection not in {"overlap_mean", "overlap_max"}:
            raise VisualConfigurationError("Unsupported reference_scoring.map_projection")
        if self.multi_scale_fusion not in {"max", "mean"}:
            raise VisualConfigurationError("Unsupported reference_scoring.multi_scale_fusion")
        if self.smoothing_sigma < 0 or self.smoothing_sigma > 100:
            raise VisualConfigurationError(
                "reference_scoring.smoothing_sigma must be between 0 and 100"
            )
        if self.maximum_image_pixels <= 0 or self.maximum_image_pixels > 1_000_000_000:
            raise VisualConfigurationError(
                "reference_scoring.maximum_image_pixels is outside supported bounds"
            )
        for name in (
            "enabled",
            "save_raw_maps",
            "save_coverage",
            "save_preview",
            "display_normalization",
        ):
            if not isinstance(getattr(self, name), bool):
                raise VisualConfigurationError(f"reference_scoring.{name} must be a boolean")


@dataclass(frozen=True)
class VisualCalibrationConfig:
    """Configuration describing future score calibration intent."""

    enabled: bool = False
    method: str = "none"
    manifest_path: str | None = None

    def validate(self) -> None:
        if self.method not in {"none", "quantile"}:
            raise VisualConfigurationError(
                "visual_engine.calibration.method must be none or quantile"
            )
        if self.enabled and self.method == "none":
            raise VisualConfigurationError("enabled calibration requires an explicit method")
        if not self.enabled and (self.method != "none" or self.manifest_path is not None):
            raise VisualConfigurationError(
                "disabled calibration cannot declare a method or manifest_path"
            )


@dataclass(frozen=True)
class VisualEngineConfig:
    """Effective visual-engine configuration with backward-compatible defaults."""

    schema_version: int = VISUAL_ENGINE_SCHEMA_VERSION
    execution_mode: str = "exploratory"
    dataset_roles: tuple[str, ...] = ("query",)
    backend_id: str = "statistical_visual_v2"
    backend_version: str = "1"
    device_policy: VisualDevicePolicy = VisualDevicePolicy.CPU
    deterministic: bool = True
    random_seed: int = 42
    cache_policy: VisualCachePolicy = VisualCachePolicy.DISABLED
    resources: VisualResourceLimits = field(default_factory=VisualResourceLimits)
    reference_memory: VisualReferenceMemoryConfig = field(
        default_factory=VisualReferenceMemoryConfig
    )
    reference_scoring: VisualReferenceScoringConfig = field(
        default_factory=VisualReferenceScoringConfig
    )
    calibration: VisualCalibrationConfig = field(default_factory=VisualCalibrationConfig)

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> VisualEngineConfig:
        """Build and strictly validate typed configuration from a mapping."""

        data = dict(value or {})
        allowed = {
            "schema_version",
            "execution_mode",
            "dataset_roles",
            "backend_id",
            "backend_version",
            "device_policy",
            "deterministic",
            "random_seed",
            "cache_policy",
            "resources",
            "reference_memory",
            "reference_scoring",
            "calibration",
        }
        unknown = sorted(set(data) - allowed)
        if unknown:
            raise VisualConfigurationError(
                f"Unknown visual_engine configuration fields: {', '.join(unknown)}"
            )
        try:
            resource_data = _mapping(data.get("resources"), "resources")
            memory_data = _mapping(data.get("reference_memory"), "reference_memory")
            scoring_data = _mapping(data.get("reference_scoring"), "reference_scoring")
            calibration_data = _mapping(data.get("calibration"), "calibration")
            roles = data.get("dataset_roles", ("query",))
            if not isinstance(roles, list | tuple) or not all(
                isinstance(role, str) for role in roles
            ):
                raise VisualConfigurationError(
                    "visual_engine.dataset_roles must be a list of roles"
                )
            config = cls(
                schema_version=_integer(data.get("schema_version", 1), "schema_version"),
                execution_mode=str(data.get("execution_mode", "exploratory")),
                dataset_roles=tuple(roles),
                backend_id=str(data.get("backend_id", "statistical_visual_v2")),
                backend_version=str(data.get("backend_version", "1")),
                device_policy=VisualDevicePolicy(str(data.get("device_policy", "cpu"))),
                deterministic=_boolean(data.get("deterministic", True), "deterministic"),
                random_seed=_integer(data.get("random_seed", 42), "random_seed"),
                cache_policy=VisualCachePolicy(str(data.get("cache_policy", "disabled"))),
                resources=VisualResourceLimits(**resource_data),
                reference_memory=VisualReferenceMemoryConfig(**memory_data),
                reference_scoring=VisualReferenceScoringConfig(**scoring_data),
                calibration=VisualCalibrationConfig(**calibration_data),
            )
        except (TypeError, ValueError) as error:
            if isinstance(error, VisualConfigurationError):
                raise
            raise VisualConfigurationError(
                f"Invalid visual_engine configuration: {error}"
            ) from error
        config.validate()
        return config

    def validate(self) -> None:
        """Reject unsupported versions and incompatible execution settings."""

        if self.schema_version != VISUAL_ENGINE_SCHEMA_VERSION:
            raise VisualContractVersionError(
                f"Unsupported visual engine schema version: {self.schema_version}",
                context={"supported_versions": [VISUAL_ENGINE_SCHEMA_VERSION]},
            )
        if self.execution_mode not in {"exploratory", "reference_anomaly"}:
            raise VisualConfigurationError(
                "visual_engine.execution_mode must be exploratory or reference_anomaly"
            )
        allowed_roles = {"query", "reference", "validation"}
        if not self.dataset_roles or len(set(self.dataset_roles)) != len(self.dataset_roles):
            raise VisualConfigurationError(
                "visual_engine.dataset_roles must be unique and non-empty"
            )
        if not set(self.dataset_roles) <= allowed_roles or "query" not in self.dataset_roles:
            raise VisualConfigurationError(
                "visual_engine.dataset_roles must contain query and only supported roles"
            )
        if not self.backend_id.strip() or not self.backend_version.strip():
            raise VisualConfigurationError("visual backend identity must be non-empty")
        if self.random_seed < 0 or self.random_seed > 2**32 - 1:
            raise VisualConfigurationError("visual_engine.random_seed must be between 0 and 2^32-1")
        if self.execution_mode == "exploratory":
            if (
                "reference" in self.dataset_roles
                or self.reference_memory.enabled
                or self.reference_scoring.enabled
            ):
                raise VisualConfigurationError(
                    "exploratory execution cannot enable reference data or reference memory"
                )
            if self.calibration.enabled or "validation" in self.dataset_roles:
                raise VisualConfigurationError(
                    "exploratory execution cannot enable calibration or validation data"
                )
        else:
            if "reference" not in self.dataset_roles or not self.reference_memory.enabled:
                raise VisualConfigurationError(
                    "reference_anomaly execution requires reference role and reference memory"
                )
            if (
                self.reference_scoring.enabled
                and self.reference_scoring.metric != self.reference_memory.metric
            ):
                raise VisualConfigurationError("reference scoring and memory metrics must match")
            if self.calibration.enabled and "validation" not in self.dataset_roles:
                raise VisualConfigurationError(
                    "enabled calibration requires a validation dataset role"
                )
        if self.device_policy is VisualDevicePolicy.ACCELERATOR and self.backend_id.startswith(
            "statistical_visual"
        ):
            raise VisualConfigurationError(
                "the statistical visual backend is incompatible with accelerator-only policy"
            )
        self.resources.validate()
        self.reference_memory.validate()
        self.reference_scoring.validate()
        self.calibration.validate()

    def to_dict(self) -> dict[str, Any]:
        """Return a stable JSON-safe representation."""

        return {
            "schema_version": self.schema_version,
            "execution_mode": self.execution_mode,
            "dataset_roles": list(self.dataset_roles),
            "backend_id": self.backend_id,
            "backend_version": self.backend_version,
            "device_policy": self.device_policy.value,
            "deterministic": self.deterministic,
            "random_seed": self.random_seed,
            "cache_policy": self.cache_policy.value,
            "resources": asdict(self.resources),
            "reference_memory": asdict(self.reference_memory),
            "calibration": asdict(self.calibration),
        }


def _mapping(value: object, name: str) -> dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise VisualConfigurationError(f"visual_engine.{name} must be a mapping")
    return dict(value)


def _integer(value: object, name: str) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise VisualConfigurationError(f"visual_engine.{name} must be an integer")
    return value


def _boolean(value: object, name: str) -> bool:
    if not isinstance(value, bool):
        raise VisualConfigurationError(f"visual_engine.{name} must be a boolean")
    return value

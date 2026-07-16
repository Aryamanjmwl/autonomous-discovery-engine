"""Contract and configuration invariants for the visual-engine boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from ade.config import load_config
from ade.visual import (
    VisualConfigurationError,
    VisualContractVersionError,
    VisualDatasetRole,
    VisualDatasetRoleError,
    VisualEngineConfig,
    VisualEngineRequest,
)


def test_visual_engine_defaults_preserve_current_exploratory_workflow() -> None:
    config = VisualEngineConfig()

    assert config.schema_version == 1
    assert config.execution_mode == "exploratory"
    assert config.dataset_roles == ("query",)
    assert config.backend_id == "statistical_visual_v2"
    assert config.device_policy.value == "cpu"
    assert config.deterministic is True
    assert config.reference_memory.enabled is False


def test_legacy_config_without_visual_section_gets_backward_compatible_defaults(
    tmp_path: Path,
) -> None:
    path = tmp_path / "legacy.yaml"
    path.write_text("preprocessing:\n  patch_size: 32\n", encoding="utf-8")

    config = load_config(path)

    assert config["preprocessing"]["patch_sizes"] == [32]
    assert config["visual_engine"] == VisualEngineConfig().to_dict()


@pytest.mark.parametrize("version", [0, 2, 999])
def test_visual_config_rejects_unsupported_schema_versions(version: int) -> None:
    with pytest.raises(VisualContractVersionError, match="Unsupported"):
        VisualEngineConfig.from_mapping({"schema_version": version})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("batch_size", 0),
        ("batch_size", 4097),
        ("max_workers", 0),
        ("max_workers", 257),
        ("max_memory_mb", 0),
        ("max_memory_mb", 1_048_577),
        ("max_files", 0),
        ("max_file_size_mb", 0),
    ],
)
def test_visual_config_rejects_unbounded_or_invalid_resources(field: str, value: int) -> None:
    with pytest.raises(VisualConfigurationError):
        VisualEngineConfig.from_mapping({"resources": {field: value}})


def test_reference_mode_requires_explicit_reference_role_and_memory() -> None:
    with pytest.raises(VisualConfigurationError, match="reference role"):
        VisualEngineConfig.from_mapping({"execution_mode": "reference_anomaly"})


def test_reference_calibration_requires_validation_role() -> None:
    with pytest.raises(VisualConfigurationError, match="validation"):
        VisualEngineConfig.from_mapping(
            {
                "execution_mode": "reference_anomaly",
                "dataset_roles": ["query", "reference"],
                "reference_memory": {"enabled": True},
                "calibration": {"enabled": True, "method": "quantile"},
            }
        )


def test_valid_reference_configuration_is_descriptive_not_executable() -> None:
    config = VisualEngineConfig.from_mapping(
        {
            "execution_mode": "reference_anomaly",
            "dataset_roles": ["query", "reference", "validation"],
            "reference_memory": {"enabled": True},
            "calibration": {"enabled": True, "method": "quantile"},
        }
    )

    assert config.execution_mode == "reference_anomaly"
    assert config.reference_memory.search_backend == "numpy_exact"


def test_request_rejects_missing_configured_dataset_role(tmp_path: Path) -> None:
    config = VisualEngineConfig.from_mapping(
        {
            "execution_mode": "reference_anomaly",
            "dataset_roles": ["query", "reference"],
            "reference_memory": {"enabled": True},
        }
    )
    request = VisualEngineRequest(
        datasets={VisualDatasetRole.QUERY: tmp_path / "query"},
        config=config,
    )

    with pytest.raises(VisualDatasetRoleError, match="exactly match"):
        request.validate()


def test_request_prevents_dataset_role_leakage(tmp_path: Path) -> None:
    dataset = tmp_path / "same"
    config = VisualEngineConfig.from_mapping(
        {
            "execution_mode": "reference_anomaly",
            "dataset_roles": ["query", "reference"],
            "reference_memory": {"enabled": True},
        }
    )
    request = VisualEngineRequest(
        datasets={
            VisualDatasetRole.QUERY: dataset,
            VisualDatasetRole.REFERENCE: dataset,
        },
        config=config,
    )

    with pytest.raises(VisualDatasetRoleError, match="multiple roles"):
        request.validate()


def test_structured_visual_error_is_machine_readable() -> None:
    error = VisualDatasetRoleError("leakage", context={"role": "validation"})

    assert error.to_dict() == {
        "code": "invalid_visual_dataset_roles",
        "message": "leakage",
        "context": {"role": "validation"},
    }

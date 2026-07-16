"""Structured errors for visual-engine contract boundaries."""

from __future__ import annotations

from typing import Any


class VisualEngineError(Exception):
    """Base error carrying a stable code and JSON-safe context."""

    code = "visual_engine_error"

    def __init__(self, message: str, *, context: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.context = dict(context or {})

    def to_dict(self) -> dict[str, Any]:
        """Return a machine-readable error object."""

        return {"code": self.code, "message": self.message, "context": self.context}


class VisualConfigurationError(VisualEngineError, ValueError):
    """Raised when visual configuration is invalid or incompatible."""

    code = "visual_configuration_error"


class VisualContractVersionError(VisualEngineError, ValueError):
    """Raised when a visual contract schema version is unsupported."""

    code = "unsupported_visual_schema_version"


class VisualDatasetRoleError(VisualEngineError, ValueError):
    """Raised when dataset roles are missing, duplicated, or leak across roles."""

    code = "invalid_visual_dataset_roles"


class VisualManifestError(VisualEngineError, ValueError):
    """Raised when a visual artifact or reproducibility manifest is malformed."""

    code = "invalid_visual_manifest"


class VisualIntegrityError(VisualEngineError, ValueError):
    """Raised when content does not match recorded integrity metadata."""

    code = "visual_integrity_error"


class VisualProvisioningError(VisualEngineError, RuntimeError):
    """Raised when an explicitly selected backend is not locally provisioned."""

    code = "visual_backend_not_provisioned"

from __future__ import annotations

import builtins
import sys
from collections.abc import Sequence
from pathlib import Path
from unittest.mock import patch as mock_patch

import numpy as np
import pytest

from ade.preprocessing.patch_extractor import Patch
from ade.visual import (
    DINOv2VisualRepresentationProvider,
    LightweightVisualRepresentationProvider,
    RepresentationProviderConfig,
    VisualIntegrityError,
    VisualProvisioningError,
    create_visual_representation_provider,
)


def image_patch(patch_id: str, value: int = 0) -> Patch:
    return Patch(
        source_path=Path("image.png"),
        array=np.full((4, 4, 3), value, dtype=np.uint8),
        x=0,
        y=0,
        width=4,
        height=4,
        patch_id=patch_id,
        image_id="image",
    )


class FakeDINOv2Adapter:
    model_id = "fake/local/dinov2"
    provider_version = "fake-1"
    feature_dimension = 3
    deterministic = True

    def encode(self, patches: Sequence[Patch]) -> np.ndarray:
        return np.asarray(
            [[float(patch.array.mean()), 1.0, 2.0] for patch in patches],
            dtype=np.float32,
        )


def config(**overrides: object) -> RepresentationProviderConfig:
    values: dict[str, object] = {
        "provider": "dinov2",
        "model_name": "dinov2-base",
        "model_path": "models/dinov2",
        "device": "cpu",
        "batch_size": 4,
        "normalize": True,
        "allow_download": False,
    }
    values.update(overrides)
    return RepresentationProviderConfig(**values)  # type: ignore[arg-type]


def test_dinov2_config_is_offline_safe_by_default() -> None:
    selected = config()
    selected.validate()
    assert selected.allow_download is False
    assert selected.device == "cpu"
    assert RepresentationProviderConfig().provider == "lightweight"


def test_download_requires_explicit_model_name_and_opt_in() -> None:
    selected = config(model_path=None, allow_download=True)
    selected.validate()
    with pytest.raises(ValueError, match="requires model_path"):
        config(model_path=None, allow_download=False).validate()


def test_missing_optional_package_raises_structured_provisioning_error() -> None:
    real_import = __import__("importlib").import_module

    def missing(name: str, package: str | None = None):
        if name == "torch":
            raise ImportError("not installed")
        return real_import(name, package)

    with (
        mock_patch("ade.visual.representation.importlib.import_module", side_effect=missing),
        pytest.raises(VisualProvisioningError) as captured,
    ):
        create_visual_representation_provider(config())
    assert captured.value.context["provider"] == "dinov2"
    assert captured.value.context["missing_package"] == "torch"
    assert "lightweight" in captured.value.context["lightweight_default"]


def test_lightweight_factory_never_imports_deep_packages() -> None:
    before = {name for name in sys.modules if name in {"torch", "transformers", "timm"}}
    real_import = builtins.__import__

    def guarded(name: str, *args: object, **kwargs: object):
        if name.split(".", 1)[0] in {"torch", "transformers", "timm"}:
            raise AssertionError("deep package imported for lightweight provider")
        return real_import(name, *args, **kwargs)

    with mock_patch("builtins.__import__", side_effect=guarded):
        provider = create_visual_representation_provider(RepresentationProviderConfig())
    assert isinstance(provider, LightweightVisualRepresentationProvider)
    assert before == {name for name in sys.modules if name in {"torch", "transformers", "timm"}}


def test_fake_adapter_encodes_deterministically_with_provenance() -> None:
    provider = DINOv2VisualRepresentationProvider(config(), adapter=FakeDINOv2Adapter())
    patches = (image_patch("one", 0), image_patch("two", 2))
    first = provider.encode_batch(patches)
    second = provider.encode_batch(patches)
    np.testing.assert_array_equal(first.records[0].vector, second.records[0].vector)
    np.testing.assert_allclose(np.linalg.norm(first.records[1].vector), 1.0)
    provenance = provider.metadata.provenance_payload()
    assert provenance["provider_name"] == "dinov2"
    assert provenance["device"] == "cpu"
    assert provenance["normalization"] == "l2"
    assert provenance["deterministic"] is True
    assert provenance["provider_details"] == {
        "model_id": "fake/local/dinov2",
        "model_name": "dinov2-base",
        "model_path": "models/dinov2",
        "allow_download": False,
        "calibrated": False,
    }


def test_fake_adapter_output_validation_and_batch_bound() -> None:
    provider = DINOv2VisualRepresentationProvider(config(batch_size=1), adapter=FakeDINOv2Adapter())
    with pytest.raises(VisualIntegrityError, match="batch exceeds"):
        provider.encode_batch((image_patch("one"), image_patch("two")))
    with pytest.raises(VisualIntegrityError, match="unique"):
        DINOv2VisualRepresentationProvider(config(), adapter=FakeDINOv2Adapter()).encode_batch(
            (image_patch("same"), image_patch("same"))
        )

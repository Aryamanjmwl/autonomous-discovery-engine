from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from ade.preprocessing.patch_extractor import Patch
from ade.representation.embedding_engine import EmbeddingEngine
from ade.visual import (
    LightweightVisualRepresentationProvider,
    RepresentationBatch,
    RepresentationProviderConfig,
    RepresentationProviderMetadata,
    RepresentationRecord,
    VisualEngineConfig,
    VisualIntegrityError,
    VisualProvisioningError,
    create_visual_representation_provider,
)


def patch(value: int = 0, patch_id: str = "patch-1") -> Patch:
    return Patch(
        source_path=Path("image.png"),
        array=np.full((4, 5, 3), value, dtype=np.uint8),
        x=0,
        y=0,
        width=5,
        height=4,
        patch_id=patch_id,
        image_id="image-1",
    )


def test_default_provider_config_is_lightweight_and_backward_compatible() -> None:
    config = VisualEngineConfig()
    assert config.representation == RepresentationProviderConfig()
    assert config.backend_id == "statistical_visual_v2"
    assert config.to_dict()["representation"]["provider"] == "lightweight"


def test_lightweight_provider_matches_existing_embedding_vector_exactly() -> None:
    source = patch(127)
    legacy = EmbeddingEngine().embed_patch(source)
    provider = LightweightVisualRepresentationProvider()
    represented = provider.encode_batch((source,)).records[0]
    assert np.array_equal(represented.vector, legacy.vector)
    assert represented.record_id == source.patch_id
    assert represented.vector.dtype == np.float32


def test_lightweight_provider_is_deterministic() -> None:
    provider = LightweightVisualRepresentationProvider()
    source = patch(83)
    first = provider.encode_batch((source,))
    second = provider.encode_batch((source,))
    assert np.array_equal(first.records[0].vector, second.records[0].vector)
    assert first.provider == second.provider
    assert first.provider.deterministic is True


def test_metadata_and_provenance_are_stable_and_complete() -> None:
    first = LightweightVisualRepresentationProvider().metadata
    second = LightweightVisualRepresentationProvider().metadata
    assert first == second
    assert first.feature_dimension == len(EmbeddingEngine.feature_names)
    assert first.provenance_payload() == {
        "provider_name": "statistical_visual_v2",
        "provider_version": "1",
        "feature_dimension": len(EmbeddingEngine.feature_names),
        "dtype": "float32",
        "normalization": "provider_defined",
        "device": "cpu",
        "deterministic": True,
        "configuration_fingerprint": first.configuration_fingerprint,
    }


@pytest.mark.parametrize(
    "config",
    [
        RepresentationProviderConfig(provider="unknown"),
        RepresentationProviderConfig(batch_size=0),
        RepresentationProviderConfig(device="accelerator"),
        RepresentationProviderConfig(provider="custom"),
        RepresentationProviderConfig(options={"bad": float("nan")}),
    ],
)
def test_invalid_provider_config_fails_clearly(config: RepresentationProviderConfig) -> None:
    with pytest.raises(ValueError):
        config.validate()


@pytest.mark.parametrize("provider", ["dinov2", "clip"])
def test_deep_provider_schema_requires_no_dependency_until_selected(provider: str) -> None:
    config = RepresentationProviderConfig(provider=provider, device="auto")
    config.validate()
    with pytest.raises(VisualProvisioningError, match="not implemented or provisioned"):
        create_visual_representation_provider(config)


def test_record_and_batch_contract_validation() -> None:
    metadata = RepresentationProviderMetadata(
        "test", "1", 2, "float32", "none", "cpu", True, "a" * 64
    )
    record = RepresentationRecord("one", np.array([1, 2], dtype=np.float32))
    assert RepresentationBatch((record,), metadata).records == (record,)
    with pytest.raises(VisualIntegrityError):
        RepresentationRecord("bad", np.array([np.inf], dtype=np.float32))
    with pytest.raises(VisualIntegrityError):
        RepresentationBatch((record, record), metadata)


def test_batch_bound_is_enforced() -> None:
    provider = LightweightVisualRepresentationProvider(RepresentationProviderConfig(batch_size=1))
    with pytest.raises(VisualIntegrityError, match="batch exceeds"):
        provider.encode_batch((patch(0, "one"), patch(1, "two")))

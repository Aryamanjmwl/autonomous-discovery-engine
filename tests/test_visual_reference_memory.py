"""Integrity and determinism tests for immutable visual reference memory."""

from __future__ import annotations

import os
from dataclasses import replace
from pathlib import Path
from typing import Any

import numpy as np
import pytest

import ade.visual.reference_memory as storage
from ade.visual import (
    ReferenceVectorRecord,
    VisualDatasetRole,
    VisualDatasetRoleError,
    VisualEngineConfig,
    VisualIntegrityError,
    VisualManifestError,
    build_reference_memory,
    derive_reference_memory_id,
    load_reference_memory,
    select_reference_coreset,
    serialize_reference_memory_manifest,
    sha256_file,
    validate_reference_memory,
    validate_reference_records,
    write_manifest,
)

REFERENCE = "a" * 64
CONFIGURATION = "b" * 64


def _records(count: int = 4) -> tuple[ReferenceVectorRecord, ...]:
    return tuple(
        ReferenceVectorRecord(
            vector_id=f"vector-{index}",
            source_identity=f"images/{index}.png",
            vector=np.array([float(index), float(index + 1)], dtype=np.float32),
            x=index,
            y=index + 1,
            width=8,
            height=8,
            scale_id="scale-0",
            metadata={"index": index, "tags": ["reference"]},
        )
        for index in range(count)
    )


def _build(
    root: Path,
    records: tuple[ReferenceVectorRecord, ...] | None = None,
    **kwargs: Any,
):
    return build_reference_memory(
        records or _records(),
        storage_root=root,
        dataset_role=VisualDatasetRole.REFERENCE,
        reference_dataset_fingerprint=REFERENCE,
        configuration_fingerprint=CONFIGURATION,
        backend_id="statistical_visual_v2",
        backend_version="1",
        **kwargs,
    )


@pytest.mark.parametrize(
    "vector",
    [
        np.array([], dtype=np.float32),
        np.zeros((1, 2), dtype=np.float32),
        np.array([np.nan], dtype=np.float32),
        np.array([np.inf], dtype=np.float32),
    ],
)
def test_reference_vector_rejects_invalid_arrays(vector: np.ndarray) -> None:
    with pytest.raises(VisualIntegrityError):
        ReferenceVectorRecord("id", "source", vector)


def test_reference_vector_rejects_unsafe_metadata() -> None:
    with pytest.raises(VisualIntegrityError, match="JSON-safe|unsupported"):
        ReferenceVectorRecord(
            "id", "source", np.ones(2, dtype=np.float32), metadata={"x": {1}}
        )


def test_reference_records_reject_duplicate_ids_and_dimensions() -> None:
    duplicate = (
        ReferenceVectorRecord("same", "a", np.ones(2, dtype=np.float32)),
        ReferenceVectorRecord("same", "b", np.ones(2, dtype=np.float32)),
    )
    inconsistent = (
        ReferenceVectorRecord("a", "a", np.ones(2, dtype=np.float32)),
        ReferenceVectorRecord("b", "b", np.ones(3, dtype=np.float32)),
    )
    with pytest.raises(VisualIntegrityError, match="unique"):
        validate_reference_records(duplicate)
    with pytest.raises(VisualIntegrityError, match="dimension"):
        validate_reference_records(inconsistent)


def test_memory_id_is_deterministic() -> None:
    arguments = dict(
        reference_dataset_fingerprint=REFERENCE,
        configuration_fingerprint=CONFIGURATION,
        backend_id="backend",
        backend_version="1",
        distance_metric="euclidean",
        coreset_strategy="none",
        coreset_parameters={"selected_vector_count": 4},
        random_seed=42,
    )
    assert derive_reference_memory_id(_records(), **arguments) == derive_reference_memory_id(
        _records(), **arguments
    )


def test_build_load_round_trip_and_same_inputs_resolve_immutably(tmp_path: Path) -> None:
    first = _build(tmp_path)
    root = first.root
    manifest_bytes = (root / "manifest.json").read_bytes()
    first.close()
    second = _build(tmp_path)
    try:
        assert second.root == root
        assert second.vectors.dtype == np.float32
        assert second.vectors.flags.c_contiguous
        assert isinstance(second.vectors, np.memmap)
        assert [record.vector_id for record in second.records] == [
            record.vector_id for record in _records()
        ]
        assert (root / "manifest.json").read_bytes() == manifest_bytes
    finally:
        second.close()


def test_load_without_memory_mapping(tmp_path: Path) -> None:
    built = _build(tmp_path)
    root = built.root
    built.close()
    loaded = load_reference_memory(root, memory_map=False)
    assert not isinstance(loaded.vectors, np.memmap)


def test_atomic_build_cleans_temporary_directory_after_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def fail_rename(
        source: str | bytes | os.PathLike[str],
        target: str | bytes | os.PathLike[str],
    ) -> None:
        del source, target
        raise OSError("simulated publication failure")

    monkeypatch.setattr(storage.os, "rename", fail_rename)
    with pytest.raises(VisualIntegrityError, match="atomic"):
        _build(tmp_path)
    assert list(tmp_path.iterdir()) == []


def test_rejects_payload_manifest_corruption_and_unexpected_files(tmp_path: Path) -> None:
    built = _build(tmp_path)
    root = built.root
    built.close()
    (root / "unexpected.txt").write_text("no", encoding="utf-8")
    with pytest.raises(VisualIntegrityError, match="unexpected"):
        validate_reference_memory(root)
    (root / "unexpected.txt").unlink()
    with (root / "vectors.npy").open("ab") as stream:
        stream.write(b"corrupt")
    with pytest.raises(VisualIntegrityError, match="manifest"):
        validate_reference_memory(root)
    (root / "manifest.json").write_text("not-json", encoding="utf-8")
    with pytest.raises(VisualManifestError):
        validate_reference_memory(root)


def _rewrite_payload_manifest(
    root: Path,
    *,
    vectors: np.ndarray | None = None,
    metadata: bytes | None = None,
) -> None:
    manifest = storage.deserialize_reference_memory_manifest(
        (root / "manifest.json").read_bytes()
    )
    if vectors is not None:
        with (root / "vectors.npy").open("wb") as stream:
            np.save(stream, vectors, allow_pickle=False)
    if metadata is not None:
        (root / "records.jsonl").write_bytes(metadata)
    updated = replace(
        manifest,
        vector_artifact=replace(
            manifest.vector_artifact,
            sha256=sha256_file(root / "vectors.npy"),
            size_bytes=(root / "vectors.npy").stat().st_size,
        ),
        metadata_artifact=replace(
            manifest.metadata_artifact,
            sha256=sha256_file(root / "records.jsonl"),
            size_bytes=(root / "records.jsonl").stat().st_size,
        ),
    )
    write_manifest(
        root / "manifest.json",
        serialize_reference_memory_manifest(updated),
        allow_replace=True,
    )


def test_rejects_truncated_jsonl_and_vector_metadata_count_mismatch(tmp_path: Path) -> None:
    built = _build(tmp_path)
    root = built.root
    built.close()
    lines = (root / "records.jsonl").read_bytes().splitlines(keepends=True)
    _rewrite_payload_manifest(root, metadata=b"".join(lines[:-1]))
    with pytest.raises(VisualIntegrityError, match="count"):
        validate_reference_memory(root)
    _rewrite_payload_manifest(root, metadata=b"".join(lines)[:-1])
    with pytest.raises(VisualIntegrityError, match="truncated"):
        validate_reference_memory(root)


@pytest.mark.parametrize(
    "vectors",
    [
        np.ones((4, 2), dtype=np.float64),
        np.ones(8, dtype=np.float32),
        np.ones((3, 2), dtype=np.float32),
    ],
)
def test_rejects_dtype_and_shape_mismatch(tmp_path: Path, vectors: np.ndarray) -> None:
    built = _build(tmp_path)
    root = built.root
    built.close()
    _rewrite_payload_manifest(root, vectors=vectors)
    with pytest.raises(VisualIntegrityError):
        validate_reference_memory(root)


def test_manifest_rejects_windows_and_posix_path_escape(tmp_path: Path) -> None:
    built = _build(tmp_path)
    manifest = built.manifest
    built.close()
    for unsafe_path in ("../vectors.npy", r"..\vectors.npy", r"C:\vectors.npy"):
        unsafe = replace(
            manifest,
            vector_artifact=replace(
                manifest.vector_artifact, relative_path=unsafe_path
            ),
        )
        with pytest.raises((VisualManifestError, VisualIntegrityError)):
            serialize_reference_memory_manifest(unsafe)


def test_rejects_backend_dimension_metric_and_config_mismatch(tmp_path: Path) -> None:
    built = _build(tmp_path)
    root = built.root
    built.close()
    for kwargs in (
        {"expected_backend_id": "other"},
        {"expected_backend_version": "2"},
        {"expected_dimension": 3},
        {"expected_metric": "cosine"},
        {"expected_configuration_fingerprint": "c" * 64},
    ):
        with pytest.raises(VisualIntegrityError, match="incompatible"):
            load_reference_memory(root, **kwargs)


def test_enforces_reference_role_and_content_leakage(tmp_path: Path) -> None:
    for role in (VisualDatasetRole.QUERY, VisualDatasetRole.VALIDATION):
        with pytest.raises(VisualDatasetRoleError):
            build_reference_memory(
                _records(),
                storage_root=tmp_path,
                dataset_role=role,
                reference_dataset_fingerprint=REFERENCE,
                configuration_fingerprint=CONFIGURATION,
                backend_id="backend",
                backend_version="1",
            )
    with pytest.raises(VisualDatasetRoleError) as error:
        _build(tmp_path, query_dataset_fingerprint=REFERENCE)
    assert error.value.context["roles"] == ["reference", "query"]


def test_configuration_defaults_remain_backward_compatible() -> None:
    config = VisualEngineConfig.from_mapping({})
    assert config.execution_mode == "exploratory"
    assert config.reference_memory.enabled is False
    assert config.reference_memory.coreset_strategy == "none"
    assert config.reference_memory.search_batch_size == 128


def test_deterministic_farthest_first_is_bounded_stable_and_records_provenance() -> None:
    first = select_reference_coreset(
        _records(6), strategy="deterministic_farthest_first", maximum_vectors=3, seed=2
    )
    second = select_reference_coreset(
        _records(6), strategy="deterministic_farthest_first", maximum_vectors=3, seed=2
    )
    assert first.source_indices == second.source_indices
    assert len(first.records) == 3
    assert first.parameters["input_vector_count"] == 6


def test_coreset_bounds_and_stable_ties() -> None:
    with pytest.raises(VisualIntegrityError, match="maximum_vectors"):
        select_reference_coreset(_records(4), strategy="none", maximum_vectors=3)
    selected = select_reference_coreset(
        _records(3), strategy="deterministic_farthest_first", maximum_vectors=50
    )
    assert selected.source_indices == (0, 1, 2)
    tied = (
        ReferenceVectorRecord("z", "z", np.array([0.0], dtype=np.float32)),
        ReferenceVectorRecord("b", "b", np.array([1.0], dtype=np.float32)),
        ReferenceVectorRecord("a", "a", np.array([-1.0], dtype=np.float32)),
    )
    tie_selection = select_reference_coreset(
        tied, strategy="deterministic_farthest_first", maximum_vectors=2, seed=0
    )
    assert tie_selection.source_indices == (0, 2)

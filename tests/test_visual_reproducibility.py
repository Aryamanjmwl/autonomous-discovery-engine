"""Fingerprint and manifest reproducibility invariants."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from ade.visual import (
    VisualArtifactManifest,
    VisualContractVersionError,
    VisualDatasetRole,
    VisualEngineConfig,
    VisualIntegrityError,
    VisualManifestError,
    VisualReproducibilityManifest,
    deserialize_artifact_manifest,
    deserialize_reproducibility_manifest,
    fingerprint_visual_content,
    fingerprint_visual_dataset,
    normalize_relative_path,
    serialize_artifact_manifest,
    serialize_reproducibility_manifest,
    sha256_file,
    validate_artifact_integrity,
    write_manifest,
)


def _dataset(root: Path) -> list[Path]:
    (root / "nested").mkdir(parents=True)
    first = root / "a.bin"
    second = root / "nested" / "b.bin"
    first.write_bytes(b"alpha")
    second.write_bytes(b"beta")
    return [first, second]


def test_fingerprint_is_stable_and_path_order_independent(tmp_path: Path) -> None:
    files = _dataset(tmp_path)
    config = VisualEngineConfig()

    forward = fingerprint_visual_dataset(tmp_path, files, config)
    reverse = fingerprint_visual_dataset(tmp_path, reversed(files), config)

    assert forward == reverse
    assert [item.relative_path for item in forward.files] == ["a.bin", "nested/b.bin"]


def test_fingerprint_excludes_machine_specific_absolute_root(tmp_path: Path) -> None:
    left = tmp_path / "machine-a" / "data"
    right = tmp_path / "machine-b" / "different" / "data"
    left_files = _dataset(left)
    right_files = _dataset(right)

    left_result = fingerprint_visual_dataset(left, left_files, VisualEngineConfig())
    right_result = fingerprint_visual_dataset(right, right_files, VisualEngineConfig())

    assert left_result.fingerprint == right_result.fingerprint


def test_fingerprint_changes_with_content(tmp_path: Path) -> None:
    files = _dataset(tmp_path)
    initial = fingerprint_visual_dataset(tmp_path, files, VisualEngineConfig())

    files[1].write_bytes(b"changed")
    changed = fingerprint_visual_dataset(tmp_path, files, VisualEngineConfig())

    assert changed.fingerprint != initial.fingerprint


def test_fingerprint_changes_with_relevant_configuration(tmp_path: Path) -> None:
    files = _dataset(tmp_path)
    initial = fingerprint_visual_dataset(tmp_path, files, VisualEngineConfig())
    changed_config = VisualEngineConfig.from_mapping({"random_seed": 7})

    changed = fingerprint_visual_dataset(tmp_path, files, changed_config)

    assert changed.configuration_fingerprint != initial.configuration_fingerprint
    assert changed.fingerprint != initial.fingerprint


def test_content_identity_ignores_execution_configuration(tmp_path: Path) -> None:
    files = _dataset(tmp_path)
    initial = fingerprint_visual_content(tmp_path, files, VisualEngineConfig())
    changed_config = VisualEngineConfig.from_mapping({"random_seed": 7})

    changed = fingerprint_visual_content(tmp_path, files, changed_config)

    assert changed == initial


def test_content_identity_changes_with_file_content(tmp_path: Path) -> None:
    files = _dataset(tmp_path)
    initial = fingerprint_visual_content(tmp_path, files, VisualEngineConfig())

    files[0].write_bytes(b"changed")
    changed = fingerprint_visual_content(tmp_path, files, VisualEngineConfig())

    assert changed != initial


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("folder/image.png", "folder/image.png"),
        (r"folder\image.png", "folder/image.png"),
        (r"folder\.\nested\image.png", "folder/nested/image.png"),
        ("folder/./nested/image.png", "folder/nested/image.png"),
    ],
)
def test_windows_and_posix_relative_paths_normalize_identically(
    source: str,
    expected: str,
) -> None:
    assert normalize_relative_path(source) == expected


@pytest.mark.parametrize("source", ["/absolute/image.png", r"C:\data\image.png", "../x"])
def test_path_normalization_rejects_absolute_and_traversing_paths(source: str) -> None:
    with pytest.raises(VisualIntegrityError):
        normalize_relative_path(source)


def test_artifact_manifest_round_trip_and_integrity(tmp_path: Path) -> None:
    artifact = tmp_path / "reports" / "result.json"
    artifact.parent.mkdir()
    artifact.write_text('{"ok":true}', encoding="utf-8")
    manifest = VisualArtifactManifest(
        schema_version=1,
        artifact_id="result-json",
        artifact_type="report",
        relative_path="reports/result.json",
        sha256=sha256_file(artifact),
        size_bytes=artifact.stat().st_size,
        media_type="application/json",
    )

    restored = deserialize_artifact_manifest(serialize_artifact_manifest(manifest))

    assert restored == manifest
    assert validate_artifact_integrity(restored, tmp_path) == artifact.resolve()


def test_artifact_integrity_rejects_corrupted_content(tmp_path: Path) -> None:
    artifact = tmp_path / "result.bin"
    artifact.write_bytes(b"expected")
    manifest = VisualArtifactManifest(
        schema_version=1,
        artifact_id="result",
        artifact_type="binary",
        relative_path="result.bin",
        sha256=sha256_file(artifact),
        size_bytes=artifact.stat().st_size,
    )
    artifact.write_bytes(b"corrupt!")

    with pytest.raises(VisualIntegrityError, match="does not match"):
        validate_artifact_integrity(manifest, tmp_path)


def test_reproducibility_manifest_round_trip() -> None:
    digest = "a" * 64
    manifest = VisualReproducibilityManifest(
        schema_version=1,
        dataset_fingerprints={VisualDatasetRole.QUERY: digest},
        configuration_fingerprint="b" * 64,
        backend_id="statistical_visual_v2",
        backend_version="1",
        random_seed=42,
        deterministic=True,
        python_version="3.11.9",
        ade_version="0.1.0",
        device="cpu",
    )

    restored = deserialize_reproducibility_manifest(
        serialize_reproducibility_manifest(manifest)
    )

    assert restored == manifest


def _reproducibility_manifest(
    fingerprints: dict[VisualDatasetRole, str],
) -> VisualReproducibilityManifest:
    return VisualReproducibilityManifest(
        schema_version=1,
        dataset_fingerprints=fingerprints,
        configuration_fingerprint="d" * 64,
        backend_id="statistical_visual_v2",
        backend_version="1",
        random_seed=42,
        deterministic=True,
        python_version="3.11.9",
        ade_version="0.1.0",
        device="cpu",
    )


def test_reproducibility_manifest_rejects_query_reference_content_leakage() -> None:
    manifest = _reproducibility_manifest(
        {
            VisualDatasetRole.QUERY: "a" * 64,
            VisualDatasetRole.REFERENCE: "a" * 64,
        }
    )

    with pytest.raises(VisualManifestError, match="multiple roles") as error:
        serialize_reproducibility_manifest(manifest)

    assert error.value.context["roles"] == ["query", "reference"]


def test_reproducibility_manifest_rejects_reference_validation_content_leakage() -> None:
    manifest = _reproducibility_manifest(
        {
            VisualDatasetRole.QUERY: "a" * 64,
            VisualDatasetRole.REFERENCE: "b" * 64,
            VisualDatasetRole.VALIDATION: "b" * 64,
        }
    )

    with pytest.raises(VisualManifestError, match="multiple roles") as error:
        serialize_reproducibility_manifest(manifest)

    assert error.value.context["roles"] == ["reference", "validation"]


def test_reproducibility_manifest_accepts_three_distinct_role_fingerprints() -> None:
    manifest = _reproducibility_manifest(
        {
            VisualDatasetRole.QUERY: "a" * 64,
            VisualDatasetRole.REFERENCE: "b" * 64,
            VisualDatasetRole.VALIDATION: "c" * 64,
        }
    )

    restored = deserialize_reproducibility_manifest(
        serialize_reproducibility_manifest(manifest)
    )

    assert restored.dataset_fingerprints == manifest.dataset_fingerprints


def test_write_manifest_publishes_atomically_with_canonical_newline(tmp_path: Path) -> None:
    destination = tmp_path / "manifest.json"

    result = write_manifest(destination, '{"schema_version":1}\n\n')

    assert result == destination.resolve()
    assert destination.read_bytes() == b'{"schema_version":1}\n'
    assert list(tmp_path.glob(".manifest.json.*.tmp")) == []


def test_write_manifest_refuses_overwrite_by_default(tmp_path: Path) -> None:
    destination = tmp_path / "manifest.json"
    destination.write_text("original\n", encoding="utf-8")

    with pytest.raises(VisualIntegrityError, match="already exists") as error:
        write_manifest(destination, "replacement")

    assert destination.read_text(encoding="utf-8") == "original\n"
    assert error.value.context["allow_replace"] is False
    assert list(tmp_path.glob(".manifest.json.*.tmp")) == []


def test_write_manifest_replaces_only_when_explicitly_allowed(tmp_path: Path) -> None:
    destination = tmp_path / "manifest.json"
    destination.write_text("original\n", encoding="utf-8")

    write_manifest(destination, "replacement", allow_replace=True)

    assert destination.read_text(encoding="utf-8") == "replacement\n"


def test_write_manifest_cleans_temporary_file_after_publication_failure(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    destination = tmp_path / "manifest.json"
    destination.write_text("original\n", encoding="utf-8")

    def fail_replace(
        source: str | bytes | os.PathLike[str],
        target: str | bytes | os.PathLike[str],
    ) -> None:
        del source, target
        raise OSError("simulated publication failure")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(VisualIntegrityError, match="atomically") as error:
        write_manifest(destination, "replacement", allow_replace=True)

    assert destination.read_text(encoding="utf-8") == "original\n"
    assert error.value.context["operation"] == "replace"
    assert list(tmp_path.glob(".manifest.json.*.tmp")) == []


def test_manifest_rejects_unsupported_schema_version() -> None:
    payload = {
        "schema_version": 2,
        "artifact_id": "result",
        "artifact_type": "report",
        "relative_path": "result.json",
        "sha256": "a" * 64,
        "size_bytes": 1,
        "media_type": None,
    }

    with pytest.raises(VisualContractVersionError):
        deserialize_artifact_manifest(json.dumps(payload))


@pytest.mark.parametrize(
    "payload",
    [
        "not-json",
        "[]",
        '{"schema_version":1}',
        json.dumps(
            {
                "schema_version": 1,
                "artifact_id": "result",
                "artifact_type": "report",
                "relative_path": "../result.json",
                "sha256": "not-a-digest",
                "size_bytes": -1,
                "media_type": None,
            }
        ),
    ],
)
def test_malformed_artifact_manifests_are_rejected(payload: str) -> None:
    with pytest.raises((VisualManifestError, VisualIntegrityError)):
        deserialize_artifact_manifest(payload)


def test_reproducibility_manifest_rejects_validation_without_query() -> None:
    payload = {
        "schema_version": 1,
        "dataset_fingerprints": {"validation": "a" * 64},
        "configuration_fingerprint": "b" * 64,
        "backend_id": "backend",
        "backend_version": "1",
        "random_seed": 42,
        "deterministic": True,
        "python_version": "3.11",
        "ade_version": "0.1.0",
        "device": "cpu",
    }

    with pytest.raises(VisualManifestError, match="query"):
        deserialize_reproducibility_manifest(json.dumps(payload))

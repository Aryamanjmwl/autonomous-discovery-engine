"""Stage 7A tests for local Studio-triggered workflow jobs."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ade.studio.jobs import StudioJobStore
from ade.studio.service import (
    StudioPaths,
    list_reports,
    resolve_report_output,
    resolve_workspace_input,
    run_temporal_analysis,
    run_visual_analysis,
)
from ade.visual import (
    VISUAL_ENGINE_SCHEMA_VERSION,
    TemporalObservation,
    TemporalObservationSequence,
    serialize_temporal_manifest,
)


def _paths(root: Path) -> StudioPaths:
    reports = root / "reports"
    return StudioPaths(
        reports_dir=reports,
        run_index_path=reports / "runs/index.json",
        dashboard_dir=root / "dashboard",
        feedback_path=root / "feedback/feedback.jsonl",
        report_assets_dir=reports / "assets",
        artifacts_dir=root / "artifacts",
        project_root=root,
    )


def _images(root: Path) -> Path:
    image_module = pytest.importorskip("PIL.Image")
    folder = root / "images"
    folder.mkdir(parents=True)
    for index, value in enumerate((20, 30, 220)):
        pixels = np.full((80, 80, 3), value, dtype=np.uint8)
        pixels[8:24, 8:24] = (value + 25) % 255
        image_module.fromarray(pixels).save(folder / f"{index}.png")
    return folder


def _manifest(root: Path) -> Path:
    images = _images(root)
    sequence = TemporalObservationSequence(
        VISUAL_ENGINE_SCHEMA_VERSION,
        "studio-run-api",
        "1",
        str(root),
        "sequence-stage-7a",
        tuple(
            TemporalObservation(f"o{index}", f"images/{index}.png", sequence_index=index)
            for index in range(3)
        ),
    )
    manifest = root / "manifest.json"
    manifest.write_text(serialize_temporal_manifest(sequence), encoding="utf-8")
    assert images.is_dir()
    return manifest


def test_studio_job_store_records_success_and_failure_safely() -> None:
    store = StudioJobStore()
    succeeded = store.create("image_folder_analysis", {"input_path": "images"})
    store.start(succeeded)
    store.succeed(succeeded, report_paths=["reports/run.json"], artifact_paths=[])
    failed = store.create("temporal_analysis", {"manifest_path": "broken.json"})
    store.start(failed)
    store.fail(failed, ValueError("Malformed temporal manifest"))

    assert store.get(succeeded.job_id)["status"] == "succeeded"  # type: ignore[index]
    failed_record = store.get(failed.job_id)
    assert failed_record is not None
    assert failed_record["status"] == "failed"
    assert failed_record["output_report_paths"] == []
    assert failed_record["error_message"] == "Malformed temporal manifest"
    assert store.list()[0]["job_id"] == failed.job_id


@pytest.mark.parametrize(
    "unsafe",
    ["../outside", "images/../../outside", "https://example.test/images"],
)
def test_studio_workspace_input_rejects_traversal_and_external_urls(
    tmp_path: Path, unsafe: str
) -> None:
    with pytest.raises(ValueError, match="traversal|external URL"):
        resolve_workspace_input(unsafe, _paths(tmp_path), kind="input path")


def test_studio_workspace_input_rejects_missing_path_cleanly(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="does not exist"):
        resolve_workspace_input("missing", _paths(tmp_path), kind="input path")


def test_studio_report_output_stays_in_reports_root(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    assert resolve_report_output("review.json", paths, prefix="unused") == (
        paths.reports_dir / "review.md"
    ).resolve()
    with pytest.raises(ValueError, match="traversal"):
        resolve_report_output("../outside.md", paths, prefix="unused")
    with pytest.raises(ValueError, match="approved local root"):
        resolve_report_output(str(tmp_path / "outside.md"), paths, prefix="unused")


def test_image_folder_local_run_creates_discoverable_report(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    images = _images(tmp_path)

    result = run_visual_analysis(images, "image_run.md", paths=paths)

    assert result["validated"] is True
    assert result["human_review_required"] is True
    assert (paths.reports_dir / "image_run.json").is_file()
    assert [report["name"] for report in list_reports(paths)] == ["image_run.json"]


def test_temporal_local_run_creates_discoverable_artifact_backed_report(
    tmp_path: Path,
) -> None:
    paths = _paths(tmp_path)
    manifest = _manifest(tmp_path)

    result = run_temporal_analysis(
        manifest,
        "temporal_run.md",
        strategy="baseline_difference",
        patch_size=4,
        paths=paths,
    )

    artifact_path = Path(str(result["artifact_path"]))
    assert result["validated"] is True
    assert artifact_path.is_dir()
    assert [report["name"] for report in list_reports(paths)] == ["temporal_run.json"]


def test_malformed_temporal_manifest_fails_without_valid_report(tmp_path: Path) -> None:
    paths = _paths(tmp_path)
    manifest = tmp_path / "broken.json"
    manifest.write_text(json.dumps({"not": "a manifest"}), encoding="utf-8")

    with pytest.raises(ValueError):
        run_temporal_analysis(
            manifest,
            "broken_temporal.md",
            strategy="adjacent_difference",
            paths=paths,
        )
    assert list_reports(paths) == []


def test_studio_run_endpoints_expose_job_metadata_when_dependencies_available(
    tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from ade.studio.api import create_app

    paths = _paths(tmp_path)
    _images(tmp_path)
    client = TestClient(create_app(paths=paths, job_store=StudioJobStore()))

    created = client.post(
        "/api/studio/runs/image-folder",
        json={"input_path": "images", "output_name": "api_image.md", "run_label": "review"},
    )
    assert created.status_code == 200
    job = created.json()
    assert job["status"] == "succeeded"
    assert job["job_type"] == "image_folder_analysis"
    assert job["human_review_required"] is True
    assert client.get(f"/api/studio/runs/{job['job_id']}").json() == job
    assert client.get("/api/studio/runs").json()[0] == job
    reports = client.get("/api/studio/reports").json()
    assert reports[0]["name"] == "api_image.json"


def test_studio_failed_endpoint_job_is_retrievable_when_dependencies_available(
    tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from ade.studio.api import create_app

    client = TestClient(create_app(paths=_paths(tmp_path), job_store=StudioJobStore()))
    response = client.post(
        "/api/studio/runs/temporal",
        json={"manifest_path": "missing.json", "strategy": "adjacent_difference"},
    )
    job = response.json()
    assert response.status_code == 200
    assert job["status"] == "failed"
    assert "does not exist" in job["error_message"]
    assert job["output_report_paths"] == []
    assert client.get(f"/api/studio/runs/{job['job_id']}").json()["status"] == "failed"


def test_studio_run_request_schema_rejects_invalid_strategy_and_url(
    tmp_path: Path,
) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    from ade.studio.api import create_app

    client = TestClient(create_app(paths=_paths(tmp_path), job_store=StudioJobStore()))
    invalid_strategy = client.post(
        "/api/studio/runs/temporal",
        json={"manifest_path": "manifest.json", "strategy": "unsupported"},
    )
    external = client.post(
        "/api/studio/runs/image-folder",
        json={"input_path": "https://example.test/images"},
    )
    assert invalid_strategy.status_code == 422
    assert external.status_code == 422

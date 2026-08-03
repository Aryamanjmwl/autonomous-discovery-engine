"""Persistence and restart-recovery tests for ADE Studio jobs."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ade.studio.jobs import StudioJobStore


def test_studio_job_store_persists_completed_jobs(tmp_path: Path) -> None:
    storage_path = tmp_path / "studio_jobs.json"
    store = StudioJobStore(storage_path)
    job = store.create("image_folder_analysis", {"input_path": "images"})
    store.start(job)
    store.succeed(
        job,
        report_paths=["reports/run.json"],
        artifact_paths=["artifacts/run"],
        warnings=["Candidate findings require human review."],
    )

    restored = StudioJobStore(storage_path).get(job.job_id)

    assert restored is not None
    assert restored["status"] == "succeeded"
    assert restored["output_report_paths"] == ["reports/run.json"]
    assert restored["output_artifact_paths"] == ["artifacts/run"]
    assert restored["warnings"] == ["Candidate findings require human review."]
    assert restored["finished_at"] is not None


@pytest.mark.parametrize("status", ["queued", "running"])
def test_studio_job_store_marks_interrupted_jobs_failed_on_restart(
    tmp_path: Path,
    status: str,
) -> None:
    storage_path = tmp_path / "studio_jobs.json"
    store = StudioJobStore(storage_path)
    job = store.create("temporal_analysis", {"manifest_path": "manifest.json"})
    if status == "running":
        store.start(job)

    restored = StudioJobStore(storage_path).get(job.job_id)

    assert restored is not None
    assert restored["status"] == "failed"
    assert restored["finished_at"] is not None
    assert restored["error_message"] == (
        "ADE Studio restarted before this job completed."
    )
    assert restored["output_report_paths"] == []
    assert restored["output_artifact_paths"] == []


def test_studio_job_store_rejects_corrupt_persistence_file(tmp_path: Path) -> None:
    storage_path = tmp_path / "studio_jobs.json"
    storage_path.write_text("not-json", encoding="utf-8")

    with pytest.raises(ValueError, match="job store is unreadable"):
        StudioJobStore(storage_path)


def test_studio_job_store_rejects_unknown_schema(tmp_path: Path) -> None:
    storage_path = tmp_path / "studio_jobs.json"
    storage_path.write_text(
        json.dumps({"schema_version": "999", "jobs": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="unsupported schema"):
        StudioJobStore(storage_path)

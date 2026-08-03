"""Tests for bounded ADE Studio job execution and cancellation."""

from __future__ import annotations

from threading import Event

from ade.studio.execution import StudioJobExecutor, StudioJobOutput
from ade.studio.jobs import StudioJobStore


def test_executor_limits_work_and_cancels_queued_job() -> None:
    store = StudioJobStore()
    executor = StudioJobExecutor(store, max_workers=1)
    started = Event()
    release = Event()
    calls: list[str] = []

    def blocking_operation() -> StudioJobOutput:
        calls.append("first")
        started.set()
        assert release.wait(timeout=5)
        return StudioJobOutput(["reports/first.json"], [])

    first = store.create("image_folder_analysis", {"input_path": "first"})
    second = store.create("image_folder_analysis", {"input_path": "second"})
    executor.submit(first, blocking_operation)
    assert started.wait(timeout=5)
    executor.submit(second, lambda: StudioJobOutput(["reports/second.json"], []))

    assert executor.cancel(second.job_id) == "cancelled"
    release.set()
    executor.shutdown()

    assert store.get(first.job_id)["status"] == "succeeded"  # type: ignore[index]
    cancelled = store.get(second.job_id)
    assert cancelled is not None
    assert cancelled["status"] == "cancelled"
    assert cancelled["output_report_paths"] == []
    assert calls == ["first"]


def test_running_cancellation_discards_success_references() -> None:
    store = StudioJobStore()
    executor = StudioJobExecutor(store, max_workers=1)
    started = Event()
    release = Event()

    def operation() -> StudioJobOutput:
        started.set()
        assert release.wait(timeout=5)
        return StudioJobOutput(["reports/cancelled.json"], ["artifacts/cancelled"])

    job = store.create("temporal_analysis", {"manifest_path": "manifest.json"})
    executor.submit(job, operation)
    assert started.wait(timeout=5)

    assert executor.cancel(job.job_id) == "requested"
    running = store.get(job.job_id)
    assert running is not None
    assert running["status"] == "running"
    assert running["cancellation_requested"] is True

    release.set()
    executor.shutdown()

    cancelled = store.get(job.job_id)
    assert cancelled is not None
    assert cancelled["status"] == "cancelled"
    assert cancelled["output_report_paths"] == []
    assert cancelled["output_artifact_paths"] == []

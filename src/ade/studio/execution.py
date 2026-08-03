"""Bounded background execution for local ADE Studio jobs."""

from __future__ import annotations

from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass, field
from threading import RLock

from ade.studio.jobs import CancellationResult, StudioJob, StudioJobStore


@dataclass(frozen=True)
class StudioJobOutput:
    report_paths: list[str]
    artifact_paths: list[str]
    warnings: list[str] = field(default_factory=list)


class StudioJobExecutor:
    """Run Studio workflows on a bounded local thread pool."""

    def __init__(self, job_store: StudioJobStore, *, max_workers: int = 2) -> None:
        if max_workers < 1:
            raise ValueError("max_workers must be at least 1")
        self._jobs = job_store
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="ade-studio",
        )
        self._futures: dict[str, Future[None]] = {}
        self._lock = RLock()

    def submit(
        self,
        job: StudioJob,
        operation: Callable[[], StudioJobOutput],
    ) -> None:
        future = self._executor.submit(self._run, job, operation)
        with self._lock:
            self._futures[job.job_id] = future
        future.add_done_callback(
            lambda completed, job_id=job.job_id: self._forget(job_id, completed)
        )

    def cancel(self, job_id: str) -> CancellationResult | None:
        result = self._jobs.request_cancel(job_id)
        if result == "cancelled":
            with self._lock:
                future = self._futures.get(job_id)
            if future is not None:
                future.cancel()
        return result

    def shutdown(self) -> None:
        self._executor.shutdown(wait=True, cancel_futures=False)

    def _run(
        self,
        job: StudioJob,
        operation: Callable[[], StudioJobOutput],
    ) -> None:
        if not self._jobs.start(job):
            return
        try:
            output = operation()
        except Exception as error:
            self._jobs.fail(job, error)
        else:
            self._jobs.succeed(
                job,
                report_paths=output.report_paths,
                artifact_paths=output.artifact_paths,
                warnings=output.warnings,
            )

    def _forget(self, job_id: str, completed: Future[None]) -> None:
        with self._lock:
            if self._futures.get(job_id) is completed:
                self._futures.pop(job_id, None)

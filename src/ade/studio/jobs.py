"""In-memory job records for local ADE Studio runs."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from threading import RLock
from typing import Literal
from uuid import uuid4

StudioJobType = Literal["image_folder_analysis", "temporal_analysis"]
StudioJobStatus = Literal["queued", "running", "succeeded", "failed"]


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


@dataclass
class StudioJob:
    """A local, human-review-oriented Studio workflow job."""

    job_id: str
    job_type: StudioJobType
    status: StudioJobStatus
    created_at: str
    started_at: str | None = None
    finished_at: str | None = None
    input_summary: dict[str, object] = field(default_factory=dict)
    output_report_paths: list[str] = field(default_factory=list)
    output_artifact_paths: list[str] = field(default_factory=list)
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)
    human_review_required: bool = True

    def to_dict(self) -> dict[str, object]:
        """Return a detached JSON-safe job representation."""

        return asdict(self)


class StudioJobStore:
    """Thread-safe process-local Studio job storage."""

    def __init__(self) -> None:
        self._jobs: dict[str, StudioJob] = {}
        self._lock = RLock()

    def create(
        self, job_type: StudioJobType, input_summary: dict[str, object]
    ) -> StudioJob:
        with self._lock:
            job = StudioJob(
                job_id=f"studio-{uuid4().hex}",
                job_type=job_type,
                status="queued",
                created_at=_timestamp(),
                input_summary=dict(input_summary),
            )
            self._jobs[job.job_id] = job
            return job

    def start(self, job: StudioJob) -> None:
        with self._lock:
            job.status = "running"
            job.started_at = _timestamp()

    def succeed(
        self,
        job: StudioJob,
        *,
        report_paths: list[str],
        artifact_paths: list[str],
        warnings: list[str] | None = None,
    ) -> None:
        with self._lock:
            job.status = "succeeded"
            job.finished_at = _timestamp()
            job.output_report_paths = list(report_paths)
            job.output_artifact_paths = list(artifact_paths)
            job.warnings = list(warnings or [])

    def fail(self, job: StudioJob, error: Exception) -> None:
        with self._lock:
            job.status = "failed"
            job.finished_at = _timestamp()
            job.error_message = str(error) or error.__class__.__name__
            job.output_report_paths = []
            job.output_artifact_paths = []

    def list(self) -> list[dict[str, object]]:
        with self._lock:
            jobs = reversed(tuple(self._jobs.values()))
            return [job.to_dict() for job in jobs]

    def get(self, job_id: str) -> dict[str, object] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job is not None else None


DEFAULT_STUDIO_JOB_STORE = StudioJobStore()

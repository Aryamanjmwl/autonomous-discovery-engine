"""Durable local job records for ADE Studio runs."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field, fields
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from threading import RLock
from typing import Literal
from uuid import uuid4

StudioJobType = Literal["image_folder_analysis", "temporal_analysis"]
StudioJobStatus = Literal["queued", "running", "succeeded", "failed"]

_STORE_SCHEMA_VERSION = "1.0"
_JOB_TYPES = {"image_folder_analysis", "temporal_analysis"}
_JOB_STATUSES = {"queued", "running", "succeeded", "failed"}
_INTERRUPTED_MESSAGE = "ADE Studio restarted before this job completed."


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
    """Thread-safe Studio job storage with optional atomic persistence."""

    def __init__(self, storage_path: Path | str | None = None) -> None:
        self._jobs: dict[str, StudioJob] = {}
        self._lock = RLock()
        self._storage_path = Path(storage_path) if storage_path is not None else None
        self._load()

    @property
    def storage_path(self) -> Path | None:
        """Return the configured persistence path, if persistence is enabled."""

        return self._storage_path

    def _load(self) -> None:
        if self._storage_path is None or not self._storage_path.exists():
            return
        try:
            payload = json.loads(self._storage_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            raise ValueError(
                f"Studio job store is unreadable: {self._storage_path}"
            ) from error
        if (
            not isinstance(payload, dict)
            or payload.get("schema_version") != _STORE_SCHEMA_VERSION
        ):
            raise ValueError(
                f"Studio job store has an unsupported schema: {self._storage_path}"
            )
        records = payload.get("jobs")
        if not isinstance(records, list):
            raise TypeError(f"Studio job store has invalid jobs: {self._storage_path}")

        recovered = False
        for record in records:
            job = self._deserialize_job(record)
            if job.job_id in self._jobs:
                raise ValueError(
                    f"Studio job store contains duplicate job_id {job.job_id}: "
                    f"{self._storage_path}"
                )
            if job.status in {"queued", "running"}:
                job.status = "failed"
                job.finished_at = _timestamp()
                job.error_message = _INTERRUPTED_MESSAGE
                job.output_report_paths = []
                job.output_artifact_paths = []
                recovered = True
            self._jobs[job.job_id] = job
        if recovered:
            self._persist()

    def _deserialize_job(self, record: object) -> StudioJob:
        if not isinstance(record, dict):
            raise TypeError(
                f"Studio job store contains an invalid record: {self._storage_path}"
            )
        expected_fields = {item.name for item in fields(StudioJob)}
        if set(record) != expected_fields:
            raise ValueError(
                f"Studio job store record fields are invalid: {self._storage_path}"
            )
        if (
            record.get("job_type") not in _JOB_TYPES
            or record.get("status") not in _JOB_STATUSES
        ):
            raise ValueError(
                f"Studio job store record values are invalid: {self._storage_path}"
            )
        try:
            return StudioJob(**record)  # type: ignore[arg-type]
        except TypeError as error:
            raise ValueError(
                f"Studio job store record is invalid: {self._storage_path}"
            ) from error

    def _persist(self) -> None:
        if self._storage_path is None:
            return
        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "schema_version": _STORE_SCHEMA_VERSION,
            "jobs": [job.to_dict() for job in self._jobs.values()],
        }
        temporary_path: Path | None = None
        try:
            with NamedTemporaryFile(
                "w",
                encoding="utf-8",
                dir=self._storage_path.parent,
                prefix=f".{self._storage_path.name}.",
                suffix=".tmp",
                delete=False,
            ) as handle:
                temporary_path = Path(handle.name)
                json.dump(payload, handle, indent=2, sort_keys=True)
                handle.write("\n")
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary_path, self._storage_path)
        finally:
            if temporary_path is not None and temporary_path.exists():
                temporary_path.unlink()

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
            self._persist()
            return job

    def start(self, job: StudioJob) -> None:
        with self._lock:
            job.status = "running"
            job.started_at = _timestamp()
            self._persist()

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
            self._persist()

    def fail(self, job: StudioJob, error: Exception) -> None:
        with self._lock:
            job.status = "failed"
            job.finished_at = _timestamp()
            job.error_message = str(error) or error.__class__.__name__
            job.output_report_paths = []
            job.output_artifact_paths = []
            self._persist()

    def list(self) -> list[dict[str, object]]:
        with self._lock:
            jobs = reversed(tuple(self._jobs.values()))
            return [job.to_dict() for job in jobs]

    def get(self, job_id: str) -> dict[str, object] | None:
        with self._lock:
            job = self._jobs.get(job_id)
            return job.to_dict() if job is not None else None


DEFAULT_STUDIO_JOB_STORE = StudioJobStore(Path("data/reports/studio_jobs.json"))

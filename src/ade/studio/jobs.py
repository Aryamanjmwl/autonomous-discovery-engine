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

from ade import __version__

StudioJobType = Literal["image_folder_analysis", "temporal_analysis"]
StudioJobStatus = Literal["queued", "running", "succeeded", "failed", "cancelled"]
CancellationResult = Literal["cancelled", "requested", "terminal"]

_STORE_SCHEMA_VERSION = "1.3"
_SUPPORTED_STORE_SCHEMA_VERSIONS = {"1.0", "1.1", "1.2", _STORE_SCHEMA_VERSION}
_JOB_MANIFEST_VERSION = "1.1"
_SUPPORTED_JOB_MANIFEST_VERSIONS = {"1.0", _JOB_MANIFEST_VERSION}
_JOB_TYPES = {"image_folder_analysis", "temporal_analysis"}
_JOB_STATUSES = {"queued", "running", "succeeded", "failed", "cancelled"}
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
    manifest_version: str = _JOB_MANIFEST_VERSION
    ade_version: str = __version__
    request_parameters: dict[str, object] = field(default_factory=dict)
    input_fingerprint: dict[str, object] | None = None
    effective_configuration: dict[str, object] | None = None
    started_at: str | None = None
    finished_at: str | None = None
    input_summary: dict[str, object] = field(default_factory=dict)
    output_report_paths: list[str] = field(default_factory=list)
    output_artifact_paths: list[str] = field(default_factory=list)
    error_message: str | None = None
    warnings: list[str] = field(default_factory=list)
    human_review_required: bool = True
    cancellation_requested: bool = False

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
        if not isinstance(payload, dict):
            raise ValueError(
                f"Studio job store has an unsupported schema: {self._storage_path}"
            )
        schema_version = payload.get("schema_version")
        if schema_version not in _SUPPORTED_STORE_SCHEMA_VERSIONS:
            raise ValueError(
                f"Studio job store has an unsupported schema: {self._storage_path}"
            )
        records = payload.get("jobs")
        if not isinstance(records, list):
            raise TypeError(f"Studio job store has invalid jobs: {self._storage_path}")

        recovered = schema_version != _STORE_SCHEMA_VERSION
        for record in records:
            job = self._deserialize_job(record, schema_version=str(schema_version))
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

    def _deserialize_job(self, record: object, *, schema_version: str) -> StudioJob:
        if not isinstance(record, dict):
            raise TypeError(
                f"Studio job store contains an invalid record: {self._storage_path}"
            )
        normalized = dict(record)
        if schema_version in {"1.0", "1.1"}:
            input_summary = normalized.get("input_summary")
            normalized["manifest_version"] = "1.0"
            normalized["ade_version"] = "unknown"
            normalized["request_parameters"] = (
                dict(input_summary) if isinstance(input_summary, dict) else {}
            )
        if schema_version == "1.0":
            normalized["cancellation_requested"] = False
        if schema_version in {"1.0", "1.1", "1.2"}:
            normalized["input_fingerprint"] = None
            normalized["effective_configuration"] = None
        expected_fields = {item.name for item in fields(StudioJob)}
        if set(normalized) != expected_fields:
            raise ValueError(
                f"Studio job store record fields are invalid: {self._storage_path}"
            )
        if (
            normalized.get("job_type") not in _JOB_TYPES
            or normalized.get("status") not in _JOB_STATUSES
            or normalized.get("manifest_version") not in _SUPPORTED_JOB_MANIFEST_VERSIONS
            or not isinstance(normalized.get("ade_version"), str)
            or not normalized.get("ade_version")
            or not isinstance(normalized.get("request_parameters"), dict)
            or (
                normalized.get("input_fingerprint") is not None
                and not isinstance(normalized.get("input_fingerprint"), dict)
            )
            or (
                normalized.get("effective_configuration") is not None
                and not isinstance(normalized.get("effective_configuration"), dict)
            )
            or not isinstance(normalized.get("cancellation_requested"), bool)
        ):
            raise ValueError(
                f"Studio job store record values are invalid: {self._storage_path}"
            )
        try:
            return StudioJob(**normalized)  # type: ignore[arg-type]
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
        self,
        job_type: StudioJobType,
        input_summary: dict[str, object],
        *,
        request_parameters: dict[str, object] | None = None,
    ) -> StudioJob:
        with self._lock:
            job = StudioJob(
                job_id=f"studio-{uuid4().hex}",
                job_type=job_type,
                status="queued",
                created_at=_timestamp(),
                input_summary=dict(input_summary),
                request_parameters=dict(
                    input_summary if request_parameters is None else request_parameters
                ),
            )
            self._jobs[job.job_id] = job
            self._persist()
            return job

    def record_provenance(
        self,
        job: StudioJob,
        *,
        input_fingerprint: dict[str, object],
        effective_configuration: dict[str, object],
    ) -> None:
        with self._lock:
            if job.status != "running":
                raise ValueError("Run provenance can only be recorded for a running job")
            job.input_fingerprint = dict(input_fingerprint)
            job.effective_configuration = dict(effective_configuration)
            self._persist()

    def start(self, job: StudioJob) -> bool:
        with self._lock:
            if job.status != "queued" or job.cancellation_requested:
                return False
            job.status = "running"
            job.started_at = _timestamp()
            self._persist()
            return True

    def request_cancel(self, job_id: str) -> CancellationResult | None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return None
            if job.status == "queued":
                job.cancellation_requested = True
                self._cancel(job)
                self._persist()
                return "cancelled"
            if job.status == "running":
                job.cancellation_requested = True
                self._persist()
                return "requested"
            return "terminal"

    def succeed(
        self,
        job: StudioJob,
        *,
        report_paths: list[str],
        artifact_paths: list[str],
        warnings: list[str] | None = None,
    ) -> None:
        with self._lock:
            if job.cancellation_requested:
                self._cancel(job)
            else:
                job.status = "succeeded"
                job.finished_at = _timestamp()
                job.output_report_paths = list(report_paths)
                job.output_artifact_paths = list(artifact_paths)
                job.warnings = list(warnings or [])
            self._persist()

    def fail(self, job: StudioJob, error: Exception) -> None:
        with self._lock:
            if job.cancellation_requested:
                self._cancel(job)
            else:
                job.status = "failed"
                job.finished_at = _timestamp()
                job.error_message = str(error) or error.__class__.__name__
                job.output_report_paths = []
                job.output_artifact_paths = []
            self._persist()

    @staticmethod
    def _cancel(job: StudioJob) -> None:
        job.status = "cancelled"
        job.finished_at = _timestamp()
        job.error_message = None
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


DEFAULT_STUDIO_JOB_STORE = StudioJobStore(Path("data/reports/studio_jobs.json"))

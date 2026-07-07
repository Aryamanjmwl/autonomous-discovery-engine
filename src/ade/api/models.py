"""Pydantic models for the ADE local API."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Health response for the local API service."""

    status: str
    ade_version: str


class VersionResponse(BaseModel):
    """Version response for the local API service."""

    package: str = "ade-discovery-engine"
    ade_version: str
    service: str = "ade-local-api"


class RunRequest(BaseModel):
    """Request body for a local ADE discovery run."""

    dataset_path: str = Field(..., min_length=1)
    output_dir: str = Field(..., min_length=1)
    config_path: str | None = None
    run_name: str | None = None


class RunResponse(BaseModel):
    """Response returned after a local discovery run completes."""

    run_id: str
    status: str
    markdown_report_path: str
    json_report_path: str
    finding_count: int
    concept_count: int


class RunSummary(BaseModel):
    """Compact run summary returned by the run index."""

    run_id: str
    generated_at: str | None = None
    input_path: str | None = None
    markdown_report_path: str | None = None
    json_report_path: str | None = None
    number_of_candidate_anomalies: int | None = None
    number_of_candidate_unknown_concepts: int | None = None
    human_review_required: bool | None = None


class RunListResponse(BaseModel):
    """Run listing response."""

    runs: list[RunSummary]


class RunDetailResponse(BaseModel):
    """Detailed metadata response for one ADE run."""

    run_id: str
    metadata: dict[str, Any]


class ReportResponse(BaseModel):
    """Report artifact paths for a known run."""

    run_id: str
    markdown_report_path: str | None = None
    json_report_path: str | None = None
    run_metadata_path: str | None = None


class ErrorResponse(BaseModel):
    """Error response shape used by API documentation."""

    detail: str

"""FastAPI application for the ADE local service."""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, HTTPException

from ade import __version__
from ade.api.models import (
    HealthResponse,
    ReportResponse,
    RunDetailResponse,
    RunListResponse,
    RunRequest,
    RunResponse,
    RunSummary,
    VersionResponse,
)
from ade.api.service import (
    ApiRequestError,
    RunNotFoundError,
    get_report_paths,
    get_run_metadata,
    list_runs,
    run_discovery,
)

app = FastAPI(
    title="ADE Local API",
    version=__version__,
    description="Local API wrapper for ADE discovery runs.",
)


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    """Return service health."""

    return HealthResponse(status="ok", ade_version=__version__)


@app.get("/version", response_model=VersionResponse)
def version() -> VersionResponse:
    """Return service and package version information."""

    return VersionResponse(ade_version=__version__)


@app.post("/runs", response_model=RunResponse)
def create_run(request: RunRequest) -> RunResponse:
    """Execute a local ADE discovery run synchronously."""

    try:
        result = run_discovery(
            dataset_path=Path(request.dataset_path),
            output_dir=Path(request.output_dir),
            config_path=Path(request.config_path) if request.config_path else None,
            run_name=request.run_name,
        )
    except ApiRequestError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except (FileNotFoundError, NotADirectoryError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:  # pragma: no cover - defensive boundary for API callers
        raise HTTPException(status_code=500, detail="ADE run failed.") from error

    return RunResponse(
        run_id=result.run_id,
        status="completed",
        markdown_report_path=result.markdown_report_path.as_posix(),
        json_report_path=result.json_report_path.as_posix(),
        finding_count=result.finding_count,
        concept_count=result.concept_count,
    )


@app.get("/runs", response_model=RunListResponse)
def get_runs() -> RunListResponse:
    """List known ADE runs from the default local run index."""

    return RunListResponse(runs=[RunSummary(**run) for run in list_runs()])


@app.get("/runs/{run_id}", response_model=RunDetailResponse)
def get_run(run_id: str) -> RunDetailResponse:
    """Return metadata for a known ADE run."""

    try:
        metadata = get_run_metadata(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return RunDetailResponse(run_id=run_id, metadata=metadata)


@app.get("/runs/{run_id}/report", response_model=ReportResponse)
def get_run_report(run_id: str) -> ReportResponse:
    """Return report artifact paths for a known ADE run."""

    try:
        paths = get_report_paths(run_id)
    except RunNotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    return ReportResponse(run_id=run_id, **paths)

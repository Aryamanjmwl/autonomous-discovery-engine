"""FastAPI app for the local ADE Studio backend."""

from __future__ import annotations

import argparse
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from ade.studio.execution import StudioJobExecutor, StudioJobOutput
from ade.studio.jobs import DEFAULT_STUDIO_JOB_STORE, StudioJobStore
from ade.studio.provenance import (
    capture_image_folder_provenance,
    capture_temporal_provenance,
)
from ade.studio.service import (
    StudioPaths,
    build_summary,
    health_status,
    list_reports,
    load_report,
    record_review_feedback,
    resolve_report_asset,
    resolve_report_html,
    run_temporal_analysis,
    run_visual_analysis,
)


class StudioAnalysisRequest(BaseModel):
    """JSON body for a local ADE Studio analysis request."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    input_path: str = Field(..., min_length=1, max_length=4096)
    workflow: Literal["visual"] = "visual"
    output_name: str | None = Field(default=None, max_length=255)

    @field_validator("input_path", "output_name")
    @classmethod
    def reject_null_bytes(cls, value: str | None) -> str | None:
        if value is not None and "\x00" in value:
            raise ValueError("must not contain null bytes")
        return value


class _LocalRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    output_name: str | None = Field(default=None, max_length=4096)
    run_label: str | None = Field(default=None, max_length=255)

    @field_validator("*")
    @classmethod
    def reject_unsafe_text(cls, value: object) -> object:
        if isinstance(value, str) and "\x00" in value:
            raise ValueError("must not contain null bytes")
        if isinstance(value, str) and "://" in value:
            raise ValueError("must be a local filesystem path, not an external URL")
        if isinstance(value, str) and ".." in Path(value).parts:
            raise ValueError("must not contain path traversal")
        return value


class ImageFolderRunRequest(_LocalRunRequest):
    """Validated body for a local image-folder run."""

    input_path: str = Field(..., min_length=1, max_length=4096)
    config_path: str | None = Field(default=None, max_length=4096)


class TemporalRunRequest(_LocalRunRequest):
    """Validated body for a local temporal run."""

    manifest_path: str = Field(..., min_length=1, max_length=4096)
    strategy: Literal["adjacent_difference", "baseline_difference"] = "adjacent_difference"
    patch_size: int | None = Field(default=None, ge=1, le=4096)
    top_k: int = Field(default=10, ge=1, le=1000)
    patch_top_k: int = Field(default=5, ge=1, le=1000)


class StudioReviewFeedbackRequest(BaseModel):
    """Validated body for one local Studio reviewer action."""

    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    report_name: str = Field(..., min_length=1, max_length=255)
    finding_id: str = Field(..., min_length=1, max_length=255)
    finding_type: Literal["visual_candidate", "temporal_candidate"]
    reviewer_action: Literal["useful", "not_useful", "needs_review"]
    note: str = Field(default="", max_length=2000)

    @field_validator("report_name", "finding_id", "note")
    @classmethod
    def reject_feedback_null_bytes(cls, value: str) -> str:
        if "\x00" in value:
            raise ValueError("must not contain null bytes")
        return value

    @field_validator("report_name")
    @classmethod
    def reject_unsafe_report_name(cls, value: str) -> str:
        if "://" in value:
            raise ValueError("must not contain an external URL")
        if ".." in Path(value).parts:
            raise ValueError("must not contain path traversal")
        return value


def create_app(
    *,
    paths: StudioPaths | None = None,
    job_store: StudioJobStore | None = None,
    job_executor: StudioJobExecutor | None = None,
) -> Any:
    """Create the ADE Studio FastAPI app."""

    try:
        from fastapi import Body, FastAPI, HTTPException
        from fastapi.middleware.cors import CORSMiddleware
        from fastapi.responses import FileResponse
    except ImportError as error:  # pragma: no cover - optional dependency path.
        raise RuntimeError(
            "ADE Studio API requires the optional studio dependencies. "
            "Install with: pip install -e .[studio]"
        ) from error

    custom_paths = paths is not None
    studio_paths = paths or StudioPaths()
    jobs = job_store or (
        StudioJobStore(studio_paths.reports_dir / "studio_jobs.json")
        if custom_paths
        else DEFAULT_STUDIO_JOB_STORE
    )
    worker = job_executor or StudioJobExecutor(jobs, max_workers=2)

    @asynccontextmanager
    async def lifespan(_: Any) -> AsyncIterator[None]:
        try:
            yield
        finally:
            worker.shutdown()

    app = FastAPI(
        title="ADE Studio Local API",
        version="0.1.0",
        description=(
            "Local-only Technical Preview API for connecting ADE Studio to "
            "ADE visual/image-folder analysis."
        ),
        lifespan=lifespan,
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:3000", "http://localhost:3000"],
        allow_methods=["GET", "POST"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, object]:
        return health_status()

    @app.get("/api/studio/summary")
    def summary() -> dict[str, object]:
        return build_summary(studio_paths) if custom_paths else build_summary()

    @app.get("/api/studio/runs")
    def runs() -> list[dict[str, object]]:
        return jobs.list()

    @app.get("/api/studio/runs/{job_id}")
    def run(job_id: str) -> dict[str, object]:
        job = jobs.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail=f"Studio job was not found: {job_id}")
        return job

    @app.post("/api/studio/runs/{job_id}/cancel")
    def cancel_run(job_id: str) -> dict[str, object]:
        result = worker.cancel(job_id)
        if result is None:
            raise HTTPException(status_code=404, detail=f"Studio job was not found: {job_id}")
        job = jobs.get(job_id)
        if job is None:  # pragma: no cover
            raise HTTPException(status_code=404, detail=f"Studio job was not found: {job_id}")
        return job

    @app.get("/api/studio/reports")
    def reports() -> list[dict[str, object]]:
        return list_reports(studio_paths) if custom_paths else list_reports()

    @app.get("/api/studio/reports/{report_name}/html")
    def report_html(report_name: str) -> Any:
        try:
            html_path = (
                resolve_report_html(report_name, studio_paths)
                if custom_paths
                else resolve_report_html(report_name)
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        return FileResponse(html_path)

    @app.get("/api/studio/reports/{report_name}")
    def report(report_name: str) -> dict[str, object]:
        try:
            return (
                load_report(report_name, studio_paths)
                if custom_paths
                else load_report(report_name)
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/api/studio/feedback")
    def feedback(payload: StudioReviewFeedbackRequest = Body(...)) -> dict[str, object]:
        try:
            return record_review_feedback(
                report_name=payload.report_name,
                finding_id=payload.finding_id,
                finding_type=payload.finding_type,
                reviewer_action=payload.reviewer_action,
                note=payload.note,
                paths=studio_paths,
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.get("/api/studio/report-assets/{asset_name:path}")
    def report_asset(asset_name: str) -> Any:
        try:
            asset_path = (
                resolve_report_asset(asset_name, studio_paths)
                if custom_paths
                else resolve_report_asset(asset_name)
            )
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return FileResponse(asset_path)

    @app.post("/api/studio/analysis")
    def analysis(payload: StudioAnalysisRequest = Body(...)) -> dict[str, object]:
        try:
            return run_visual_analysis(
                input_path=Path(payload.input_path),
                output_name=payload.output_name,
                paths=studio_paths,
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.post("/api/studio/runs/image-folder", status_code=202)
    def image_folder_run(payload: ImageFolderRunRequest = Body(...)) -> dict[str, object]:
        job = jobs.create(
            "image_folder_analysis",
            {
                "input_path": payload.input_path,
                "config_path": payload.config_path,
                "run_label": payload.run_label,
            },
            request_parameters=payload.model_dump(mode="json"),
        )

        def execute() -> StudioJobOutput:
            provenance = capture_image_folder_provenance(
                payload.input_path,
                payload.config_path,
                paths=studio_paths,
            )
            jobs.record_provenance(
                job,
                input_fingerprint=provenance.input_fingerprint,
                effective_configuration=provenance.effective_configuration,
            )
            result = run_visual_analysis(
                input_path=Path(payload.input_path),
                output_name=payload.output_name,
                config_path=Path(payload.config_path) if payload.config_path else None,
                paths=studio_paths,
            )
            report_paths = [
                value
                for key in (
                    "markdown_report_path",
                    "json_report_path",
                    "html_report_path",
                )
                if isinstance((value := result.get(key)), str)
            ]
            return StudioJobOutput(report_paths=report_paths, artifact_paths=[])

        worker.submit(job, execute)
        return job.to_dict()

    @app.post("/api/studio/runs/temporal", status_code=202)
    def temporal_run(payload: TemporalRunRequest = Body(...)) -> dict[str, object]:
        job = jobs.create(
            "temporal_analysis",
            {
                "manifest_path": payload.manifest_path,
                "strategy": payload.strategy,
                "run_label": payload.run_label,
            },
            request_parameters=payload.model_dump(mode="json"),
        )

        def execute() -> StudioJobOutput:
            provenance = capture_temporal_provenance(
                payload.manifest_path,
                strategy=payload.strategy,
                patch_size=payload.patch_size,
                top_k=payload.top_k,
                patch_top_k=payload.patch_top_k,
                paths=studio_paths,
            )
            jobs.record_provenance(
                job,
                input_fingerprint=provenance.input_fingerprint,
                effective_configuration=provenance.effective_configuration,
            )
            result = run_temporal_analysis(
                manifest_path=Path(payload.manifest_path),
                output_name=payload.output_name,
                strategy=payload.strategy,
                patch_size=payload.patch_size,
                top_k=payload.top_k,
                patch_top_k=payload.patch_top_k,
                paths=studio_paths,
            )
            report_paths = [
                value
                for key in ("markdown_report_path", "json_report_path")
                if isinstance((value := result.get(key)), str)
            ]
            artifact = result.get("artifact_path")
            return StudioJobOutput(
                report_paths=report_paths,
                artifact_paths=[artifact] if isinstance(artifact, str) else [],
            )

        worker.submit(job, execute)
        return job.to_dict()

    return app


def _load_app() -> Any:
    """Load the ASGI app and keep import errors clear."""

    return create_app()


_APP_IMPORT_ERROR: RuntimeError | None

try:
    app = _load_app()
except RuntimeError as error:  # pragma: no cover - depends on optional extras.
    app = None
    _APP_IMPORT_ERROR = error
else:
    _APP_IMPORT_ERROR = None


def main(argv: list[str] | None = None) -> int:
    """Run the local ADE Studio API with uvicorn."""

    parser = argparse.ArgumentParser(description="Run the ADE Studio local API.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", default=8765, type=int)
    args = parser.parse_args(argv)

    try:
        import uvicorn
    except ImportError as error:  # pragma: no cover - optional dependency path.
        raise RuntimeError(
            "ADE Studio API requires uvicorn. Install with: pip install -e .[studio]"
        ) from error
    if _APP_IMPORT_ERROR is not None:
        raise _APP_IMPORT_ERROR

    uvicorn.run("ade.studio.api:app", host=args.host, port=args.port)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())




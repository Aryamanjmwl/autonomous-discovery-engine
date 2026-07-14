"""FastAPI app for the local ADE Studio backend."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

try:
    from pydantic import BaseModel, Field
except ImportError:  # pragma: no cover - optional dependency path.
    BaseModel = None
    Field = None

from ade.studio.service import (
    StudioPaths,
    build_summary,
    health_status,
    list_reports,
    list_runs,
    load_report,
    resolve_report_asset,
    run_visual_analysis,
)


if BaseModel is not None and Field is not None:

    class StudioAnalysisRequest(BaseModel):
        """JSON body for a local ADE Studio analysis request."""

        input_path: str = Field(..., min_length=1)
        workflow: str = "visual"
        output_name: str | None = None

else:
    StudioAnalysisRequest = None


def create_app() -> Any:
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

    if StudioAnalysisRequest is None:
        raise RuntimeError(
            "ADE Studio API requires pydantic. Install with: pip install -e .[studio]"
        )

    app = FastAPI(
        title="ADE Studio Local API",
        version="0.1.0",
        description=(
            "Local-only Technical Preview API for connecting ADE Studio to "
            "ADE visual/image-folder analysis."
        ),
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
        return build_summary()

    @app.get("/api/studio/runs")
    def runs() -> list[dict[str, object]]:
        return list_runs()

    @app.get("/api/studio/reports")
    def reports() -> list[dict[str, object]]:
        return list_reports()

    @app.get("/api/studio/reports/{report_name}")
    def report(report_name: str) -> dict[str, object]:
        try:
            return load_report(report_name)
        except FileNotFoundError as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    @app.get("/api/studio/report-assets/{asset_name:path}")
    def report_asset(asset_name: str) -> Any:
        try:
            asset_path = resolve_report_asset(asset_name)
        except (FileNotFoundError, ValueError) as error:
            raise HTTPException(status_code=404, detail=str(error)) from error
        return FileResponse(asset_path)

    @app.post("/api/studio/analysis")
    def analysis(payload: StudioAnalysisRequest = Body(...)) -> dict[str, object]:
        if payload.workflow != "visual":
            raise HTTPException(
                status_code=400,
                detail="Only the visual/image-folder workflow is supported in this milestone.",
            )
        try:
            return run_visual_analysis(
                input_path=Path(payload.input_path),
                output_name=payload.output_name,
                paths=StudioPaths(),
            )
        except FileNotFoundError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error
        except ValueError as error:
            raise HTTPException(status_code=400, detail=str(error)) from error

    return app


def _load_app() -> Any:
    """Load the ASGI app and keep import errors clear."""

    return create_app()


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




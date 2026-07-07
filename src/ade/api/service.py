"""Service helpers for the ADE local API."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ade.cli import run_pipeline
from ade.reporting.run_index import load_run_index

DEFAULT_REPORTS_DIR = Path("data/reports")


class ApiRequestError(ValueError):
    """Raised when an API request is invalid."""


class RunNotFoundError(LookupError):
    """Raised when a requested run cannot be found."""


@dataclass(frozen=True)
class RunResult:
    """Result of a local ADE run executed through the API service."""

    run_id: str
    markdown_report_path: Path
    json_report_path: Path
    finding_count: int
    concept_count: int


def run_discovery(
    dataset_path: Path,
    output_dir: Path,
    config_path: Path | None = None,
    run_name: str | None = None,
) -> RunResult:
    """Run ADE synchronously and return compact report metadata."""

    _validate_dataset_path(dataset_path)
    _validate_config_path(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / _report_filename(run_name)

    report_path = run_pipeline(
        input_dir=dataset_path,
        output_path=output_path,
        config_path=config_path,
    )
    json_path = report_path.with_suffix(".json")
    report_data = _read_json(json_path)
    return RunResult(
        run_id=str(report_data.get("run_id", "")),
        markdown_report_path=report_path,
        json_report_path=json_path,
        finding_count=int(report_data.get("number_of_candidate_anomalies", 0)),
        concept_count=int(report_data.get("number_of_candidate_unknown_concepts", 0)),
    )


def list_runs(reports_dir: Path = DEFAULT_REPORTS_DIR) -> list[dict[str, Any]]:
    """Return known runs from an ADE run index."""

    index = load_run_index(reports_dir / "runs" / "index.json")
    if index is None:
        return []
    runs = index.get("runs", [])
    return [run for run in runs if isinstance(run, dict)]


def get_run_metadata(
    run_id: str,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
) -> dict[str, Any]:
    """Return run metadata for one known run."""

    run = _find_run(run_id=run_id, reports_dir=reports_dir)
    metadata_path = run.get("run_metadata_path")
    if not metadata_path:
        raise RunNotFoundError(f"Run metadata path is not available for run: {run_id}")
    path = Path(str(metadata_path))
    if not path.exists():
        raise RunNotFoundError(f"Run metadata file was not found for run: {run_id}")
    data = _read_json(path)
    if not isinstance(data, dict):
        raise RunNotFoundError(f"Run metadata is not valid for run: {run_id}")
    return data


def get_report_paths(
    run_id: str,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
) -> dict[str, str | None]:
    """Return report paths for one known run."""

    run = _find_run(run_id=run_id, reports_dir=reports_dir)
    return {
        "markdown_report_path": _optional_string(run.get("markdown_report_path")),
        "json_report_path": _optional_string(run.get("json_report_path")),
        "run_metadata_path": _optional_string(run.get("run_metadata_path")),
    }


def _find_run(run_id: str, reports_dir: Path) -> dict[str, Any]:
    """Find a run summary by id."""

    for run in list_runs(reports_dir):
        if run.get("run_id") == run_id:
            return run
    raise RunNotFoundError(f"Run not found: {run_id}")


def _validate_dataset_path(path: Path) -> None:
    """Validate a local dataset path."""

    if not path.exists():
        raise ApiRequestError(f"Dataset path does not exist: {path}")
    if not path.is_dir():
        raise ApiRequestError(f"Dataset path must be a directory: {path}")


def _validate_config_path(path: Path | None) -> None:
    """Validate an optional local config path."""

    if path is None:
        return
    if not path.exists():
        raise ApiRequestError(f"Config path does not exist: {path}")
    if not path.is_file():
        raise ApiRequestError(f"Config path must be a file: {path}")


def _report_filename(run_name: str | None) -> str:
    """Return a safe Markdown report filename."""

    if not run_name:
        return "ade_report.md"
    stem = re.sub(r"[^a-zA-Z0-9_.-]+", "_", run_name).strip("._")
    if not stem:
        stem = "ade_report"
    return f"{Path(stem).stem}.md"


def _read_json(path: Path) -> Any:
    """Read JSON from a local path."""

    return json.loads(path.read_text(encoding="utf-8"))


def _optional_string(value: object) -> str | None:
    """Return a string value or None."""

    if value is None:
        return None
    return str(value)

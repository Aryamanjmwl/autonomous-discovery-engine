"""Dependency-light service helpers for the ADE Studio local API."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import UTC, datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from ade import __version__
from ade.cli import run_pipeline
from ade.reporting.html_report import write_html_report
from ade.reporting.report_validator import validate_report_file
from ade.reporting.run_index import load_run_index

DEFAULT_REPORTS_DIR = Path("data/reports")
DEFAULT_RUN_INDEX_PATH = Path("data/reports/runs/index.json")
DEFAULT_DASHBOARD_DIR = Path("data/dashboard")
DEFAULT_FEEDBACK_PATH = Path("data/feedback/feedback.jsonl")
DEFAULT_REPORT_ASSETS_DIR = Path("data/reports/assets")
DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[3]


@dataclass(frozen=True)
class StudioPaths:
    """Local artifact locations used by ADE Studio."""

    reports_dir: Path = DEFAULT_REPORTS_DIR
    run_index_path: Path = DEFAULT_RUN_INDEX_PATH
    dashboard_dir: Path = DEFAULT_DASHBOARD_DIR
    feedback_path: Path = DEFAULT_FEEDBACK_PATH
    report_assets_dir: Path = DEFAULT_REPORT_ASSETS_DIR
    project_root: Path = DEFAULT_PROJECT_ROOT


def health_status() -> dict[str, object]:
    """Return local ADE engine status for ADE Studio."""

    return {
        "status": "ok",
        "engine": "ADE",
        "version": __version__,
        "mode": "local-only",
        "label": "Technical Preview",
        "supports_remote_execution": False,
        "supported_workflows": ["visual"],
        "human_review_required": True,
    }


def build_summary(paths: StudioPaths = StudioPaths()) -> dict[str, object]:
    """Return local artifact counts and latest run context."""

    runs = list_runs(paths=paths)
    reports = list_reports(paths=paths)
    latest_run = runs[0] if runs else None
    latest_report = reports[0] if reports else None
    feedback_count = _count_feedback_records(paths.feedback_path)
    latest_report_detail = (
        _normalize_report_detail(latest_report["name"], paths, _load_json_object(paths.reports_dir / latest_report["name"]))
        if latest_report is not None and isinstance(latest_report.get("name"), str)
        else None
    )
    return {
        "mode": "local-only",
        "label": "Technical Preview",
        "reports_dir": paths.reports_dir.as_posix(),
        "run_index_path": paths.run_index_path.as_posix(),
        "dashboard_dir": paths.dashboard_dir.as_posix(),
        "feedback_path": paths.feedback_path.as_posix(),
        "run_count": len(runs),
        "report_count": len(reports),
        "feedback_count": feedback_count,
        "latest_run": latest_run,
        "latest_report": latest_report,
        "latest_run_id": _string_from_mapping(latest_run, "run_id"),
        "latest_report_name": _string_from_mapping(latest_report, "name"),
        "latest_report_json_path": _string_from_mapping(latest_report, "path"),
        "latest_report_html_path": _string_from_mapping(latest_report, "html_path"),
        "candidate_anomaly_count": _int_from_mapping(
            latest_report,
            "candidate_anomaly_count",
        ),
        "candidate_concept_count": _int_from_mapping(
            latest_report,
            "candidate_concept_count",
        ),
        "input_type": _string_from_mapping(latest_report_detail, "input_type"),
        "input_directory": _string_from_mapping(latest_report_detail, "input_directory"),
        "number_of_images": _int_from_mapping(latest_report_detail, "number_of_images"),
        "number_of_patches": _int_from_mapping(latest_report_detail, "number_of_patches"),
        "human_review_required": True,
        "no_cloud_upload": True,
    }


def list_runs(paths: StudioPaths = StudioPaths(), limit: int = 25) -> list[dict[str, object]]:
    """Return recent run summaries from the local run index."""

    index = load_run_index(paths.run_index_path)
    if index is None:
        return []
    runs = [run for run in index.get("runs", []) if isinstance(run, dict)]
    runs.reverse()
    return [_json_safe(run) for run in runs[:limit]]


def list_reports(paths: StudioPaths = StudioPaths()) -> list[dict[str, object]]:
    """Return available local ADE JSON reports."""

    reports_dir = paths.reports_dir
    if not reports_dir.exists() or not reports_dir.is_dir():
        return []

    reports: list[dict[str, object]] = []
    for report_path in sorted(reports_dir.glob("*.json"), key=_modified_time, reverse=True):
        report = _load_json_object(report_path)
        if report is None or "candidate_anomalies" not in report:
            continue
        markdown_path = report_path.with_suffix(".md")
        html_path = report_path.with_suffix(".html")
        reports.append(
            {
                "name": report_path.name,
                "path": report_path.as_posix(),
                "markdown_path": markdown_path.as_posix() if markdown_path.exists() else None,
                "html_path": html_path.as_posix() if html_path.exists() else None,
                "run_id": report.get("run_id"),
                "generated_at": _generated_at(report),
                "candidate_anomaly_count": len(_list(report.get("candidate_anomalies"))),
                "candidate_concept_count": len(
                    _list(report.get("candidate_unknown_concepts"))
                ),
                "human_review_required": report.get("human_review_required") is True,
                "modality": report.get("modality", "image"),
            }
        )
    return reports


def load_report(report_name: str, paths: StudioPaths = StudioPaths()) -> dict[str, object]:
    """Return normalized report detail plus the raw local report JSON."""

    safe_name = Path(report_name).name
    if safe_name != report_name or not safe_name.endswith(".json"):
        raise ValueError("report_name must be the name of a local JSON report file")
    report_path = paths.reports_dir / safe_name
    if not report_path.exists() or not report_path.is_file():
        raise FileNotFoundError(f"Report was not found: {safe_name}")
    report = _load_json_object(report_path)
    if report is None:
        raise ValueError(f"Report is not valid JSON: {safe_name}")
    detail = _normalize_report_detail(safe_name, paths, report)
    detail["raw_report"] = report
    return _json_safe(detail)


def resolve_report_asset(asset_name: str, paths: StudioPaths = StudioPaths()) -> Path:
    """Return a safe local report asset path by filename."""

    safe_name = Path(asset_name).name
    if safe_name != asset_name:
        raise ValueError("asset_name must be a local report asset filename")
    asset_path = paths.report_assets_dir / safe_name
    assets_root = paths.report_assets_dir.resolve()
    resolved_asset = asset_path.resolve()
    if assets_root not in resolved_asset.parents:
        raise ValueError("asset_name must resolve inside the report assets directory")
    if not resolved_asset.exists() or not resolved_asset.is_file():
        raise FileNotFoundError(f"Report asset was not found: {safe_name}")
    return resolved_asset


def run_visual_analysis(
    input_path: Path | str,
    output_name: str | None = None,
    paths: StudioPaths = StudioPaths(),
) -> dict[str, object]:
    """Run ADE's existing visual workflow for a local image folder."""

    source = _resolve_input_path(input_path, paths.project_root)
    if not source.exists():
        raise FileNotFoundError(f"Input path does not exist: {source}")
    if not source.is_dir():
        raise ValueError("Only visual/image-folder analysis is supported in ADE Studio.")

    report_name = _report_name(output_name)
    output_path = paths.reports_dir / report_name
    output_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path = run_pipeline(input_dir=source, output_path=output_path, modality="image")
    json_path = markdown_path.with_suffix(".json")
    validation = validate_report_file(json_path)
    if not validation.is_valid:
        errors = "; ".join(validation.errors)
        raise ValueError(f"Generated report did not validate: {errors}")

    html_path = json_path.with_suffix(".html")
    try:
        write_html_report(json_path, html_path)
    except (OSError, ValueError, JSONDecodeError):
        html_path = None

    report = _load_json_object(json_path) or {}
    detail = _normalize_report_detail(json_path.name, paths, report)
    return {
        "status": "ok",
        "message": "Analysis complete.",
        "run_id": report.get("run_id"),
        "workflow": "visual",
        "input_path": source.as_posix(),
        "number_of_images": detail["number_of_images"],
        "number_of_patches": detail["number_of_patches"],
        "markdown_report_path": markdown_path.as_posix(),
        "json_report_path": json_path.as_posix(),
        "html_report_path": html_path.as_posix() if html_path is not None else None,
        "candidate_anomaly_count": len(_list(report.get("candidate_anomalies"))),
        "candidate_concept_count": len(_list(report.get("candidate_unknown_concepts"))),
        "human_review_required": report.get("human_review_required") is True,
        "validated": True,
    }


def _normalize_report_detail(
    report_name: str,
    paths: StudioPaths,
    report: dict[str, Any] | None,
) -> dict[str, object]:
    """Return screenshot-friendly report fields derived from ADE report JSON."""

    report = report or {}
    run_metadata = _dict(report.get("run_metadata"))
    scoring_metadata = _dict(report.get("scoring_metadata"))
    input_summary = _dict(report.get("input_summary"))
    profile = _dict(input_summary.get("profile"))
    markdown_path = _first_string(
        run_metadata.get("markdown_report_path"),
        str(paths.reports_dir / Path(report_name).with_suffix(".md").name),
    )
    json_path = _first_string(
        run_metadata.get("json_report_path"),
        str(paths.reports_dir / report_name),
    )
    html_path = str(paths.reports_dir / Path(report_name).with_suffix(".html").name)
    html_path = html_path if Path(html_path).exists() else None
    anomalies = [_normalize_candidate_anomaly(item) for item in _list(report.get("candidate_anomalies"))]
    concepts = [_json_safe(item) for item in _list(report.get("candidate_unknown_concepts"))]
    return {
        "report_name": report_name,
        "run_id": _first_string(report.get("run_id"), run_metadata.get("run_id")),
        "generated_at": _first_string(report.get("generated_at"), run_metadata.get("generated_at")),
        "input_directory": _first_string(
            run_metadata.get("input_path"),
            input_summary.get("input_dir"),
            input_summary.get("input_path"),
        ),
        "input_type": _first_string(profile.get("input_type"), report.get("modality"), "image folder"),
        "number_of_images": _first_int(
            report.get("number_of_images"),
            run_metadata.get("number_of_images"),
            profile.get("valid_images"),
        ),
        "number_of_patches": _first_int(
            report.get("number_of_patches"),
            run_metadata.get("number_of_patches"),
            run_metadata.get("total_patches"),
        ),
        "candidate_anomaly_count": len(anomalies),
        "candidate_concept_count": len(concepts),
        "novelty_strategy": _first_string(
            scoring_metadata.get("novelty_strategy"),
            run_metadata.get("novelty_strategy"),
        ),
        "human_review_required": report.get("human_review_required") is True
        or run_metadata.get("human_review_required") is True,
        "candidate_anomalies": anomalies,
        "candidate_concepts": concepts,
        "markdown_report_path": markdown_path,
        "json_report_path": json_path,
        "html_report_path": html_path,
    }


def _normalize_candidate_anomaly(item: object) -> dict[str, object]:
    """Return a stable candidate anomaly shape for ADE Studio."""

    row = _dict(item)
    preview_path = _first_string(row.get("preview_path"), row.get("preview_asset_path"))
    return {
        "anomaly_id": _first_string(row.get("anomaly_id")),
        "source_image_path": _first_string(row.get("source_path"), row.get("source_image_path")),
        "coordinates": _json_safe(row.get("coordinates")),
        "patch_scale": _first_string(row.get("scale_label"), row.get("scale_id"))
        or _first_int(row.get("patch_size")),
        "novelty_score": _first_number(row.get("novelty_score"), row.get("normalized_score")),
        "evidence_note": _first_string(row.get("reason"), row.get("evidence_note")),
        "score_breakdown": _json_safe(row.get("score_breakdown")),
        "largest_feature_deviations": _json_safe(row.get("feature_deviations")),
        "preview_asset_path": preview_path,
        "preview_asset_name": Path(preview_path).name if preview_path else None,
    }


def _resolve_input_path(input_path: Path | str, project_root: Path) -> Path:
    """Resolve absolute or repo-relative Studio analysis input paths."""

    source = Path(input_path).expanduser()
    if source.is_absolute():
        return source
    return project_root / source


def _report_name(output_name: str | None) -> str:
    """Return a safe Markdown report filename."""

    if output_name:
        safe = Path(output_name).name
        stem = Path(safe).stem
    else:
        stem = f"studio_report_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._")
    if not stem:
        stem = "studio_report"
    return f"{stem}.md"


def _load_json_object(path: Path) -> dict[str, Any] | None:
    """Return a JSON object from disk if it is safe to parse."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _count_feedback_records(path: Path) -> int:
    """Return the number of local feedback JSONL records."""

    if not path.exists() or not path.is_file():
        return 0
    try:
        return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())
    except OSError:
        return 0


def _generated_at(report: dict[str, Any]) -> object:
    """Return best available generated timestamp from a report."""

    run_metadata = report.get("run_metadata")
    if isinstance(run_metadata, dict):
        return run_metadata.get("generated_at")
    return report.get("generated_at")


def _modified_time(path: Path) -> float:
    """Return path mtime for sorting."""

    try:
        return path.stat().st_mtime
    except OSError:
        return 0.0


def _list(value: object) -> list[object]:
    """Return list values safely."""

    return value if isinstance(value, list) else []


def _dict(value: object) -> dict[str, Any]:
    """Return dict values safely."""

    return value if isinstance(value, dict) else {}


def _first_string(*values: object) -> str | None:
    """Return the first non-empty string from values."""

    for value in values:
        if isinstance(value, str) and value:
            return value
    return None


def _first_int(*values: object) -> int:
    """Return the first integer-compatible value from values."""

    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
    return 0


def _first_number(*values: object) -> float | None:
    """Return the first numeric value from values."""

    for value in values:
        if isinstance(value, bool):
            continue
        if isinstance(value, int | float):
            return float(value)
    return None


def _string_from_mapping(mapping: dict[str, object] | None, key: str) -> str | None:
    """Return a string field from a mapping when present."""

    if mapping is None:
        return None
    value = mapping.get(key)
    return value if isinstance(value, str) else None


def _int_from_mapping(mapping: dict[str, object] | None, key: str) -> int:
    """Return an integer field from a mapping when present."""

    if mapping is None:
        return 0
    value = mapping.get(key)
    return value if isinstance(value, int) else 0


def _json_safe(value: object) -> Any:
    """Return a JSON-safe value for API responses."""

    if isinstance(value, Path):
        return value.as_posix()
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe(item) for item in value]
    return value




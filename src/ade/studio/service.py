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
from ade.cancellation import CancellationToken
from ade.cli import add_feedback_from_report, run_pipeline, run_temporal_pipeline
from ade.feedback import FeedbackStore, ReviewFeedback
from ade.reporting.html_report import write_html_report
from ade.reporting.report_validator import validate_report_dict, validate_report_file
from ade.reporting.run_index import load_run_index
from ade.reporting.temporal_report import (
    TEMPORAL_REPORT_TYPE,
    validate_temporal_report_dict,
)
from ade.visual.temporal_artifacts import validate_temporal_change_artifact

DEFAULT_PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REPORTS_DIR = DEFAULT_PROJECT_ROOT / "data/reports"
DEFAULT_RUN_INDEX_PATH = DEFAULT_REPORTS_DIR / "runs/index.json"
DEFAULT_DASHBOARD_DIR = DEFAULT_PROJECT_ROOT / "data/dashboard"
DEFAULT_FEEDBACK_PATH = DEFAULT_PROJECT_ROOT / "data/feedback/feedback.jsonl"
DEFAULT_REPORT_ASSETS_DIR = DEFAULT_REPORTS_DIR / "assets"
DEFAULT_ARTIFACTS_DIR = DEFAULT_PROJECT_ROOT / "data/artifacts"
ADVANCED_EVIDENCE_FIELDS = (
    "reference_scoring_summary",
    "spatial_anomaly_map_summary",
    "calibration_summary",
    "threshold_operating_point_summary",
    "benchmark_validation_summary",
)


@dataclass(frozen=True)
class StudioPaths:
    """Local artifact locations used by ADE Studio."""

    reports_dir: Path = DEFAULT_REPORTS_DIR
    run_index_path: Path = DEFAULT_RUN_INDEX_PATH
    dashboard_dir: Path = DEFAULT_DASHBOARD_DIR
    feedback_path: Path = DEFAULT_FEEDBACK_PATH
    report_assets_dir: Path = DEFAULT_REPORT_ASSETS_DIR
    artifacts_dir: Path = DEFAULT_ARTIFACTS_DIR
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
    temporal_reports = [report for report in reports if report.get("type") == "temporal"]
    latest_temporal_report = temporal_reports[0] if temporal_reports else None
    feedback_count = _count_feedback_records(paths.feedback_path)
    latest_report_name = _string_from_mapping(latest_report, "name")
    latest_report_detail = (
        _normalize_report_detail(
            latest_report_name,
            paths,
            _load_json_object(paths.reports_dir / latest_report_name),
        )
        if latest_report_name is not None
        else None
    )
    advanced_flags = _advanced_evidence_flags(latest_report_detail)
    return {
        "mode": "local-only",
        "label": "Technical Preview",
        "reports_dir": paths.reports_dir.as_posix(),
        "run_index_path": paths.run_index_path.as_posix(),
        "dashboard_dir": paths.dashboard_dir.as_posix(),
        "feedback_path": paths.feedback_path.as_posix(),
        "run_count": len(runs),
        "report_count": len(reports),
        "temporal_report_count": len(temporal_reports),
        "latest_temporal_report": latest_temporal_report,
        "temporal_report_warnings": _temporal_report_warnings(paths),
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
        "advanced_evidence_available": advanced_flags,
        "human_review_required": True,
        "no_cloud_upload": True,
    }


def list_runs(paths: StudioPaths = StudioPaths(), limit: int = 25) -> list[dict[str, object]]:
    """Return recent run summaries from the local run index."""

    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")
    index = load_run_index(paths.run_index_path)
    if index is None:
        return []
    runs = [run for run in _list(index.get("runs")) if isinstance(run, dict)]
    runs.reverse()
    return [_json_safe(run) for run in runs[:limit]]


def list_reports(paths: StudioPaths = StudioPaths()) -> list[dict[str, object]]:
    """Return available local ADE JSON reports."""

    reports_dir = paths.reports_dir
    if not reports_dir.exists() or not reports_dir.is_dir():
        return []

    reports: list[dict[str, object]] = []
    report_paths = sorted(
        reports_dir.glob("*.json"),
        key=lambda path: (-_modified_time(path), path.name),
    )
    for report_path in report_paths:
        report = _load_json_object(report_path)
        if report is None:
            continue
        temporal = report.get("report_type") == TEMPORAL_REPORT_TYPE
        if temporal:
            if _temporal_report_error(report, report_path, paths) is not None:
                continue
        elif "candidate_anomalies" not in report:
            continue
        markdown_path = report_path.with_suffix(".md")
        html_path = report_path.with_suffix(".html")
        sequence = _dict(report.get("sequence_summary"))
        temporal_events = _list(report.get("candidate_change_events")) if temporal else []
        reports.append(
            {
                "name": report_path.name,
                "path": report_path.as_posix(),
                "markdown_path": markdown_path.as_posix() if markdown_path.exists() else None,
                "html_path": html_path.as_posix() if html_path.exists() else None,
                "run_id": report.get("run_id"),
                "generated_at": _generated_at(report),
                "candidate_anomaly_count": len(_list(report.get("candidate_anomalies"))),
                "candidate_concept_count": len(_list(report.get("candidate_unknown_concepts"))),
                "human_review_required": report.get("human_review_required") is True,
                "modality": "temporal" if temporal else report.get("modality", "image"),
                "type": "temporal" if temporal else "standard",
                "sequence_id": sequence.get("sequence_id") if temporal else None,
                "dataset_name": sequence.get("dataset_name") if temporal else None,
                "observation_count": sequence.get("observation_count") if temporal else None,
                "candidate_event_count": len(temporal_events),
            }
        )
    return reports


def load_report(report_name: str, paths: StudioPaths = StudioPaths()) -> dict[str, object]:
    """Return normalized report detail plus the raw local report JSON."""

    safe_name = _validate_report_name(report_name)
    report_path = paths.reports_dir / safe_name
    if not report_path.exists() or not report_path.is_file():
        raise FileNotFoundError(f"Report was not found: {safe_name}")
    report = _load_json_object(report_path)
    if report is None:
        raise ValueError(f"Report is not valid JSON: {safe_name}")
    if report.get("report_type") == TEMPORAL_REPORT_TYPE:
        temporal_error = _temporal_report_error(report, report_path, paths)
        if temporal_error is not None:
            raise ValueError(f"Temporal report is invalid: {temporal_error}")
    detail = _normalize_report_detail(safe_name, paths, report)
    detail["raw_report"] = report
    return _json_safe(detail)


def resolve_report_asset(asset_name: str, paths: StudioPaths = StudioPaths()) -> Path:
    """Return a safe local report asset path by filename."""

    safe_name = Path(asset_name).name
    if not asset_name or safe_name != asset_name or safe_name in {".", ".."}:
        raise ValueError("asset_name must be a local report asset filename")
    asset_path = paths.report_assets_dir / safe_name
    assets_root = paths.report_assets_dir.resolve()
    resolved_asset = asset_path.resolve()
    if assets_root not in resolved_asset.parents:
        raise ValueError("asset_name must resolve inside the report assets directory")
    if not resolved_asset.exists() or not resolved_asset.is_file():
        raise FileNotFoundError(f"Report asset was not found: {safe_name}")
    return resolved_asset


def resolve_report_html(report_name: str, paths: StudioPaths = StudioPaths()) -> Path:
    """Return a safe generated HTML report path for a local JSON report name."""

    safe_name = _validate_report_name(report_name)
    html_path = paths.reports_dir / Path(safe_name).with_suffix(".html")
    reports_root = paths.reports_dir.resolve()
    resolved_html = html_path.resolve()
    if reports_root != resolved_html.parent:
        raise ValueError("report HTML must resolve inside the reports directory")
    if not resolved_html.exists() or not resolved_html.is_file():
        raise FileNotFoundError(f"HTML report was not found for: {safe_name}")
    return resolved_html


def run_visual_analysis(
    input_path: Path | str,
    output_name: str | None = None,
    config_path: Path | str | None = None,
    paths: StudioPaths = StudioPaths(),
    cancellation_token: CancellationToken | None = None,
) -> dict[str, object]:
    """Run ADE's existing visual workflow for a local image folder."""

    source = resolve_workspace_input(input_path, paths, kind="input path")
    if not source.exists():
        raise FileNotFoundError(f"Input path does not exist: {source}")
    if not source.is_dir():
        raise ValueError("Only visual/image-folder analysis is supported in ADE Studio.")

    config = (
        resolve_workspace_input(config_path, paths, kind="config file")
        if config_path is not None
        else None
    )
    if config is not None and not config.is_file():
        raise ValueError("Config path must identify a local file.")
    output_path = resolve_report_output(output_name, paths, prefix="studio_report")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    markdown_path = run_pipeline(
        input_dir=source,
        output_path=output_path,
        config_path=config,
        modality="image",
        cancellation_token=cancellation_token,
    )
    json_path = markdown_path.with_suffix(".json")
    validation = validate_report_file(json_path)
    if not validation.is_valid:
        errors = "; ".join(validation.errors)
        raise ValueError(f"Generated report did not validate: {errors}")

    generated_html_path = json_path.with_suffix(".html")
    html_path: Path | None = generated_html_path
    try:
        write_html_report(json_path, generated_html_path)
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


def run_temporal_analysis(
    manifest_path: Path | str,
    output_name: str | None,
    *,
    strategy: str,
    patch_size: int | None = None,
    top_k: int = 10,
    patch_top_k: int = 5,
    paths: StudioPaths = StudioPaths(),
    cancellation_token: CancellationToken | None = None,
) -> dict[str, object]:
    """Run ADE's existing manifest-driven temporal workflow locally."""

    manifest = resolve_workspace_input(manifest_path, paths, kind="temporal manifest")
    if not manifest.is_file():
        raise ValueError("Temporal manifest path must identify a local file.")
    output_path = resolve_report_output(output_name, paths, prefix="studio_temporal")
    artifact_root = (paths.artifacts_dir / output_path.stem).resolve()
    _require_within(artifact_root, paths.artifacts_dir.resolve(), "artifact output")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    artifact_root.parent.mkdir(parents=True, exist_ok=True)
    markdown_path, json_path, artifact_path = run_temporal_pipeline(
        manifest,
        output_path,
        strategy=strategy,  # type: ignore[arg-type]
        patch_size=patch_size,
        top_k=top_k,
        patch_top_k=patch_top_k,
        artifact_root=artifact_root,
        cancellation_token=cancellation_token,
    )
    return {
        "status": "ok",
        "message": (
            "Temporal analysis complete. Candidate temporal changes require human review."
        ),
        "workflow": "temporal",
        "input_path": manifest.as_posix(),
        "markdown_report_path": markdown_path.as_posix(),
        "json_report_path": json_path.as_posix(),
        "artifact_path": artifact_path.as_posix(),
        "human_review_required": True,
        "validated": True,
    }


def record_review_feedback(
    *,
    report_name: str,
    finding_id: str,
    finding_type: str,
    reviewer_action: str,
    note: str = "",
    paths: StudioPaths = StudioPaths(),
) -> dict[str, object]:
    """Validate and append local Studio review feedback using ADE's JSONL store."""

    safe_name = _validate_report_name(report_name)
    report_path = paths.reports_dir / safe_name
    report = _load_json_object(report_path)
    if report is None:
        if not report_path.exists():
            raise FileNotFoundError(f"Report was not found: {safe_name}")
        raise ValueError(f"Report is not valid JSON: {safe_name}")
    label_by_action = {
        "useful": "interesting",
        "not_useful": "not_useful",
        "needs_review": "needs_more_data",
    }
    label = label_by_action.get(reviewer_action)
    if label is None:
        raise ValueError("Unsupported reviewer action")

    if finding_type == "visual_candidate":
        target_type = _visual_feedback_target_type(report, finding_id)
        feedback = add_feedback_from_report(
            report_path=report_path,
            target_type=target_type,
            target_id=finding_id,
            label=label,
            notes=note,
            reviewer="studio-local",
            store_path=paths.feedback_path,
        )
    elif finding_type == "temporal_candidate":
        error = _temporal_report_error(report, report_path, paths)
        if error is not None:
            raise ValueError(f"Temporal report is invalid: {error}")
        events = [_dict(item) for item in _list(report.get("candidate_change_events"))]
        if finding_id not in {
            str(event.get("event_id")) for event in events if event.get("event_id")
        }:
            raise ValueError(f"Candidate temporal change was not found: {finding_id}")
        summary = _dict(report.get("sequence_summary"))
        sequence_id = _first_string(summary.get("sequence_id"))
        if sequence_id is None:
            raise ValueError("Temporal report does not contain a sequence_id")
        feedback = ReviewFeedback.create(
            run_id=f"temporal:{sequence_id}",
            report_path=report_path,
            target_type="temporal",
            target_id=finding_id,
            label=label,
            notes=note,
            reviewer="studio-local",
            metadata={"report_type": TEMPORAL_REPORT_TYPE},
        )
        FeedbackStore(paths.feedback_path).append(feedback)
    else:
        raise ValueError("Unsupported finding type")

    result = feedback.to_dict()
    result["report_name"] = safe_name
    result["finding_type"] = finding_type
    result["reviewer_action"] = reviewer_action
    result["human_review_required"] = True
    return _json_safe(result)


def _visual_feedback_target_type(report: dict[str, Any], finding_id: str) -> str:
    anomalies = [_dict(item) for item in _list(report.get("candidate_anomalies"))]
    concepts = [_dict(item) for item in _list(report.get("candidate_unknown_concepts"))]
    if finding_id in {
        str(item.get("anomaly_id") or item.get("id"))
        for item in anomalies
        if item.get("anomaly_id") or item.get("id")
    }:
        return "anomaly"
    if finding_id in {
        str(item.get("concept_id") or item.get("id"))
        for item in concepts
        if item.get("concept_id") or item.get("id")
    }:
        return "concept"
    raise ValueError(f"Visual candidate was not found: {finding_id}")


def resolve_workspace_input(
    input_path: Path | str,
    paths: StudioPaths,
    *,
    kind: str,
) -> Path:
    """Validate and resolve a local input confined to the Studio workspace."""

    raw_path = str(input_path).strip()
    if not raw_path or "\x00" in raw_path:
        raise ValueError(f"{kind} must be a non-empty local filesystem path")
    if _looks_like_url(raw_path):
        raise ValueError(f"{kind} must not be an external URL")
    candidate = Path(raw_path)
    if ".." in candidate.parts:
        raise ValueError(f"{kind} must not contain path traversal")
    root = paths.project_root.resolve()
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    _require_within(resolved, root, kind)
    if not resolved.exists():
        raise FileNotFoundError(f"{kind.capitalize()} does not exist: {resolved}")
    return resolved


def resolve_report_output(
    output_name: str | None,
    paths: StudioPaths,
    *,
    prefix: str,
) -> Path:
    """Resolve a Markdown output confined to the configured reports root."""

    reports_root = paths.reports_dir.resolve()
    if output_name is None or not output_name.strip():
        name = f"{prefix}_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S_%f')}.md"
        return reports_root / name
    raw_path = output_name.strip()
    if "\x00" in raw_path or _looks_like_url(raw_path):
        raise ValueError("Output report must be a local path")
    candidate = Path(raw_path)
    if ".." in candidate.parts:
        raise ValueError("Output report must not contain path traversal")
    resolved = (
        candidate.resolve()
        if candidate.is_absolute()
        else (reports_root / candidate).resolve()
    )
    _require_within(resolved, reports_root, "output report")
    if resolved.parent != reports_root:
        raise ValueError("Output report must be directly inside the reports directory")
    return resolved.with_suffix(".md")


def _require_within(path: Path, root: Path, kind: str) -> None:
    if path != root and root not in path.parents:
        raise ValueError(f"{kind.capitalize()} must remain inside the approved local root")


def _looks_like_url(value: str) -> bool:
    return bool(re.match(r"^[A-Za-z][A-Za-z0-9+.-]*://", value))


def _normalize_report_detail(
    report_name: str,
    paths: StudioPaths,
    report: dict[str, Any] | None,
) -> dict[str, object]:
    """Return screenshot-friendly report fields derived from ADE report JSON."""

    report = report or {}
    if report.get("report_type") == TEMPORAL_REPORT_TYPE:
        return _normalize_temporal_report_detail(report_name, paths, report)
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
    html_candidate = paths.reports_dir / Path(report_name).with_suffix(".html").name
    html_path = str(html_candidate) if html_candidate.exists() else None
    anomalies = [
        _normalize_candidate_anomaly(item) for item in _list(report.get("candidate_anomalies"))
    ]
    concepts = [_json_safe(item) for item in _list(report.get("candidate_unknown_concepts"))]
    advanced_evidence = _valid_advanced_evidence(report)
    return {
        "report_name": report_name,
        "run_id": _first_string(report.get("run_id"), run_metadata.get("run_id")),
        "generated_at": _first_string(report.get("generated_at"), run_metadata.get("generated_at")),
        "input_directory": _first_string(
            run_metadata.get("input_path"),
            input_summary.get("input_dir"),
            input_summary.get("input_path"),
        ),
        "input_type": _first_string(
            profile.get("input_type"), report.get("modality"), "image folder"
        ),
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
        "advanced_evidence": advanced_evidence,
        "advanced_evidence_available": {
            key: key in advanced_evidence for key in ADVANCED_EVIDENCE_FIELDS
        },
        "markdown_report_path": markdown_path,
        "json_report_path": json_path,
        "html_report_path": html_path,
    }


def _normalize_temporal_report_detail(
    report_name: str,
    paths: StudioPaths,
    report: dict[str, Any],
) -> dict[str, object]:
    """Return validated temporal report fields for connected Studio views."""

    summary = _dict(report.get("sequence_summary"))
    provenance = _dict(report.get("artifact_provenance"))
    events = [_json_safe(item) for item in _list(report.get("candidate_change_events"))]
    markdown_candidate = paths.reports_dir / Path(report_name).with_suffix(".md").name
    html_candidate = paths.reports_dir / Path(report_name).with_suffix(".html").name
    return {
        "report_name": report_name,
        "report_type": "temporal",
        "run_id": None,
        "generated_at": None,
        "input_directory": None,
        "input_type": "temporal observation sequence",
        "number_of_images": _first_int(summary.get("observation_count")),
        "number_of_patches": 0,
        "candidate_anomaly_count": 0,
        "candidate_concept_count": 0,
        "candidate_event_count": len(events),
        "novelty_strategy": None,
        "human_review_required": report.get("human_review_required") is True,
        "candidate_anomalies": [],
        "candidate_concepts": [],
        "candidate_temporal_change_events": events,
        "temporal_sequence_summary": _json_safe(summary),
        "temporal_artifact_provenance": _json_safe(provenance),
        "temporal_warnings": _json_safe(report.get("warnings")),
        "temporal_limitations": _json_safe(report.get("limitations")),
        "advanced_evidence": {},
        "advanced_evidence_available": {key: False for key in ADVANCED_EVIDENCE_FIELDS},
        "markdown_report_path": (
            markdown_candidate.as_posix() if markdown_candidate.is_file() else None
        ),
        "json_report_path": (paths.reports_dir / report_name).as_posix(),
        "html_report_path": html_candidate.as_posix() if html_candidate.is_file() else None,
    }


def _temporal_report_error(
    report: dict[str, Any], report_path: Path, paths: StudioPaths
) -> str | None:
    errors = validate_temporal_report_dict(report)
    if errors:
        return "; ".join(errors)
    provenance = _dict(report.get("artifact_provenance"))
    artifact_value = provenance.get("artifact_path")
    if not isinstance(artifact_value, str) or not artifact_value:
        return "artifact path is missing"
    artifact_path = Path(artifact_value)
    if not artifact_path.is_absolute():
        artifact_path = report_path.parent / artifact_path
    resolved = artifact_path.resolve()
    allowed_roots = (paths.reports_dir.resolve(), paths.project_root.resolve())
    if not any(resolved == root or resolved.is_relative_to(root) for root in allowed_roots):
        return "artifact path resolves outside the local workspace"
    fingerprint = provenance.get("artifact_fingerprint")
    if resolved.name != fingerprint:
        return "artifact path does not match its fingerprint"
    try:
        validate_temporal_change_artifact(resolved)
    except (OSError, ValueError) as error:
        return f"artifact validation failed: {error}"
    return None


def _temporal_report_warnings(paths: StudioPaths) -> list[str]:
    if not paths.reports_dir.is_dir():
        return []
    warnings: list[str] = []
    for report_path in sorted(paths.reports_dir.glob("*.json")):
        report = _load_json_object(report_path)
        if report is None or report.get("report_type") != TEMPORAL_REPORT_TYPE:
            continue
        error = _temporal_report_error(report, report_path, paths)
        if error is not None:
            warnings.append(f"Ignored {report_path.name}: {error}")
    return warnings


def _valid_advanced_evidence(report: dict[str, Any]) -> dict[str, object]:
    """Return only strict artifact-backed optional evidence summaries."""

    evidence: dict[str, object] = {}
    for field_name in ADVANCED_EVIDENCE_FIELDS:
        if field_name not in report:
            continue
        candidate = {
            "project_name": "ADE",
            "run_id": "studio-validation",
            "run_metadata": {},
            "candidate_anomalies": [],
            "candidate_unknown_concepts": [],
            "human_review_required": True,
            field_name: report[field_name],
        }
        if validate_report_dict(candidate).is_valid:
            evidence[field_name] = _json_safe(report[field_name])
    return evidence


def _advanced_evidence_flags(
    detail: dict[str, object] | None,
) -> dict[str, bool]:
    evidence = _dict(detail.get("advanced_evidence")) if detail is not None else {}
    return {key: key in evidence for key in ADVANCED_EVIDENCE_FIELDS}


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

    raw_path = str(input_path).strip()
    if not raw_path or "\x00" in raw_path:
        raise ValueError("input_path must be a non-empty local filesystem path")
    source = Path(raw_path).expanduser()
    if source.is_absolute():
        return source.resolve()
    return (project_root / source).resolve()


def _report_name(output_name: str | None) -> str:
    """Return a safe Markdown report filename."""

    if output_name and output_name.strip():
        if "\x00" in output_name:
            raise ValueError("output_name contains an invalid null byte")
        safe = Path(output_name).name
        stem = Path(safe).stem
    else:
        stem = f"studio_report_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", stem).strip("._")
    if not stem:
        stem = "studio_report"
    return f"{stem}.md"


def _validate_report_name(report_name: str) -> str:
    """Validate an API-visible JSON report filename."""

    safe_name = Path(report_name).name
    if (
        not report_name
        or "\x00" in report_name
        or safe_name != report_name
        or safe_name in {".", ".."}
        or Path(safe_name).suffix.lower() != ".json"
    ):
        raise ValueError("report_name must be the name of a local JSON report file")
    return safe_name


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

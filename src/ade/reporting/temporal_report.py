"""Deterministic review reports for temporal visual change results."""

from __future__ import annotations

import json
import math
from html import escape
from pathlib import Path
from typing import Any

from ade.visual.config import VISUAL_ENGINE_SCHEMA_VERSION
from ade.visual.temporal_contracts import TemporalChangeResult

TEMPORAL_REPORT_TYPE = "temporal-visual-change-report"
TEMPORAL_REPORT_SCHEMA_VERSION = 1
_CERTAINTY_LANGUAGE = (
    "confirmed geological activity",
    "confirmed biological growth",
    "guaranteed movement detection",
    "autonomous scientific conclusion",
    "production monitoring",
)


def build_temporal_report(
    result: TemporalChangeResult,
    artifact_path: Path,
    artifact_fingerprint: str,
) -> dict[str, object]:
    """Build a deterministic, artifact-backed temporal report dictionary."""

    sequence = result.sequence
    ordering_mode = (
        "timestamp" if sequence.observations[0].timestamp is not None else "sequence_index"
    )
    events = [
        {
            "event_id": event.event_id,
            "rank": event.rank,
            "candidate_label": event.candidate_label,
            "possible_interpretation": event.possible_interpretation,
            "source_observation_id": event.score.source_observation_id,
            "target_observation_id": event.score.target_observation_id,
            "change_score": event.score.global_feature_distance,
            "requires_human_review": event.requires_human_review,
            "patch_evidence": [
                {
                    "source_observation_id": patch.source_observation_id,
                    "target_observation_id": patch.target_observation_id,
                    "x": patch.x,
                    "y": patch.y,
                    "width": patch.width,
                    "height": patch.height,
                    "patch_scale": patch.patch_scale,
                    "change_score": patch.change_score,
                    "evidence_note": patch.evidence_note,
                }
                for patch in event.patch_evidence
            ],
        }
        for event in result.events
    ]
    return {
        "schema_version": TEMPORAL_REPORT_SCHEMA_VERSION,
        "visual_engine_schema_version": VISUAL_ENGINE_SCHEMA_VERSION,
        "report_type": TEMPORAL_REPORT_TYPE,
        "sequence_summary": {
            "sequence_id": sequence.sequence_id,
            "dataset_name": sequence.dataset_name,
            "dataset_version": sequence.dataset_version,
            "scene_id": sequence.scene_id,
            "entity_id": sequence.entity_id,
            "observation_count": result.summary.observation_count,
            "ordering_mode": ordering_mode,
            "range_start": result.summary.range_start,
            "range_end": result.summary.range_end,
            "strategy": result.provenance.strategy,
            "max_change_score": result.summary.max_change_score,
            "mean_adjacent_change_score": result.summary.mean_adjacent_change_score,
            "strongest_observation_pair": list(result.summary.strongest_observation_pair),
        },
        "observation_ids": [item.observation_id for item in sequence.observations],
        "candidate_change_events": events,
        "artifact_provenance": {
            "artifact_path": artifact_path.resolve().as_posix(),
            "artifact_fingerprint": artifact_fingerprint,
            "manifest_fingerprint": result.provenance.manifest_fingerprint,
            "feature_backend": result.provenance.feature_backend,
            "feature_backend_version": result.provenance.feature_backend_version,
            "deterministic": result.provenance.deterministic,
            "local_offline": result.provenance.local_offline,
        },
        "warnings": list(result.summary.warnings),
        "limitations": list(result.provenance.limitations),
        "human_review_required": True,
    }


def render_temporal_markdown(report: dict[str, Any]) -> str:
    """Render a cautious Markdown temporal review report."""

    summary = _object(report.get("sequence_summary"))
    provenance = _object(report.get("artifact_provenance"))
    lines = [
        "# ADE Temporal Change Report",
        "",
        "Candidate temporal changes are review-prioritization signals and require human review.",
        "",
        "## Observation Sequence",
        "",
        f"- Sequence ID: `{summary.get('sequence_id')}`",
        f"- Dataset: `{summary.get('dataset_name')}` version `{summary.get('dataset_version')}`",
    ]
    if summary.get("scene_id") is not None:
        lines.append(f"- Scene ID: `{summary['scene_id']}`")
    if summary.get("entity_id") is not None:
        lines.append(f"- Entity ID: `{summary['entity_id']}`")
    lines.extend(
        [
            f"- Observations: {summary.get('observation_count')}",
            f"- Ordering mode: `{summary.get('ordering_mode')}`",
            f"- Range: `{summary.get('range_start')}` to `{summary.get('range_end')}`",
            f"- Strategy: `{summary.get('strategy')}`",
            "",
            "## Candidate Change Summary",
            "",
            f"- Maximum change score: {_number(summary.get('max_change_score'))}",
            f"- Mean adjacent change score: {_number(summary.get('mean_adjacent_change_score'))}",
            f"- Strongest observation pair: `{_pair(summary.get('strongest_observation_pair'))}`",
            "",
            "## Top Candidate Temporal Change Events",
            "",
        ]
    )
    events = report.get("candidate_change_events")
    if isinstance(events, list) and events:
        lines.extend(
            [
                "| Rank | Candidate change event | Source | Target | Change score | Review |",
                "| ---: | --- | --- | --- | ---: | --- |",
            ]
        )
        for event_value in events:
            event = _object(event_value)
            lines.append(
                f"| {event.get('rank')} | `{event.get('event_id')}` | "
                f"`{event.get('source_observation_id')}` | "
                f"`{event.get('target_observation_id')}` | "
                f"{_number(event.get('change_score'))} | requires human review |"
            )
            patches = event.get("patch_evidence")
            if isinstance(patches, list) and patches:
                lines.extend(["", f"Patch evidence for `{event.get('event_id')}`:"])
                for patch_value in patches:
                    patch = _object(patch_value)
                    lines.append(
                        "- Source pair "
                        f"`{patch.get('source_observation_id')}` → "
                        f"`{patch.get('target_observation_id')}`; coordinates "
                        f"({patch.get('x')}, {patch.get('y')}, {patch.get('width')}, "
                        f"{patch.get('height')}); change score "
                        f"{_number(patch.get('change_score'))}"
                    )
    else:
        lines.append("No candidate change events were reported.")
    lines.extend(
        [
            "",
            "## Artifact Provenance",
            "",
            f"- Artifact path: `{provenance.get('artifact_path')}`",
            f"- Artifact fingerprint: `{provenance.get('artifact_fingerprint')}`",
            f"- Manifest fingerprint: `{provenance.get('manifest_fingerprint')}`",
            f"- Feature backend: `{provenance.get('feature_backend')}`",
            "",
            "## Warnings and Limitations",
            "",
        ]
    )
    warnings = report.get("warnings")
    limitations = report.get("limitations")
    notes = [
        str(item)
        for values in (warnings, limitations)
        if isinstance(values, list)
        for item in values
    ]
    lines.extend(f"- {note}" for note in notes)
    lines.extend(
        [
            "- ADE does not confirm movement, growth, damage, or scientific causation.",
            "- Every candidate temporal change requires human review.",
            "",
        ]
    )
    return "\n".join(lines)


def write_temporal_report(
    result: TemporalChangeResult,
    output_path: Path,
    artifact_path: Path,
    artifact_fingerprint: str,
) -> tuple[Path, Path]:
    """Write deterministic Markdown and canonical-readable JSON report files."""

    report = build_temporal_report(result, artifact_path, artifact_fingerprint)
    validation = validate_temporal_report_dict(report)
    if validation:
        raise ValueError("Invalid generated temporal report: " + "; ".join(validation))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_temporal_markdown(report), encoding="utf-8", newline="\n")
    json_path = output_path.with_suffix(".json")
    json_path.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return output_path, json_path


def validate_temporal_report_file(path: Path) -> list[str]:
    """Return temporal report validation errors for a JSON file."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        return [f"Temporal report is not valid JSON: {error}"]
    if not isinstance(value, dict):
        return ["Temporal report root must be an object."]
    return validate_temporal_report_dict(value)


def validate_temporal_report_dict(report: dict[str, Any]) -> list[str]:
    """Strictly validate temporal report identity, references, and finite scores."""

    errors: list[str] = []
    if report.get("schema_version") != TEMPORAL_REPORT_SCHEMA_VERSION:
        errors.append("schema_version is unsupported.")
    if report.get("visual_engine_schema_version") != VISUAL_ENGINE_SCHEMA_VERSION:
        errors.append("visual_engine_schema_version is unsupported.")
    if report.get("report_type") != TEMPORAL_REPORT_TYPE:
        errors.append("report_type must identify a temporal visual change report.")
    if report.get("human_review_required") is not True:
        errors.append("human_review_required must be true.")
    summary = report.get("sequence_summary")
    if not isinstance(summary, dict):
        errors.append("sequence_summary must be an object.")
        summary = {}
    for key in ("sequence_id", "dataset_name", "dataset_version", "range_start", "range_end"):
        if not isinstance(summary.get(key), str) or not summary[key]:
            errors.append(f"sequence_summary.{key} must be a non-empty string.")
    if summary.get("ordering_mode") not in {"timestamp", "sequence_index"}:
        errors.append("sequence_summary.ordering_mode is unsupported.")
    if summary.get("strategy") not in {"adjacent_difference", "baseline_difference"}:
        errors.append("sequence_summary.strategy is unsupported.")
    _finite(summary, "max_change_score", "sequence_summary", errors)
    _finite(summary, "mean_adjacent_change_score", "sequence_summary", errors)
    observation_ids = report.get("observation_ids")
    if (
        not isinstance(observation_ids, list)
        or len(observation_ids) < 2
        or any(not isinstance(item, str) or not item for item in observation_ids)
    ):
        errors.append("observation_ids must contain at least two non-empty strings.")
        known_ids: set[str] = set()
    else:
        known_ids = set(observation_ids)
        if len(known_ids) != len(observation_ids):
            errors.append("observation_ids must be unique.")
        observation_count = summary.get("observation_count")
        if (
            not isinstance(observation_count, int)
            or isinstance(observation_count, bool)
            or observation_count != len(observation_ids)
        ):
            errors.append("sequence_summary.observation_count must match observation_ids.")
    pair = summary.get("strongest_observation_pair")
    if not isinstance(pair, list) or len(pair) != 2 or any(item not in known_ids for item in pair):
        errors.append("sequence_summary.strongest_observation_pair must reference observations.")
    events = report.get("candidate_change_events")
    if not isinstance(events, list):
        errors.append("candidate_change_events must be a list.")
    else:
        _validate_events(events, known_ids, errors)
    provenance = report.get("artifact_provenance")
    if not isinstance(provenance, dict):
        errors.append("artifact_provenance must be an object.")
    else:
        for key in ("artifact_path", "artifact_fingerprint", "manifest_fingerprint"):
            if not isinstance(provenance.get(key), str) or not provenance[key]:
                errors.append(f"artifact_provenance.{key} must be a non-empty string.")
        for key in ("artifact_fingerprint", "manifest_fingerprint"):
            value = provenance.get(key)
            if isinstance(value, str) and (
                len(value) != 64 or any(character not in "0123456789abcdef" for character in value)
            ):
                errors.append(f"artifact_provenance.{key} must be a lowercase SHA-256 digest.")
    for key in ("warnings", "limitations"):
        values = report.get(key)
        if not isinstance(values, list) or any(not isinstance(item, str) for item in values):
            errors.append(f"{key} must be a list of strings.")
        elif any(term in item.lower() for item in values for term in _CERTAINTY_LANGUAGE):
            errors.append(f"{key} contains prohibited scientific-certainty language.")
    return errors


def write_temporal_html_report(report_path: Path, output_path: Path) -> Path:
    """Validate and export a static temporal HTML review report."""

    errors = validate_temporal_report_file(report_path)
    if errors:
        raise ValueError("Invalid temporal report: " + "; ".join(errors))
    report = json.loads(report_path.read_text(encoding="utf-8"))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_temporal_html(report), encoding="utf-8")
    return output_path


def render_temporal_html(report: dict[str, Any]) -> str:
    """Render metadata and evidence without inventing charts or image previews."""

    summary = _object(report.get("sequence_summary"))
    rows = []
    for value in report.get("candidate_change_events", []):
        event = _object(value)
        patches = event.get("patch_evidence")
        patch_items = []
        if isinstance(patches, list):
            for patch_value in patches:
                patch = _object(patch_value)
                patch_items.append(
                    "<li>"
                    f"{_html(patch.get('source_observation_id'))} → "
                    f"{_html(patch.get('target_observation_id'))}; "
                    f"({_html(patch.get('x'))}, {_html(patch.get('y'))}, "
                    f"{_html(patch.get('width'))}, {_html(patch.get('height'))}); "
                    f"score {_html(patch.get('change_score'))}</li>"
                )
        patch_metadata = f"<ul>{''.join(patch_items)}</ul>" if patch_items else "none"
        rows.append(
            "<tr>"
            f"<td>{_html(event.get('rank'))}</td><td>{_html(event.get('event_id'))}</td>"
            f"<td>{_html(event.get('source_observation_id'))}</td>"
            f"<td>{_html(event.get('target_observation_id'))}</td>"
            f"<td>{_html(event.get('change_score'))}</td><td>{patch_metadata}</td>"
            "</tr>"
        )
    warnings = [
        str(item)
        for key in ("warnings", "limitations")
        for item in report.get(key, [])
        if isinstance(item, str)
    ]
    warning_items = "".join(f"<li>{_html(item)}</li>" for item in warnings)
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        "<title>ADE Temporal Change Report</title><style>"
        "body{font-family:Arial,sans-serif;margin:2rem;line-height:1.5}"
        "table{border-collapse:collapse;width:100%}"
        "th,td{border:1px solid #ddd;padding:.5rem;text-align:left}"
        "code{background:#f4f4f4;padding:.1rem .25rem}</style></head><body>"
        "<h1>ADE Temporal Change Report</h1>"
        "<p>Candidate temporal changes are review-prioritization signals and "
        "require human review.</p><h2>Observation Sequence</h2>"
        f"<p>Sequence <code>{_html(summary.get('sequence_id'))}</code>; dataset "
        f"<code>{_html(summary.get('dataset_name'))}</code>; "
        f"{summary.get('observation_count')} observations ordered by "
        f"{_html(summary.get('ordering_mode'))}.</p>"
        f"<p>Range: {_html(summary.get('range_start'))} to "
        f"{_html(summary.get('range_end'))}. Strategy: "
        f"<code>{_html(summary.get('strategy'))}</code>.</p>"
        f"<p>Strongest pair: <code>"
        f"{_html(_pair(summary.get('strongest_observation_pair')))}</code>.</p>"
        "<h2>Candidate Change Events</h2><table><thead><tr>"
        "<th>Rank</th><th>Event</th><th>Source</th><th>Target</th>"
        "<th>Change score</th><th>Patch evidence</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody></table><h2>Warnings and Limitations</h2>"
        f"<ul>{warning_items}</ul><p><strong>Every candidate change event requires "
        "human review.</strong></p></body></html>"
    )


def _validate_events(events: list[Any], known_ids: set[str], errors: list[str]) -> None:
    previous_key: tuple[float, str] | None = None
    for index, value in enumerate(events, 1):
        if not isinstance(value, dict):
            errors.append(f"candidate_change_events[{index}] must be an object.")
            continue
        source = value.get("source_observation_id")
        target = value.get("target_observation_id")
        if source not in known_ids or target not in known_ids:
            errors.append(f"candidate_change_events[{index}] references an unknown observation.")
        if source == target:
            errors.append(f"candidate_change_events[{index}] must compare two observations.")
        if value.get("rank") != index:
            errors.append(f"candidate_change_events[{index}].rank must match report ordering.")
        score = _finite(value, "change_score", f"candidate_change_events[{index}]", errors)
        if value.get("requires_human_review") is not True:
            errors.append(f"candidate_change_events[{index}].requires_human_review must be true.")
        event_id = value.get("event_id")
        if not isinstance(event_id, str) or not event_id:
            errors.append(f"candidate_change_events[{index}].event_id must be a non-empty string.")
            event_id = ""
        if score is not None:
            order_key = (-score, event_id)
            if previous_key is not None and order_key < previous_key:
                errors.append("candidate_change_events must use deterministic score ordering.")
            previous_key = order_key
        patches = value.get("patch_evidence")
        if not isinstance(patches, list):
            errors.append(f"candidate_change_events[{index}].patch_evidence must be a list.")
            continue
        for patch_index, patch in enumerate(patches, 1):
            if not isinstance(patch, dict):
                errors.append(
                    f"candidate_change_events[{index}].patch_evidence[{patch_index}] "
                    "must be an object."
                )
                continue
            for key in ("x", "y", "width", "height"):
                coordinate = patch.get(key)
                minimum = 1 if key in {"width", "height"} else 0
                if (
                    not isinstance(coordinate, int)
                    or isinstance(coordinate, bool)
                    or coordinate < minimum
                ):
                    errors.append(f"patch evidence {key} has an invalid coordinate.")
            if (
                patch.get("source_observation_id") != source
                or patch.get("target_observation_id") != target
            ):
                errors.append("patch evidence source pair must match its candidate event.")
            _finite(patch, "change_score", "patch evidence", errors)


def _finite(value: dict[str, Any], key: str, prefix: str, errors: list[str]) -> float | None:
    item = value.get(key)
    if (
        not isinstance(item, int | float)
        or isinstance(item, bool)
        or not math.isfinite(float(item))
    ):
        errors.append(f"{prefix}.{key} must be a finite number.")
        return None
    return float(item)


def _object(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _number(value: object) -> str:
    return f"{float(value):.6f}" if isinstance(value, int | float) else "not available"


def _pair(value: object) -> str:
    return " → ".join(str(item) for item in value) if isinstance(value, list) else "not available"


def _html(value: object) -> str:
    return escape("" if value is None else str(value))

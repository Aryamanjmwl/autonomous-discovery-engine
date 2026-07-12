"""Small self-contained HTML export for ADE JSON reports."""

from __future__ import annotations

import json
from html import escape
from pathlib import Path
from typing import Any


def write_html_report(report_path: Path | str, output_path: Path | str) -> Path:
    """Write a local HTML review artifact from an ADE JSON report."""

    source_path = Path(report_path)
    if not source_path.exists():
        raise FileNotFoundError(f"Report JSON does not exist: {source_path}")

    report = json.loads(source_path.read_text(encoding="utf-8"))
    if not isinstance(report, dict):
        raise ValueError("Report JSON root must be an object.")

    target_path = Path(output_path)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_text(render_html_report(report), encoding="utf-8")
    return target_path


def render_html_report(report: dict[str, Any]) -> str:
    """Render a concise static HTML report for local human review."""

    run_id = _text(report.get("run_id"))
    anomalies = (
        report.get("candidate_anomalies")
        if isinstance(report.get("candidate_anomalies"), list)
        else []
    )
    concepts = (
        report.get("candidate_unknown_concepts")
        if isinstance(report.get("candidate_unknown_concepts"), list)
        else []
    )
    anomaly_items = "\n".join(_anomaly_item(item) for item in anomalies if isinstance(item, dict))
    concept_items = "\n".join(_concept_item(item) for item in concepts if isinstance(item, dict))
    review_memory_section = _review_memory_section(report)
    feedback_section = _feedback_section(report)

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>ADE Local Review Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 2rem; line-height: 1.5; }}
    .card {{ border: 1px solid #ddd; border-radius: 8px; padding: 1rem; margin: 1rem 0; }}
    .muted {{ color: #555; }}
    code {{ background: #f4f4f4; padding: 0.1rem 0.25rem; }}
  </style>
</head>
<body>
  <h1>ADE Local Review Report</h1>
  <p class="muted">Run ID: <code>{run_id}</code></p>
  <p>All findings are candidate findings and require human review.</p>
  {review_memory_section}
  <h2>Candidate Anomalies</h2>
  {anomaly_items or "<p>No candidate anomalies reported.</p>"}
  <h2>Candidate Concepts</h2>
  {concept_items or "<p>No candidate concepts reported.</p>"}
  {feedback_section}
</body>
</html>
"""


def _anomaly_item(item: dict[str, Any]) -> str:
    anomaly_id = item.get("anomaly_id") or item.get("target_id") or item.get("id")
    score = item.get("novelty_score")
    source = item.get("source_path")
    return (
        '<section class="card">'
        f"<h3>{_text(anomaly_id)}</h3>"
        f"<p>Novelty score: {_text(score)}</p>"
        f"<p>Source: <code>{_text(source)}</code></p>"
        f"<p>Review memory: {_text(_signal_text(item.get('review_memory_signal')))}</p>"
        "</section>"
    )


def _concept_item(item: dict[str, Any]) -> str:
    concept_id = item.get("concept_id") or item.get("target_id") or item.get("id")
    count = item.get("example_count")
    return (
        '<section class="card">'
        f"<h3>{_text(concept_id)}</h3>"
        f"<p>Supporting examples: {_text(count)}</p>"
        f"<p>Review memory: {_text(_signal_text(item.get('review_memory_signal')))}</p>"
        "</section>"
    )


def _review_memory_section(report: dict[str, Any]) -> str:
    summary = report.get("review_memory_summary")
    if not isinstance(summary, dict):
        return """
  <h2>Review Memory</h2>
  <p>No review-memory summary is attached to this report.</p>
"""
    total = summary.get("total_feedback_count", 0)
    label_counts = summary.get("label_counts")
    labels = ""
    if isinstance(label_counts, dict) and label_counts:
        labels = "<ul>" + "".join(
            f"<li>{_text(label)}: {_text(count)}</li>"
            for label, count in sorted(label_counts.items())
        ) + "</ul>"
    else:
        labels = "<p>No feedback labels were available.</p>"
    return f"""
  <h2>Review Memory</h2>
  <p>Review-memory signals are feedback-informed ranking support, not automated truth.</p>
  <p>Feedback records available: {_text(total)}</p>
  {labels}
"""


def _feedback_section(report: dict[str, Any]) -> str:
    labels = report.get("supported_feedback_labels")
    if not isinstance(labels, list):
        labels = [
            "interesting",
            "known_pattern",
            "false_positive",
            "duplicate",
            "important",
            "not_useful",
            "needs_more_data",
        ]
    label_text = ", ".join(_text(label) for label in labels)
    anomaly_command = (
        "python -m ade.cli --add-feedback data/reports/demo_report.json "
        "--target-type anomaly --target-id <anomaly_id> --label interesting "
        '--notes "Local review note" --reviewer local'
    )
    concept_command = (
        "python -m ade.cli --add-feedback data/reports/demo_report.json "
        "--target-type concept --target-id <concept_id> --label known_pattern "
        '--notes "Known recurring pattern" --reviewer local'
    )
    return f"""
  <h2>Human Review Feedback</h2>
  <p>Feedback is local reviewer state for candidate findings that require human review.</p>
  <p>Supported labels: {label_text}</p>
  <pre><code>{_text(anomaly_command)}</code></pre>
  <pre><code>{_text(concept_command)}</code></pre>
"""


def _signal_text(value: object) -> str:
    if not isinstance(value, dict):
        return "no signal"
    matched = int(value.get("matched_feedback_count") or 0)
    if matched == 0:
        return "no matching feedback"
    delta = float(value.get("priority_delta") or 0.0)
    notes = value.get("notes")
    note_text = "; ".join(str(note) for note in notes) if isinstance(notes, list) else ""
    return f"delta {delta:+.2f}" + (f"; {note_text}" if note_text else "")


def _text(value: object) -> str:
    return escape("" if value is None else str(value))

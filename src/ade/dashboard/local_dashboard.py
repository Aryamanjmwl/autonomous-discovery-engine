"""Local static dashboard export for ADE artifacts."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from html import escape
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from ade.reporting.report_validator import validate_report_dict
from ade.reporting.run_index import load_run_index

DEFAULT_REPORTS_DIR = Path("data/reports")
DEFAULT_RUN_INDEX_PATH = Path("data/reports/runs/index.json")
DEFAULT_BENCHMARKS_DIR = Path("data/benchmarks")
DEFAULT_FEEDBACK_PATH = Path("data/feedback/feedback.jsonl")
DEFAULT_LOCAL_DASHBOARD_DIR = Path("data/dashboard")


@dataclass(frozen=True)
class LocalDashboardExportResult:
    """Summary of a local dashboard export."""

    output_dir: Path
    index_path: Path
    data_path: Path
    run_count: int
    report_count: int
    benchmark_count: int
    feedback_count: int


def collect_dashboard_data(
    *,
    run_index_path: Path = DEFAULT_RUN_INDEX_PATH,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    benchmarks_dir: Path = DEFAULT_BENCHMARKS_DIR,
    feedback_path: Path = DEFAULT_FEEDBACK_PATH,
) -> dict[str, Any]:
    """Collect local ADE artifacts for a static dashboard export."""

    runs = _collect_runs(run_index_path)
    reports = _collect_reports(reports_dir)
    benchmarks = _collect_benchmarks(benchmarks_dir)
    feedback_records = _collect_feedback(feedback_path)
    feedback_labels = Counter(str(item.get("label", "")) for item in feedback_records)
    feedback_labels.pop("", None)

    run_anomaly_total = sum(
        _int(run.get("number_of_candidate_anomalies")) for run in runs
    )
    run_concept_total = sum(
        _int(run.get("number_of_candidate_unknown_concepts")) for run in runs
    )
    report_anomaly_total = sum(
        _int(report.get("candidate_anomaly_count")) for report in reports
    )
    report_concept_total = sum(
        _int(report.get("candidate_concept_count")) for report in reports
    )
    latest_run_timestamp = _latest_timestamp(
        [str(run.get("generated_at", "")) for run in runs]
    )
    latest_report_timestamp = _latest_timestamp(
        [str(report.get("generated_at", "")) for report in reports]
    )
    summary = {
        "total_runs": len(runs),
        "total_candidate_anomalies": run_anomaly_total or report_anomaly_total,
        "total_candidate_concepts": run_concept_total or report_concept_total,
        "latest_run_timestamp": latest_run_timestamp or latest_report_timestamp,
        "benchmark_count": len(benchmarks),
        "feedback_count": len(feedback_records),
    }

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "source_paths": {
            "run_index_path": run_index_path.as_posix(),
            "reports_dir": reports_dir.as_posix(),
            "benchmarks_dir": benchmarks_dir.as_posix(),
            "feedback_path": feedback_path.as_posix(),
        },
        "summary": summary,
        "runs": runs,
        "reports": reports,
        "benchmarks": benchmarks,
        "feedback": {
            "total_feedback_records": len(feedback_records),
            "label_counts": dict(sorted(feedback_labels.items())),
            "recent_records": feedback_records[-10:],
        },
        "limitations": [
            "Local static export only.",
            "Not hosted and does not start a server.",
            "No authentication, user accounts, database, billing, or cloud workflow.",
            "No production audit system.",
            "Findings are candidate findings and require human review.",
        ],
    }


def render_dashboard_html(data: dict[str, Any]) -> str:
    """Render a self-contained dark local dashboard HTML document."""

    summary = _dict(data.get("summary"))
    runs = _list(data.get("runs"))
    reports = _list(data.get("reports"))
    benchmarks = _list(data.get("benchmarks"))
    feedback = _dict(data.get("feedback"))
    limitations = _list(data.get("limitations"))

    return "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "<meta charset=\"utf-8\">",
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            "<title>ADE Local Dashboard</title>",
            "<style>",
            _dashboard_css(),
            "</style>",
            "</head>",
            "<body>",
            "<header>",
            "<p class=\"eyebrow\">Technical Preview demo viewer</p>",
            "<h1>ADE Local Dashboard</h1>",
            "<p class=\"notice\">Local static export for existing ADE artifacts. "
            "Candidate findings require human review.</p>",
            "</header>",
            "<main>",
            _summary_cards(summary),
            _runs_section(runs),
            _reports_section(reports),
            _benchmarks_section(benchmarks),
            _feedback_section(feedback),
            _limitations_section(limitations),
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def export_local_dashboard(
    *,
    output_dir: Path = DEFAULT_LOCAL_DASHBOARD_DIR,
    run_index_path: Path = DEFAULT_RUN_INDEX_PATH,
    reports_dir: Path = DEFAULT_REPORTS_DIR,
    benchmarks_dir: Path = DEFAULT_BENCHMARKS_DIR,
    feedback_path: Path = DEFAULT_FEEDBACK_PATH,
) -> LocalDashboardExportResult:
    """Write local dashboard HTML and JSON data files."""

    output_dir.mkdir(parents=True, exist_ok=True)
    data = collect_dashboard_data(
        run_index_path=run_index_path,
        reports_dir=reports_dir,
        benchmarks_dir=benchmarks_dir,
        feedback_path=feedback_path,
    )
    index_path = output_dir / "index.html"
    data_path = output_dir / "dashboard_data.json"
    index_path.write_text(render_dashboard_html(data), encoding="utf-8")
    data_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    summary = _dict(data["summary"])
    return LocalDashboardExportResult(
        output_dir=output_dir,
        index_path=index_path,
        data_path=data_path,
        run_count=_int(summary.get("total_runs")),
        report_count=len(_list(data.get("reports"))),
        benchmark_count=len(_list(data.get("benchmarks"))),
        feedback_count=_int(summary.get("feedback_count")),
    )


def _collect_runs(run_index_path: Path) -> list[dict[str, Any]]:
    run_index = load_run_index(run_index_path)
    if run_index is None:
        return []
    runs = [run for run in run_index.get("runs", []) if isinstance(run, dict)]
    return [
        {
            "run_id": run.get("run_id"),
            "generated_at": run.get("generated_at"),
            "input_path": run.get("input_path"),
            "modality": run.get("modality"),
            "markdown_report_path": run.get("markdown_report_path"),
            "json_report_path": run.get("json_report_path"),
            "number_of_candidate_anomalies": run.get("number_of_candidate_anomalies"),
            "number_of_candidate_unknown_concepts": run.get(
                "number_of_candidate_unknown_concepts"
            ),
            "human_review_required": run.get("human_review_required"),
        }
        for run in reversed(runs)
    ]


def _collect_reports(reports_dir: Path) -> list[dict[str, Any]]:
    if not reports_dir.exists() or not reports_dir.is_dir():
        return []
    html_reports = {
        path.with_suffix(".json").name: path.as_posix()
        for path in sorted(reports_dir.glob("*.html"))
    }
    reports: list[dict[str, Any]] = []
    for path in sorted(reports_dir.glob("*.json")):
        loaded, error = _read_json(path)
        report: dict[str, Any] = {
            "filename": path.name,
            "path": path.as_posix(),
            "html_report_path": html_reports.get(path.name),
            "validation_status": "invalid",
            "validation_errors": [],
        }
        if isinstance(loaded, dict):
            validation = validate_report_dict(loaded)
            report.update(
                {
                    "report_version": loaded.get("report_version"),
                    "schema_version": loaded.get("schema_version"),
                    "modality": loaded.get("modality") or _infer_modality(loaded),
                    "run_id": loaded.get("run_id"),
                    "generated_at": loaded.get("generated_at"),
                    "number_of_candidate_anomalies": loaded.get(
                        "number_of_candidate_anomalies"
                    ),
                    "number_of_candidate_unknown_concepts": loaded.get(
                        "number_of_candidate_unknown_concepts"
                    ),
                    "human_review_required": loaded.get("human_review_required"),
                    "validation_status": "valid" if validation.is_valid else "invalid",
                    "validation_errors": validation.errors,
                    "validation_warnings": validation.warnings,
                }
            )
        else:
            report["validation_errors"] = [error or "Report JSON could not be read."]
        reports.append(report)
    return reports


def _collect_benchmarks(benchmarks_dir: Path) -> list[dict[str, Any]]:
    if not benchmarks_dir.exists() or not benchmarks_dir.is_dir():
        return []
    benchmarks: list[dict[str, Any]] = []
    for path in sorted(benchmarks_dir.glob("*.json")):
        loaded, error = _read_json(path)
        if not isinstance(loaded, dict):
            benchmarks.append(
                {
                    "filename": path.name,
                    "path": path.as_posix(),
                    "error": error or "Benchmark JSON could not be read.",
                }
            )
            continue
        benchmarks.append(
            {
                "filename": path.name,
                "path": path.as_posix(),
                "benchmark_id": loaded.get("benchmark_id"),
                "generated_at": loaded.get("generated_at"),
                "duration_seconds": loaded.get("duration_seconds"),
                "report_valid": loaded.get("report_valid"),
                "input_path": loaded.get("input_path"),
                "config_path": loaded.get("config_path"),
            }
        )
    return benchmarks


def _collect_feedback(feedback_path: Path) -> list[dict[str, Any]]:
    if not feedback_path.exists() or not feedback_path.is_file():
        return []
    records: list[dict[str, Any]] = []
    with feedback_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                loaded = json.loads(stripped)
            except JSONDecodeError:
                records.append(
                    {
                        "target_type": "invalid",
                        "target_id": f"{feedback_path}:{line_number}",
                        "label": "malformed_feedback",
                        "reviewer": "unknown",
                        "created_at": None,
                    }
                )
                continue
            if isinstance(loaded, dict):
                records.append(
                    {
                        "feedback_id": loaded.get("feedback_id"),
                        "run_id": loaded.get("run_id"),
                        "target_type": loaded.get("target_type"),
                        "target_id": loaded.get("target_id"),
                        "label": loaded.get("label"),
                        "reviewer": loaded.get("reviewer"),
                        "created_at": loaded.get("created_at"),
                    }
                )
    records.sort(key=lambda item: str(item.get("created_at") or ""))
    return records


def _read_json(path: Path) -> tuple[dict[str, Any] | None, str | None]:
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError as error:
        return None, f"Malformed JSON: {error.msg}"
    except OSError as error:
        return None, str(error)
    if not isinstance(loaded, dict):
        return None, "JSON root is not an object."
    return loaded, None


def _summary_cards(summary: dict[str, Any]) -> str:
    cards = [
        ("Total runs", summary.get("total_runs")),
        ("Candidate anomalies", summary.get("total_candidate_anomalies")),
        ("Candidate concepts", summary.get("total_candidate_concepts")),
        ("Latest run", summary.get("latest_run_timestamp") or "Not available"),
        ("Benchmarks", summary.get("benchmark_count")),
        ("Feedback records", summary.get("feedback_count")),
    ]
    return "<section class=\"cards\">" + "".join(
        f"<article><span>{escape(label)}</span><strong>{escape(_string(value))}</strong></article>"
        for label, value in cards
    ) + "</section>"


def _runs_section(runs: list[Any]) -> str:
    headers = [
        "run_id",
        "generated_at",
        "input_path",
        "modality",
        "markdown_report_path",
        "json_report_path",
        "number_of_candidate_anomalies",
        "number_of_candidate_unknown_concepts",
        "human_review_required",
    ]
    return _section("Recent Runs", _table(headers, runs, empty="No run history found."))


def _reports_section(reports: list[Any]) -> str:
    headers = [
        "filename",
        "report_version",
        "modality",
        "number_of_candidate_anomalies",
        "number_of_candidate_unknown_concepts",
        "validation_status",
        "html_report_path",
    ]
    return _section("Reports", _table(headers, reports, empty="No report JSON files found."))


def _benchmarks_section(benchmarks: list[Any]) -> str:
    headers = [
        "benchmark_id",
        "generated_at",
        "duration_seconds",
        "report_valid",
        "input_path",
        "config_path",
    ]
    return _section("Benchmarks", _table(headers, benchmarks, empty="No benchmarks found."))


def _feedback_section(feedback: dict[str, Any]) -> str:
    label_counts = _dict(feedback.get("label_counts"))
    recent = _list(feedback.get("recent_records"))
    label_list = (
        "<ul>"
        + "".join(
            f"<li><code>{escape(label)}</code>: {escape(_string(count))}</li>"
            for label, count in sorted(label_counts.items())
        )
        + "</ul>"
        if label_counts
        else "<p>No feedback labels found.</p>"
    )
    headers = ["target_type", "target_id", "label", "reviewer", "created_at"]
    return _section(
        "Feedback",
        f"<p>Total feedback records: {escape(_string(feedback.get('total_feedback_records', 0)))}</p>"
        "<h3>Labels</h3>"
        f"{label_list}"
        "<h3>Recent Feedback</h3>"
        f"{_table(headers, recent, empty='No feedback records found.')}",
    )


def _limitations_section(limitations: list[Any]) -> str:
    items = "".join(f"<li>{escape(_string(item))}</li>" for item in limitations)
    return _section("Limitations", f"<ul>{items}</ul>")


def _section(title: str, body: str) -> str:
    return f"<section><h2>{escape(title)}</h2>{body}</section>"


def _table(headers: list[str], rows: list[Any], *, empty: str) -> str:
    dict_rows = [row for row in rows if isinstance(row, dict)]
    if not dict_rows:
        return f"<p>{escape(empty)}</p>"
    header_html = "".join(f"<th>{escape(_label(header))}</th>" for header in headers)
    row_html = []
    for row in dict_rows:
        cells = "".join(f"<td>{_cell(row.get(header))}</td>" for header in headers)
        row_html.append(f"<tr>{cells}</tr>")
    return (
        "<div class=\"table-wrap\"><table>"
        f"<thead><tr>{header_html}</tr></thead>"
        f"<tbody>{''.join(row_html)}</tbody>"
        "</table></div>"
    )


def _cell(value: object) -> str:
    if isinstance(value, str) and (value.endswith(".html") or value.endswith(".json")):
        safe = escape(value)
        return f"<code>{safe}</code>"
    return escape(_string(value))


def _dashboard_css() -> str:
    return """
:root { color-scheme: dark; font-family: Arial, sans-serif; background: #0f141b; color: #e6edf3; }
body { margin: 0; background: #0f141b; }
header { padding: 28px 32px; border-bottom: 1px solid #263241; background: #121923; }
main { max-width: 1280px; margin: 0 auto; padding: 24px; }
h1 { margin: 0 0 8px; font-size: 32px; }
h2 { margin-top: 0; }
h3 { color: #b8c7d9; }
.eyebrow { margin: 0 0 8px; color: #8fb7ff; text-transform: uppercase; font-size: 12px; letter-spacing: 0; }
.notice { margin: 0; color: #b8c7d9; }
section { background: #151e2a; border: 1px solid #263241; border-radius: 8px; padding: 18px; margin-bottom: 18px; }
.cards { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 12px; background: transparent; border: 0; padding: 0; }
.cards article { background: #151e2a; border: 1px solid #263241; border-radius: 8px; padding: 16px; }
.cards span { display: block; color: #9fb0c3; font-size: 13px; margin-bottom: 8px; }
.cards strong { display: block; font-size: 22px; overflow-wrap: anywhere; }
.table-wrap { overflow-x: auto; }
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th, td { border-bottom: 1px solid #263241; padding: 10px; text-align: left; vertical-align: top; }
th { color: #b8c7d9; background: #101721; }
td { color: #e6edf3; }
code { color: #d6e4ff; background: #0f141b; padding: 2px 4px; border-radius: 4px; }
ul { margin-bottom: 0; }
""".strip()


def _infer_modality(report: dict[str, Any]) -> str:
    if "timeseries_profile" in report:
        return "timeseries"
    if "tabular_profile" in report:
        return "tabular"
    return "image"


def _latest_timestamp(values: list[str]) -> str | None:
    present = sorted(value for value in values if value)
    return present[-1] if present else None


def _dict(value: object) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: object) -> list[Any]:
    return value if isinstance(value, list) else []


def _int(value: object) -> int:
    try:
        return int(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0


def _string(value: object) -> str:
    if value is None:
        return "Not available"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _label(value: str) -> str:
    return value.replace("_", " ").strip().capitalize()

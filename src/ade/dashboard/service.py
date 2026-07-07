"""Generate a small static dashboard from ADE run history."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from html import escape
from json import JSONDecodeError
from pathlib import Path
from typing import Any

from ade.reporting.run_index import load_run_index

DEFAULT_DASHBOARD_DIR = Path("data/reports/dashboard")
DEFAULT_RUN_INDEX_PATH = Path("data/reports/runs/index.json")


@dataclass(frozen=True)
class DashboardBuildResult:
    """Summary of a generated dashboard."""

    output_dir: Path
    index_path: Path
    runs_path: Path
    run_count: int


@dataclass(frozen=True)
class DashboardRun:
    """Normalized run data used by dashboard rendering."""

    summary: dict[str, Any]
    report: dict[str, Any] | None = None
    report_error: str | None = None
    detail_path: Path | None = None
    detail_href: str | None = None

    @property
    def run_id(self) -> str:
        """Return the run identifier."""

        return str(self.summary.get("run_id", "unknown-run"))


def generate_dashboard(
    index_path: Path = DEFAULT_RUN_INDEX_PATH,
    output_dir: Path = DEFAULT_DASHBOARD_DIR,
) -> DashboardBuildResult:
    """Generate static dashboard HTML from the ADE run history index."""

    output_dir.mkdir(parents=True, exist_ok=True)
    runs_dir = output_dir / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)

    runs = load_dashboard_runs(index_path=index_path, output_dir=output_dir)
    index_file = output_dir / "index.html"
    runs_file = output_dir / "runs.html"

    index_file.write_text(_render_home(runs), encoding="utf-8")
    runs_file.write_text(_render_runs(runs), encoding="utf-8")

    for run in runs:
        if run.detail_path is None:
            continue
        run.detail_path.write_text(_render_run_detail(run), encoding="utf-8")

    return DashboardBuildResult(
        output_dir=output_dir,
        index_path=index_file,
        runs_path=runs_file,
        run_count=len(runs),
    )


def load_dashboard_runs(
    index_path: Path = DEFAULT_RUN_INDEX_PATH,
    output_dir: Path = DEFAULT_DASHBOARD_DIR,
) -> list[DashboardRun]:
    """Load normalized run summaries and optional report JSON for the dashboard."""

    run_index = load_run_index(index_path)
    if run_index is None:
        return []

    runs = [run for run in run_index.get("runs", []) if isinstance(run, dict)]
    normalized: list[DashboardRun] = []
    for run in reversed(runs):
        run_id = str(run.get("run_id", "unknown-run"))
        detail_path = output_dir / "runs" / f"{_slugify(run_id)}.html"
        report_path = _path_from_value(run.get("json_report_path"))
        report, error = _load_report(report_path)
        normalized.append(
            DashboardRun(
                summary=run,
                report=report,
                report_error=error,
                detail_path=detail_path,
                detail_href=f"runs/{detail_path.name}",
            )
        )
    return normalized


def _load_report(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    """Load one report JSON file if it is available and valid."""

    if path is None:
        return None, "No JSON report path is recorded for this run."
    if not path.exists():
        return None, f"JSON report file was not found: {path}"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except JSONDecodeError:
        return None, f"JSON report file is malformed: {path}"
    except OSError as error:
        return None, f"JSON report file could not be read: {error}"
    if not isinstance(data, dict):
        return None, f"JSON report file does not contain an object: {path}"
    return data, None


def _render_home(runs: list[DashboardRun]) -> str:
    """Render the dashboard landing page."""

    latest = runs[0] if runs else None
    latest_line = (
        f"Latest run: <a href=\"{escape(latest.detail_href or '#')}\">"
        f"{escape(latest.run_id)}</a>"
        if latest
        else "No ADE runs found yet."
    )
    return _page(
        title="ADE Dashboard",
        active="home",
        root_prefix="",
        body=[
            "<section>",
            "<h1>ADE Local Dashboard</h1>",
            "<p>Review local ADE run history, candidate findings, evidence, and report artifacts.</p>",
            f"<p>{latest_line}</p>",
            "<p><a class=\"button\" href=\"runs.html\">Browse runs</a></p>",
            "</section>",
            "<section>",
            "<h2>Local Use Note</h2>",
            "<p>This dashboard reads existing files from the local report directory. "
            "It does not upload data, create user accounts, or run a hosted service.</p>",
            "</section>",
        ],
    )


def _render_runs(runs: list[DashboardRun]) -> str:
    """Render the run list page."""

    if not runs:
        table = "<p>No ADE runs found yet. Run an analysis before generating the dashboard.</p>"
    else:
        rows = []
        for run in runs:
            summary = run.summary
            rows.append(
                "<tr>"
                f"<td><a href=\"{escape(run.detail_href or '#')}\">{escape(run.run_id)}</a></td>"
                f"<td>{escape(_string(summary.get('generated_at')))}</td>"
                f"<td>{escape(_string(summary.get('input_path')))}</td>"
                f"<td>{escape(_string(summary.get('number_of_candidate_anomalies')))}</td>"
                f"<td>{escape(_string(summary.get('number_of_candidate_unknown_concepts')))}</td>"
                f"<td>{escape(_status_for_run(run))}</td>"
                "</tr>"
            )
        table = (
            "<table>"
            "<thead><tr><th>Run ID</th><th>Timestamp</th><th>Dataset</th>"
            "<th>Findings</th><th>Concepts</th><th>Status</th></tr></thead>"
            f"<tbody>{''.join(rows)}</tbody>"
            "</table>"
        )
    return _page(
        title="ADE Runs",
        active="runs",
        root_prefix="",
        body=["<section>", "<h1>ADE Runs</h1>", table, "</section>"],
    )


def _render_run_detail(run: DashboardRun) -> str:
    """Render one run detail page."""

    summary = run.summary
    report = run.report or {}
    sections = [
        "<section>",
        f"<h1>{escape(run.run_id)}</h1>",
        _metadata_list(
            {
                "Generated at": summary.get("generated_at"),
                "Dataset": summary.get("input_path"),
                "Markdown report": summary.get("markdown_report_path"),
                "JSON report": summary.get("json_report_path"),
                "Candidate anomalies": summary.get("number_of_candidate_anomalies"),
                "Candidate concepts": summary.get("number_of_candidate_unknown_concepts"),
                "Human review required": summary.get("human_review_required"),
            }
        ),
        "</section>",
    ]
    if run.report_error:
        sections.extend(
            [
                "<section>",
                "<h2>Report Data</h2>",
                f"<p class=\"warning\">{escape(run.report_error)}</p>",
                "</section>",
            ]
        )
    else:
        sections.extend(
            [
                _dataset_section(report),
                _backend_section(report),
                _findings_section(report, run),
                _concepts_section(report, run),
                _limitations_section(report),
            ]
        )
    return _page(
        title=f"ADE Run {run.run_id}",
        active="runs",
        root_prefix="../",
        body=sections,
    )


def _dataset_section(report: dict[str, Any]) -> str:
    """Render dataset summary and profile information."""

    input_summary = _dict(report.get("input_summary"))
    profile = _dict(report.get("dataset_profile"))
    if report.get("modality") == "tabular" or profile.get("modality") == "tabular":
        rows = {
            "Input path": input_summary.get("input_path") or input_summary.get("input_dir"),
            "Modality": "tabular",
            "Rows": input_summary.get("row_count") or report.get("number_of_rows"),
            "Columns": input_summary.get("column_count") or report.get("number_of_columns"),
            "Numeric columns": input_summary.get("numeric_column_count"),
            "Categorical columns": input_summary.get("categorical_column_count"),
            "Input type": profile.get("input_type"),
        }
    else:
        rows = {
            "Input directory": input_summary.get("input_dir"),
            "Images": report.get("number_of_images"),
            "Patches": report.get("number_of_patches"),
            "Input type": profile.get("input_type"),
            "Valid images": profile.get("valid_images"),
            "Unsupported files": profile.get("unsupported_file_count"),
            "Unreadable files": profile.get("unreadable_file_count"),
            "Estimated patches": profile.get("estimated_patch_count"),
        }
    warnings = profile.get("warnings")
    warning_html = _list_items(warnings) if isinstance(warnings, list) and warnings else "<p>None.</p>"
    return (
        "<section>"
        "<h2>Dataset Summary</h2>"
        f"{_metadata_list(rows)}"
        "<h3>Input Warnings</h3>"
        f"{warning_html}"
        "</section>"
    )


def _backend_section(report: dict[str, Any]) -> str:
    """Render backend and scoring metadata."""

    backend = _dict(report.get("backend_metadata"))
    return (
        "<section>"
        "<h2>Discovery Configuration</h2>"
        f"{_metadata_list(backend or {'Backend metadata': 'Not available'})}"
        "</section>"
    )


def _findings_section(report: dict[str, Any], run: DashboardRun) -> str:
    """Render candidate anomalies and evidence previews."""

    candidates = report.get("candidate_anomalies")
    if not isinstance(candidates, list) or not candidates:
        return (
            "<section><h2>Top Findings</h2>"
            "<p>No candidate anomalies are recorded in the JSON report.</p></section>"
        )

    rows = []
    for candidate in candidates[:20]:
        if not isinstance(candidate, dict):
            continue
        preview = _preview_image(candidate.get("preview_path"), run)
        rows.append(
            "<tr>"
            f"<td>{escape(_string(candidate.get('rank')))}</td>"
            f"<td>{preview}</td>"
            f"<td>{escape(_candidate_item_label(candidate))}</td>"
            f"<td>{escape(_string(candidate.get('novelty_score')))}</td>"
            f"<td>{escape(_string(candidate.get('reason')))}</td>"
            f"<td>{escape(_string(candidate.get('nearest_neighbor_id')))}</td>"
            "</tr>"
        )
    return (
        "<section>"
        "<h2>Top Findings</h2>"
        "<table>"
        "<thead><tr><th>Rank</th><th>Preview</th><th>Item</th><th>Score</th>"
        "<th>Reason</th><th>Nearest neighbor</th></tr></thead>"
        f"<tbody>{''.join(rows)}</tbody>"
        "</table>"
        "</section>"
    )


def _concepts_section(report: dict[str, Any], run: DashboardRun) -> str:
    """Render candidate concept groups."""

    concepts = report.get("candidate_unknown_concepts")
    if not isinstance(concepts, list) or not concepts:
        return (
            "<section><h2>Concept Groups</h2>"
            "<p>No candidate unknown concepts are recorded in the JSON report.</p></section>"
        )

    blocks = []
    for concept in concepts:
        if not isinstance(concept, dict):
            continue
        examples = concept.get("examples")
        example_items = []
        if isinstance(examples, list):
            for example in examples[:8]:
                if not isinstance(example, dict):
                    continue
                example_items.append(
                    "<li>"
                    f"{_preview_image(example.get('preview_path'), run)}"
                    f"<span>{escape(_string(example.get('source_path')))} "
                    f"score={escape(_string(example.get('novelty_score')))} "
                    f"rank={escape(_string(example.get('rank')))}</span>"
                    "</li>"
                )
        concept_metadata = {
            "Example count": concept.get("example_count"),
            "Average novelty": concept.get("average_novelty"),
            "Confidence score": concept.get("confidence_score"),
            "Representative anomaly": concept.get("representative_anomaly_id"),
            "Summary": concept.get("summary"),
            "Possible pattern": concept.get("possible_pattern"),
        }
        concept_metadata_html = _metadata_list(concept_metadata)
        evidence_html = "".join(example_items) or "<li>No examples recorded.</li>"
        blocks.append(
            "<article class=\"concept\">"
            f"<h3>{escape(_string(concept.get('concept_id')))}</h3>"
            f"{concept_metadata_html}"
            f"<ul class=\"evidence-list\">{evidence_html}</ul>"
            "</article>"
        )
    return "<section><h2>Concept Groups</h2>" + "".join(blocks) + "</section>"


def _limitations_section(report: dict[str, Any]) -> str:
    """Render limitations and reproducibility notes."""

    limitations = report.get("limitations")
    limitation_html = (
        _list_items(limitations)
        if isinstance(limitations, list) and limitations
        else "<p>All results are candidate findings and require human review.</p>"
    )
    run_metadata = _dict(report.get("run_metadata"))
    return (
        "<section>"
        "<h2>Limitations and Reproducibility</h2>"
        f"{limitation_html}"
        "<h3>Run Metadata</h3>"
        f"{_metadata_list(run_metadata or {'Run metadata': 'Not available'})}"
        "</section>"
    )


def _page(title: str, active: str, root_prefix: str, body: list[str]) -> str:
    """Wrap page body in a minimal dashboard shell."""

    home_class = "active" if active == "home" else ""
    runs_class = "active" if active == "runs" else ""
    return "\n".join(
        [
            "<!doctype html>",
            "<html lang=\"en\">",
            "<head>",
            "<meta charset=\"utf-8\">",
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">",
            f"<title>{escape(title)}</title>",
            "<style>",
            _css(),
            "</style>",
            "</head>",
            "<body>",
            "<header>",
            "<strong>ADE</strong>",
            "<nav>",
            f"<a class=\"{home_class}\" href=\"{root_prefix}index.html\">Home</a>",
            f"<a class=\"{runs_class}\" href=\"{root_prefix}runs.html\">Runs</a>",
            "</nav>",
            "</header>",
            "<main>",
            *body,
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def _css() -> str:
    """Return compact dashboard CSS."""

    return """
:root { color-scheme: light; font-family: Arial, sans-serif; color: #202124; }
body { margin: 0; background: #f7f8fa; }
header { display: flex; justify-content: space-between; align-items: center; padding: 14px 24px; background: #fff; border-bottom: 1px solid #d9dde3; }
nav a { color: #344054; margin-left: 14px; text-decoration: none; }
nav a.active { color: #0b5cab; font-weight: 700; }
main { max-width: 1180px; margin: 0 auto; padding: 24px; }
section, article.concept { background: #fff; border: 1px solid #d9dde3; border-radius: 6px; margin-bottom: 18px; padding: 18px; }
h1, h2, h3 { margin-top: 0; }
table { width: 100%; border-collapse: collapse; font-size: 14px; }
th, td { border-bottom: 1px solid #e6e8ec; padding: 10px; text-align: left; vertical-align: top; }
th { background: #f2f4f7; font-weight: 700; }
.button { display: inline-block; padding: 8px 12px; border: 1px solid #0b5cab; border-radius: 4px; color: #0b5cab; text-decoration: none; }
.warning { color: #8a4b00; background: #fff8e6; border: 1px solid #f0d28a; padding: 10px; border-radius: 4px; }
.meta { display: grid; grid-template-columns: minmax(160px, 240px) 1fr; gap: 8px 14px; }
.meta dt { font-weight: 700; color: #475467; }
.meta dd { margin: 0; overflow-wrap: anywhere; }
.preview { max-width: 96px; max-height: 96px; border: 1px solid #d9dde3; background: #f7f8fa; }
.evidence-list { list-style: none; padding-left: 0; }
.evidence-list li { display: flex; gap: 12px; align-items: center; margin-bottom: 10px; }
""".strip()


def _metadata_list(data: dict[str, Any]) -> str:
    """Render key-value metadata as a definition list."""

    items = []
    for key, value in data.items():
        items.append(f"<dt>{escape(_label(key))}</dt><dd>{escape(_string(value))}</dd>")
    return f"<dl class=\"meta\">{''.join(items)}</dl>"


def _list_items(items: list[Any]) -> str:
    """Render a simple list."""

    return "<ul>" + "".join(f"<li>{escape(_string(item))}</li>" for item in items) + "</ul>"


def _preview_image(preview_path: object, run: DashboardRun) -> str:
    """Render an image preview when the referenced asset is available."""

    asset_path = _asset_path(preview_path, run)
    if asset_path is None:
        return "preview unavailable"
    return f"<img class=\"preview\" src=\"{escape(asset_path)}\" alt=\"candidate evidence preview\">"


def _asset_path(preview_path: object, run: DashboardRun) -> str | None:
    """Return a detail-page-relative asset path for a report preview."""

    if not isinstance(preview_path, str) or not preview_path:
        return None
    report_path = _path_from_value(run.summary.get("json_report_path"))
    if report_path is None or run.detail_path is None:
        return None
    asset_path = report_path.parent / preview_path
    if not asset_path.exists():
        return None
    return _relative_path(asset_path, run.detail_path.parent)


def _relative_path(path: Path, start: Path) -> str:
    """Return a POSIX-style relative path for local HTML links."""

    try:
        return path.resolve().relative_to(start.resolve()).as_posix()
    except ValueError:
        import os

        return Path(os.path.relpath(path.resolve(), start.resolve())).as_posix()


def _path_from_value(value: object) -> Path | None:
    """Return a Path from a string-like value."""

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return Path(text)


def _dict(value: object) -> dict[str, Any]:
    """Return a dictionary or an empty dictionary."""

    return value if isinstance(value, dict) else {}


def _string(value: object) -> str:
    """Return a display string for dashboard values."""

    if value is None:
        return "Not available"
    if isinstance(value, float):
        return f"{value:.4f}"
    return str(value)


def _label(value: object) -> str:
    """Return a human-readable metadata label."""

    return str(value).replace("_", " ").strip().capitalize()


def _status_for_run(run: DashboardRun) -> str:
    """Return a compact status label for a dashboard run."""

    if run.report_error:
        return "report unavailable"
    return "report available"


def _candidate_item_label(candidate: dict[str, Any]) -> str:
    """Return a concise item label for visual or tabular findings."""

    if candidate.get("row_index") is not None:
        return f"{_string(candidate.get('source_path'))} row {_string(candidate.get('row_index'))}"
    return _string(candidate.get("source_path"))


def _slugify(value: str) -> str:
    """Return a filesystem-safe slug."""

    keep = [character if character.isalnum() or character in {"-", "_"} else "_" for character in value]
    slug = "".join(keep).strip("._")
    return slug or "run"

"""Run history index helpers for ADE reports."""

from __future__ import annotations

from datetime import UTC, datetime
import json
from pathlib import Path


INDEX_VERSION = "1.0"


def build_run_summary(
    run_metadata: dict[str, object],
    run_metadata_path: Path,
) -> dict[str, object]:
    """Return a compact run summary for the run history index."""

    return {
        "run_id": str(run_metadata["run_id"]),
        "generated_at": str(run_metadata["generated_at"]),
        "input_path": str(run_metadata["input_path"]),
        "markdown_report_path": str(run_metadata["markdown_report_path"]),
        "json_report_path": str(run_metadata["json_report_path"]),
        "run_metadata_path": run_metadata_path.as_posix(),
        "number_of_images": int(run_metadata["number_of_images"]),
        "number_of_patches": int(run_metadata["number_of_patches"]),
        "number_of_candidate_anomalies": int(
            run_metadata["number_of_candidate_anomalies"]
        ),
        "number_of_candidate_unknown_concepts": int(
            run_metadata["number_of_candidate_unknown_concepts"]
        ),
        "human_review_required": bool(run_metadata["human_review_required"]),
    }


def update_run_index(
    index_path: Path,
    run_summary: dict[str, object],
    updated_at: datetime | None = None,
) -> Path:
    """Create or update the run history index with one run summary."""

    index = _load_run_index(index_path)
    run_id = run_summary["run_id"]
    existing_runs = [
        run
        for run in index["runs"]
        if isinstance(run, dict) and run.get("run_id") != run_id
    ]
    existing_runs.append(run_summary)

    index["index_version"] = INDEX_VERSION
    index["updated_at"] = (updated_at or datetime.now(UTC)).isoformat()
    index["runs"] = existing_runs

    index_path.parent.mkdir(parents=True, exist_ok=True)
    index_path.write_text(
        json.dumps(index, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return index_path


def load_run_index(index_path: Path) -> dict[str, object] | None:
    """Load a run index if it exists."""

    if not index_path.exists():
        return None
    return _load_run_index(index_path)


def _load_run_index(index_path: Path) -> dict[str, object]:
    """Load an existing run index or return an empty index."""

    if not index_path.exists():
        return {"index_version": INDEX_VERSION, "updated_at": None, "runs": []}

    data = json.loads(index_path.read_text(encoding="utf-8"))
    runs = data.get("runs", [])
    if not isinstance(runs, list):
        runs = []

    return {
        "index_version": str(data.get("index_version", INDEX_VERSION)),
        "updated_at": data.get("updated_at"),
        "runs": runs,
    }

"""Tests for the ADE Studio local backend service."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ade.cli import run_temporal_pipeline
from ade.studio.service import (
    StudioPaths,
    build_summary,
    health_status,
    list_reports,
    list_runs,
    load_report,
    resolve_report_html,
    run_visual_analysis,
)
from ade.visual import (
    VISUAL_ENGINE_SCHEMA_VERSION,
    TemporalObservation,
    TemporalObservationSequence,
    serialize_temporal_manifest,
)


def test_studio_health_status_is_local_technical_preview() -> None:
    health = health_status()

    assert health["status"] == "ok"
    assert health["mode"] == "local-only"
    assert health["label"] == "Technical Preview"
    assert health["human_review_required"] is True


def test_studio_fastapi_health_endpoint_when_dependency_available() -> None:
    fastapi = pytest.importorskip("fastapi")
    del fastapi
    from fastapi.testclient import TestClient

    from ade.studio.api import create_app

    client = TestClient(create_app())
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["mode"] == "local-only"


def test_studio_analysis_request_rejects_unsupported_and_extra_fields() -> None:
    fastapi = pytest.importorskip("fastapi")
    del fastapi
    from fastapi.testclient import TestClient

    from ade.studio.api import create_app

    client = TestClient(create_app())

    unsupported = client.post(
        "/api/studio/analysis",
        json={"input_path": "data/raw/demo_images", "workflow": "tabular"},
    )
    extra = client.post(
        "/api/studio/analysis",
        json={"input_path": "data/raw/demo_images", "unexpected": True},
    )

    assert unsupported.status_code == 422
    assert extra.status_code == 422


def test_studio_analysis_request_rejects_blank_and_null_byte_paths() -> None:
    fastapi = pytest.importorskip("fastapi")
    del fastapi
    from fastapi.testclient import TestClient

    from ade.studio.api import create_app

    client = TestClient(create_app())

    assert client.post("/api/studio/analysis", json={"input_path": "   "}).status_code == 422
    null_byte = client.post(
        "/api/studio/analysis",
        json={"input_path": "bad\x00path"},
    )
    assert null_byte.status_code == 422


def test_studio_run_limit_is_bounded(tmp_path: Path) -> None:
    paths = StudioPaths(run_index_path=tmp_path / "missing.json")

    with pytest.raises(ValueError, match="between 1 and 100"):
        list_runs(paths=paths, limit=0)
    with pytest.raises(ValueError, match="between 1 and 100"):
        list_runs(paths=paths, limit=101)


def test_studio_summary_tolerates_missing_artifact_folders(tmp_path: Path) -> None:
    paths = StudioPaths(
        reports_dir=tmp_path / "missing-reports",
        run_index_path=tmp_path / "runs" / "index.json",
        dashboard_dir=tmp_path / "dashboard",
        feedback_path=tmp_path / "feedback" / "feedback.jsonl",
    )

    summary = build_summary(paths)

    assert summary["run_count"] == 0
    assert summary["report_count"] == 0
    assert summary["feedback_count"] == 0
    assert summary["no_cloud_upload"] is True
    assert summary["temporal_report_count"] == 0
    assert summary["latest_temporal_report"] is None


def test_studio_discovers_only_valid_artifact_backed_temporal_reports(tmp_path: Path) -> None:
    image_module = pytest.importorskip("PIL.Image")
    images = tmp_path / "images"
    reports_dir = tmp_path / "reports"
    images.mkdir()
    for index, value in enumerate((0, 20, 200)):
        image_module.fromarray(np.full((8, 8, 3), value, dtype=np.uint8)).save(
            images / f"{index}.png"
        )
    sequence = TemporalObservationSequence(
        VISUAL_ENGINE_SCHEMA_VERSION,
        "studio-temporal",
        "1",
        str(tmp_path),
        "sequence-studio",
        tuple(
            TemporalObservation(f"o{index}", f"images/{index}.png", sequence_index=index)
            for index in range(3)
        ),
        scene_id="scene-studio",
    )
    manifest = tmp_path / "manifest.json"
    manifest.write_text(serialize_temporal_manifest(sequence), encoding="utf-8")
    output = reports_dir / "temporal.json"
    markdown, json_path, artifact_path = run_temporal_pipeline(
        manifest, output.with_suffix(".md"), patch_size=4
    )
    assert markdown.is_file() and json_path == output and artifact_path.is_dir()
    malformed = json.loads(json_path.read_text(encoding="utf-8"))
    malformed["human_review_required"] = False
    (reports_dir / "broken_temporal.json").write_text(json.dumps(malformed), encoding="utf-8")
    paths = StudioPaths(
        reports_dir=reports_dir,
        run_index_path=reports_dir / "runs" / "index.json",
        dashboard_dir=tmp_path / "dashboard",
        feedback_path=tmp_path / "feedback.jsonl",
        project_root=tmp_path,
    )

    reports = list_reports(paths)
    detail = load_report("temporal.json", paths)
    summary = build_summary(paths)

    assert [report["name"] for report in reports] == ["temporal.json"]
    assert reports[0]["type"] == "temporal"
    assert reports[0]["candidate_event_count"] == 2
    assert detail["report_type"] == "temporal"
    assert detail["temporal_sequence_summary"]["sequence_id"] == "sequence-studio"
    assert detail["candidate_event_count"] == 2
    assert detail["candidate_temporal_change_events"][0]["requires_human_review"] is True
    assert detail["temporal_artifact_provenance"]["artifact_path"] == artifact_path.as_posix()
    assert summary["temporal_report_count"] == 1
    assert summary["latest_temporal_report"]["name"] == "temporal.json"
    assert summary["temporal_report_warnings"]
    with pytest.raises(ValueError, match="Temporal report is invalid"):
        load_report("broken_temporal.json", paths)


def test_studio_run_and_report_listing(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    assets_dir = reports_dir / "assets"
    runs_dir = reports_dir / "runs"
    reports_dir.mkdir()
    assets_dir.mkdir()
    runs_dir.mkdir()
    (assets_dir / "anomaly_0001.png").write_bytes(b"png")
    report_path = reports_dir / "demo_report.json"
    report_path.write_text(
        json.dumps(
            {
                "run_id": "ade-demo",
                "run_metadata": {
                    "generated_at": "2026-07-13T00:00:00+00:00",
                    "input_path": "data/raw/demo_images",
                    "number_of_images": 6,
                    "number_of_patches": 96,
                    "novelty_strategy": "hybrid",
                },
                "candidate_anomalies": [
                    {
                        "anomaly_id": "anomaly-0001",
                        "coordinates": [1, 2, 3, 4],
                        "feature_deviations": [{"feature": "red", "deviation": 0.8}],
                        "novelty_score": 0.9,
                        "patch_size": 64,
                        "preview_path": "assets/anomaly_0001.png",
                        "reason": "Candidate anomaly requires human review.",
                        "score_breakdown": {"strategy": "hybrid"},
                        "source_path": "data/raw/demo_images/demo_image_01.png",
                    }
                ],
                "candidate_unknown_concepts": [
                    {"concept_id": "concept-001", "confidence_score": 0.8}
                ],
                "human_review_required": True,
                "number_of_images": 6,
                "number_of_patches": 96,
            }
        ),
        encoding="utf-8",
    )
    (reports_dir / "demo_report.md").write_text("# Demo", encoding="utf-8")
    (reports_dir / "demo_report.html").write_text("<h1>Demo</h1>", encoding="utf-8")
    run_index = runs_dir / "index.json"
    run_index.write_text(
        json.dumps(
            {
                "index_version": "1.0",
                "updated_at": "2026-07-13T00:00:00+00:00",
                "runs": [{"run_id": "ade-demo", "json_report_path": report_path.as_posix()}],
            }
        ),
        encoding="utf-8",
    )
    paths = StudioPaths(
        reports_dir=reports_dir,
        run_index_path=run_index,
        dashboard_dir=tmp_path / "dashboard",
        feedback_path=tmp_path / "feedback.jsonl",
        report_assets_dir=assets_dir,
    )

    reports = list_reports(paths)
    runs = list_runs(paths)
    loaded_report = load_report("demo_report.json", paths)

    assert reports[0]["name"] == "demo_report.json"
    assert reports[0]["candidate_anomaly_count"] == 1
    assert reports[0]["candidate_concept_count"] == 1
    assert runs[0]["run_id"] == "ade-demo"
    assert loaded_report["run_id"] == "ade-demo"
    assert loaded_report["report_name"] == "demo_report.json"
    assert loaded_report["input_directory"] == "data/raw/demo_images"
    assert loaded_report["number_of_images"] == 6
    assert loaded_report["number_of_patches"] == 96
    assert loaded_report["novelty_strategy"] == "hybrid"
    assert loaded_report["candidate_anomalies"][0]["preview_asset_name"] == "anomaly_0001.png"
    assert loaded_report["candidate_anomalies"][0]["source_image_path"].endswith(
        "demo_image_01.png"
    )

    summary = build_summary(paths)
    assert summary["latest_run_id"] == "ade-demo"
    assert summary["latest_report_name"] == "demo_report.json"
    assert summary["latest_report_json_path"] == report_path.as_posix()
    assert summary["latest_report_html_path"] == (reports_dir / "demo_report.html").as_posix()
    assert summary["candidate_anomaly_count"] == 1
    assert summary["candidate_concept_count"] == 1
    assert summary["input_type"] == "image folder"
    assert summary["number_of_images"] == 6
    assert summary["number_of_patches"] == 96


def test_studio_analysis_rejects_missing_input_path(tmp_path: Path) -> None:
    paths = StudioPaths(
        reports_dir=tmp_path / "reports",
        run_index_path=tmp_path / "reports" / "runs" / "index.json",
        dashboard_dir=tmp_path / "dashboard",
        feedback_path=tmp_path / "feedback.jsonl",
    )

    with pytest.raises(FileNotFoundError, match="Input path does not exist"):
        run_visual_analysis(tmp_path / "missing", paths=paths)


def test_studio_fastapi_analysis_accepts_json_body(monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import ade.studio.api as studio_api

    def fake_run_visual_analysis(
        input_path: Path,
        output_name: str | None,
        paths: StudioPaths,
    ) -> dict[str, object]:
        del paths
        assert input_path == Path("data/raw/demo_images")
        assert output_name == "studio_report.md"
        return {
            "status": "ok",
            "message": "Analysis complete.",
            "run_id": "ade-studio-test",
            "workflow": "visual",
            "input_path": input_path.as_posix(),
            "markdown_report_path": "data/reports/studio_report.md",
            "json_report_path": "data/reports/studio_report.json",
            "html_report_path": "data/reports/studio_report.html",
            "candidate_anomaly_count": 1,
            "candidate_concept_count": 2,
            "human_review_required": True,
            "validated": True,
        }

    monkeypatch.setattr(studio_api, "run_visual_analysis", fake_run_visual_analysis)
    client = TestClient(studio_api.create_app())

    response = client.post(
        "/api/studio/analysis",
        json={
            "input_path": "data/raw/demo_images",
            "workflow": "visual",
            "output_name": "studio_report.md",
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["run_id"] == "ade-studio-test"
    assert body["markdown_report_path"] == "data/reports/studio_report.md"
    assert body["json_report_path"] == "data/reports/studio_report.json"
    assert body["html_report_path"] == "data/reports/studio_report.html"
    assert body["candidate_anomaly_count"] == 1
    assert body["candidate_concept_count"] == 2
    assert body["human_review_required"] is True


def test_studio_fastapi_analysis_missing_input_path_returns_clear_400(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import ade.studio.api as studio_api

    def fake_run_visual_analysis(
        input_path: Path,
        output_name: str | None,
        paths: StudioPaths,
    ) -> dict[str, object]:
        del input_path, output_name, paths
        raise FileNotFoundError("Input path does not exist: data/raw/missing")

    monkeypatch.setattr(studio_api, "run_visual_analysis", fake_run_visual_analysis)
    client = TestClient(studio_api.create_app())

    response = client.post(
        "/api/studio/analysis",
        json={"input_path": "data/raw/missing", "workflow": "visual"},
    )

    assert response.status_code == 400
    assert "Input path does not exist" in response.json()["detail"]


def test_studio_fastapi_report_asset_endpoint_serves_local_asset(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import ade.studio.api as studio_api
    import ade.studio.service as studio_service

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()
    (assets_dir / "anomaly_0001.png").write_bytes(b"png")

    def fake_resolve_report_asset(asset_name: str) -> Path:
        return studio_service.resolve_report_asset(
            asset_name,
            paths=StudioPaths(report_assets_dir=assets_dir),
        )

    monkeypatch.setattr(studio_api, "resolve_report_asset", fake_resolve_report_asset)
    client = TestClient(studio_api.create_app())

    response = client.get("/api/studio/report-assets/anomaly_0001.png")

    assert response.status_code == 200
    assert response.content == b"png"


def test_studio_fastapi_report_asset_endpoint_blocks_path_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import ade.studio.api as studio_api
    import ade.studio.service as studio_service

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    def fake_resolve_report_asset(asset_name: str) -> Path:
        return studio_service.resolve_report_asset(
            asset_name,
            paths=StudioPaths(report_assets_dir=assets_dir),
        )

    monkeypatch.setattr(studio_api, "resolve_report_asset", fake_resolve_report_asset)
    client = TestClient(studio_api.create_app())

    response = client.get("/api/studio/report-assets/../secret.txt")

    assert response.status_code == 404


def test_studio_fastapi_report_asset_endpoint_returns_404_for_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import ade.studio.api as studio_api
    import ade.studio.service as studio_service

    assets_dir = tmp_path / "assets"
    assets_dir.mkdir()

    def fake_resolve_report_asset(asset_name: str) -> Path:
        return studio_service.resolve_report_asset(
            asset_name,
            paths=StudioPaths(report_assets_dir=assets_dir),
        )

    monkeypatch.setattr(studio_api, "resolve_report_asset", fake_resolve_report_asset)
    client = TestClient(studio_api.create_app())

    response = client.get("/api/studio/report-assets/missing.png")

    assert response.status_code == 404


def test_studio_resolve_report_html_serves_sibling_html_report(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    html_path = reports_dir / "demo_report.html"
    html_path.write_text("<h1>Demo</h1>", encoding="utf-8")

    resolved = resolve_report_html(
        "demo_report.json",
        paths=StudioPaths(reports_dir=reports_dir),
    )

    assert resolved == html_path.resolve()


def test_studio_resolve_report_html_blocks_path_traversal(tmp_path: Path) -> None:
    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    with pytest.raises(ValueError, match="report_name"):
        resolve_report_html("../demo_report.json", paths=StudioPaths(reports_dir=reports_dir))


def test_studio_fastapi_report_html_endpoint_serves_local_html(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import ade.studio.api as studio_api
    import ade.studio.service as studio_service

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()
    (reports_dir / "demo_report.html").write_text("<h1>Demo</h1>", encoding="utf-8")

    def fake_resolve_report_html(report_name: str) -> Path:
        return studio_service.resolve_report_html(
            report_name,
            paths=StudioPaths(reports_dir=reports_dir),
        )

    monkeypatch.setattr(studio_api, "resolve_report_html", fake_resolve_report_html)
    client = TestClient(studio_api.create_app())

    response = client.get("/api/studio/reports/demo_report.json/html")

    assert response.status_code == 200
    assert b"Demo" in response.content


def test_studio_fastapi_report_html_endpoint_blocks_path_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("fastapi")
    from fastapi.testclient import TestClient

    import ade.studio.api as studio_api
    import ade.studio.service as studio_service

    reports_dir = tmp_path / "reports"
    reports_dir.mkdir()

    def fake_resolve_report_html(report_name: str) -> Path:
        return studio_service.resolve_report_html(
            report_name,
            paths=StudioPaths(reports_dir=reports_dir),
        )

    monkeypatch.setattr(studio_api, "resolve_report_html", fake_resolve_report_html)
    client = TestClient(studio_api.create_app())

    response = client.get("/api/studio/reports/../demo_report.json/html")

    assert response.status_code in {400, 404}


def test_studio_analysis_resolves_repo_relative_input_path(tmp_path: Path) -> None:
    paths = StudioPaths(
        reports_dir=tmp_path / "reports",
        run_index_path=tmp_path / "reports" / "runs" / "index.json",
        dashboard_dir=tmp_path / "dashboard",
        feedback_path=tmp_path / "feedback.jsonl",
        project_root=tmp_path,
    )

    with pytest.raises(FileNotFoundError, match="data.raw.demo_images"):
        run_visual_analysis("data/raw/demo_images", paths=paths)

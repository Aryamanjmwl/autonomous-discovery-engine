import importlib.util
import json
from pathlib import Path
from types import ModuleType

import pytest

from ade.api.service import ApiRequestError, run_discovery


def test_run_discovery_rejects_missing_dataset_path(tmp_path: Path) -> None:
    with pytest.raises(ApiRequestError, match="Dataset path does not exist"):
        run_discovery(
            dataset_path=tmp_path / "missing",
            output_dir=tmp_path / "reports",
        )


def test_health_and_version_endpoints() -> None:
    TestClient = pytest.importorskip("fastapi.testclient").TestClient
    from ade.api.app import app

    client = TestClient(app)

    health = client.get("/health")
    version = client.get("/version")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert "ade_version" in health.json()
    assert version.status_code == 200
    assert version.json()["service"] == "ade-local-api"


def test_run_request_validation_returns_400(tmp_path: Path) -> None:
    TestClient = pytest.importorskip("fastapi.testclient").TestClient
    from ade.api.app import app

    client = TestClient(app)
    response = client.post(
        "/runs",
        json={
            "dataset_path": str(tmp_path / "missing"),
            "output_dir": str(tmp_path / "reports"),
        },
    )

    assert response.status_code == 400
    assert "Dataset path does not exist" in response.json()["detail"]


def test_run_listing_endpoint_reads_default_index(tmp_path: Path, monkeypatch) -> None:
    TestClient = pytest.importorskip("fastapi.testclient").TestClient
    from ade.api.app import app

    index_path = tmp_path / "data" / "reports" / "runs" / "index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(
        json.dumps(
            {
                "index_version": "1.0",
                "updated_at": "2026-07-07T00:00:00+00:00",
                "runs": [
                    {
                        "run_id": "ade_20260707_120000_abcdef",
                        "generated_at": "2026-07-07T12:00:00+00:00",
                        "input_path": "data/raw/demo_images",
                        "markdown_report_path": "data/reports/demo_report.md",
                        "json_report_path": "data/reports/demo_report.json",
                        "run_metadata_path": (
                            "data/reports/runs/ade_20260707_120000_abcdef.json"
                        ),
                        "number_of_candidate_anomalies": 3,
                        "number_of_candidate_unknown_concepts": 1,
                        "human_review_required": True,
                    }
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)

    response = TestClient(app).get("/runs")

    assert response.status_code == 200
    assert response.json()["runs"][0]["run_id"] == "ade_20260707_120000_abcdef"


def test_run_detail_not_found_returns_404(tmp_path: Path, monkeypatch) -> None:
    TestClient = pytest.importorskip("fastapi.testclient").TestClient
    from ade.api.app import app

    monkeypatch.chdir(tmp_path)
    response = TestClient(app).get("/runs/missing")

    assert response.status_code == 404


def test_api_can_run_pipeline_on_demo_dataset(tmp_path: Path) -> None:
    TestClient = pytest.importorskip("fastapi.testclient").TestClient
    pytest.importorskip("PIL.Image")
    from ade.api.app import app

    image_dir = tmp_path / "images"
    output_dir = tmp_path / "reports"
    generate_demo_images = _load_demo_data_module().generate_demo_images
    generate_demo_images(output_dir=image_dir)

    response = TestClient(app).post(
        "/runs",
        json={
            "dataset_path": str(image_dir),
            "output_dir": str(output_dir),
            "run_name": "api_demo",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "completed"
    assert data["run_id"].startswith("ade_")
    assert Path(data["markdown_report_path"]).is_file()
    assert Path(data["json_report_path"]).is_file()


def test_docker_files_exist_and_exclude_generated_artifacts() -> None:
    root = Path(__file__).resolve().parents[1]
    dockerfile = root / "Dockerfile"
    compose = root / "docker-compose.yml"
    dockerignore = root / ".dockerignore"

    assert dockerfile.is_file()
    assert compose.is_file()
    assert dockerignore.is_file()

    ignore_text = dockerignore.read_text(encoding="utf-8")
    assert ".git" in ignore_text
    assert "data/reports/runs/" in ignore_text
    assert "data/reports/assets/" in ignore_text
    assert "**/__pycache__" in ignore_text


def _load_demo_data_module() -> ModuleType:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "create_demo_data.py"
    spec = importlib.util.spec_from_file_location("ade_demo_data_script", script_path)
    if spec is None or spec.loader is None:
        raise AssertionError(f"Could not load demo data script: {script_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

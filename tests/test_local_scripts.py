from __future__ import annotations

import csv
import importlib.util
import os
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def test_local_verification_scripts_exist() -> None:
    assert (PROJECT_ROOT / "scripts" / "run_benchmark.py").is_file()
    assert (PROJECT_ROOT / "scripts" / "verify_local.py").is_file()


def test_create_demo_data_runs_as_direct_subprocess() -> None:
    result = _run_python_script(["scripts/create_demo_data.py"])

    assert result.returncode == 0
    assert "Images created:" in result.stdout


def test_create_tabular_demo_data_runs_and_writes_deterministic_csv(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "tabular"
    result = _run_python_script(
        ["scripts/create_tabular_demo_data.py", "--output-dir", output_dir.as_posix()]
    )

    csv_path = output_dir / "operations.csv"
    first_text = csv_path.read_text(encoding="utf-8")
    second_result = _run_python_script(
        ["scripts/create_tabular_demo_data.py", "--output-dir", output_dir.as_posix()]
    )
    second_text = csv_path.read_text(encoding="utf-8")
    rows = _read_csv_rows(csv_path)

    assert result.returncode == 0
    assert second_result.returncode == 0
    assert "Suggested ADE tabular command" in result.stdout
    assert first_text == second_text
    assert rows[0].keys() == {
        "row_id",
        "segment",
        "region",
        "amount",
        "transactions",
        "error_rate",
        "latency_ms",
        "status",
        "anomaly_marker",
    }
    assert len(rows) == 48
    assert sum(1 for row in rows if row["anomaly_marker"]) == 3
    assert any(row["anomaly_marker"] == "injected_latency_spike" for row in rows)


def test_create_timeseries_demo_data_runs_and_writes_deterministic_csv(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "timeseries"
    result = _run_python_script(
        ["scripts/create_timeseries_demo_data.py", "--output-dir", output_dir.as_posix()]
    )

    csv_path = output_dir / "machine_metrics.csv"
    first_text = csv_path.read_text(encoding="utf-8")
    second_result = _run_python_script(
        ["scripts/create_timeseries_demo_data.py", "--output-dir", output_dir.as_posix()]
    )
    second_text = csv_path.read_text(encoding="utf-8")
    rows = _read_csv_rows(csv_path)

    assert result.returncode == 0
    assert second_result.returncode == 0
    assert "Suggested ADE time-series command" in result.stdout
    assert first_text == second_text
    assert rows[0].keys() == {
        "timestamp",
        "machine",
        "temperature",
        "pressure",
        "throughput",
        "anomaly_marker",
    }
    assert len(rows) == 96
    assert sum(1 for row in rows if row["anomaly_marker"]) == 3
    assert any(
        row["anomaly_marker"] == "injected_temperature_pressure_spike"
        for row in rows
    )


def test_run_benchmark_runs_after_demo_data_generation(tmp_path: Path) -> None:
    demo_result = _run_python_script(["scripts/create_demo_data.py"])
    assert demo_result.returncode == 0

    output_path = tmp_path / "benchmark.json"
    benchmark_result = _run_python_script(
        [
            "scripts/run_benchmark.py",
            "--input",
            "data/raw/demo_images",
            "--config",
            "configs/default.yaml",
            "--output",
            output_path.as_posix(),
        ]
    )

    assert benchmark_result.returncode == 0
    assert output_path.is_file()
    assert "Report valid: True" in benchmark_result.stdout


def test_verify_local_exposes_deterministic_steps() -> None:
    module = _load_script_module("verify_local")

    steps = module.verification_steps("python")
    names = [step.name for step in steps]
    commands = [step.command for step in steps]

    assert callable(module.main)
    assert names == [
        "ruff",
        "tests",
        "demo data",
        "demo analysis",
        "report validation",
        "html export",
        "benchmark",
        "local dashboard export",
        "run listing",
    ]
    assert ["ruff", "check"] in commands
    assert ["pytest"] in commands
    assert any("--validate-report" in command for command in commands)
    assert any("--export-html-report" in command for command in commands)
    assert any("--export-local-dashboard" in command for command in commands)
    assert any("scripts/run_benchmark.py" in command for command in commands)


def test_modality_example_docs_and_matrix_exist() -> None:
    tabular_doc = PROJECT_ROOT / "examples" / "modalities" / "tabular_workflow.md"
    timeseries_doc = PROJECT_ROOT / "examples" / "modalities" / "timeseries_workflow.md"
    matrix_doc = PROJECT_ROOT / "docs" / "modality_capability_matrix.md"

    assert tabular_doc.is_file()
    assert timeseries_doc.is_file()
    assert matrix_doc.is_file()
    matrix = matrix_doc.read_text(encoding="utf-8").lower()
    assert "tabular csv | implemented lightweight adapter foundation and cli workflow" in matrix
    assert "time-series csv | implemented lightweight adapter foundation" in matrix
    assert "production streaming" in matrix


def _run_python_script(args: list[str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    src_path = str(PROJECT_ROOT / "src")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        src_path if not existing_pythonpath else os.pathsep.join([src_path, existing_pythonpath])
    )
    return subprocess.run(
        [sys.executable, *args],
        cwd=PROJECT_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def _load_script_module(name: str):
    script_path = PROJECT_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

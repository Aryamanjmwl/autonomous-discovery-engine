from __future__ import annotations

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
        "run listing",
    ]
    assert ["ruff", "check"] in commands
    assert ["pytest"] in commands
    assert any("--validate-report" in command for command in commands)
    assert any("--export-html-report" in command for command in commands)
    assert any("scripts/run_benchmark.py" in command for command in commands)


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


def _load_script_module(name: str):
    script_path = PROJECT_ROOT / "scripts" / f"{name}.py"
    spec = importlib.util.spec_from_file_location(name, script_path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module

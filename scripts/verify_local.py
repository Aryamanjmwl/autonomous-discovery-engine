"""Run ADE's local verification workflow."""

from __future__ import annotations

import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"


@dataclass(frozen=True)
class VerificationStep:
    """A named local verification command."""

    name: str
    command: list[str]


def verification_steps(python_executable: str = sys.executable) -> list[VerificationStep]:
    """Return the deterministic local verification command sequence."""

    return [
        VerificationStep("ruff", ["ruff", "check"]),
        VerificationStep("tests", ["pytest"]),
        VerificationStep("demo data", [python_executable, "scripts/create_demo_data.py"]),
        VerificationStep(
            "demo analysis",
            [
                python_executable,
                "-m",
                "ade.cli",
                "--input",
                "data/raw/demo_images",
                "--output",
                "data/reports/demo_report.md",
            ],
        ),
        VerificationStep(
            "report validation",
            [
                python_executable,
                "-m",
                "ade.cli",
                "--validate-report",
                "data/reports/demo_report.json",
            ],
        ),
        VerificationStep(
            "html export",
            [
                python_executable,
                "-m",
                "ade.cli",
                "--export-html-report",
                "data/reports/demo_report.json",
                "--output",
                "data/reports/demo_report.html",
            ],
        ),
        VerificationStep(
            "benchmark",
            [
                python_executable,
                "scripts/run_benchmark.py",
                "--input",
                "data/raw/demo_images",
                "--config",
                "configs/default.yaml",
                "--output",
                "data/benchmarks/demo_benchmark.json",
            ],
        ),
        VerificationStep(
            "run listing",
            [python_executable, "-m", "ade.cli", "--list-runs", "--limit", "5"],
        ),
    ]


def main() -> int:
    """Run local verification and stop on the first failed command."""

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_PATH)
        if not existing_pythonpath
        else os.pathsep.join([str(SRC_PATH), existing_pythonpath])
    )

    steps = verification_steps(sys.executable)
    for index, step in enumerate(steps, start=1):
        print(f"[{index}/{len(steps)}] {step.name}: {' '.join(step.command)}")
        result = subprocess.run(step.command, cwd=REPO_ROOT, env=env, check=False)
        if result.returncode != 0:
            print(f"FAILED: {step.name} exited with code {result.returncode}")
            return result.returncode

    print("Local verification passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Run a lightweight local ADE benchmark through the public CLI."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from time import perf_counter
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
REPORT_PATH = Path("data/reports/benchmark_report.md")


@dataclass(frozen=True)
class CommandResult:
    """Subprocess result captured for benchmark diagnostics."""

    command: list[str]
    returncode: int
    stdout: str
    stderr: str


def build_parser() -> argparse.ArgumentParser:
    """Create the benchmark script parser."""

    parser = argparse.ArgumentParser(description="Run a local ADE benchmark smoke check.")
    parser.add_argument("--input", required=True, type=Path, help="Input dataset path.")
    parser.add_argument("--config", required=True, type=Path, help="ADE config path.")
    parser.add_argument("--output", required=True, type=Path, help="Benchmark JSON output path.")
    return parser


def main() -> int:
    """Run analysis, validate the report, and write benchmark metadata."""

    args = build_parser().parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)

    analysis_command = [
        sys.executable,
        "-m",
        "ade.cli",
        "--input",
        args.input.as_posix(),
        "--output",
        REPORT_PATH.as_posix(),
        "--config",
        args.config.as_posix(),
    ]
    validation_command = [
        sys.executable,
        "-m",
        "ade.cli",
        "--validate-report",
        REPORT_PATH.with_suffix(".json").as_posix(),
    ]

    started = perf_counter()
    analysis_result = _run_command(analysis_command)
    if analysis_result.returncode != 0:
        _write_result(
            output_path=args.output,
            input_path=args.input,
            config_path=args.config,
            report_valid=False,
            duration_seconds=perf_counter() - started,
            command=analysis_command,
            warnings=_warnings([analysis_result]),
            metadata={"failed_step": "analysis"},
        )
        _print_failure("analysis", analysis_result)
        return analysis_result.returncode

    validation_result = _run_command(validation_command)
    report_valid = validation_result.returncode == 0
    result_data = _write_result(
        output_path=args.output,
        input_path=args.input,
        config_path=args.config,
        report_valid=report_valid,
        duration_seconds=perf_counter() - started,
        command=analysis_command,
        warnings=_warnings([analysis_result, validation_result]),
        metadata={"validation_command": validation_command},
    )

    if not report_valid:
        _print_failure("validation", validation_result)
        return validation_result.returncode or 1

    print(f"ADE benchmark written to {args.output}")
    print(f"Benchmark ID: {result_data['benchmark_id']}")
    print(f"Duration seconds: {result_data['duration_seconds']:.4f}")
    print(f"Report valid: {result_data['report_valid']}")
    return 0


def _run_command(command: list[str]) -> CommandResult:
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_PATH)
        if not existing_pythonpath
        else os.pathsep.join([str(SRC_PATH), existing_pythonpath])
    )
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        env=env,
        check=False,
        capture_output=True,
        text=True,
    )
    return CommandResult(command, result.returncode, result.stdout, result.stderr)


def _write_result(
    output_path: Path,
    input_path: Path,
    config_path: Path,
    report_valid: bool,
    duration_seconds: float,
    command: list[str],
    warnings: list[str],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    benchmark_id = (
        f"bench_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}"
    )
    data: dict[str, Any] = {
        "benchmark_id": benchmark_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "input_path": input_path.as_posix(),
        "config_path": config_path.as_posix(),
        "output_path": output_path.as_posix(),
        "report_json_path": REPORT_PATH.with_suffix(".json").as_posix(),
        "report_valid": bool(report_valid),
        "duration_seconds": float(duration_seconds),
        "command": command,
        "warnings": warnings,
        "metadata": metadata,
    }
    output_path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return data


def _warnings(results: list[CommandResult]) -> list[str]:
    return [result.stderr.strip() for result in results if result.stderr.strip()]


def _print_failure(step_name: str, result: CommandResult) -> None:
    print(f"ADE benchmark {step_name} failed with exit code {result.returncode}.")
    if result.stdout.strip():
        print(result.stdout.strip())
    if result.stderr.strip():
        print(result.stderr.strip())


if __name__ == "__main__":
    raise SystemExit(main())

"""Run the deterministic temporal demo workflow end to end."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SRC_PATH = REPO_ROOT / "src"
DEMO_ROOT = REPO_ROOT / "data/raw/temporal_demo"


def main() -> int:
    """Generate local demo data and validate one complete temporal evidence package."""

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        str(SRC_PATH)
        if not existing_pythonpath
        else os.pathsep.join([str(SRC_PATH), existing_pythonpath])
    )
    generate = _run(
        [sys.executable, "scripts/create_temporal_demo_data.py"], env, "demo generation"
    )
    if generate:
        return generate
    manifest = DEMO_ROOT / "scene_revisit_shift/manifest.json"
    validate_manifest = _run(
        [sys.executable, "-m", "ade.cli", "--validate-temporal-manifest", str(manifest)],
        env,
        "manifest validation",
    )
    if validate_manifest:
        return validate_manifest
    with tempfile.TemporaryDirectory(prefix=".tmp_temporal_demo_verify_", dir=REPO_ROOT) as value:
        temporary = Path(value)
        report_path = temporary / "temporal_demo.md"
        analysis = _run(
            [
                sys.executable,
                "-m",
                "ade.cli",
                "--temporal-manifest",
                str(manifest),
                "--temporal-output",
                str(report_path),
                "--temporal-strategy",
                "adjacent_difference",
                "--temporal-patch-size",
                "16",
            ],
            env,
            "temporal analysis",
        )
        if analysis:
            return analysis
        json_path = report_path.with_suffix(".json")
        report = json.loads(json_path.read_text(encoding="utf-8"))
        artifact_path = str(report["artifact_provenance"]["artifact_path"])
        commands = (
            (
                "artifact validation",
                [sys.executable, "-m", "ade.cli", "--validate-temporal-artifact", artifact_path],
            ),
            (
                "report validation",
                [sys.executable, "-m", "ade.cli", "--validate-temporal-report", str(json_path)],
            ),
            (
                "HTML export",
                [
                    sys.executable,
                    "-m",
                    "ade.cli",
                    "--export-temporal-html-report",
                    str(json_path),
                    "--temporal-output",
                    str(report_path.with_suffix(".html")),
                ],
            ),
        )
        for name, command in commands:
            result = _run(command, env, name)
            if result:
                return result
    print("Temporal demo verification passed. Candidate temporal changes require human review.")
    return 0


def _run(command: list[str], env: dict[str, str], name: str) -> int:
    print(f"[{name}] {' '.join(command)}")
    result = subprocess.run(command, cwd=REPO_ROOT, env=env, check=False)
    if result.returncode:
        print(f"FAILED: {name} exited with code {result.returncode}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())

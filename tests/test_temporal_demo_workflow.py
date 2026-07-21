from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from ade.reporting.temporal_report import validate_temporal_report_file
from ade.visual import load_temporal_manifest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _load_generator():
    path = PROJECT_ROOT / "scripts/create_temporal_demo_data.py"
    spec = importlib.util.spec_from_file_location("create_temporal_demo_data", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_temporal_demo_generator_creates_valid_deterministic_sequences(tmp_path: Path) -> None:
    pytest.importorskip("PIL.Image")
    generator = _load_generator()
    root = tmp_path / "temporal_demo"

    manifests = generator.generate_temporal_demo(root)
    first_hashes = _file_hashes(root)
    repeated = generator.generate_temporal_demo(root)
    second_hashes = _file_hashes(root)

    assert [path.parent.name for path in manifests] == [
        "scene_revisit_shift",
        "plant_growth_like",
        "inspection_damage_like",
    ]
    assert repeated == manifests
    assert first_hashes == second_hashes
    assert len(first_hashes) == 12
    for manifest_path in manifests:
        sequence = load_temporal_manifest(manifest_path, strict=True)
        assert len(sequence.observations) == 3
        assert sequence.metadata["synthetic_generated_demo"] is True
        assert [item.sequence_index for item in sequence.observations] == [0, 1, 2]


def test_temporal_demo_cli_builds_valid_report_artifact_and_html(tmp_path: Path) -> None:
    pytest.importorskip("PIL.Image")
    generator = _load_generator()
    manifest = generator.generate_temporal_demo(tmp_path / "data")[0]
    report_path = tmp_path / "reports/temporal_demo.md"

    analysis = _run(
        "--temporal-manifest",
        str(manifest),
        "--temporal-output",
        str(report_path),
        "--temporal-patch-size",
        "16",
    )
    report_json = report_path.with_suffix(".json")
    report = json.loads(report_json.read_text(encoding="utf-8"))
    artifact_path = Path(report["artifact_provenance"]["artifact_path"])
    validate_artifact = _run("--validate-temporal-artifact", str(artifact_path))
    validate_report = _run("--validate-temporal-report", str(report_json))
    html_path = report_path.with_suffix(".html")
    export_html = _run(
        "--export-temporal-html-report",
        str(report_json),
        "--temporal-output",
        str(html_path),
    )

    assert analysis.returncode == 0, analysis.stderr
    assert validate_artifact.returncode == 0, validate_artifact.stderr
    assert validate_report.returncode == 0, validate_report.stderr
    assert export_html.returncode == 0, export_html.stderr
    assert validate_temporal_report_file(report_json) == []
    assert artifact_path.is_dir()
    assert html_path.is_file()
    assert "candidate temporal changes" in report_path.read_text(encoding="utf-8").lower()


def test_temporal_demo_outputs_are_ignored_and_default_demo_verifier_is_unchanged() -> None:
    ignore = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    verify_local = (PROJECT_ROOT / "scripts/verify_local.py").read_text(encoding="utf-8")
    create_demo = (PROJECT_ROOT / "scripts/create_demo_data.py").read_text(encoding="utf-8")

    assert "data/raw/*" in ignore
    assert "data/reports/*" in ignore
    assert ".tmp_*" in ignore
    assert "create_temporal_demo_data" not in verify_local
    assert "IMAGE_COUNT = int(_DEMO_CONFIG" in create_demo


def test_temporal_demo_scripts_run_directly(tmp_path: Path) -> None:
    pytest.importorskip("PIL.Image")
    output = tmp_path / "direct"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/create_temporal_demo_data.py",
            "--output-dir",
            str(output),
        ],
        cwd=PROJECT_ROOT,
        env=_environment(),
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert "Temporal manifests created: 3" in result.stdout
    assert (output / "scene_revisit_shift/manifest.json").is_file()


def _file_hashes(root: Path) -> dict[str, str]:
    return {
        path.relative_to(root).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(root.rglob("*"))
        if path.is_file()
    }


def _run(*arguments: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "-m", "ade.cli", *arguments],
        cwd=PROJECT_ROOT,
        env=_environment(),
        check=False,
        capture_output=True,
        text=True,
    )


def _environment() -> dict[str, str]:
    env = os.environ.copy()
    src = str(PROJECT_ROOT / "src")
    existing = env.get("PYTHONPATH")
    env["PYTHONPATH"] = src if not existing else os.pathsep.join((src, existing))
    return env

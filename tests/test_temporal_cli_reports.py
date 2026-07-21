from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from ade.cli import build_parser, main
from ade.reporting.temporal_report import validate_temporal_report_file
from ade.visual import (
    VISUAL_ENGINE_SCHEMA_VERSION,
    TemporalObservation,
    TemporalObservationSequence,
    serialize_temporal_manifest,
)


def _manifest(tmp_path: Path) -> Path:
    image_module = pytest.importorskip("PIL.Image")
    images = tmp_path / "images"
    images.mkdir()
    for index, value in enumerate((0, 12, 220)):
        array = np.full((12, 12, 3), value, dtype=np.uint8)
        if index == 2:
            array[:6, :6] = 255
        image_module.fromarray(array).save(images / f"{index}.png")
    sequence = TemporalObservationSequence(
        VISUAL_ENGINE_SCHEMA_VERSION,
        "temporal-demo",
        "1",
        str(tmp_path),
        "sequence-1",
        (
            TemporalObservation("o2", "images/2.png", sequence_index=2),
            TemporalObservation("o0", "images/0.png", sequence_index=0),
            TemporalObservation("o1", "images/1.png", sequence_index=1),
        ),
        scene_id="scene-a",
    )
    path = tmp_path / "manifest.json"
    path.write_text(serialize_temporal_manifest(sequence), encoding="utf-8")
    return path


def test_cli_validates_temporal_manifest(
    monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path
) -> None:
    manifest = _manifest(tmp_path)
    monkeypatch.setattr("sys.argv", ["ade", "--validate-temporal-manifest", str(manifest)])

    main()

    assert "temporal manifest validation passed" in capsys.readouterr().out


def test_cli_rejects_invalid_temporal_manifest(
    monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path
) -> None:
    manifest = tmp_path / "invalid.json"
    manifest.write_text("{}", encoding="utf-8")
    monkeypatch.setattr("sys.argv", ["ade", "--validate-temporal-manifest", str(manifest)])

    with pytest.raises(SystemExit):
        main()

    assert "error:" in capsys.readouterr().err.lower()


def test_cli_temporal_analysis_reports_artifact_and_html(
    monkeypatch: pytest.MonkeyPatch, capsys, tmp_path: Path
) -> None:
    manifest = _manifest(tmp_path)
    markdown_path = tmp_path / "reports" / "change.md"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ade",
            "--temporal-manifest",
            str(manifest),
            "--temporal-output",
            str(markdown_path),
            "--temporal-strategy",
            "adjacent_difference",
            "--temporal-patch-size",
            "6",
        ],
    )

    main()

    output = capsys.readouterr().out
    json_path = markdown_path.with_suffix(".json")
    report = json.loads(json_path.read_text(encoding="utf-8"))
    assert "Candidate temporal changes" in markdown_path.read_text(encoding="utf-8")
    assert "require human review" in output.lower()
    assert validate_temporal_report_file(json_path) == []
    assert Path(report["artifact_provenance"]["artifact_path"]).is_dir()
    assert len(report["artifact_provenance"]["artifact_fingerprint"]) == 64
    scores = [event["change_score"] for event in report["candidate_change_events"]]
    assert scores == sorted(scores, reverse=True)
    assert any(event["patch_evidence"] for event in report["candidate_change_events"])

    monkeypatch.setattr(
        "sys.argv",
        ["ade", "--validate-temporal-artifact", report["artifact_provenance"]["artifact_path"]],
    )
    main()
    monkeypatch.setattr("sys.argv", ["ade", "--validate-temporal-report", str(json_path)])
    main()

    html_path = tmp_path / "reports" / "change.html"
    monkeypatch.setattr(
        "sys.argv",
        [
            "ade",
            "--export-temporal-html-report",
            str(json_path),
            "--temporal-output",
            str(html_path),
        ],
    )
    main()
    html = html_path.read_text(encoding="utf-8")
    assert "Candidate Change Events" in html
    assert "requires human review" in html
    assert "o1 → o2" in html or "o0 → o1" in html


def test_temporal_report_without_patch_request_has_no_patch_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest = _manifest(tmp_path)
    output = tmp_path / "no-patches.md"
    monkeypatch.setattr(
        "sys.argv",
        ["ade", "--temporal-manifest", str(manifest), "--temporal-output", str(output)],
    )

    main()

    report = json.loads(output.with_suffix(".json").read_text(encoding="utf-8"))
    assert all(not event["patch_evidence"] for event in report["candidate_change_events"])


def test_malformed_temporal_report_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "bad-report.json"
    path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "report_type": "temporal-visual-change-report",
                "human_review_required": False,
                "candidate_change_events": [{"change_score": float("nan")}],
            }
        ),
        encoding="utf-8",
    )

    errors = validate_temporal_report_file(path)

    assert errors
    assert any("human_review_required" in error for error in errors)
    assert any("finite" in error for error in errors)


def test_temporal_cli_adds_no_dependency_or_default_modality() -> None:
    project = Path("pyproject.toml").read_text(encoding="utf-8")
    args = build_parser().parse_args(["--input", "images", "--output", "report.md"])
    assert "opencv" not in project
    assert args.modality is None
    assert args.temporal_manifest is None

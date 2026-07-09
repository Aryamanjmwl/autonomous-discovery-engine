"""Release-readiness documentation checks."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_private_alpha_docs_exist() -> None:
    required_paths = [
        "docs/README.md",
        "docs/cli_reference.md",
        "docs/report_schema.md",
        "docs/release_checklist.md",
        "docs/versioning_policy.md",
        "docs/releases/private_alpha_readiness_audit.md",
        "examples/README.md",
        "examples/demo_workflow.md",
        "CHANGELOG.md",
    ]

    missing = [path for path in required_paths if not (PROJECT_ROOT / path).is_file()]

    assert missing == []


def test_private_alpha_docs_keep_human_review_language() -> None:
    checked_docs = [
        "README.md",
        "docs/README.md",
        "docs/report_schema.md",
        "docs/releases/private_alpha_readiness_audit.md",
        "examples/demo_workflow.md",
    ]

    for path in checked_docs:
        assert "human review" in _read(path).lower(), path


def test_cli_reference_covers_local_verification_and_benchmark() -> None:
    cli_reference = _read("docs/cli_reference.md")

    assert "scripts/verify_local.py" in cli_reference
    assert "scripts/run_benchmark.py" in cli_reference


def test_report_schema_documents_stable_feedback_targets() -> None:
    report_schema = _read("docs/report_schema.md")

    assert "anomaly_id" in report_schema
    assert "concept_id" in report_schema


def test_release_audit_and_demo_workflow_exist() -> None:
    assert (PROJECT_ROOT / "docs/releases/private_alpha_readiness_audit.md").is_file()
    assert (PROJECT_ROOT / "examples/demo_workflow.md").is_file()


def test_dashboard_docs_are_present_if_dashboard_contract_exists() -> None:
    dashboard_docs = sorted((PROJECT_ROOT / "docs").glob("*dashboard*"))

    for path in dashboard_docs:
        text = path.read_text(encoding="utf-8").lower()
        assert "dashboard" in text
        assert "human review" in text or "review" in text


def test_design_tokens_json_files_are_valid_when_present() -> None:
    for path in PROJECT_ROOT.rglob("design_tokens.json"):
        json.loads(path.read_text(encoding="utf-8"))

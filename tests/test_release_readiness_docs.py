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
        "docs/modality_capability_matrix.md",
        "docs/dashboard/dashboard_product_spec.md",
        "docs/dashboard/dashboard_frontend_contract.md",
        "docs/dashboard/design_tokens.json",
        "docs/dashboard/dashboard_release_plan.md",
        "docs/release_checklist.md",
        "docs/versioning_policy.md",
        "docs/releases/private_alpha_readiness_audit.md",
        "examples/README.md",
        "examples/demo_workflow.md",
        "examples/modalities/README.md",
        "CHANGELOG.md",
    ]

    missing = [path for path in required_paths if not (PROJECT_ROOT / path).is_file()]

    assert missing == []


def test_private_alpha_docs_keep_human_review_language() -> None:
    checked_docs = [
        "README.md",
        "docs/README.md",
        "docs/report_schema.md",
        "docs/modality_capability_matrix.md",
        "docs/dashboard/dashboard_product_spec.md",
        "docs/dashboard/dashboard_frontend_contract.md",
        "docs/dashboard/dashboard_release_plan.md",
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


def test_modality_positioning_docs_are_adapter_based() -> None:
    combined_docs = "\n".join(
        [
            _read("README.md"),
            _read("docs/product_scope.md"),
            _read("docs/architecture.md"),
            _read("docs/modality_capability_matrix.md"),
            _read("examples/modalities/README.md"),
        ]
    ).lower()

    assert "adapter-based" in combined_docs
    assert "computer-vision-only" not in combined_docs
    assert "visual-only system" in combined_docs


def test_modality_matrix_covers_current_and_planned_modalities() -> None:
    matrix = _read("docs/modality_capability_matrix.md").lower()

    for keyword in [
        "visual image folders",
        "tabular csv",
        "time-series csv",
        "sensor streams",
        "live satellite feeds",
        "audio input",
    ]:
        assert keyword in matrix

    for keyword in ["sensor streams", "live satellite feeds", "audio input"]:
        section_start = matrix.index(keyword)
        section = matrix[section_start : section_start + 240]
        assert "planned" in section or "future" in section


def test_dashboard_frontend_contract_documents_stable_targets() -> None:
    frontend_contract = _read("docs/dashboard/dashboard_frontend_contract.md")

    assert "anomaly_id" in frontend_contract
    assert "concept_id" in frontend_contract


def test_dashboard_release_plan_exists() -> None:
    assert (PROJECT_ROOT / "docs/dashboard/dashboard_release_plan.md").is_file()


def test_dashboard_docs_do_not_claim_deployed_app() -> None:
    dashboard_docs = [
        "docs/dashboard/dashboard_product_spec.md",
        "docs/dashboard/dashboard_frontend_contract.md",
        "docs/dashboard/dashboard_release_plan.md",
    ]
    non_implementation_phrases = [
        "does not implement",
        "no dashboard app is implemented",
        "future phases are not implemented",
    ]

    combined_text = "\n".join(_read(path).lower() for path in dashboard_docs)
    for path in dashboard_docs:
        text = _read(path).lower()
        assert "dashboard" in text

    assert any(phrase in combined_text for phrase in non_implementation_phrases)


def test_release_audit_and_demo_workflow_exist() -> None:
    assert (PROJECT_ROOT / "docs/releases/private_alpha_readiness_audit.md").is_file()
    assert (PROJECT_ROOT / "examples/demo_workflow.md").is_file()


def test_design_tokens_json_files_are_valid_when_present() -> None:
    for path in PROJECT_ROOT.rglob("design_tokens.json"):
        json.loads(path.read_text(encoding="utf-8"))

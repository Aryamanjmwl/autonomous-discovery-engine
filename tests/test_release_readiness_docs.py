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
        "docs/modality_capability_matrix.md",
        "docs/report_schema.md",
        "docs/portfolio_case_study.md",
        "docs/sample_outputs.md",
        "docs/cv_project_description.md",
        "docs/demo_assets.md",
        "docs/dashboard/dashboard_product_spec.md",
        "docs/dashboard/dashboard_frontend_contract.md",
        "docs/dashboard/design_tokens.json",
        "docs/dashboard/dashboard_release_plan.md",
        "docs/release_checklist.md",
        "docs/versioning_policy.md",
        "docs/releases/private_alpha_readiness_audit.md",
        "docs/releases/v0.1.0-private-alpha.md",
        "docs/releases/github_release_body_v0.1.0-private-alpha.md",
        "examples/README.md",
        "examples/demo_workflow.md",
        "examples/modalities/tabular_workflow.md",
        "examples/modalities/timeseries_workflow.md",
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
        "docs/portfolio_case_study.md",
        "docs/sample_outputs.md",
        "docs/cv_project_description.md",
        "docs/demo_assets.md",
        "docs/releases/private_alpha_readiness_audit.md",
        "docs/releases/v0.1.0-private-alpha.md",
        "docs/releases/github_release_body_v0.1.0-private-alpha.md",
        "examples/demo_script.md",
        "examples/demo_workflow.md",
        "examples/modalities/tabular_workflow.md",
        "examples/modalities/timeseries_workflow.md",
    ]

    for path in checked_docs:
        assert "human review" in _read(path).lower(), path


def test_cli_reference_covers_local_verification_and_benchmark() -> None:
    cli_reference = _read("docs/cli_reference.md")

    assert "scripts/verify_local.py" in cli_reference
    assert "scripts/run_benchmark.py" in cli_reference
    assert "--export-local-dashboard" in cli_reference


def test_report_schema_documents_stable_feedback_targets() -> None:
    report_schema = _read("docs/report_schema.md")

    assert "anomaly_id" in report_schema
    assert "concept_id" in report_schema


def test_modality_matrix_reflects_tabular_and_timeseries_status() -> None:
    matrix = _read("docs/modality_capability_matrix.md").lower()

    assert "tabular csv | implemented lightweight adapter foundation and cli workflow" in matrix
    assert "time-series csv | implemented lightweight adapter foundation" in matrix
    assert "live streams | planned adapter path" in matrix
    assert "human review" in matrix


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


def test_portfolio_docs_exist_and_keep_private_alpha_framing() -> None:
    required_paths = [
        "docs/portfolio_case_study.md",
        "docs/sample_outputs.md",
        "docs/cv_project_description.md",
        "examples/demo_script.md",
    ]

    for path in required_paths:
        assert (PROJECT_ROOT / path).is_file(), path

    portfolio = _read("docs/portfolio_case_study.md").lower()
    sample_outputs = _read("docs/sample_outputs.md").lower()
    cv_description = _read("docs/cv_project_description.md").lower()

    assert "human review" in portfolio
    assert "ignored by git" in sample_outputs
    assert "not a production saas" in cv_description


def test_readme_includes_portfolio_demo_status_language() -> None:
    readme = _read("README.md").lower()

    assert "--export-local-dashboard" in readme
    assert "v0.1.0-private-alpha.md" in readme
    assert "implemented" in readme
    assert "foundation" in readme
    assert "planned" in readme
    assert "requires human review" in readme or "require human review" in readme


def test_private_alpha_release_docs_are_release_ready_without_overclaiming() -> None:
    release_note = _read("docs/releases/v0.1.0-private-alpha.md").lower()
    release_body = _read(
        "docs/releases/github_release_body_v0.1.0-private-alpha.md"
    ).lower()
    demo_assets = _read("docs/demo_assets.md").lower()
    checklist = _read("docs/release_checklist.md").lower()

    assert "human review" in release_note
    assert "not a production saas" in release_note
    assert "not a production saas" in release_body
    assert "verify_local.py" in checklist
    assert "--export-local-dashboard" in checklist
    assert "git tag -a v0.1.0-private-alpha" in checklist
    assert "do not commit generated private data" in demo_assets


def test_design_tokens_json_files_are_valid_when_present() -> None:
    for path in PROJECT_ROOT.rglob("design_tokens.json"):
        json.loads(path.read_text(encoding="utf-8"))

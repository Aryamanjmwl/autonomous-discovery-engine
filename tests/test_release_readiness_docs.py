"""Release-readiness documentation checks."""

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def _read(path: str) -> str:
    return (PROJECT_ROOT / path).read_text(encoding="utf-8")


def test_technical_preview_docs_exist() -> None:
    required_paths = [
        "SECURITY.md",
        "docs/README.md",
        "docs/cli_reference.md",
        "docs/extension_examples.md",
        "docs/modality_capability_matrix.md",
        "docs/public_release_checklist.md",
        "docs/report_schema.md",
        "docs/modality_capability_matrix.md",
        "docs/dashboard/dashboard_product_spec.md",
        "docs/dashboard/dashboard_frontend_contract.md",
        "docs/dashboard/design_tokens.json",
        "docs/dashboard/dashboard_release_plan.md",
        "docs/release_checklist.md",
        "docs/versioning_policy.md",
        "docs/releases/technical_preview_readiness_audit.md",
        "docs/releases/v0.1.0-preview.md",
        "docs/releases/github_release_body_v0.1.0-preview.md",
        "examples/README.md",
        "examples/demo_workflow.md",
        "examples/modalities/tabular_workflow.md",
        "examples/modalities/timeseries_workflow.md",
        "apps/studio/README.md",
        "CHANGELOG.md",
    ]

    missing = [path for path in required_paths if not (PROJECT_ROOT / path).is_file()]

    assert missing == []


def test_technical_preview_docs_keep_human_review_language() -> None:
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
        "docs/ade_studio.md",
        "docs/cv_project_description.md",
        "docs/demo_assets.md",
        "docs/releases/technical_preview_readiness_audit.md",
        "docs/releases/v0.1.0-preview.md",
        "docs/releases/github_release_body_v0.1.0-preview.md",
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
    assert (PROJECT_ROOT / "docs/releases/technical_preview_readiness_audit.md").is_file()
    assert (PROJECT_ROOT / "examples/demo_workflow.md").is_file()


def test_portfolio_docs_exist_and_keep_technical_preview_framing() -> None:
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
    assert "not a hosted product deployment" in cv_description


def test_readme_includes_portfolio_demo_status_language() -> None:
    readme = _read("README.md").lower()

    assert "most ai tools answer known questions" in readme
    assert "--export-local-dashboard" in readme
    assert "v0.1.0-preview.md" in readme
    assert "ade v0.1.0 technical preview" in readme
    assert "implemented" in readme
    assert "foundation" in readme
    assert "planned" in readme
    assert "requires human review" in readme or "require human review" in readme
    assert "ade studio" in readme
    assert "local ade" in readme
    assert "mock preview" in readme
    assert "license.md" in readme


def test_ade_studio_frontend_package_metadata() -> None:
    package_path = PROJECT_ROOT / "apps/studio/frontend/package.json"
    package_data = json.loads(package_path.read_text(encoding="utf-8"))

    assert package_data["name"] == "ade-studio"
    assert package_data["version"] == "0.1.0"
    assert package_data["private"] is True
    for script in ["dev", "build", "start", "lint", "typecheck"]:
        assert script in package_data["scripts"]
    assert "@vercel/analytics" not in package_data.get("dependencies", {})


def test_ade_studio_docs_and_ui_keep_local_foundation_framing() -> None:
    checked_paths = [
        "apps/studio/README.md",
        "docs/ade_studio.md",
        "apps/studio/frontend/app/layout.tsx",
        "apps/studio/frontend/app/page.tsx",
        "apps/studio/frontend/components/ade/ade-studio.tsx",
        "apps/studio/frontend/components/ade/sidebar.tsx",
        "apps/studio/frontend/components/ade/topbar.tsx",
        "apps/studio/frontend/components/ade/primitives.tsx",
        "apps/studio/frontend/lib/ade-data.ts",
    ]

    for path in (PROJECT_ROOT / "apps/studio/frontend/components/ade/screens").glob("*.tsx"):
        checked_paths.append(str(path.relative_to(PROJECT_ROOT)))

    combined = "\n".join(_read(path) for path in checked_paths)
    lowered = combined.lower()

    assert "local ade engine" in lowered
    assert "mock preview" in lowered or "mock data" in lowered
    assert "requires human review" in lowered or "require human review" in lowered
    assert "v0.app" not in lowered
    assert "@vercel/analytics" not in lowered
    assert "private-alpha" not in lowered
    assert "private alpha" not in lowered
    assert "production saas" not in lowered
    assert "start discovery engine" not in lowered
    assert "live monitoring" not in lowered


def test_ade_studio_connected_mode_components_do_not_hardcode_mock_dataset_values() -> None:
    connected_component_paths = [
        "apps/studio/frontend/components/ade/ade-studio.tsx",
        "apps/studio/frontend/components/ade/execution-strip.tsx",
        "apps/studio/frontend/components/ade/topbar.tsx",
        "apps/studio/frontend/components/ade/screens/overview.tsx",
        "apps/studio/frontend/components/ade/screens/new-analysis.tsx",
        "apps/studio/frontend/components/ade/screens/runs.tsx",
        "apps/studio/frontend/components/ade/screens/reports.tsx",
        "apps/studio/frontend/components/ade/screens/findings.tsx",
        "apps/studio/frontend/components/ade/screens/projects.tsx",
        "apps/studio/frontend/components/ade/screens/benchmarks.tsx",
        "apps/studio/frontend/components/ade/screens/feedback.tsx",
    ]
    forbidden = [
        "Manufacturing QC Pipeline",
        "847,293",
        "PARQUET",
        "sensor_b1_v",
        "sensor_b2_v",
        "sensor_b3_v",
        "run_847_q4",
        "qc_sensor_2024",
        "Quarterly Performance Drift",
        "47h 12m",
    ]

    for path in connected_component_paths:
        text = _read(path)
        for phrase in forbidden:
            assert phrase not in text, f"{phrase!r} found in {path}"


def test_ade_studio_connected_mode_does_not_expose_inert_controls() -> None:
    checked_paths = [
        "apps/studio/frontend/components/ade/topbar.tsx",
        "apps/studio/frontend/components/ade/screens/new-analysis.tsx",
        "apps/studio/frontend/components/ade/screens/reports.tsx",
        "apps/studio/frontend/components/ade/screens/findings.tsx",
        "apps/studio/frontend/components/ade/screens/runs.tsx",
    ]
    combined = "\n".join(_read(path) for path in checked_paths)

    forbidden = [
        "Search reports...",
        "Search runs, reports, or evidence",
        "Review presets",
        "Export data",
        "Export</TechButton>",
        "Stage stepper",
    ]

    for phrase in forbidden:
        assert phrase not in combined

    assert "Studio feedback submission is not implemented in this Technical Preview" in combined
    assert "reportHtmlUrl" in combined
    assert "Clear form" in combined
    assert "onRefresh" in combined


def test_technical_preview_release_docs_are_release_ready_without_overclaiming() -> None:
    release_note = _read("docs/releases/v0.1.0-preview.md").lower()
    release_body = _read(
        "docs/releases/github_release_body_v0.1.0-preview.md"
    ).lower()
    demo_assets = _read("docs/demo_assets.md").lower()
    checklist = _read("docs/release_checklist.md").lower()

    assert "human review" in release_note
    assert "technical preview" in release_note
    assert "not a hosted product" in release_note
    assert "not a hosted product" in release_body
    assert "verify_local.py" in checklist
    assert "--export-local-dashboard" in checklist
    assert "git tag -a v0.1.0-preview" in checklist
    assert "do not commit generated private data" in demo_assets


def test_public_release_readiness_docs_exist_and_are_discoverable() -> None:
    docs_index = _read("docs/README.md").lower()
    security = _read("SECURITY.md").lower()
    extension_examples = _read("docs/extension_examples.md").lower()
    checklist = _read("docs/public_release_checklist.md").lower()
    demo_assets = _read("docs/demo_assets.md").lower()

    assert "local-first" in security
    assert "no intentional cloud upload" in security
    assert "formal security audit" in security
    assert "add a new adapter" in extension_examples
    assert "lightweight scoring backend" in extension_examples
    assert "custom report" in extension_examples
    assert "license is selected" in checklist
    assert "security.md" in checklist
    assert "ade studio overview" in demo_assets
    assert "findings review" in demo_assets
    assert "extension_examples.md" in docs_index
    assert "public_release_checklist.md" in docs_index
    assert "security.md" in docs_index


def test_license_notice_is_not_promoted_as_open_source_license() -> None:
    readme = _read("README.md").lower()
    license_text = _read("LICENSE.md").lower()
    checklist = _read("docs/public_release_checklist.md").lower()

    assert "all rights" in license_text and "reserved" in license_text
    assert "choose a public" in readme and "license before promoting" in readme
    assert "before promoting the repository as open source" in checklist


def test_project_release_docs_and_readme_do_not_use_old_release_branding() -> None:
    checked_paths = [
        "README.md",
        "docs/README.md",
        "docs/release_checklist.md",
        "docs/releases/technical_preview_readiness_audit.md",
        "docs/releases/v0.1.0-preview.md",
        "docs/releases/github_release_body_v0.1.0-preview.md",
        "SECURITY.md",
        "docs/extension_examples.md",
        "docs/public_release_checklist.md",
    ]
    forbidden = ["private-alpha", "private alpha", "Private Alpha"]

    for path in checked_paths:
        text = _read(path)
        for phrase in forbidden:
            assert phrase not in text, f"{phrase!r} found in {path}"


def test_public_docs_do_not_use_hosted_product_overclaims() -> None:
    checked_paths = [
        "README.md",
        "SECURITY.md",
        "docs/README.md",
        "docs/cv_project_description.md",
        "docs/extension_examples.md",
        "docs/portfolio_case_study.md",
        "docs/public_release_checklist.md",
        "docs/releases/v0.1.0-preview.md",
        "docs/releases/github_release_body_v0.1.0-preview.md",
    ]
    forbidden = [
        "production saas",
        "guaranteed detection",
        "fully autonomous truth",
        "cloud intelligence",
        "most-starred",
    ]

    for path in checked_paths:
        text = _read(path).lower()
        for phrase in forbidden:
            assert phrase not in text, f"{phrase!r} found in {path}"


def test_docs_do_not_claim_published_pip_package() -> None:
    checked_paths = [
        "README.md",
        "docs/README.md",
        "docs/cli_reference.md",
        "docs/development_workflow.md",
        "examples/demo_workflow.md",
    ]

    for path in checked_paths:
        text = _read(path).lower()
        assert "pip install ade" not in text, path
        assert "pip install ade-discovery-engine" not in text, path


def test_design_tokens_json_files_are_valid_when_present() -> None:
    for path in PROJECT_ROOT.rglob("design_tokens.json"):
        json.loads(path.read_text(encoding="utf-8"))

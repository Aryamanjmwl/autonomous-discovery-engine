"""Run the ADE demo pipeline with default local paths."""

from __future__ import annotations

from pathlib import Path

from ade.cli import run_pipeline


def main() -> None:
    """Execute the demo pipeline."""

    report_path = run_pipeline(
        input_dir=Path("data/raw"),
        output_path=Path("data/reports/demo_report.md"),
    )
    print(f"ADE demo report written to {report_path}")


if __name__ == "__main__":
    main()

"""Create deterministic CSV demo data for ADE tabular discovery."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("data/raw/demo_tabular")
DEFAULT_FILENAME = "operations.csv"


def build_rows() -> list[dict[str, object]]:
    """Return deterministic tabular rows with a few injected candidate anomalies."""

    rows: list[dict[str, object]] = []
    anomaly_rows = {
        13: {
            "amount": 945.0,
            "transactions": 6,
            "error_rate": 0.31,
            "latency_ms": 420,
            "status": "review",
            "anomaly_marker": "injected_high_amount_error",
        },
        29: {
            "amount": 8.0,
            "transactions": 38,
            "error_rate": 0.02,
            "latency_ms": 58,
            "status": "review",
            "anomaly_marker": "injected_volume_mismatch",
        },
        42: {
            "amount": 525.0,
            "transactions": 4,
            "error_rate": 0.19,
            "latency_ms": 610,
            "status": "review",
            "anomaly_marker": "injected_latency_spike",
        },
    }
    regions = ["north", "south", "east", "west"]
    segments = ["standard", "standard", "standard", "priority"]

    for row_id in range(1, 49):
        region = regions[row_id % len(regions)]
        segment = segments[row_id % len(segments)]
        amount = 96.0 + ((row_id * 7) % 29) + (5.0 if segment == "priority" else 0.0)
        transactions = 12 + (row_id % 5)
        error_rate = 0.01 + ((row_id % 4) * 0.01)
        latency_ms = 88 + ((row_id * 11) % 35)
        status = "ok"
        anomaly_marker = ""

        if row_id in anomaly_rows:
            injected = anomaly_rows[row_id]
            amount = float(injected["amount"])
            transactions = int(injected["transactions"])
            error_rate = float(injected["error_rate"])
            latency_ms = int(injected["latency_ms"])
            status = str(injected["status"])
            anomaly_marker = str(injected["anomaly_marker"])

        rows.append(
            {
                "row_id": f"demo-{row_id:03d}",
                "segment": segment,
                "region": region,
                "amount": f"{amount:.2f}",
                "transactions": transactions,
                "error_rate": f"{error_rate:.3f}",
                "latency_ms": latency_ms,
                "status": status,
                "anomaly_marker": anomaly_marker,
            }
        )
    return rows


def write_demo_csv(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Write the deterministic tabular demo CSV and return its path."""

    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / DEFAULT_FILENAME
    rows = build_rows()
    fieldnames = list(rows[0])
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    return output_path


def main() -> int:
    """Create local tabular demo data."""

    parser = argparse.ArgumentParser(description="Create ADE tabular demo CSV data.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated tabular demo data.",
    )
    args = parser.parse_args()

    output_path = write_demo_csv(args.output_dir)
    print(f"Output file: {output_path}")
    print(f"Rows created: {len(build_rows())}")
    print("Injected candidate anomaly markers: 3")
    print("Suggested ADE tabular command:")
    print(
        "python -m ade.cli --input "
        f"{output_path.as_posix()} --output data/reports/tabular_demo_report.md "
        "--modality tabular"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

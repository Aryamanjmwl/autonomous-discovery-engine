"""Create deterministic CSV demo data for ADE time-series discovery."""

from __future__ import annotations

import argparse
import csv
import math
from datetime import datetime, timedelta
from pathlib import Path

DEFAULT_OUTPUT_DIR = Path("data/raw/demo_timeseries")
DEFAULT_FILENAME = "machine_metrics.csv"


def build_rows() -> list[dict[str, object]]:
    """Return deterministic timestamped rows with injected candidate anomalies."""

    rows: list[dict[str, object]] = []
    start = datetime(2026, 7, 7, 0, 0, 0)
    anomaly_points = {
        18: {
            "temperature": 92.0,
            "pressure": 161.0,
            "throughput": 42.0,
            "anomaly_marker": "injected_temperature_pressure_spike",
        },
        47: {
            "temperature": 64.0,
            "pressure": 119.0,
            "throughput": 4.0,
            "anomaly_marker": "injected_throughput_drop",
        },
        73: {
            "temperature": 89.0,
            "pressure": 101.0,
            "throughput": 35.0,
            "anomaly_marker": "injected_temperature_spike",
        },
    }

    for index in range(96):
        timestamp = start + timedelta(minutes=15 * index)
        seasonal = math.sin((index / 96.0) * 2.0 * math.pi)
        short_cycle = math.sin((index / 12.0) * 2.0 * math.pi)
        temperature = 62.0 + (5.0 * seasonal) + (1.5 * short_cycle)
        pressure = 118.0 + (4.0 * seasonal) + ((index % 6) * 0.4)
        throughput = 30.0 + (3.0 * short_cycle) - (1.0 if index % 17 == 0 else 0.0)
        anomaly_marker = ""

        if index in anomaly_points:
            injected = anomaly_points[index]
            temperature = float(injected["temperature"])
            pressure = float(injected["pressure"])
            throughput = float(injected["throughput"])
            anomaly_marker = str(injected["anomaly_marker"])

        rows.append(
            {
                "timestamp": timestamp.isoformat(),
                "machine": "line-a",
                "temperature": f"{temperature:.3f}",
                "pressure": f"{pressure:.3f}",
                "throughput": f"{throughput:.3f}",
                "anomaly_marker": anomaly_marker,
            }
        )
    return rows


def write_demo_csv(output_dir: Path = DEFAULT_OUTPUT_DIR) -> Path:
    """Write the deterministic time-series demo CSV and return its path."""

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
    """Create local time-series demo data."""

    parser = argparse.ArgumentParser(description="Create ADE time-series demo CSV data.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for generated time-series demo data.",
    )
    args = parser.parse_args()

    output_path = write_demo_csv(args.output_dir)
    print(f"Output file: {output_path}")
    print(f"Rows created: {len(build_rows())}")
    print("Injected candidate anomaly markers: 3")
    print("Suggested ADE time-series command:")
    print(
        "python -m ade.cli --input "
        f"{output_path.as_posix()} --output data/reports/timeseries_demo_report.md "
        "--modality timeseries --timestamp-column timestamp --entity-column machine"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

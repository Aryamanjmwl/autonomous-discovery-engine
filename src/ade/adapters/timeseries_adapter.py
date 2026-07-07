"""CSV adapter for lightweight time-series ADE datasets."""

from __future__ import annotations

import csv
from collections import Counter
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

from ade.models import ADERecord, DatasetSummary, TimeSeriesProfile, TimeSeriesRecord

DEFAULT_MISSING_VALUE_TOKENS = {"", "na", "n/a", "nan", "null", "none"}
TIMESTAMP_CANDIDATES = ("timestamp", "time", "datetime", "date", "ts")


class TimeSeriesAdapter:
    """Load timestamped CSV rows and profile basic time-series structure."""

    name = "timeseries_csv"

    def __init__(
        self,
        input_path: Path | str,
        timestamp_column: str | None = None,
        entity_column: str | None = None,
        missing_value_tokens: set[str] | None = None,
    ) -> None:
        self.input_path = Path(input_path)
        self.timestamp_column = timestamp_column
        self.entity_column = entity_column
        self.missing_value_tokens = {
            token.lower() for token in (missing_value_tokens or DEFAULT_MISSING_VALUE_TOKENS)
        }

    def validate(self) -> None:
        """Raise a clear exception if the CSV input cannot be read."""

        if not self.input_path.exists():
            raise FileNotFoundError(f"Time-series CSV path does not exist: {self.input_path}")
        if not self.input_path.is_file():
            raise ValueError(f"Time-series input must be a CSV file: {self.input_path}")
        if self.input_path.suffix.lower() != ".csv":
            raise ValueError(f"Time-series input must be a .csv file: {self.input_path}")
        if self.input_path.stat().st_size == 0:
            raise ValueError(f"Time-series CSV is empty: {self.input_path}")

    def load(self) -> list[TimeSeriesRecord]:
        """Return valid timestamped records sorted by entity and timestamp."""

        return list(self.iter_records())

    def iter_records(self) -> Iterator[TimeSeriesRecord]:
        """Yield valid timestamped records in deterministic time order."""

        header, rows, _warnings = self._read_csv()
        timestamp_column = self._resolve_timestamp_column(header)
        entity_column = self._resolve_entity_column(header)
        parsed_rows = []
        for row_index, row in enumerate(rows, start=1):
            timestamp_text = row.get(timestamp_column, "")
            parsed_timestamp = _parse_timestamp(timestamp_text)
            if parsed_timestamp is None:
                continue
            entity_id = row.get(entity_column, "") if entity_column else None
            parsed_rows.append((entity_id or "", parsed_timestamp, row_index, row))

        for entity_id, parsed_timestamp, row_index, row in sorted(parsed_rows):
            yield TimeSeriesRecord(
                record_id=f"ts-{row_index:06d}",
                source_path=self.input_path,
                row_index=row_index,
                timestamp=parsed_timestamp.isoformat(),
                entity_id=entity_id or None,
                values={column: row.get(column, "") for column in header},
                metadata={"timestamp_column": timestamp_column},
            )

    def iter_ade_records(self) -> Iterator[ADERecord]:
        """Yield time-series points as generic ADE records."""

        for record in self.iter_records():
            yield record.to_ade_record()

    def summarize(self) -> DatasetSummary:
        """Return a lightweight summary for the time-series input."""

        profile = self.profile()
        return DatasetSummary(
            input_path=self.input_path,
            input_type=self.name,
            record_count=profile.row_count,
            metadata={
                "timestamp_column": profile.timestamp_column,
                "entity_column": profile.entity_column,
                "signal_columns": profile.signal_columns,
                "time_start": profile.time_start,
                "time_end": profile.time_end,
            },
        )

    def profile(self) -> TimeSeriesProfile:
        """Return a deterministic profile for a timestamped CSV file."""

        header, rows, warnings = self._read_csv()
        timestamp_column = self._resolve_timestamp_column(header)
        entity_column = self._resolve_entity_column(header)
        missing_summary = {column: 0 for column in header}
        signal_values: dict[str, list[str]] = {
            column: []
            for column in header
            if column not in {timestamp_column, entity_column}
        }
        parsed_timestamps: list[datetime] = []
        timestamp_keys: list[tuple[str, datetime]] = []
        missing_timestamp_count = 0
        malformed_timestamp_count = 0

        for row in rows:
            for column in header:
                if self._is_missing(row.get(column, "")):
                    missing_summary[column] += 1

            timestamp_text = row.get(timestamp_column, "")
            if self._is_missing(timestamp_text):
                missing_timestamp_count += 1
                continue
            parsed_timestamp = _parse_timestamp(timestamp_text)
            if parsed_timestamp is None:
                malformed_timestamp_count += 1
                continue
            parsed_timestamps.append(parsed_timestamp)
            entity_id = row.get(entity_column, "") if entity_column else ""
            timestamp_keys.append((entity_id, parsed_timestamp))

            for column in signal_values:
                value = row.get(column, "")
                if not self._is_missing(value):
                    signal_values[column].append(value.strip())

        signal_columns = [
            column
            for column, values in signal_values.items()
            if values and all(_to_float(value) is not None for value in values)
        ]
        if not signal_columns:
            warnings.append("No numeric signal columns detected.")
        duplicate_count = _duplicate_count(timestamp_keys)
        if duplicate_count:
            warnings.append(f"Duplicate timestamp rows found: {duplicate_count}")
        if missing_timestamp_count:
            warnings.append(f"Rows with missing timestamps: {missing_timestamp_count}")
        if malformed_timestamp_count:
            warnings.append(f"Rows with malformed timestamps: {malformed_timestamp_count}")

        interval_summary = _sampling_summary(parsed_timestamps)
        if interval_summary.get("irregular"):
            warnings.append("Timestamp intervals appear irregular.")

        return TimeSeriesProfile(
            input_path=self.input_path,
            timestamp_column=timestamp_column,
            entity_column=entity_column,
            row_count=len(parsed_timestamps),
            column_count=len(header),
            columns=header,
            signal_columns=signal_columns,
            time_start=min(parsed_timestamps).isoformat() if parsed_timestamps else None,
            time_end=max(parsed_timestamps).isoformat() if parsed_timestamps else None,
            sampling_interval_summary=interval_summary,
            missing_value_summary=missing_summary,
            missing_timestamp_count=missing_timestamp_count,
            malformed_timestamp_count=malformed_timestamp_count,
            duplicate_timestamp_count=duplicate_count,
            warnings=warnings,
            is_valid=bool(parsed_timestamps and signal_columns),
        )

    def _read_csv(self) -> tuple[list[str], list[dict[str, str]], list[str]]:
        """Read a CSV file and return header, rows, and warnings."""

        self.validate()
        try:
            with self.input_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, restkey="__extra__", restval="")
                fieldnames = [str(name).strip() for name in (reader.fieldnames or [])]
                if not fieldnames:
                    raise ValueError(f"Time-series CSV has no header row: {self.input_path}")
                rows: list[dict[str, str]] = []
                warnings: list[str] = []
                for row_number, row in enumerate(reader, start=2):
                    extra = row.pop("__extra__", None)
                    if extra:
                        warnings.append(
                            f"Row {row_number} has more fields than the header; extra fields were ignored."
                        )
                    rows.append(
                        {
                            column: _clean_cell(row.get(column, ""))
                            for column in fieldnames
                        }
                    )
        except UnicodeDecodeError as error:
            raise ValueError(f"Time-series CSV could not be decoded as UTF-8: {self.input_path}") from error
        except csv.Error as error:
            raise ValueError(f"Time-series CSV is malformed: {self.input_path}") from error
        return fieldnames, rows, warnings

    def _resolve_timestamp_column(self, header: list[str]) -> str:
        """Return configured or safely detected timestamp column."""

        if self.timestamp_column:
            if self.timestamp_column not in header:
                raise ValueError(
                    f"Timestamp column '{self.timestamp_column}' was not found in: {self.input_path}"
                )
            return self.timestamp_column
        lowered = {column.lower(): column for column in header}
        for candidate in TIMESTAMP_CANDIDATES:
            if candidate in lowered:
                return lowered[candidate]
        raise ValueError(
            "Could not detect a timestamp column. Set timeseries.timestamp_column "
            "or pass --timestamp-column."
        )

    def _resolve_entity_column(self, header: list[str]) -> str | None:
        """Return configured entity column when available."""

        if self.entity_column is None:
            return None
        if self.entity_column not in header:
            raise ValueError(
                f"Entity column '{self.entity_column}' was not found in: {self.input_path}"
            )
        return self.entity_column

    def _is_missing(self, value: str) -> bool:
        """Return True when a value should be treated as missing."""

        return value.strip().lower() in self.missing_value_tokens


def _clean_cell(value: object) -> str:
    """Return a normalized string cell value."""

    if value is None:
        return ""
    return str(value).strip()


def _to_float(value: str) -> float | None:
    """Parse a finite float value when possible."""

    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if parsed == parsed and parsed not in {float("inf"), float("-inf")} else None


def _parse_timestamp(value: str) -> datetime | None:
    """Parse an ISO-like timestamp."""

    text = value.strip()
    if not text:
        return None
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        return datetime.fromisoformat(text)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y %H:%M:%S", "%m/%d/%Y"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _duplicate_count(keys: list[tuple[str, datetime]]) -> int:
    """Return duplicate timestamp/entity key count."""

    counts = Counter(keys)
    return sum(count - 1 for count in counts.values() if count > 1)


def _sampling_summary(timestamps: list[datetime]) -> dict[str, Any]:
    """Return a simple sampling interval summary in seconds."""

    if len(timestamps) <= 1:
        return {
            "count": 0,
            "min_seconds": None,
            "median_seconds": None,
            "max_seconds": None,
            "irregular": False,
        }
    ordered = sorted(timestamps)
    intervals = [
        max(0.0, (current - previous).total_seconds())
        for previous, current in zip(ordered, ordered[1:])
    ]
    intervals_sorted = sorted(intervals)
    median = intervals_sorted[len(intervals_sorted) // 2]
    interval_min = min(intervals_sorted)
    interval_max = max(intervals_sorted)
    return {
        "count": len(intervals_sorted),
        "min_seconds": float(interval_min),
        "median_seconds": float(median),
        "max_seconds": float(interval_max),
        "irregular": bool(interval_max > interval_min),
    }

"""CSV adapter for lightweight tabular ADE datasets."""

from __future__ import annotations

import csv
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from ade.models import ADERecord, DatasetSummary, TabularProfile, TabularRecord

DEFAULT_MISSING_VALUE_TOKENS = {"", "na", "n/a", "nan", "null", "none"}


class TabularAdapter:
    """Load CSV rows and profile basic tabular structure."""

    name = "tabular_csv"

    def __init__(
        self,
        input_path: Path | str,
        missing_value_tokens: set[str] | None = None,
        max_categorical_cardinality: int = 50,
    ) -> None:
        self.input_path = Path(input_path)
        self.missing_value_tokens = {
            token.lower() for token in (missing_value_tokens or DEFAULT_MISSING_VALUE_TOKENS)
        }
        self.max_categorical_cardinality = max_categorical_cardinality

    def validate(self) -> None:
        """Raise a clear exception if the CSV input cannot be read."""

        if not self.input_path.exists():
            raise FileNotFoundError(f"CSV input path does not exist: {self.input_path}")
        if not self.input_path.is_file():
            raise ValueError(f"CSV input path must be a file: {self.input_path}")
        if self.input_path.suffix.lower() != ".csv":
            raise ValueError(f"Tabular input must be a .csv file: {self.input_path}")
        if self.input_path.stat().st_size == 0:
            raise ValueError(f"CSV input is empty: {self.input_path}")

    def load(self) -> list[TabularRecord]:
        """Return CSV row records in file order."""

        return list(self.iter_records())

    def iter_records(self) -> Iterator[TabularRecord]:
        """Yield row records in deterministic order."""

        header, rows, _warnings = self._read_csv()
        for row_index, row in enumerate(rows, start=1):
            values = {column: row.get(column, "") for column in header}
            yield TabularRecord(
                record_id=f"row-{row_index:06d}",
                source_path=self.input_path,
                row_index=row_index,
                values=values,
            )

    def iter_ade_records(self) -> Iterator[ADERecord]:
        """Yield row records as generic ADE records."""

        for record in self.iter_records():
            yield record.to_ade_record()

    def summarize(self) -> DatasetSummary:
        """Return a lightweight summary for the CSV input."""

        profile = self.profile()
        return DatasetSummary(
            input_path=self.input_path,
            input_type=self.name,
            record_count=profile.row_count,
            metadata={
                "row_count": profile.row_count,
                "column_count": profile.column_count,
                "numeric_columns": profile.numeric_columns,
                "categorical_columns": profile.categorical_columns,
            },
        )

    def profile(self) -> TabularProfile:
        """Return a deterministic CSV profile."""

        header, rows, warnings = self._read_csv()
        missing_summary = {column: 0 for column in header}
        non_missing_values: dict[str, list[str]] = {column: [] for column in header}

        for row in rows:
            for column in header:
                value = row.get(column, "")
                if self._is_missing(value):
                    missing_summary[column] += 1
                else:
                    non_missing_values[column].append(value.strip())

        numeric_columns: list[str] = []
        categorical_columns: list[str] = []
        column_metadata: dict[str, dict[str, Any]] = {}
        for column in header:
            values = non_missing_values[column]
            numeric_values = [_to_float(value) for value in values]
            numeric_count = sum(value is not None for value in numeric_values)
            unique_count = len(set(values))
            is_numeric = bool(values) and numeric_count == len(values)
            if is_numeric:
                numeric_columns.append(column)
            else:
                categorical_columns.append(column)
                if unique_count > self.max_categorical_cardinality:
                    warnings.append(
                        f"Column '{column}' has high categorical cardinality: {unique_count}"
                    )
            column_metadata[column] = {
                "missing_count": missing_summary[column],
                "non_missing_count": len(values),
                "unique_count": unique_count,
                "detected_type": "numeric" if is_numeric else "categorical",
            }

        if not rows:
            warnings.append("CSV contains a header but no data rows.")
        if not numeric_columns:
            warnings.append("No numeric columns detected; discovery will use categorical signals.")

        return TabularProfile(
            input_path=self.input_path,
            row_count=len(rows),
            column_count=len(header),
            columns=header,
            numeric_columns=numeric_columns,
            categorical_columns=categorical_columns,
            missing_value_summary=missing_summary,
            column_metadata=column_metadata,
            warnings=warnings,
            is_valid=bool(header and rows),
        )

    def _read_csv(self) -> tuple[list[str], list[dict[str, str]], list[str]]:
        """Read a CSV file and return header, rows, and warnings."""

        self.validate()
        try:
            with self.input_path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle, restkey="__extra__", restval="")
                fieldnames = [str(name).strip() for name in (reader.fieldnames or [])]
                if not fieldnames:
                    raise ValueError(f"CSV input has no header row: {self.input_path}")
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
            raise ValueError(f"CSV input could not be decoded as UTF-8: {self.input_path}") from error
        except csv.Error as error:
            raise ValueError(f"CSV input is malformed: {self.input_path}") from error
        return fieldnames, rows, warnings

    def _is_missing(self, value: str) -> bool:
        """Return True when a cell value should be treated as missing."""

        return value.strip().lower() in self.missing_value_tokens


def _clean_cell(value: object) -> str:
    """Return a normalized string cell value."""

    if value is None:
        return ""
    return str(value).strip()


def _to_float(value: str) -> float | None:
    """Parse a float value when possible."""

    try:
        parsed = float(value)
    except ValueError:
        return None
    return parsed if parsed == parsed and parsed not in {float("inf"), float("-inf")} else None

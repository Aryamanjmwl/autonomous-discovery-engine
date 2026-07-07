"""Lightweight deterministic feature extraction for tabular rows."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ade.models import TabularProfile, TabularRecord


@dataclass(frozen=True)
class TabularEmbeddingRecord:
    """Feature vector and metadata for one tabular row."""

    record: TabularRecord
    vector: np.ndarray
    feature_names: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe embedding metadata without dumping full vectors."""

        return {
            "record_id": self.record.record_id,
            "row_index": int(self.record.row_index),
            "source_path": self.record.source_path.as_posix(),
            "vector_length": int(self.vector.size),
            "feature_names": list(self.feature_names),
            "metadata": dict(self.metadata),
        }


class TabularFeatureEngine:
    """Create simple row-level feature vectors from CSV records."""

    name = "statistical_tabular_row"

    def __init__(self, missing_value_tokens: set[str] | None = None) -> None:
        self.missing_value_tokens = {
            token.lower()
            for token in (missing_value_tokens or {"", "na", "n/a", "nan", "null", "none"})
        }

    def embed(
        self,
        records: list[TabularRecord],
        profile: TabularProfile,
    ) -> list[TabularEmbeddingRecord]:
        """Return deterministic tabular row embeddings."""

        if not records:
            return []

        numeric_stats = self._numeric_stats(records, profile.numeric_columns)
        categorical_counts = self._categorical_counts(records, profile.categorical_columns)
        feature_names = self._feature_names(profile)
        embeddings: list[TabularEmbeddingRecord] = []
        for record in records:
            vector, metadata = self._row_vector(
                record=record,
                profile=profile,
                numeric_stats=numeric_stats,
                categorical_counts=categorical_counts,
            )
            embeddings.append(
                TabularEmbeddingRecord(
                    record=record,
                    vector=vector,
                    feature_names=feature_names,
                    metadata=metadata,
                )
            )
        return embeddings

    def _row_vector(
        self,
        record: TabularRecord,
        profile: TabularProfile,
        numeric_stats: dict[str, tuple[float, float]],
        categorical_counts: dict[str, Counter[str]],
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Return one row vector and compact feature metadata."""

        features: list[float] = []
        missing_columns: list[str] = []
        numeric_deviations: dict[str, float] = {}
        categorical_rarity: dict[str, float] = {}

        for column in profile.numeric_columns:
            raw_value = record.values.get(column, "")
            if self._is_missing(raw_value):
                missing_columns.append(column)
                features.append(0.0)
                features.append(1.0)
                numeric_deviations[column] = 0.0
                continue
            parsed = _to_float(raw_value)
            mean, scale = numeric_stats[column]
            deviation = 0.0 if parsed is None else (parsed - mean) / scale
            features.append(float(deviation))
            features.append(0.0)
            numeric_deviations[column] = float(deviation)

        row_count = max(1, profile.row_count)
        for column in profile.categorical_columns:
            raw_value = record.values.get(column, "")
            if self._is_missing(raw_value):
                missing_columns.append(column)
                rarity = 1.0
                features.append(rarity)
                features.append(1.0)
                categorical_rarity[column] = rarity
                continue
            value = raw_value.strip()
            frequency = categorical_counts[column][value] / row_count
            rarity = 1.0 - frequency
            features.append(float(rarity))
            features.append(0.0)
            categorical_rarity[column] = float(rarity)

        completeness = (
            1.0 - (len(set(missing_columns)) / profile.column_count)
            if profile.column_count
            else 0.0
        )
        features.append(float(completeness))
        vector = np.nan_to_num(
            np.asarray(features, dtype=np.float32),
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        return vector, {
            "missing_columns": sorted(set(missing_columns)),
            "numeric_deviations": numeric_deviations,
            "categorical_rarity": categorical_rarity,
            "completeness_ratio": float(completeness),
        }

    def _numeric_stats(
        self,
        records: list[TabularRecord],
        numeric_columns: list[str],
    ) -> dict[str, tuple[float, float]]:
        """Return mean and scale for numeric columns."""

        stats: dict[str, tuple[float, float]] = {}
        for column in numeric_columns:
            values = [
                parsed
                for record in records
                if not self._is_missing(record.values.get(column, ""))
                for parsed in [_to_float(record.values.get(column, ""))]
                if parsed is not None
            ]
            if not values:
                stats[column] = (0.0, 1.0)
                continue
            array = np.asarray(values, dtype=np.float32)
            mean = float(array.mean())
            std = float(array.std())
            stats[column] = (mean, std if std > 1e-12 else 1.0)
        return stats

    def _categorical_counts(
        self,
        records: list[TabularRecord],
        categorical_columns: list[str],
    ) -> dict[str, Counter[str]]:
        """Return frequency counts for non-missing categorical values."""

        counts: dict[str, Counter[str]] = {}
        for column in categorical_columns:
            counter: Counter[str] = Counter()
            for record in records:
                value = record.values.get(column, "")
                if not self._is_missing(value):
                    counter[value.strip()] += 1
            counts[column] = counter
        return counts

    @staticmethod
    def _feature_names(profile: TabularProfile) -> list[str]:
        """Return feature names in vector order."""

        names: list[str] = []
        for column in profile.numeric_columns:
            names.extend([f"{column}:numeric_z", f"{column}:missing"])
        for column in profile.categorical_columns:
            names.extend([f"{column}:categorical_rarity", f"{column}:missing"])
        names.append("row:completeness_ratio")
        return names

    def _is_missing(self, value: str) -> bool:
        """Return True when a cell is configured as missing."""

        return value.strip().lower() in self.missing_value_tokens


def _to_float(value: str) -> float | None:
    """Parse a finite float value when possible."""

    try:
        parsed = float(value)
    except ValueError:
        return None
    if not np.isfinite(parsed):
        return None
    return float(parsed)

"""Lightweight deterministic feature extraction for time-series records."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import numpy as np

from ade.models import TimeSeriesProfile, TimeSeriesRecord


@dataclass(frozen=True)
class TimeSeriesEmbeddingRecord:
    """Feature vector and metadata for one timestamped point."""

    record: TimeSeriesRecord
    vector: np.ndarray
    feature_names: list[str]
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Return JSON-safe embedding metadata without dumping full vectors."""

        return {
            "record_id": self.record.record_id,
            "row_index": int(self.record.row_index),
            "timestamp": self.record.timestamp,
            "source_path": self.record.source_path.as_posix(),
            "vector_length": int(self.vector.size),
            "feature_names": list(self.feature_names),
            "metadata": dict(self.metadata),
        }


class TimeSeriesFeatureEngine:
    """Create simple point-level feature vectors from timestamped records."""

    name = "statistical_timeseries_point"

    def __init__(
        self,
        window_size: int = 3,
        missing_value_tokens: set[str] | None = None,
    ) -> None:
        self.window_size = max(1, window_size)
        self.missing_value_tokens = {
            token.lower()
            for token in (missing_value_tokens or {"", "na", "n/a", "nan", "null", "none"})
        }

    def embed(
        self,
        records: list[TimeSeriesRecord],
        profile: TimeSeriesProfile,
    ) -> list[TimeSeriesEmbeddingRecord]:
        """Return deterministic time-series embeddings."""

        if not records:
            return []
        ordered = sorted(records, key=lambda item: (item.entity_id or "", item.timestamp, item.row_index))
        stats = self._signal_stats(ordered, profile.signal_columns)
        baseline_gap = _baseline_gap_seconds(ordered)
        feature_names = self._feature_names(profile)
        by_entity: dict[str, list[TimeSeriesRecord]] = {}
        for record in ordered:
            by_entity.setdefault(record.entity_id or "", []).append(record)

        embeddings: list[TimeSeriesEmbeddingRecord] = []
        for entity_records in by_entity.values():
            for index, record in enumerate(entity_records):
                vector, metadata = self._record_vector(
                    record=record,
                    entity_records=entity_records,
                    index=index,
                    profile=profile,
                    stats=stats,
                    baseline_gap_seconds=baseline_gap,
                )
                embeddings.append(
                    TimeSeriesEmbeddingRecord(
                        record=record,
                        vector=vector,
                        feature_names=feature_names,
                        metadata=metadata,
                    )
                )
        embeddings.sort(key=lambda item: item.record.row_index)
        return embeddings

    def _record_vector(
        self,
        record: TimeSeriesRecord,
        entity_records: list[TimeSeriesRecord],
        index: int,
        profile: TimeSeriesProfile,
        stats: dict[str, tuple[float, float]],
        baseline_gap_seconds: float,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        """Return one point vector and compact metadata."""

        previous = entity_records[index - 1] if index > 0 else None
        previous_timestamp = _parse_timestamp(previous.timestamp) if previous else None
        current_timestamp = _parse_timestamp(record.timestamp)
        gap_seconds = (
            max(0.0, (current_timestamp - previous_timestamp).total_seconds())
            if current_timestamp and previous_timestamp
            else 0.0
        )
        time_gap_indicator = (
            1.0
            if baseline_gap_seconds > 0 and gap_seconds > baseline_gap_seconds
            else 0.0
        )

        features: list[float] = []
        missing_signals: list[str] = []
        signal_deltas: dict[str, float] = {}
        spike_signals: list[str] = []
        for signal in profile.signal_columns:
            raw_value = record.values.get(signal, "")
            value = _to_float(raw_value)
            mean, scale = stats[signal]
            if value is None or self._is_missing(raw_value):
                missing_signals.append(signal)
                normalized = 0.0
                missing_indicator = 1.0
            else:
                normalized = (value - mean) / scale
                missing_indicator = 0.0
            previous_value = _to_float(previous.values.get(signal, "")) if previous else None
            delta = 0.0 if value is None or previous_value is None else (value - previous_value) / scale
            history = _history_values(entity_records, signal, end_index=index, window_size=self.window_size)
            rolling_mean = float(np.mean(history)) if history else mean
            rolling_std = float(np.std(history)) if len(history) > 1 else 0.0
            rolling_mean_delta = 0.0 if value is None else (value - rolling_mean) / scale
            rolling_std_scaled = rolling_std / scale
            spike = 1.0 if abs(delta) > 2.0 or abs(rolling_mean_delta) > 2.0 else 0.0
            if spike:
                spike_signals.append(signal)
            signal_deltas[signal] = float(delta)
            features.extend(
                [
                    float(normalized),
                    float(missing_indicator),
                    float(delta),
                    float(abs(delta)),
                    float(rolling_mean_delta),
                    float(rolling_std_scaled),
                    float(spike),
                ]
            )

        completeness = (
            1.0 - len(set(missing_signals)) / len(profile.signal_columns)
            if profile.signal_columns
            else 0.0
        )
        features.extend([float(time_gap_indicator), float(completeness)])
        vector = np.nan_to_num(
            np.asarray(features, dtype=np.float32),
            nan=0.0,
            posinf=0.0,
            neginf=0.0,
        )
        return vector, {
            "timestamp": record.timestamp,
            "entity_id": record.entity_id,
            "gap_seconds": float(gap_seconds),
            "time_gap_indicator": float(time_gap_indicator),
            "missing_signals": sorted(set(missing_signals)),
            "signal_deltas": signal_deltas,
            "spike_signals": sorted(set(spike_signals)),
            "completeness_ratio": float(completeness),
        }

    def _signal_stats(
        self,
        records: list[TimeSeriesRecord],
        signal_columns: list[str],
    ) -> dict[str, tuple[float, float]]:
        """Return mean and scale for each numeric signal."""

        stats: dict[str, tuple[float, float]] = {}
        for signal in signal_columns:
            values = [
                parsed
                for record in records
                if not self._is_missing(record.values.get(signal, ""))
                for parsed in [_to_float(record.values.get(signal, ""))]
                if parsed is not None
            ]
            if not values:
                stats[signal] = (0.0, 1.0)
                continue
            array = np.asarray(values, dtype=np.float32)
            mean = float(array.mean())
            std = float(array.std())
            stats[signal] = (mean, std if std > 1e-12 else 1.0)
        return stats

    @staticmethod
    def _feature_names(profile: TimeSeriesProfile) -> list[str]:
        """Return feature names in vector order."""

        names: list[str] = []
        for signal in profile.signal_columns:
            names.extend(
                [
                    f"{signal}:value_z",
                    f"{signal}:missing",
                    f"{signal}:delta_z",
                    f"{signal}:abs_delta_z",
                    f"{signal}:rolling_mean_delta_z",
                    f"{signal}:rolling_std_z",
                    f"{signal}:spike_indicator",
                ]
            )
        names.extend(["time:gap_indicator", "row:completeness_ratio"])
        return names

    def _is_missing(self, value: str) -> bool:
        """Return True when a value should be treated as missing."""

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


def _parse_timestamp(value: str) -> datetime | None:
    """Parse an ISO timestamp emitted by the adapter."""

    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _history_values(
    records: list[TimeSeriesRecord],
    signal: str,
    end_index: int,
    window_size: int,
) -> list[float]:
    """Return numeric signal values before and including the current point."""

    start = max(0, end_index - window_size + 1)
    values: list[float] = []
    for record in records[start : end_index + 1]:
        parsed = _to_float(record.values.get(signal, ""))
        if parsed is not None:
            values.append(parsed)
    return values


def _baseline_gap_seconds(records: list[TimeSeriesRecord]) -> float:
    """Return median positive timestamp gap across records."""

    timestamps = sorted(
        timestamp
        for record in records
        for timestamp in [_parse_timestamp(record.timestamp)]
        if timestamp is not None
    )
    gaps = [
        (current - previous).total_seconds()
        for previous, current in zip(timestamps, timestamps[1:])
        if (current - previous).total_seconds() > 0
    ]
    if not gaps:
        return 0.0
    gaps.sort()
    return float(gaps[len(gaps) // 2])

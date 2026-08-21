"""Cooperative cancellation primitives for long-running ADE workflows."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


class CancellationRequested(RuntimeError):
    """Raised when a workflow reaches a cancellation checkpoint."""


@dataclass(frozen=True)
class CancellationToken:
    """Read cancellation state and protect the final publication boundary."""

    _is_requested: Callable[[], bool]
    _begin_finalization: Callable[[], bool]

    def checkpoint(self) -> None:
        """Stop at a safe workflow boundary when cancellation was requested."""

        if self._is_requested():
            raise CancellationRequested("Workflow cancellation was requested")

    def begin_finalization(self) -> None:
        """Enter the non-interruptible publication boundary or stop first."""

        self.checkpoint()
        if not self._begin_finalization():
            raise CancellationRequested("Workflow cancellation was requested")

    @classmethod
    def disabled(cls) -> CancellationToken:
        """Return a token for callers that do not support cancellation."""

        return cls(lambda: False, lambda: True)

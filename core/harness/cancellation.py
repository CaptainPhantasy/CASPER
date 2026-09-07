"""Cooperative cancellation shared by bounded harness operations."""

from __future__ import annotations

import threading
from collections.abc import Callable


class CancellationError(RuntimeError):
    """Raised when a cancelled operation reaches a cancellation boundary."""


class CancellationToken:
    """Thread-safe, one-way cancellation signal with optional child tokens."""

    def __init__(self, parent: "CancellationToken | None" = None) -> None:
        self._event = threading.Event()
        self._reason = ""
        self._callbacks: list[Callable[[str], None]] = []
        self._lock = threading.Lock()
        if parent is not None:
            def cancel_child(reason: str) -> None:
                self.cancel(reason)

            parent.add_callback(cancel_child)

    @property
    def cancelled(self) -> bool:
        return self._event.is_set()

    @property
    def reason(self) -> str:
        return self._reason

    def cancel(self, reason: str = "cancelled by operator") -> bool:
        """Cancel once and invoke callbacks. Return false if already cancelled."""
        with self._lock:
            if self._event.is_set():
                return False
            self._reason = reason.strip() or "cancelled"
            self._event.set()
            callbacks = tuple(self._callbacks)
            self._callbacks.clear()
        for callback in callbacks:
            callback(self._reason)
        return True

    def add_callback(self, callback: Callable[[str], None]) -> None:
        with self._lock:
            if not self._event.is_set():
                self._callbacks.append(callback)
                return
            reason = self._reason
        callback(reason)

    def raise_if_cancelled(self) -> None:
        if self.cancelled:
            raise CancellationError(self.reason)

    def child(self) -> "CancellationToken":
        return CancellationToken(self)

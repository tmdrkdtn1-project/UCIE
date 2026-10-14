"""Stage-3 bounded scheduling policy, offline only.

This module prepares next-run decisions; it never registers a task or sleeps.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .core import MiningError

INTERVAL = timedelta(hours=1)
MAX_FAILURES = 6


def next_cycle(last_finished: datetime | None, *, now: datetime,
               consecutive_failures: int = 0) -> dict:
    """Fail closed on invalid clocks; exponential retry capped at one hour."""
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise MiningError("UTC-aware clock required")
    if type(consecutive_failures) is not int or not 0 <= consecutive_failures <= MAX_FAILURES:
        raise MiningError("failure counter outside bounds")
    if last_finished is None:
        return {"decision": "DUE", "retry_after_seconds": 0}
    if last_finished.tzinfo is None or last_finished.utcoffset() != timedelta(0):
        raise MiningError("UTC-aware prior completion required")
    if last_finished > now:
        raise MiningError("future prior completion")
    delay = INTERVAL if consecutive_failures == 0 else timedelta(
        minutes=min(60, 2 ** consecutive_failures))
    seconds = max(0, int((last_finished + delay - now).total_seconds()))
    return {"decision": "DUE" if seconds == 0 else "WAIT",
            "retry_after_seconds": seconds}

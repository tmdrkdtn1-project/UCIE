"""Stage-3 bounded scheduling policy, offline only.

This module prepares next-run decisions; it never registers a task or sleeps.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from .core import MiningError

INTERVAL = timedelta(hours=1)
# The hourly OS trigger is scheduled on a fixed wall-clock boundary; a prior
# collector may start seconds later. Permit bounded trigger jitter without
# skipping the alternate hour. The OS single-instance lock still applies.
SUCCESS_TRIGGER_JITTER = timedelta(seconds=30)
# A failed cycle can finish seconds after a fixed Windows hourly trigger.
# Permit 15 seconds of skew only for the capped 60-minute failure backoff.
FAILURE_TRIGGER_JITTER = timedelta(seconds=15)
MAX_FAILURES = 6


def next_cycle(last_finished: datetime | None, *, now: datetime,
               consecutive_failures: int = 0,
               last_started: datetime | None = None) -> dict:
    """Hourly start-to-start cadence with bounded failed-trigger tolerance.

    Windows Task Scheduler fires at the previous scheduled START + 1 hour.
    Gating from FINISH + 1 hour skips alternate tasks after even an 8-second
    successful run. Bound normal trigger/start skew to 30 seconds, while
    permitting only 15 seconds of skew at the capped 60-minute failed retry.
    The OS lock prevents overlaps; no retry may be due before last finish.
    Older receipts lacking a start timestamp preserve their old policy.
    """
    if now.tzinfo is None or now.utcoffset() != timedelta(0):
        raise MiningError("UTC-aware clock required")
    if type(consecutive_failures) is not int or not 0 <= consecutive_failures <= MAX_FAILURES:
        raise MiningError("failure counter outside bounds")
    if last_finished is None:
        if last_started is not None:
            raise MiningError("start timestamp without prior completion")
        return {"decision": "DUE", "retry_after_seconds": 0}
    if last_finished.tzinfo is None or last_finished.utcoffset() != timedelta(0):
        raise MiningError("UTC-aware prior completion required")
    if last_finished > now:
        raise MiningError("future prior completion")
    if last_started is not None:
        if (last_started.tzinfo is None
                or last_started.utcoffset() != timedelta(0)
                or last_started > last_finished):
            raise MiningError("invalid prior start/completion ordering")
    if consecutive_failures == 0 and last_started is not None:
        due_at = max(last_started + INTERVAL - SUCCESS_TRIGGER_JITTER,
                     last_finished)
    else:
        delay = INTERVAL if consecutive_failures == 0 else timedelta(
            minutes=min(60, 2 ** consecutive_failures))
        due_at = last_finished + delay
        if (consecutive_failures > 0 and last_started is not None
                and delay == INTERVAL):
            # Do not grant grace for shorter retries, legacy receipts,
            # or any moment before the previous cycle finished.
            due_at = max(last_finished, due_at - FAILURE_TRIGGER_JITTER)
    seconds = max(0, int((due_at - now).total_seconds()))
    return {"decision": "DUE" if seconds == 0 else "WAIT",
            "retry_after_seconds": seconds}

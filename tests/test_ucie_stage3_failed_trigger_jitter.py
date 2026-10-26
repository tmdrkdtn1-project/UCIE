"""Regression for capped failure backoff aligned to fixed hourly Windows task.

All times synthetic. No scheduler registration, network or disk modification.
"""
import unittest
from datetime import datetime, timedelta, timezone
from ucie_miner.schedule_policy import next_cycle

START = datetime(2026, 10, 26, 2, 37, 10, tzinfo=timezone.utc)
FINISH = START + timedelta(seconds=3)
HOURLY_TRIGGER = START + timedelta(hours=1)


class BoundedFailedTriggerSkew(unittest.TestCase):
    def test_previous_failure_at_real_scheduled_boundary_is_due(self):
        self.assertEqual(
            next_cycle(FINISH, now=HOURLY_TRIGGER,
                       last_started=START, consecutive_failures=6)["decision"],
            "DUE")

    def test_too_early_still_waits(self):
        self.assertEqual(
            next_cycle(FINISH, now=FINISH + timedelta(minutes=59, seconds=40),
                       last_started=START, consecutive_failures=6)["decision"],
            "WAIT")

    def test_legacy_receipt_without_start_has_no_grace(self):
        self.assertEqual(
            next_cycle(FINISH, now=HOURLY_TRIGGER,
                       consecutive_failures=6)["decision"],
            "WAIT")

    def test_never_retries_before_previous_completion(self):
        self.assertEqual(
            next_cycle(FINISH, now=FINISH,
                       last_started=START, consecutive_failures=6)["decision"],
            "WAIT")

    def test_short_backoff_and_success_unchanged(self):
        self.assertEqual(
            next_cycle(FINISH, now=FINISH + timedelta(minutes=3, seconds=50),
                       last_started=START, consecutive_failures=2)["decision"],
            "WAIT")
        self.assertEqual(
            next_cycle(FINISH, now=HOURLY_TRIGGER,
                       last_started=START, consecutive_failures=0)["decision"],
            "DUE")


if __name__ == "__main__":
    unittest.main()

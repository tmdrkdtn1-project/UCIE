"""Regression for Stage-3 fractional-second scheduler deadline handling.

All times are synthetic UTC instants. No Windows task, network or DB changes.
"""
import unittest
from datetime import datetime, timedelta, timezone
from ucie_miner.schedule_policy import next_cycle

BASE = datetime(2026, 11, 6, 9, 0, 0, tzinfo=timezone.utc)


class FractionalDueBoundary(unittest.TestCase):
    def test_success_start_based_one_microsecond_early_waits(self):
        start = BASE
        finish = BASE + timedelta(seconds=10)
        due = BASE + timedelta(minutes=59, seconds=30)
        result = next_cycle(finish, now=due - timedelta(microseconds=1),
                            last_started=start)
        self.assertEqual(result, {"decision": "WAIT", "retry_after_seconds": 1})

    def test_success_start_based_exact_due(self):
        due = BASE + timedelta(minutes=59, seconds=30)
        result = next_cycle(BASE + timedelta(seconds=10), now=due,
                            last_started=BASE)
        self.assertEqual(result, {"decision": "DUE", "retry_after_seconds": 0})

    def test_legacy_finish_anchored_half_second_early_waits(self):
        result = next_cycle(
            BASE, now=BASE + timedelta(minutes=59, seconds=59, microseconds=500000))
        self.assertEqual(result, {"decision": "WAIT", "retry_after_seconds": 1})

    def test_failure_backoff_quarter_second_early_waits(self):
        due = BASE + timedelta(minutes=8)
        result = next_cycle(BASE, now=due - timedelta(microseconds=250000),
                            consecutive_failures=3)
        self.assertEqual(result, {"decision": "WAIT", "retry_after_seconds": 1})

    def test_capped_failure_jitter_early_waits(self):
        finish = BASE + timedelta(seconds=3)
        due = finish + timedelta(minutes=59, seconds=45)
        result = next_cycle(finish, now=due - timedelta(microseconds=100),
                            last_started=BASE, consecutive_failures=6)
        self.assertEqual(result, {"decision": "WAIT", "retry_after_seconds": 1})

    def test_remaining_one_point_five_seconds_is_rounded_up(self):
        due = BASE + timedelta(hours=1)
        result = next_cycle(
            BASE, now=due - timedelta(seconds=1, microseconds=500000))
        self.assertEqual(result, {"decision": "WAIT", "retry_after_seconds": 2})

    def test_first_cycle_due_remains_unchanged(self):
        self.assertEqual(next_cycle(None, now=BASE),
                         {"decision": "DUE", "retry_after_seconds": 0})


if __name__ == "__main__":
    unittest.main()

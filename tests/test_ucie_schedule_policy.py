"""Stage-3 scheduling policy tests, entirely offline."""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from ucie_miner.core import MiningError
from ucie_miner.schedule_policy import next_cycle

UTC = timezone.utc


class SchedulePolicyTests(unittest.TestCase):
    def setUp(self):
        self.now = datetime(2026, 10, 14, 4, tzinfo=UTC)

    def test_first_cycle_due(self):
        self.assertEqual(next_cycle(None, now=self.now)["decision"], "DUE")

    def test_hourly_gate(self):
        self.assertEqual(next_cycle(self.now - timedelta(minutes=30),
                                    now=self.now)["decision"], "WAIT")
        self.assertEqual(next_cycle(self.now - timedelta(hours=1),
                                    now=self.now)["decision"], "DUE")

    def test_task_one_hour_from_last_start_is_due_despite_completion_seconds(self):
        last_started = self.now - timedelta(hours=1)
        last_finished = last_started + timedelta(seconds=8)
        result = next_cycle(last_finished, now=self.now,
                            last_started=last_started)
        self.assertEqual(result["decision"], "DUE")
        # Legacy finish-anchored behavior remains for old receipts.
        self.assertEqual(next_cycle(last_finished, now=self.now)["decision"], "WAIT")

    def test_start_based_cadence_does_not_run_early(self):
        last_started = self.now - timedelta(minutes=59)
        last_finished = last_started + timedelta(seconds=9)
        self.assertEqual(next_cycle(last_finished, now=self.now,
                                     last_started=last_started)["decision"], "WAIT")

    def test_bad_start_timestamp_rejected(self):
        finish = self.now - timedelta(seconds=2)
        for invalid in (
            finish + timedelta(seconds=1),
            finish.replace(tzinfo=None),
            self.now + timedelta(seconds=1),
        ):
            with self.assertRaises(MiningError):
                next_cycle(finish, now=self.now, last_started=invalid)
        with self.assertRaises(MiningError):
            next_cycle(None, now=self.now, last_started=self.now)

    def test_failed_run_backoff_still_anchors_to_last_finish(self):
        started = self.now - timedelta(hours=2)
        finished = self.now - timedelta(minutes=1)
        outcome = next_cycle(finished, last_started=started,
                             now=self.now, consecutive_failures=3)
        self.assertEqual(outcome["decision"], "WAIT")
        self.assertEqual(outcome["retry_after_seconds"], 7 * 60)

    def test_retry_backoff(self):
        result = next_cycle(self.now - timedelta(minutes=1),
                            now=self.now, consecutive_failures=3)
        self.assertEqual(result["retry_after_seconds"], 7 * 60)

    def test_future_clock_denied(self):
        with self.assertRaises(MiningError):
            next_cycle(self.now + timedelta(seconds=1), now=self.now)

    def test_naive_clock_denied(self):
        with self.assertRaises(MiningError):
            next_cycle(None, now=self.now.replace(tzinfo=None))

    def test_invalid_failures_denied(self):
        with self.assertRaises(MiningError):
            next_cycle(None, now=self.now, consecutive_failures=True)

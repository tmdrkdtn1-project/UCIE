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

    def test_ten_minute_gate(self):
        self.assertEqual(next_cycle(self.now - timedelta(minutes=9),
                                    now=self.now)["decision"], "WAIT")
        self.assertEqual(next_cycle(self.now - timedelta(minutes=10),
                                    now=self.now)["decision"], "DUE")

    def test_task_ten_minutes_from_last_start_is_due_despite_completion_seconds(self):
        last_started = self.now - timedelta(minutes=10)
        last_finished = last_started + timedelta(seconds=8)
        result = next_cycle(last_finished, now=self.now,
                            last_started=last_started)
        self.assertEqual(result["decision"], "DUE")
        # Legacy finish-anchored behavior remains for old receipts.
        self.assertEqual(next_cycle(last_finished, now=self.now)["decision"], "WAIT")

    def test_scheduler_seconds_skew_does_not_skip_next_ten_minute_slot(self):
        # At 04:00:00, the prior 03:50 scheduled task may actually have
        # started at 03:50:08. An exact 10-minute guard skips this trigger.
        last_started = self.now - timedelta(minutes=10) + timedelta(seconds=8)
        last_finished = last_started + timedelta(seconds=7)
        self.assertEqual(next_cycle(last_finished, now=self.now,
                                    last_started=last_started)["decision"], "DUE")

    def test_scheduler_jitter_boundary_never_allows_early_manual_repeats(self):
        at_boundary = self.now - timedelta(minutes=10) + timedelta(seconds=30)
        past_boundary = at_boundary + timedelta(seconds=2)
        self.assertEqual(next_cycle(at_boundary + timedelta(seconds=5),
                                    now=self.now, last_started=at_boundary)["decision"], "DUE")
        self.assertEqual(next_cycle(past_boundary + timedelta(seconds=5),
                                    now=self.now, last_started=past_boundary)["decision"], "WAIT")

    def test_start_based_cadence_does_not_run_early(self):
        last_started = self.now - timedelta(minutes=9)
        last_finished = last_started + timedelta(seconds=9)
        self.assertEqual(next_cycle(last_finished, now=self.now,
                                     last_started=last_started)["decision"], "WAIT")

    def test_failure_60min_backoff_is_preserved_after_cadence_change(self):
        started = self.now - timedelta(minutes=60) + timedelta(seconds=8)
        finished = started + timedelta(seconds=7)
        self.assertEqual(next_cycle(finished, now=self.now,
                                    last_started=started,
                                    consecutive_failures=6)["decision"], "DUE")
        self.assertEqual(next_cycle(finished, now=self.now-timedelta(seconds=16),
                                    last_started=started,
                                    consecutive_failures=6)["decision"], "WAIT")

    def test_failure_backoff_is_not_unconditionally_10_minutes(self):
        last_finished = self.now - timedelta(minutes=9)
        result = next_cycle(last_finished, now=self.now, consecutive_failures=4)
        self.assertEqual(result["decision"], "WAIT")
        self.assertEqual(result["retry_after_seconds"], 7*60)

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

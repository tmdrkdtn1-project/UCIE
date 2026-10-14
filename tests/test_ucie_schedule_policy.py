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

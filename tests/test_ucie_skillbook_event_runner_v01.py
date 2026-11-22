"""Event synchronization real first-party tests, never upstream code."""
from __future__ import annotations

import unittest
from ucie_miner.skillbook_event_runner_v01 import (
    run_event_scenario, evaluate_first_party_event_suite,
)


class RealUCIEEventRunnerTests(unittest.TestCase):
    def test_actual_event_wait_and_stable_baseline(self):
        r = run_event_scenario("benign_cleanup")
        self.assertEqual(r["status"], "STABLE_NO_CHANGE")
        self.assertEqual(r["naive_early_baseline"], 7)
        self.assertEqual(r["stabilized_baseline"], 6)
        self.assertEqual(r["after_trial"], 6)
        self.assertTrue(r["real_event_wait_executed"])
        self.assertTrue(r["worker_joined"])

    def test_detect_real_synthetic_difference(self):
        r = run_event_scenario("changed_count")
        self.assertEqual(r["status"], "DIFFERENCE_DETECTED")
        self.assertEqual(r["stabilized_baseline"], 6)
        self.assertEqual(r["after_trial"], 7)
        self.assertTrue(r["worker_joined"])

    def test_missing_completion_fails_closed_without_baseline(self):
        r = run_event_scenario("timeout")
        self.assertEqual(r["status"], "BLOCKED_NO_COMPLETION")
        self.assertIsNone(r["stabilized_baseline"])
        self.assertIsNone(r["after_trial"])
        self.assertTrue(r["worker_joined"])

    def test_bounded_run_repeatedly_produces_same_statuses(self):
        for _ in range(8):
            r = evaluate_first_party_event_suite()
            self.assertEqual(r["passed"], 3)
            self.assertEqual(r["total"], 3)
            self.assertEqual(r["status"], "UCIE_EVENT_SYNTHETIC_PASS_NOT_UPSTREAM_QA")
            self.assertEqual([x["status"] for x in r["cases"]],
                ["STABLE_NO_CHANGE", "DIFFERENCE_DETECTED", "BLOCKED_NO_COMPLETION"])

    def test_reject_unknown_untrusted_mode(self):
        for item in (None, "", "python/cpython", "../other", "real", 1, True):
            with self.subTest(item=item), self.assertRaises(ValueError):
                run_event_scenario(item)

    def test_no_project_data_or_runtime_mutation(self):
        for mode in ("benign_cleanup", "changed_count", "timeout"):
            r = run_event_scenario(mode)
            self.assertFalse(r["real_fd_count_measured"])
            self.assertFalse(r["source_api_called"])
            self.assertFalse(r["upstream_code_executed"])
            self.assertFalse(r["c40_or_scheduled_tasks_modified"])
            self.assertEqual(r["operating_database_writes"], 0)


if __name__ == "__main__":
    unittest.main()

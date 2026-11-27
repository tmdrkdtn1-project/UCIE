"""B5 offline fixed-task technical probe contract and route tests."""
import unittest
from unittest.mock import patch

from ucie_miner.b5_local_task_probe_v01 import B5ProbeError, run_b5_local_probe


class TestB5Probe(unittest.TestCase):
    def test_real_fixed_render_paths(self):
        report = run_b5_local_probe(2)
        self.assertEqual(report["task_count"], 7)
        self.assertEqual(report["task_observations"], 14)
        self.assertEqual(len(report["rows"]), 7)
        self.assertTrue(all(r["expected_content_found"] for r in report["rows"]))
        self.assertTrue(all(r["route_render_wall_median_ms"] >= 0 for r in report["rows"]))
        self.assertTrue(all(
            (r["route_render_cpu_median_ms"] is None
             and r["cpu_measurement_status"] == "BELOW_TIMER_RESOLUTION")
            or (r["route_render_cpu_median_ms"] >= 0
                and r["cpu_measurement_status"] == "MEASURED")
            for r in report["rows"]))

    def test_human_and_comparative_outcomes_remain_unmeasured(self):
        report = run_b5_local_probe(1)
        for field in ("official_documentation_baseline", "normal_tools_baseline",
                      "novice_first_action_within_10s", "human_comprehension",
                      "buyer_willingness", "peak_ram", "retest_cost"):
            self.assertEqual(report[field], "NOT_MEASURED")
        self.assertFalse(report["persistent_usage_logs"])
        self.assertFalse(report["export_allowed"])
        self.assertEqual(report["operating_database_writes"], 0)

    def test_bounded_repeat_count(self):
        for value in (0, -1, 6, True, "2"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(B5ProbeError, "INVALID_REPETITIONS"):
                    run_b5_local_probe(value)

    def test_render_mismatch_fails_closed(self):
        from ucie_miner import v2_b1_b4_explorer_v01 as explorer
        with patch.object(explorer, "route_v2_request",
                          return_value=(200, "<main>wrong</main>")):
            with self.assertRaisesRegex(B5ProbeError, "FIXED_TASK_UNEXPECTED_OUTPUT"):
                run_b5_local_probe(1)


if __name__ == "__main__":
    unittest.main()

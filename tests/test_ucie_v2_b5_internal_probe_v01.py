"""B5 self-contained UCIE technical workload and honest hold probes."""
from __future__ import annotations

from unittest import TestCase, mock

from ucie_miner import ucie_v2_b5_internal_probe_v01 as b5


class V2B5InternalProbeTests(TestCase):
    def test_actual_b1_to_b4_truth_path(self):
        row = b5._check_once()
        self.assertEqual(row["case_id"], "mcp-prompts")
        self.assertEqual(row["source_retest_proposals"], 0)
        self.assertEqual(row["false_positive_proof_claims"], 0)
        self.assertEqual(row["synthetic_wire_statuses"], (
            "CONTRACT_MATCH", "CONTRACT_VIOLATION", "CONTROL_ONLY"))
        self.assertEqual(len(row["hypothesis_content_sha256"]), 64)

    def test_resource_probe_uses_actual_modules_not_mock(self):
        row = b5.run_internal_probe(repeats=2)
        self.assertEqual(row["schema"], b5.SCHEMA)
        self.assertEqual(row["status"], "UCIE_OWNED_INTERNAL_MEASUREMENT_ONLY")
        self.assertEqual(row["repeats"], 2)
        self.assertEqual(len(row["wall_ns_samples"]), 2)
        self.assertEqual(len(row["cpu_ns_samples"]), 2)
        self.assertTrue(all(type(n) is int and n >= 0
                            for n in row["wall_ns_samples"]))
        self.assertTrue(all(type(n) is int and n >= 0
                            for n in row["cpu_ns_samples"]))
        self.assertGreater(row["python_peak_traced_bytes"], 0)

    def test_actual_b1_b2_id_matches_hypothesis(self):
        row = b5.run_internal_probe(repeats=2)
        self.assertIn("UCIE-CAPSULE-MCP-PROMPTS", row["capsule_id"])
        self.assertTrue(row["hypothesis_id"].startswith("UCIE-B4-HYP-"))

    def test_no_owner_or_customer_pass_claims(self):
        row = b5.run_internal_probe(repeats=2)
        for name in (
            "real_customer_pc_tested", "real_mcp_sdk_rerun",
            "official_docs_baseline_measured", "general_tool_baseline_measured",
            "comparative_speedup_claimed", "human_task_success_claimed",
            "independent_qa_verified", "customer_release_authorized",
            "auto_promoted", "model_trained",
        ):
            self.assertIs(row[name], False, name)
        self.assertEqual(row["real_user_sample_count"], 0)
        self.assertEqual(row["network_requests"], 0)
        self.assertEqual(row["operating_database_writes"], 0)

    def test_resource_scope_is_python_allocations_only(self):
        row = b5.run_internal_probe(repeats=2)
        self.assertEqual(
            row["resource_scope"],
            "CURRENT_DISPOSABLE_PROCESS_PYTHON_ALLOCATIONS_ONLY")

    def test_negative_and_edge_repeat_bounds_reject(self):
        for value in (-1, 0, 1, 13, True, False, "2", 2.0, None, {}, []):
            with self.subTest(value=repr(value)):
                with self.assertRaises(b5.B5ProbeError):
                    b5.run_internal_probe(repeats=value)

    def test_tracemalloc_competing_profiler_is_rejected(self):
        with mock.patch.object(b5.tracemalloc, "is_tracing", return_value=True):
            with self.assertRaises(b5.B5ProbeError):
                b5.run_internal_probe(repeats=2)

    def test_b2_disconnected_ui_rejected(self):
        with mock.patch(
            "ucie_miner.ucie_v2_beginner_preview_v01.render_preview",
            return_value="<html>mock only</html>",
        ):
            with self.assertRaises(b5.B5ProbeError):
                b5._check_once()

    def test_b4_without_negative_control_rejected(self):
        from ucie_miner import ucie_v2_generalization_transfer_v01 as b4
        actual = b4.run_bounded_transfer(b4.build_hypothesis())
        forged = {**actual, "positive_negative_control":
                  ["CONTRACT_MATCH", "CONTRACT_MATCH", "CONTROL_ONLY"]}
        with mock.patch.object(b4, "run_bounded_transfer", return_value=forged):
            with self.assertRaises(b5.B5ProbeError):
                b5._check_once()

    def test_b3_unnecessary_retests_rejected(self):
        from ucie_miner import ucie_v2_revision_impact_v01 as b3
        baseline = b3.assess_revision_impacts(())
        forged = {**baseline, "proposed_test_files": ["unrelated_test.py"]}
        with mock.patch.object(b3, "assess_revision_impacts", return_value=forged):
            with self.assertRaises(b5.B5ProbeError):
                b5._check_once()

    def test_b1_claimed_license_is_not_a_success(self):
        from ucie_miner import ucie_v2_capsule_v01 as b1
        original = b1.explain_for_beginner
        def forged(capsule, app):
            return {**original(capsule, app), "rights": "APPROVED"}
        with mock.patch.object(b1, "explain_for_beginner", side_effect=forged):
            # B2 itself blocks forged customer rights *before* the B5
            # postcondition runs. Preserve that earlier fail-closed boundary.
            with self.assertRaisesRegex(
                ValueError, "B1 evidence drift blocks isolated preview"
            ):
                b5._check_once()


if __name__ == "__main__":
    import unittest
    unittest.main()
